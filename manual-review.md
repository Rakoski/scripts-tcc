# Revisão Manual Necessária

Projetos que precisaram de decisão humana durante a coleta de dados.

## Resolvidos

| Projeto | Empresa | Motivo | Resolução |
|---------|---------|--------|-----------|
| dubbo | Apache | Branch principal é `origin/3.3`, não `main`/`master` | Corrigido para ativo (último commit 2026-04-13) |
| tink | Google | Clone falhou (DNS temporário); repo desmembrado pelo Google | Re-clonado; marcado como **arquivado** (último commit main 2024-04-17). Precisa de substituto Google se critério exclui arquivados |
| jvm-profiler | Uber | Sem tags estáveis | **Substituído por okbuck** (uber/okbuck, tag 0.54.4) |
| mina | Apache | Arquivado (último commit 2023-10-05) | **Substituído por commons-codec** (apache/commons-codec, tag rel/commons-codec-1.17.1) |
| conductor | Netflix | Arquivado (último commit 2023-12-13, doado ao CNCF/Orkes) | **Substituído por ambry** (linkedin/ambry, tag v0.4.533) |
| completable-futures | Spotify | Arquivado (último commit 2023-12-12) | **Substituído por brooklin** (linkedin/brooklin, tag 5.4.3) |
| ndbench | Netflix | Candidato substituto de conductor, mas também arquivado (último commit 2023-06-21) | Descartado; ambry usado no lugar |

## Pendente de decisão

| Projeto | Empresa | Questão |
|---------|---------|---------|
| tink | Google | Arquivado (24 meses). Se critério Saída 1 exclui arquivados do Google, precisa de 1 substituto Google. O repo original tem 15 Google — sem tink seriam 14. |
| ribbon | Netflix | Está no CSV original (`Dataset do projeto de TCC - Página1.csv`) com status manutenção, mas não constava na lista dos 45. Incluir como descentralizado? |
| AutoDispose | Uber | Último commit da tag é 2023-07-25, mas status calculado como "ativo" — verificar se main está realmente ativo |

## Composição atual do dataset (por arquétipo)

- **Apache**: 14 ativos + dubbo (ativo, corrigido) = **15** ✓
- **Google**: 14 ativos + tink (arquivado) = 14 ativos + 1 arquivado. Se exclui arquivados = **14** (falta 1)
- **Descentralizado**: hollow, mantis, EVCache, spectator, metacat, dgs-framework (Netflix=6) + NullAway, AutoDispose, okbuck, h3-java, RIBs (Uber=5) + github-java-client (Spotify=1) + cruise-control, ambry, brooklin (LinkedIn=3) = **15** ✓
