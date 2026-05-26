#!/usr/bin/env python3
"""Valida candidatos de candidatos_expansao_v1.6.csv contra os 6 critérios
objetivos do protocolo (§A5 / seleção amostral).

Critérios (do protocolo):
  C1. Linguagem: >= 70% Java via endpoint /languages (bytes).
  C2. Tamanho: 10k <= NCLOC <= 1M (aproximação: tamanho Java em bytes / 30,
      sendo 30 ~ média de bytes-por-linha Java; serve como heurística).
  C3. Idade: >= 3 anos entre o primeiro commit e 2026-01-01
      (aproximação: usa created_at do repo).
  C4. Contribuidores: >= 25 distintos (via Link rel=last no /contributors).
  C5. Release: >= 1 tag estável (não prerelease/draft) com published_at
      anterior a 2026-01-01.
  C6. Build: Maven OU Gradle na raiz (presença de pom.xml, build.gradle,
      build.gradle.kts ou settings.gradle). Bazel-only é REPROVADO; outros
      sistemas (sbt, make, etc.) também. Verificado via /contents/ na raiz.

Limitações conhecidas:
  - NCLOC é estimado por bytes_Java/30 (heurística — pode errar perto dos
    limites de 10k/1M, mas confiável fora deles).
  - Idade usa created_at do repo; repos importados/migrados podem ter
    created_at posterior ao primeiro commit real.
  - Contribuidores via Link rel=last vai até 500 (limite da API); para o
    threshold >=25 não afeta, mas o número exato fica subestimado.
  - C6 só checa presença de arquivo na raiz: monorepos com pom.xml em
    subdiretórios podem dar falso-negativo.

Uso:
  python3 validar_candidatos_v17.py [csv_entrada [csv_saida]]
  Defaults: candidatos_expansao_v1.6.csv → validacao_candidatos_v17.csv
"""
from __future__ import annotations

import csv
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import dotenv_values

SCRIPTS_DIR = Path(__file__).resolve().parent
ENV_PATH = SCRIPTS_DIR / ".env"
IN_CSV = SCRIPTS_DIR / "candidatos_expansao_v1.6.csv"
CLONES_CSV = SCRIPTS_DIR / "clones_v17.csv"
OUT_CSV = SCRIPTS_DIR / "validacao_candidatos_v17.csv"
LOG_PATH = SCRIPTS_DIR / "validacao_candidatos_v17.log"

GITHUB_API = "https://api.github.com"
SLEEP_ENTRE_REQUESTS = 0.3
RATE_LIMIT_MINIMO = 100

# Limites do protocolo
MIN_JAVA_PCT = 70.0
MIN_NCLOC = 10_000
MAX_NCLOC = 1_000_000
MIN_IDADE_ANOS = 3.0
MIN_CONTRIBUIDORES = 25
DATA_CORTE = datetime(2026, 1, 1, tzinfo=timezone.utc)
BYTES_POR_LINHA_JAVA = 30  # heurística para estimar NCLOC

OUT_COLS = [
    "arquetipo", "full_name", "stars", "size_kb",
    "java_pct", "java_bytes", "ncloc_est",
    "created_at", "idade_anos",
    "contribuidores", "release_estavel_pre_2026",
    "build_tool",
    "c1_lang", "c2_size", "c3_idade", "c4_contribs", "c5_release", "c6_build",
    "aprovado", "ja_na_v17", "observacao",
]

BUILD_FILES: list[tuple[str, str]] = [
    ("pom.xml", "maven"),
    ("build.gradle", "gradle"),
    ("build.gradle.kts", "gradle"),
    ("settings.gradle", "gradle"),
    ("settings.gradle.kts", "gradle"),
    ("BUILD", "bazel"),
    ("BUILD.bazel", "bazel"),
    ("WORKSPACE", "bazel"),
    ("WORKSPACE.bazel", "bazel"),
    ("MODULE.bazel", "bazel"),
]


def setup_logger() -> logging.Logger:
    logger = logging.getLogger("validar_v17")
    logger.handlers.clear()
    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s",
                            datefmt="%Y-%m-%d %H:%M:%S")
    fh = logging.FileHandler(LOG_PATH, mode="w", encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    sh = logging.StreamHandler(sys.stdout)
    sh.setLevel(logging.INFO)
    sh.setFormatter(fmt)
    logger.addHandler(sh)
    return logger


def carregar_token() -> str:
    valores = dotenv_values(ENV_PATH) if ENV_PATH.exists() else {}
    token = (valores.get("GITHUB_TOKEN") or "").strip().strip('"').strip("'")
    if not token:
        raise SystemExit("GITHUB_TOKEN ausente em scripts-tcc/.env")
    return token


def ja_no_v17() -> set[str]:
    """Conjunto de URLs (lower) dos repos já presentes em clones_v17.csv."""
    if not CLONES_CSV.exists():
        return set()
    out: set[str] = set()
    with CLONES_CSV.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            url = (row.get("url") or "").strip().lower()
            if url:
                # normaliza p/ comparar com html_url do candidatos
                out.add(url.rstrip("/"))
    return out


def gh_get(caminho: str, params: dict, token: str,
           logger: logging.Logger) -> requests.Response | None:
    """GET autenticado com retry simples (3 tentativas). Retorna None em erro."""
    url = f"{GITHUB_API}{caminho}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    for tentativa in range(1, 4):
        try:
            resp = requests.get(url, headers=headers, params=params, timeout=30)
            # checa rate limit
            rl = resp.headers.get("X-RateLimit-Remaining")
            if rl is not None and int(rl) < RATE_LIMIT_MINIMO:
                logger.warning("rate limit baixo (%s) — parando", rl)
                raise SystemExit(2)
            return resp
        except requests.RequestException as e:
            espera = 2 ** tentativa
            logger.warning("rede falhou em %s (%s) — retry em %ds",
                           url, e, espera)
            time.sleep(espera)
    logger.error("falhou 3x em %s", url)
    return None


def parse_last_page(link_header: str | None) -> int | None:
    """Extrai o número da última página do header Link do GitHub."""
    if not link_header:
        return None
    # formato: <https://...&page=42>; rel="last", <...>; rel="next"
    for parte in link_header.split(","):
        if 'rel="last"' in parte:
            url = parte.strip().split(";")[0].strip().strip("<>")
            # extrai page=N
            for kv in url.split("?", 1)[-1].split("&"):
                if kv.startswith("page="):
                    try:
                        return int(kv[5:])
                    except ValueError:
                        return None
    return None


def checar_linguagem(full_name: str, token: str,
                     logger: logging.Logger) -> tuple[float, int]:
    """Retorna (java_pct, java_bytes). (0, 0) se falhar."""
    resp = gh_get(f"/repos/{full_name}/languages", {}, token, logger)
    if resp is None or resp.status_code != 200:
        return 0.0, 0
    try:
        data = resp.json()
    except ValueError:
        return 0.0, 0
    total = sum(data.values()) or 1
    java = data.get("Java", 0)
    return java * 100.0 / total, java


def checar_contribuidores(full_name: str, token: str,
                          logger: logging.Logger) -> int:
    """Retorna número de contribuidores (inclui anônimos). 0 se falhar."""
    resp = gh_get(f"/repos/{full_name}/contributors",
                  {"per_page": 1, "anon": 1}, token, logger)
    if resp is None or resp.status_code != 200:
        return 0
    last = parse_last_page(resp.headers.get("Link"))
    if last is not None:
        return last
    # sem header Link → 0 ou 1 contribuidor
    try:
        data = resp.json()
        return len(data) if isinstance(data, list) else 0
    except ValueError:
        return 0


def checar_repo(full_name: str, token: str,
                logger: logging.Logger) -> tuple[str, float]:
    """Retorna (created_at_iso, idade_em_anos). ('', 0) se falhar."""
    resp = gh_get(f"/repos/{full_name}", {}, token, logger)
    if resp is None or resp.status_code != 200:
        return "", 0.0
    try:
        data = resp.json()
    except ValueError:
        return "", 0.0
    created = data.get("created_at", "")
    if not created:
        return "", 0.0
    try:
        dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
    except ValueError:
        return created, 0.0
    delta = DATA_CORTE - dt
    return created, delta.days / 365.25


def checar_release_estavel(full_name: str, token: str,
                           logger: logging.Logger) -> bool:
    """True se houver release não-prerelease/não-draft published_at < 2026-01-01."""
    resp = gh_get(f"/repos/{full_name}/releases",
                  {"per_page": 30}, token, logger)
    if resp is None or resp.status_code != 200:
        return False
    try:
        data = resp.json()
    except ValueError:
        return False
    if not isinstance(data, list):
        return False
    for rel in data:
        if rel.get("draft") or rel.get("prerelease"):
            continue
        pub = rel.get("published_at") or ""
        if not pub:
            continue
        try:
            dt = datetime.fromisoformat(pub.replace("Z", "+00:00"))
        except ValueError:
            continue
        if dt < DATA_CORTE:
            return True
    return False


def checar_build_tool(full_name: str, token: str,
                      logger: logging.Logger) -> str:
    """Identifica build system pela presença de arquivo na raiz.

    Ordem de prioridade: maven > gradle > bazel > outro. Se ambos maven
    e gradle existirem, retorna 'maven+gradle'. Bazel só é reportado se
    nenhum dos dois principais estiver presente.
    """
    encontrados: set[str] = set()
    for path, tipo in BUILD_FILES:
        resp = gh_get(f"/repos/{full_name}/contents/{path}", {}, token, logger)
        if resp is not None and resp.status_code == 200:
            encontrados.add(tipo)
        time.sleep(0.1)
    if "maven" in encontrados and "gradle" in encontrados:
        return "maven+gradle"
    if "maven" in encontrados:
        return "maven"
    if "gradle" in encontrados:
        return "gradle"
    if "bazel" in encontrados:
        return "bazel"
    return "outro"


def validar(row: dict, token: str, ja_clonados: set[str],
            logger: logging.Logger) -> dict:
    full = row["full_name"]
    logger.info("validando %s ...", full)

    java_pct, java_bytes = checar_linguagem(full, token, logger)
    time.sleep(SLEEP_ENTRE_REQUESTS)
    contribs = checar_contribuidores(full, token, logger)
    time.sleep(SLEEP_ENTRE_REQUESTS)
    created, idade = checar_repo(full, token, logger)
    time.sleep(SLEEP_ENTRE_REQUESTS)
    release_ok = checar_release_estavel(full, token, logger)
    time.sleep(SLEEP_ENTRE_REQUESTS)
    build_tool = checar_build_tool(full, token, logger)
    time.sleep(SLEEP_ENTRE_REQUESTS)

    ncloc_est = java_bytes // BYTES_POR_LINHA_JAVA

    c1 = java_pct >= MIN_JAVA_PCT
    c2 = MIN_NCLOC <= ncloc_est <= MAX_NCLOC
    c3 = idade >= MIN_IDADE_ANOS
    c4 = contribs >= MIN_CONTRIBUIDORES
    c5 = release_ok
    c6 = build_tool in ("maven", "gradle", "maven+gradle")

    aprovado = all([c1, c2, c3, c4, c5, c6])
    url_norm = (row.get("html_url") or "").strip().lower().rstrip("/")
    ja_v17 = url_norm in ja_clonados

    return {
        "arquetipo": row["arquetipo"],
        "full_name": full,
        "stars": row.get("stars", ""),
        "size_kb": row.get("size_kb", ""),
        "java_pct": f"{java_pct:.1f}",
        "java_bytes": java_bytes,
        "ncloc_est": ncloc_est,
        "created_at": created,
        "idade_anos": f"{idade:.1f}",
        "contribuidores": contribs,
        "release_estavel_pre_2026": "sim" if release_ok else "nao",
        "build_tool": build_tool,
        "c1_lang": "ok" if c1 else "FAIL",
        "c2_size": "ok" if c2 else "FAIL",
        "c3_idade": "ok" if c3 else "FAIL",
        "c4_contribs": "ok" if c4 else "FAIL",
        "c5_release": "ok" if c5 else "FAIL",
        "c6_build": "ok" if c6 else "FAIL",
        "aprovado": "sim" if aprovado else "nao",
        "ja_na_v17": "sim" if ja_v17 else "nao",
        "observacao": "",
    }


def imprimir_resumo(resultados: list[dict], logger: logging.Logger) -> None:
    logger.info("=" * 70)
    logger.info("RESUMO POR ARQUÉTIPO (apenas APROVADOS e NÃO já em v17)")
    logger.info("=" * 70)
    por_arq: dict[str, list[dict]] = {}
    for r in resultados:
        por_arq.setdefault(r["arquetipo"], []).append(r)
    for arq in sorted(por_arq):
        candidatos = [r for r in por_arq[arq]
                      if r["aprovado"] == "sim" and r["ja_na_v17"] == "nao"]
        # ordena por stars desc
        candidatos.sort(key=lambda r: int(r.get("stars") or 0), reverse=True)
        logger.info("[%s] %d aprovados disponíveis (não-v17):",
                    arq, len(candidatos))
        for r in candidatos[:15]:
            logger.info("  %-50s stars=%5s java=%5s%% ncloc≈%7d contribs=%4d",
                        r["full_name"], r["stars"], r["java_pct"],
                        r["ncloc_est"], r["contribuidores"])


def main() -> int:
    logger = setup_logger()
    token = carregar_token()
    ja_clonados = ja_no_v17()
    logger.info("já em v17: %d repos", len(ja_clonados))

    in_csv = Path(sys.argv[1]) if len(sys.argv) > 1 else IN_CSV
    out_csv = Path(sys.argv[2]) if len(sys.argv) > 2 else OUT_CSV
    logger.info("entrada: %s", in_csv)
    logger.info("saída:   %s", out_csv)

    if not in_csv.exists():
        logger.error("não encontrei %s", in_csv)
        return 1

    with in_csv.open(encoding="utf-8") as f:
        candidatos = list(csv.DictReader(f))

    logger.info("validando %d candidatos contra 6 critérios objetivos...",
                len(candidatos))

    resultados: list[dict] = []
    for i, row in enumerate(candidatos, 1):
        try:
            res = validar(row, token, ja_clonados, logger)
        except SystemExit:
            raise
        except Exception as e:
            logger.exception("erro em %s: %s", row.get("full_name"), e)
            continue
        resultados.append(res)
        if i % 10 == 0:
            logger.info("progresso: %d/%d", i, len(candidatos))

    with out_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=OUT_COLS)
        w.writeheader()
        for r in resultados:
            w.writerow(r)

    logger.info("CSV: %s", out_csv)
    imprimir_resumo(resultados, logger)
    return 0


if __name__ == "__main__":
    sys.exit(main())
