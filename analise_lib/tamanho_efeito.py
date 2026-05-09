"""Procedimento 4 do §8 — Cliff's δ pareado, Romano et al. (2006)."""
from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd


def cliffs_delta(x, y) -> float:
    """δ = P(X > Y) - P(X < Y), no intervalo [-1, 1]."""
    nx, ny = len(x), len(y)
    if nx == 0 or ny == 0:
        return float("nan")
    x_arr = np.asarray(x).reshape(-1, 1)
    y_arr = np.asarray(y).reshape(1, -1)
    diff = x_arr - y_arr
    return float(((diff > 0).sum() - (diff < 0).sum()) / (nx * ny))


def magnitude(delta: float) -> str:
    """Romano et al. (2006)."""
    a = abs(delta)
    if a < 0.147:
        return "negligenciável"
    if a < 0.33:
        return "pequeno"
    if a < 0.474:
        return "médio"
    return "grande"


PARES = [
    ("apache", "google"),
    ("apache", "descentralizado"),
    ("google", "descentralizado"),
]


def cliffs_delta_pares(df: pd.DataFrame, tabelas_dir: Path,
                       logger: logging.Logger) -> pd.DataFrame:
    rows = []
    for a, b in PARES:
        x = df.loc[df["arquetipo"] == a, "densidade_divida"].values
        y = df.loc[df["arquetipo"] == b, "densidade_divida"].values
        d = cliffs_delta(x, y)
        rows.append({
            "grupo_x": a,
            "grupo_y": b,
            "n_x": len(x),
            "n_y": len(y),
            "cliff_delta": d,
            "magnitude": magnitude(d),
            "interpretacao": (
                "x > y em maioria estocástica" if d > 0
                else "y > x em maioria estocástica" if d < 0
                else "sem dominância"
            ),
        })
    out = pd.DataFrame(rows)
    csv_path = tabelas_dir / "tab4_cliffs_delta_pares.csv"
    out.to_csv(csv_path, index=False, float_format="%.6f")
    logger.info("tab4 escrita: %s", csv_path)
    return out
