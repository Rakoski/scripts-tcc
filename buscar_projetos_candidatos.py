#!/usr/bin/env python3
"""Busca de candidatos para expansão amostral do TCC.

OBJETIVO
    Listar repositórios do GitHub que batem critérios objetivos PRÉ-DECLARADOS,
    servindo de base para a curadoria manual da lista de expansão da amostra
    (N=34 → N≈52). O script entrega a lista bruta filtrada; a decisão de quais
    projetos incluir é exclusivamente manual.

CRITÉRIOS OBJETIVOS PRÉ-DECLARADOS (ver CRITERIOS abaixo)
    - linguagem primária Java;
    - >= 1000 stars;
    - atividade nos últimos 12 meses (pushed_at);
    - não arquivado;
    - não fork;
    - tamanho do repo >= 1000 KB (aproxima >5k LOC).
    Nenhum filtro de "facilidade técnica", toolchain ou prioridade subjetiva
    é aplicado — isso é deliberado e metodológico.

EXCLUSÕES
    Duas fontes, unidas num conjunto único (match case-insensitive do nome
    do repo):
      1. projetos já analisados — dados/2026-05-17/consolidado.csv, coluna `nome`;
      2. projetos descartados por limitação técnica de plataforma —
         coleta_lib.io_utils.PROJETOS_EXCLUIDOS_LIMITACAO_TECNICA (ex.: j2objc,
         macOS-only). Esses nunca chegam ao consolidado, mas não devem voltar
         como candidatos: novos projetos podem ter problemas de toolchain
         similares, e mantê-los fora é decisão metodológica pré-declarada.

REGRA DE FAMÍLIAS
    Para evitar sobre-representação de monorepos/famílias (ex.: apache/commons-*,
    googleapis/java-*), mantém no máximo 3 candidatos por (org, família), onde
    família = primeira palavra do nome do repo antes de qualquer hífen.

OUTPUT
    - CSV : scripts-tcc/candidatos_expansao_v1.6.csv
    - Log : scripts-tcc/candidatos_expansao.log
    - Resumo no terminal (totais por arquétipo + top 10 por arquétipo).

AUTENTICAÇÃO
    Token pessoal do GitHub em scripts-tcc/.env, variável GITHUB_TOKEN.
    Crie em https://github.com/settings/tokens com escopo `public_repo`.

COMO RODAR
    python3 buscar_projetos_candidatos.py
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

from coleta_lib.io_utils import PROJETOS_EXCLUIDOS_LIMITACAO_TECNICA

# ---------------- caminhos ----------------

SCRIPTS_DIR = Path(__file__).resolve().parent
BASE_DIR = SCRIPTS_DIR.parent
ENV_PATH = SCRIPTS_DIR / ".env"
CONSOLIDADO_CSV = BASE_DIR / "dados" / "2026-05-17" / "consolidado.csv"
PLANILHA_CSV = SCRIPTS_DIR / "projetos-tcc-dataset-3.csv"
OUT_CSV = SCRIPTS_DIR / "candidatos_expansao_v1.6.csv"
LOG_PATH = SCRIPTS_DIR / "candidatos_expansao.log"

# ---------------- configuração ----------------

ORGS_POR_ARQUETIPO: dict[str, list[str]] = {
    "apache": ["apache"],
    "google": ["google", "googleapis", "bazelbuild", "firebase",
               "androidx", "GoogleCloudPlatform", "google-deepmind"],
    "descentralizado": ["Netflix", "uber", "linkedin", "square"],
}

CRITERIOS = {
    "language": "Java",
    "min_stars": 1000,
    "max_meses_inativo": 12,
    "is_archived": False,
    "is_fork": False,
    "min_size_kb": 1000,  # tamanho do repo em KB, aproxima >5k LOC
}

MAX_POR_FAMILIA = 3
DIAS_POR_MES = 30.44
SLEEP_ENTRE_REQUESTS = 0.5
RATE_LIMIT_MINIMO = 100
GITHUB_API = "https://api.github.com"

OUT_COLS = [
    "arquetipo", "org", "full_name", "repo_name", "stars", "language",
    "size_kb", "ultimo_commit_iso", "html_url", "descricao", "familia",
]


class CandidatosError(RuntimeError):
    """Erro fatal — aborta a busca."""


class RateLimitBaixo(RuntimeError):
    """Rate limit do GitHub abaixo do mínimo seguro — para e salva parcial."""

    def __init__(self, restante: int):
        super().__init__(f"rate limit restante={restante}")
        self.restante = restante


# ---------------- logger ----------------

def setup_logger(log_path: Path) -> logging.Logger:
    logger = logging.getLogger("candidatos")
    logger.handlers.clear()
    logger.setLevel(logging.DEBUG)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s",
                            datefmt="%Y-%m-%d %H:%M:%S")
    fh = logging.FileHandler(log_path, mode="w", encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    sh = logging.StreamHandler(sys.stdout)
    sh.setLevel(logging.INFO)
    sh.setFormatter(fmt)
    logger.addHandler(sh)
    return logger


# ---------------- token / exclusões ----------------

def carregar_token(logger: logging.Logger) -> str:
    valores = dotenv_values(ENV_PATH) if ENV_PATH.exists() else {}
    token = (valores.get("GITHUB_TOKEN") or "").strip().strip('"').strip("'")
    if not token:
        raise CandidatosError(
            "GITHUB_TOKEN ausente em scripts-tcc/.env. Crie um token pessoal "
            "em https://github.com/settings/tokens (escopo `public_repo` "
            "apenas) e adicione a linha GITHUB_TOKEN=<token> ao .env."
        )
    return token


def _carregar_planilha_projetos(path: Path) -> dict[str, dict]:
    """Mapa id -> linha {nome, empresa, ...} da planilha-fonte do TCC.
    Vazio se a planilha não existir (resolução cai no fallback heurístico)."""
    out: dict[str, dict] = {}
    if not path.exists():
        return out
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            pid = (row.get("id") or "").strip()
            if pid:
                out[pid] = row
    return out


# id -> {nome, ...} dos projetos do TCC. Usado para resolver os ids de
# PROJETOS_EXCLUIDOS_LIMITACAO_TECNICA em nomes de repo.
PLANILHA_PROJETOS: dict[str, dict] = _carregar_planilha_projetos(PLANILHA_CSV)


def extrair_nome_de_id(pid: str,
                       planilha: dict[str, dict] | None = None) -> str:
    """Resolve id de projeto do TCC → nome do repositório.

    Primeiro consulta a planilha (id -> {nome}). Se o id não estiver lá,
    fallback heurístico: remove o prefixo '{empresa}-' e o sufixo '-{numero}'.
    Ex.: 'google-j2objc-11' -> 'j2objc';
         'uber-cadence-java-client-05' -> 'cadence-java-client'."""
    if planilha is None:
        planilha = PLANILHA_PROJETOS
    registro = planilha.get(pid)
    if registro and (registro.get("nome") or "").strip():
        return registro["nome"].strip()
    partes = pid.split("-")
    if partes and partes[-1].isdigit():
        partes = partes[:-1]            # remove sufixo -{numero}
    if len(partes) > 1:
        partes = partes[1:]            # remove prefixo {empresa}-
    return "-".join(partes)


def nomes_de_limitacao_tecnica(excluidos_map: dict[str, str] | None = None,
                               planilha: dict[str, dict] | None = None
                               ) -> set[str]:
    """Conjunto de nomes de repo (lowercased) descartados por limitação
    técnica de plataforma, resolvidos via planilha + fallback heurístico."""
    if excluidos_map is None:
        excluidos_map = PROJETOS_EXCLUIDOS_LIMITACAO_TECNICA
    nomes: set[str] = set()
    for pid in excluidos_map:
        nome = extrair_nome_de_id(pid, planilha)
        if nome:
            nomes.add(nome.lower())
    return nomes


def carregar_excluidos(logger: logging.Logger) -> tuple[set[str], int, int]:
    """Conjunto de nomes (lowercased) a excluir dos candidatos, de DUAS fontes:
    consolidado.csv (projetos já analisados) e PROJETOS_EXCLUIDOS_LIMITACAO_
    TECNICA (descartados por toolchain). Retorna (set, n_consolidado, n_tecnica)."""
    if not CONSOLIDADO_CSV.exists():
        raise CandidatosError(f"consolidado.csv não encontrado: {CONSOLIDADO_CSV}")
    nomes_consolidado: set[str] = set()
    with CONSOLIDADO_CSV.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            nome = (row.get("nome") or "").strip()
            if nome:
                nomes_consolidado.add(nome.lower())

    nomes_tecnica = nomes_de_limitacao_tecnica()
    total = nomes_consolidado | nomes_tecnica
    logger.info("%d projetos do consolidado + %d projetos com limitação "
                "técnica = %d exclusões totais",
                len(nomes_consolidado), len(nomes_tecnica), len(total))
    return total, len(nomes_consolidado), len(nomes_tecnica)


# ---------------- funções puras (testáveis) ----------------

def _parse_iso(s: str) -> datetime:
    """Parse de timestamp ISO 8601 do GitHub (ex.: 2025-12-02T10:30:00Z)."""
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def repo_bate_criterios(repo: dict, criterios: dict, agora: datetime) -> bool:
    """True se o repo satisfaz TODOS os critérios objetivos pré-declarados."""
    if (repo.get("language") or "") != criterios["language"]:
        return False
    if (repo.get("stargazers_count") or 0) < criterios["min_stars"]:
        return False
    if bool(repo.get("archived", False)) != criterios["is_archived"]:
        return False
    if bool(repo.get("fork", False)) != criterios["is_fork"]:
        return False
    if (repo.get("size") or 0) < criterios["min_size_kb"]:
        return False
    pushed = repo.get("pushed_at")
    if not pushed:
        return False
    try:
        meses_inativo = (agora - _parse_iso(pushed)).days / DIAS_POR_MES
    except (ValueError, TypeError):
        return False
    return meses_inativo <= criterios["max_meses_inativo"]


def extrair_familia(repo_name: str) -> str:
    """Sub-família = primeira palavra do nome do repo antes de qualquer hífen.

    'commons-lang' → 'commons'; 'java-storage' → 'java'; 'guava' → 'guava'."""
    return repo_name.split("-")[0].lower()


def normalizar(arquetipo: str, org: str, repo: dict) -> dict:
    """Projeta um repo bruto da API do GitHub no schema do CSV de saída."""
    nome = repo.get("name", "")
    return {
        "arquetipo":         arquetipo,
        "org":               org,
        "full_name":         repo.get("full_name", ""),
        "repo_name":         nome,
        "stars":             repo.get("stargazers_count", 0) or 0,
        "language":          repo.get("language", "") or "",
        "size_kb":           repo.get("size", 0) or 0,
        "ultimo_commit_iso": repo.get("pushed_at", "") or "",
        "html_url":          repo.get("html_url", "") or "",
        "descricao":         repo.get("description", "") or "",
        "familia":           extrair_familia(nome),
    }


def deduplicar(candidatos: list[dict]) -> list[dict]:
    """Remove duplicatas por full_name, preservando a primeira ocorrência."""
    vistos: set[str] = set()
    out: list[dict] = []
    for c in candidatos:
        fn = c["full_name"]
        if fn in vistos:
            continue
        vistos.add(fn)
        out.append(c)
    return out


def excluir_ja_coletados(candidatos: list[dict],
                         nomes_excluidos: set[str]) -> list[dict]:
    """Remove candidatos cujo repo_name já está no consolidado N=34."""
    excl = {n.lower() for n in nomes_excluidos}
    return [c for c in candidatos if c["repo_name"].lower() not in excl]


def limitar_por_familia(candidatos: list[dict],
                        max_por_familia: int = MAX_POR_FAMILIA) -> list[dict]:
    """Mantém no máximo `max_por_familia` candidatos por (org, família),
    escolhendo os de maior número de stars."""
    grupos: dict[tuple[str, str], list[dict]] = {}
    for c in candidatos:
        grupos.setdefault((c["org"], c["familia"]), []).append(c)
    out: list[dict] = []
    for lista in grupos.values():
        lista_ord = sorted(lista, key=lambda c: c["stars"], reverse=True)
        out.extend(lista_ord[:max_por_familia])
    return out


def ordenar_final(candidatos: list[dict]) -> list[dict]:
    """Ordena por arquétipo e, dentro do arquétipo, por stars descendente."""
    return sorted(candidatos, key=lambda c: (c["arquetipo"], -c["stars"]))


# ---------------- GitHub API ----------------

def _github_get(caminho: str, params: dict, token: str,
                logger: logging.Logger) -> requests.Response:
    """GET autenticado com retry+backoff (3 tentativas, sleep 2/4/8s)."""
    url = f"{GITHUB_API}{caminho}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    ultimo_erro = None
    for tentativa in range(1, 4):
        try:
            return requests.get(url, headers=headers, params=params, timeout=30)
        except requests.RequestException as e:
            ultimo_erro = e
            if tentativa < 3:
                espera = 2 ** tentativa  # 2, 4, 8
                logger.warning("rede falhou em %s (%s) — retry em %ds (%d/3)",
                               url, e, espera, tentativa)
                time.sleep(espera)
    raise CandidatosError(f"rede falhou após 3 tentativas em {url}: {ultimo_erro}")


def _checar_rate_limit(resp: requests.Response, logger: logging.Logger) -> None:
    restante_raw = resp.headers.get("X-RateLimit-Remaining")
    if restante_raw is None:
        return
    try:
        restante = int(restante_raw)
    except ValueError:
        return
    if restante < RATE_LIMIT_MINIMO:
        raise RateLimitBaixo(restante)


def listar_repos_org(org: str, token: str,
                     logger: logging.Logger) -> list[dict]:
    """Lista todos os repos de uma org, paginando per_page=100.

    404/outros HTTP de erro → warning e retorna o que tiver. 401 → fatal."""
    repos: list[dict] = []
    page = 1
    while True:
        resp = _github_get(f"/orgs/{org}/repos",
                           {"per_page": 100, "page": page}, token, logger)
        if resp.status_code == 401:
            raise CandidatosError(
                "token GitHub inválido ou expirado (HTTP 401). Gere um novo "
                "em https://github.com/settings/tokens (escopo `public_repo`)."
            )
        if resp.status_code == 404:
            logger.warning("org '%s' não encontrada (404) — pulando", org)
            return repos
        if resp.status_code != 200:
            logger.warning("org '%s' retornou HTTP %d — pulando",
                           org, resp.status_code)
            return repos
        _checar_rate_limit(resp, logger)
        try:
            lote = resp.json()
        except ValueError:
            logger.warning("org '%s' p=%d: resposta não-JSON — pulando",
                           org, page)
            return repos
        if not lote:
            break
        repos.extend(lote)
        if len(lote) < 100:
            break
        page += 1
        time.sleep(SLEEP_ENTRE_REQUESTS)
    return repos


# ---------------- saída ----------------

def escrever_csv(candidatos: list[dict], out_csv: Path) -> None:
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OUT_COLS)
        writer.writeheader()
        for c in candidatos:
            writer.writerow({col: c.get(col, "") for col in OUT_COLS})


def imprimir_resumo(candidatos: list[dict], logger: logging.Logger) -> None:
    por_arq: dict[str, list[dict]] = {}
    for c in candidatos:
        por_arq.setdefault(c["arquetipo"], []).append(c)

    logger.info("=" * 60)
    logger.info("RESUMO — %d candidatos no total", len(candidatos))
    for arq in ORGS_POR_ARQUETIPO:
        lista = por_arq.get(arq, [])
        logger.info("  %-16s %d candidatos", arq, len(lista))

    for arq in ORGS_POR_ARQUETIPO:
        lista = sorted(por_arq.get(arq, []),
                       key=lambda c: c["stars"], reverse=True)
        if not lista:
            continue
        logger.info("-" * 60)
        logger.info("TOP 10 — %s", arq)
        for c in lista[:10]:
            logger.info("  %6d★  %-40s %s",
                        c["stars"], c["full_name"], c["ultimo_commit_iso"])


# ---------------- main ----------------

def main() -> int:
    logger = setup_logger(LOG_PATH)
    logger.info("=== buscar_projetos_candidatos (expansão N=34 → N≈52) ===")

    try:
        token = carregar_token(logger)
        nomes_excluidos, n_consolidado, n_tecnica = carregar_excluidos(logger)
    except CandidatosError as e:
        logger.error("%s", e)
        return 1
    logger.info("%d projetos do consolidado + %d limitação técnica = %d "
                "exclusões totais aplicadas",
                n_consolidado, n_tecnica, len(nomes_excluidos))

    agora = datetime.now(timezone.utc)
    brutos: list[dict] = []
    interrompido = False

    try:
        for arquetipo, orgs in ORGS_POR_ARQUETIPO.items():
            for org in orgs:
                repos = listar_repos_org(org, token, logger)
                batem = [r for r in repos
                         if repo_bate_criterios(r, CRITERIOS, agora)]
                logger.info("%s: %d repos encontrados, %d batem critérios",
                            org, len(repos), len(batem))
                for r in batem:
                    brutos.append(normalizar(arquetipo, org, r))
                time.sleep(SLEEP_ENTRE_REQUESTS)
    except CandidatosError as e:
        logger.error("%s", e)
        return 1
    except RateLimitBaixo as e:
        logger.warning("rate limit do GitHub abaixo de %d (restante=%d) — "
                       "interrompendo e salvando estado parcial",
                       RATE_LIMIT_MINIMO, e.restante)
        interrompido = True

    candidatos = deduplicar(brutos)
    candidatos = excluir_ja_coletados(candidatos, nomes_excluidos)
    candidatos = limitar_por_familia(candidatos, MAX_POR_FAMILIA)
    candidatos = ordenar_final(candidatos)

    escrever_csv(candidatos, OUT_CSV)
    logger.info("CSV salvo: %s (%d candidatos)", OUT_CSV, len(candidatos))
    imprimir_resumo(candidatos, logger)

    if interrompido:
        logger.warning("EXECUÇÃO PARCIAL — rate limit atingido. Rode novamente "
                       "após a janela de rate limit (1h) para resultado completo.")
        return 2
    logger.info("Concluído.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
