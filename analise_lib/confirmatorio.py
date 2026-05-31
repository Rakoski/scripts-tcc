from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

N_REPS_NULL = 10_000
ALPHA = 0.05

def calibrar_f_critico_empirico(df: pd.DataFrame, logger: logging.Logger,
                                n_reps: int = N_REPS_NULL,
                                seed: int = 42) -> dict:
    rng = np.random.default_rng(seed)

    densidade = df["densidade_divida"].values
    if (densidade <= 0).any():
        raise ValueError("densidade_divida tem valores não-positivos; "
                         "lognormal.fit indefinido")

    shape, loc, scale = stats.lognorm.fit(densidade, floc=0)
    sigma_obs = float(shape)
    mu_obs = float(np.log(scale))
    logger.info("Lognormal ajustada à densidade observada: μ=%.4f, σ=%.4f",
                mu_obs, sigma_obs)
    
    ks_fit_stat, ks_fit_p = stats.kstest(
        densidade,
        lambda x: stats.lognorm.cdf(x, shape, loc=loc, scale=scale)
    )
    
    logger.info("Ajuste lognormal: KS stat=%.4f, p=%.4g", ks_fit_stat, ks_fit_p)
    if ks_fit_p < 0.05:
        logger.warning(
            "Ajuste lognormal rejeitado pelo KS — calibração de F-crítico "
            "pode estar mal-especificada. Considerar bootstrap não-paramétrico "
            "como alternativa."
        )

    counts = df["arquetipo"].value_counts().to_dict()
    n_apache = counts.get("apache", 0)
    n_google = counts.get("google", 0)
    n_desc = counts.get("descentralizado", 0)
    n_total = n_apache + n_google + n_desc

    F_null = np.empty(n_reps)
    for i in range(n_reps):
        ga = rng.lognormal(mean=mu_obs, sigma=sigma_obs, size=n_apache)
        gg = rng.lognormal(mean=mu_obs, sigma=sigma_obs, size=n_google)
        gd = rng.lognormal(mean=mu_obs, sigma=sigma_obs, size=n_desc)
        F, _ = stats.levene(ga, gg, gd, center="median")
        F_null[i] = F

    F_crit_emp = float(np.percentile(F_null, (1 - ALPHA) * 100))
    F_crit_theo = float(stats.f.ppf(1 - ALPHA, 2, n_total - 3))
    desvio = (F_crit_emp / F_crit_theo - 1) * 100.0

    ks_stat, ks_p = stats.kstest(F_null, lambda x: stats.f.cdf(x, 2, n_total - 3))

    logger.info("F-crítico empírico (p95) = %.4f", F_crit_emp)
    logger.info("F-crítico teórico F(2, %d, 0.95) = %.4f", n_total - 3, F_crit_theo)
    logger.info("Desvio relativo emp/teo = %+.2f%%", desvio)
    logger.info("KS-test contra F(2, %d): stat=%.4f, p=%.4g",
                n_total - 3, ks_stat, ks_p)
    if ks_p < 0.05:
        logger.info("KS rejeita compatibilidade com F teórica — usar F-crítico empírico (exigência §8 v1.5)")

    return {
        "F_crit_empirico": F_crit_emp,
        "F_crit_teorico": F_crit_theo,
        "desvio_relativo_pct": desvio,
        "ks_stat": float(ks_stat),
        "ks_p": float(ks_p),
        "n_apache": n_apache,
        "n_google": n_google,
        "n_desc": n_desc,
        "n_total": n_total,
        "lognormal_mu_obs": mu_obs,
        "lognormal_sigma_obs": sigma_obs,
        "n_reps": n_reps,
    }

def brown_forsythe(df: pd.DataFrame, tabelas_dir: Path,
                   logger: logging.Logger) -> dict:
    g_apache = df.loc[df["arquetipo"] == "apache", "densidade_divida"].values
    g_google = df.loc[df["arquetipo"] == "google", "densidade_divida"].values
    g_desc = df.loc[df["arquetipo"] == "descentralizado", "densidade_divida"].values

    F_obs, p_teorico = stats.levene(g_apache, g_google, g_desc, center="median")

    var_apache = float(np.var(g_apache, ddof=1))
    var_google = float(np.var(g_google, ddof=1))
    var_desc = float(np.var(g_desc, ddof=1))

    out = {
        "F_obs": float(F_obs),
        "p_teorico": float(p_teorico),
        "var_apache": var_apache,
        "var_google": var_google,
        "var_desc": var_desc,
    }
    pd.DataFrame([out]).to_csv(
        tabelas_dir / "tab3_brown_forsythe.csv",
        index=False, float_format="%.6f",
    )
    logger.info("tab3 escrita")
    return out

def aplicar_regra_decisao(bf: dict, calib: dict, tabelas_dir: Path,
                          logger: logging.Logger) -> dict:
    F_obs = bf["F_obs"]
    F_crit_emp = calib["F_crit_empirico"]
    F_crit_theo = calib["F_crit_teorico"]
    p_teorico = bf["p_teorico"]

    var_a = bf["var_apache"]
    var_g = bf["var_google"]
    var_d = bf["var_desc"]

    c1 = F_obs > F_crit_emp
    c2 = (var_g < var_a) and (var_a < var_d)
    h1_aceita = bool(c1 and c2)

    if h1_aceita:
        interp = ("Evidência forte para H1, dado o poder limitado: "
                  "variâncias diferem na ordem prevista "
                  "(Google < Apache < Descentralizado).")
    elif c1 and not c2:
        interp = ("Variâncias diferem mas não na ordem prevista — "
                  "evidência contra H1. Discutir mecanismo causal "
                  "alternativo em §5 do TCC.")
    else:
        interp = ("Falha em detectar diferença de variâncias. "
                  "Sob poder de ~9% (v1.5), NÃO constitui evidência "
                  "de equivalência entre arquétipos.")

    out = {
        "F_obs": F_obs,
        "F_crit_empirico": F_crit_emp,
        "F_crit_teorico": F_crit_theo,
        "p_teorico": p_teorico,
        "var_apache": var_a,
        "var_google": var_g,
        "var_desc": var_d,
        "C1_satisfeita": bool(c1),
        "C2_satisfeita": bool(c2),
        "H1_aceita": h1_aceita,
        "interpretacao": interp,
    }
    pd.DataFrame([out]).to_csv(
        tabelas_dir / "regra_decisao_h1.csv",
        index=False, float_format="%.6f",
    )
    logger.info("Regra §8.2 v1.5: C1=%s, C2=%s, H1_aceita=%s",
                c1, c2, h1_aceita)
    logger.info("Interpretação: %s", interp)
    return out
