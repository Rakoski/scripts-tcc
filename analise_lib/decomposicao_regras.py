from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd

from .descritivas import ARQUETIPOS_ORDEM

def decomposicao_por_tag_arquetipo(df, issues, regras_meta, tabelas_dir, logger):
    if not issues or not regras_meta:
        logger.warning("Sem issues ou regras_meta — A1 (decomposição por tag) pulada")
        return pd.DataFrame()
    
    tag_rows = []
    for pid, dfi in issues.items():
        proj = df.loc[df["id"] == pid]
        if proj.empty:
            continue
        sqale = float(proj["sqale_index"].iloc[0])
        arq = proj["arquetipo"].iloc[0]
        
        effort_por_tag = {}
        for _, issue in dfi.iterrows():
            rule = issue["rule"]
            effort = issue["effort_min"]
            tags = regras_meta.get(rule, {}).get("tags", [])
            for tag in tags:
                effort_por_tag[tag] = effort_por_tag.get(tag, 0) + effort
        
        for tag, eff in effort_por_tag.items():
            tag_rows.append({
                "id": pid,
                "arquetipo": arq,
                "tag": tag,
                "effort": eff,
                "prop": eff / sqale if sqale else 0,
            })
    
    proj_df = pd.DataFrame(tag_rows)
    
    agg = proj_df.groupby(["arquetipo", "tag"]).agg(
        n_projetos=("id", "nunique"),
        prop_media=("prop", "mean"),
        prop_std=("prop", "std"),
    ).reset_index()
    
    csv_path = tabelas_dir / "tab9b_decomposicao_tags_por_arquetipo.csv"
    agg.to_csv(csv_path, index=False, float_format="%.6f")
    logger.info("tab9b escrita (decomposição por tag): %s", csv_path)
    return agg

def decomposicao_por_type_arquetipo(df: pd.DataFrame,
                                    issues: dict[str, pd.DataFrame],
                                    tabelas_dir: Path,
                                    logger: logging.Logger) -> pd.DataFrame:
    if not issues:
        logger.warning("Sem issues — A1 (decomposição por type) pulada")
        return pd.DataFrame()

    rows = []
    for pid, dfi in issues.items():
        proj = df.loc[df["id"] == pid]
        if proj.empty:
            logger.warning("Issues para id=%s sem linha em consolidado.csv", pid)
            continue
        sqale = float(proj["sqale_index"].iloc[0])
        arq = proj["arquetipo"].iloc[0]
        eff_by_type = dfi.groupby("type")["effort_min"].sum().to_dict()
        rows.append({
            "id": pid,
            "arquetipo": arq,
            "sqale_index": sqale,
            "effort_smell": eff_by_type.get("CODE_SMELL", 0),
            "effort_bug": eff_by_type.get("BUG", 0),
            "effort_vuln": eff_by_type.get("VULNERABILITY", 0),
        })
    proj_df = pd.DataFrame(rows)
    if proj_df.empty:
        logger.warning("Nenhum projeto cruzado entre issues e consolidado")
        return proj_df

    proj_df["prop_smell"] = proj_df["effort_smell"] / proj_df["sqale_index"]
    proj_df["prop_bug"] = proj_df["effort_bug"] / proj_df["sqale_index"]
    proj_df["prop_vuln"] = proj_df["effort_vuln"] / proj_df["sqale_index"]

    agg_rows = []
    for arq in ARQUETIPOS_ORDEM:
        sub = proj_df[proj_df["arquetipo"] == arq]
        if sub.empty:
            continue
        agg_rows.append({
            "arquetipo": arq,
            "n_projetos": len(sub),
            "prop_smell_media": float(sub["prop_smell"].mean()),
            "prop_smell_std": float(sub["prop_smell"].std(ddof=1)) if len(sub) > 1 else float("nan"),
            "prop_bug_media": float(sub["prop_bug"].mean()),
            "prop_bug_std": float(sub["prop_bug"].std(ddof=1)) if len(sub) > 1 else float("nan"),
            "prop_vuln_media": float(sub["prop_vuln"].mean()),
            "prop_vuln_std": float(sub["prop_vuln"].std(ddof=1)) if len(sub) > 1 else float("nan"),
        })
    out = pd.DataFrame(agg_rows)
    csv_path = tabelas_dir / "tab9_decomposicao_regras_por_arquetipo.csv"
    out.to_csv(csv_path, index=False, float_format="%.6f")
    logger.info("tab9 escrita: %s", csv_path)
    return out

def top10_regras_por_projeto(df: pd.DataFrame,
                             issues: dict[str, pd.DataFrame],
                             regras_meta: dict[str, dict],
                             tabelas_dir: Path,
                             logger: logging.Logger) -> pd.DataFrame:
    if not issues:
        logger.warning("Sem issues — A4 (top-10 regras) pulada")
        return pd.DataFrame()

    rows = []
    for pid, dfi in issues.items():
        proj = df.loc[df["id"] == pid]
        if proj.empty:
            continue
        sqale = float(proj["sqale_index"].iloc[0])
        agg = dfi.groupby("rule")["effort_min"].sum().reset_index()
        agg = agg.sort_values("effort_min", ascending=False).head(10)
        for posicao, (_, row) in enumerate(agg.iterrows(), start=1):
            rk = row["rule"]
            meta = regras_meta.get(rk, {})
            rows.append({
                "projeto": pid,
                "posicao": posicao,
                "rule_key": rk,
                "rule_name": meta.get("name", ""),
                "type": meta.get("type", ""),
                "tags": ",".join(meta.get("tags", [])) if isinstance(meta.get("tags"), list) else "",
                "effort_total": int(row["effort_min"]),
                "prop_do_sqale_index": float(row["effort_min"]) / sqale if sqale else float("nan"),
            })
    out = pd.DataFrame(rows)
    csv_path = tabelas_dir / "tab10_top10_regras_por_projeto.csv"
    out.to_csv(csv_path, index=False, float_format="%.6f")
    logger.info("tab10 escrita: %s (%d linhas)", csv_path, len(out))
    return out
