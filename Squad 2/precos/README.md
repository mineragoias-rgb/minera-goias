# Squad 2 — Preço e custo de energia

Este módulo entrega a **projeção de preço de energia elétrica de 2027 a 2040** e o **custo de energia da mineração em Goiás**,
que é a projeção de preço multiplicada pela demanda. Ele completa o motor econômico-energético: o motor projeta MWh, este
módulo projeta R$/MWh e R$.

```bash
python scripts/build_precos_energia.py     # gera data/precos/precos.json e os CSV em Squad 2/precos/saidas/
python -m unittest discover -s tests -p test_precos.py
```

O resultado aparece na aba **Preços e custo de energia** do Panorama, no painel autenticado.

## O ponto de partida, dito antes de qualquer número

**Não existe nenhum preço de energia neste repositório.** Não há PLD, não há tarifa homologada, não há preço de leilão, não há
preço de contrato. A base da CCEE que temos (`Squad 1/dados/CCEE/`) traz consumo em MWh e capacidade em MW — nunca R$.

Por isso o módulo separa com rigor duas coisas que não se misturam:

| | O que é | De onde vem | Como está marcado |
|---|---|---|---|
| **Consumo** | Observação | Parcelas de carga da CCEE em Goiás, 2024–2026 | `observado` |
| **Preço** | Premissa do Squad 2 | `premissas/premissas_preco_energia.csv` | `premissa_ilustrativa` |
| **Demanda futura** | Premissa do Squad 2 | `premissas/premissas_demanda_energia.csv` | `premissa_ilustrativa` |

Os valores de premissa servem para o pipeline e o painel rodarem de ponta a ponta e para mostrar **a estrutura** da projeção.
Eles não foram conferidos contra fonte oficial e **não são evidência empírica**: precisam ser substituídos pelas séries da
seção "O que falta coletar" antes de qualquer entrega. Todo quadro do painel que mostra preço ou custo carrega esse aviso.

## Como o preço é modelado

O preço que um consumidor livre paga não é um número só; são três componentes, somados em R$ reais do ano base, sem ICMS:

| Componente | O que é | O que determina |
|---|---|---|
| `energia` | Energia contratada (commodity) | PLD, hidrologia, contratos bilaterais, custo de expansão nos leilões |
| `uso_de_rede` | TUSD e TE, uso do sistema de distribuição e transmissão | Reajuste tarifário da ANEEL, RAP da transmissão, reforços de rede |
| `encargos_e_perdas` | CDE, encargos de sistema, perdas técnicas | Política setorial e regulação |

A energia é a parte volátil e reverte a um nível de longo prazo; a rede e os encargos são regulados e se movem por tendência.
O módulo trata cada um com a forma que lhe cabe:

```
reversao_a_media   P(t) = L·(1 + g)^t + (P0 − L)·e^(−λ·t),   λ = ln 2 / meia-vida
tendencia_real     P(t) = P0·(1 + g)^t
```

`P0` é o preço no ano base, `L` o nível de longo prazo do cenário, `g` a tendência real ao ano e `t` os anos desde o ano base.
A meia-vida diz em quantos anos metade da distância entre `P0` e `L` é percorrida.

Os três cenários mantêm os nomes do motor, e para preço significam **oferta de geração**, não produção mineral:

- `conservador` — oferta apertada, hidrologia desfavorável, encargos crescendo: preço real mais alto;
- `referencia` — estabilidade em termos reais;
- `expansao` — expansão renovável mais rápida que a demanda: preço real mais baixo.

## Como o custo é calculado

```
custo(ano) = demanda(ano) [MWh] × preço(ano) [R$/MWh]
```

O cenário de preço e o cenário de demanda são **cruzados**, não amarrados: o painel mostra a matriz 3 × 3, porque preço de
energia não determina produção mineral e produção mineral não determina preço de energia. Combinar os dois no mesmo rótulo
esconderia uma hipótese dentro da outra.

A demanda tem duas origens possíveis:

1. **hoje** — o consumo observado da CCEE anualizado, crescendo à taxa de premissa de cada cenário. É um cenário de
   referência, não previsão;
2. **quando o motor entregar** — a série `projecao_total_goias` do motor econômico-energético, que hoje só roda sobre dados
   sintéticos (`estimated_demo`). O campo `meta.demanda_motor` do pacote fica `null` até isso acontecer.

## O recorte do consumo mineral

A base da CCEE cobre 16 ramos de atividade. O recorte mineral usa o critério mais forte que o repositório já tem: **a carga
cuja raiz de CNPJ aparece como titular na base consolidada do Squad 1** (aba `02_dim_empresas`) — o mesmo vínculo do
Panorama. O campo autodeclarado `RAMO_ATIVIDADE` fica como recorte alternativo, mais largo, publicado ao lado para
comparação (`mwh_ramo`), como manda a `METODOLOGIA.md` §3.1.

Nenhum ano da base está completo (2024 tem 4 meses; 2025, 7; 2026, 7), então o baseline é a **média mensal do ano com mais
meses cobertos × 12**, e o pacote diz quantos meses entraram nessa conta. Toda a carga observada está no mercado livre: o
campo `CONSUMO_CATIVO_PARC_LIVRE` é zero em todas as linhas.

## Contrato de dados: `energy_prices`

Esta é a oitava tabela do contrato do motor (as sete primeiras estão em `Squad 2/README (1).md`). A camada de integração deve
entregar os preços neste formato, por CSV ou por consulta ao banco:

| Campo | Obrigatório | Descrição |
|---|---:|---|
| `year` | Sim | Ano de referência. |
| `scenario` | Sim | `conservador`, `referencia` ou `expansao`. |
| `component` | Sim | `energia`, `uso_de_rede` ou `encargos_e_perdas`. Componentes não se somam entre cenários. |
| `price_brl_mwh` | Sim | Preço em R$ por MWh, reais da moeda do ano base. |
| `currency_base_year` | Sim | Ano da moeda. Nenhum valor nominal entra sem deflator declarado. |
| `market` | Sim | `acl` ou `cativo`: o preço de um não serve para o outro. |
| `subgroup` | Não | Subgrupo tarifário (A2, A3, A3a, A4) quando a fonte distinguir. |
| `data_nature` | Sim | `observado`, `estimado` ou `premissa_*`. Premissa nunca é registrada como observação. |
| `source_id` | Sim | Fonte no catálogo `fontes_preco_energia.csv`. |
| `method` | Sim | Como o valor foi obtido: série direta, média, projeção, deflação. |
| `uncertainty` | Não | Faixa ou intervalo, quando a fonte permitir. |

Regras de validação antes de entregar:

- preço não pode ser negativo e a soma dos componentes é o preço total do cenário no ano;
- ACL e cativo não se somam nem se substituem sem regra documentada;
- valor nominal só entra com o deflator e o ano-base declarados;
- ausência fica ausência: nada é preenchido com zero;
- cobertura completa de 2027 a 2040 nos três cenários, como já vale para o resto do motor.

## O que falta coletar

O catálogo completo, com URL e granularidade, está em `premissas/fontes_preco_energia.csv`. Em resumo:

| Série | Fonte | Para que serve |
|---|---|---|
| PLD do submercado Sudeste/Centro-Oeste | CCEE | Ancorar o componente de energia e medir a volatilidade |
| Preço médio de contratos do ACL | CCEE (InfoMercado) | O preço efetivamente pago por consumidor livre industrial |
| TUSD e TE homologadas | ANEEL | O componente de uso de rede das cargas em Goiás |
| Preço médio dos leilões de energia nova | ANEEL/MME | O nível de longo prazo: custo de expansão da oferta |
| Preço de referência do PDE | EPE | A única projeção oficial no horizonte do motor |
| Carga e geração do SIN | ONS | Justificar a direção de cada cenário |
| IPCA | IBGE | Deflator de tudo |

Enquanto isso não chega, cada valor de preço no painel aparece marcado como premissa. Substituir é editar os CSV de
`premissas/`, rodar `scripts/build_precos_energia.py` de novo e trocar `data_nature` e `source_id` das linhas que passarem a
vir de fonte oficial.

## Estrutura

```text
Squad 2/precos/
├── README.md
├── premissas/
│   ├── premissas_preco_energia.csv      # componente × cenário: ancoragem, faixa, nível de longo prazo, tendência
│   ├── premissas_demanda_energia.csv    # crescimento da demanda por cenário, até o motor entregar a série real
│   └── fontes_preco_energia.csv         # catálogo de fontes, com o que já está em uso e o que falta coletar
└── saidas/
    ├── precos_energia_projetados.csv    # ano × cenário × componente, 2027–2040
    ├── custo_energia_projetado.csv      # ano × cenário de preço × cenário de demanda
    └── consumo_observado_ccee.csv       # o observado que entra na conta, por ano
```

## Governança

O pacote publicado no painel não nomeia pessoa física: só razão social de pessoa jurídica sai em `observado.por_empresa`, com
a mesma máscara de CPF da base consolidada. O custo por empresa é uma conta de carga observada × preço de premissa — não é
gasto declarado por nenhuma empresa, e não deve ser apresentado como tal.
