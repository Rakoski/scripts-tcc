from __future__ import annotations

import csv
import hashlib
import logging
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Iterable

import requests

def get_scripts_dir() -> Path:
    return Path(__file__).resolve().parent.parent

def get_repo_root() -> Path:
    return get_scripts_dir().parent

def get_clones_dir() -> Path:
    return get_repo_root() / "projetos-clonados"

def get_dados_dir() -> Path:
    return get_repo_root() / "dados"

ARQUETIPOS_VALIDOS = {"apache", "google", "descentralizado"}

N_AMOSTRA = 60

PROJETOS_EXCLUIDOS_LIMITACAO_TECNICA: dict[str, str] = {
    "google-j2objc-11": (
        "Build exige macOS (xcodebuild, xcrun, Xcode). "
        "Incompatível com Linux Debian 12."
    ),

    "apache-hadoop-18": (
        "Violação §3.1.2 (C2): NCLOC Sonar 1.028.933 > 1.000.000. "
        "Excluído pela §A17 do adendo v1.8."
    ),
    "apache-doris-19": (
        "Violação §3.1.1 (C1): 48.1% Java < 70%. "
        "Excluído pela §A17 do adendo v1.8."
    ),
    "google-open-location-code-16": (
        "Violação §3.1.1 (C1): 22.2% Java < 70%. "
        "Excluído pela §A17 do adendo v1.8."
    ),
    "google-bundletool-17": (
        "Violação §3.1.4 (C4): 22 contribuidores < 25. "
        "Excluído pela §A17 do adendo v1.8."
    ),
    "google-bindiff-18": (
        "Violação §3.1.3 (C3): 2.3 anos < 3 anos. "
        "Excluído pela §A17 do adendo v1.8."
    ),
    "google-firebase-android-sdk-21": (
        "Violação §3.1.1 (C1): 44.7% Java < 70%. "
        "Excluído pela §A17 do adendo v1.8."
    ),
    "netflix-maestro-10": (
        "Violação §3.1.3 (C3): 1.7 anos < 3 anos; "
        "§3.1.4 (C4): 12 contribuidores < 25. "
        "Excluído pela §A17 do adendo v1.8."
    ),
    "netflix-servo-10": (
        "Violação §3.1.2 detectada pós-coleta: NCLOC Sonar=9233 < 10000 "
        "(-7.7%). Excluído pela §A23 do adendo v1.9, substituído por "
        "Netflix/Priam."
    ),

    "google-bazel-12": (
        "Bazel meta-build (recursos): travou PC em primeira tentativa. "
        "Deferred para pós-banca. Excluído pela §A29 do adendo v1.10."
    ),
    "google-google-java-format-15": (
        "Maven Tycho 5.0.2: ProvisionException no "
        "TargetPlatformWorkspaceReader, mesmo no pom raiz. "
        "Excluído pela §A29 do adendo v1.10."
    ),
    "google-java-docs-samples-16": (
        "Monorepo Gradle: samples independentes sem build unificado na raiz. "
        "Excluído pela §A29 do adendo v1.10."
    ),
    "linkedin-dexmaker-04": (
        "NDK Android 27.0.12077973 corrompido (sem source.properties). "
        "Excluído pela §A29 do adendo v1.10."
    ),
}

class ColetaError(RuntimeError):
    pass

class ProjetoError(RuntimeError):
    pass

def carregar_env(path: Path) -> dict[str, str]:
    if not path.exists():
        raise ColetaError(f".env não encontrado: {path}")
    out: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            if line.startswith(("squ_", "sqa_", "sqp_")):
                out.setdefault("SONAR_TOKEN", line)
            continue
        k, _, v = line.partition("=")
        v = v.strip().strip('"').strip("'")
        out[k.strip()] = v
    out.setdefault("SONAR_URL", os.environ.get("SONAR_URL", "http://localhost:9000"))
    if "SONAR_TOKEN" not in out:
        env_tok = os.environ.get("SONAR_TOKEN")
        if env_tok:
            out["SONAR_TOKEN"] = env_tok
    if "SONAR_TOKEN" not in out:
        raise ColetaError("SONAR_TOKEN não definido em .env nem no ambiente")
    if "DATA_COLETA" not in out:
        env_data = os.environ.get("DATA_COLETA")
        if env_data:
            out["DATA_COLETA"] = env_data
    return out

def mask_token(t: str) -> str:
    if not t or len(t) < 12:
        return "<token>"
    return t[:6] + "…" + t[-4:]

def setup_logger(log_path: Path) -> logging.Logger:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("coleta")
    logger.handlers.clear()
    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    fh = logging.FileHandler(log_path, mode="a", encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    sh = logging.StreamHandler(sys.stdout)
    sh.setLevel(logging.INFO)
    sh.setFormatter(fmt)
    logger.addHandler(sh)
    return logger

def carregar_planilha(csv_path: Path, logger: logging.Logger) -> list[dict]:
    if not csv_path.exists():
        raise ColetaError(f"Planilha não encontrada: {csv_path}")
    candidatos: list[dict] = []
    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            arq = (r.get("arquetipo") or "").strip().lower()
            if arq not in ARQUETIPOS_VALIDOS:
                continue
            candidatos.append(r)

    rows: list[dict] = []
    for r in candidatos:
        pid = (r.get("id") or "").strip()
        motivo = PROJETOS_EXCLUIDOS_LIMITACAO_TECNICA.get(pid)
        if motivo:
            logger.info("[EXCLUSAO] %s: %s", pid, motivo)
            continue
        rows.append(r)

    logger.info("Planilha: %d linhas com arquétipo válido (após exclusões técnicas)",
                len(rows))
    if len(rows) != N_AMOSTRA:
        raise ColetaError(
            f"Esperadas {N_AMOSTRA} linhas após exclusões técnicas, encontradas {len(rows)}. "
            f"Exclusões aplicadas: {sorted(PROJETOS_EXCLUIDOS_LIMITACAO_TECNICA)}. "
            f"Confirme planilha contra v1.5 §5.1 antes de coletar."
        )
    return rows

def filtrar_planilha(rows: list[dict], only: str | None, limit: int) -> list[dict]:
    out = rows
    if only:
        out = [r for r in out if r.get("nome") == only or r.get("id") == only]
        if not out:
            raise ColetaError(f"--only {only!r} não casou com nenhuma linha")
    if limit and limit > 0:
        out = out[:limit]
    return out

def derivar_instancia(row: dict) -> str:
    arq = row["arquetipo"]
    if arq != "descentralizado":
        return arq
    empresa = (row.get("empresa") or "").strip().lower()
    return empresa or "desconhecida"

class SonarClient:

    def __init__(self, url: str, token: str, logger: logging.Logger):
        self.url = url.rstrip("/")
        self.token = token
        self.logger = logger
        self.session = requests.Session()
        self.session.auth = (token, "")

    def _request(self, method: str, path: str, **kwargs):
        max_retries = 3
        backoff = 1.0
        for attempt in range(1, max_retries + 1):
            try:
                resp = self.session.request(
                    method, self.url + path, timeout=60, **kwargs
                )
            except requests.RequestException as e:
                self.logger.warning("HTTP exception %s (tentativa %d/%d): %s",
                                    path, attempt, max_retries, e)
                if attempt == max_retries:
                    raise
                time.sleep(backoff)
                backoff *= 2
                continue
            if resp.status_code in (401, 403):
                raise ColetaError(
                    f"HTTP {resp.status_code} em {path} — token sem permissão. "
                    f"Abortando (não tenta de novo)."
                )
            if 500 <= resp.status_code < 600:
                self.logger.warning("HTTP %d em %s (tentativa %d/%d)",
                                    resp.status_code, path, attempt, max_retries)
                if attempt == max_retries:
                    return resp
                time.sleep(backoff)
                backoff *= 2
                continue
            return resp
        return resp

    def get(self, path: str, **params):
        return self._request("GET", path, params=params)

    def post(self, path: str, **data):
        return self._request("POST", path, data=data)

    def projeto_existe(self, key: str) -> bool:
        r = self.get(f"/api/measures/component", component=key, metricKeys="ncloc")
        return r.status_code == 200

    def system_status_ok(self) -> bool:
        try:
            r = self._request("GET", "/api/system/status")
            return r.status_code == 200
        except Exception:
            return False

def hash_arquivo(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def dir_dados(base: Path, data_iso: str | None = None) -> Path:
    data = data_iso or datetime.now().strftime("%Y-%m-%d")
    p = base / "dados" / data
    p.mkdir(parents=True, exist_ok=True)
    (p / "issues").mkdir(exist_ok=True)
    return p

def now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
