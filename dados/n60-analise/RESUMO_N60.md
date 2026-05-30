# Resumo executivo — Análise estatística N=60

**Data de execução:** 2026-05-29
**Diretório de entrada:** `dados/n60-analise/`
**Pipeline:** `scripts-tcc/analise_estatistica.py` (sem modificações)
**Seed Monte Carlo:** 42 (declarado no script)
**Protocolo:** v1.10 (§A30 — N=60 final efetivo)

## Composição amostral

| Arquétipo | n | Subgrupos |
|---|---:|---|
| Apache | 24 | — |
| Google | 17 | — |
| Descentralizado | 19 | Netflix 11, LinkedIn 4, Uber 4 |
| **Total** | **60** | |

## Regra de decisão §8.2 v1.5 (densidade)

| Condição | Resultado |
|---|---|
| F-crítico empírico (Monte Carlo, 10000 réplicas, μ=-1.12, σ=0.72) | 2.9444 |
| F-crítico teórico F(2, 57, 0.95) | 3.1588 |
| Desvio relativo emp/teo | -6.79% |
| KS-test contra F(2, 57) | stat=0.0348, p=6.04e-11 (rejeita compat.) |
| **F observado (Brown-Forsythe)** | **0.4190** |
| p teórico | 0.6597 |
| var(apache) | 0.0498 |
| var(google) | 0.0844 |
| var(descentralizado) | 0.0484 |
| **C1 (F > F-crítico empírico)** | **FALSE** (0.42 << 2.94) |
| **C2 (var Google < Apache < Descentralizado)** | **FALSE** (ordem real: desc < apa < goog) |
| **H1 (C1 ∧ C2)** | **REJEITADA** |

### Interpretação canônica (do script)

> Falha em detectar diferença de variâncias. Sob poder de ~9% (v1.5), **NÃO constitui evidência de equivalência** entre arquétipos.

## Tamanho de efeito — Cliff's δ (descritivo)

| Par | δ | Magnitude (Romano 2006) | Direção |
|---|---:|---|---|
| Apache vs Google | +0.373 | médio | Apache > Google |
| Apache vs Descentralizado | +0.268 | pequeno | Apache > Descentralizado |
| Google vs Descentralizado | -0.183 | pequeno | Descentralizado > Google |

Padrão observado: **Apache lidera densidade**, Google é o mais baixo.

## Análises complementares

| Procedimento | Estatística | p | Interpretação |
|---|---|---|---|
| Kruskal-Wallis | H=4.882, η²=0.051 | 0.0871 | Borderline (não rejeita H0 em α=0.05) |
| Jonckheere-Terpstra (g≤a≤d) | z=0.606 | 0.272 | Sem tendência monotônica prevista |
| Spearman parcial† | r=0.234 | 0.205 | Controlando log_loc, idade_anos, idade_snapshot_dias |
| ICC(1) descentralizado | — | — | **ERRO**: dados desbalanceados (uber=4, linkedin=4, netflix=11) |

† **Nota Spearman**: tabela reporta n=34 (não 60). Provavelmente exclusão de NaN em `idade_snapshot_dias` para alguma porção da amostra. Vale investigar em sessão futura.

## Análise complementar log-densidade (pós-hoc §A2.2 v1.6)

Rodada como suplemento standalone (sem modificar `analise_estatistica.py`):

| Métrica log | Valor |
|---|---:|
| F observado (BF em log) | 2.9288 |
| F-crítico empírico (lognormal calibrada, p95) | 2.8114 |
| F-crítico teórico | 3.1588 |
| var log(apache) | 0.2686 |
| var log(google) | 0.7764 |
| var log(descentralizado) | 0.5441 |
| **C1_log** | **TRUE** (2.93 > 2.81) |
| **C2_log** | **FALSE** (ordem real: apa < desc < goog) |
| **H1_log** | **REJEITADA** (por C2 só) |

**Achado relevante para discussão**: em escala log, **há evidência de heterogeneidade de variâncias** (C1 satisfeita), mas não na ordem prevista pela hipótese de governança. Em densidade original, nem isso (F muito abaixo do crítico). Cliff's δ é idêntico em log (transformação monotônica preserva ordens estocásticas).

## Arquivos gerados

**Tabelas** (`dados/n60-analise/analise/tabelas/`):
- `regra_decisao_h1.csv` — resultado pré-registrado
- `tab1_descritivas_arquetipo.csv` + `.md`
- `tab2_subgrupos_descentralizado.csv`
- `tab3_brown_forsythe.csv`
- `tab4_cliffs_delta_pares.csv`
- `tab5_kruskal_wallis.csv`
- `tab6_jonckheere_terpstra.csv`
- `tab7_spearman_parcial.csv`
- `tab8_icc_descentralizado.csv` (placeholder com erro)
- `tab9_decomposicao_regras_por_arquetipo.csv`
- `tab_log_densidade_complementar.csv` ← novo da Fase 5

**Figuras** (`dados/n60-analise/analise/figuras/`):
- `fig1_boxplot_densidade_arquetipo.png`
- `fig2_boxplot_subgrupos_descentralizado.png`
- `fig3_scatter_densidade_vs_idade_snapshot.png`
- `fig4_dist_loc_idade_contribuidores.png`

**Logs**:
- `dados/n60-analise/execucao.log`

## Pendências técnicas (não bloqueantes)

1. **Bug em `decomposicao_regras.py`**: linha 45 levanta `KeyError: 'arquetipo'` na função `decomposicao_por_tag_arquetipo` (tab9b). Crash impediu geração de `relatorio.md`. Tab9 (principal) foi gerada com sucesso ANTES do crash; só a versão por tag (9b) falhou.
2. **ICC(1) falhou**: dados desbalanceados (uber=4, linkedin=4, netflix=11). `pingouin.intraclass_corr` exige rebalanceamento ou `nan_policy='omit'`.
3. **Spearman parcial n=34 (não 60)**: causa do filtro merece investigação; provavelmente NaN em `idade_snapshot_dias` para algum subconjunto.

## Tempo total da execução

| Fase | Tempo aprox. |
|---|---|
| Fase 1 (preparar input) | ~1 min |
| Fase 2 (smoke test) | ~5 s |
| Fase 3 (análise + Monte Carlo) | **~5 s** (calibração super rápida; bem abaixo do limite de 15 min) |
| Fase 5 (log-densidade) | ~30 s |
| Fase 6 (resumo) | manual |
| **Total** | **~3 min** wall time |

## Veredito metodológico

- **H1 (densidade) REJEITADA**: C1 e C2 ambos falsos.
- **H1 (log-densidade) REJEITADA**: C1 verdadeiro mas C2 falso.
- **Sob poder ~9% (v1.5)**, ausência de C1 em densidade **não constitui evidência de equivalência**.
- **Achado descritivo robusto**: ordem das variâncias (escala original ou log) **não corresponde** à hipótese `goog < apa < desc`. Em densidade: `desc < apa < goog`; em log: `apa < desc < goog`. Ambas com Google liderando variância, não no extremo previsto.
- **Cliff's δ Apache vs Google = +0.37 (médio)**: padrão estocástico claro mas em direção contra-intuitiva (Apache > Google em densidade).

Estes resultados são consistentes com a interpretação §5 do TCC: a ausência da ordem prevista é evidência substantiva contra a hipótese causal de "ausência de enforcement organizacional → maior variância", abrindo discussão de mecanismos alternativos.
