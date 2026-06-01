# Tabela 10 — Análise de robustez por tamanho (NCLOC 10k–100k)

**Análise:** Cliff's δ na subamostra restrita à faixa de sobreposição entre arquétipos (NCLOC entre 10.000 e 100.000).

**Pré-registro:** declarada no protocolo §3.8 (subseção `Tratamento analítico de confundidores`) como teste de robustez ao confundimento por tamanho.

## Composição da subamostra

| Arquétipo | n (subamostra) | n (total N=60) | % retido |
|---|---:|---:|---:|
| apache | 6 | 24 | 25% |
| google | 12 | 17 | 71% |
| descentralizado | 17 | 19 | 89% |

## Descritivas da densidade SQALE na subamostra

| Arquétipo | n | Mediana | Q1 | Q3 | Variância |
|---|---:|---:|---:|---:|---:|
| apache | 6 | 0.74 | 0.625 | 0.914 | 0.031 |
| google | 12 | 0.149 | 0.115 | 0.465 | 0.062 |
| descentralizado | 17 | 0.413 | 0.252 | 0.512 | 0.051 |

## Cliff's δ na subamostra

| Grupo X | Grupo Y | n_X | n_Y | δ | Magnitude |
|---|---|---:|---:|---:|---|
| apache | google | 6 | 12 | +0.833 | grande |
| apache | descentralizado | 6 | 17 | +0.804 | grande |
| google | descentralizado | 12 | 17 | -0.333 | média |

## Interpretação

O efeito descritivo Apache > demais arquétipos **persiste e se intensifica** quando o tamanho amostral é controlado.

| Par | δ (N=60) | δ (subamostra 10k–100k) | Mudança |
|---|---:|---:|---|
| Apache vs Google | +0,373 (médio) | +0,833 (grande) | reforçou |
| Apache vs Descentralizado | +0,268 (pequeno) | +0,804 (grande) | reforçou |
| Google vs Descentralizado | -0,183 (pequeno) | -0,333 (médio) | reforçou |

**Conclusão:** a direção Apache > Google em densidade SQALE não é artefato de confundimento por NCLOC. O efeito é robusto à restrição de tamanho amostral.

**Ressalva:** n=6 Apache na subamostra reduz a confiabilidade do estimador; resultado descritivo, não confirmatório.
