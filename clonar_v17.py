#!/usr/bin/env python3
"""Clona os 30 projetos novos da §A5 (v1.6) e detecta branch principal + SHA do HEAD.

Para projetos já clonados (Hystrix, archaius, ribbon, zuul), apenas atualiza
(git fetch) e re-detecta o estado atual.

Saída:
- CSV: scripts-tcc/clones_v17.csv com colunas prontas para append em
  projetos-tcc-dataset-3.csv (id, nome, empresa, arquetipo, status, url,
  tag, commit_sha, data_commit, branch_principal, snapshot_type, subconjunto)
- Log: scripts-tcc/clones_v17.log
"""
from __future__ import annotations

import csv
import logging
import subprocess
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path("/home/mateus/Documentos/artigos-tcc/repos/tcc")
SCRIPTS_DIR = BASE_DIR / "scripts-tcc"
CLONES_DIR = BASE_DIR / "projetos-clonados"
OUT_CSV = SCRIPTS_DIR / "clones_v17.csv"
LOG_PATH = SCRIPTS_DIR / "clones_v17.log"

# Lista §A5 do adendo v1.6 (30 projetos)
# Numeração dos ids segue sequência do projetos-tcc-dataset-3.csv atual:
# - apache: continua de 14 → 15-24
# - google: continua de 11 (j2objc-11 excluído) → 12-21
# - netflix: continua de 06 → 07-12 (mas com hystrix/ribbon/archaius/zuul intercalados)
# - linkedin: continua de 03 → 04-05
# - uber: continua de 05 (cadence-05) → 06-07

# Estrutura: (id, repo_full_name, nome_dir, empresa, arquetipo)
# nome_dir é como aparece em projetos-clonados/ (case-sensitive)
PROJETOS_V17 = [
    # Apache (+10)
    ("apache-skywalking-15",        "apache/skywalking",                "skywalking",                "Apache",   "apache"),
    ("apache-rocketmq-16",          "apache/rocketmq",                  "rocketmq",                  "Apache",   "apache"),
    ("apache-shardingsphere-17",    "apache/shardingsphere",            "shardingsphere",            "Apache",   "apache"),
    ("apache-incubator-seata-18", "apache/incubator-seata", "incubator-seata", "Apache", "apache"),
    ("apache-shenyu-19", "apache/shenyu", "shenyu", "Apache", "apache"),
    ("apache-dolphinscheduler-20",  "apache/dolphinscheduler",          "dolphinscheduler",          "Apache",   "apache"),
    ("apache-druid-21",             "apache/druid",                     "druid",                     "Apache",   "apache"),
    ("apache-jmeter-22",            "apache/jmeter",                    "jmeter",                    "Apache",   "apache"),
    ("apache-seatunnel-23",         "apache/seatunnel",                 "seatunnel",                 "Apache",   "apache"),
    ("apache-iceberg-24",           "apache/iceberg",                   "iceberg",                   "Apache",   "apache"),
    # Google (+10)
    ("google-bazel-12",             "bazelbuild/bazel",                 "bazel",                     "Google",   "google"),
    ("google-guice-13",             "google/guice",                     "guice",                     "Google",   "google"),
    ("google-tsunami-14",           "google/tsunami-security-scanner",  "tsunami-security-scanner",  "Google",   "google"),
    ("google-google-java-format-15","google/google-java-format",        "google-java-format",        "Google",   "google"),
    ("google-java-docs-samples-16", "GoogleCloudPlatform/java-docs-samples", "java-docs-samples", "Google", "google"),
    ("google-flogger-17", "google/flogger", "flogger", "Google", "google"),
    ("google-j2cl-18", "google/j2cl", "j2cl", "Google", "google"),
    ("google-copybara-19",          "google/copybara",                  "copybara",                  "Google",   "google"),
    ("google-jimfs-20",             "google/jimfs",                     "jimfs",                     "Google",   "google"),
    ("google-dataflow-templates-21", "GoogleCloudPlatform/DataflowTemplates", "dataflow-templates", "Google", "google"),
    # Descentralizado (+10)
    ("netflix-hystrix-07",          "Netflix/Hystrix",                  "Hystrix",                   "Netflix",  "descentralizado"),
    ("netflix-zuul-08",             "Netflix/zuul",                     "zuul",                      "Netflix",  "descentralizado"),
    ("netflix-ribbon-09",           "Netflix/ribbon",                   "ribbon",                    "Netflix",  "descentralizado"),
    ("netflix-priam-10", "Netflix/Priam", "Priam", "Netflix", "descentralizado"),
    ("netflix-archaius-11",         "Netflix/archaius",                 "archaius",                  "Netflix",  "descentralizado"),
    ("netflix-genie-12",            "Netflix/genie",                    "genie",                     "Netflix",  "descentralizado"),
    ("linkedin-dexmaker-04",        "linkedin/dexmaker",                "dexmaker",                  "LinkedIn", "descentralizado"),
    ("linkedin-parseq-05",          "linkedin/parseq",                  "parseq",                    "LinkedIn", "descentralizado"),
    ("uber-autodispose-06",         "uber/AutoDispose",                 "AutoDispose",               "Uber",     "descentralizado"),
    ("uber-okbuck-07",              "uber/okbuck",                      "okbuck",                    "Uber",     "descentralizado"),
]


def setup_logger() -> logging.Logger:
    logger = logging.getLogger("clones_v17")
    logger.handlers.clear()
    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s",
                            datefmt="%Y-%m-%d %H:%M:%S")
    fh = logging.FileHandler(LOG_PATH, mode="w", encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    logger.addHandler(sh)
    return logger


def run(cmd: list[str], cwd: Path | None = None,
        capture: bool = False, timeout: int = 600) -> subprocess.CompletedProcess:
    """Wrapper de subprocess.run com timeout e cwd opcional."""
    return subprocess.run(
        cmd, cwd=str(cwd) if cwd else None,
        capture_output=capture, text=True,
        timeout=timeout, check=False,
    )


def clonar_ou_atualizar(repo_full: str, nome_dir: str,
                        logger: logging.Logger) -> bool:
    """Clona se não existe; faz fetch se já existe. Retorna True se OK."""
    destino = CLONES_DIR / nome_dir
    if destino.is_dir() and (destino / ".git").is_dir():
        logger.info("[%s] já clonado, fazendo fetch...", nome_dir)
        r = run(["git", "fetch", "origin", "--quiet"], cwd=destino, timeout=300)
        if r.returncode != 0:
            logger.warning("[%s] git fetch retornou rc=%d", nome_dir, r.returncode)
            return False
        return True
    logger.info("[%s] clonando https://github.com/%s.git ...", nome_dir, repo_full)
    url = f"https://github.com/{repo_full}.git"
    r = run(["git", "clone", url, str(destino)], timeout=1800)
    if r.returncode != 0:
        logger.error("[%s] git clone falhou (rc=%d)", nome_dir, r.returncode)
        return False
    return True


def detectar_branch_principal(repo: Path, logger: logging.Logger) -> str | None:
    """Implementa A12 do protocolo: symbolic-ref + fallback main/master."""
    r = run(["git", "symbolic-ref", "--short", "refs/remotes/origin/HEAD"],
            cwd=repo, capture=True)
    if r.returncode == 0:
        ref = r.stdout.strip()
        if ref.startswith("origin/"):
            return ref[len("origin/"):]
        return ref
    # fallback: existe main ou master?
    for cand in ("main", "master"):
        r = run(["git", "show-ref", "--verify", "--quiet",
                 f"refs/remotes/origin/{cand}"], cwd=repo)
        if r.returncode == 0:
            logger.warning("[%s] symbolic-ref falhou, fallback para '%s'",
                           repo.name, cand)
            return cand
    logger.error("[%s] branch principal indeterminado", repo.name)
    return None


def head_de_branch(repo: Path, branch: str) -> tuple[str | None, str | None]:
    """Retorna (sha_completo, data_iso) do HEAD do branch remoto. None se falhar."""
    r = run(["git", "rev-parse", f"origin/{branch}"], cwd=repo, capture=True)
    if r.returncode != 0:
        return None, None
    sha = r.stdout.strip()
    r = run(["git", "log", "-1", "--format=%cI", sha], cwd=repo, capture=True)
    if r.returncode != 0:
        return sha, None
    data_iso = r.stdout.strip()
    # extrair apenas YYYY-MM-DD
    return sha, data_iso[:10] if data_iso else None


def processar_um(entry: tuple, logger: logging.Logger) -> dict | None:
    pid, repo_full, nome_dir, empresa, arquetipo = entry
    if not clonar_ou_atualizar(repo_full, nome_dir, logger):
        return None
    repo = CLONES_DIR / nome_dir
    branch = detectar_branch_principal(repo, logger)
    if not branch:
        return None
    sha, data_commit = head_de_branch(repo, branch)
    if not sha:
        logger.error("[%s] não conseguiu ler SHA do HEAD origin/%s",
                     nome_dir, branch)
        return None
    data_coleta = datetime.now().strftime("%Y-%m-%d")
    marcador_tag = f"HEAD-on-{branch}-{data_coleta}"
    logger.info("[%s] branch=%s sha=%s data_commit=%s",
                nome_dir, branch, sha[:7], data_commit)
    return {
        "id": pid,
        "nome": nome_dir,
        "empresa": empresa,
        "arquetipo": arquetipo,
        "status": "ativo",
        "url": f"https://github.com/{repo_full}",
        "tag": marcador_tag,
        "commit_sha": sha,
        "data_commit": data_commit or "",
        "branch_principal": branch,
        "snapshot_type": "head-of-main",
        "subconjunto": "n30-v1.6",
    }


def main() -> int:
    logger = setup_logger()
    logger.info("=== clonar_e_detectar_v17 — %d projetos ===", len(PROJETOS_V17))

    CLONES_DIR.mkdir(parents=True, exist_ok=True)

    sucesso: list[dict] = []
    falhas: list[str] = []

    for i, entry in enumerate(PROJETOS_V17, 1):
        pid = entry[0]
        logger.info("[%d/%d] %s", i, len(PROJETOS_V17), pid)
        try:
            out = processar_um(entry, logger)
        except subprocess.TimeoutExpired as e:
            logger.error("[%s] TIMEOUT: %s", pid, e)
            out = None
        except Exception as e:
            logger.exception("[%s] erro inesperado: %s", pid, e)
            out = None
        if out is None:
            falhas.append(pid)
        else:
            sucesso.append(out)

    # escreve CSV
    cols = ["id", "nome", "empresa", "arquetipo", "status", "url",
            "tag", "commit_sha", "data_commit",
            "branch_principal", "snapshot_type", "subconjunto"]
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for row in sucesso:
            w.writerow(row)

    logger.info("=" * 60)
    logger.info("RESUMO: %d sucesso, %d falhas", len(sucesso), len(falhas))
    if falhas:
        logger.warning("Falhas: %s", ", ".join(falhas))
    logger.info("CSV: %s", OUT_CSV)
    return 0 if not falhas else 2


if __name__ == "__main__":
    sys.exit(main())