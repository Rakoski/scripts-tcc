# Protocolo de Pesquisa — Estudo do Paradoxo da Governança em Escala

**Autor:** Mateus Rakoski
**Orientadora:** Evanise A. C. Ruiz
**Instituição:** IFPR — Campus Paranavaí
**Versão:** 1.1 — congelada em 2026-04-14
**Status:** Fase 1 — aberta para coleta após congelamento

> Este documento congela as decisões metodológicas do TCC. Alterações posteriores devem
> ser registradas como versões sucessivas (1.2, 1.3, ...) com justificativa datada no
> final do arquivo, não como reescrita silenciosa. Qualquer decisão tomada durante a
> execução que não esteja aqui é ad-hoc e precisa ser promovida para este documento
> antes de ser aplicada aos dados da amostra oficial.

---

## 1. Questão de pesquisa

**QP:** A força da governança arquitetural no nível organizacional correlaciona-se
com a estabilidade e a variância da dívida técnica no nível de código-fonte em
ecossistemas de software de grande escala?

### 1.1 Escopo explícito

Este estudo mede **apenas o lado do controle/qualidade** do paradoxo da governança.
A medição empírica da velocidade de inovação — o outro lado do paradoxo — é
deixada como trabalho futuro e declarada como tal na introdução. Isto é uma decisão
de escopo, não uma omissão.

## 2. Hipóteses

- **H0:** Não há diferença estatisticamente significativa na variância nem na
  densidade da dívida técnica entre os três arquétipos de governança.
- **H1 (primária, ordenada, unilateral):** A **variância** da densidade de dívida
  técnica segue a ordem Google < Apache < Descentralizado, à medida que cresce a
  escala do projeto e a diversidade do time de contribuidores.
- **H1' (secundária):** A densidade mediana de dívida técnica difere entre os três
  arquétipos (sem direção pré-especificada).

**Teste primário:** Jonckheere-Terpstra unilateral sobre a variância da densidade
de dívida por arquétipo, α = 0,05, com a ordem `google < apache < descentralizado`
fixada *a priori* a partir da literatura de governança (ver §3.1) **antes** de
qualquer coleta de dados.

**Teste de existência complementar:** Brown-Forsythe (Levene com `center='median'`)
sobre homogeneidade de variâncias. Brown-Forsythe testa se as variâncias diferem;
Jonckheere-Terpstra testa se diferem **na ordem prevista**. Os dois respondem
perguntas distintas e ambos serão reportados.

**Testes secundários e exploratórios:** Kruskal-Wallis sobre densidade mediana
(secundário, sem direção), Cliff's δ pareado e η² (tamanhos de efeito,
obrigatórios), estatística descritiva por arquétipo. Sem correção para múltiplas
comparações: o teste primário é único (J-T sobre variância) e os demais são
declarados exploratórios na Seção 5.

**Compromisso de pré-registro:** a ordem `google < apache < descentralizado` é
congelada nesta versão do protocolo. Se o resultado do J-T for não-significativo,
isso é reportado como evidência contra H1 e o protocolo **não** será re-rodado com
ordem alternativa. A análise descritiva e Cliff's δ continuam revelando o padrão
real independentemente.

**Métrica primária:** densidade de dívida técnica = `sqale_index / ncloc`,
em minutos por linha de código não-comentada, agregada ao nível de projeto.
**Métrica secundária:** densidade mediana de dívida (mesma fórmula, foco em
tendência central em vez de variância).

## 3. Arquétipos de governança

### 3.1 Definições operacionais e ordem a priori

A ordem `google < apache < descentralizado` no eixo de centralização da
governança é estabelecida **a priori** com a seguinte justificativa:

- **Google** (mais centralizado): monorepo, revisão de código obrigatória,
  style guides corporativos, ferramentas internas padronizadas. Decisões
  arquiteturais top-down.
- **Apache** (intermediário): "The Apache Way" exige consenso comunitário
  (lazy consensus, votos formais para decisões maiores), revisão por pares,
  meritocracia. Centralização por *processo*, não por *autoridade*.
- **Descentralizado** (menos centralizado): paved-road / golden-paths em
  Netflix, Uber, Spotify, LinkedIn — defaults recomendados mas não obrigatórios,
  times autônomos podem optar por sair. Decisões arquiteturais bottom-up.

Esta ordem é a hipótese sobre a *variável independente* do estudo. Sua
validade conceitual é defendida na Seção 2 do TCC e independe do resultado
empírico do J-T.

### 3.2 Critério de atribuição

A classificação é feita **na planilha**, não em código. Cada projeto recebe um único
valor de `arquetipo` ∈ {apache, google, descentralizado} e, quando aplicável,
um valor de `instancia` (netflix, uber, spotify, linkedin).

### 3.3 Composição esperada do arquétipo descentralizado

Distribuição prevista: Netflix 7, Uber 5, Spotify 2, LinkedIn 1 (total 15). Esta
imbalance é assumida como característica do ecossistema público (Netflix publica
mais Java ativo que os outros três) e será:

1. Reportada em análise de subgrupo junto ao agregado.
2. Discutida como achado substantivo: organizações descentralizadas diferem em
   quanto Java mantêm publicamente.

## 4. Critérios de seleção de projetos

### 4.1 Critérios de inclusão (aplicados a todos os arquétipos)

1. **Linguagem:** ≥ 70% Java segundo a API do GitHub (`languages` endpoint).
2. **Tamanho:** 10k ≤ NCLOC ≤ 1M linhas Java não-comentadas no commit selecionado.
3. **Idade:** ≥ 3 anos entre primeiro commit e 2026-01-01.
4. **Contribuidores:** ≥ 10 contribuidores distintos no histórico.
5. **Release:** possui pelo menos um tag de release estável antes de 2026-01-01.
6. **Build:** compilável localmente com Maven ou Gradle (Bazel será tratado na §7.2).

### 4.2 Critérios de exclusão

- Projetos com `archived: true` no GitHub para Apache e descentralizado
  (ver §4.3, Saída 1). Para Google, projetos arquivados são incluídos sob
  Saída 2.
- Projetos cujo último commit precede 2024-01-01 (proxy de abandono mesmo sem flag).
- Projetos que são apenas wrappers/bindings finos (< 5k NCLOC de código próprio).

### 4.3 Saídas diferenciais sobre arquivamento (design assimétrico)

- **Apache — Saída 1:** exclui arquivados. Justificativa: pool enorme de projetos
  ativos, exclusão é trivial.
- **Descentralizado — Saída 1:** exclui arquivados. Justificativa: sem esta regra,
  o arquétipo colapsaria em "Netflix OSS arquivado 2018-2019". A lista de candidatos
  ativos foi validada e é suficiente.
- **Google — Saída 2:** inclui arquivados/manutenção, marcando explicitamente a
  coluna `status` ∈ {ativo, manutencao, arquivado}.

**Justificativa do design assimétrico (não é inconsistência metodológica):** o
estado "arquivado" carrega significados organizacionais distintos em cada arquétipo
e portanto não constitui uma categoria uniforme que possa ser tratada
simetricamente. No Google, arquivar é um sinal deliberado de manutenção concluída
("construímos, funciona, está pronto"). Na Apache Software Foundation, projetos
arquivados vão para o Apache Attic e isso sinaliza evaporação da comunidade
mantenedora — abandono, não conclusão. No ecossistema descentralizado, projetos
arquivados (Hystrix, Eureka, Ribbon, Archaius da Netflix; etc.) representam pivôs
estratégicos abandonados pela organização patrocinadora. Tratar os três como uma
única categoria "arquivado" mascararia três fenômenos qualitativamente distintos.
A assimetria reflete esta distinção e é declarada explicitamente para que
revisores entendam que se trata de decisão fundamentada.

**Mitigação do confundidor introduzido pela Saída 2 no Google:** os resultados do
Google serão reportados em duas versões:

1. **Primária:** apenas subconjunto `ativo` do Google vs. Apache vs. descentralizado.
2. **Robustez:** Google completo (ativo + manutenção + arquivado) vs. os outros.

Se as duas versões concordarem na direção, a conclusão é forte. Se discordarem,
isto próprio é um achado e será discutido na Seção 5.

### 4.4 Critério temporal uniforme

Para cada projeto selecionado:

1. Identificar o **último tag de release estável** anterior a 2026-01-01.
2. Executar `git checkout <tag>` para fixar o commit.
3. Registrar na planilha: `tag`, `sha`, `data_commit` (ISO 8601).
4. Rodar `sonar-scanner` sobre o commit fixado.

**A fonte de verdade da reprodutibilidade é o SHA**, não a data de análise no
SonarQube. Releases "estáveis" excluem alphas, betas, RCs, milestones e snapshots.

## 5. Amostra

- **Tamanho:** n = 15 por arquétipo, total N = 45.
- **Justificativa do tamanho:** convenience sample limitado pelo tempo de TCC e pela
  necessidade de build local reprodutível. O estudo é **poderado para detectar
  efeitos grandes apenas** (Cliff's δ ≥ ~0,47, que é o limiar convencional para
  "efeito grande"). Esta limitação é declarada na Seção 5 do TCC e reconhecida
  como ameaça à validade externa.

### 5.1 Lista de candidatos congelada

Candidatos primários (Fase 1):

- **Apache (15):** tomcat, zookeeper, kafka, cassandra, flink, commons-lang,
  commons-io, commons-collections, maven, lucene, camel, curator, dubbo, pulsar, mina.
- **Google (15):** guava, gson, dagger, auto, grpc-java, error-prone, truth, tink,
  jib, closure-compiler, j2objc, protobuf (Java), flatbuffers (Java), caliper,
  google-java-format.
- **Descentralizado (15):** Netflix — hollow, mantis, conductor, EVCache, spectator,
  metacat, dgs-framework; Uber — NullAway, AutoDispose, jvm-profiler, h3-java, tally;
  Spotify — github-java-client, completable-futures; LinkedIn — cruise-control.

### 5.2 Lista de reservas

Se um candidato falhar build ou violar critério de inclusão após inspeção, ele é
substituído por um projeto da lista de reservas **do mesmo arquétipo e, quando
descentralizado, da mesma instância preferencial**, mantendo a distribuição de §3.3.
A substituição é registrada na planilha em coluna `substituiu` apontando para o
candidato original. **Máximo de 3 substituições por arquétipo** antes de revisão do
protocolo (versão 1.2).

Reservas a serem definidas em passo subsequente antes de iniciar coleta oficial.

## 6. Configuração de ferramentas

### 6.1 SonarQube

- **Versão:** SonarQube Community Build **v26.2.0.119303**, **MQR Mode** ativo.
- **Nota sobre MQR Mode:** o MQR (Multi-Quality Rule) Mode é o modelo de
  categorização de regras introduzido nas versões 10.x da plataforma e adotado
  como padrão na linha Community Build a partir da v25. Sob MQR, regras são
  classificadas em múltiplas qualidades de software (manutenibilidade,
  confiabilidade, segurança) em vez do modelo legado de categoria única. Isto
  **não** afeta a métrica primária (`sqale_index` mantém a mesma definição
  semântica), mas pode produzir contagens de regras ligeiramente diferentes em
  reproduções feitas com SonarQube em modo legado. A reprodutibilidade exige
  versão **e** modo registrados.
- **Quality Profile:** `Sonar way` (default) para Java, na versão empacotada
  com a v26.2.0.119303. Sem customização.
- **Configuração do scanner:**
  - `sonar.sources=.` (ajustado por projeto quando `src/` existe)
  - `sonar.java.binaries` apontando para `target/` ou `build/` após compilação
  - `sonar.java.source` detectado do `pom.xml` / `build.gradle`,
    **não fixado em 1.8**
  - **Sem** `sonar.compiler.skip=true` (remover o uso atual nos scripts)
  - `sonar.scm.disabled=true` para evitar variação de métricas por blame

### 6.2 Métricas extraídas via API

Nível **projeto** (primário), endpoint `/api/measures/component`:

`sqale_index, ncloc, sqale_debt_ratio, code_smells, bugs, vulnerabilities,
complexity, cognitive_complexity, duplicated_lines_density, comment_lines_density`

Justificativa de exclusões em relação à proposta inicial:

- **`coverage`** removida: requer instrumentação de testes, não disponível para
  a maioria dos projetos da amostra. Valores ausentes ou zerados poluiriam as
  estatísticas descritivas. Cobertura é objeto de sub-estudo separado se vier
  a ser feito.
- **`reliability_rating`, `security_rating`, `sqale_rating`** removidas: são
  métricas ordinais (A-E) derivadas dos contadores brutos já incluídos.
  Adicionam ruído sem informação nova e tentam o analista a rodar testes sobre
  notas em letras, o que é estatisticamente impróprio. Se necessárias na
  discussão, são computadas post-hoc dos dados brutos.

Nível **arquivo** (secundário, exploratório), endpoint `/api/measures/component_tree`
com paginação completa (`ps=500`, iterar `p` até `paging.total`).

### 6.3 JDK

- **Versão pinada:** OpenJDK 17 LTS para todos os builds da amostra oficial.
- **Fallback:** se um projeto exigir JDK declarado diferente (verificável no
  `pom.xml`/`build.gradle`), tentar com o JDK declarado antes de marcar falha
  de build (ver §7.2).

### 6.4 Arcan (Fase 2, condicional)

Decisão de critério de inclusão Fase 2 adiada para versão 1.2 do protocolo,
após conclusão completa da Fase 1. Restrição conhecida: projetos Bazel (guava,
error-prone, grpc-java) provavelmente saem da Fase 2 por custo de extração de
bytecode — decisão formal na v1.2.

## 7. Pipeline de execução

### 7.1 Ordem canônica por projeto

1. `git clone` (se ainda não clonado)
2. Ler `tag` e `sha` da planilha
3. `git checkout <sha>` (usar SHA, não tag, para imutabilidade)
4. Build local (`mvn package -DskipTests` ou `./gradlew assemble`)
5. `sonar-scanner` com configuração de §6.1
6. Extração via API e escrita em `dados/YYYY-MM-DD/projeto.json`
7. Agregação em `dados/YYYY-MM-DD/consolidado.csv`

### 7.2 Falhas de build

Ordem de tentativas antes de marcar como falha:

1. Build com JDK 17 (default da amostra, §6.3).
2. Build com JDK declarado no projeto se diferente.
3. Pular testes (`-DskipTests`, `-x test`).

Após as três tentativas, projeto é marcado `build_status=falhou` e substituído
conforme §5.2.

## 8. Análise estatística

- **Ambiente:** Python 3.11+, `pandas`, `scipy.stats` (≥ 1.13 para
  `jonckheere_terpstra`), `pingouin`. R como backup se necessário.
- **Descritivas por arquétipo:** mediana, IQR, variância, coeficiente de variação,
  n, mínimo, máximo. Tabela obrigatória na Seção 4 do TCC.
- **Visualização obrigatória:** boxplot + strip plot por arquétipo, com subgrupo
  Netflix/Uber/Spotify/LinkedIn destacado dentro de descentralizado, e subgrupo
  ativo/manutenção/arquivado destacado dentro de Google.
- **Pipeline confirmatório (cinco testes obrigatórios):**

| # | Teste | Função | Status | Sobre o quê |
|---|---|---|---|---|
| 1 | Brown-Forsythe | Existência de diferença de variâncias | Complementar ao primário | Variância da densidade |
| 2 | Jonckheere-Terpstra (unilateral) | Diferença na ordem prevista | **Primário (H1)** | Variância da densidade |
| 3 | Kruskal-Wallis | Diferença em tendência central | Secundário (H1') | Densidade mediana |
| 4 | Cliff's δ (pareado) | Tamanho de efeito não-paramétrico | **Obrigatório** | Todos os pares |
| 5 | η² (de Kruskal-Wallis) | Tamanho de efeito omnibus | Obrigatório | Densidade mediana |

- **Decisão sobre H1:** rejeitar H0 a favor de H1 se e somente se o J-T
  unilateral retornar p < 0,05 **e** Cliff's δ apontar efeito grande
  (|δ| ≥ 0,474) em pelo menos um dos pares relevantes. Significância sem
  efeito grande é reportada como "padrão direcional fraco, não conclusivo".
- **Pré-comprometimento:** o script `analise_estatistica.py` será commitado
  no repositório do TCC **antes** da coleta oficial dos dados, para garantir
  que a análise não seja moldada pelos resultados.

## 9. Reprodutibilidade

- Toda execução gera um diretório `dados/YYYY-MM-DD/` imutável.
- A planilha mestre (`amostra.csv`) é versionada no repositório do TCC com cada
  mudança como commit.
- O SHA de cada projeto analisado é registrado e conferido ao abrir cada análise.
- Scripts fixam o commit **antes** de rodar o scanner (correção pendente dos
  scripts atuais — bloqueador #1 após congelamento deste protocolo).
- Versão do SonarQube (v26.2.0.119303), modo (MQR), versão do scanner, versão
  do JDK (17): registrados em `ambiente.txt` dentro de cada diretório
  `dados/YYYY-MM-DD/`.

## 10. Cronograma alvo

- **Abril 2026:** congelar protocolo (este documento), corrigir scripts, clonar
  restante da amostra, popular planilha, commitar `analise_estatistica.py`.
- **Maio 2026:** coleta oficial Fase 1 completa sobre N=45.
- **Junho 2026:** análise estatística, escrita das Seções 3-4.
- **Julho 2026:** Seção 5, revisão do texto, submissão SBQS 2026 CTICQS.
- **Agosto 2026:** se tempo permitir, Fase 2 (Arcan) sobre subconjunto.
- **Setembro 2026:** defesa.

## 11. Venues alvo (ordem de ambição)

1. SBQS 2026 CTICQS — primário.
2. SBQS 2026 Trilha de Trabalhos Técnicos ou SBCARS 2026 — se Fase 2 entregar.
3. ERES 2026 — soft landing para feedback.
4. **Não alvo:** SBES Research Track.

---

## Histórico de versões

- **1.0 (2026-04-14):** versão inicial congelada antes da coleta oficial.
- **1.1 (2026-04-14):** integração de decisões pós-revisão:
  - §2: H1 reformulada para deixar variância como primária e densidade
    secundária (H1'); critério de decisão sobre H1 explicitado em §8.
  - §3.1: justificativa *a priori* da ordem dos arquétipos adicionada,
    referenciando a literatura de governança como base da hipótese ordenada.
  - §4.3: justificativa do design assimétrico de Saída 1/Saída 2 expandida
    para deixar claro que é decisão fundamentada, não inconsistência.
  - §6.1: SonarQube pinado em v26.2.0.119303 Community Build com nota sobre
    MQR Mode e seu impacto em reprodutibilidade.
  - §6.2: lista de métricas reduzida — `coverage` e os três `*_rating`
    removidos com justificativa.
  - §6.3: JDK pinado em OpenJDK 17 LTS.
  - §8: pipeline estatístico reorganizado em tabela de cinco testes
    obrigatórios; critério de decisão sobre H1 combinando significância e
    tamanho de efeito; pré-comprometimento do script de análise.