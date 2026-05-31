#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import logging
import subprocess
import sys
from pathlib import Path

from coleta_lib.io_utils import (
    N_AMOSTRA,
    PROJETOS_EXCLUIDOS_LIMITACAO_TECNICA,
    get_clones_dir,
    get_scripts_dir,
)

SCRIPTS_DIR = get_scripts_dir()
CLONES_DIR = get_clones_dir()
CSV_PATH = SCRIPTS_DIR / "projetos-tcc-dataset-4.csv"
OUT_CSV = SCRIPTS_DIR / "clones_v17.csv"
LOG_PATH = SCRIPTS_DIR / "clones_v17.log"

SUBCONJUNTOS = ("n34-v1.5", "n30-v1.6")

OUT_COLS = [
    "id", "nome", "empresa", "arquetipo", "status", "url", "tag", "commit_sha",
    "data_commit", "branch_principal", "snapshot_type", "subconjunto", "resultado",
]

TIMEOUT_CLONE = 1800
TIMEOUT_FETCH = 600
TIMEOUT_GIT = 120

def setup_logger() -> logging.Logger:
    logger = logging.getLogger("clones_v17")
    logger.handlers.clear()
    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s",
                            datefmt="%Y-%m-%d %H:%M:%S")
    fh = logging.FileHandler(LOG_PATH, mode="w", encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    logger.addHandler(sh)
    return logger

def run(cmd: list[str], cwd: Path | None = None,
        timeout: int = TIMEOUT_GIT) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd, cwd=str(cwd) if cwd else None,
        capture_output=True, text=True,
        timeout=timeout, check=False,
    )

def carregar_linhas(csv_path: Path) -> list[dict]:
    if not csv_path.exists():
        raise FileNotFoundError(f"Planilha não encontrada: {csv_path}")
    rows: list[dict] = []
    with csv_path.open(newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if (r.get("id") or "").strip():
                rows.append(r)
    return rows

def linha_saida(row: dict, resultado: str) -> dict:
    out = {c: (row.get(c) or "").strip() for c in OUT_COLS if c != "resultado"}
    out["resultado"] = resultado
    return out

def verificar_head(repo: Path, sha: str) -> bool:
    r = run(["git", "rev-parse", "HEAD"], cwd=repo)
    return r.returncode == 0 and r.stdout.strip() == sha

def sha_existe(repo: Path, sha: str) -> bool:
    r = run(["git", "rev-parse", "--verify", "--quiet", f"{sha}^{{commit}}"], cwd=repo)
    return r.returncode == 0

def clonar_projeto(row: dict, logger: logging.Logger,
                   dry_run: bool) -> str:
    nome = (row.get("nome") or "").strip()
    url = (row.get("url") or "").strip()
    sha = (row.get("commit_sha") or "").strip()
    destino = CLONES_DIR / nome

    if not nome or not url or not sha:
        return "falha:planilha-incompleta"

    ja_existe = destino.is_dir() and (destino / ".git").is_dir()

    if dry_run:
        acao = "atualizaria" if ja_existe else "clonaria"
        logger.info("[DRY] %s %s (%s) -> checkout %s",
                    acao, nome, url, sha[:10])
        return "atualizado" if ja_existe else "clonado"

    try:
        if ja_existe:
            logger.info("[%s] já clonado; git fetch origin...", nome)
            r = run(["git", "fetch", "origin", "--quiet"], cwd=destino,
                    timeout=TIMEOUT_FETCH)
            if r.returncode != 0:
                logger.error("[%s] git fetch falhou (rc=%d): %s",
                             nome, r.returncode, r.stderr.strip())
                return "falha:fetch"
            resultado = "atualizado"
        else:
            logger.info("[%s] git clone %s ...", nome, url)
            r = run(["git", "clone", url, str(destino)], timeout=TIMEOUT_CLONE)
            if r.returncode != 0:
                logger.error("[%s] git clone falhou (rc=%d): %s",
                             nome, r.returncode, r.stderr.strip())
                return "falha:clone"
            resultado = "clonado"

        r = run(["git", "checkout", "--quiet", sha], cwd=destino, timeout=TIMEOUT_GIT)
        if r.returncode != 0:
            if not sha_existe(destino, sha):
                logger.error("[%s] SHA %s não existe no repo (upstream mudou?)",
                             nome, sha[:10])
                return "falha:sha-not-found"
            logger.error("[%s] git checkout falhou (rc=%d): %s",
                         nome, r.returncode, r.stderr.strip())
            return "falha:checkout"

        if not verificar_head(destino, sha):
            logger.error("[%s] HEAD != commit_sha esperado (%s)", nome, sha[:10])
            return "falha:head-mismatch"

        logger.info("[%s] OK (%s) HEAD=%s", nome, resultado, sha[:10])
        return resultado

    except subprocess.TimeoutExpired:
        logger.error("[%s] TIMEOUT", nome)
        return "falha:timeout"

def selecionar(rows: list[dict], subset: str | None,
               include_excluded: bool) -> tuple[list[dict], list[dict]]:
    if subset:
        rows = [r for r in rows if (r.get("subconjunto") or "").strip() == subset]

    a_clonar: list[dict] = []
    a_excluir: list[dict] = []
    for r in rows:
        pid = (r.get("id") or "").strip()
        if pid in PROJETOS_EXCLUIDOS_LIMITACAO_TECNICA and not include_excluded:
            a_excluir.append(r)
        else:
            a_clonar.append(r)
    return a_clonar, a_excluir

def _contar(rows: list[dict], chave: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for r in rows:
        k = (r.get(chave) or "").strip() or "?"
        out[k] = out.get(k, 0) + 1
    return out

def imprimir_resumo(logger: logging.Logger, a_clonar: list[dict],
                    a_excluir: list[dict], resultados: dict[str, str],
                    subset: str | None, include_excluded: bool,
                    dry_run: bool) -> int:
    clonados = sum(1 for v in resultados.values() if v == "clonado")
    atualizados = sum(1 for v in resultados.values() if v == "atualizado")
    falhas = {pid: v for pid, v in resultados.items() if v.startswith("falha")}
    ok_rows = [r for r in a_clonar
               if resultados.get((r.get("id") or "").strip(), "").startswith(
                   ("clonado", "atualizado"))]

    esperado_total = len(a_clonar)
    esp_arq = _contar(a_clonar, "arquetipo")
    esp_sub = _contar(a_clonar, "subconjunto")
    obt_arq = _contar(ok_rows, "arquetipo")
    obt_sub = _contar(ok_rows, "subconjunto")

    ok = True
    logger.info("=" * 60)
    logger.info("=== RESUMO%s ===", " (DRY-RUN)" if dry_run else "")
    logger.info("Clonados: %d", clonados)
    logger.info("Atualizados: %d", atualizados)
    logger.info("Excluídos (limitação técnica): %d", len(a_excluir))
    for r in a_excluir:
        pid = (r.get("id") or "").strip()
        logger.info("    - %s: %s", pid,
                    PROJETOS_EXCLUIDOS_LIMITACAO_TECNICA.get(pid, ""))
    logger.info("Falhas: %d", len(falhas))
    for pid, v in falhas.items():
        logger.info("    - %s: %s", pid, v)

    logger.info("")
    logger.info("Composição clonada por arquétipo (obtido / esperado):")
    for arq in sorted(esp_arq):
        obt = obt_arq.get(arq, 0)
        esp = esp_arq[arq]
        marca = "" if obt == esp else "  <-- DIVERGÊNCIA"
        if obt != esp:
            ok = False
        logger.info("  %-16s %d (esperado: %d)%s", arq + ":", obt, esp, marca)
    obt_total = len(ok_rows)
    if obt_total != esperado_total:
        ok = False
    logger.info("  %-16s %d (esperado: %d)%s", "TOTAL:", obt_total,
                esperado_total, "" if obt_total == esperado_total else "  <-- DIVERGÊNCIA")

    logger.info("")
    logger.info("Composição por subconjunto (obtido / esperado):")
    for sub in sorted(esp_sub):
        obt = obt_sub.get(sub, 0)
        esp = esp_sub[sub]
        if obt != esp:
            ok = False
        logger.info("  %-16s %d (esperado: %d)%s", sub + ":", obt, esp,
                    "" if obt == esp else "  <-- DIVERGÊNCIA")

    if not subset and not include_excluded:
        if esperado_total != N_AMOSTRA:
            ok = False
            logger.error("Alvo efetivo %d != N_AMOSTRA %d (io_utils) — "
                         "planilha ou exclusões inconsistentes!",
                         esperado_total, N_AMOSTRA)

    logger.info("=" * 60)
    if dry_run:
        return 0 if ok else 2
    return 0 if (ok and not falhas) else 2

def parse_args(argv=None):
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--include-excluded", action="store_true",
                   help="clona inclusive os projetos em PROJETOS_EXCLUIDOS "
                        "(reprodução total)")
    p.add_argument("--subset", choices=SUBCONJUNTOS, default=None,
                   help="clona apenas o subconjunto indicado")
    p.add_argument("--dry-run", action="store_true",
                   help="lista o que seria feito, sem clonar nem escrever CSV")
    return p.parse_args(argv)

def main(argv=None) -> int:
    args = parse_args(argv)
    logger = setup_logger()
    logger.info("=== clonar_v17 — planilha: %s ===", CSV_PATH.name)
    if args.subset:
        logger.info("Filtro --subset: %s", args.subset)
    if args.include_excluded:
        logger.info("Flag --include-excluded: incluindo projetos excluídos")

    rows = carregar_linhas(CSV_PATH)
    logger.info("Planilha: %d linhas brutas", len(rows))

    a_clonar, a_excluir = selecionar(rows, args.subset, args.include_excluded)
    logger.info("A clonar: %d | Excluídos pulados: %d",
                len(a_clonar), len(a_excluir))

    if not args.dry_run:
        CLONES_DIR.mkdir(parents=True, exist_ok=True)

    resultados: dict[str, str] = {}
    linhas_out: list[dict] = []

    for r in a_excluir:
        pid = (r.get("id") or "").strip()
        resultados[pid] = "excluido"
        linhas_out.append(linha_saida(r, "excluido"))

    for i, r in enumerate(a_clonar, 1):
        pid = (r.get("id") or "").strip()
        logger.info("[%d/%d] %s", i, len(a_clonar), pid)
        res = clonar_projeto(r, logger, args.dry_run)
        resultados[pid] = res
        linhas_out.append(linha_saida(r, res))

    if not args.dry_run:
        if OUT_CSV.exists():
            backup = OUT_CSV.with_suffix(".csv.bak")
            OUT_CSV.replace(backup)
            logger.info("clones_v17.csv anterior preservado em %s", backup.name)
        tmp = OUT_CSV.with_suffix(".csv.tmp")
        with tmp.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=OUT_COLS)
            w.writeheader()
            w.writerows(linhas_out)
        tmp.replace(OUT_CSV)
        logger.info("CSV de auditoria: %s", OUT_CSV)

    return imprimir_resumo(logger, a_clonar, a_excluir, resultados,
                           args.subset, args.include_excluded, args.dry_run)

if __name__ == "__main__":
    sys.exit(main())
