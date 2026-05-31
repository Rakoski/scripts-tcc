from __future__ import annotations

import hashlib
import json
import logging
import re
import sys
from datetime import datetime
from pathlib import Path
import math
import pandas as pd

ARQUETIPOS_VALIDOS = {"apache", "google", "descentralizado"}

COLUNAS_OBRIGATORIAS = [
    "id", "nome", "empresa", "arquetipo", "instancia", "status",
    "tag", "commit_sha", "data_commit", "idade_anos", "contribuidores",
    "loc_total", "loc_java", "sqale_index", "ncloc",
    "sqale_debt_ratio", "code_smells", "bugs", "vulnerabilities",
    "complexity", "cognitive_complexity",
    "duplicated_lines_density", "comment_lines_density",
]

class ValidationError(RuntimeError):
    pass

def setup_logger(log_path: Path) -> logging.Logger:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("analise")
    logger.handlers.clear()
    logger.setLevel(logging.DEBUG)

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    fh = logging.FileHandler(log_path, mode="w", encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    sh = logging.StreamHandler(sys.stdout)
    sh.setLevel(logging.INFO)
    sh.setFormatter(fmt)
    logger.addHandler(sh)

    return logger

def parse_effort_minutes(s: object) -> int:
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return 0
    if isinstance(s, (int,)):
        return int(s)
    if isinstance(s, float):
        return int(s)
    s = str(s).strip().lower()
    if not s:
        return 0
    if s.isdigit():
        return int(s)
    total = 0
    for amount, unit in re.findall(r"(\d+)\s*(d|h|min|m)", s):
        amount = int(amount)
        if unit == "d":
            total += amount * 8 * 60
        elif unit == "h":
            total += amount * 60
        elif unit in ("min", "m"):
            total += amount
    return total

def carregar_consolidado(data_dir: Path, logger: logging.Logger) -> pd.DataFrame:
    csv_path = data_dir / "consolidado.csv"
    if not csv_path.exists():
        raise ValidationError(f"Arquivo não encontrado: {csv_path}")

    df = pd.read_csv(csv_path)
    logger.info("consolidado.csv carregado: %d linhas, %d colunas",
                len(df), len(df.columns))

    faltam = [c for c in COLUNAS_OBRIGATORIAS if c not in df.columns]
    if faltam:
        raise ValidationError(f"Colunas obrigatórias ausentes: {faltam}")

    if df["id"].duplicated().any():
        dup = df.loc[df["id"].duplicated(), "id"].tolist()
        raise ValidationError(f"IDs duplicados em consolidado.csv: {dup}")

    arq_invalidos = set(df["arquetipo"].unique()) - ARQUETIPOS_VALIDOS
    if arq_invalidos:
        raise ValidationError(
            f"arquetipo deve estar em {ARQUETIPOS_VALIDOS}; "
            f"valores inválidos: {arq_invalidos}"
        )

    for col in ("ncloc", "sqale_index"):
        nulos = df[df[col].isna() | (df[col] == 0)]
        if not nulos.empty:
            raise ValidationError(
                f"{col} nulo ou zero em projetos: {nulos['id'].tolist()}. "
                f"Pré-§4.1 #2 do protocolo proíbe ncloc=0; corrigir manualmente."
            )

    df["densidade_divida"] = df["sqale_index"] / df["ncloc"]
    df["log_loc"] = df["loc_total"].apply(lambda x: float("nan") if x <= 0 else math.log(x))

    df["arquetipo_ordinal"] = df["arquetipo"].map({
        "google": 1, "apache": 2, "descentralizado": 3
    })

    logger.info("Validação OK; densidade_divida calculada (mediana=%.4f, "
                "min=%.4f, max=%.4f)",
                df["densidade_divida"].median(),
                df["densidade_divida"].min(),
                df["densidade_divida"].max())
    return df

def carregar_issues(data_dir: Path, projeto_ids: list[str],
                    logger: logging.Logger) -> dict[str, pd.DataFrame]:
    issues_dir = data_dir / "issues"
    if not issues_dir.exists():
        logger.warning("Diretório issues/ ausente — decomposição por regras será pulada")
        return {}

    out: dict[str, pd.DataFrame] = {}
    for pid in projeto_ids:
        path = issues_dir / f"{pid}.json"
        if not path.exists():
            logger.warning("issues/%s.json ausente", pid)
            continue
        with path.open(encoding="utf-8") as f:
            payload = json.load(f)
        if isinstance(payload, dict) and "issues" in payload:
            payload = payload["issues"]
        if not isinstance(payload, list):
            raise ValidationError(f"issues/{pid}.json: esperado list, got {type(payload)}")

        rows = []
        for it in payload:
            rows.append({
                "rule": it.get("rule", ""),
                "type": it.get("type", ""),
                "severity": it.get("severity", ""),
                "effort_min": parse_effort_minutes(it.get("effort", 0)),
            })
        out[pid] = pd.DataFrame(rows)
    logger.info("Issues carregados para %d/%d projetos",
                len(out), len(projeto_ids))
    return out

def carregar_regras_metadata(data_dir: Path,
                             logger: logging.Logger) -> dict[str, dict]:
    path = data_dir / "regras_metadata.json"
    if not path.exists():
        logger.warning("regras_metadata.json ausente — tags de regras indisponíveis")
        return {}
    with path.open(encoding="utf-8") as f:
        meta = json.load(f)
    if not isinstance(meta, dict):
        raise ValidationError("regras_metadata.json deve ser dict {rule_key: {...}}")
    logger.info("regras_metadata.json: %d regras", len(meta))
    return meta

def carregar_ambiente(data_dir: Path, logger: logging.Logger) -> str:
    path = data_dir / "ambiente.txt"
    if not path.exists():
        logger.warning("ambiente.txt ausente — relatório sem cabeçalho de ambiente")
        return "(ambiente.txt ausente)"
    return path.read_text(encoding="utf-8")

def hash_arquivo(path: Path) -> str:
    if not path.exists():
        return "(arquivo ausente)"
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def calcular_idade_snapshot(df: pd.DataFrame, data_coleta: str,
                            logger: logging.Logger) -> pd.DataFrame:
    dt_coleta = pd.to_datetime(data_coleta)
    df = df.copy()
    df["idade_snapshot_dias"] = (
        dt_coleta - pd.to_datetime(df["data_commit"])
    ).dt.days
    if (df["idade_snapshot_dias"] < 0).any():
        ids = df.loc[df["idade_snapshot_dias"] < 0, "id"].tolist()
        raise ValidationError(
            f"data_coleta {data_coleta} é anterior a data_commit em {ids}"
        )
    logger.info("idade_snapshot_dias calculada (mediana=%d dias) com data_coleta=%s",
                int(df["idade_snapshot_dias"].median()), data_coleta)
    return df

def garantir_arvore_saida(data_dir: Path) -> dict[str, Path]:
    base = data_dir / "analise"
    paths = {
        "base": base,
        "tabelas": base / "tabelas",
        "figuras": base / "figuras",
    }
    for p in paths.values():
        p.mkdir(parents=True, exist_ok=True)
    return paths

def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")
