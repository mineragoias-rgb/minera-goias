# Pacote da aba Preços e custo de energia

`precos.json` alimenta a aba **Preços e custo de energia** do Panorama (`public/panorama-cards4.js`), servida autenticada por
`Squad 3/backend/precos.py`. Junta o consumo observado das cargas com título minerário na CCEE com a projeção de preço e de
custo de 2027 a 2040 do Squad 2.

```bash
python scripts/build_precos_energia.py
```

## De onde vem cada bloco

| Chave | Fonte no repositório | Natureza |
|---|---|---|
| `observado.por_ano`, `observado.por_empresa` | `Squad 1/dados/CCEE/parcela_carga_consumo_*_GO.csv`, recortado pelas raízes de CNPJ da aba `02_dim_empresas` | observado |
| `premissas.preco`, `premissas.demanda`, `premissas.fontes` | `Squad 2/precos/premissas/*.csv` | premissa |
| `precos` | calculado das premissas: ano × cenário × componente | premissa |
| `custo` | `demanda × preço`, cruzando cenário de preço com cenário de demanda | premissa |
| `sensibilidade` | variação do custo no fim do horizonte quando um parâmetro muda | premissa |

## Limitações

- **Nenhum preço aqui é observado.** O repositório não tem PLD, tarifa, preço de leilão nem preço de contrato; o que existe é
  premissa do Squad 2, marcada `premissa_ilustrativa` em cada linha e avisada em cada quadro do painel. A lista do que falta
  coletar está no próprio pacote (`premissas.fontes`) e em `Squad 2/precos/README.md`.
- O consumo é de **parcelas de carga do mercado livre**, não do estado inteiro: 2024 cobre 4 meses, 2025 sete e 2026 sete. O
  baseline é a média mensal do ano com mais meses × 12, e não um ano fechado.
- O recorte mineral é por **título minerário na base do Squad 1** (raiz do CNPJ). O recorte por `RAMO_ATIVIDADE` aparece ao
  lado porque é autodeclarado, e os dois não devem ser somados.
- A demanda de 2027 a 2040 é o baseline crescendo a uma taxa de premissa. Quando o motor econômico-energético entregar
  `projecao_total_goias` com dados reais, ela substitui essa conta — `meta.demanda_motor` fica `null` até então.
- Preço e demanda são hipóteses independentes: o custo é publicado como matriz 3 × 3, e um cenário só é "o cenário" quando as
  duas escolhas são ditas.
- Todos os valores são reais na moeda do ano base, sem ICMS. Nenhum valor nominal entra sem deflator declarado.
