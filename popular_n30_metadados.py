#!/usr/bin/env python3
from __future__ import annotations

import csv
import os
import re
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import dotenv_values

from coleta_lib.io_utils import get_clones_dir, get_repo_root, get_scripts_dir

BASE = get_repo_root()
CONSOL = BASE / "dados" / "n60-analise" / "consolidado.csv"
DATASET4 = get_scripts_dir() / "projetos-tcc-dataset-4.csv"
CLONES = get_clones_dir()
ENV = get_scripts_dir() / ".env"

DATA_CORTE = datetime(2026, 1, 1, tzinfo=timezone.utc)

CODE_EXTS = {".java", ".kt", ".kts", ".scala", ".groovy", ".gradle",
             ".js", ".ts", ".jsx", ".tsx", ".py", ".rb", ".go",
             ".c", ".h", ".cpp", ".hpp", ".cc", ".cs", ".rs",
             ".sh", ".bash", ".pl", ".sql", ".xml", ".yaml", ".yml",
             ".json", ".html", ".css", ".scss", ".less"}

EXCLUDE_DIR_PARTS = {"build", "target", "out", "node_modules", ".git",
                     "bazel-bin", "bazel-out", "bazel-testlogs",
                     ".gradle", ".scannerwork", ".idea", "dist", ".cache"}

def carregar_token() -> str:
    if not ENV.exists():
        raise SystemExit(f"{ENV} ausente")
    vals = dotenv_values(ENV)
    tok = (vals.get("GITHUB_TOKEN") or "").strip().strip('"').strip("'")
    if not tok:
        raise SystemExit("GITHUB_TOKEN ausente no .env")
    return tok

def gh(path: str, token: str, params: dict | None = None,
       ) -> requests.Response | None:
    url = f"https://api.github.com{path}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    for attempt in range(3):
        try:
            return requests.get(url, headers=headers, params=params or {},
                                timeout=30)
        except requests.RequestException as e:
            if attempt < 2:
                time.sleep(2 ** attempt)
            else:
                print(f"  rede falhou {url}: {e}", file=sys.stderr)
    return None

def parse_last_page(link_header: str | None) -> int | None:
    if not link_header:
        return None
    for parte in link_header.split(","):
        if 'rel="last"' in parte:
            url = parte.strip().split(";")[0].strip().strip("<>")
            for kv in url.split("?", 1)[-1].split("&"):
                if kv.startswith("page="):
                    try:
                        return int(kv[5:])
                    except ValueError:
                        return None
    return None

def github_metadados(owner_repo: str, token: str
                     ) -> tuple[float | None, int | None]:
    r = gh(f"/repos/{owner_repo}", token)
    idade = None
    if r is not None and r.status_code == 200:
        try:
            created = r.json().get("created_at", "")
            dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
            idade = round((DATA_CORTE - dt).days / 365.25, 1)
        except (ValueError, TypeError):
            pass
    time.sleep(0.25)

    r = gh(f"/repos/{owner_repo}/contributors", token,
           params={"per_page": 1, "anon": 1})
    contribs = None
    if r is not None and r.status_code == 200:
        last = parse_last_page(r.headers.get("Link"))
        if last is not None:
            contribs = last
        else:
            try:
                data = r.json()
                contribs = len(data) if isinstance(data, list) else 0
            except ValueError:
                pass
    time.sleep(0.25)

    return idade, contribs

def is_excluded_dir(path: Path) -> bool:
    return any(p in EXCLUDE_DIR_PARTS for p in path.parts)

def cloc_local(repo_dir: Path) -> int | None:
    if not repo_dir.is_dir():
        return None
    total = 0
    for path in repo_dir.rglob("*"):
        if not path.is_file():
            continue
        if is_excluded_dir(path.relative_to(repo_dir)):
            continue
        if path.suffix.lower() not in CODE_EXTS:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except (OSError, UnicodeDecodeError):
            continue
        text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
        for line in text.splitlines():
            s = line.strip()
            if not s:
                continue
            if (s.startswith("//") or s.startswith("#")
                    or s.startswith(";") or s.startswith("--")):
                continue
            if s.startswith("*") and not s.startswith("*/"):
                continue
            total += 1
    return total

def carregar_urls() -> dict[str, str]:
    out: dict[str, str] = {}
    with DATASET4.open() as f:
        for r in csv.DictReader(f):
            url = (r.get("url") or "").strip()
            if url:
                out[r["id"]] = url
    return out

def carregar_nomes_dir() -> dict[str, str]:
    out: dict[str, str] = {}
    with DATASET4.open() as f:
        for r in csv.DictReader(f):
            out[r["id"]] = (r.get("nome") or "").strip()
    return out

def url_para_owner_repo(url: str) -> str | None:
    if "github.com/" not in url:
        return None
    parte = url.split("github.com/", 1)[1].rstrip("/")
    if parte.endswith(".git"):
        parte = parte[:-4]
    return parte

def main() -> int:
    token = carregar_token()
    urls = carregar_urls()
    nomes = carregar_nomes_dir()

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    bak = CONSOL.with_name(f"{CONSOL.name}.bak-popular-{ts}")
    shutil.copy2(CONSOL, bak)
    print(f"backup: {bak.name}")

    with CONSOL.open() as f:
        reader = csv.DictReader(f)
        cols = list(reader.fieldnames or [])
        rows = list(reader)

    alvos = [r for r in rows
             if r["subconjunto"] == "n30-v1.6" and not r["idade_anos"]]
    print(f"populando {len(alvos)}/{len(rows)} linhas (n30-v1.6, sem idade)")
    print()

    sucessos = 0
    for i, row in enumerate(alvos, 1):
        pid = row["id"]
        url = urls.get(pid, "")
        nome_dir = nomes.get(pid, "")
        owner_repo = url_para_owner_repo(url) if url else None
        if not owner_repo:
            print(f"  [{i}/{len(alvos)}] {pid}: sem url válido — pulando")
            continue

        idade, contribs = github_metadados(owner_repo, token)
        repo_dir = CLONES / nome_dir if nome_dir else None
        loc = cloc_local(repo_dir) if repo_dir else None

        if idade is not None:
            row["idade_anos"] = idade
        if contribs is not None:
            row["contribuidores"] = contribs
        if loc is not None:
            row["loc_total"] = loc

        marca = ("✓" if (idade is not None and contribs is not None
                         and loc is not None) else "~")
        print(f"  [{i}/{len(alvos)}] {marca} {pid:35s} "
              f"idade={idade} contribs={contribs} loc_total={loc}")
        if (idade is not None and contribs is not None
                and loc is not None):
            sucessos += 1

    tmp = CONSOL.with_suffix(CONSOL.suffix + ".tmp")
    with tmp.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in cols})
    os.replace(tmp, CONSOL)

    print()
    print(f"=== concluído: {sucessos}/{len(alvos)} totalmente populados ===")
    print(f"consolidado: {CONSOL}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
