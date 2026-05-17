"""Fases 2-4 — métricas (component), issues (search paginado), regras (rules/show).

Issues são coletadas com segmentação por `type` (CODE_SMELL/BUG/VULNERABILITY)
para contornar o limite duro de 10000 itens por consulta da API Sonar. Se algum
type ainda truncar, segunda camada de segmentação por `severity`.
"""
from __future__ import annotations

import json
import logging
import math
import time
from pathlib import Path

from .io_utils import ProjetoError, SonarClient

METRICAS = [
    "ncloc", "sqale_index", "sqale_debt_ratio",
    "code_smells", "bugs", "vulnerabilities",
    "complexity", "cognitive_complexity",
    "duplicated_lines_density", "comment_lines_density",
    "ncloc_language_distribution",
]

ISSUE_PS = 500
ISSUE_RATE_LIMIT_SLEEP = 0.5
RULE_RATE_LIMIT_SLEEP = 0.2
SONAR_PAGINATION_CAP = 10_000

ISSUE_TYPES = ["CODE_SMELL", "BUG", "VULNERABILITY"]
SEVERITY_GROUPS = [
    ("BLOCKER,CRITICAL", "BLOCKER+CRITICAL"),
    ("MAJOR",            "MAJOR"),
    ("MINOR,INFO",       "MINOR+INFO"),
]


def extrair_metricas(client: SonarClient, project_key: str,
                     logger: logging.Logger) -> dict:
    r = client.get("/api/measures/component",
                   component=project_key,
                   metricKeys=",".join(METRICAS))
    if r.status_code != 200:
        logger.warning("[%s] /api/measures/component HTTP %d",
                       project_key, r.status_code)
        return {}
    try:
        data = r.json()
    except ValueError:
        logger.warning("[%s] resposta não-JSON em /measures/component", project_key)
        return {}

    measures = data.get("component", {}).get("measures", [])
    out: dict[str, str] = {}
    for m in measures:
        out[m["metric"]] = m.get("value", "")
    # parse loc_java
    dist = out.get("ncloc_language_distribution", "")
    loc_java = ""
    if dist:
        for tok in dist.split(";"):
            if tok.startswith("java="):
                loc_java = tok.split("=", 1)[1]
                break
    out["loc_java_sonar"] = loc_java
    return out


def _paginar_issues(client: SonarClient, project_key: str,
                    params_extra: dict, logger: logging.Logger
                    ) -> tuple[list[dict], bool]:
    """Pagina /api/issues/search com filtros adicionais.

    Retorna (lista_de_issues, truncated_bool). truncated=True só quando
    paging.total > SONAR_PAGINATION_CAP (i.e. existem issues além das 10k
    que a API se recusa a paginar)."""
    todas: list[dict] = []
    page = 1
    truncated = False
    while True:
        params = dict(componentKeys=project_key, ps=ISSUE_PS, p=page)
        params.update(params_extra)
        r = client.get("/api/issues/search", **params)
        if r.status_code != 200:
            logger.warning("[%s] /api/issues/search p=%d %s HTTP %d",
                           project_key, page, params_extra, r.status_code)
            break
        try:
            data = r.json()
        except ValueError:
            logger.warning("[%s] /issues/search resposta não-JSON p=%d",
                           project_key, page)
            break
        issues = data.get("issues", []) or []
        for it in issues:
            todas.append({
                "rule": it.get("rule", ""),
                "type": it.get("type", ""),
                "severity": it.get("severity", ""),
                "effort": it.get("effort") or it.get("debt") or "",
            })
        total = int(data.get("paging", {}).get("total", 0))
        if page * ISSUE_PS >= total:
            break
        if page * ISSUE_PS >= SONAR_PAGINATION_CAP:
            if total > SONAR_PAGINATION_CAP:
                truncated = True
            break
        page += 1
        time.sleep(ISSUE_RATE_LIMIT_SLEEP)
    return todas, truncated


def extrair_issues(client: SonarClient, project_key: str,
                   issues_dir: Path, logger: logging.Logger) -> int:
    """Coleta segmentada por type (e por severity como 2º nível).
    Levanta ProjetoError se ainda houver truncamento após segmentação."""
    issues_dir.mkdir(parents=True, exist_ok=True)
    todas: list[dict] = []
    contagens: dict[str, int] = {}

    for tipo in ISSUE_TYPES:
        tipo_issues, truncou = _paginar_issues(
            client, project_key, {"types": tipo}, logger,
        )

        if truncou:
            logger.warning("[%s] %s truncou em %d, sub-segmentando por severity",
                           project_key, tipo, SONAR_PAGINATION_CAP)
            tipo_issues = []
            counts_sev: dict[str, int] = {}
            for sev_param, sev_label in SEVERITY_GROUPS:
                sev_issues, sev_truncou = _paginar_issues(
                    client, project_key,
                    {"types": tipo, "severities": sev_param}, logger,
                )
                if sev_truncou:
                    msg = (f"[{project_key}] {tipo} severity={sev_label} ainda "
                           f">= {SONAR_PAGINATION_CAP} — sub-segmentação insuficiente")
                    logger.error(msg)
                    raise ProjetoError(msg)
                counts_sev[sev_label] = len(sev_issues)
                tipo_issues.extend(sev_issues)
            partes = ", ".join(f"{lbl}={n}" for lbl, n in counts_sev.items())
            logger.info("[%s] %s: %s → %d", project_key, tipo, partes, len(tipo_issues))

        contagens[tipo] = len(tipo_issues)
        todas.extend(tipo_issues)

    out_path = issues_dir / f"{project_key}.json"
    out_path.write_text(json.dumps(todas, ensure_ascii=False, indent=2),
                        encoding="utf-8")
    logger.info("[%s] CODE_SMELL: %d, BUG: %d, VULNERABILITY: %d → total: %d",
                project_key,
                contagens.get("CODE_SMELL", 0),
                contagens.get("BUG", 0),
                contagens.get("VULNERABILITY", 0),
                len(todas))
    return len(todas)


def coletar_regras_metadata(client: SonarClient, todas_rule_keys: set[str],
                            saida_path: Path,
                            logger: logging.Logger) -> dict:
    """Carrega metadata existente (se houver), atualiza com regras novas,
    grava merge. Idempotente para retomadas e --only/--limit."""
    out: dict[str, dict] = {}
    if saida_path.exists():
        try:
            existing = json.loads(saida_path.read_text(encoding="utf-8"))
            if isinstance(existing, dict):
                out.update(existing)
                logger.info("regras_metadata.json carregado: %d regras pré-existentes",
                            len(out))
        except Exception as e:
            logger.warning("regras_metadata.json corrompido (%s) — recriando", e)

    a_buscar = sorted(rk for rk in todas_rule_keys if rk not in out)
    logger.info("Coletando metadata de %d regras novas (%d já em cache)...",
                len(a_buscar), len(out))
    for i, rk in enumerate(a_buscar, start=1):
        r = client.get("/api/rules/show", key=rk)
        if r.status_code != 200:
            logger.warning("[regra %s] HTTP %d", rk, r.status_code)
            continue
        try:
            data = r.json()
        except ValueError:
            logger.warning("[regra %s] resposta não-JSON", rk)
            continue
        rule = data.get("rule", {})
        out[rk] = {
            "name": rule.get("name", ""),
            "type": rule.get("type", ""),
            "tags": rule.get("tags", []) or [],
            "sysTags": rule.get("sysTags", []) or [],
            "severity": rule.get("severity", ""),
            "lang": rule.get("lang", ""),
        }
        if i % 50 == 0:
            logger.info("Regras novas: %d/%d", i, len(a_buscar))
        time.sleep(RULE_RATE_LIMIT_SLEEP)

    saida_path.write_text(json.dumps(out, ensure_ascii=False, indent=2),
                          encoding="utf-8")
    logger.info("regras_metadata.json salvo: %d regras totais (+%d novas)",
                len(out), len(a_buscar))
    return out


def carregar_issues_acumulado(issues_dir: Path) -> set[str]:
    """Acumula rule_keys de todos os issues/{id}.json existentes."""
    out: set[str] = set()
    for p in issues_dir.glob("*.json"):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(data, dict) and "issues" in data:
            data = data["issues"]
        if not isinstance(data, list):
            continue
        for it in data:
            rk = it.get("rule")
            if rk:
                out.add(rk)
    return out
