#!/usr/bin/env python3
from __future__ import annotations

import csv
import logging
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from coleta_lib import consolidacao
from coleta_lib.io_utils import ColetaError
from coleta_lib.scan import (
    SNAPSHOT_TYPE_HEAD, SNAPSHOT_TYPE_RELEASE_TAG,
    detectar_branch_principal, git_checkout,
)

LOG = logging.getLogger("test_scan_v17")
LOG.addHandler(logging.NullHandler())

def _git(cwd: Path, *args: str) -> str:
    r = subprocess.run(["git", *args], cwd=str(cwd),
                       capture_output=True, text=True, check=True)
    return r.stdout.strip()

def _criar_repo_remote(tmp: Path, branch: str = "main",
                       com_tag: str | None = None) -> Path:
    work = tmp / f"work-{branch}"
    work.mkdir()
    _git(work, "init", "-q", "-b", branch)
    _git(work, "config", "user.email", "t@t")
    _git(work, "config", "user.name", "t")
    (work / "a.txt").write_text("hello\n")
    _git(work, "add", "a.txt")
    _git(work, "commit", "-q", "-m", "c1")
    if com_tag:
        _git(work, "tag", com_tag)
    (work / "b.txt").write_text("world\n")
    _git(work, "add", "b.txt")
    _git(work, "commit", "-q", "-m", "c2")

    bare = tmp / f"remote-{branch}.git"
    _git(work, "clone", "--bare", "-q", str(work), str(bare))
    return bare

def _clonar(bare: Path, dest: Path) -> Path:
    _git(dest.parent, "clone", "-q", str(bare), dest.name)
    return dest

def test_git_checkout_release_tag():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        bare = _criar_repo_remote(tmp, branch="main", com_tag="v1.0")
        clone = _clonar(bare, tmp / "clone")
        sha = git_checkout(clone, "v1.0", LOG)
        assert len(sha) == 7, f"sha7 esperado, veio {sha!r}"
        head = _git(clone, "rev-parse", "HEAD")
        tagged = _git(clone, "rev-list", "-n", "1", "v1.0")
        assert head == tagged, f"HEAD={head} ≠ tag={tagged}"
        print("  ✓ release-tag-pre-2026 (modo v1.5) faz checkout literal da tag")

def test_git_checkout_head_of_main():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        bare = _criar_repo_remote(tmp, branch="main", com_tag="v1.0")
        clone = _clonar(bare, tmp / "clone")
        git_checkout(clone, "v1.0", LOG)
        head_v1 = _git(clone, "rev-parse", "HEAD")
        sha = git_checkout(clone, "", LOG,
                           snapshot_type=SNAPSHOT_TYPE_HEAD,
                           branch_principal="main")
        assert len(sha) == 7
        head_now = _git(clone, "rev-parse", "HEAD")
        tip = _git(clone, "rev-parse", "origin/main")
        assert head_now == tip, f"HEAD={head_now} ≠ origin/main={tip}"
        assert head_now != head_v1, "checkout HEAD não avançou da tag"
        print("  ✓ head-of-main (modo v1.7) faz checkout de origin/<branch>")

def test_git_checkout_head_aceita_master():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        bare = _criar_repo_remote(tmp, branch="master")
        clone = _clonar(bare, tmp / "clone")
        sha = git_checkout(clone, "", LOG,
                           snapshot_type=SNAPSHOT_TYPE_HEAD,
                           branch_principal="master")
        assert len(sha) == 7
        head = _git(clone, "rev-parse", "HEAD")
        tip = _git(clone, "rev-parse", "origin/master")
        assert head == tip
        print("  ✓ head-of-main funciona com branch=master")

def test_git_checkout_validacao_input():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        bare = _criar_repo_remote(tmp, branch="main", com_tag="v1.0")
        clone = _clonar(bare, tmp / "clone")

        try:
            git_checkout(clone, "v1.0", LOG, snapshot_type="bogus")
        except ColetaError as e:
            assert "snapshot_type inválido" in str(e)
        else:
            raise AssertionError("snapshot_type inválido deveria ter falhado")

        try:
            git_checkout(clone, "", LOG, snapshot_type=SNAPSHOT_TYPE_HEAD,
                         branch_principal=None)
        except ColetaError as e:
            assert "branch_principal" in str(e)
        else:
            raise AssertionError("head-of-main sem branch deveria ter falhado")

        try:
            git_checkout(clone, "", LOG,
                         snapshot_type=SNAPSHOT_TYPE_RELEASE_TAG)
        except ColetaError as e:
            assert "requer tag" in str(e)
        else:
            raise AssertionError("release-tag sem tag deveria ter falhado")

        print("  ✓ validação rejeita 3 combinações inválidas")

def test_detectar_branch_principal_main():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        bare = _criar_repo_remote(tmp, branch="main")
        clone = _clonar(bare, tmp / "clone")
        assert detectar_branch_principal(clone, LOG) == "main"
        print("  ✓ detecta 'main' via symbolic-ref")

def test_detectar_branch_principal_master():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        bare = _criar_repo_remote(tmp, branch="master")
        clone = _clonar(bare, tmp / "clone")
        assert detectar_branch_principal(clone, LOG) == "master"
        print("  ✓ detecta 'master' via symbolic-ref")

def test_detectar_branch_principal_fallback_show_ref():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        bare = _criar_repo_remote(tmp, branch="main")
        clone = _clonar(bare, tmp / "clone")
        subprocess.run(["git", "symbolic-ref", "--delete",
                        "refs/remotes/origin/HEAD"], cwd=str(clone), check=True)
        assert detectar_branch_principal(clone, LOG) == "main"
        print("  ✓ fallback show-ref encontra 'main' quando symbolic-ref ausente")

def test_detectar_branch_principal_falha():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        bare = _criar_repo_remote(tmp, branch="custom-default")
        clone = _clonar(bare, tmp / "clone")
        subprocess.run(["git", "symbolic-ref", "--delete",
                        "refs/remotes/origin/HEAD"], cwd=str(clone), check=False)
        try:
            detectar_branch_principal(clone, LOG)
        except ColetaError as e:
            assert "branch_principal indeterminado" in str(e)
            print("  ✓ falha quando nem main nem master existem")
            return
        raise AssertionError("deveria ter levantado ColetaError")

def test_montar_consolidado_inclui_novos_campos():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        rows = [
            {"id": "apache-foo-99", "nome": "foo", "empresa": "Apache",
             "arquetipo": "apache", "status": "ativo",
             "tag": "v1.0", "commit_sha": "abc1234",
             "data_commit": "2025-12-02", "idade_anos": "5",
             "contribuidores": "10", "loc_total": "1000", "loc_java": "900"},
            {"id": "google-bar-50", "nome": "bar", "empresa": "Google",
             "arquetipo": "google", "status": "ativo",
             "tag": "HEAD-on-main-2026-05-24", "commit_sha": "def5678",
             "data_commit": "2026-05-20",
             "snapshot_type": "head-of-main", "branch_principal": "main",
             "subconjunto": "n30-v1.6"},
        ]
        metricas = {
            "apache-foo-99": {"ncloc": "900", "sqale_index": "100"},
            "google-bar-50": {"ncloc": "500", "sqale_index": "50"},
        }
        saida = tmp / "consolidado.csv"
        consolidacao.montar_consolidado(rows, metricas, saida, LOG,
                                        data_coleta="2026-05-24")

        with saida.open(encoding="utf-8") as f:
            out = list(csv.DictReader(f))
        assert len(out) == 2

        for col in ("snapshot_type", "branch_principal",
                    "idade_snapshot_dias", "subconjunto"):
            assert col in out[0], f"coluna {col} faltando no CSV"

        retro = next(r for r in out if r["id"] == "apache-foo-99")
        novo = next(r for r in out if r["id"] == "google-bar-50")

        assert retro["snapshot_type"] == "release-tag-pre-2026"
        assert retro["subconjunto"] == "n34-v1.5"
        assert retro["branch_principal"] == ""
        assert retro["idade_snapshot_dias"] == "173", \
            f"idade esperada=173, veio={retro['idade_snapshot_dias']!r}"

        assert novo["snapshot_type"] == "head-of-main"
        assert novo["branch_principal"] == "main"
        assert novo["subconjunto"] == "n30-v1.6"
        assert novo["idade_snapshot_dias"] == "4"

        print("  ✓ consolidado.csv inclui snapshot_type, branch_principal, "
              "idade_snapshot_dias, subconjunto (com defaults retroativos)")

def test_montar_consolidado_idade_sem_data_coleta():
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        rows = [{"id": "x", "nome": "x", "empresa": "Apache",
                 "arquetipo": "apache", "data_commit": "2025-01-01"}]
        saida = tmp / "c.csv"
        consolidacao.montar_consolidado(rows, {}, saida, LOG,
                                        data_coleta=None)
        with saida.open(encoding="utf-8") as f:
            out = list(csv.DictReader(f))
        assert out[0]["idade_snapshot_dias"] == ""
        print("  ✓ idade_snapshot_dias vazio quando data_coleta=None")

def main() -> int:
    testes = [
        test_git_checkout_release_tag,
        test_git_checkout_head_of_main,
        test_git_checkout_head_aceita_master,
        test_git_checkout_validacao_input,
        test_detectar_branch_principal_main,
        test_detectar_branch_principal_master,
        test_detectar_branch_principal_fallback_show_ref,
        test_detectar_branch_principal_falha,
        test_montar_consolidado_inclui_novos_campos,
        test_montar_consolidado_idade_sem_data_coleta,
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
