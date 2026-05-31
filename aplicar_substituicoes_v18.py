#!/usr/bin/env python3
from __future__ import annotations

import csv
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from coleta_lib.io_utils import get_clones_dir, get_repo_root, get_scripts_dir

BASE_DIR = get_repo_root()
SCRIPTS_DIR = get_scripts_dir()
CLONES_DIR = get_clones_dir()
DATASET4 = SCRIPTS_DIR / "projetos-tcc-dataset-4.csv"
CLONES_V17 = SCRIPTS_DIR / "clones_v17.csv"
CLONAR_V17_PY = SCRIPTS_DIR / "clonar_v17.py"

EXCLUIDOS = [
    "apache-hadoop-18",
    "apache-doris-19",
    "google-open-location-code-16",
    "google-bundletool-17",
    "google-bindiff-18",
    "google-firebase-android-sdk-21",
    "netflix-maestro-10",
]

SUBSTITUTOS: list[tuple[str, str, str, str, str, str]] = [
    ("apache-incubator-seata-18", "apache/incubator-seata",
     "incubator-seata", "Apache", "apache", "incubator-seata"),
    ("apache-shenyu-19", "apache/shenyu",
     "shenyu", "Apache", "apache", "shenyu"),
    ("google-java-docs-samples-16", "GoogleCloudPlatform/java-docs-samples",
     "java-docs-samples", "Google", "google", "java-docs-samples"),
    ("google-flogger-17", "google/flogger",
     "flogger", "Google", "google", "flogger"),
    ("google-j2cl-18", "google/j2cl",
     "j2cl", "Google", "google", "j2cl"),
    ("google-dataflow-templates-21", "GoogleCloudPlatform/DataflowTemplates",
     "dataflow-templates", "Google", "google", "DataflowTemplates"),
    ("netflix-servo-10", "Netflix/servo",
     "servo", "Netflix", "descentralizado", "servo"),
]

BRANCH_FALLBACK = {
    "apache/incubator-seata": "2.x",
    "apache/shenyu": "master",
    "GoogleCloudPlatform/java-docs-samples": "main",
    "google/flogger": "master",
    "google/j2cl": "master",
    "GoogleCloudPlatform/DataflowTemplates": "main",
    "Netflix/servo": "master",
}

DATA_TAG = "2026-05-24"

DATASET4_COLS = [
    "id", "nome", "empresa", "arquetipo", "status", "url",
    "tag", "commit_sha", "data_commit",
    "loc_total", "loc_java", "pct_java",
    "contribuidores", "idade_anos", "sonar_status", "sonar_project_key",
    "notas",
    "branch_principal", "snapshot_type", "subconjunto", "idade_snapshot_dias",
]

CLONES_V17_COLS = [
    "id", "nome", "empresa", "arquetipo", "status", "url",
    "tag", "commit_sha", "data_commit",
    "branch_principal", "snapshot_type", "subconjunto",
]

def log(msg: str) -> None:
    print(f"[v1.8] {msg}", flush=True)

def abortar(msg: str) -> None:
    print(f"\n[v1.8] ABORT: {msg}\n", file=sys.stderr, flush=True)
    sys.exit(1)

def run(cmd: list[str], cwd: Path | None = None, timeout: int = 1800
        ) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd, cwd=str(cwd) if cwd else None,
        capture_output=True, text=True, timeout=timeout, check=False,
    )

def ler_csv(path: Path) -> tuple[list[str], list[dict]]:
    with path.open(encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        cols = list(r.fieldnames or [])
        rows = list(r)
    return cols, rows

def escrever_csv_atomico(path: Path, cols: list[str],
                         rows: list[dict]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for row in rows:
            w.writerow({c: row.get(c, "") for c in cols})
    os.replace(tmp, path)

def fase1_validar() -> None:
    log("FASE 1 — validação read-only")

    if not DATASET4.exists():
        abortar(f"não encontrei {DATASET4}")
    if not CLONES_V17.exists():
        abortar(f"não encontrei {CLONES_V17}")
    if not CLONAR_V17_PY.exists():
        abortar(f"não encontrei {CLONAR_V17_PY}")

    cols4, rows4 = ler_csv(DATASET4)
    ids4 = {r["id"] for r in rows4}
    log(f"  dataset-4: {len(rows4)} linhas de dados, {len(cols4)} colunas")

    faltam_excluidos_4 = [e for e in EXCLUIDOS if e not in ids4]
    if faltam_excluidos_4:
        abortar(f"dataset-4: faltam reprovados que deveriam estar: "
                f"{faltam_excluidos_4}")

    ids_subs = {s[0] for s in SUBSTITUTOS}
    presentes_subs_4 = ids_subs & ids4
    if presentes_subs_4:
        abortar(f"dataset-4: substitutos já presentes (não pode): "
                f"{sorted(presentes_subs_4)}")

    if len(rows4) != 64:
        log(f"  AVISO: dataset-4 tem {len(rows4)} linhas (esperado 64). "
            f"Seguindo mesmo assim.")

    cols17, rows17 = ler_csv(CLONES_V17)
    ids17 = {r["id"] for r in rows17}
    log(f"  clones_v17: {len(rows17)} linhas de dados, {len(cols17)} colunas")

    faltam_excluidos_17 = [e for e in EXCLUIDOS if e not in ids17]
    if faltam_excluidos_17:
        abortar(f"clones_v17: faltam reprovados: {faltam_excluidos_17}")

    presentes_subs_17 = ids_subs & ids17
    if presentes_subs_17:
        abortar(f"clones_v17: substitutos já presentes: "
                f"{sorted(presentes_subs_17)}")

    if len(rows17) != 30:
        log(f"  AVISO: clones_v17 tem {len(rows17)} linhas (esperado 30).")

    colidem = []
    for (_, _, _, _, _, dir_clone) in SUBSTITUTOS:
        destino = CLONES_DIR / dir_clone
        if destino.exists():
            colidem.append(str(destino))
    if colidem:
        abortar(f"diretórios de clone dos substitutos já existem (não dá "
                f"pra clonar em cima):\n  " + "\n  ".join(colidem))

    log("  FASE 1 OK — pode prosseguir")

def detectar_branch(repo_dir: Path, owner_repo: str) -> str:
    r = run(["git", "symbolic-ref", "--short", "refs/remotes/origin/HEAD"],
            cwd=repo_dir)
    if r.returncode == 0:
        ref = r.stdout.strip()
        if ref.startswith("origin/"):
            return ref[len("origin/"):]
        return ref
    fb = BRANCH_FALLBACK.get(owner_repo)
    if not fb:
        raise RuntimeError(
            f"branch indeterminado para {owner_repo} e sem fallback")
    r = run(["git", "show-ref", "--verify", "--quiet",
             f"refs/remotes/origin/{fb}"], cwd=repo_dir)
    if r.returncode != 0:
        raise RuntimeError(
            f"branch fallback '{fb}' não existe em origin para {owner_repo}")
    return fb

def detectar_sha_data(repo_dir: Path, branch: str
                      ) -> tuple[str, str]:
    r = run(["git", "rev-parse", f"origin/{branch}"], cwd=repo_dir)
    if r.returncode != 0:
        raise RuntimeError(f"git rev-parse origin/{branch} falhou: "
                           f"{r.stderr.strip()}")
    sha = r.stdout.strip()
    r = run(["git", "log", "-1", "--format=%cI", sha], cwd=repo_dir)
    if r.returncode != 0:
        raise RuntimeError(f"git log de {sha} falhou: {r.stderr.strip()}")
    data_iso = r.stdout.strip()
    data_iso = data_iso[:10] if data_iso else ""
    return sha, data_iso

def fase2_clonar(metadados: dict[str, dict]) -> None:
    log("FASE 2 — clonar 7 substitutos e detectar metadados")
    CLONES_DIR.mkdir(parents=True, exist_ok=True)

    for (id_novo, owner_repo, _nome, _empresa,
         _arq, dir_clone) in SUBSTITUTOS:
        destino = CLONES_DIR / dir_clone
        log(f"  clonando {owner_repo} -> {dir_clone}/")
        url = f"https://github.com/{owner_repo}.git"
        r = run(["git", "clone", url, str(destino)], timeout=1800)
        if r.returncode != 0:
            tail = (r.stderr or r.stdout).strip().splitlines()[-5:]
            abortar(f"git clone falhou para {owner_repo}:\n  "
                    + "\n  ".join(tail))
        try:
            branch = detectar_branch(destino, owner_repo)
            sha, data = detectar_sha_data(destino, branch)
        except RuntimeError as e:
            abortar(f"detecção de metadados falhou em {id_novo}: {e}")
        metadados[id_novo] = {"branch": branch, "sha": sha, "data": data}
        log(f"    branch={branch}  sha={sha[:7]}  data={data}")

def montar_linha_dataset4(sub: tuple, meta: dict,
                          cols: list[str]) -> dict:
    (id_novo, owner_repo, nome_repo, empresa, arquetipo, _dir_clone) = sub
    branch = meta["branch"]
    sha = meta["sha"]
    data_commit = meta["data"]
    row = {c: "" for c in cols}
    row.update({
        "id": id_novo,
        "nome": nome_repo,
        "empresa": empresa,
        "arquetipo": arquetipo,
        "status": "ativo",
        "url": f"https://github.com/{owner_repo}",
        "tag": f"HEAD-on-{branch}-{DATA_TAG}",
        "commit_sha": sha,
        "data_commit": data_commit,
        "sonar_project_key": id_novo,
        "branch_principal": branch,
        "snapshot_type": "head-of-main",
        "subconjunto": "n30-v1.6",
    })
    return row

def montar_linha_clones_v17(sub: tuple, meta: dict) -> dict:
    (id_novo, owner_repo, nome_repo, empresa, arquetipo, _dir_clone) = sub
    branch = meta["branch"]
    return {
        "id": id_novo,
        "nome": nome_repo,
        "empresa": empresa,
        "arquetipo": arquetipo,
        "status": "ativo",
        "url": f"https://github.com/{owner_repo}",
        "tag": f"HEAD-on-{branch}-{DATA_TAG}",
        "commit_sha": meta["sha"],
        "data_commit": meta["data"],
        "branch_principal": branch,
        "snapshot_type": "head-of-main",
        "subconjunto": "n30-v1.6",
    }

def fase3_csvs(metadados: dict[str, dict]) -> None:
    log("FASE 3 — backup + reescrita dos 2 CSVs")
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")

    bak4 = DATASET4.with_name(f"{DATASET4.name}.bak-v18-{ts}")
    shutil.copy2(DATASET4, bak4)
    log(f"  backup: {bak4.name}")
    cols4, rows4 = ler_csv(DATASET4)
    rows4_filtrado = [r for r in rows4 if r["id"] not in EXCLUIDOS]
    for sub in SUBSTITUTOS:
        rows4_filtrado.append(montar_linha_dataset4(sub, metadados[sub[0]],
                                                    cols4))
    escrever_csv_atomico(DATASET4, cols4, rows4_filtrado)
    log(f"  dataset-4: {len(rows4)} → {len(rows4_filtrado)} linhas de dados")

    bak17 = CLONES_V17.with_name(f"{CLONES_V17.name}.bak-v18-{ts}")
    shutil.copy2(CLONES_V17, bak17)
    log(f"  backup: {bak17.name}")
    cols17, rows17 = ler_csv(CLONES_V17)
    rows17_filtrado = [r for r in rows17 if r["id"] not in EXCLUIDOS]
    for sub in SUBSTITUTOS:
        rows17_filtrado.append(montar_linha_clones_v17(sub, metadados[sub[0]]))
    escrever_csv_atomico(CLONES_V17, cols17, rows17_filtrado)
    log(f"  clones_v17: {len(rows17)} → {len(rows17_filtrado)} linhas de dados")

EXCLUIDO_TO_SUB = {
    "apache-hadoop-18":              ("apache-incubator-seata-18", "apache/incubator-seata",
                                      "incubator-seata", "Apache", "apache"),
    "apache-doris-19":               ("apache-shenyu-19", "apache/shenyu",
                                      "shenyu", "Apache", "apache"),
    "google-open-location-code-16":  ("google-java-docs-samples-16",
                                      "GoogleCloudPlatform/java-docs-samples",
                                      "java-docs-samples", "Google", "google"),
    "google-bundletool-17":          ("google-flogger-17", "google/flogger",
                                      "flogger", "Google", "google"),
    "google-bindiff-18":             ("google-j2cl-18", "google/j2cl",
                                      "j2cl", "Google", "google"),
    "google-firebase-android-sdk-21":("google-dataflow-templates-21",
                                      "GoogleCloudPlatform/DataflowTemplates",
                                      "dataflow-templates", "Google", "google"),
    "netflix-maestro-10":            ("netflix-servo-10", "Netflix/servo",
                                      "servo", "Netflix", "descentralizado"),
}

def fase4_clonar_v17_py() -> None:
    log("FASE 4 — substituir tuplas em PROJETOS_V17 (clonar_v17.py)")
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    bak = CLONAR_V17_PY.with_name(f"{CLONAR_V17_PY.name}.bak-v18-{ts}")
    shutil.copy2(CLONAR_V17_PY, bak)
    log(f"  backup: {bak.name}")

    texto = CLONAR_V17_PY.read_text(encoding="utf-8")
    novo = texto

    for excl_id, (id_novo, owner_repo, nome_repo, empresa, arq) in (
            EXCLUIDO_TO_SUB.items()):
        padrao = re.compile(
            r'^([ \t]*)\("' + re.escape(excl_id) + r'",.*?\n',
            re.MULTILINE,
        )
        m = padrao.search(novo)
        if not m:
            abortar(f"não achei tupla com id '{excl_id}' em clonar_v17.py")
        indent = m.group(1)
        nova_linha = (
            f'{indent}("{id_novo}", "{owner_repo}", "{nome_repo}", '
            f'"{empresa}", "{arq}"),\n'
        )
        novo = novo[:m.start()] + nova_linha + novo[m.end():]
        log(f"  {excl_id} -> {id_novo}")

    residuais = [e for e in EXCLUIDO_TO_SUB if f'"{e}"' in novo]
    if residuais:
        abortar(f"após substituição ainda há menções aos excluídos: "
                f"{residuais}")
    for (id_novo, _, _, _, _) in EXCLUIDO_TO_SUB.values():
        marcador = f'"{id_novo}"'
        n_ocorr = novo.count(marcador)
        if n_ocorr != 1:
            abortar(f"substituto '{id_novo}' aparece "
                    f"{n_ocorr}x em clonar_v17.py (esperado 1)")

    tmp = CLONAR_V17_PY.with_suffix(CLONAR_V17_PY.suffix + ".tmp")
    tmp.write_text(novo, encoding="utf-8")
    os.replace(tmp, CLONAR_V17_PY)
    log("  clonar_v17.py reescrito")

def fase5_validar_final() -> None:
    log("FASE 5 — validação final")

    cols4, rows4 = ler_csv(DATASET4)
    cols17, rows17 = ler_csv(CLONES_V17)
    ids4 = {r["id"] for r in rows4}
    ids17 = {r["id"] for r in rows17}

    log(f"  dataset-4: {len(rows4)} dados (esperado 64)")
    log(f"  clones_v17: {len(rows17)} dados (esperado 30)")
    n30 = sum(1 for r in rows4 if r.get("subconjunto") == "n30-v1.6")
    log(f"  dataset-4 subconjunto=n30-v1.6: {n30} (esperado 30)")

    por_arq: dict[str, int] = {}
    for r in rows4:
        por_arq[r["arquetipo"]] = por_arq.get(r["arquetipo"], 0) + 1
    log(f"  dataset-4 por arquétipo: {por_arq}  "
        f"(esperado apache=24, google=20, descentralizado=20)")

    excl_residuais = [e for e in EXCLUIDOS if e in ids4 or e in ids17]
    if excl_residuais:
        abortar(f"excluídos ainda presentes: {excl_residuais}")
    ids_sub = {s[0] for s in SUBSTITUTOS}
    falta_subs = [s for s in ids_sub if s not in ids4 or s not in ids17]
    if falta_subs:
        abortar(f"substitutos ausentes em algum CSV: {falta_subs}")

    texto = CLONAR_V17_PY.read_text(encoding="utf-8")
    for e in EXCLUIDOS:
        if f'"{e}"' in texto:
            abortar(f"clonar_v17.py ainda menciona excluído: {e}")
    for s in ids_sub:
        if f'"{s}"' not in texto:
            abortar(f"clonar_v17.py não menciona substituto: {s}")

    log("  ✅ tudo OK")

def main() -> int:
    log(f"=== aplicar_substituicoes_v18 — {datetime.now().isoformat()} ===")
    fase1_validar()
    metadados: dict[str, dict] = {}
    fase2_clonar(metadados)
    fase3_csvs(metadados)
    fase4_clonar_v17_py()
    fase5_validar_final()
    log("=== concluído com sucesso ===")
    return 0

if __name__ == "__main__":
    sys.exit(main())
