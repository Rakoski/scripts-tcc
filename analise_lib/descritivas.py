from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd

ARQUETIPOS_ORDEM = ["google", "apache", "descentralizado"]

def _resumo(serie: pd.Series) -> dict:
    return {
        "n": int(serie.size),
        "mediana": float(serie.median()),
        "Q1": float(serie.quantile(0.25)),
        "Q3": float(serie.quantile(0.75)),
        "IQR": float(serie.quantile(0.75) - serie.quantile(0.25)),
        "variancia": float(serie.var(ddof=1)) if serie.size > 1 else float("nan"),
        "desvio": float(serie.std(ddof=1)) if serie.size > 1 else float("nan"),
        "min": float(serie.min()),
        "max": float(serie.max()),
    }

def descritivas_por_arquetipo(df: pd.DataFrame, tabelas_dir: Path,
                              logger: logging.Logger) -> pd.DataFrame:
    rows = []
    for arq in ARQUETIPOS_ORDEM:
        sub = df[df["arquetipo"] == arq]["densidade_divida"]
        rows.append({"arquetipo": arq, **_resumo(sub)})
    out = pd.DataFrame(rows)

    csv_path = tabelas_dir / "tab1_descritivas_arquetipo.csv"
    out.to_csv(csv_path, index=False, float_format="%.6f")
    logger.info("tab1 escrita: %s", csv_path)

    md_path = tabelas_dir / "tab1_descritivas_arquetipo.md"
    md = ["# Tabela 1 — Descritivas de densidade de dívida por arquétipo",
          "",
          "Densidade = `sqale_index / ncloc` (minutos por linha não-comentada).",
          "",
          out.to_markdown(index=False, floatfmt=".4f"),
          ""]
    md_path.write_text("\n".join(md), encoding="utf-8")
    logger.info("tab1 markdown escrita: %s", md_path)
    return out

def descritivas_subgrupos_descentralizado(df: pd.DataFrame, tabelas_dir: Path,
                                          logger: logging.Logger) -> pd.DataFrame:
    desc = df[df["arquetipo"] == "descentralizado"]
    rows = []
    for inst in sorted(desc["instancia"].dropna().unique()):
        sub = desc[desc["instancia"] == inst]["densidade_divida"]
        rows.append({"instancia": inst, **_resumo(sub)})
    out = pd.DataFrame(rows)

    csv_path = tabelas_dir / "tab2_subgrupos_descentralizado.csv"
    out.to_csv(csv_path, index=False, float_format="%.6f")
    logger.info("tab2 escrita: %s", csv_path)

    n_uber = int(out.loc[out["instancia"] == "uber", "n"].sum()) if (out["instancia"] == "uber").any() else 0
    if n_uber == 2:
        logger.warning("Subgrupo Uber n=2: §3.3 v1.4 declara que não suporta inferência intra-subgrupo")
    if "spotify" not in out["instancia"].values:
        logger.info("Subgrupo Spotify ausente conforme §3.3 v1.4 (n=0)")
    return out

def composicao_amostral(df: pd.DataFrame, logger: logging.Logger) -> pd.DataFrame:
    rows = []
    for arq in ARQUETIPOS_ORDEM:
        sub = df[df["arquetipo"] == arq]
        rows.append({
            "arquetipo": arq,
            "n": len(sub),
            "loc_total_mediana": float(sub["loc_total"].median()),
            "idade_anos_mediana": float(sub["idade_anos"].median()),
            "contribuidores_mediana": float(sub["contribuidores"].median()),
            "loc_total_iqr": float(sub["loc_total"].quantile(0.75) - sub["loc_total"].quantile(0.25)),
            "idade_anos_iqr": float(sub["idade_anos"].quantile(0.75) - sub["idade_anos"].quantile(0.25)),
            "contribuidores_iqr": float(sub["contribuidores"].quantile(0.75) - sub["contribuidores"].quantile(0.25)),
        })
    out = pd.DataFrame(rows)
    logger.info("Composição amostral:\n%s", out.to_string(index=False))
    return out
