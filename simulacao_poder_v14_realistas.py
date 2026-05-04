#!/usr/bin/env python3
"""
Simulação Monte Carlo — cenários realistas para SQALE.
Estende simulacao_poder_v14.py com razões de variância fisicamente
plausíveis (2x a 10x), em vez de >100x dos cenários originais.

Mesma calibração (seed=42, lognormal μ=2.5, n=14/11/10, 10000 réplicas).
Reporta P(C1), P(C2), P(C3), P(C1∧C2), P(C1∧C2∧C3) para cada cenário.
"""

import csv
import random
import numpy as np
from scipy import stats

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

OUTPUT_CSV = "/home/mateus/Documentos/artigos-tcc/repos/tcc/scripts-tcc/simulacao_poder_v14_realistas.csv"

# (name, sigma_apache, sigma_google, sigma_desc) — razões realistas
# σ_desc²/σ_google² mostra a razão de variâncias σ² (não de σ)
SCENARIOS = [
    ("Realista_pequeno",  0.7,  0.6, 0.8),    # razão var: 1.36 / 1.78
    ("Realista_moderado", 0.75, 0.6, 0.95),   # razão var: 1.56 / 2.51
    ("Realista_grande",   0.85, 0.6, 1.1),    # razão var: 2.01 / 3.36
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
    print("Simulação Monte Carlo — cenários realistas (v1.4 §8.2)")
    print(f"n = {N_APACHE} (Apache) + {N_GOOGLE} (Google) + {N_DESC} (Desc) = {N_TOTAL}")
    print(f"Réplicas por cenário: {N_REPS}, seed=42")
    print("=" * 72)

    # === Calibração (mesma seed, mesma F_crit_emp do script original) ===
    print("\n[1] Calibrando F-crítico empírico sob H0 (σ=0.6 para os três)...")
    F_null = np.empty(N_REPS)
    for i in range(N_REPS):
        ga = gen_lognorm(0.6, N_APACHE)
        gg = gen_lognorm(0.6, N_GOOGLE)
        gd = gen_lognorm(0.6, N_DESC)
        F, _ = stats.levene(ga, gg, gd, center='median')
        F_null[i] = F
    F_crit_emp = float(np.percentile(F_null, (1 - ALPHA) * 100))
    print(f"  F_crit empírico: {F_crit_emp:.4f} (idêntico ao script original)")

    # === Loop sobre cenários ===
    print("\n[2] Rodando cenários realistas:")
    results = []
    for name, s_apache, s_google, s_desc in SCENARIOS:
        # razão de variâncias σ² (mais interpretável que σ em SQALE)
        var_ratio_apache_google = (s_apache / s_google) ** 2
        var_ratio_desc_google = (s_desc / s_google) ** 2

        print(f"\n  • {name}  σ=({s_apache}, {s_google}, {s_desc})")
        print(f"    razão var: Apache/Google = {var_ratio_apache_google:.2f}x, Desc/Google = {var_ratio_desc_google:.2f}x")

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
        p_c1c2 = float((c1 & c2).mean())
        p_conj = float((c1 & c2 & c3).mean())

        print(f"    P(C1)={p_c1:.4f}  P(C2)={p_c2:.4f}  P(C3)={p_c3:.4f}")
        print(f"    P(C1∧C2)={p_c1c2:.4f}  P(C1∧C2∧C3)={p_conj:.4f}")

        results.append({
            "scenario": name,
            "sigma_apache": s_apache,
            "sigma_google": s_google,
            "sigma_desc": s_desc,
            "var_ratio_A_G": round(var_ratio_apache_google, 3),
            "var_ratio_D_G": round(var_ratio_desc_google, 3),
            "P_C1": round(p_c1, 4),
            "P_C2": round(p_c2, 4),
            "P_C3": round(p_c3, 4),
            "P_C1_C2": round(p_c1c2, 4),
            "P_conjunctive": round(p_conj, 4),
        })

    # === Tabela ===
    print("\n[3] Tabela final:")
    cols = ["scenario", "sigma_apache", "sigma_google", "sigma_desc",
            "var_ratio_A_G", "var_ratio_D_G",
            "P_C1", "P_C2", "P_C3", "P_C1_C2", "P_conjunctive"]
    widths = [20, 8, 8, 8, 8, 8, 8, 8, 8, 8, 14]
    line = " | ".join(f"{c:<{w}}" for c, w in zip(cols, widths))
    print(line)
    print("-" * len(line))
    for r in results:
        print(" | ".join(f"{str(r[c]):<{w}}" for c, w in zip(cols, widths)))

    # === CSV ===
    with open(OUTPUT_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in results:
            w.writerow(r)
    print(f"\n[4] CSV salvo: {OUTPUT_CSV}")

    # === Análise do gargalo ===
    print("\n[5] Decomposição do poder por condição:")
    print("    (mostra onde a regra conjuntiva está perdendo poder)")
    for r in results:
        if r["P_C1_C2"] > 0:
            ratio_drop = r["P_conjunctive"] / r["P_C1_C2"]
            drop_from_c3 = (r["P_C1_C2"] - r["P_conjunctive"]) / r["P_C1_C2"] * 100
            print(f"  {r['scenario']:<20}: C3 'come' {drop_from_c3:.1f}% do que C1∧C2 já tinha (passa {ratio_drop*100:.1f}%)")


if __name__ == "__main__":
    main()
