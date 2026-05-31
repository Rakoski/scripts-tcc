#!/usr/bin/env python3

import csv
import random
import numpy as np
from scipy import stats

from coleta_lib.io_utils import get_scripts_dir

random.seed(42)
np.random.seed(42)

MU = 2.5
N_APACHE = 14
N_GOOGLE = 11
N_DESC = 10
N_TOTAL = N_APACHE + N_GOOGLE + N_DESC
N_REPS = 10_000
ALPHA = 0.05
DELTA_LARGE = 0.474

OUTPUT_CSV = get_scripts_dir() / "simulacao_poder_v14.csv"

SCENARIOS = [
    ("Nulo (H0)", 0.6,  0.6,  0.6),
    ("Pequeno",   0.78, 0.6,  1.02),
    ("Moderado",  1.02, 0.6,  1.5),
    ("Grande",    1.5,  0.6,  2.4),
]

def gen_lognorm(sigma, n):
    return np.random.lognormal(mean=MU, sigma=sigma, size=n)

def cliffs_delta(x, y):
    nx, ny = len(x), len(y)
    x_arr = np.asarray(x).reshape(-1, 1)
    y_arr = np.asarray(y).reshape(1, -1)
    diff = x_arr - y_arr
    return ((diff > 0).sum() - (diff < 0).sum()) / (nx * ny)

def main():
    print("=" * 72)
    print("Simulação Monte Carlo — regra v1.4 §8.2")
    print(f"n = {N_APACHE} (Apache) + {N_GOOGLE} (Google) + {N_DESC} (Desc) = {N_TOTAL}")
    print(f"Réplicas por cenário: {N_REPS}")
    print(f"α = {ALPHA}, |δ| grande = {DELTA_LARGE}")
    print(f"Seed: 42")
    print("=" * 72)

    print("\n[1] Calibrando F-crítico empírico sob H0 (σ=0.6 para os três)...")
    F_null = np.empty(N_REPS)
    for i in range(N_REPS):
        ga = gen_lognorm(0.6, N_APACHE)
        gg = gen_lognorm(0.6, N_GOOGLE)
        gd = gen_lognorm(0.6, N_DESC)
        F, _ = stats.levene(ga, gg, gd, center='median')
        F_null[i] = F

    F_crit_emp = float(np.percentile(F_null, (1 - ALPHA) * 100))
    F_crit_theo = float(stats.f.ppf(1 - ALPHA, 2, N_TOTAL - 3))

    print(f"  F_crit empírico (p95):              {F_crit_emp:.4f}")
    print(f"  F_crit teórico F(2, {N_TOTAL-3}, 0.95):     {F_crit_theo:.4f}")
    print(f"  desvio relativo:                    {(F_crit_emp/F_crit_theo - 1)*100:+.2f}%")

    ks_stat, ks_p = stats.kstest(F_null, lambda x: stats.f.cdf(x, 2, N_TOTAL - 3))
    print(f"\n[2] Diagnóstico: F sob H0 ~ F(2, {N_TOTAL-3})?")
    print(f"  KS statistic: {ks_stat:.4f}   KS p-valor: {ks_p:.4g}")
    if ks_p < 0.05:
        print(f"  → REJEITA compatibilidade com F teórica (p < 0.05).")
        print(f"    Lognormal + Brown-Forsythe a esse n produz cauda diferente.")
        print(f"    USE F_crit_empírico nas comparações.")
    else:
        print(f"  → não rejeita compatibilidade (p ≥ 0.05).")

    print("\n[3] Rodando cenários (10k réplicas cada):")
    results = []
    for name, s_apache, s_google, s_desc in SCENARIOS:
        print(f"  • {name:<14} σ=({s_apache}, {s_google}, {s_desc})...", end=" ", flush=True)

        c1 = np.zeros(N_REPS, dtype=bool)
        c2 = np.zeros(N_REPS, dtype=bool)
        c3 = np.zeros(N_REPS, dtype=bool)

        for i in range(N_REPS):
            ga = gen_lognorm(s_apache, N_APACHE)
            gg = gen_lognorm(s_google, N_GOOGLE)
            gd = gen_lognorm(s_desc, N_DESC)

            F, _ = stats.levene(ga, gg, gd, center='median')
            c1[i] = F > F_crit_emp

            var_a = np.var(ga, ddof=1)
            var_g = np.var(gg, ddof=1)
            var_d = np.var(gd, ddof=1)
            c2[i] = (var_g < var_a) and (var_a < var_d)

            d_ga = cliffs_delta(gg, ga)
            d_ad = cliffs_delta(ga, gd)
            d_gd = cliffs_delta(gg, gd)
            c3[i] = max(abs(d_ga), abs(d_ad), abs(d_gd)) >= DELTA_LARGE

        p_c1 = float(c1.mean())
        p_c2 = float(c2.mean())
        p_c3 = float(c3.mean())
        p_conj = float((c1 & c2 & c3).mean())
        type_I = p_conj if "Nulo" in name else None

        print(f"P(C1)={p_c1:.4f}  P(C2)={p_c2:.4f}  P(C3)={p_c3:.4f}  P(conj)={p_conj:.4f}")

        results.append({
            "scenario": name,
            "sigma_apache": s_apache,
            "sigma_google": s_google,
            "sigma_desc": s_desc,
            "P_C1": round(p_c1, 4),
            "P_C2": round(p_c2, 4),
            "P_C3": round(p_c3, 4),
            "P_conjunctive": round(p_conj, 4),
            "type_I_error": round(type_I, 4) if type_I is not None else "",
        })

    print("\n[4] Tabela final:")
    cols = ["scenario", "sigma_apache", "sigma_google", "sigma_desc",
            "P_C1", "P_C2", "P_C3", "P_conjunctive", "type_I_error"]
    widths = [14, 12, 12, 10, 8, 8, 8, 14, 12]
    line = " | ".join(f"{c:<{w}}" for c, w in zip(cols, widths))
    print(line)
    print("-" * len(line))
    for r in results:
        print(" | ".join(f"{str(r[c]):<{w}}" for c, w in zip(cols, widths)))

    with open(OUTPUT_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in results:
            w.writerow(r)
    print(f"\n[5] CSV salvo em: {OUTPUT_CSV}")

    print("\n[6] Validação (sob nulo):")
    nulo = next(r for r in results if "Nulo" in r["scenario"])
    checks = [
        ("P(C1) ≈ 0.05",       nulo["P_C1"],          0.04, 0.06),
        ("P(C2) ≈ 0.167",      nulo["P_C2"],          0.12, 0.21),
        ("P(C3) baixo",        nulo["P_C3"],          0.0,  0.25),
        ("P(conj) próx. 0",    nulo["P_conjunctive"], 0.0,  0.02),
    ]
    all_ok = True
    for desc, val, lo, hi in checks:
        ok = lo <= val <= hi
        all_ok &= ok
        print(f"  {'✓' if ok else '✗'} {desc:<22} obs = {val:.4f}  esperado ∈ [{lo}, {hi}]")
    if not all_ok:
        print("  ⚠ Algum check falhou — investigar.")
    else:
        print("  Todos os checks passam.")

if __name__ == "__main__":
    main()
