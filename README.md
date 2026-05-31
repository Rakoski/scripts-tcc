# O paradoxo da governança em escala: uma comparação quantitativa da dívida técnica em nível de código entre ecossistemas Java Apache, Google e de plataforma descentralizada

**Trabalho de Conclusão de Curso — 2026**

A força da governança arquitetural, em um nível de organização, se relaciona com a variância da dívida técnica, a nível de código?

É isso que esse estudo quer descobrir.

A métrica primária usada é a densidade SQALE (`sqale_index / ncloc`, em minutos por linha de código não-comentada (**NCLOC = Non Commented Lines of Code**)). O teste confirmatório é
Brown-Forsythe sobre as variâncias entre arquétipos, com
regra de decisão pré-registrada em [`protocolo.md`](protocolo.md).

## H1

Como o Google adota **scaffolding padronizado**, a Apache opera por governança comunitária e consenso e o arquétipo descentalizado torna a padronização opcional, em teoria a ordem das variâncias de dívida técnicas deveriam seguir assim:

Google < Apache < Descentralizado

Essa ordem foi fixada **antes da coleta dos dados** e não é revisável.


### Pré-registro auditável

O [`protocolo.md`](protocolo.md) versionado neste repositório foi congelado
antes da coleta. A cronologia das decisões metodológicas é auditável via
tags git e commits datados:

| Tag git | Data | Decisão metodológica |
|---|---|---|
| `coleta-oficial-v1.5` | 17/05/2026 | Coleta inicial N=34 finalizada |
| `ampliacao-v1.6-predeclarada` | 22/05/2026 | Expansão para N=64 declarada antes da nova coleta |
| `relaxamento-v1.7-predeclarada` | 23/05/2026 | Critério `HEAD-of-main` para os 30 projetos novos |
| `substituicao-v1.8-predeclarada` | 26/05/2026 | Substituições por violação de critérios 3.1 |
| `cascata-v1.9-predeclarada` | 28/05/2026 | Substituição em cascata servo → Priam |

## Resultados resumidos (N=60)

A regra de decisão pré-registrada 8.2 v1.5 (`C1 ∧ C2`) **não foi
satisfeita**:

| Análise | C1 (significância) | C2 (ordem) | H1 |
|---|---|---|---|
| Brown-Forsythe em densidade | False (F=0.42, F_crit=2.94) | False | rejeitada |
| Brown-Forsythe em log-densidade (complementar A2.2) | True (F=2.93, F_crit=2.81) | False | rejeitada |

A ordem amostral das variâncias, na verdade, é **inversa à prevista**:

- Google: 0.084 (maior variância — não a menor)
- Apache: 0.050
- Descentralizado: 0.048 (menor variância — não a maior)

Apache apresenta densidade de dívida sistematicamente maior que Google (Cliff's δ = +0.37, efeito médio).

As tabelas podem ser encontradas em [`dados/n60-analise/analise/tabelas/`](dados/n60-analise/analise/tabelas/).

## Limitações

1. **Poder estatístico** do teste primário estimado em ~9% para razões de variância plausíveis (protocolo v1.5 5)
2. **4 projetos excluídos** por limitação técnica do ambiente de build
   (protocolo v1.10 A29).
3. **Composição não-balanceada** do arquétipo descentralizado (Netflix
   representa 11/19 = 58%), declarada em A6 v1.6
4. **Heterogeneidade interna** do arquétipo Apache (7/24 projetos de
   origem chinesa via incubator), declarada em A18 v1.8

Limitações são tratadas conforme 8.1 do protocolo
(correlação parcial Spearman, ICC intra-organização), com análises
detalhadas em material suplementar (não no corpo do paper resultante).

## Reprodução

### Análise estatística (rápido, sem precisar de SonarQube)

Se você só quer rodar a análise estatística sobre os dados já coletados:

```bash
python3 analise_estatistica.py \
  --data-dir dados/n60-analise \
  --data-coleta 2026-05-29
```

Tempo esperado: 3-5 minutos (incluindo simulação Monte Carlo de 10.000
réplicas para calibração do F-crítico empírico).

**Pré-requisitos:**
- Python 3.11+
- `pandas`, `scipy`, `pingouin`, `seaborn`, `matplotlib`, `numpy`

### Coleta completa (requer infraestrutura)

Para refazer a coleta do zero (clones, build, scan Sonar):

**Pré-requisitos adicionais:**
- SonarQube Community Build v26.2.0.119303 em MQR Mode
- Sonar Scanner 5.0.1.3006
- JDK 21 (Temurin) + fallbacks JDK 17, 11 e 8
- Maven, Gradle, Ant, Bazel (instalado via bazelisk)
- Variáveis de ambiente em `.env`: `SONAR_URL`, `SONAR_TOKEN`, `GITHUB_TOKEN`

**Passos:**

```bash
# 1. para clonar os repositórios da amostra
python3 clonar_v17.py

# 2. pra coletar as métricas Sonar (gera dados/YYYY-MM-DD/)
python3 coletar_dados_sonar.py

# 3. pra rodar a análise sobre os dados coletados
python3 analise_estatistica.py \
  --data-dir dados/YYYY-MM-DD \
  --data-coleta YYYY-MM-DD
```

### Clonagem dos projetos

A clonagem é feita pelo script `clonar_v17.py`, que lê a planilha mestra
`projetos-tcc-dataset-4.csv` (fonte única de verdade, 65 linhas brutas) e
clona os projetos da amostra em `../projetos-clonados/` (fora do repo
público). Para reprodutibilidade exata, cada repositório recebe `git
checkout` no `commit_sha` registrado na planilha.

Por default, o script pula os 5 projetos presentes em
`PROJETOS_EXCLUIDOS_LIMITACAO_TECNICA` (`coleta_lib/io_utils.py`) —
`google-j2objc-11` (build exige macOS, A11) e os 4 da limitação técnica de
build A29 v1.10 (bazel, google-java-format, java-docs-samples, dexmaker) —
resultando na amostra efetiva **n=60** (Apache 24, Google 17,
Descentralizado 19).

```bash
python3 clonar_v17.py                     # clona 60 (sem os excluídos)
python3 clonar_v17.py --include-excluded   # clona 65 (reprodução total)
python3 clonar_v17.py --subset n34-v1.5    # só o subconjunto v1.5 (34)
python3 clonar_v17.py --subset n30-v1.6    # só o subconjunto v1.6 (26)
python3 clonar_v17.py --dry-run            # lista o que seria feito, sem clonar
```

Cada execução gera `clones_v17.csv` (auditoria, uma linha por projeto com a
coluna `resultado`) e `clones_v17.log`. Tempo estimado: 30-60 minutos numa
conexão decente — repositórios grandes (Apache cassandra, druid, kafka)
podem demorar vários minutos cada.

