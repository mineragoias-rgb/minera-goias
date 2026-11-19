# Frente 8 · Indicadores compostos e cenários — registro metodológico (v0.1, semana 2)

Status: **protótipo para revisão técnica. Nenhum índice está validado.** Reprodução: `python3 run_indices.py <repo>` e `python3 test_indices.py` (semente 20261112).

## Fontes
| Fonte | Uso | Período | Observação |
|---|---|---|---|
| `data/panorama/panorama.json` · cfem (ANM) | arrecadação, diversificação por substância e por titular | 2022–2025 (2026 é parcial e fica fora) | R$ correntes |
| panorama.json · proc (SIGMINE, 16.875 processos) | estrutura minerária por município (status 0, 1, 3) | retrato de 24/10/2026 | processo ≠ mina |
| panorama.json · dims.mun (IBGE/IMB) | população (ano mais recente por município) e PIB 2023 | — | defasagem entre PIB e CFEM |
| panorama.json · ccee | energia (só na variante) | 05/2024–06/2026 | mercado livre; 9 municípios com carga de extração |
| panorama.json · amb_go, amb_br (AMB) | índice por substância | 2010–2025 | |

## Método
1. **Indicadores brutos** por unidade (município ou substância). Tabelas em `irmm_indicadores_brutos.csv` e `ipes_indicadores_brutos.csv`.
2. **Normalização** para [0, 1]: caso-base `log1p` nos indicadores assimétricos + mínimo–máximo, sem winsorização (preserva o topo). Alternativas na grade: z-score pela normal acumulada e percentil.
3. **Dimensões** = média simples dos indicadores normalizados.
4. **Pesos**: caso-base iguais entre dimensões. Lentes (cenários de ponderação): Fiscal, Estrutural, Local. Alternativas por dados (entropia, CRITIC) só na grade.
5. **Agregação**: caso-base aritmética (compensatória). Geométrica (piso 0,01) e ordinal (soma de percentis) na grade.
6. **Posição**: 1 = maior nota; empate recebe a mesma posição. **Nunca publicar posição sem intervalo ou faixa.**
7. **Sensibilidade**: (a) 10.000 sorteios de pesos (Dirichlet), uniforme no simplex e concentrado em torno do caso-base; (b) grade de 54 combinações; (c) remoção de uma dimensão; (d) sentido da dependência invertido; (e) variante com energia; (f) 500 reamostragens dos meses de CFEM com os indicadores refeitos.

## Índices
- **IRMM — Índice de Relevância Minerária Municipal** (181 municípios com CFEM em 2022–2025). Dimensões: Arrecadação (CFEM média anual e per capita), Dependência local (CFEM/PIB), Estrutura minerária (processos de lavra e de pré-lavra), Diversificação (1 − HHI por substância e por titular).
- **IPES — Índice de Posição Estratégica por Substância** (13 substâncias). Dimensões: Peso econômico, Posição nacional, Dinâmica, Robustez. **Reprovou a validade de face: não publicar como ranking.**

## Decisões
| ID | Decisão | Alternativa testada |
|---|---|---|
| D-01 | Universo = municípios com CFEM em 2022–2025; 2026 parcial fora | — |
| D-02 | Quatro dimensões; média simples dentro da dimensão | remoção de cada dimensão |
| D-03 | log1p + mínimo–máximo, sem winsorização | z-score, percentil, grade |
| D-04 | Pesos iguais no caso-base (não há consenso nem consulta a especialistas) | lentes, entropia, CRITIC, sorteio |
| D-05 | Dependência CFEM/PIB lida como relevância local (sentido +) | sentido invertido |
| D-06 | Energia fora do caso-base (cobertura de 9 municípios, só mercado livre) | variante com energia |
| D-07 | Agregação aritmética no caso-base | geométrica, ordinal |
| D-08 | Empate = mesma posição; resultado em faixas A–D com intervalo | — |
| D-09 | IPES não publicado como ranking | lente econômica |
| D-10 | ABERTA: Diversificação dentro do índice ou separada como resiliência | sem ela, Alto Horizonte passa a 1º; decidir na revisão técnica |

## Limitações
Pesos sem validação por especialistas; processos contados sem ponderar tamanho; PIB (2023) e população (mais recente) com defasagem; R$ correntes sem deflator; universo exclui municípios sem CFEM; território (MapBiomas) e investimento só em nível estadual; bases não validadas por ato humano.

## Defeito encontrado e corrigido
O teste T09 (dominância) reprovou a versão inicial: a posição simulada contava as unidades *abaixo* em vez das *acima* (sinal invertido em `mc_weights`). Corrigido; todas as simulações foram refeitas.

## Validação técnica do IRMM (validacao.py → validacao_resultado.json)
Limiares fixados antes de rodar. Resultado: 7 de 8 critérios. V1 reprodutibilidade, V2 validade de face, V3 estabilidade temporal (Spearman 0,86; 8 de 10 no top 10), V5 não é proxy de população (0,33), V6 robustez ao maior outlier (0,999), V7 modelo nulo (P95 |ρ| 0,14), V8 remoção de indicador (mín. 0,95) passaram.
**V4 reprovou**: convergência com energia medida (CCEE) Spearman 0,20, n = 9, p = 0,61 (inconclusivo por n; limiar não relaxado).
Veredito: IRMM **não validado**. Faltam consulta de pesos (AHP), revisão técnica independente e validação humana das bases. IPES: reprovado (D06).
Origem das análises: "antiga" = já no site (mun_cfem, mun_percap, mun_dep, mun_proc, ee_mun, benef_ano, cfem_min, uf_rank) ou em entrega anterior; "nova" = produzida na frente 8.

## Família de índices e cenários (run_extra.py, cenarios.py, test_extra.py)
- **IVFM** (vulnerabilidade fiscal): 42 municípios com CFEM média ≥ R$ 250 mil/ano; dimensões Dependência (CFEM/PIB), Concentração (HHI substância e titular), Volatilidade (CV mensal, 48 meses); pesos iguais. Validação 4 de 5: o modelo nulo reprovou porque o limiar (0,2) era inatingível com n = 42 (ruído esperado ≈ 0,32); limiar não alterado.
- **IPMM** (pipeline): 246 municípios; Volume de títulos (pesquisa, pré-lavra, requerimentos), Área (pesquisa, rodadas arrematadas e ofertadas), Diversidade (titulares e substâncias). Validação 3 de 4: reprovou a não redundância com o IRMM (0,64 > 0,6). Preditivo: 0,42.
- **Tipologia** IRMM x IVFM por medianas: 5 âncoras expostas, 16 resilientes, 16 pequenas e expostas, 5 pequenas e estáveis. Resolve D-10 (Diversificação deixa de ser decisão aberta como relevância; vira índice separado de vulnerabilidade, ainda sem validação).
- **Cenários de estresse** (ilustrativos): E1–E5 choques de preço (alíquota fixa) e P1–P5 paralisação do maior titular dos 5 primeiros do IRMM. Prospectivos: carteira da previsão v1 como quinta dimensão (3 de 13 projetos com peso). Nenhum cenário é previsão.
- Limiares de validação fixados antes de rodar. Origem: tudo novo, exceto indicadores brutos já no site e a série de demanda da previsão v1.

## Atualização de 19/11/2026 — banco de indicadores 2025 e erro de área nas rodadas

- **Erro encontrado:** `rod.area_ha` (rodadas de disponibilidade) está em unidade ~100× maior que a área dos processos e repete o mesmo processo em várias rodadas/situações. O IPMM entregue antes (indicadores de área arrematada e ofertada) usou esses valores. Efeito no ranking: pequeno (Spearman 0,9945; top 10 igual; Minaçu do 7º para o 9º). Os scripts `run_extra.py` e os resultados do IPMM **não foram refeitos**; fica como pendência.
- **Valores corrigidos** (usados em `build_xlsx.py`): área ÷ 100 e um registro por processo, separando arrematada (situação Conquistada ou Arrematada) de ofertada (Livre ou Aguardando Leilão, exceto já arrematada). Totais: 1.310.956 ha arrematados (1.467 processos) e 462.760 ha ofertados (1.099 processos).
- **Banco de 20 indicadores por município (2025):** `entregas/MINERA_Goias_Indicadores_2025.xlsx`, gerado por `build_xlsx.py`. Sem índice composto; HHI direto (parcela pela área); Sharpe no lugar do CV.
- **Limites:** população (um valor por município, rótulo 2026) e PIB de 2023 vêm do repositório, não a série estimada 2022–2025 nem o PIB 2022 pedidos; os arquivos do IBGE não puderam ser baixados do ambiente de execução. Trocar a aba Insumos recalcula R3 e R4.
- **Nada aqui é resultado validado de índice:** IRMM 7/8, IVFM 4/5 e IPMM 3/4 critérios; IPES reprovado na validade de face.
