"""Fase 5 — monta consolidado.csv, ambiente.txt e valida coerência."""
from __future__ import annotations

import csv
import json
import logging
import platform
import subprocess
from datetime import datetime
from pathlib import Path

from .io_utils import ColetaError, derivar_instancia, hash_arquivo, mask_token

CONSOLIDADO_COLS = [
    "id", "nome", "empresa", "arquetipo", "instancia", "status",
    "tag", "commit_sha", "data_commit", "idade_anos", "contribuidores",
    "loc_total", "loc_java",
    "sqale_index", "ncloc",
    "sqale_debt_ratio", "code_smells", "bugs", "vulnerabilities",
    "complexity", "cognitive_complexity",
    "duplicated_lines_density", "comment_lines_density",
]

PROTOCOL_VERSION = "1.5"
SONAR_VERSION = "Community Build v26.2.0.119303"
SONAR_MODE = "MQR"
SCANNER_VERSION = "sonar-scanner-5.0.1.3006-linux"


def _parse_first_int(s: str) -> int | float:
    if s in (None, "", "NaN"):
        return float("nan")
    try:
        return int(s)
    except ValueError:
        try:
            return float(s)
        except ValueError:
            return float("nan")


def _build_row(r: dict, m: dict) -> dict:
    return {
        "id":                       r["id"],
        "nome":                     r.get("nome", ""),
        "empresa":                  r.get("empresa", ""),
        "arquetipo":                r.get("arquetipo", ""),
        "instancia":                derivar_instancia(r),
        "status":                   r.get("status", ""),
        "tag":                      r.get("tag", ""),
        "commit_sha":               r.get("commit_sha", ""),
        "data_commit":              r.get("data_commit", ""),
        "idade_anos":               r.get("idade_anos", ""),
        "contribuidores":           r.get("contribuidores", ""),
        "loc_total":                r.get("loc_total", ""),
        "loc_java":                 r.get("loc_java", "") or m.get("loc_java_sonar", ""),
        "sqale_index":              m.get("sqale_index", ""),
        "ncloc":                    m.get("ncloc", ""),
        "sqale_debt_ratio":         m.get("sqale_debt_ratio", ""),
        "code_smells":              m.get("code_smells", ""),
        "bugs":                     m.get("bugs", ""),
        "vulnerabilities":          m.get("vulnerabilities", ""),
        "complexity":               m.get("complexity", ""),
        "cognitive_complexity":     m.get("cognitive_complexity", ""),
        "duplicated_lines_density": m.get("duplicated_lines_density", ""),
        "comment_lines_density":    m.get("comment_lines_density", ""),
    }


def montar_consolidado(rows_planilha: list[dict],
                       metricas_por_id: dict[str, dict],
                       saida_csv: Path, logger: logging.Logger,
                       merge: bool = False) -> None:
    """Grava consolidado.csv. Se merge=True e o arquivo já existir, preserva
    linhas para projetos NÃO incluídos em rows_planilha (usado com
    --only/--limit). Modo padrão (merge=False) sobrescreve totalmente."""
    novos = {r["id"]: _build_row(r, metricas_por_id.get(r["id"], {}))
             for r in rows_planilha}

    if merge and saida_csv.exists():
        with saida_csv.open(encoding="utf-8") as f:
            reader = csv.DictReader(f)
            existentes = {row["id"]: row for row in reader}
        # Atualiza só as linhas dos IDs processados nesta execução
        existentes.update(novos)
        out_rows = list(existentes.values())
        logger.info("consolidado.csv merge: %d linhas pré-existentes, %d atualizadas",
                    len(existentes), len(novos))
    else:
        out_rows = list(novos.values())

    saida_csv.parent.mkdir(parents=True, exist_ok=True)
    with saida_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CONSOLIDADO_COLS)
        w.writeheader()
        for row in out_rows:
            w.writerow(row)
    logger.info("consolidado.csv escrito: %s (%d linhas)", saida_csv, len(out_rows))


def _java_version() -> str:
    try:
        r = subprocess.run(["java", "-version"], capture_output=True, text=True)
        return (r.stderr or r.stdout).splitlines()[0] if (r.stderr or r.stdout) else "?"
    except Exception:
        return "?"


def _git_tag(base_dir: Path) -> str:
    try:
        r = subprocess.run(["git", "describe", "--tags", "--always"],
                           cwd=str(base_dir), capture_output=True, text=True)
        return r.stdout.strip() or "?"
    except Exception:
        return "?"


def escrever_ambiente(saida_dir: Path, base_dir: Path, sonar_url: str,
                      sonar_token: str, hash_consolidado: str,
                      logger: logging.Logger) -> Path:
    p = saida_dir / "ambiente.txt"
    lines = [
        f"SonarQube: {SONAR_VERSION}",
        f"Modo: {SONAR_MODE}",
        f"Scanner: {SCANNER_VERSION}",
        f"JDK: {_java_version()}",
        f"Python: {platform.python_version()}",
        f"Plataforma: {platform.platform()}",
        f"Data da coleta: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"SONAR_URL: {sonar_url}",
        f"SONAR_TOKEN (mask): {mask_token(sonar_token)}",
        f"Hash do consolidado.csv: {hash_consolidado}",
        f"Versão do protocolo: {PROTOCOL_VERSION}",
        f"Tag git do repo TCC: {_git_tag(base_dir)}",
    ]
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    logger.info("ambiente.txt escrito: %s", p)
    return p


def validar(saida_dir: Path, n_esperado: int, logger: logging.Logger) -> list[str]:
    """Roda checagens de coerência. Retorna lista de erros (string vazia = OK)."""
    erros: list[str] = []
    cons_path = saida_dir / "consolidado.csv"
    if not cons_path.exists():
        erros.append("consolidado.csv ausente")
        return erros

    with cons_path.open(encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    if len(rows) != n_esperado:
        erros.append(f"consolidado.csv tem {len(rows)} linhas (esperado {n_esperado})")

    issues_dir = saida_dir / "issues"
    rule_keys = set()
    for r in rows:
        pid = r["id"]
        ipath = issues_dir / f"{pid}.json"
        if not ipath.exists():
            erros.append(f"issues/{pid}.json ausente")
            continue
        try:
            data = json.loads(ipath.read_text(encoding="utf-8"))
        except Exception as e:
            erros.append(f"issues/{pid}.json inválido: {e}")
            continue
        parciais_flag = False
        total_sonar = None
        if isinstance(data, dict) and "issues" in data:
            parciais_flag = bool(data.get("parciais"))
            total_sonar = data.get("total_sonar")
            data = data["issues"]
        if not isinstance(data, list):
            erros.append(f"issues/{pid}.json: estrutura inesperada")
            continue
        for it in data:
            rk = it.get("rule")
            if rk:
                rule_keys.add(rk)
        if parciais_flag:
            # Paginação ficou aquém do total, mas as métricas agregadas em
            # consolidado.csv vêm de /api/measures/component (sem limite) e
            # são a fonte de verdade da análise estatística. Warning, não erro.
            tot = total_sonar if total_sonar is not None else "?"
            logger.warning("[VALID] %s: issues parciais (%d/%s capturadas — "
                           "usando contagem agregada). Métricas válidas no "
                           "consolidado.", pid, len(data), tot)
        # ncloc / sqale_index não podem ser nulo/0
        for col in ("ncloc", "sqale_index"):
            v = (r.get(col) or "").strip()
            if v in ("", "0", "NaN", "nan"):
                erros.append(f"{pid}: {col} vazio/zero ({v!r}) — quebra pipeline analítico")

    regras_path = saida_dir / "regras_metadata.json"
    if not regras_path.exists():
        erros.append("regras_metadata.json ausente")
    else:
        try:
            meta = json.loads(regras_path.read_text(encoding="utf-8"))
        except Exception as e:
            erros.append(f"regras_metadata.json inválido: {e}")
            meta = {}
        faltam = sorted(rk for rk in rule_keys if rk not in meta)
        if faltam:
            erros.append(f"regras_metadata.json: {len(faltam)} rule_keys ausentes "
                         f"(ex: {faltam[:3]})")

    if erros:
        for e in erros:
            logger.error("[VALID] %s", e)
    else:
        logger.info("[VALID] todas as checagens OK")
    return erros
