#!/usr/bin/env python3
"""Coleta oficial — TCC Paradoxo da Governança em Escala (protocolo v1.5).

Modos:
    ./coletar_dados_sonar.py
    ./coletar_dados_sonar.py --only gson
    ./coletar_dados_sonar.py --limit 3
    ./coletar_dados_sonar.py --skip-existing
    ./coletar_dados_sonar.py --phase scan|extract|validate|all
    ./coletar_dados_sonar.py --data-coleta 2026-05-15

Saída em dados/YYYY-MM-DD/:
    consolidado.csv, issues/{id}.json, regras_metadata.json,
    ambiente.txt, coleta.log
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from coleta_lib import consolidacao, extracao, scan
from coleta_lib.io_utils import (
    ColetaError, N_AMOSTRA, ProjetoError, SonarClient, carregar_env,
    carregar_planilha, dir_dados, filtrar_planilha, hash_arquivo, now_iso,
    setup_logger,
)

BASE_DIR = Path("/home/mateus/Documentos/artigos-tcc/repos/tcc")
SCRIPTS_DIR = BASE_DIR / "scripts-tcc"
CSV_PATH = SCRIPTS_DIR / "projetos-tcc-dataset-4.csv"
ENV_PATH = SCRIPTS_DIR / ".env"
CLONES_DIR = BASE_DIR / "projetos-clonados"

PHASES = ["scan", "extract", "validate", "all"]


def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--only", default=None,
                   help="processar apenas o projeto com nome ou id")
    p.add_argument("--limit", type=int, default=0,
                   help="processar apenas os N primeiros (após filtro de arquétipo)")
    p.add_argument("--skip-existing", action="store_true",
                   help="pular scan se projeto já existe no Sonar")
    p.add_argument("--phase", choices=PHASES, default="all",
                   help="rodar apenas uma fase")
    p.add_argument("--data-coleta", default=None,
                   help="data ISO YYYY-MM-DD (default: hoje)")
    return p.parse_args(argv)


def main(argv=None) -> int:
    args = parse_args(argv)

    try:
        env = carregar_env(ENV_PATH)
    except ColetaError as e:
        print(f"[ERRO] {e}", file=sys.stderr); return 2

    # Precedência: --data-coleta CLI > DATA_COLETA do .env > hoje
    data_coleta = args.data_coleta or env.get("DATA_COLETA")

    saida = dir_dados(BASE_DIR, data_coleta)
    log_path = saida / "coleta.log"
    logger = setup_logger(log_path)

    logger.info("=" * 70)
    logger.info("coletar_dados_sonar.py — protocolo v1.5 — %s", now_iso())
    logger.info("Saída: %s", saida)
    logger.info("data_coleta=%s (fonte: %s)", data_coleta or "(hoje)",
                "CLI" if args.data_coleta else "env" if env.get("DATA_COLETA") else "default")

    sonar_url = env["SONAR_URL"]
    sonar_token = env["SONAR_TOKEN"]
    logger.info("Sonar: %s (token=%s)", sonar_url, "<oculto>")

    client = SonarClient(sonar_url, sonar_token, logger)
    if not client.system_status_ok():
        logger.error("Sonar não acessível em %s", sonar_url)
        return 3

    # Planilha
    try:
        rows_full = carregar_planilha(CSV_PATH, logger)
        rows = filtrar_planilha(rows_full, args.only, args.limit)
    except ColetaError as e:
        logger.error(str(e)); return 4
    logger.info("Processando %d projeto(s) (filtros: only=%s limit=%d)",
                len(rows), args.only, args.limit)

    log_dir = saida / "scanner-logs"
    log_dir.mkdir(exist_ok=True)
    issues_dir = saida / "issues"
    issues_dir.mkdir(exist_ok=True)

    metricas_por_id: dict[str, dict] = {}
    issues_count: dict[str, int] = {}
    scan_results: list[dict] = []

    t0 = time.time()

    # ---------------- Fase 1: scan ----------------
    if args.phase in ("scan", "all"):
        logger.info("=" * 70); logger.info("FASE 1 — scan")
        for i, r in enumerate(rows, start=1):
            pid = r["id"]; nome = r["nome"]
            logger.info("[%d/%d] %s (%s)", i, len(rows), pid, r["arquetipo"])
            repo = CLONES_DIR / nome
            try:
                res = scan.coletar_um_projeto(
                    r, repo, BASE_DIR, log_dir, sonar_url, sonar_token,
                    client, logger, skip_existing=args.skip_existing,
                )
            except ColetaError as e:
                logger.error("[ABORT] %s", e); return 5
            except Exception as e:
                logger.exception("[%s] erro inesperado: %s", pid, e)
                res = {"id": pid, "scan_ok": False, "build_caminho": f"erro: {e}"}
            scan_results.append(res)

    # ---------------- Fase 2: extracao (métricas + issues) ----------------
    if args.phase in ("extract", "all"):
        logger.info("=" * 70); logger.info("FASE 2 — métricas (component) + issues")
        for r in rows:
            pid = r["id"]
            try:
                m = extracao.extrair_metricas(client, pid, logger)
                metricas_por_id[pid] = m
                n_issues = extracao.extrair_issues(client, pid, issues_dir, logger,
                                                   metricas=m)
                issues_count[pid] = n_issues
            except ProjetoError as e:
                logger.error("[PROJ_ERR] %s — issues incompletas, seguindo", e)
                issues_count[pid] = -1
            except ColetaError as e:
                logger.error("[ABORT] %s", e); return 5

        # Fase 4 inline: regras
        logger.info("=" * 70); logger.info("FASE 4 — regras_metadata")
        rule_keys = extracao.carregar_issues_acumulado(issues_dir)
        try:
            extracao.coletar_regras_metadata(
                client, rule_keys,
                saida / "regras_metadata.json", logger,
            )
        except ColetaError as e:
            logger.error("[ABORT] %s", e); return 5

    # ---------------- Fase 5: consolidação ----------------
    if args.phase in ("validate", "all"):
        logger.info("=" * 70); logger.info("FASE 5 — consolidação + validação")

        # Detecta execução parcial: --only ou --limit ou rows < 35.
        # Nesse caso, faz MERGE com consolidado.csv pré-existente para
        # preservar projetos não processados nesta execução.
        parcial = bool(args.only) or bool(args.limit) or len(rows) < len(rows_full)

        if not metricas_por_id:
            for r in rows:
                pid = r["id"]
                metricas_por_id[pid] = extracao.extrair_metricas(client, pid, logger)

        # data_coleta para idade_snapshot_dias (§A13). Usa o nome do dir
        # de saída (já é YYYY-MM-DD) — assim valor é consistente com onde
        # o consolidado está escrito, mesmo se a coleta levar dias.
        consolidacao.montar_consolidado(
            rows, metricas_por_id,
            saida / "consolidado.csv", logger,
            merge=parcial,
            data_coleta=saida.name,
        )
        h = hash_arquivo(saida / "consolidado.csv")
        consolidacao.escrever_ambiente(saida, BASE_DIR, sonar_url, sonar_token,
                                       h, logger)

        # Validação usa o n efetivo do CSV em disco, não o da execução
        n_total_disco = sum(1 for _ in (saida / "consolidado.csv").open(encoding="utf-8")) - 1
        if parcial and n_total_disco != len(rows_full):
            logger.warning("Execução parcial (%d/%d projetos). Validação completa "
                           "(N=%d) só roda quando consolidado.csv estiver completo.",
                           len(rows), len(rows_full), N_AMOSTRA)
            erros = consolidacao.validar(saida, n_esperado=n_total_disco, logger=logger)
        else:
            erros = consolidacao.validar(saida, n_esperado=len(rows_full), logger=logger)
        if erros:
            logger.error("Validação reportou %d erros (mantendo arquivos para debug)", len(erros))

    elapsed = time.time() - t0
    logger.info("=" * 70)
    logger.info("Resumo: scan=%d ok=%d issues_total=%d",
                len(scan_results),
                sum(1 for r in scan_results if r.get("scan_ok")),
                sum(issues_count.values()))
    logger.info("Tempo total: %.1fs", elapsed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
