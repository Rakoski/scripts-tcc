# Protocolo de Pesquisa — Estudo do Paradoxo da Governança em Escala

**Autor:** Mateus Rakoski
**Orientadora:** Evanise A. C. Ruiz
**Instituição:** IFPR — Campus Paranavaí
**Versão:** 1.5 — atualizada em 05/05/2026
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
- **H1 (primária, ordenada):** A **variância** da densidade de dívida
  técnica segue a ordem Google < Apache < Descentralizado, refletindo a ausência
  de mecanismos de enforcement organizacional à medida que a governança se
  descentraliza.
- **H1' (secundária):** A densidade mediana de dívida técnica difere entre os três
  arquétipos (sem direção pré-especificada).

**Teste primário:** Brown-Forsythe (Levene com `center='median'`) sobre
homogeneidade de variâncias da densidade de dívida entre os três arquétipos,
α = 0,05. Brown-Forsythe testa se as variâncias diferem entre os grupos sem
assumir normalidade nem homocedasticidade prévia, sendo o teste padrão para
esta pergunta na literatura estatística. A ordem `google < apache <
descentralizado` é fixada *a priori* a partir da literatura de governança
(ver §3.1) **antes** de qualquer coleta de dados, e a confirmação dessa ordem
é verificada descritivamente sobre as variâncias amostrais (não por teste
inferencial sobre a ordenação).

**Tamanho de efeito obrigatório:** Cliff's δ pareado entre os três pares de
arquétipos (Google–Apache, Apache–Descentralizado, Google–Descentralizado),
calculado sobre as densidades de dívida. Cliff's δ é não-paramétrico, robusto
a outliers, e tem interpretação direta como a probabilidade de um projeto
escolhido ao acaso de um arquétipo apresentar densidade maior do que um
projeto de outro arquétipo. Limiares de Romano et al. (2006): |δ| < 0,147
negligenciável; 0,147 ≤ |δ| < 0,33 pequeno; 0,33 ≤ |δ| < 0,474 médio;
|δ| ≥ 0,474 grande. A partir da v1.5, Cliff's δ é reportado como tamanho de efeito descritivo, mas não constitui condição da regra de decisão pré-registrada (ver §8.2 reformulada).

Teste único confirmatório (v1.5): Brown-Forsythe é o único teste confirmatório do estudo, sob a regra de decisão revisada em §8.2 (C1 ∧ C2). Cliff's δ é tamanho de efeito reportado descritivamente, não componente da regra de decisão. Todos os demais procedimentos mencionados nesta seção e na §8 — Kruskal-Wallis, η², Jonckheere-Terpstra, correlação parcial Spearman — são descritivos / exploratórios e não constituem evidência confirmatória, independentemente de
seus p-valores. Sem correção para múltiplas comparações porque há apenas um
teste confirmatório. Esta decisão é congelada e não revisável após observação
dos dados.

**Compromisso de pré-registro:** a ordem `google < apache < descentralizado` é
congelada nesta versão do protocolo. Se a ordem observada das variâncias
amostrais não corresponder à ordem prevista, isto é reportado como evidência
contra H1 e o protocolo **não** será re-rodado com ordem alternativa. A
análise descritiva e Cliff's δ continuam revelando o padrão real
independentemente.

**Métrica primária:** densidade de dívida técnica = `sqale_index / ncloc`,
em minutos por linha de código não-comentada, agregada ao nível de projeto.
**Métrica secundária:** densidade mediana de dívida (mesma fórmula, foco em
tendência central em vez de variância). Adicionalmente ao teste primário Brown-Forsythe, será reportada a variância intra-organizacional para cada organização do arquétipo descentralizado com n ≥ 2 (Netflix, Uber, LinkedIn). Para o subconjunto do arquétipo descentralizado (n=10, sem Spotify presente na composição final), será calculado o ICC(1) com organização como fator aleatório, para quantificar a proporção da variância atribuível a diferenças inter-organizacionais. Estas análises são exploratórias e não constituem testes confirmatórios da hipótese H1.

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
empírico do teste primário.

### 3.2 Critério de atribuição

A classificação é feita **na planilha**, não em código. Cada projeto recebe um único
valor de `arquetipo` ∈ {apache, google, descentralizado} e, quando aplicável,
um valor de `instancia` (netflix, uber, spotify, linkedin).

### 3.3 Composição efetiva do arquétipo descentralizado

Distribuição efetiva da amostra após aplicação dos critérios refinados em v1.4:
**Netflix 5, Uber 2, LinkedIn 3, Spotify 0 (total 10).** A trajetória da
composição ao longo das versões do protocolo (v1.1: Netflix 7, Uber 5, Spotify 2,
LinkedIn 1; v1.2: Netflix 6, Uber 5, LinkedIn 3, Spotify 1; v1.4: composição
final acima) reflete a aplicação progressivamente mais rigorosa dos critérios
de inclusão e a revalidação empírica de NCLOC e contribuidores via Sonar e
GitHub API.

Esta composição é mantida como achado substantivo sobre a presença pública de
Java em cada organização — não como ruído amostral a ser corrigido — e será:

1. Reportada em análise de subgrupo junto ao agregado.
2. Discutida como achado substantivo: organizações descentralizadas diferem em
   quanto Java mantêm publicamente.
3. Subgrupo Spotify (n=0) ausente da amostra final, com discussão substantiva
   em §5 do TCC sobre o significado dessa ausência. Subgrupo Uber (n=2)
   apresenta ponto único insuficiente para análise inferencial intra-subgrupo;
   Boxplots e estatísticas descritivas dentro do arquétipo descentralizado
   tratarão Uber como dois pontos individuais agregados ao subgrupo. Análises
   intra-arquétipo serão restritas a Netflix (n=5) e LinkedIn (n=3).

## 4. Critérios de seleção de projetos

### 4.1 Critérios de inclusão (aplicados a todos os arquétipos)

1. **Linguagem:** ≥ 70% Java segundo a API do GitHub (`languages` endpoint).
2. **Tamanho:** 10k ≤ NCLOC ≤ 1M linhas Java não-comentadas no commit selecionado.
3. **Idade:** ≥ 3 anos entre primeiro commit e 2026-01-01.
4. **Contribuidores:** ≥ 25 contribuidores distintos no histórico.
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

> **Atualização v1.4:** Após aplicação do critério temporal ≤ 24 meses (v1.4),
> nenhum projeto Google arquivado satisfaz simultaneamente todos os critérios
> de inclusão. Na composição final, todos os 11 projetos Google têm
> `status='ativo'`. As duas versões (primária e robustez) colapsam no mesmo
> subconjunto, e o reporte duplo torna-se redundante. A coluna `status` é
> mantida no schema da planilha por consistência metodológica e para
> reprodutibilidade.

### 4.4 Critério temporal uniforme

Para cada projeto selecionado:

1. Identificar o **último tag de release estável** anterior a 2026-01-01.
2. Executar `git checkout <tag>` para fixar o commit.
3. Registrar na planilha: `tag`, `sha`, `data_commit` (ISO 8601).
4. Rodar `sonar-scanner` sobre o commit fixado.

**A fonte de verdade da reprodutibilidade é o SHA**, não a data de análise no
SonarQube. Releases "estáveis" excluem alphas, betas, RCs, milestones e snapshots.

## 5. Amostra

- **Tamanho final (v1.4):** n = 14/11/10 (Apache/Google/Descentralizado),
  total N = 35.
- **Tamanho originalmente projetado (v1.0–v1.3):** n = 15 por arquétipo,
  total N = 45. Composição revista para N = 35 em v1.4 após aplicação
  rigorosa dos critérios de inclusão (ver histórico de versões).

- **Justificativa do tamanho:** convenience sample limitado pelo tempo
  de TCC e pela necessidade de build local reprodutível. A composição
  efetiva reflete a aplicação dos critérios à oferta pública de Java
  sob cada arquétipo, não otimização de poder.

- **Poder estatístico (v1.5):** simulação Monte Carlo com 10000 réplicas
  sob amostra final n=14/11/10 estimou poder da regra de decisão revisada
  (§8.2, C1 ∧ C2) em **aproximadamente 9% para razão de variância 3.36×**
  entre Google e Descentralizado. Detalhes em v1.5 do histórico de versões.

- **Implicação para interpretação:** resultado não-significativo no
  Brown-Forsythe **não constitui evidência de equivalência** entre
  arquétipos, sob poder limitado da amostra. Esta limitação é declarada
  explicitamente em §5 do TCC.

- **Tratamento de não-independência intra-arquétipo:** a análise primária
  (Brown-Forsythe one-way) trata os projetos de cada arquétipo como
  observações independentes. No arquétipo descentralizado, esta independência
  é apenas aproximada, dado que múltiplos projetos provêm da mesma
  organização. A decomposição complementar de variância (ICC) busca
  caracterizar a magnitude dessa não-independência e contextualizar a
  interpretação dos resultados.

### 5.1 Lista final de projetos da amostra (v1.4)

A composição abaixo é a amostra final pré-coleta após aplicação dos
critérios refinados em v1.4 e revalidação via Sonar:

- **Apache (n=14):** tomcat, zookeeper, kafka, cassandra, flink,
  commons-lang, commons-io, commons-collections, maven, lucene, camel,
  curator, dubbo, pulsar.

- **Google (n=11):** guava, gson, dagger, auto, grpc-java, error-prone,
  truth, conscrypt, jib, google-http-java-client, j2objc.

- **Descentralizado (n=10):**
  - Netflix (5): hollow, mantis, EVCache, spectator, eureka.
  - Uber (2): NullAway, cadence-java-client.
  - LinkedIn (3): ambry, rest.li, cruise-control.
  - Spotify (0): nenhum projeto satisfaz simultaneamente os critérios
    de inclusão após aplicação do critério temporal v1.4.

A trajetória de composição entre versões (Apache: 15→14, Google: 15→11,
Descentralizado: 15→10) e as substituições documentadas estão registradas
no histórico de versões da v1.4.

### 5.2 Substituições e saídas (v1.4 — congeladas)

A política de substituições foi aplicada em v1.4 com os seguintes resultados:

- **Substituições registradas:** guice → conscrypt (Google), brooklin →
  rest.li (LinkedIn). Detalhes em v1.4 do histórico.

- **Saídas sem substituto:** tchannel-java, AutoDispose, h3-java,
  github-java-client, flogger, jimfs, google-java-format, compile-testing,
  concurrency-limits, commons-codec. A não-substituição preserva a
  composição como reflexo direto da aplicação dos critérios à oferta
  pública de Java sob cada arquétipo, em consonância com a postura de
  v1.1 e v1.2 sobre composição como achado substantivo.

- **Limite de substituições por arquétipo (v1.0):** "Máximo de 3
  substituições antes de revisão do protocolo" foi observado em v1.4
  (Google: 5 saídas, mas com 1 substituição efetiva; Descentralizado: 6
  saídas, com 1 substituição efetiva). Excesso de saídas sem substituição
  é documentado como aplicação rigorosa de critérios, não violação
  metodológica.

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
  com a v26.2.0.119303. Sem customização. As medidas reportadas neste estudo
  são objetivas condicionalmente ao uso da Quality Profile `Sonar way` default
  empacotada com SonarQube Community Build v26.2.0.119303 em MQR Mode.
  Reproduções com versão diferente, modo legado, ou Quality Profile
  customizada podem produzir valores absolutos diferentes.
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

- **`coverage`** removida definitivamente: requer instrumentação de testes incompatível com o pipeline -DskipTests da §7.2. Reintroduzir cobertura geraria três classes de dados (cobertura real, cobertura zero por testes pulados, cobertura ausente por falta de testes), missing-not-at-random entre arquétipos, poluindo qualquer comparação. A análise de cobertura é deixada como trabalho futuro com pipeline próprio (build com testes, ingestão de relatórios JaCoCo), fora do escopo deste TCC.

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

Decisão de critério de inclusão Fase 2 adiada para versão futura do protocolo,
após conclusão completa da Fase 1. Restrição conhecida: projetos Bazel (guava,
error-prone, grpc-java) provavelmente saem da Fase 2 por custo de extração de
bytecode — decisão formal posterior.

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

- **Ambiente:** Python 3.11+, `pandas`, `scipy.stats`, `pingouin`. R como
  backup se necessário.
- **Descritivas por arquétipo:** mediana, IQR, variância, desvio-padrão,
  mínimo, máximo, n. Tabela obrigatória na Seção 4 do TCC.
- **Visualização obrigatória:** boxplot + strip plot por arquétipo, com subgrupo
  Netflix/Uber/Spotify/LinkedIn destacado dentro de descentralizado, e subgrupo
  ativo/manutenção/arquivado destacado dentro de Google.
- **Pipeline analítico:**

| # | Procedimento | Função | Status | Sobre o quê |
|---|---|---|---|---|
| 1 | Tabela descritiva por arquétipo (mediana, IQR, variância, std, min, max, n) | Apresentação primária da evidência | Obrigatório | Densidade |
| 2 | Boxplot + strip plot por arquétipo | Visualização da dispersão | Obrigatório | Densidade |
| 3 | Brown-Forsythe (Levene com `center='median'`) | Teste de homogeneidade de variâncias | **Primário (H1)** | Variância da densidade |
| 4 | Cliff's δ pareado (3 pares) | Tamanho de efeito não-paramétrico | **Obrigatório** | Densidade, todos os pares |
| 5 | Kruskal-Wallis + η² | Diferença em tendência central (H1') | Secundário | Densidade mediana |
| 6 | Jonckheere-Terpstra sobre densidades | Tendência monotônica (exploratório) | Exploratório | Densidade |
| 7 | Decomposição do sqale_index por type e tag de regra | Diagnóstico de viés de Quality Profile | Exploratório (v1.4) | Composição da dívida |
| 8 | Top-10 regras dominantes por projeto | Diagnóstico de viés de stack tecnológico | Exploratório/Suplemento (v1.4) | Regras individuais |
| 9 | ICC(1) intra-arquétipo descentralizado | Decomposição de variância inter vs intra-organização | Descritivo (v1.4) | Variância da densidade |
| 10 | Correlação parcial Spearman estendida (NCLOC, idade do projeto, idade do snapshot) | Controle analítico de confundidores | Descritivo (v1.4) | Densidade |

- **Pré-comprometimento:** o script `analise_estatistica.py` será commitado
  no repositório do TCC **antes** da coleta oficial dos dados, para garantir
  que a análise não seja moldada pelos resultados.

### 8.1 Tratamento de confundidores (NCLOC e idade)

A amostra apresenta diferenças sistemáticas em NCLOC e idade entre arquétipos (medianas: Apache 51k LOC / 18,7 anos; Google 16k LOC / 12,9 anos; descentralizado 21k LOC / 8,2 anos). Esses confundidores não são tratados por manipulação amostral — restringir Apache a projetos pequenos e jovens não representaria Apache — mas analiticamente:

1. Reporte prominente da composição amostral em Seção 4 antes de qualquer inferência: distribuição de NCLOC, idade, e contadores de contribuidores por arquétipo, com visualização (boxplot ou strip plot).
2. Correlação parcial baseada em rank (Spearman parcial) entre arquétipo (codificado ordinalmente como em §3.1) e densidade de dívida, controlando para log(NCLOC), idade do projeto e idade do snapshot (v1.4). Reportada como análise descritiva, não confirmatória.
3. Análise de robustez em sub-amostra de tamanho comparável: re-execução do Brown-Forsythe sobre o subconjunto de projetos com NCLOC entre 10k e 100k (faixa de sobreposição entre arquétipos). Se a direção do efeito persistir, isto fortalece a interpretação de governança; se inverter ou desaparecer, isto enfraquece e será discutido honestamente na Seção 5.

A análise de robustez é descritiva, não confirmatória — ela não substitui o Brown-Forsythe primário sobre a amostra completa, que continua sendo o teste pré-registrado.

### 8.2 Regra de decisão sobre H1 (v1.5)

H0 é rejeitada a favor de H1 se e somente se as duas condições abaixo
forem simultaneamente satisfeitas:

1. **Significância:** Brown-Forsythe retorna F > F-crítico empírico
   (calibrado conforme §8) sobre a homogeneidade das variâncias entre
   os três arquétipos.

2. **Ordem:** a ordenação das variâncias amostrais corresponde à ordem
   prevista *a priori* — variância(Google) < variância(Apache) < variância(Descentralizado).

Falha em qualquer das duas condições é reportada como falha de H1, com
interpretação específica:

- **C1 sem C2:** variâncias diferem mas não na ordem prevista — evidência
  contra H1, sugere mecanismo causal alternativo a ser discutido em §5
  do TCC.
- **Ausência de C1:** falha em detectar diferença de variâncias — sob
  poder de ~9% (v1.5), não constitui evidência de equivalência entre
  arquétipos.

Cliff's δ pareado é reportado como tamanho de efeito descritivo (limiares
de Romano et al., 2006), mas não constitui condição da regra de decisão
desde v1.5 (justificativa conceitual e empírica em v1.5 do histórico).

Histórico desta seção: v1.3 introduziu três condições conjuntivas (Brown-Forsythe + ordem + Cliff's δ ≥ 0,474). v1.5 reformulou para
duas condições, removendo a condição sobre Cliff's δ após simulação Monte
Carlo demonstrar que C3 reduzia o poder da regra sem agregar informação
sobre H1.

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

- **Abril 2026:** congelamento inicial do protocolo (v1.0–v1.3),
  correção de scripts, clonagem inicial da amostra.
- **Início de Maio 2026:** revisão metodológica adversarial e congelamento
  final do protocolo (v1.4 e v1.5), incluindo composição amostral final
  N=35 e regra de decisão simplificada (C1 ∧ C2).
- **Maio 2026:** coleta oficial Fase 1 completa sobre **N=35**.
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

- **1.2 (2026-04-27):** ajustes pós-revisão pré-coleta:
  - §2: J-T unilateral sobre variância confirmado como ÚNICO teste
    confirmatório. Brown-Forsythe, Kruskal-Wallis, Cliff's δ e η²
    explicitamente rebaixados a descritivos/exploratórios no corpo da §2,
    não apenas em nota.
  - §3.3: distribuição efetiva da amostra descentralizada corrigida para
    Netflix 6, Uber 5, LinkedIn 3, Spotify 1 (total 15), com justificativa
    empírica. Nota adicionada sobre Spotify n=1 não suportar análise
    inferencial intra-subgrupo.
  - §5: declaração explícita de poder estatístico (~70-75% para δ ≥ 0,474
    com n=15 por grupo, α=0,05 unilateral). Resultados não-significativos
    não serão interpretados como evidência de equivalência entre
    arquétipos.
  - §6.1: parágrafo adicionado sobre objetividade condicional das medidas
    em relação à Quality Profile `Sonar way` default em v26.2.0.119303
    MQR Mode.
  - §6.2: `coverage` removida definitivamente (não readicionada) com
    justificativa expandida sobre missing-not-at-random.
  - §8: nova subseção §8.1 introduzindo tratamento analítico de
    confundidores (NCLOC, idade) via correlação parcial Spearman e
    análise de robustez em sub-amostra de tamanho comparável (10k-100k
    NCLOC). Confundidores tratados analiticamente em vez de via
    manipulação amostral. Existing decision rule on H1 reorganized as
    §8.2.
  - Título do TCC ajustado para incluir "Code-Level Technical Debt" /
    "Dívida Técnica em Nível de Código" e "Java", deixando explícito o
    nível de medição e o escopo de linguagem.
  - Introdução do TCC: mecanismo causal "diversidade de contribuidores"
    substituído por "ausência de mecanismos de enforcement organizacional",
    consistente com a distribuição observada de contribuidores
    (Apache mediana 289 > Google 131 > descentralizado 55).
  - Introdução do TCC: parágrafo de disclosure de composição amostral
    adicionado antes de §1.1, declarando confundidores de tamanho e
    idade upfront e o compromisso de tratá-los analiticamente.
  - Introdução do TCC: parágrafo SQALE estendido para declarar
    explicitamente que o estudo mede a assinatura código-nível das
    escolhas de governança, não degradação arquitetural; análise
    arquitetural via Arcan declarada como trabalho futuro fora do
    escopo deste paper.

- **1.3 (2026-05-03):** simplificação do pipeline confirmatório, decidida
  antes da coleta oficial:
  - §2: Brown-Forsythe (Levene com `center='median'`) promovido a teste
    primário e único confirmatório sobre a homogeneidade das variâncias
    de densidade de dívida entre arquétipos. Justificativa: Brown-Forsythe
    é o teste padrão da literatura para esta pergunta, sem premissas
    paramétricas relevantes, e dispensa o uso de bootstrap sobre
    estatísticas de variância que seria necessário para aplicar
    Jonckheere-Terpstra ao mesmo objeto. Pipeline mais simples reduz
    riscos de implementação e facilita revisão metodológica.
  - §2: Jonckheere-Terpstra removido como teste confirmatório. Mantido
    apenas como procedimento exploratório sobre as densidades brutas
    (não sobre variâncias), reportado na §4 do TCC apenas como suporte
    descritivo da ordenação.
  - §2: Cliff's δ pareado mantido como tamanho de efeito obrigatório,
    com limiares de Romano et al. (2006) explicitados.
  - §8: tabela do pipeline analítico reorganizada para refletir a nova
    hierarquia (descritiva + visualização + Brown-Forsythe + Cliff's δ
    como núcleo, Kruskal-Wallis e J-T como secundários/exploratórios).
  - §8.2: nova subseção dedicada à regra de decisão sobre H1, com as
    três condições conjuntivas (significância via Brown-Forsythe + ordem
    descritiva prevista + magnitude de Cliff's δ ≥ 0,474 em pelo menos
    um par) e interpretação explícita de cada modo de falha.
  - Esta mudança é uma simplificação metodológica registrada antes da
    coleta oficial dos dados (cf. §10 — coleta prevista para maio de
    2026). Não constitui resposta a observações nos dados.
- **1.4 05/05/2026:** ajustes pré-coleta documentados em sessão de revisão metodológica adversarial:

  ### Critérios de inclusão e exclusão

  - **§4.1 #2 — esclarecimento operacional (não modificação).** A medida de
    "linhas Java não-comentadas" é operacionalizada como o valor reportado
    pelo SonarQube em `ncloc_language_distribution[java]`, ou seja, o
    componente Java do `ncloc` total. Esta operacionalização é coerente
    com a delimitação da porção do código-fonte sob análise estática
    Java. O critério literal `10k ≤ NCLOC Java ≤ 1M` é aplicado a esse
    valor.

  - **§4.1 #4 — fonte autoritativa de contagem de contribuidores.**
    Contagem feita exclusivamente via GitHub API
    `/repos/{owner}/{repo}/contributors?per_page=100&anon=false` com
    paginação completa quando aplicável. Contagem da sidebar do GitHub
    descartada como fonte por discrepância sistemática observada entre
    sidebar e API durante revalidação (caso ilustrativo: uForwarder
    reporta 28 contribuidores na sidebar, 6 via API).

  - **§4.2 — critério temporal adicional.** A última tag de release
    pré-2026-01-01 deve datar de 2024-05-01 ou posterior (idade do
    snapshot ≤ 24 meses em relação à data planejada de coleta,
    2026-05). Justificativa: aplicação de regras Sonar contemporâneas a
    snapshots significativamente defasados introduz confundidor entre
    arquétipo e idade do snapshot, dado que projetos em manutenção do
    arquétipo descentralizado apresentam snapshots sistematicamente
    mais antigos que projetos Apache e Google. O critério é aplicado
    uniformemente aos três arquétipos. Inclusão das organizações no
    descentralizado preserva a interpretação substantiva da §3.3:
    organizações que mantêm pouco Java público com release recente
    contribuem com menos projetos elegíveis, e isto é reportado como
    achado, não corrigido por flexibilização de critério.

  - **§4.2 — referência temporal do status `archived`.** Status
    `archived` aferido em DATA EXATA via GitHub API (`GET /repos/{owner}/{repo}`,
    campo `.archived`). Mudanças subsequentes de status não alteram a
    composição da amostra.

  ### Composição amostral revisada e congelada

  Após aplicação rigorosa dos critérios e revalidação completa de
  `ncloc_language_distribution[java]` para todos os candidatos via Sonar
  Community Build v26.2.0.119303 (não confiando em medições prévias da
  planilha de candidatos):

  | Arquétipo | n | Detalhamento |
  |---|---|---|
  | Apache | 14 | tomcat, zookeeper, kafka, cassandra, flink, commons-lang, commons-io, commons-collections, maven, lucene, camel, curator, dubbo, pulsar |
  | Google | 11 | guava, gson, dagger, auto, grpc-java, error-prone, truth, conscrypt, jib, google-http-java-client, j2objc |
  | Descentralizado | 10 | Netflix (5): hollow, mantis, EVCache, spectator, eureka. Uber (2): NullAway, cadence-java-client. LinkedIn (3): ambry, rest.li, cruise-control. Spotify (0). |
  | **TOTAL** | **35** | |

  Substituições aplicadas pré-coleta (registradas com motivo):

  - **guice → conscrypt** (Google): guice violou critério temporal
    (snapshot 35,6 meses), conscrypt o substitui mantendo n=11. Conscrypt
    teve coleta especial documentada em §6.3 (fallback JDK 8 e build
    parcial JNI nativo).
  - **brooklin → rest.li** (LinkedIn): brooklin violou critério temporal
    (snapshot 30,0 meses).

  Saídas sem substituto disponível dentro dos critérios:

  - **tchannel-java** (Uber): arquivado, em conformidade com Saída 1 do
    descentralizado (§4.3).
  - **AutoDispose** (Uber): violação temporal (33,2 meses).
  - **h3-java** (Uber): contribuidores < 25 via API (10 contribuidores
    reais, divergente de 20 reportados na sidebar).
  - **github-java-client** (Spotify): NCLOC Java < 10k (6636) e
    arquivado durante a revalidação de protocolo.
  - **flogger** (Google): NCLOC Java < 10k (7503).
  - **jimfs** (Google): NCLOC Java < 10k (7560).
  - **google-java-format** (Google): NCLOC Java < 10k (4675).
  - **compile-testing** (Google): NCLOC Java < 10k (3246).
  - **concurrency-limits** (Netflix): NCLOC Java < 10k (2617).
  - **commons-codec** (Apache): NCLOC Java < 10k (9573, falha por 4%).

  Após análise sistemática das listagens públicas das organizações
  Uber, LinkedIn, Google e Spotify (orgs `uber`, `linkedin`, `google`,
  `googleapis`, `GoogleContainerTools`, `spotify`), nenhum candidato
  satisfez simultaneamente todos os critérios para os papéis de
  substituto de tchannel-java, AutoDispose, h3-java e github-java-client.
  Para commons-codec (Apache), substituição é trivial dentro do pool
  Apache, mas a saída foi mantida sem substituto para preservar
  simetria de tratamento com Google (que perdeu 4 projetos sem
  compensação) e para manter a composição como reflexo direto da
  aplicação dos critérios à oferta pública de Java sob cada arquétipo.

  **Achado descritivo declarado, a ser reportado em §3.3 e §4 do TCC:**
  A presença pública de projetos Java elegíveis aos critérios deste
  estudo é desigual entre as organizações do arquétipo descentralizado.
  Spotify desce de n=1 (v1.3) para n=0 (v1.4) com a perda de
  github-java-client por NCLOC Java insuficiente e arquivamento
  superveniente. Uber mantém apenas 2 projetos elegíveis após
  filtragem rigorosa. Esta assimetria é mantida como evidência
  substantiva sobre a operacionalização da governança descentralizada
  em open-source Java, não como ruído amostral, em consonância com a
  postura adotada na v1.1 e v1.2 do protocolo.

  ### Saída 2 do Google revisitada

  Após aplicação do critério temporal ≤ 24 meses, nenhum projeto
  Google arquivado satisfaz simultaneamente todos os critérios de
  inclusão. Portanto, na composição final, **Saída 2 não introduz
  subgrupo arquivado/manutenção dentro do Google**. A análise
  primária e a análise de robustez declaradas em §4.3 colapsam no
  mesmo subconjunto da amostra. A coluna `status` permanece registrada
  para consistência metodológica, com valor uniformemente `ativo`
  para todos os 11 projetos Google.

  ### Análises complementares adicionadas (exploratórias)

  Em resposta a vetores de ataque identificados em revisão metodológica
  adversarial:

  - **§8 — Decomposição do sqale_index por categoria de regra Sonar.**
    Para cada projeto, será reportada a proporção do `sqale_index`
    atribuível a `type` ∈ {CODE_SMELL, BUG, VULNERABILITY} e a `tag`
    da regra (convention, design, security, performance, etc.). Esta
    análise diagnostica potencial viés do Quality Profile Sonar way
    default, no qual diferenças entre arquétipos podem refletir
    convergência cultural com convenções externas formalizadas em vez
    de variação na qualidade arquitetural intrínseca. Análise é
    descritiva, não confirmatória.

  - **§8 — Top-10 regras dominantes por projeto.** Para cada projeto,
    listagem das 10 regras com maior contribuição absoluta ao
    `sqale_index`. Material disponibilizado como suplemento online,
    com análise qualitativa em §5 do TCC sobre potencial viés de
    stack tecnológico (regras dedicadas a bibliotecas e frameworks
    específicos contribuem desproporcionalmente quando uma stack é
    predominante em um arquétipo).

  - **§8.1 — Idade do snapshot como variável de controle adicional.**
    A correlação parcial Spearman é estendida para incluir, além de
    log(NCLOC) e idade do projeto, a idade do snapshot (dias entre a
    data da última tag e a data efetiva da coleta). Inspeção visual
    da relação densidade × idade do snapshot por arquétipo será
    reportada em §4 do TCC para diagnosticar potencial confounding
    residual com idade de snapshot.

  - **§8.1 — ICC intra-arquétipo descentralizado.** Para o subconjunto
    do descentralizado com n ≥ 2 por organização (Netflix=5, Uber=2,
    LinkedIn=3), será calculado o ICC(1) com organização como fator
    aleatório, quantificando a proporção da variância da densidade de
    dívida no descentralizado atribuível a diferenças
    inter-organizacionais. Análise é descritiva, com IC reportado, e
    sujeita a imprecisão dado os tamanhos de subgrupo. Não constitui
    teste confirmatório.

  ### Recálculo de poder estatístico

  Com composição revisada n = 14/11/10 (Apache/Google/Descentralizado),
  a declaração de poder de v1.2 (~70-75% para Cliff's δ ≥ 0,474 sob
  n=15 por grupo) deixa de ser válida. O poder real do teste primário
  Brown-Forsythe e da regra conjuntiva de §8.2 será caracterizado via
  simulação Monte Carlo com 10000 réplicas, sob distribuições calibradas
  pela literatura SQALE e por diferentes razões de variância entre
  arquétipos, antes da coleta oficial dos dados. O resultado dessa
  simulação será documentado em emenda subsequente (v1.5 ou nota de
  rodapé ao final desta seção) e a regra de decisão de §8.2 será
  reavaliada à luz desse resultado.

  ### Postura sobre o pré-registro

  Esta versão v1.4 documenta esclarecimentos operacionais (critério
  NCLOC, fonte de contribuidores) e mudanças metodológicas conscientes
  (critério temporal, composição revisada) feitas antes da coleta
  oficial dos dados (prevista para 2026-05, conforme §10). Nenhuma
  decisão registrada nesta versão foi informada por observação dos
  dados de sqale_index ou de qualquer métrica primária da Fase 1.
  As substituições e saídas registradas baseiam-se exclusivamente em
  metadados estruturais dos repositórios (status archived, contagem de
  commits, contagem de contribuidores, NCLOC Java) e em revalidação
  via Sonar para projetos limítrofes ao critério §4.1 #2. O
  pré-registro permanece intacto.

- **1.5 05/05/2026:** Reformulação da regra de decisão sobre H1, baseada em
  simulação Monte Carlo do desenho final (n=14/11/10):

  ### Calibração empírica de F-crítico
  
  Sob lognormal calibrada para densidade SQALE (μ=2.5, σ=0.6 sob H0) com
  n total = 35, a estatística de Brown-Forsythe não segue exatamente a
  distribuição F(2, 32) teórica. Simulação com 10000 réplicas sob H0
  produziu F-crítico empírico de 3.0578 (vs F-crítico teórico de 3.2945,
  desvio relativo de -7.2%). Teste de Kolmogorov-Smirnov rejeita
  compatibilidade com F(2, 32) (p < 1e-5). A análise estatística usará
  F-crítico empírico calibrado para o desenho específico, não tabela F
  teórica. Esta exigência metodológica é necessária para reproduções:
  o pipeline `analise_estatistica.py` deve gerar a distribuição nula
  empírica antes de aplicar testes confirmatórios.
  
  ### Reformulação de §8.2 — regra de decisão sobre H1
  
  A regra conjuntiva original (C1 ∧ C2 ∧ C3 da v1.3) foi reformulada
  pré-coleta para C1 ∧ C2, removendo a condição original §8.2(3)
  (Cliff's δ ≥ 0.474 em pelo menos um par). A reformulação tem
  justificativa dupla:
  
  **(a) Conceitual:** Cliff's δ é uma medida de dominância estocástica
  em tendência central — ele captura o quanto valores de um grupo
  tendem a ser maiores que os de outro. H1 prediz diferença de
  *variância*, condição lógica e estatisticamente distinta de
  dominância em tendência central. Distribuições com mesma média e
  diferentes variâncias podem ter Cliff's δ próximo de zero. A
  inclusão de C3 misturava operacionalmente duas hipóteses
  conceitualmente distintas.
  
  **(b) Empírica:** simulação Monte Carlo com 10000 réplicas sob
  cenários com razão de variância entre arquétipos extremos variando
  de 1× a 161000× revelou que P(C3) varia apenas entre 0.124 e 0.154,
  independente da magnitude do efeito. C3 opera na prática como filtro
  de taxa aproximadamente constante sob amostras pequenas, sem agregar
  informação sobre H1. A inclusão de C3 reduzia o poder da regra
  conjuntiva por aproximadamente fator 5-6 sem aumentar especificidade.
  
  Cliff's δ é mantido como tamanho de efeito reportado
  descritivamente em §8 (Tabela 1 e tabela analítica), com limiares
  de Romano et al. (2006), mas não constitui condição da regra de
  decisão pré-registrada.
  
  **Regra de decisão revisada:** H0 é rejeitada a favor de H1 se e
  somente se as duas condições abaixo forem simultaneamente
  satisfeitas:
  
  1. **Significância:** Brown-Forsythe retorna F > F-crítico empírico
     (calibrado conforme §8 acima) sobre a homogeneidade das variâncias
     entre os três arquétipos.
  2. **Ordem:** a ordenação das variâncias amostrais corresponde à
     ordem prevista a priori — variância(Google) < variância(Apache) < variância(Descentralizado).
  
  Falha em qualquer das duas condições é reportada como falha de H1,
  com interpretação específica:
  
  - C1 sem C2: variâncias diferem mas não na ordem prevista — evidência
    contra H1, sugere mecanismo causal alternativo a ser discutido em §5.
  - Ausência de C1: falha em detectar diferença de variâncias —
    sob poder limitado da amostra, não constitui evidência de
    equivalência.
  
  ### Recálculo de poder estatístico
  
  Simulação Monte Carlo do poder da regra revisada (C1 ∧ C2) sob
  cenários realistas para SQALE:
  
  | Razão variância | P(C1) | P(C2) | P(C1 ∧ C2) |
  |---|---|---|---|
  | 1.78× | 0.073 | 0.335 | 0.035 |
  | 2.51× | 0.115 | 0.438 | 0.068 |
  | 3.36× | 0.139 | 0.512 | 0.090 |
  
  O poder da regra revisada é aproximadamente **9% para razão de
  variância de 3.36×** entre Google e Descentralizado, sob amostra
  final n=14/11/10. A declaração de poder de 70-75% em v1.2 §5 é
  superada por esta análise e fica revogada.
  
  ### Implicação para interpretação
  
  Resultado significativo (C1 ∧ C2 satisfeitos) constitui evidência
  forte para H1, dado o poder limitado: significa que o efeito real
  é provavelmente substantivo, e não detectado por acaso.
  
  Resultado não-significativo, sob poder de 9%, **não constitui
  evidência de equivalência** entre arquétipos. É consistente com:
  (a) ausência real de diferença substantiva, (b) efeito real
  presente mas não detectado pela amostra. A Seção 5 do TCC discute
  ambas interpretações.
  
  ### Postura sobre o pré-registro
  
  Esta versão v1.5 documenta uma reformulação metodológica feita
  antes da coleta oficial dos dados (prevista para 2026-05). A
  decisão de remover C3 baseou-se em (a) análise conceitual sobre
  o que cada condição mede e (b) simulação prévia de poder do
  desenho. Nenhuma das duas evidências é dependente de observação
  dos dados de sqale_index. A reformulação não constitui resposta
  a observações nos dados, e portanto não viola pré-registro.

  ---

# Adendo v1.6 (22/05/2026) — Ampliação Amostral

> **AVISO METODOLÓGICO CRÍTICO:** Esta seção é uma ADIÇÃO ao protocolo v1.5,
> escrita DEPOIS de:
>
> 1. Coleta oficial conforme protocolo v1.5 (17/05/2026)
> 2. Execução completa da análise estatística sobre N=34 (21/05/2026 14:50)
> 3. Observação dos resultados (H1 não sustentada por C1=False, C2=False)
> 4. Análise de poder post-hoc revelando poder a priori ~8% para razão de variância plausível
> 5. Exploração de log-transformação revelando F=3.19 (borderline empírico) em log-densidade
>
> Esta cronologia é declarada explicitamente para que revisores e leitores
> entendam que a expansão amostral E a análise log são adições conscientes
> pós-observação de resultado em N=34, mas pré-coleta dos N=30 novos projetos.
>
> Esta cronologia será preservada via tag git `ampliacao-v1.6-predeclarada`
> criada IMEDIATAMENTE após este commit, ANTES de qualquer coleta de novos
> dados.

## A1. Cronologia detalhada

| Data | Evento |
|------|--------|
| 16/05/2026 | Tag `pre-coleta-v1.5` criada, congelando protocolo v1.5 |
| 17/05/2026 | Coleta oficial N=34 executada conforme protocolo v1.5 |
| 21/05/2026 14:50 | Análise estatística N=34 executada |
| 21/05/2026 14:50 | Resultado: C1=False (F=0.52, p=0.60), C2=False (var(desc)<var(apa)<var(goog)). H1 não sustentada. |
| 21/05/2026 ~16h | Análise de poder post-hoc via simulação Monte Carlo (1000 réplicas) revelou poder a priori de aproximadamente 8% para razão de variância 2.38× plausível. |
| 21/05/2026 ~17h | Exploração estatística com log-transformação revelou que poder em escala log atinge ~71% com N=30/grupo (vs ~14% em densidade). |
| 21/05/2026 ~18h | Análise exploratória de log-densidade nos N=34: F=3.190, p=0.055 (> F-crítico empírico 3.09 mas borderline). Ordenamento em log: var(apa)<var(desc)<var(goog). C2 ainda False. |
| 22/05/2026 | Decisão: expandir amostra para N=64, formalizar análise log como complementar declaradamente post-hoc, escrever este adendo. |

## A2. Decisões formalizadas

### A2.1 Expansão amostral

Amostra é expandida de **N=34 para N=64** via adição de 30 projetos novos
distribuídos pelos três arquétipos:

| Arquétipo | Atual (v1.5) | Novos | Final (v1.6) |
|-----------|--------------|-------|--------------|
| Apache | 14 | +10 | 24 |
| Google | 10 | +10 | 20 |
| Descentralizado | 10 | +10 | 20 |
| **Total** | **34** | **+30** | **64** |

**Razão metodológica para expansão:**

- Poder estatístico ~8% (a priori) demonstrado inadequado para detecção de efeitos plausíveis em escala densidade
- Estabilidade de variâncias amostrais com n=10-14 é baixa (intervalos de confiança amplos)
- Expansão preserva análise primária em densidade conforme protocolo v1.5; aumenta estabilidade de estimativas

### A2.2 Análise estatística complementar em log-densidade

Análise estatística será conduzida em **duas escalas**:

1. **Análise primária (inalterada):** densidade (sqale_index/ncloc) conforme
   protocolo v1.5 §2 e §8.2. Regra de decisão H1 = C1 ∧ C2 permanece
   inalterada. Esta é a análise pré-registrada original.

2. **Análise complementar (post-hoc):** log-densidade (log(sqale_index/ncloc))
   declarada explicitamente como adicionada após observação de poder
   limitado em escala original em N=34.

**Justificativa metodológica da análise log:**

- Validação distribucional via Kolmogorov-Smirnov (protocolo v1.5 §8) já
  havia confirmado lognormalidade da densidade (KS p=0.7071, não rejeita)
- Transformação log é tratamento padrão para variáveis lognormais em análises
  de variância
- Análise de poder via simulação Monte Carlo demonstrou ganho de poder
  significativo: ~71% em log vs ~14% em densidade com N=30/grupo

**Declaração de cronologia para a análise log:**

A análise log NÃO estava no protocolo v1.5. Foi explorada após observação
do resultado em densidade e do baixo poder. Esta cronologia será reportada
explicitamente no paper resultante: análise log é apresentada como
complementar, descritivamente, com declaração explícita de que foi
adicionada após coleta e análise primária em densidade.

### A2.3 Reporte transparente de cronologia

O paper resultante (TCC e submissão VEM) reportará:

1. Análise primária em densidade conforme protocolo v1.5 com todos os
   resultados, **independentemente da direção**
2. Análise complementar em log-densidade com declaração explícita de
   cronologia (post-hoc)
3. Esta seção do protocolo (adendo v1.6) referenciada no texto como
   pré-declaração da expansão e da análise log
4. Tag git `ampliacao-v1.6-predeclarada` referenciada como evidência
   de pré-declaração antes da nova coleta

## A3. Critérios de inclusão pré-declarados para novos projetos

Critérios objetivos aplicados na busca de candidatos via GitHub API:

- **Linguagem primária:** Java (campo `language` da API do GitHub)
- **Stars:** ≥ 1.000
- **Atividade:** último commit em main/master nos últimos 12 meses
  (após 22/05/2025)
- **Não fork**, **não arquivado**
- **Tamanho:** ≥ 1.000 KB (aproxima ≥5.000 LOC)

**Exclusões:**

- Projetos já presentes em `dados/2026-05-17/consolidado.csv` (N=34 original)
- Projetos previamente registrados em `PROJETOS_EXCLUIDOS_LIMITACAO_TECNICA`
  (em `coleta_lib/io_utils.py`): atualmente apenas `google/j2objc` (macOS-only)

**Regra de famílias:** máximo 3 projetos por (organização, sub-família), onde
sub-família = primeira palavra do nome do repositório antes de qualquer hífen.

**Organizações pesquisadas por arquétipo:**

- Apache: `apache`
- Google: `google`, `googleapis`, `bazelbuild`, `firebase`
- Descentralizado: `Netflix`, `uber`, `linkedin`, `square`

**Nota sobre Square:** Embora `square` tenha sido incluído nas organizações
pesquisadas, nenhum projeto Square satisfez o critério `language == "Java"`
devido à classificação primária do GitHub (Retrofit, por exemplo, é
classificado como HTML 68% pela alta proporção de documentação em HTML
apesar do código core ser Java). Esta limitação técnica é declarada;
nenhuma exceção foi feita à regra pré-declarada.

## A4. Critério de seleção dos novos projetos

Após aplicação dos critérios objetivos via GitHub API (script
`scripts-tcc/buscar_projetos_candidatos.py`), seleção dos novos projetos
foi feita por critério mecânico declarado:

- **Apache:** top 10 por número de stars entre candidatos elegíveis
- **Google:** top 10 por stars excluindo google/ExoPlayer (deprecated
  oficialmente conforme descrição do próprio projeto: "This project is
  deprecated and stale")
- **Descentralizado:** distribuição balanceada por organização —
  Netflix 6, LinkedIn 2, Uber 2. Limitação: LinkedIn e Uber possuem
  apenas 2 candidatos elegíveis cada após aplicação dos critérios; Netflix
  domina por ter maior representação pública de projetos OSS Java.

## A5. Lista final pré-declarada de projetos a coletar

### Apache (+10)

1. `apache/skywalking` — 24802★ — APM, Application Performance Monitoring System
2. `apache/rocketmq` — 22436★ — cloud native messaging and streaming platform
3. `apache/shardingsphere` — 20723★ — distributed SQL for sharding
4. `apache/hadoop` — 15548★ — Apache Hadoop
5. `apache/doris` — 15378★ — high performance unified analytics database
6. `apache/dolphinscheduler` — 14281★ — data orchestration platform
7. `apache/druid` — 14003★ — real-time analytics database
8. `apache/jmeter` — 9392★ — load testing tool
9. `apache/seatunnel` — 9340★ — high-performance data integration
10. `apache/iceberg` — 8880★ — table format for analytics

### Google (+10)

1. `bazelbuild/bazel` — 25410★ — build system
2. `google/guice` — 12739★ — dependency injection framework
3. `google/tsunami-security-scanner` — 8571★ — network security scanner
4. `google/google-java-format` — 6133★ — Java code formatter
5. `google/open-location-code` — 4318★ — short location code library
6. `google/bundletool` — 3991★ — Android App Bundle manipulation
7. `google/bindiff` — 3047★ — binary difference analysis
8. `google/copybara` — 2729★ — code transformation/moving tool
9. `google/jimfs` — 2546★ — in-memory file system for Java
10. `firebase/firebase-android-sdk` — 2511★ — Firebase Android SDK

### Descentralizado (+10)

**Netflix (6):**

1. `Netflix/Hystrix` — 24456★ — latency and fault tolerance library (declarado
   em maintenance mode oficial pela Netflix; ver A6)
2. `Netflix/zuul` — 14013★ — gateway service
3. `Netflix/ribbon` — 4618★ — Inter Process Communication library (declarado
   em maintenance mode; ver A6)
4. `Netflix/maestro` — 3779★ — Workflow Orchestrator
5. `Netflix/archaius` — 2493★ — configuration management library (declarado
   em maintenance mode; ver A6)
6. `Netflix/genie` — 1763★ — Big Data Orchestration Service

**LinkedIn (2):**

7. `linkedin/dexmaker` — 1965★ — compile/runtime code generation
8. `linkedin/parseq` — 1176★ — async Java framework

**Uber (2):**

9. `uber/AutoDispose` — 3352★ — RxJava stream binding/disposal
10. `uber/okbuck` — 1528★ — gradle plugin for Buck build

## A6. Limitações declaradas a priori

- **Projetos em maintenance mode:** Netflix/Hystrix, Netflix/Ribbon e
  Netflix/Archaius (último commit em dezembro/2025, em maintenance mode
  oficial pela Netflix) batem o critério pré-declarado de "<12 meses
  inativos" e são incluídos. Captam padrões de dívida acumulada
  característica de projetos legados ativos sob a mesma organização.
  Esta inclusão é declarada explicitamente para evitar interpretação
  pós-hoc.

- **Apache de origem chinesa:** 6 dos 10 projetos Apache pré-declarados
  (skywalking, rocketmq, shardingsphere, doris, dolphinscheduler,
  seatunnel) têm origem em empresas chinesas (Alibaba, Huawei, etc.) que
  foram doados/incubados na Apache Software Foundation. Cultura técnica
  de origem pode diferir de projetos Apache "tradicionais" (Hadoop,
  JMeter). Esta heterogeneidade interna ao arquétipo Apache é declarada
  como possível confundidor; subgrupos podem ser analisados
  descritivamente em discussão.

- **Square excluído por critério estrito:** Apesar de Square ser
  organização classificável como descentralizada com projetos Java
  ativos (Retrofit, OkHttp, etc.), a classificação primária do GitHub
  como "HTML" (devido a alto volume de documentação) impediu inclusão
  sob critério estrito `language == "Java"`. A decisão de manter critério
  estrito sem exceção é declarada para evitar cherry-picking pós-coleta.

- **Domínio Netflix no arquétipo descentralizado:** Após expansão,
  Netflix representa 9 dos 20 projetos descentralizados (45%). Esta
  composição reflete a maior representação pública de Java sob Netflix
  em comparação com LinkedIn e Uber, e é declarada como possível
  confundidor entre "arquétipo descentralizado" e "cultura técnica
  Netflix" para discussão substantiva em §5 do TCC.

## A7. Regra de decisão sobre H1 (v1.6)

A regra de decisão pré-registrada permanece **inalterada** desde a v1.5:

**H0 é rejeitada a favor de H1 se e somente se:**

1. **C1:** Brown-Forsythe (sobre densidade) retorna F > F-crítico empírico
2. **C2:** ordenamento var(Google) < var(Apache) < var(Descentralizado)

**A análise log-densidade NÃO é parte da regra de decisão pré-registrada.**
Os resultados em log-densidade serão reportados como evidência descritiva
complementar, com declaração explícita de cronologia.

## A8. Compromissos formais

1. A nova coleta será conduzida com o mesmo pipeline da coleta original
   (mesma versão do SonarQube, mesmas configurações).
2. Nenhuma decisão de inclusão/exclusão pós-coleta será feita exceto por
   limitação técnica declarada (com mesmo padrão dos casos j2objc/cadence
   da v1.5).
3. Análise primária em densidade reportará TODOS os 64 projetos.
4. Análise complementar em log-densidade reportará TODOS os 64 projetos.
5. Subgrupos N=34 (originais) e N=30 (novos) também serão reportados
   descritivamente para verificação de consistência inter-coleta.

## A9. Postura sobre pré-registro

Esta seção v1.6 documenta:

- **Adição CONSCIENTE pós-observação** da expansão amostral
- **Adição CONSCIENTE pós-observação** da análise log-densidade como complementar
- **Manutenção INTACTA** da regra de decisão sobre H1 (regra v1.5 = regra v1.6)
- **Manutenção INTACTA** da análise primária em densidade
- **Pré-declaração formal** da lista de 30 novos projetos antes de qualquer
  coleta adicional

O pré-registro do protocolo v1.5 sobre análise primária permanece intacto.
A v1.6 adiciona componentes complementares e expansão amostral declarados
explicitamente como decisões pós-observação, com cronologia auditável via
git tags (`pre-coleta-v1.5` e `ampliacao-v1.6-predeclarada`).

A lista §A5 foi gerada com versão do script de 22/05 manhã (commit 0530b8d, bug do j2objc ativo)
O j2objc não estava no top 10 do Google de qualquer forma (saiu por critério temporal/limitação técnica documentada em PROJETOS_EXCLUIDOS_LIMITACAO_TECNICA), então o bug não afetou a lista §A5
O fix posterior (Claude Code, hoje) corrigiu o bug pra runs futuros, mas a coleta segue a §A5 pré-declarada, não a saída do script pós-fix

---

# Adendo v1.7 (23/05/2026) — Relaxamento do critério temporal §4.4 para os 30 novos projetos

> **AVISO METODOLÓGICO CRÍTICO:** Esta seção é uma ADIÇÃO ao adendo v1.6,
> escrita ANTES da coleta dos 30 novos projetos da §A5, mas DEPOIS de:
>
> 1. Tentativa de identificação de tags estáveis pré-2026-01-01 conforme §4.4 v1.5
> 2. Levantamento empírico via `git ls-remote --tags` em 22-23/05/2026 sobre
>    os 30 projetos da §A5
> 3. Constatação de que a regra §4.4 v1.5 é inviável para parte substancial
>    dos 30 novos projetos
>
> Esta cronologia é declarada explicitamente. A regra é relaxada por
> impossibilidade prática evidenciada por dados objetivos, não por
> conveniência pós-observação dos resultados da nova coleta (que ainda
> não ocorreu).

## A10. Relaxamento do critério temporal §4.4 v1.5

### A10.1 Problema declarado

O critério §4.4 v1.5 ("último tag de release estável anterior a 2026-01-01")
foi formulado sob a premissa implícita de que projetos open-source Java
mantêm convenção uniforme de releases via git tags. O levantamento
empírico realizado em 22-23/05/2026 sobre os 30 projetos da §A5 (via
`git ls-remote --tags --sort=-version:refname`) demonstrou que esta
premissa não se sustenta para a amostra ampliada.

### A10.2 Evidência empírica do levantamento

Inventário das tags por categoria observada (22-23/05/2026):

**Categoria 1 — Tag estável recente identificável pré-2026-01-01:**
Subconjunto dos 30 projetos. Critério §4.4 v1.5 aplicável diretamente.

**Categoria 2 — Tag estável recente mas posterior a 2026-01-01:**
Projetos como apache/hadoop (`rel/release-3.4.3` de 12/02/2026,
`rel/release-3.5.0` de 24/03/2026) e apache/druid (`druid-37.0.0`
de 28/04/2026, `druid-36.0.0` de 02/02/2026). Critério §4.4 v1.5
inaplicável (data limite violada).

**Categoria 3 — Tags estáveis existem mas refletem versões muito antigas:**
- `google/guice`: tag mais recente é `snapshot20101120` (2010); releases
  reais distribuídos via Maven Central sem tags git correspondentes
- `Netflix/zuul`: tag mais recente `zuul-1.0.28`; projeto operacional em
  zuul 2.x sem tags git correspondentes
- `linkedin/dexmaker`: tag estável `2.28.6` existe mas ordenação por
  versão retorna `v1.4` como "mais recente" devido a esquema misto de
  tagging
- `apache/iceberg`: tags retornadas são de subprojeto `pyiceberg-*`, não
  da release principal de iceberg-Java
- `apache/jmeter`: tag mais recente `v5_2_RC1` (release candidate);
  releases finais distribuídas via Apache Mirror sem tags estáveis
  correspondentes

**Categoria 4 — Sem tags git ou apenas pre-releases contínuos:**
- `firebase/firebase-android-sdk`: sem tags
- `Netflix/maestro`: sem tags
- `bazelbuild/bazel`: apenas tags `10.0.0-pre.YYYYMMDD.N` (pre-releases
  contínuos)
- `google/tsunami-security-scanner`: apenas `v0.2.0`

### A10.3 Inviabilidade da regra §4.4 v1.5 para os 30 novos

Tentativa de aplicação estrita da regra §4.4 v1.5 produziria:

- Para Categoria 1: aplicação direta
- Para Categoria 2: nenhum snapshot elegível (todas as tags violam data limite)
- Para Categoria 3: snapshots arbitrariamente antigos (snapshot20101120
  do guice teria 15+ anos de idade)
- Para Categoria 4: nenhum snapshot disponível

Isto produziria heterogeneidade extrema de idade de snapshot dentro do
próprio subconjunto N=30, com idades variando de meses a décadas, criando
confundidor temporal intra-grupo de magnitude maior que o confundidor
inter-grupo (N=34 vs N=30) tratado em A11.

### A10.4 Critério substituto pré-declarado para os 30 novos projetos

Para os 30 projetos listados na §A5:

1. **Identificar o branch principal** via `git symbolic-ref refs/remotes/origin/HEAD`.
   Default observado: `main` para projetos modernos, `master` para alguns
   projetos legados. Registrar o nome do branch em campo dedicado do
   consolidado.

2. **Executar `git checkout origin/<branch_principal>`** na data efetiva da coleta.

3. **Registrar no consolidado**:
   - `tag`: vazio ou marcador especial (`HEAD-on-<branch>-YYYY-MM-DD`)
   - `commit_sha`: SHA completo do HEAD na data da coleta
   - `data_commit`: data ISO 8601 do commit selecionado
   - `snapshot_type`: `head-of-main` (novo campo declarado a seguir)

### A10.5 Aplicabilidade

- **Aplicável**: 30 projetos da §A5 (Apache +10, Google +10, Descentralizado +10)
- **Não aplicável**: 34 projetos originais. A coleta v1.5 (tag
  `coleta-oficial-v1.5`, dados em `dados/2026-05-17/consolidado.csv`)
  permanece intocada. Os SHAs registrados continuam sendo as tags
  estáveis pré-2026-01-01 conforme §4.4 v1.5.

### A10.6 Justificativa metodológica

O critério substituto é uniforme dentro do subconjunto N=30 (todos os
projetos coletados via HEAD do branch principal na mesma janela
temporal de coleta), o que minimiza confundidor temporal intra-grupo.
A diferença sistemática entre N=34 e N=30 é declarada explicitamente
em A11 e tratada analiticamente.

A inviabilidade de §4.4 v1.5 para os 30 novos projetos foi documentada
via dados objetivos (`git ls-remote`) antes da coleta, não inferida
post-hoc dos resultados.

## A11. Confundidor temporal entre N=34 e N=30

### A11.1 Reconhecimento explícito

Subconjuntos da amostra N=64 têm diferença sistemática de idade de
snapshot:

- **N=34 (v1.5)**: tags estáveis pré-2026-01-01. Idade média de
  snapshot estimada em ~6-18 meses contados a partir da data de
  coleta original (17/05/2026).
- **N=30 (v1.6)**: HEAD do branch principal na data de coleta.
  Idade média de snapshot ~0-7 dias.

Esta diferença é estrutural ao desenho v1.6, não acidental.

### A11.2 Hipóteses sobre direção do efeito do confundidor

Snapshots mais novos podem apresentar densidade de dívida técnica
sistematicamente diferente de snapshots mais antigos pelas seguintes
razões plausíveis:

1. **Acumulação de dívida ao longo do tempo**: snapshots novos
   refletem dívida acumulada por mais tempo, podendo aumentar
   densidade
2. **Atualização de regras do SonarQube**: regras introduzidas em
   versões recentes do Sonar afetam código novo e código legado
   uniformemente, mas snapshots novos têm potencialmente mais código
   afetado por regras introduzidas recentemente
3. **Refatorações recentes**: projetos ativos refatoram continuamente,
   potencialmente reduzindo densidade em snapshots novos

Direções (1) e (3) operam em sentidos opostos, e direção (2) é
neutra em direção mas adiciona ruído. Direção líquida não é
predizível a priori.

### A11.3 Tratamento analítico

1. **Idade do snapshot como variável de controle obrigatória**: já
   prevista em §8.1 v1.4 (correlação parcial Spearman estendida).
   Mantida e aplicada a todo o N=64 sem alteração.

2. **Análise de subgrupos N=34 vs N=30 pré-registrada**: além do
   teste primário em N=64 conforme §8.2, será reportado:
   - Tabela descritiva separada (mediana, IQR, variância, std) para
     subgrupos N=34 e N=30 dentro de cada arquétipo
   - Brown-Forsythe aplicado separadamente a N=34 e a N=30 (apenas
     descritivo, não confirmatório — N=30 sozinho não satisfaz a
     regra de decisão pré-registrada)
   - Boxplot lado a lado dos dois subgrupos por arquétipo

3. **Verificação de robustez declarada**:
   - Se a direção do ordenamento de variâncias for consistente entre
     N=34 e N=30 dentro de cada arquétipo, isto fortalece interpretação
     de governança como variável estrutural
   - Se a direção divergir, isto fragiliza interpretação e é discutido
     honestamente em §5 do paper com hipóteses alternativas (efeito de
     idade de snapshot, mudança de stacks tecnológicos, evolução de
     práticas)

4. **Sub-amostra etariamente comparável (exploratória)**: para os
   projetos do N=34 cujo snapshot tem idade ≤ 12 meses contados de
   17/05/2026 (i.e. tag pré-2026-01-01 datada de 2025), execução
   adicional do Brown-Forsythe sobre o subconjunto N=30 ∪ (N=34 com
   snapshot recente). Análise exploratória, não substitui o teste
   primário em N=64.

### A11.4 Limitação declarada

O tratamento analítico de A11.3 não elimina o confundidor temporal,
apenas o caracteriza e quantifica. Resultado confirmatório do teste
primário em N=64 (regra C1 ∧ C2 da §8.2) será interpretado **sob a
ressalva** de que parte da variância observada pode ser atribuível
à diferença sistemática de idade de snapshot entre subgrupos, não
exclusivamente a diferenças de governança arquitetural.

Esta limitação é declarada como limitação intrínseca do desenho v1.6
e listada em §6.2 do paper resultante junto com as outras limitações
da v1.5 (poder estatístico, confundidores de NCLOC/idade do projeto,
heterogeneidade do arquétipo Apache, domínio Netflix no
descentralizado).

## A12. Identificação operacional do branch principal

Pseudocódigo da regra de identificação do branch principal por projeto:

1. Existe `origin/main`? → usar `main`
2. Existe `origin/master`? → usar `master`
3. Falha: registrar `branch_status=indeterminado` e abortar coleta do projeto

Branch identificado é registrado no consolidado em coluna dedicada
(`branch_principal`).

## A13. Novos campos no schema do consolidado

Os seguintes campos são adicionados ao schema do `consolidado.csv` a
partir da coleta v1.6:

| Campo | Valores | Aplicabilidade |
|-------|---------|----------------|
| `snapshot_type` | `release-tag-pre-2026` (N=34) ou `head-of-main` (N=30) | Todos |
| `branch_principal` | string (`main`, `master`, ou outro) | N=30; vazio para N=34 |
| `idade_snapshot_dias` | int (dias entre `data_commit` e data de coleta) | Todos |
| `subconjunto` | `n34-v1.5` ou `n30-v1.6` | Todos |

Para os projetos N=34, os campos `snapshot_type` e `subconjunto` são
preenchidos retroativamente sem alterar o conteúdo dos demais campos
do consolidado original.

## A14. Compromissos formais adicionais

Adicionalmente aos compromissos da §A8:

6. O `consolidado.csv` original em `dados/2026-05-17/consolidado.csv`
   permanece intocado. Os campos novos de A13 são adicionados ao
   `consolidado.csv` unificado em diretório separado.

7. A análise primária em densidade conforme §8.2 v1.5 é aplicada ao
   `consolidado.csv` unificado (N=64). A regra de decisão C1 ∧ C2
   permanece inalterada.

8. A análise de subgrupos A11.3 é reportada em apêndice ou seção
   dedicada do paper resultante, com declaração explícita de que
   não constitui teste confirmatório adicional.

9. A discussão de limitações em §5 do paper incluirá obrigatoriamente
   o confundidor temporal A11 como item dedicado.

## A15. Postura sobre pré-registro

Esta seção v1.7 documenta:

- **Relaxamento PRÉ-COLETA** do critério §4.4 v1.5 para os 30 novos
  projetos, motivado por dados objetivos (`git ls-remote`) coletados
  antes de qualquer coleta de métricas Sonar dos novos projetos
- **Manutenção INTACTA** do critério §4.4 v1.5 para os 34 projetos
  originais
- **Manutenção INTACTA** da regra de decisão §8.2 v1.5 (C1 ∧ C2)
- **Pré-declaração formal** do tratamento analítico do confundidor
  temporal (A11.3) antes da coleta dos novos dados

A coleta dos 30 novos projetos será executada APÓS o commit deste
adendo e a criação da tag `relaxamento-v1.7-predeclarada`, registrando
a sequência: levantamento empírico de tags → relaxamento declarado →
coleta.

---

# Adendo v1.8 (26/05/2026) — Substituições por violação de critérios objetivos §3.1

> **AVISO METODOLÓGICO CRÍTICO:** Esta seção é uma ADIÇÃO ao adendo v1.7,
> escrita durante a coleta v1.6, APÓS:
>
> 1. Coleta v1.6 executada parcialmente (18 dos 30 projetos com sucesso)
> 2. Execução do script `validar_candidatos_v17.py` retroativamente sobre
>    os 30 projetos da §A5 v1.6
> 3. Identificação de 7 projetos da §A5 que violam critérios objetivos
>    §3.1 (linguagem, NCLOC, idade, contribuidores)
>
> Esta cronologia é declarada explicitamente. As substituições são por
> violação objetiva de critério pré-existente §3.1, não por conveniência
> pós-observação de resultados.
>
> Esta cronologia será preservada via tag git `substituicao-v1.8-predeclarada`
> criada IMEDIATAMENTE após este commit, ANTES de qualquer coleta dos
> substitutos.

## A16. Detecção de violação de critérios

### A16.1 Origem da detecção

A §A5 do adendo v1.6 declarou 30 projetos a coletar, gerados por busca
automatizada via GitHub API. Durante a coleta v1.6, observamos
inconsistências em projetos individuais (NCLOC absurdamente baixo,
falhas estruturais de build). Para verificar se as falhas eram técnicas
(pipeline) ou estruturais (projeto inelegível), aplicamos retroativamente
o script `validar_candidatos_v17.py` (commitado em
`scripts-tcc/validar_candidatos_v17.py`) sobre os 30 projetos da §A5.

O script verifica 6 critérios mecanicamente:
- **C1:** ≥70% Java via `/repos/{owner}/{repo}/languages` (bytes)
- **C2:** 10k ≤ NCLOC ≤ 1M (estimado como `java_bytes / 30`, heurística)
- **C3:** ≥3 anos desde `created_at`
- **C4:** ≥25 contribuidores via paginação `Link rel=last`
- **C5:** ≥1 release estável (não-prerelease, não-draft) pre-2026-01-01
- **C6:** Presença de `pom.xml`, `build.gradle`, `build.gradle.kts` ou
  `settings.gradle` na raiz (build Maven/Gradle, não Bazel)

### A16.2 Imprecisões conhecidas do script

Documentadas para registro:
- C2 usa heurística `bytes/30` que conta arquivos `.java` em testes,
  comentários, código gerado, etc. Sistematicamente superestima NCLOC
  em 3-7x comparado a `ncloc_language_distribution[java]` do Sonar
  (definição operacional autoritativa via §4.1 v1.4).
- C3 usa `created_at` do repo, que pode ser posterior ao primeiro commit
  para repos importados/migrados.
- C5 reflete o critério v1.5 original, **sem considerar o relaxamento
  v1.7** que substitui release estável por HEAD-of-main para os 30 da §A5.

### A16.3 Aplicação aos 30 projetos da §A5

Resultado salvo em `scripts-tcc/validacao_candidatos_v17.csv` (commit
deste adendo). Falhas registradas categorizadas em:

**Falsos positivos C2 (NCLOC estimado vs NCLOC Sonar real)** — mantidos:
- apache/shardingsphere: estimativa 1.18M vs Sonar 250.957 ✓ elegível
- apache/druid: estimativa 2.13M vs Sonar 640.579 ✓ elegível
- apache/iceberg: estimativa 1.46M vs Sonar 211.913 ✓ elegível
- bazelbuild/bazel: estimativa 1.51M, NCLOC Sonar não disponível pois
  build Bazel pendente (§7.2)

**Falsos positivos C5 (já relaxado em v1.7)** — mantidos:
- apache/hadoop, Netflix/zuul, linkedin/parseq, google/tsunami-security-scanner

**Violações reais** — listadas em §A17 abaixo.

## A17. Projetos excluídos da §A5 v1.6 por violação objetiva

| Projeto | Arquétipo | Critério violado | Valor observado | Limiar |
|---------|-----------|------------------|-----------------|--------|
| apache/hadoop | apache | C2 (Sonar) | 1.028.933 NCLOC | ≤ 1.000.000 |
| apache/doris | apache | C1 | 48.1% Java | ≥ 70% |
| google/open-location-code | google | C1 | 22.2% Java | ≥ 70% |
| google/bundletool | google | C4 | 22 contribuidores | ≥ 25 |
| google/bindiff | google | C3 | 2.3 anos | ≥ 3 |
| firebase/firebase-android-sdk | google | C1 | 44.7% Java | ≥ 70% |
| Netflix/maestro | descentralizado | C4 | 12 contribuidores | ≥ 25 |

Notas:
- **apache/hadoop:** o script aprovou erroneamente o C2 via estimativa
  inflada de bytes, mas o NCLOC real do Sonar (1.028.933) viola o teto
  de 1.000.000 em 2.9%. Tratamento consistente com a exclusão de
  `apache/commons-codec` na v1.4 (9.573 NCLOC, 4% abaixo do mínimo de
  10.000), em que o critério foi aplicado literalmente sem flexibilização
  por margem pequena.

## A18. Substitutos pré-declarados

Substitutos selecionados pelo mesmo critério mecânico da §A4 v1.6:
**top por stars entre candidatos aprovados pelo script** e não-presentes
em `clones_v17.csv`.

Lista do CSV de aprovados (`validacao_candidatos_v17.csv`, coluna
`aprovado=sim` e `ja_na_v17=nao`) usada como base.

### Apache (+2)

1. **apache/incubator-seata** (25965★) → substitui hadoop
2. **apache/shenyu** (8791★) → substitui doris

### Google (+4)

1. **GoogleCloudPlatform/java-docs-samples** (1888★) → substitui open-location-code
2. **google/flogger** (1479★) → substitui bundletool
3. **google/j2cl** (1370★) → substitui bindiff
4. **GoogleCloudPlatform/DataflowTemplates** (1295★) → substitui firebase-android-sdk

### Descentralizado (+1)

1. **Netflix/servo** (1427★) → substitui maestro

### Notas de auditoria

**apache/incubator-seata** é #1 Apache em stars (25965). Foi omitido da
§A5 v1.6 original sem motivo documentado — falha do levantamento
automatizado. O adendo v1.8 trata esta inclusão como **correção de
omissão**, não substituição arbitrária.

**google/ExoPlayer** (21924★) NÃO é incluído. Foi explicitamente excluído
da §A5 v1.6 pela §A4: "Google: top 10 por stars excluindo google/ExoPlayer
(deprecated oficialmente conforme descrição do próprio projeto)". Status
confirmado em 26/05/2026: continua deprecated. A regra original mantém-se.

**google/flogger** foi excluído da v1.4 do protocolo por NCLOC Java
< 10k (7.503 NCLOC). Revalidação em 26/05/2026 via contagem rigorosa
(cloc-like Python) revelou 14.000+ NCLOC reais, dentro da janela
10k-1M. Reentra elegibilidade. Esta reentrada é justificada por
mudança objetiva no projeto entre 04/2026 e 05/2026, não por mudança
de critério.

**Netflix/servo** (1427★) é o próximo Netflix elegível na lista
após exclusão de Netflix/maestro. Preserva a composição
Netflix=6/LinkedIn=2/Uber=2 declarada na §A4 v1.6.

**apache/shenyu** é Apache de origem chinesa (Dromara doado para ASF).
A composição Apache "origem chinesa" sobe de 6/10 para 7/10 após
substituições (incubator-seata também é origem chinesa). A
heterogeneidade interna do arquétipo Apache, declarada como possível
confundidor na §A6 v1.6, é reafirmada e listada nas limitações do
paper resultante.

## A19. Schema do consolidado e classificação dos excluídos

Os 7 projetos excluídos por §A17 são adicionados ao registro
`PROJETOS_EXCLUIDOS_LIMITACAO_TECNICA` em `coleta_lib/io_utils.py`
com motivo categorizado em "violação de critério §3.1".

Distinção operacional entre as categorias de exclusão em
`PROJETOS_EXCLUIDOS_LIMITACAO_TECNICA`:

- **Plataforma incompatível** (j2objc): build exige plataforma não
  disponível ao ambiente da coleta.
- **Violação de critério §3.1** (hadoop, doris, open-location-code,
  bundletool, bindiff, firebase-android-sdk, maestro): projeto não
  satisfaz critérios objetivos da seleção amostral. Detectado
  retroativamente via `validar_candidatos_v17.py`.

Os dados parciais coletados desses 7 projetos em `dados/2026-05-24/`
(via execução do loop §A8 da v1.7) **NÃO** entram no `consolidado.csv`
unificado para análise. São removidos do consolidado e os projetos
correspondentes são deletados do SonarQube para evitar contaminação.

## A20. Substituição N=64 → N=64 (preserva tamanho amostral)

A substituição é **um-por-um**, preservando N=64 e a composição
declarada §A2.1 v1.6:

- Apache: 14 (v1.5) + 10 (v1.6 menos hadoop/doris + seata/shenyu) = 24
- Google: 10 (v1.5 sem j2objc, conforme limitação técnica)
  + 10 (v1.6 menos 4 excluídos + 4 substitutos) = 20
- Descentralizado: 10 (v1.5) + 10 (v1.6 menos maestro + servo) = 20

N total: 64. Inalterado em relação a v1.6.

## A21. Compromissos formais adicionais

Adicionalmente aos compromissos da §A8 v1.6 e §A14 v1.7:

10. A coleta dos 7 substitutos seguirá o mesmo pipeline e as mesmas
    regras §A10.4 v1.7 (HEAD-of-main, `snapshot_type=head-of-main`,
    `subconjunto=n30-v1.6`).

11. O `validacao_candidatos_v17.csv` é commitado neste adendo como
    evidência da aplicação mecânica do script aos 30 da §A5 v1.6.

12. A análise primária e complementar conforme §A2.2 v1.6 será
    aplicada à amostra final N=64 com substituições aplicadas, sem
    revisão da regra de decisão (§8.2 v1.5 inalterada).

## A22. Postura sobre pré-registro

Esta seção v1.8 documenta:

- **Detecção objetiva** de violações de §3.1 via script mecânico
  aplicado retroativamente
- **Substituições por critério idêntico** ao levantamento original
  (top por stars entre aprovados, mesma janela de candidatos
  `candidatos_expansao_v1.6.csv`)
- **Manutenção INTACTA** da regra de decisão §8.2 v1.5 (C1 ∧ C2)
- **Manutenção INTACTA** da análise primária em densidade e complementar
  em log-densidade
- **Preservação INTACTA** do N=64 declarado em v1.6

A substituição NÃO foi informada por observação dos resultados Sonar
dos projetos coletados em v1.6 — foi informada pela detecção de
inelegibilidade estrutural via metadados (GitHub API). A regra de
decisão e o desenho analítico permanecem inalterados desde v1.5.

---

# Adendo v1.9 (28/05/2026) — Cascata servo → Priam por violação §3.1.2 pós-coleta

> **AVISO METODOLÓGICO:** Esta seção documenta substituição em cascata
> realizada APÓS coleta Sonar de Netflix/servo revelar NCLOC abaixo do
> piso §3.1.2. A detecção foi via medida operacional autoritativa
> (Sonar `ncloc`), não via estimativa pré-coleta.

## A23. Detecção da violação

Coleta de `netflix-servo-10` em 2026-05-28 17:20:51 retornou:
- NCLOC Sonar = 9.233
- Piso §3.1.2 = 10.000
- Margem abaixo do piso = 7.67%

O script de validação `validar_candidatos_v17.py` havia aprovado servo
em 2026-05-26 com `ncloc_est=26.558` (heurística `java_bytes/30`). A
inflação observada (26.558/9.233 ≈ 2.88×) é consistente com a inflação
sistemática 3-7× declarada na §A16.2 do adendo v1.8.

## A24. Decisão de exclusão por consistência

`netflix-servo-10` é excluído da amostra n30-v1.6, por consistência com:
- `apache-commons-codec` (v1.4): excluído por 4% abaixo do piso (9.573 NCLOC).
- `apache-hadoop-18` (v1.8 §A17): excluído por 3% acima do teto (1.028.933 NCLOC).

Servo (7.7% abaixo) está em margem maior que ambos os casos precedentes.
Manter servo introduziria assimetria não justificável no tratamento de
§3.1.2.

## A25. Substituto pré-declarado

Próximo Netflix elegível por critério estrito (top stars entre aprovados
pelo `validar_candidatos_v17.py`, descontando v1.5 e v1.6 já em uso):
**Netflix/Priam** (1.038 estrelas).

Validação prévia via contagem cloc-like local antes da clonagem oficial:
- NCLOC main (sem testes) = 13.170 → ≥ 10.000 ✓
- Margem acima do piso = 31.7%

A contagem cloc-like local é declarada como **triagem adicional** após
servo. Para Priam, a estimativa pré-coleta (`ncloc_est = 39.882`) e a
contagem cloc-like (`13.170 main`) divergem em 3.03× — coerente com a
inflação esperada. Priam tem margem suficiente acima do piso para que
diferença residual entre cloc-like e Sonar não cause violação.

A próxima opção (Netflix/astyanax, 1.034 estrelas) será considerada se
Priam violar §3.1.2 na coleta Sonar.

## A26. Mapeamento atualizado §A18

A substituição em §A18 v1.8 (`Netflix/servo` no lugar de
`Netflix/maestro`) é modificada para:

| Excluído (v1.8) | Substituto (v1.8) | Substituto (v1.9) |
|---|---|---|
| Netflix/maestro | ~~Netflix/servo~~ | Netflix/Priam |

`Netflix/servo` é adicionado a `PROJETOS_EXCLUIDOS_LIMITACAO_TECNICA`
com categoria "violação §3.1.2 detectada pós-coleta".

## A27. Operações pré-declaradas

A coleta de Priam será conduzida APÓS:

1. Commit deste adendo v1.9
2. Tag git `cascata-v1.9-predeclarada`
3. Remoção de servo do consolidado v1.6 (`dados/2026-05-24/consolidado.csv`)
4. Remoção de servo do SonarQube (HTTP DELETE)
5. Substituição de servo por Priam em `projetos-tcc-dataset-4.csv`,
   `clones_v17.csv` e `clonar_v17.py`
6. Clone de Priam em `projetos-clonados/Priam`

## A28. Postura sobre pré-registro

Esta seção v1.9 documenta:

- **Detecção objetiva pós-coleta** de violação §3.1.2 via medida Sonar
  (definição operacional autoritativa §4.1 v1.4)
- **Substituição por critério idêntico** ao levantamento (top stars)
- **Manutenção INTACTA** da regra de decisão §8.2 v1.5 (C1 ∧ C2)
- **Manutenção INTACTA** da análise primária em densidade e complementar
  em log-densidade
- **Preservação INTACTA** do N=64 declarado em v1.6

A coleta dos 17 projetos v1.6 anteriores não é afetada. Os 4 substitutos
restantes (java-docs-samples, shenyu, incubator-seata, DataflowTemplates)
ainda não foram coletados e serão coletados após a cascata servo→Priam.

---

# Adendo v1.10 (29/05/2026) — Limitação técnica de build + estado amostral final efetivo N=60

> **AVISO METODOLÓGICO:** Esta seção documenta 4 projetos que, mesmo após
> esforço documentado de fix de build (patches pós-checkout, suporte Bazel
> nativo no pipeline, fallbacks de JDK), não foram coletáveis no ambiente
> da pré-banca. A exclusão é por **limitação técnica do ambiente de
> coleta**, não por inelegibilidade pelos critérios §3.1.

## A29. Limitação técnica adicional v1.10 (4 projetos)

Os 4 projetos abaixo passam os critérios §3.1 (linguagem, tamanho,
idade, contribuidores, release) mas falham na execução do pipeline de
build local pré-Sonar. Cada um documenta a causa exata observada e a
condição para reintrodução pós-banca.

### A29.1. `google-bazel-12` (bazelbuild/bazel)

- **Causa**: Bazel meta-build (recursos). Primeira tentativa via
  `_bazel_completo` esgotou memória/CPU do ambiente e travou o PC
  (Bazel buildando o próprio Bazel é caso patológico de recursos).
- **Diagnóstico**: não é falha de critério §3.1 — bazelbuild/bazel
  aprova nos 6 critérios (Java 83.5%, contribs 1.373, release tags
  contínuas, idade 11+ anos, NCLOC dentro da faixa real). É falha
  estritamente de recursos do ambiente de coleta.
- **Reintrodução pós-banca**: tentar build com `bazel build //src/main/...`
  (target reduzido via `BAZEL_TARGETS_OVERRIDE`) em ambiente com mais
  memória, ou aceitar análise apenas do subdiretório `src/main/java`
  via scanner standalone com binários pré-compilados de release oficial.

### A29.2. `google-google-java-format-15` (google/google-java-format)

- **Causa**: Maven Tycho 5.0.2 lança `ProvisionException` no
  `TargetPlatformWorkspaceReader` mesmo invocando `mvn package` no pom
  raiz. Tycho é orientado a Eclipse PDE — requer configuração de
  target platform Eclipse não presente no ambiente CI/Linux.
- **Diagnóstico**: não é falha de critério §3.1 — google-java-format
  aprova nos 6 critérios. Falha é toolchain-específica (Tycho requer
  Eclipse target platform; coleta Sonar não pode depender disso).
- **Reintrodução pós-banca**: configurar Tycho com p2 repositories
  apontando para um Eclipse SDK local, ou desativar Tycho via
  `-Dtycho.mode=maven` se viável sem quebrar empacotamento.

### A29.3. `google-java-docs-samples-16` (GoogleCloudPlatform/java-docs-samples)

- **Causa**: monorepo Gradle de samples independentes — cada subdiretório
  tem `pom.xml` ou `build.gradle` próprio mas não há build unificado na
  raiz. `gradle assemble` na raiz não compila nada útil (sem `settings.gradle`
  agregador).
- **Diagnóstico**: aprovação nos critérios §3.1 ocorreu sobre o repo
  agregado (415 contribuidores, 95% Java, 402k NCLOC heurístico), mas
  o pipeline atual assume um build unificado por projeto. Análise por
  subdiretório individual quebraria comparabilidade (qual sample? por
  que esse e não outro?).
- **Reintrodução pós-banca**: ou (a) escolher pré-declaradamente UM
  subdiretório-âncora representativo (ex.: `cloud-tasks`) e analisar
  esse, com nota explícita de que NÃO é o repo agregado; ou (b)
  rodar Sonar standalone sobre o repo todo aceitando inflação por
  duplicação de boilerplate entre samples.

### A29.4. `linkedin-dexmaker-04` (linkedin/dexmaker)

- **Causa**: build Gradle exige NDK Android `27.0.12077973`; instalação
  via Android SDK Manager produziu diretório corrompido (sem
  `source.properties`), fazendo Gradle abortar com
  `NullPointerException` ao resolver toolchain. Reinstalação manual
  não resolveu (vários `sdkmanager` retornam mesma corrupção).
- **Diagnóstico**: aprovação nos critérios §3.1 ocorreu sobre metadados
  GitHub (87% Java, 55 contribs, stable releases). Falha é
  ambiente-específica (NDK package corrompido no repositório Google);
  outros projetos com NDK podem ter o mesmo problema.
- **Reintrodução pós-banca**: tentar instalação manual do NDK via
  download direto do Google (link oficial pula o SDK Manager), ou
  buildar com NDK mais antigo declarado no `build.gradle` como
  override.

## A30. Estado amostral final efetivo N=60

Recompõe a contagem após todos os adendos v1.4 → v1.10:

| Categoria | Quantidade | Origem |
|---|---:|---|
| Declarado v1.5 (n34) | 34 | §A1 v1.5 |
| Expansão v1.6 (n30) | 30 | §A5 v1.6 |
| **Subtotal bruto** | **64** | — |
| Excluído por plataforma macOS (v1.5) | -1 | j2objc (§A11) |
| Excluído por violação §3.1 v1.8 | -7 | hadoop, doris, open-location-code, bundletool, bindiff, firebase, maestro (§A17) → substituídos por incubator-seata, shenyu, java-docs-samples, flogger, j2cl, DataflowTemplates, servo (preserva N=64) |
| Excluído por violação §3.1.2 pós-coleta v1.9 | -1 | servo → substituído por Priam (preserva N=64) |
| **Subtotal após substituições preservadoras** | **64** | — |
| Excluído por limitação técnica v1.5 | -1 | j2objc (sem substituto: §A11 v1.5 já contabilizou) |
| Excluído por limitação técnica v1.10 | -3 | bazel, google-java-format, java-docs-samples (sem substituto: §A30) |
| Excluído por limitação técnica v1.10 | -1 | dexmaker (sem substituto: §A30) |
| **N final efetivo** | **60** | — |

**Composição N=60 por arquétipo:**

| Arquétipo | v1.5 | v1.6 entrada | Excl. v1.10 | Final |
|---|---:|---:|---:|---:|
| Apache | 14 | 10 (bem-sucedidos via §A17) | 0 | 24 |
| Google | 10 (após j2objc) | 10 (após §A17) | -3 (bazel, google-java-format, java-docs-samples) | 17 |
| Descentralizado | 10 | 10 (após §A17/§A23) | -1 (dexmaker) | 19 |
| **Total** | **34** | **30** | **-4** | **60** |

**Implicação metodológica**: a redução de N=64 → N=60 (-6,25%) NÃO
afeta a regra de decisão §8.2 v1.5 (C1 ∧ C2) nem o desenho analítico
primário (Brown-Forsythe sobre densidade). O poder estatístico do
teste primário em N=60 é discutido na §10 da redação final como parte
das limitações.

## A31. Implementações de pipeline registradas em v1.10

Mudanças em `coleta_lib/scan.py` (commitadas como parte de v1.10) que
suportam projetos Bazel e patches pós-checkout. Documentadas aqui para
auditabilidade — não alteram critérios §3.1 nem método estatístico.

### A31.1. Patches pós-checkout Gradle

Registrados em `PATCHES_POST_CHECKOUT: dict[str, str]` em
`coleta_lib/scan.py`. Scripts em `scripts-tcc/patches/`.

| Projeto | Script | Motivo |
|---|---|---|
| `uber-cadence-java-client-05` | `cadence-libthrift.sh` | Thrift compiler/runtime mismatch — bump de `libthrift` para v0.20.0 |
| `google-tsunami-14` | `tsunami-skip-javadocjar.sh` | Gradle 8.10 detecta implicit-dep entre `:tsunami-proto:generateProto` e `:tsunami-proto:javadocJar`; desativa `java.withJavadocJar()` nos subprojects |
| `netflix-genie-12` | `genie-skip-vendor-and-ui-npm.sh` | (a) `gradle-daemon-jvm.properties` exige `toolchainVendor` estrito; remove a linha; (b) `:genie-ui` depende de npm 5.8.0 quebrado, desliga as dependências `npmInstall` e `bundle` |

Cada patch é shell idempotente (usando `sed -i` / `/pattern/d`), aplicado
APÓS `git checkout --force` do SHA da planilha e ANTES da invocação do
build. Patches modificam o working tree do clone; o repo upstream não é
afetado. Backup do estado original em `*.bak-*` na primeira invocação.

### A31.2. Suporte nativo a Bazel

`coleta_lib/scan.py` ganha:

- **`detectar_build(repo)`** retorna `"bazel"` quando `MODULE.bazel`,
  `WORKSPACE`, `WORKSPACE.bazel`, `BUILD` ou `BUILD.bazel` está
  presente na raiz (após Maven/Gradle, antes de Ant).
- **`_bazel_completo(repo, ..., scanner_bin)`** roda `bazelisk build
  <target>` (default `//...`), coleta JARs de `bazel-bin/`, e invoca
  `sonar-scanner` standalone com `sonar.java.binaries` apontando para
  os JARs e `sonar.sources` para os diretórios reais de código.
- **`BAZEL_TARGETS_OVERRIDE: dict[str, list[str]]`** permite override
  do target Bazel por projeto. Necessário em `google-j2cl-18` (uso de
  `//transpiler/java/...` em vez de `//...` que falha por macros
  internas Google).
- **`BAZEL_SOURCE_HINTS: dict[str, list[str]]`** declara source roots
  específicos quando o layout não é `src/main/java` (j2cl tem 5 source
  roots em subdirs convencionais).
- **`find_bazel_sources(repo, project_key)`** prioriza HINTS, depois
  cai pra `find_main_sources`, depois faz busca heurística em `java/`
  na raiz e `*/java/` em subdirs até 2 níveis, excluindo
  `bazel-*/`, `external/`, `third_party/`, `javatests/`. Retorna
  vazio explicitamente em vez de `.` (fallback ausente — `sources=.`
  contamina ncloc com dependências; better fail than inflated data).
- **Filtragem de JARs em `_bazel_completo`**: exclui JARs em paths
  `javatests/`, `tests/`, `test/` (paridade com `STANDALONE_EXCLUSIONS`)
  e JARs cujo símlink resolvido aponta para path inexistente (evita
  `IllegalStateException` no Sonar por path inválido).
- **Properties file para `sonar.java.binaries`**: lista de JARs pode
  exceder `MAX_ARG_STRLEN` Linux (~128KB por argumento único); o
  pipeline escreve a propriedade em `sonar-project.properties`
  temporário e a remove no `finally`.

### A31.3. Resultados de aplicação em v1.10

Projetos Bazel coletados com sucesso após implementação:

| Projeto | Target Bazel | n_jars | n_source dirs | NCLOC Sonar |
|---|---|---:|---:|---:|
| `google-flogger-17` | `//...` | 1.904 | 5 (via src/main/java) | 10.797 |
| `google-copybara-19` | `//...` | 27.886 | 1 (via heurística `java/` raiz) | 63.228 |
| `google-j2cl-18` | `//transpiler/java/...` (override) | 3.770 (após filtro test JARs) | 5 (via HINTS) | 80.622 |

Projetos Gradle coletados com sucesso via patches:

| Projeto | Patch | NCLOC Sonar |
|---|---|---:|
| `google-tsunami-14` | `tsunami-skip-javadocjar.sh` | 11.015 |
| `netflix-genie-12` | `genie-skip-vendor-and-ui-npm.sh` | 39.678 |

## A32. Compromisso de tentativa pós-banca

Os 4 projetos da §A29 NÃO são abandonados — são deferidos. Compromisso
formal pós-banca:

1. **Tentar reintrodução** de cada um conforme protocolo de
   reintrodução específico declarado em §A29.1-A29.4.
2. **Registrar resultado** de cada tentativa (sucesso → adição ao
   dataset, falha → manter exclusão com diagnóstico atualizado) em
   adendo v1.11+ pós-banca.
3. **Não alterar regra de decisão §8.2** se a coleta pós-banca dos 4
   for bem-sucedida — análise principal do TCC é fechada em N=60 e
   uma re-análise opcional em N=64 (com os 4 reincluídos) é
   apresentada como **análise de robustez** na seção de discussão.

Esta postura preserva integridade do pré-registro: a análise primária
em N=60 está formalmente fechada em v1.10. Reintrodução pós-banca não
contamina a regra de decisão, apenas alimenta análise complementar.

## A33. Postura sobre pré-registro

Esta seção v1.10 documenta:

- **Limitação técnica do ambiente de coleta** como categoria de
  exclusão distinta de violação §3.1 — coerente com §A11 v1.5 (j2objc).
- **Critérios de reintrodução pós-banca pré-declarados** por projeto
  individual (§A29.1-A29.4), não inventados após a tentativa.
- **N=60 como amostra primária** — fixada antes da análise estatística
  primária. Qualquer reintrodução posterior é análise de robustez,
  não substituição da primária.
- **Manutenção INTACTA** da regra de decisão §8.2 v1.5 (C1 ∧ C2)
  aplicada agora sobre N=60.
- **Manutenção INTACTA** do desenho analítico (Brown-Forsythe sobre
  densidade, complementar em log-densidade, análise de robustez
  conforme §8.1).
- **Reconhecimento explícito** de redução de poder estatístico de
  N=64 para N=60 (-6,25%), discutido nas limitações da §10 da redação.

A escolha de declarar limitação técnica em vez de substituir os 4 (à
moda v1.8) é deliberada: substituir reabriria o levantamento
`candidatos_expansao_v1.6.csv` num momento pós-pré-banca, configurando
mudança de critério após observação parcial de resultados. Manter N=60
preserva a sequência de decisões pré-registradas.