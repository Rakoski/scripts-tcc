#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import platform
import random
import sys
from datetime import datetime
from importlib import metadata as importlib_metadata
from pathlib import Path

import numpy as np
import pandas as pd

from analise_lib import io_utils
from analise_lib.confirmatorio import (
    aplicar_regra_decisao,
    brown_forsythe,
    calibrar_f_critico_empirico,
)
from analise_lib.decomposicao_regras import (
    decomposicao_por_tag_arquetipo,
    decomposicao_por_type_arquetipo,
    top10_regras_por_projeto,
)
from analise_lib.descritivas import (
    composicao_amostral,
    descritivas_por_arquetipo,
    descritivas_subgrupos_descentralizado,
)
from analise_lib.exploratorio import (
    icc_descentralizado,
    jonckheere_terpstra,
    kruskal_wallis_eta2,
    robustez_10k_100k,
    spearman_parcial,
)
from analise_lib.tamanho_efeito import cliffs_delta_pares
from analise_lib import visualizacao as viz

SEED = 42
PROTOCOL_VERSION = "1.5"

def parse_args(argv=None):
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--data-dir", required=True, type=Path,
                   help="Diretório com consolidado.csv, issues/, regras_metadata.json, ambiente.txt")
    p.add_argument("--data-coleta", default=None,
                   help="Data da coleta YYYY-MM-DD (default: hoje)")
    return p.parse_args(argv)

def versoes_pacotes():
    pkgs = ["pandas", "numpy", "scipy", "pingouin", "matplotlib", "seaborn"]
    out = {}
    for p in pkgs:
        try:
            out[p] = importlib_metadata.version(p)
        except importlib_metadata.PackageNotFoundError:
            out[p] = "NOT_INSTALLED"
    out["python"] = platform.python_version()
    return out

def _bool(b):
    return "Sim" if b else "Não"

def gerar_relatorio(saida, out_dir):
    rel_path = out_dir / "relatorio.md"
    md = []
    md.append("# Relatório de Análise — TCC Paradoxo da Governança em Escala")
    md.append("")
    md.append(f"**Data da análise:** {saida['data_execucao']}")
    md.append(f"**Versão do protocolo:** {PROTOCOL_VERSION}")
    md.append(f"**Seed:** {SEED}")
    md.append("")
    md.append("**Ambiente:**")
    md.append("```")
    md.append(saida["ambiente_txt"].rstrip())
    md.append("```")
    md.append("")

    md.append("## 1. Composição da amostra")
    md.append("")
    md.append(saida["composicao"].to_markdown(index=False, floatfmt=".2f"))
    md.append("")
    md.append("![composição](figuras/fig4_dist_loc_idade_contribuidores.png)")
    md.append("")
    md.append("Spotify ausente do arquétipo descentralizado conforme §3.3 v1.4.")
    md.append("")

    md.append("## 2. Estatísticas descritivas")
    md.append("")
    md.append(saida["tab1"].to_markdown(index=False, floatfmt=".4f"))
    md.append("")
    md.append("![boxplot](figuras/fig1_boxplot_densidade_arquetipo.png)")
    md.append("")

    md.append("## 3. Análise confirmatória — Regra §8.2 v1.5")
    md.append("")
    rd = saida["regra"]
    md.append(f"- F-crítico empírico: **{rd['F_crit_empirico']:.4f}** (vs teórico {rd['F_crit_teorico']:.4f})")
    md.append(f"- F observado: **{rd['F_obs']:.4f}**")
    md.append(f"- p-valor (referência teórica F): {rd['p_teorico']:.4g}")
    md.append(f"- Variâncias amostrais: Google={rd['var_google']:.4f}, "
              f"Apache={rd['var_apache']:.4f}, Desc={rd['var_desc']:.4f}")
    md.append(f"- C1 (significância): {_bool(rd['C1_satisfeita'])}")
    md.append(f"- C2 (ordem prevista): {_bool(rd['C2_satisfeita'])}")
    md.append(f"- **H1: {'aceita' if rd['H1_aceita'] else 'rejeitada'}**")
    md.append(f"- Interpretação: {rd['interpretacao']}")
    md.append("")

    md.append("## 4. Tamanho de efeito (descritivo)")
    md.append("")
    md.append("Cliff's δ pareado com limiares de Romano et al. (2006). "
              "Não é mais condição da regra de decisão (v1.5).")
    md.append("")
    md.append(saida["tab4"].to_markdown(index=False, floatfmt=".4f"))
    md.append("")

    md.append("## 5. Análises secundárias e exploratórias")
    md.append("")
    kw = saida["tab5"]
    md.append(f"**Kruskal-Wallis (H1', tendência central):** H={kw['H']:.4f}, "
              f"p={kw['p']:.4g}, η²={kw['eta2']:.4f}.")
    md.append("")
    jt = saida["tab6"]
    md.append(f"**Jonckheere-Terpstra (exploratório, ordem prevista):** "
              f"JT={jt['JT']:.2f}, z={jt['z']:.4f}, p_unilat={jt['p_unilateral']:.4g}.")
    md.append("")
    md.append("**Spearman parcial** (descritivo, controlando log_loc, idade_anos, idade_snapshot_dias):")
    md.append("")
    md.append("Ver `tabelas/tab7_spearman_parcial.csv`.")
    md.append("")

    md.append("## 6. Tratamento de confundidores")
    md.append("")
    rob = saida["tab11"]
    if rob.get("abortada"):
        md.append(f"Robustez 10k-100k: **abortada**. Motivo: {rob['motivo']}. "
                  f"Contagens: {rob['contagens']}.")
    else:
        md.append(f"Robustez 10k-100k: n=({rob['n_apache']}/{rob['n_google']}/{rob['n_desc']}), "
                  f"F={rob['F_obs']:.4f}, ordem prevista preservada: {_bool(rob['ordem_observada_match_priori'])}.")
    md.append("")

    md.append("## 7. Decomposição inter-organizacional do descentralizado")
    md.append("")
    md.append("Ver `tabelas/tab2_subgrupos_descentralizado.csv` e "
              "`tabelas/tab8_icc_descentralizado.csv`.")
    md.append("")

    md.append("## 8. Diagnóstico de viés do Quality Profile (A1, A4)")
    md.append("")
    md.append("### 8.1 Decomposição por type")
    md.append("")
    if saida["tab9"].empty:
        md.append("*Decomposição por type indisponível (issues ausentes).*")
    else:
        md.append(saida["tab9"].to_markdown(index=False, floatfmt=".4f"))
    md.append("")
    md.append("### 8.2 Decomposição por tag")
    md.append("")
    if saida["tab9b"].empty:
        md.append("*Decomposição por tag indisponível (regras_metadata ausente).*")
    else:
        md.append("Top tags por arquétipo (proporção média do sqale_index):")
        md.append("")
        tab9b = saida["tab9b"]
        top_tags = (
            tab9b.sort_values("prop_media", ascending=False)
            .groupby("arquetipo")
            .head(10)
            .reset_index(drop=True)
        )
        md.append(top_tags.to_markdown(index=False, floatfmt=".4f"))
    md.append("")
    md.append("Tabela completa em `tabelas/tab9b_decomposicao_tags_por_arquetipo.csv`.")
    md.append("Top-10 regras por projeto: `tabelas/tab10_top10_regras_por_projeto.csv`.")
    md.append("")
    md.append("![decomposição](figuras/fig5_decomposicao_regras.png)")
    md.append("")

    md.append("## 9. Limitações declaradas")
    md.append("")
    md.append("- Poder estatístico aproximadamente 9% para a regra §8.2 v1.5 sob "
              "cenários realistas de razão de variância em SQALE (v1.5 §8).")
    md.append("- Falha em rejeitar H0 NÃO constitui evidência de equivalência entre "
              "arquétipos (§8.2).")
    md.append("- Spotify ausente do arquétipo descentralizado (n=0), Uber n=2.")
    md.append("")

    md.append("## 10. Reprodutibilidade")
    md.append("")
    md.append(f"- Hash do consolidado.csv: `{saida['hash_consolidado']}`")
    md.append(f"- Seed: {SEED}")
    md.append("- Versões de pacotes:")
    md.append("")
    for p, v in saida["versoes"].items():
        md.append(f"  - {p}: `{v}`")
    md.append("")

    rel_path.write_text("\n".join(md), encoding="utf-8")
    return rel_path

def main(argv=None):
    args = parse_args(argv)

    random.seed(SEED)
    np.random.seed(SEED)

    data_dir = args.data_dir.resolve()
    if not data_dir.exists():
        print(f"[ERRO] data_dir não existe: {data_dir}", file=sys.stderr)
        return 2

    out_paths = io_utils.garantir_arvore_saida(data_dir)
    log_path = out_paths["base"] / "execucao.log"
    logger = io_utils.setup_logger(log_path)

    logger.info("=" * 70)
    logger.info("analise_estatistica.py — protocolo v%s — seed=%d", PROTOCOL_VERSION, SEED)
    logger.info("data_dir=%s", data_dir)

    data_coleta = args.data_coleta or datetime.now().strftime("%Y-%m-%d")
    logger.info("data_coleta=%s", data_coleta)

    try:
        df = io_utils.carregar_consolidado(data_dir, logger)
        df = io_utils.calcular_idade_snapshot(df, data_coleta, logger)
        ambiente_txt = io_utils.carregar_ambiente(data_dir, logger)
        regras_meta = io_utils.carregar_regras_metadata(data_dir, logger)
        issues = io_utils.carregar_issues(data_dir, df["id"].tolist(), logger)
    except io_utils.ValidationError as e:
        logger.error("Validação falhou: %s", e)
        return 3

    tabelas_dir = out_paths["tabelas"]
    figuras_dir = out_paths["figuras"]

    composicao = composicao_amostral(df, logger)
    tab1 = descritivas_por_arquetipo(df, tabelas_dir, logger)
    tab2 = descritivas_subgrupos_descentralizado(df, tabelas_dir, logger)

    viz.fig1_boxplot_densidade(df, figuras_dir, logger)
    viz.fig2_subgrupos_descentralizado(df, figuras_dir, logger)
    viz.fig3_scatter_idade_snapshot(df, figuras_dir, logger)
    viz.fig4_composicao_amostral(df, figuras_dir, logger)

    logger.info("Calibrando F-crítico empírico (pode demorar ~10-30s)...")
    calib = calibrar_f_critico_empirico(df, logger, n_reps=10_000, seed=SEED)

    bf = brown_forsythe(df, tabelas_dir, logger)
    regra = aplicar_regra_decisao(bf, calib, tabelas_dir, logger)

    tab4 = cliffs_delta_pares(df, tabelas_dir, logger)

    tab5 = kruskal_wallis_eta2(df, tabelas_dir, logger)
    tab6 = jonckheere_terpstra(df, tabelas_dir, logger)

    tab7 = spearman_parcial(df, tabelas_dir, logger)

    tab8 = icc_descentralizado(df, tabelas_dir, logger)

    tab9 = decomposicao_por_type_arquetipo(df, issues, tabelas_dir, logger)
    tab9b = decomposicao_por_tag_arquetipo(df, issues, regras_meta, tabelas_dir, logger)
    viz.fig5_decomposicao_regras(df, tab9, figuras_dir, logger)

    tab10 = top10_regras_por_projeto(df, issues, regras_meta, tabelas_dir, logger)

    tab11 = robustez_10k_100k(df, calib, tabelas_dir, logger)

    saida = {
        "data_execucao": io_utils.now_iso(),
        "ambiente_txt": ambiente_txt,
        "composicao": composicao,
        "tab1": tab1, "tab2": tab2, "tab4": tab4,
        "tab5": tab5, "tab6": tab6, "tab7": tab7,
        "tab8": tab8, "tab9": tab9, "tab9b": tab9b, "tab10": tab10,
        "tab11": tab11,
        "regra": regra,
        "hash_consolidado": io_utils.hash_arquivo(data_dir / "consolidado.csv"),
        "versoes": versoes_pacotes(),
    }
    rel = gerar_relatorio(saida, out_paths["base"])
    logger.info("Relatório gerado: %s", rel)

    return 0

if __name__ == "__main__":
    sys.exit(main())
