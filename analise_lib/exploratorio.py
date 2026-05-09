"""Procedimentos 5-6 do §8 (KW + JT) e §8.1 (Spearman parcial, ICC, robustez)."""
from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from .descritivas import ARQUETIPOS_ORDEM
from .tamanho_efeito import cliffs_delta_pares


def kruskal_wallis_eta2(df: pd.DataFrame, tabelas_dir: Path,
                        logger: logging.Logger) -> dict:
    grupos = [df.loc[df["arquetipo"] == a, "densidade_divida"].values
              for a in ARQUETIPOS_ORDEM]
    H, p = stats.kruskal(*grupos)
    n_total = sum(len(g) for g in grupos)
    eta2 = (H - 2) / (n_total - 3) if n_total > 3 else float("nan")
    out = {
        "H": float(H),
        "p": float(p),
        "eta2": float(eta2),
        "n_total": int(n_total),
        "df": 2,
        "status": "secundário (H1' — tendência central)",
    }
    pd.DataFrame([out]).to_csv(
        tabelas_dir / "tab5_kruskal_wallis.csv",
        index=False, float_format="%.6f",
    )
    logger.info("tab5 escrita: KW H=%.4f, p=%.4g, η²=%.4f", H, p, eta2)
    return out


def jonckheere_terpstra(df: pd.DataFrame, tabelas_dir: Path,
                        logger: logging.Logger) -> dict:
    """Implementação manual: ordem prevista google ≤ apache ≤ desc.
    Estatística JT = Σ_{i<j} U(X_i, X_j) onde U é o número de pares
    onde X_j > X_i. Aprox. normal com correção para ties."""
    ordem = ["google", "apache", "descentralizado"]
    grupos = [df.loc[df["arquetipo"] == a, "densidade_divida"].values
              for a in ordem]
    ns = [len(g) for g in grupos]
    n_total = sum(ns)

    JT = 0.0
    for i in range(len(grupos)):
        for j in range(i + 1, len(grupos)):
            xi = grupos[i].reshape(-1, 1)
            xj = grupos[j].reshape(1, -1)
            JT += float(((xj > xi).sum()) + 0.5 * ((xj == xi).sum()))

    mu_jt = (n_total ** 2 - sum(n * n for n in ns)) / 4.0

    var_jt = (n_total ** 2 * (2 * n_total + 3)
              - sum(n * n * (2 * n + 3) for n in ns)) / 72.0
    
    z = (JT - mu_jt) / np.sqrt(var_jt) if var_jt > 0 else float("nan")

    p_unilateral = 1 - stats.norm.cdf(z) if not np.isnan(z) else float("nan")

    n_ties = sum(((grupos[i].reshape(-1, 1) == grupos[j].reshape(1, -1)).sum())
             for i in range(len(grupos)) for j in range(i+1, len(grupos)))
    if n_ties > 0:
        logger.warning(
            "Jonckheere-Terpstra: %d empates detectados; variância sob H0 "
            "não corrigida para empates. P-valor pode ser conservador.",
            n_ties
        )

    out = {
        "JT": JT,
        "mu_jt_H0": float(mu_jt),
        "var_jt_H0": float(var_jt),
        "z": float(z),
        "p_unilateral": float(p_unilateral),
        "ordem_testada": "google ≤ apache ≤ descentralizado",
        "status": "exploratório (§2 v1.3 rebaixou de confirmatório)",
    }
    pd.DataFrame([out]).to_csv(
        tabelas_dir / "tab6_jonckheere_terpstra.csv",
        index=False, float_format="%.6f",
    )
    logger.info("tab6 escrita: JT=%.4f, z=%.4f, p_unilat=%.4g", JT, z, p_unilateral)
    return out


def spearman_parcial(df: pd.DataFrame, tabelas_dir: Path,
                     logger: logging.Logger) -> dict:
    import pingouin as pg
    sub = df[["arquetipo_ordinal", "densidade_divida",
              "log_loc", "idade_anos", "idade_snapshot_dias"]].dropna()
    
    if len(sub) < 10:
        logger.warning("Spearman parcial: n=%d após dropna, resultado pode ser instável", len(sub))
    
    res = pg.partial_corr(
        data=sub,
        x="arquetipo_ordinal",
        y="densidade_divida",
        covar=["log_loc", "idade_anos", "idade_snapshot_dias"],
        method="spearman",
    )
    csv_path = tabelas_dir / "tab7_spearman_parcial.csv"
    res.to_csv(csv_path, index=False, float_format="%.6f")
    
    if not res.empty:
        row = res.iloc[0]
        r_value = float(row['r']) if 'r' in row.index else float('nan')
        p_col = next((c for c in ['p-val', 'p_val', 'p-value'] if c in row.index), None)
        p_value = float(row[p_col]) if p_col else float('nan')
        logger.info("Spearman parcial: r=%.4f, p=%.4g (controlando log_loc, idade_anos, idade_snapshot_dias)", 
                    r_value, p_value)
    else:
        logger.warning("Spearman parcial: resultado vazio")
    
    return res.to_dict(orient="records")[0] if not res.empty else {}


def icc_descentralizado(df: pd.DataFrame, tabelas_dir: Path,
                        logger: logging.Logger) -> pd.DataFrame:
    import pingouin as pg
    desc = df[df["arquetipo"] == "descentralizado"].copy()
    contagens = desc["instancia"].value_counts()
    logger.info("Subgrupos descentralizado: %s", contagens.to_dict())

    if (contagens < 2).any() or len(contagens) < 2:
        logger.warning("ICC: subgrupo(s) com n<2 ou apenas 1 instância — "
                       "ICC indefinido, salvando placeholder")
        out = pd.DataFrame([{
            "type": "indefinido",
            "motivo": "subgrupo com n<2 ou apenas 1 instância",
            "subgrupos": str(contagens.to_dict()),
        }])
        out.to_csv(tabelas_dir / "tab8_icc_descentralizado.csv", index=False)
        return out

    try:
        icc = pg.intraclass_corr(
            data=desc,
            targets="id",
            raters="instancia",
            ratings="densidade_divida",
        )
    except Exception as e:
        logger.error("ICC falhou: %s — salvando placeholder", e)
        out = pd.DataFrame([{
            "type": "erro",
            "motivo": f"{type(e).__name__}: {e}",
        }])
        out.to_csv(tabelas_dir / "tab8_icc_descentralizado.csv", index=False)
        return out

    csv_path = tabelas_dir / "tab8_icc_descentralizado.csv"
    icc.to_csv(csv_path, index=False, float_format="%.6f")
    logger.info("tab8 escrita: ICC descentralizado calculado")
    return icc


def robustez_10k_100k(df: pd.DataFrame, calib: dict, tabelas_dir: Path,
                     logger: logging.Logger) -> dict:
    sub = df[(df["ncloc"] >= 10_000) & (df["ncloc"] <= 100_000)]
    contagens = {a: int((sub["arquetipo"] == a).sum()) for a in ARQUETIPOS_ORDEM}

    if any(v < 5 for v in contagens.values()):
        logger.warning("Robustez 10k-100k abortada: n_efetivo < 5 em algum arquétipo. Contagens: %s", contagens)
        out = {
            "abortada": True,
            "motivo": "n_efetivo < 5 em algum arquétipo",
            "contagens": str(contagens),
        }
        pd.DataFrame([out]).to_csv(
            tabelas_dir / "tab11_robustez_10k_100k.csv", index=False
        )
        return out

    g_apache = sub.loc[sub["arquetipo"] == "apache", "densidade_divida"].values
    g_google = sub.loc[sub["arquetipo"] == "google", "densidade_divida"].values
    g_desc = sub.loc[sub["arquetipo"] == "descentralizado", "densidade_divida"].values

    F_obs, p_teorico = stats.levene(g_apache, g_google, g_desc, center="median")
    var_a = float(np.var(g_apache, ddof=1))
    var_g = float(np.var(g_google, ddof=1))
    var_d = float(np.var(g_desc, ddof=1))

    out = {
        "abortada": False,
        "n_apache": contagens["apache"],
        "n_google": contagens["google"],
        "n_desc": contagens["descentralizado"],
        "F_obs_subamostra": float(F_obs),
        "p_teorico_F_referencia": float(p_teorico),
        "var_apache": var_a,
        "var_google": var_g,
        "var_desc": var_d,
        "ordem_observada_match_priori": (var_g < var_a) and (var_a < var_d),
        "nota_metodologica": (
            "Análise descritiva (§8.1 #3 v1.4). F-crítico não recalculado "
            "para sub-amostra. Comparação com amostra completa é apenas "
            "direcional, não inferencial."
        ),  
    }
    pd.DataFrame([out]).to_csv(
        tabelas_dir / "tab11_robustez_10k_100k.csv",
        index=False, float_format="%.6f",
    )
    logger.info("tab11 escrita: robustez 10k-100k, n=%s, F=%.4f", contagens, F_obs)
    return out
