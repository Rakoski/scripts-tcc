from __future__ import annotations

import logging
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from .descritivas import ARQUETIPOS_ORDEM

PALETTE = {"google": "#4285F4", "apache": "#D22128", "descentralizado": "#888888"}
DPI = 300

def _save(fig, path: Path, logger: logging.Logger):
    fig.tight_layout()
    fig.savefig(path, dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    logger.info("Figura salva: %s", path)

def fig1_boxplot_densidade(df: pd.DataFrame, figuras_dir: Path,
                           logger: logging.Logger):
    fig, ax = plt.subplots(figsize=(7, 5))
    sns.boxplot(
        data=df, x="arquetipo", y="densidade_divida",
        order=ARQUETIPOS_ORDEM, palette=PALETTE, ax=ax,
        showfliers=False,
    )
    sns.stripplot(
        data=df, x="arquetipo", y="densidade_divida",
        order=ARQUETIPOS_ORDEM, jitter=0.1, color="black",
        size=4, alpha=0.6, ax=ax,
    )
    ax.set_xlabel("Arquétipo de governança")
    ax.set_ylabel("Densidade de dívida (min / linha não-comentada)")
    ax.set_title("Distribuição da densidade de dívida por arquétipo")
    _save(fig, figuras_dir / "fig1_boxplot_densidade_arquetipo.png", logger)

def fig2_subgrupos_descentralizado(df: pd.DataFrame, figuras_dir: Path,
                                   logger: logging.Logger):
    desc = df[df["arquetipo"] == "descentralizado"]
    fig, ax = plt.subplots(figsize=(7, 5))
    if desc.empty:
        ax.text(0.5, 0.5, "Sem projetos descentralizados", ha="center", va="center")
        _save(fig, figuras_dir / "fig2_boxplot_subgrupos_descentralizado.png", logger)
        return
    ordem = sorted(desc["instancia"].dropna().unique())
    sns.boxplot(data=desc, x="instancia", y="densidade_divida",
                order=ordem, ax=ax, showfliers=False)
    sns.stripplot(data=desc, x="instancia", y="densidade_divida",
                  order=ordem, jitter=0.1, color="black", size=4, alpha=0.6, ax=ax)
    ax.set_xlabel("Organização (subgrupo)")
    ax.set_ylabel("Densidade de dívida")
    ax.set_title("Descentralizado — densidade de dívida por organização\n"
                 "(Spotify ausente conforme §3.3 v1.4)")
    _save(fig, figuras_dir / "fig2_boxplot_subgrupos_descentralizado.png", logger)

def fig3_scatter_idade_snapshot(df: pd.DataFrame, figuras_dir: Path,
                                logger: logging.Logger):
    fig, ax = plt.subplots(figsize=(8, 5))
    for arq in ARQUETIPOS_ORDEM:
        sub = df[df["arquetipo"] == arq]
        ax.scatter(sub["idade_snapshot_dias"], sub["densidade_divida"],
                   c=PALETTE[arq], label=arq, alpha=0.7, s=40)
        if len(sub) >= 2:
            try:
                z = np.polyfit(sub["idade_snapshot_dias"], sub["densidade_divida"], 1)
                xs = np.linspace(sub["idade_snapshot_dias"].min(),
                                 sub["idade_snapshot_dias"].max(), 50)
                ax.plot(xs, np.polyval(z, xs), c=PALETTE[arq], alpha=0.4, lw=1)
            except Exception:
                pass
    ax.set_xlabel("Idade do snapshot (dias até a coleta)")
    ax.set_ylabel("Densidade de dívida")
    ax.set_title("Densidade × idade do snapshot — diagnóstico §8.1 / B1")
    ax.legend(title="Arquétipo")
    _save(fig, figuras_dir / "fig3_scatter_densidade_vs_idade_snapshot.png", logger)

def fig4_composicao_amostral(df: pd.DataFrame, figuras_dir: Path,
                             logger: logging.Logger):
    fig, axes = plt.subplots(1, 3, figsize=(13, 4))
    cfgs = [
        ("loc_total", "loc_total"),
        ("idade_anos", "idade_anos"),
        ("contribuidores", "contribuidores"),
    ]
    for ax, (col, _) in zip(axes, cfgs):
        sns.boxplot(data=df, x="arquetipo", y=col, order=ARQUETIPOS_ORDEM,
                    palette=PALETTE, ax=ax, showfliers=False)
        ax.set_title(col)
        ax.set_xlabel("")
    fig.suptitle("Composição amostral por arquétipo (§8.1 #1)")
    _save(fig, figuras_dir / "fig4_dist_loc_idade_contribuidores.png", logger)

def fig5_decomposicao_regras(df: pd.DataFrame,
                             tab9: pd.DataFrame,
                             figuras_dir: Path,
                             logger: logging.Logger):
    fig, ax = plt.subplots(figsize=(7, 5))
    if tab9.empty:
        ax.text(0.5, 0.5, "Decomposição indisponível (sem issues)",
                ha="center", va="center")
        _save(fig, figuras_dir / "fig5_decomposicao_regras.png", logger)
        return
    pivot = tab9.set_index("arquetipo")[
        ["prop_smell_media", "prop_bug_media", "prop_vuln_media"]
    ]
    pivot = pivot.reindex([a for a in ARQUETIPOS_ORDEM if a in pivot.index])
    pivot.columns = ["smell", "bug", "vulnerability"]
    pivot.plot(kind="bar", stacked=True, ax=ax,
               color=["#888", "#D22128", "#FFC107"])
    ax.set_xlabel("Arquétipo")
    ax.set_ylabel("Proporção média do sqale_index (effort)")
    ax.set_title("Decomposição do sqale_index por type — A1 (§8 v1.4)")
    plt.xticks(rotation=0)
    _save(fig, figuras_dir / "fig5_decomposicao_regras.png", logger)
