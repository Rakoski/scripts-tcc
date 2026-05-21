"""Fases 2-4 — métricas (component), issues (search paginado), regras (rules/show).

Issues são coletadas com segmentação em cascata para contornar o limite duro
de 10000 itens por consulta da API Sonar:

  1. por `type` (CODE_SMELL/BUG/VULNERABILITY);
  2. se ainda truncar, por `severity` individual (BLOCKER/CRITICAL/MAJOR/MINOR/INFO);
  3. se uma severity isolada ainda truncar, recursão temporal via
     createdAfter/createdBefore (halving da janela até <10000 por bucket);
  4. se a recursão temporal exceder TEMPORAL_MAX_DEPTH (gigantes como kafka,
     flink, camel), a coleta segue como PARCIAL: salva o que conseguiu coletar,
     marca o arquivo com `parciais: true`, e a análise estatística usa as
     contagens agregadas de /api/measures/component (sempre completas, sem
     limite de paginação).

A tese de TCC usa apenas métricas agregadas; issues individuais são apoio à
análise exploratória. Por isso paginação incompleta NÃO bloqueia o estudo.
"""
from __future__ import annotations

import json
import logging
import time
from datetime import date
from pathlib import Path

from .io_utils import SonarClient

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
INDIVIDUAL_SEVERITIES = ["BLOCKER", "CRITICAL", "MAJOR", "MINOR", "INFO"]

# Recursão temporal: profundidade máxima e janela inicial. 2^5 = 32 buckets
# por severity é mais que suficiente para projetos com históricos longos
# (kafka, flink, camel). Janela inicial cobre histórico de qualquer projeto
# de software contemporâneo.
TEMPORAL_MAX_DEPTH = 5
TEMPORAL_INITIAL_AFTER = "2000-01-01"


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


def _segmentar_temporalmente(client: SonarClient, project_key: str,
                             base_params: dict, label: str,
                             after_iso: str, before_iso: str,
                             depth: int,
                             logger: logging.Logger
                             ) -> tuple[list[dict], bool]:
    """Halving recursivo da janela createdAfter..createdBefore enquanto truncar.
    Semântica Sonar: createdAfter inclusivo, createdBefore exclusivo →
    intervalos [after, mid) e [mid, before) são disjuntos.

    Retorna (issues, parcial). parcial=True quando profundidade máxima foi
    atingida ou a janela ficou diária e ainda truncava — nesses casos,
    devolve as primeiras 10000 issues que a API liberou e marca a flag para
    o caller usar contagem agregada de /api/measures/component."""
    params = dict(base_params)
    params["createdAfter"] = after_iso
    params["createdBefore"] = before_iso
    issues, truncou = _paginar_issues(client, project_key, params, logger)
    if not truncou:
        return issues, False

    if depth >= TEMPORAL_MAX_DEPTH:
        logger.warning(
            "[%s] %s createdAfter=%s createdBefore=%s ainda >= %d após "
            "profundidade máxima — usando contagem agregada de "
            "/api/measures/component. Issues individuais coletadas serão "
            "salvas como parciais.",
            project_key, label, after_iso, before_iso, SONAR_PAGINATION_CAP,
        )
        return issues, True

    after_d = date.fromisoformat(after_iso)
    before_d = date.fromisoformat(before_iso)
    if (before_d - after_d).days <= 1:
        logger.warning(
            "[%s] %s janela %s..%s já é diária e ainda >= %d — usando "
            "contagem agregada de /api/measures/component. Issues coletadas "
            "serão salvas como parciais.",
            project_key, label, after_iso, before_iso, SONAR_PAGINATION_CAP,
        )
        return issues, True
    mid_d = after_d + (before_d - after_d) // 2
    mid_iso = mid_d.isoformat()
    logger.info("[%s] %s createdBefore=%s ainda >= %d, halving para mid=%s",
                project_key, label, before_iso, SONAR_PAGINATION_CAP, mid_iso)

    a, pa = _segmentar_temporalmente(client, project_key, base_params,
                                     label, after_iso, mid_iso, depth + 1, logger)
    b, pb = _segmentar_temporalmente(client, project_key, base_params,
                                     label, mid_iso, before_iso, depth + 1, logger)
    return a + b, (pa or pb)


def _agregado_int(metricas: dict | None, chave: str) -> int:
    v = (metricas or {}).get(chave, "")
    try:
        return int(v)
    except (ValueError, TypeError):
        return 0


def extrair_issues(client: SonarClient, project_key: str,
                   issues_dir: Path, logger: logging.Logger,
                   metricas: dict | None = None) -> int:
    """Coleta com cascata type → severity individual → recursão temporal.

    Se a recursão temporal atinge TEMPORAL_MAX_DEPTH (gigantes tipo Kafka),
    coleta segue como PARCIAL: salva o que conseguiu pegar com `parciais: true`
    e logs apontam para uso da contagem agregada de /api/measures/component.
    Não levanta exceção — análise estatística usa métricas agregadas (sempre
    completas) e a paginação é apoio à exploração.
    """
    issues_dir.mkdir(parents=True, exist_ok=True)
    todas: list[dict] = []
    contagens: dict[str, int] = {}
    parciais = False

    for tipo in ISSUE_TYPES:
        tipo_issues, truncou = _paginar_issues(
            client, project_key, {"types": tipo}, logger,
        )

        if truncou:
            logger.warning("[%s] %s truncou em %d, sub-segmentando por severity individual",
                           project_key, tipo, SONAR_PAGINATION_CAP)
            tipo_issues = []
            counts_sev: dict[str, int] = {}
            janelas_extra = 0
            today_iso = date.today().isoformat()

            for sev in INDIVIDUAL_SEVERITIES:
                params_sev = {"types": tipo, "severities": sev}
                sev_issues, sev_truncou = _paginar_issues(
                    client, project_key, params_sev, logger,
                )
                if sev_truncou:
                    logger.warning("[%s] %s severity=%s ainda >= %d, "
                                   "segmentando por createdBefore/createdAfter",
                                   project_key, tipo, sev, SONAR_PAGINATION_CAP)
                    sev_issues, sev_parcial = _segmentar_temporalmente(
                        client, project_key, params_sev,
                        label=f"{tipo} severity={sev}",
                        after_iso=TEMPORAL_INITIAL_AFTER,
                        before_iso=today_iso,
                        depth=0,
                        logger=logger,
                    )
                    if sev_parcial:
                        parciais = True
                    janelas_extra += 1
                counts_sev[sev] = len(sev_issues)
                tipo_issues.extend(sev_issues)

            partes = ", ".join(f"{lbl}={n}" for lbl, n in counts_sev.items())
            sufixo = (f" (sub-segmentado em {janelas_extra} severity(s) com "
                      f"recursão temporal)" if janelas_extra else "")
            logger.info("[%s] %s: %s → %d%s",
                        project_key, tipo, partes, len(tipo_issues), sufixo)

        contagens[tipo] = len(tipo_issues)
        todas.extend(tipo_issues)

    out_path = issues_dir / f"{project_key}.json"
    if parciais:
        cs = _agregado_int(metricas, "code_smells")
        bg = _agregado_int(metricas, "bugs")
        vu = _agregado_int(metricas, "vulnerabilities")
        total_sonar = cs + bg + vu
        razao = (f"sub-segmentação por createdAfter/createdBefore atingiu "
                 f"profundidade máxima — {len(todas)} coletadas de "
                 f"{total_sonar} issues totais")
        payload = {
            "issues":      todas,
            "parciais":    True,
            "razao":       razao,
            "total_sonar": total_sonar,
        }
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                            encoding="utf-8")
        logger.warning("[%s] usando contagens agregadas: code_smells=%d, "
                       "bugs=%d, vulnerabilities=%d (paginação foi insuficiente)",
                       project_key, cs, bg, vu)
        logger.info("[%s] CODE_SMELL: %d, BUG: %d, VULNERABILITY: %d → "
                    "paginação=%d (parciais; total agregado=%d)",
                    project_key,
                    contagens.get("CODE_SMELL", 0),
                    contagens.get("BUG", 0),
                    contagens.get("VULNERABILITY", 0),
                    len(todas), total_sonar)
    else:
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
