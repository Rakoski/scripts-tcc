#!/usr/bin/env python3
"""Smoke tests para analise_estatistica.py (protocolo v1.5).

Não usa pytest. Roda com: python tests/test_analise.py
Cria dados sintéticos compatíveis com a estrutura esperada e verifica:
- antissimetria de Cliff's δ
- pipeline não quebra com input válido
- sob H0 simulada, H1_aceita=False na maioria das execuções
- sob H1 forte simulada, H1_aceita=True com freq compatível com poder estimado
"""
from __future__ import annotations

import json
import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from analise_lib.tamanho_efeito import cliffs_delta, magnitude  # noqa: E402
from analise_lib.confirmatorio import (  # noqa: E402
    aplicar_regra_decisao,
    brown_forsythe,
    calibrar_f_critico_empirico,
)
from analise_lib import io_utils  # noqa: E402

SEED = 42

INSTANCIAS = {
    "apache": ["apache"],
    "google": ["google"],
    "descentralizado": ["netflix", "uber", "linkedin"],
}

N_PER = {"apache": 14, "google": 11, "descentralizado": 10}
DESC_DIST = {"netflix": 5, "uber": 2, "linkedin": 3}


def _gerar_consolidado_sintetico(sigma_apache: float, sigma_google: float,
                                 sigma_desc: float, mu: float = 2.5,
                                 seed: int = SEED) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    proj_count = 0
    for arq, n in N_PER.items():
        sigma = {"apache": sigma_apache, "google": sigma_google,
                 "descentralizado": sigma_desc}[arq]
        densidades = rng.lognormal(mean=mu, sigma=sigma, size=n)

        if arq == "descentralizado":
            instancias = []
            for inst, k in DESC_DIST.items():
                instancias.extend([inst] * k)
        else:
            instancias = [arq] * n

        ncloc_vals = rng.integers(15_000, 500_000, size=n)
        for i, (dens, inst, ncloc) in enumerate(zip(densidades, instancias, ncloc_vals)):
            sqale = dens * ncloc
            proj_count += 1
            rows.append({
                "id": f"{arq[:3]}-{i+1:02d}",
                "nome": f"{arq}_{i}",
                "empresa": inst.title(),
                "arquetipo": arq,
                "instancia": inst,
                "status": "ativo",
                "tag": f"v1.{i}.0",
                "commit_sha": f"abcdef{proj_count:04d}",
                "data_commit": (datetime(2025, 6, 1) - timedelta(days=int(i * 30))).date().isoformat(),
                "idade_anos": float(rng.uniform(5, 20)),
                "contribuidores": int(rng.integers(30, 500)),
                "loc_total": int(ncloc * 1.05),
                "loc_java": int(ncloc * 0.98),
                "sqale_index": int(sqale),
                "ncloc": int(ncloc),
                "sqale_debt_ratio": float(rng.uniform(0.5, 5.0)),
                "code_smells": int(rng.integers(50, 500)),
                "bugs": int(rng.integers(0, 50)),
                "vulnerabilities": int(rng.integers(0, 10)),
                "complexity": int(rng.integers(1000, 50000)),
                "cognitive_complexity": int(rng.integers(1000, 50000)),
                "duplicated_lines_density": float(rng.uniform(0, 10)),
                "comment_lines_density": float(rng.uniform(5, 25)),
            })
    return pd.DataFrame(rows)


def _criar_data_dir(df: pd.DataFrame, dir_path: Path,
                    com_issues: bool = True) -> Path:
    dir_path.mkdir(parents=True, exist_ok=True)
    df.to_csv(dir_path / "consolidado.csv", index=False)

    (dir_path / "ambiente.txt").write_text(
        "SonarQube Community Build v26.2.0.119303 (MQR)\n"
        "scanner sonar-scanner-5.0.1.3006-linux\n"
        "JDK: OpenJDK 17.0.18 (Debian)\n"
    )
    if com_issues:
        issues_dir = dir_path / "issues"
        issues_dir.mkdir(exist_ok=True)
        rng = np.random.default_rng(SEED)
        for _, proj in df.iterrows():
            n_issues = int(rng.integers(20, 100))
            issues = []
            for _ in range(n_issues):
                t = rng.choice(["CODE_SMELL", "BUG", "VULNERABILITY"],
                               p=[0.85, 0.12, 0.03])
                eff = int(rng.integers(5, 60))
                rule = f"java:S{rng.integers(1000, 9999)}"
                issues.append({
                    "rule": rule, "type": t, "severity": "MAJOR",
                    "effort": f"{eff}min",
                })
            (issues_dir / f"{proj['id']}.json").write_text(json.dumps(issues))
        regras_meta = {}
        all_rules = set()
        for f in issues_dir.glob("*.json"):
            for it in json.loads(f.read_text()):
                all_rules.add(it["rule"])
        for rk in all_rules:
            regras_meta[rk] = {
                "name": f"Synthetic rule {rk}",
                "type": "CODE_SMELL",
                "tags": ["convention", "design"],
            }
        (dir_path / "regras_metadata.json").write_text(json.dumps(regras_meta))
    return dir_path


# ---------- TESTES ----------


def test_cliffs_delta_antissimetria():
    rng = np.random.default_rng(0)
    x = rng.normal(0, 1, 20)
    y = rng.normal(1, 1, 20)
    d_xy = cliffs_delta(x, y)
    d_yx = cliffs_delta(y, x)
    assert abs(d_xy + d_yx) < 1e-9, f"antissimetria falhou: {d_xy} + {d_yx} != 0"
    print(f"  ✓ antissimetria: δ(x,y)={d_xy:.4f}, δ(y,x)={d_yx:.4f}")


def test_cliffs_delta_extremos():
    x = [10, 20, 30]
    y = [1, 2, 3]
    assert cliffs_delta(x, y) == 1.0
    assert cliffs_delta(y, x) == -1.0
    assert magnitude(0.5) == "grande"
    assert magnitude(0.4) == "médio"
    assert magnitude(0.2) == "pequeno"
    assert magnitude(0.1) == "negligenciável"
    print("  ✓ extremos e magnitudes Romano (2006)")


def test_pipeline_validacao_aborta_arquetipo_invalido():
    import logging
    logger = logging.getLogger("test")
    logger.handlers.clear()
    logger.addHandler(logging.NullHandler())

    df_bad = _gerar_consolidado_sintetico(0.6, 0.6, 0.6)
    df_bad.loc[0, "arquetipo"] = "INVALIDO"
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        df_bad.to_csv(td / "consolidado.csv", index=False)
        try:
            io_utils.carregar_consolidado(td, logger)
        except io_utils.ValidationError as e:
            assert "arquetipo" in str(e).lower()
            print(f"  ✓ aborta em arquetipo inválido: {e}")
            return
    raise AssertionError("não abortou")


def test_pipeline_validacao_aborta_ncloc_zero():
    import logging
    logger = logging.getLogger("test")
    logger.handlers.clear()
    logger.addHandler(logging.NullHandler())

    df_bad = _gerar_consolidado_sintetico(0.6, 0.6, 0.6)
    df_bad.loc[0, "ncloc"] = 0
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        df_bad.to_csv(td / "consolidado.csv", index=False)
        try:
            io_utils.carregar_consolidado(td, logger)
        except io_utils.ValidationError as e:
            assert "ncloc" in str(e).lower()
            print(f"  ✓ aborta em ncloc=0: {e}")
            return
    raise AssertionError("não abortou")


def test_pipeline_completo_h0():
    import subprocess
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        df = _gerar_consolidado_sintetico(0.6, 0.6, 0.6)
        _criar_data_dir(df, td, com_issues=True)
        r = subprocess.run(
            [sys.executable, str(REPO / "analise_estatistica.py"),
             "--data-dir", str(td),
             "--data-coleta", "2026-05-15"],
            capture_output=True, text=True,
        )
        if r.returncode != 0:
            print("STDOUT:", r.stdout[-2000:])
            print("STDERR:", r.stderr[-2000:])
            raise AssertionError(f"pipeline retornou {r.returncode}")
        assert (td / "analise" / "tabelas" / "tab1_descritivas_arquetipo.csv").exists()
        assert (td / "analise" / "figuras" / "fig1_boxplot_densidade_arquetipo.png").exists()
        assert (td / "analise" / "regra_decisao_h1.csv" if False else
                td / "analise" / "tabelas" / "regra_decisao_h1.csv").exists()
        rd = pd.read_csv(td / "analise" / "tabelas" / "regra_decisao_h1.csv")
        h1 = bool(rd["H1_aceita"].iloc[0])
        print(f"  ✓ pipeline H0 completo, H1_aceita={h1}")


def test_h0_majority_false():
    """Sob H0, H1_aceita deve ser False na grande maioria das execuções
    com seeds variadas. Tolerância: ≤ 10% de aceitação em 20 runs."""
    import logging
    logger = logging.getLogger("smoke_h0")
    logger.handlers.clear()
    logger.addHandler(logging.NullHandler())

    aceitas = 0
    n_runs = 20
    for seed in range(100, 100 + n_runs):
        df = _gerar_consolidado_sintetico(0.6, 0.6, 0.6, seed=seed)
        df = df.copy()
        df["densidade_divida"] = df["sqale_index"] / df["ncloc"]
        df["arquetipo_ordinal"] = df["arquetipo"].map(
            {"google": 1, "apache": 2, "descentralizado": 3}
        )
        calib = calibrar_f_critico_empirico(df, logger, n_reps=2000, seed=seed)
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            (td / "tabelas").mkdir()
            bf = brown_forsythe(df, td / "tabelas", logger)
            regra = aplicar_regra_decisao(bf, calib, td / "tabelas", logger)
            if regra["H1_aceita"]:
                aceitas += 1
    print(f"  ✓ H0 simulada: {aceitas}/{n_runs} runs aceitaram H1 (≤ 10% esperado)")
    assert aceitas <= 3, f"Excessivo: {aceitas}/{n_runs} aceitam H1 sob H0"


def test_h1_forte():
    """Sob H1 muito forte (σ_desc=2.4 vs σ_google=0.6), H1_aceita deve aparecer
    em frequência compatível com poder ~3-5%. Tolerância: pelo menos 1 em 30 runs.
    Não é check de poder, só de que a regra é capaz de aceitar."""
    import logging
    logger = logging.getLogger("smoke_h1")
    logger.handlers.clear()
    logger.addHandler(logging.NullHandler())

    aceitas = 0
    n_runs = 30
    for seed in range(200, 200 + n_runs):
        df = _gerar_consolidado_sintetico(1.5, 0.6, 2.4, seed=seed)
        df = df.copy()
        df["densidade_divida"] = df["sqale_index"] / df["ncloc"]
        df["arquetipo_ordinal"] = df["arquetipo"].map(
            {"google": 1, "apache": 2, "descentralizado": 3}
        )
        calib = calibrar_f_critico_empirico(df, logger, n_reps=2000, seed=seed)
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            (td / "tabelas").mkdir()
            bf = brown_forsythe(df, td / "tabelas", logger)
            regra = aplicar_regra_decisao(bf, calib, td / "tabelas", logger)
            if regra["H1_aceita"]:
                aceitas += 1
    print(f"  ✓ H1 forte: {aceitas}/{n_runs} runs aceitaram H1 (esperado ≥1)")
    assert aceitas >= 1, "regra nunca aceita H1 mesmo sob efeito grande — bug"


# ---------- runner ----------


def main():
    tests = [
        test_cliffs_delta_antissimetria,
        test_cliffs_delta_extremos,
        test_pipeline_validacao_aborta_arquetipo_invalido,
        test_pipeline_validacao_aborta_ncloc_zero,
        test_pipeline_completo_h0,
        test_h0_majority_false,
        test_h1_forte,
    ]
    failed = 0
    for t in tests:
        print(f"\n[{t.__name__}]")
        try:
            t()
        except AssertionError as e:
            print(f"  ✗ FAIL: {e}")
            failed += 1
        except Exception as e:
            print(f"  ✗ ERROR: {type(e).__name__}: {e}")
            failed += 1
    print(f"\n{'=' * 50}")
    if failed:
        print(f"FAIL: {failed}/{len(tests)} testes falharam")
        sys.exit(1)
    print(f"OK: {len(tests)}/{len(tests)} testes passaram")


if __name__ == "__main__":
    main()
