# Retrato do catálogo do P3M

Cópia do que o site P3M (https://p3mgeo.sgb.gov.br/#/map) publica sobre as próprias camadas, tirada em 22/10/2026. É o que
`scripts/build_inventario_p3m.py` usa para classificar e descrever as camadas de `Squad 1/P3M` sem depender do site no ar.

| Arquivo | Origem | O que traz |
|---|---|---|
| `categorias.json` | `https://p3mgeo.sgb.gov.br/api/categorias/?lang=pt-BR` | árvore categoria → tema → subtema → camadas, com metadados (órgão, fonte, resumo, data quando há) e link do shapefile |
| `camadas.json` | `https://p3mgeo.sgb.gov.br/api/camadas/?lang=pt-BR` | as 444 entradas de camada do site, com serviço, tipo de geometria e link da ficha de metadados |
| `opendata_datasets.json` | `https://opendata.sgb.gov.br/api/v2/datasets` | data de publicação e de última atualização das camadas que o portal de dados do SGB cataloga (só uma parte delas) |

Para atualizar o retrato: `python scripts/build_inventario_p3m.py --atualizar-catalogo` (precisa de internet).
