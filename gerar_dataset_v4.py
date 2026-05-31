#!/usr/bin/env python3
from __future__ import annotations

import csv
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
DATASET_V3 = SCRIPTS / "projetos-tcc-dataset-3.csv"
CLONES_V17 = SCRIPTS / "clones_v17.csv"
DATASET_V4 = SCRIPTS / "projetos-tcc-dataset-4.csv"

SCHEMA_V4 = [
    "id", "nome", "empresa", "arquetipo", "status", "url", "tag", "commit_sha",
    "data_commit", "loc_total", "loc_java", "pct_java", "contribuidores",
    "idade_anos", "sonar_status", "sonar_project_key", "notas",
    "branch_principal", "snapshot_type", "subconjunto", "idade_snapshot_dias",
]

SNAPSHOT_TYPES_VALIDOS = {"release-tag-pre-2026", "head-of-main"}
SUBCONJUNTOS_VALIDOS = {"n34-v1.5", "n30-v1.6"}

def _ler_csv(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(f"input ausente: {path}")
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))

def linha_v3_para_v4(r: dict) -> dict:
    out = {col: r.get(col, "") for col in SCHEMA_V4}
    out["branch_principal"] = ""
    out["snapshot_type"] = "release-tag-pre-2026"
    out["subconjunto"] = "n34-v1.5"
    out["idade_snapshot_dias"] = ""
    return out

def linha_clones_para_v4(r: dict) -> dict:
    out = {col: "" for col in SCHEMA_V4}
    for col in ("id", "nome", "empresa", "arquetipo", "status", "url",
                "tag", "commit_sha", "data_commit",
                "branch_principal", "snapshot_type", "subconjunto"):
        out[col] = r.get(col, "")
    out["sonar_project_key"] = r.get("id", "")
    return out

def validar(linhas: list[dict], n_v3: int, n_clones: int) -> None:
    erros: list[str] = []

    if len(linhas) != n_v3 + n_clones:
        erros.append(f"total={len(linhas)} esperado={n_v3 + n_clones}")

    ids = [l["id"] for l in linhas]
    dup = [i for i in set(ids) if ids.count(i) > 1]
    if dup:
        erros.append(f"ids duplicados: {sorted(dup)}")

    for i, l in enumerate(linhas):
        faltam = [c for c in SCHEMA_V4 if c not in l]
        if faltam:
            erros.append(f"linha {i} ({l.get('id','?')}): colunas ausentes {faltam}")
        st = l.get("snapshot_type", "")
        if st not in SNAPSHOT_TYPES_VALIDOS:
            erros.append(f"linha {i} ({l.get('id','?')}): snapshot_type inválido {st!r}")
        sc = l.get("subconjunto", "")
        if sc not in SUBCONJUNTOS_VALIDOS:
            erros.append(f"linha {i} ({l.get('id','?')}): subconjunto inválido {sc!r}")

    for l in linhas:
        if l["snapshot_type"] == "head-of-main" and not l["branch_principal"]:
            erros.append(f"{l['id']}: snapshot_type=head-of-main sem branch_principal")
        if l["snapshot_type"] == "release-tag-pre-2026" and l["branch_principal"]:
            erros.append(f"{l['id']}: release-tag-pre-2026 com branch_principal não-vazio")

    if erros:
        msg = "Validação falhou:\n  - " + "\n  - ".join(erros)
        raise ValueError(msg)

def gerar(escrever: bool = True) -> list[dict]:
    rows_v3 = _ler_csv(DATASET_V3)
    rows_clones = _ler_csv(CLONES_V17)

    unificado: list[dict] = [linha_v3_para_v4(r) for r in rows_v3]
    unificado += [linha_clones_para_v4(r) for r in rows_clones]

    validar(unificado, n_v3=len(rows_v3), n_clones=len(rows_clones))

    if escrever:
        with DATASET_V4.open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=SCHEMA_V4, extrasaction="ignore")
            w.writeheader()
            w.writerows(unificado)
        print(f"escrito: {DATASET_V4}")
        print(f"  {len(rows_v3)} linhas N=34 (n34-v1.5) + "
              f"{len(rows_clones)} linhas N=30 (n30-v1.6) = "
              f"{len(unificado)} totais")

    return unificado

if __name__ == "__main__":
    try:
        gerar()
    except (FileNotFoundError, ValueError) as e:
        print(f"[ERRO] {e}", file=sys.stderr)
        sys.exit(1)
