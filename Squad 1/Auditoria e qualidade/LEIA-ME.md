# Auditoria e qualidade dos dados (Frente 1 — Eliel)

## Catálogo das bases

`catalogo_bases.xlsx` lista todas as bases que a plataforma usa, com nome, nível, órgão de origem, arquivos, abas/camadas, campos e
unidades de medida. Os três CSVs ao lado são as mesmas abas, para ler no GitHub e comparar versões.

| Aba | Linhas | O que tem |
|---|---:|---|
| `1_Bases` | 42 | uma por base: nome, nível, órgão, arquivos, formato, links, frequência na fonte, retrato atual, uso no site, principais unidades |
| `2_Abas_camadas` | 415 | cada aba de planilha, camada de shapefile/GeoJSON ou tabela de JSON, com linhas e colunas |
| `3_Campos` | 5.357 | cada campo: tipo, exemplo, unidade de medida e de onde a unidade foi tirada |

Níveis: Fonte bruta (24), Curadoria (10), Base consolidada (2), Pacote do site (6).

**De onde vem cada unidade:** não se aplica (3.344), pelo nome do campo (832), a confirmar (600), dicionário oficial (aba 14) (439), metadado da fonte / conferido no arquivo (142).
Os campos "a confirmar" (600, 11%) são números sem unidade identificável pelo
metadado nem pelo nome; estão destacados em laranja na planilha e entram na lista de correções. Onde estão: SGB_P3M (338), ANM_PLANILHAS_DERIVADAS (133), EPE_BEN (36), SITE_PANORAMA (25), ONS_LT_SE (12), NOTICIAS_RSS (9).

Refazer depois de mudar ou acrescentar uma base: `python scripts/build_catalogo_bases.py`. A lista de bases e as unidades conferidas
na fonte ficam no começo do script (`BASES` e `UNIDADES_CONHECIDAS`); origem, links e frequência vêm de `docs/fontes_de_dados.csv`.
