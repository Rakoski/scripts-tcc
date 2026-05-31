#!/usr/bin/env python3
from __future__ import annotations

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from buscar_projetos_candidatos import (
    CRITERIOS, deduplicar, excluir_ja_coletados, extrair_familia,
    extrair_nome_de_id, limitar_por_familia, nomes_de_limitacao_tecnica,
    normalizar, ordenar_final, repo_bate_criterios,
)

AGORA = datetime(2026, 5, 18, tzinfo=timezone.utc)

def _repo(**kw) -> dict:
    base = {
        "name": "exemplo",
        "full_name": "apache/exemplo",
        "language": "Java",
        "stargazers_count": 5000,
        "archived": False,
        "fork": False,
        "size": 50000,
        "pushed_at": (AGORA - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "html_url": "https://github.com/apache/exemplo",
        "description": "projeto exemplo",
    }
    base.update(kw)
    return base

def test_criterios_aceita_repo_valido():
    assert repo_bate_criterios(_repo(), CRITERIOS, AGORA) is True
    print("  ✓ repo válido passa em todos os critérios")

def test_criterios_rejeita_nao_java():
    assert repo_bate_criterios(_repo(language="Kotlin"), CRITERIOS, AGORA) is False
    assert repo_bate_criterios(_repo(language=None), CRITERIOS, AGORA) is False
    print("  ✓ rejeita linguagem != Java")

def test_criterios_rejeita_poucas_stars():
    assert repo_bate_criterios(_repo(stargazers_count=999), CRITERIOS, AGORA) is False
    assert repo_bate_criterios(_repo(stargazers_count=1000), CRITERIOS, AGORA) is True
    print("  ✓ corte de stars em 1000 (inclusivo)")

def test_criterios_rejeita_arquivado_e_fork():
    assert repo_bate_criterios(_repo(archived=True), CRITERIOS, AGORA) is False
    assert repo_bate_criterios(_repo(fork=True), CRITERIOS, AGORA) is False
    print("  ✓ rejeita arquivados e forks")

def test_criterios_rejeita_pequeno_e_inativo():
    assert repo_bate_criterios(_repo(size=999), CRITERIOS, AGORA) is False
    inativo = (AGORA - timedelta(days=400)).strftime("%Y-%m-%dT%H:%M:%SZ")
    assert repo_bate_criterios(_repo(pushed_at=inativo), CRITERIOS, AGORA) is False
    print("  ✓ rejeita repo pequeno (<1000 KB) e inativo (>12 meses)")

def test_extrair_familia():
    assert extrair_familia("commons-lang") == "commons"
    assert extrair_familia("commons-io") == "commons"
    assert extrair_familia("java-storage") == "java"
    assert extrair_familia("guava") == "guava"
    print("  ✓ família = palavra antes do primeiro hífen")

def test_limitar_por_familia_top3():
    cands = [
        normalizar("apache", "apache", _repo(name=f"commons-{i}",
                                             full_name=f"apache/commons-{i}",
                                             stargazers_count=stars))
        for i, stars in enumerate([5000, 4000, 3000, 2000, 1000])
    ]
    out = limitar_por_familia(cands, max_por_familia=3)
    assert len(out) == 3, f"esperado 3, veio {len(out)}"
    assert sorted(c["stars"] for c in out) == [3000, 4000, 5000]
    print("  ✓ mantém top-3 por (org, família), maiores stars")

def test_familia_separa_por_org():
    cands = [
        normalizar("google", "google", _repo(name="java-a",
                                              full_name="google/java-a",
                                              stargazers_count=5000)),
        normalizar("google", "googleapis", _repo(name="java-b",
                                                  full_name="googleapis/java-b",
                                                  stargazers_count=4000)),
    ]
    out = limitar_por_familia(cands, max_por_familia=3)
    assert len(out) == 2, "famílias 'java' de orgs diferentes não se misturam"
    print("  ✓ (org, família) é a chave — orgs distintas não competem")

def test_excluir_ja_coletados():
    cands = [
        normalizar("apache", "apache", _repo(name="tomcat",
                                             full_name="apache/tomcat")),
        normalizar("apache", "apache", _repo(name="kafka",
                                             full_name="apache/kafka")),
    ]
    out = excluir_ja_coletados(cands, {"tomcat", "zookeeper"})
    nomes = {c["repo_name"] for c in out}
    assert nomes == {"kafka"}, f"esperado só kafka, veio {nomes}"
    print("  ✓ remove repos já no consolidado")

def test_exclusao_case_insensitive():
    cands = [normalizar("descentralizado", "Netflix",
                        _repo(name="EVCache", full_name="Netflix/EVCache"))]
    out = excluir_ja_coletados(cands, {"evcache"})
    assert out == [], "exclusão deve ser case-insensitive"
    print("  ✓ exclusão é case-insensitive (EVCache vs evcache)")

def test_excluir_limitacao_tecnica():
    excluidos_map = {"google-j2objc-11": "macOS-only"}
    planilha = {"google-j2objc-11": {"nome": "j2objc"}}
    tecnica = nomes_de_limitacao_tecnica(excluidos_map, planilha)
    assert tecnica == {"j2objc"}, f"esperado {{'j2objc'}}, veio {tecnica}"

    cand = [normalizar("google", "google",
                       _repo(name="j2objc", full_name="google/j2objc"))]
    out = excluir_ja_coletados(cand, tecnica)
    assert out == [], "j2objc deve ser excluído via limitação técnica"
    print("  ✓ projeto de limitação técnica é excluído mesmo fora do consolidado")

def test_extrair_nome_de_id():
    assert extrair_nome_de_id("google-j2objc-11", {}) == "j2objc"
    assert extrair_nome_de_id("uber-cadence-java-client-05", {}) == \
        "cadence-java-client"
    print("  ✓ fallback heurístico: remove prefixo empresa- e sufixo -numero")

def test_extrair_nome_de_id_prefere_planilha():
    planilha = {"google-j2objc-11": {"nome": "j2objc-real"}}
    assert extrair_nome_de_id("google-j2objc-11", planilha) == "j2objc-real"
    print("  ✓ planilha tem precedência sobre o fallback heurístico")

def test_ordenar_final():
    cands = [
        normalizar("google", "google", _repo(full_name="google/a",
                                              stargazers_count=2000)),
        normalizar("apache", "apache", _repo(full_name="apache/b",
                                             stargazers_count=1000)),
        normalizar("apache", "apache", _repo(full_name="apache/c",
                                             stargazers_count=9000)),
    ]
    out = ordenar_final(cands)
    assert [c["arquetipo"] for c in out] == ["apache", "apache", "google"]
    assert [c["stars"] for c in out] == [9000, 1000, 2000]
    print("  ✓ ordena por arquétipo, depois stars desc")

def test_deduplicar():
    cands = [
        normalizar("apache", "apache", _repo(full_name="apache/x")),
        normalizar("apache", "apache", _repo(full_name="apache/x")),
        normalizar("apache", "apache", _repo(full_name="apache/y")),
    ]
    out = deduplicar(cands)
    assert {c["full_name"] for c in out} == {"apache/x", "apache/y"}
    assert len(out) == 2
    print("  ✓ remove duplicatas por full_name")

def main():
    tests = [
        test_criterios_aceita_repo_valido,
        test_criterios_rejeita_nao_java,
        test_criterios_rejeita_poucas_stars,
        test_criterios_rejeita_arquivado_e_fork,
        test_criterios_rejeita_pequeno_e_inativo,
        test_extrair_familia,
        test_limitar_por_familia_top3,
        test_familia_separa_por_org,
        test_excluir_ja_coletados,
        test_exclusao_case_insensitive,
        test_excluir_limitacao_tecnica,
        test_extrair_nome_de_id,
        test_extrair_nome_de_id_prefere_planilha,
        test_ordenar_final,
        test_deduplicar,
    ]
    failed = 0
    for t in tests:
        print(f"\n[{t.__name__}]")
        try:
            t()
        except AssertionError as e:
            print(f"  ✗ FAIL: {e}")
            failed += 1
        except Exception as e:
            print(f"  ✗ ERROR: {type(e).__name__}: {e}")
            failed += 1
    print(f"\n{'=' * 50}")
    if failed:
        print(f"FAIL: {failed}/{len(tests)} testes falharam")
        sys.exit(1)
    print(f"OK: {len(tests)}/{len(tests)} testes passaram")

if __name__ == "__main__":
    main()
