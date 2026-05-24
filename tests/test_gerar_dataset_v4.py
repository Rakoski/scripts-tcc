#!/usr/bin/env python3
"""Smoke tests para gerar_dataset_v4.py + projetos-tcc-dataset-4.csv.

Não usa pytest. Roda com: python3 tests/test_gerar_dataset_v4.py

Lê os CSVs reais (v3, clones_v17, v4) e valida invariantes do briefing.
Re-gera dataset-4 em memória (escrever=False) quando precisa comparar.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from gerar_dataset_v4 import (  # noqa: E402
    CLONES_V17, DATASET_V3, DATASET_V4, SCHEMA_V4, gerar,
)

# Conjunto canônico = o que está no disco (escrito por gerar_dataset_v4.py).
# Se o disco e a regeração divergirem, _ler_v4 e gerar() vão dar contagens
# distintas e os testes falham (sinal de que dataset-4 está stale).
def _ler(path: Path) -> list[dict]:
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def test_total_linhas():
    v4 = _ler(DATASET_V4)
    v3 = _ler(DATASET_V3)
    clones = _ler(CLONES_V17)
    esperado = len(v3) + len(clones)
    assert len(v4) == esperado, \
        f"v4={len(v4)} ≠ v3({len(v3)})+clones({len(clones)})={esperado}"
    print(f"  ✓ total={len(v4)} = v3({len(v3)}) + clones({len(clones)})")


def test_sem_duplicatas_id():
    v4 = _ler(DATASET_V4)
    ids = [r["id"] for r in v4]
    dup = [i for i in set(ids) if ids.count(i) > 1]
    assert not dup, f"ids duplicados: {dup}"
    print(f"  ✓ {len(set(ids))} ids únicos")


def test_n34_retroativo():
    v4 = _ler(DATASET_V4)
    v3 = _ler(DATASET_V3)
    ids_v3 = {r["id"] for r in v3}
    antigas = [r for r in v4 if r["id"] in ids_v3]
    assert len(antigas) == len(v3), \
        f"v4 deveria conter todas as {len(v3)} antigas, tem {len(antigas)}"
    for r in antigas:
        assert r["snapshot_type"] == "release-tag-pre-2026", \
            f"{r['id']}: snapshot_type={r['snapshot_type']!r}"
        assert r["subconjunto"] == "n34-v1.5", \
            f"{r['id']}: subconjunto={r['subconjunto']!r}"
    print(f"  ✓ todas as {len(antigas)} antigas marcadas n34-v1.5 / release-tag-pre-2026")


def test_n30_novo():
    v4 = _ler(DATASET_V4)
    clones = _ler(CLONES_V17)
    ids_clones = {r["id"] for r in clones}
    novas = [r for r in v4 if r["id"] in ids_clones]
    assert len(novas) == len(clones)
    for r in novas:
        assert r["snapshot_type"] == "head-of-main", \
            f"{r['id']}: snapshot_type={r['snapshot_type']!r}"
        assert r["subconjunto"] == "n30-v1.6", \
            f"{r['id']}: subconjunto={r['subconjunto']!r}"
    print(f"  ✓ todas as {len(novas)} novas marcadas n30-v1.6 / head-of-main")


def test_branch_principal_n30():
    v4 = _ler(DATASET_V4)
    clones = _ler(CLONES_V17)
    ids_clones = {r["id"] for r in clones}
    novas = [r for r in v4 if r["id"] in ids_clones]
    for r in novas:
        assert r["branch_principal"], \
            f"{r['id']}: branch_principal vazio (head-of-main exige branch)"
    print(f"  ✓ {len(novas)} novas têm branch_principal não-vazio")


def test_branch_principal_n34_vazio():
    v4 = _ler(DATASET_V4)
    v3 = _ler(DATASET_V3)
    ids_v3 = {r["id"] for r in v3}
    antigas = [r for r in v4 if r["id"] in ids_v3]
    for r in antigas:
        assert r["branch_principal"] == "", \
            f"{r['id']}: branch_principal={r['branch_principal']!r} (esperado vazio)"
    print(f"  ✓ {len(antigas)} antigas têm branch_principal vazio")


def test_sonar_project_key_preenchido():
    v4 = _ler(DATASET_V4)
    for r in v4:
        assert r["sonar_project_key"], \
            f"{r['id']}: sonar_project_key vazio"
        # Convenção v1.5: sonar_project_key = id
        assert r["sonar_project_key"] == r["id"], \
            f"{r['id']}: sonar_project_key={r['sonar_project_key']!r} ≠ id"
    print(f"  ✓ {len(v4)} linhas têm sonar_project_key=id")


def test_ordem_preservada():
    v4 = _ler(DATASET_V4)
    v3 = _ler(DATASET_V3)
    n = len(v3)
    primeiras = v4[:n]
    for i, (a, b) in enumerate(zip(primeiras, v3)):
        assert a["id"] == b["id"], \
            f"posição {i}: v4={a['id']!r} ≠ v3={b['id']!r}"
    print(f"  ✓ primeiras {n} linhas do v4 batem ordem do v3")


def test_schema_v4_completo():
    """Sanity: header do CSV bate com SCHEMA_V4 (mesmo conteúdo, mesma ordem)."""
    with DATASET_V4.open(encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
    assert header == SCHEMA_V4, \
        f"header divergente:\n  arquivo={header}\n  esperado={SCHEMA_V4}"
    print(f"  ✓ header bate SCHEMA_V4 ({len(SCHEMA_V4)} colunas)")


def test_geracao_idempotente():
    """gerar(escrever=False) reproduz exatamente o disco."""
    em_memoria = gerar(escrever=False)
    disco = _ler(DATASET_V4)
    assert len(em_memoria) == len(disco)
    for a, b in zip(em_memoria, disco):
        for col in SCHEMA_V4:
            va, vb = a.get(col, ""), b.get(col, "")
            assert va == vb, f"{a['id']}.{col}: memória={va!r} ≠ disco={vb!r}"
    print(f"  ✓ regeração in-memory reproduz disco linha-a-linha")


def main() -> int:
    testes = [
        test_total_linhas,
        test_sem_duplicatas_id,
        test_n34_retroativo,
        test_n30_novo,
        test_branch_principal_n30,
        test_branch_principal_n34_vazio,
        test_sonar_project_key_preenchido,
        test_ordem_preservada,
        test_schema_v4_completo,
        test_geracao_idempotente,
    ]
    falhas = 0
    for t in testes:
        print(f"\n{t.__name__}")
        try:
            t()
        except AssertionError as e:
            print(f"  ✗ FALHA: {e}")
            falhas += 1
        except Exception as e:
            print(f"  ✗ ERRO: {type(e).__name__}: {e}")
            falhas += 1
    print(f"\n{'=' * 60}")
    if falhas:
        print(f"FALHOU: {falhas}/{len(testes)}")
        return 1
    print(f"OK: {len(testes)}/{len(testes)} passaram")
    return 0


if __name__ == "__main__":
    sys.exit(main())
