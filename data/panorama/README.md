# Pacote da aba Panorama

`panorama.json` alimenta a aba **Panorama** do painel (`public/panorama*.js`), servida autenticada por `Squad 3/backend/panorama.py`. Refaz os
gráficos e tabelas do *Panorama da Mineração de Goiás* com as bases do Squad 1 que estão neste repositório, e deixa o navegador filtrar por ano,
mês, município, mineral, titular, fase do processo, tipo de gasto em pesquisa e ramo da CCEE.

```bash
python scripts/build_panorama_base.py
```

## De onde vem cada tabela

| Chave | Fonte no repositório | Grão |
|---|---|---|
| `cfem` | aba 08 da planilha consolidada (`cfem_recolhido`) | ano × mês × município × mineral × titular |
| `amb_go`, `amb_br`, `amb_uf` | aba 08 (Anuário Mineral Brasileiro, todas as UFs) | ano × mineral (Goiás e Brasil) e ano × UF |
| `proc` | aba 03 (SIGMINE Goiás com titular, CFEM e status) | processo |
| `inv_go`, `inv_br` | `Squad 1/Dados brutos/ANM - Investimento em pesquisa mineral/` | ano × substância × tipo de gasto (Goiás) e ano × gasto (Brasil) |
| `rod` | `Squad 1/dados/ResultadoRodadaDisponibilidade (1).csv` | área ofertada em Goiás |
| `ccee` | `Squad 1/dados/CCEE/parcela_carga_consumo_*_GO.csv` | mês × município × ramo × raiz do CNPJ |
| `dims.mun` | aba 10 da planilha (população e PIB municipal) | município: código, nome, população (2025) e PIB (2023, em R$) |

A energia e a intensidade por município e as barragens vêm do atlas (`data/atlas/atlas.json`), que a aba também carrega.

## Limitações

- Pessoa física não aparece com nome: titular só é nomeado quando o `company_id` é `COM_CNPJ_` e o nome não traz CPF mascarado; arrematante de
  rodada só quando o documento é CNPJ.
- A base CCEE são as parcelas de carga de abril de 2024 a julho de 2026 (não há dado publicado antes de abril/2024 — o conjunto
  `PARCELA_CARGA_CONSUMO` do portal de dados abertos da CCEE foi criado em 29/05/2024). As cargas sem ramo de atividade são das distribuidoras
  Equatorial Goiás e CHESP: ficam no ramo `DISTRIBUIDORA (MERCADO CATIVO)` e representam o mercado cativo; as demais cargas são o mercado livre.
  A ligação carga → titular é pela raiz do CNPJ.
- Somar a produção bruta de minerais diferentes conta duas vezes os co-produtos do mesmo minério.
- Não foram refeitos, por falta de fonte nas bases do repositório: CFEM nacional e ranking das UFs, repasse da CFEM, água mineral, TAH, planos de
  pesquisa (RePEM), processos inativos e coeficientes por operação tirados de relatórios das empresas (lista em `meta.not_reproduced`).
