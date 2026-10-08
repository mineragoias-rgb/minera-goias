# Dados brutos — Squad 1 / Estudante 1

Arquivos originais usados para gerar a base consolidada do Squad 1 (pasta [`../Bases consolidadas/`](../Bases%20consolidadas/)), uma pasta por fonte, no formato em que a fonte publica. O catálogo completo de cada fonte — URL oficial, metadados, período, sha256 e as abas que usam cada uma — está na aba `07_dim_fontes` da planilha v17.

- **Nada foi corrigido aqui.** Tratamento, padronização e divergências ficam no pipeline e nas abas de auditoria da planilha.
- **Cadastro Mineiro recortado para Goiás.** Os 13 arquivos da ANM são nacionais (309.950 linhas, 71,6 MB). Aqui ficam só as linhas de Goiás (21.048 linhas, 4,9 MB): município de Goiás pela mesma regra que o pipeline usa, ou processo com poligonal em Goiás no SIGMINE (processos de divisa podem ter só município de outro estado no Cadastro); as linhas de cada arquivo continuam exatamente como a ANM publica. `Guia_de_Utilizacao_Autorizada.csv` não tem município e é recortado só pelo processo. A regra, o sha256 do arquivo nacional e as contagens estão em `ANM - Cadastro Mineiro/recorte_goias.json`. O pipeline rodado sobre o recorte gera a mesma planilha que o arquivo nacional.
- **Dados pessoais.** Os arquivos da ANM (Cadastro Mineiro, CFEM e SIGMINE) são publicados aqui como a ANM os divulga e trazem, em algumas linhas, nome e CPF de titulares pessoa física. A base consolidada mascara o CPF (`***456789**`) e não publica esses nomes no atlas.
- **Importador do site.** Os CSV e XLSX desta pasta são carregados no banco do site como fontes não validadas; ZIP, JSON, GeoJSON, ODS e PDF só entram no catálogo.
- **Rodar o pipeline.** `caminhos.py` encontra esta pasta sozinho quando o pipeline roda a partir de `Bases consolidadas/`; na cópia de trabalho os mesmos arquivos ficam em `dados/`. A planilha cita sempre o caminho lógico (`dados/ANM/cfem/…`); a correspondência com as pastas daqui está em `PASTAS_BRUTOS`, no `caminhos.py`. Clonar o repositório muda a data dos arquivos, por isso a data de acesso de cada um fica registrada em `datas_de_acesso.json`, que o pipeline usa no lugar da data do arquivo.

## Fontes

| Pasta | Fonte | Tipo | Período coberto | Arquivo do dia | Usada em |
|---|---|---|---|---|---|
| `ANM - Anuário Mineral Brasileiro (AMB)` | **SRC_ANM_PROD_BRUTA** — ANM — Anuário Mineral Brasileiro (AMB): produção bruta (minério ROM) | oficial | 2010–2025 | 2026-09-10 | 01_dim_minerais; 08_fato_producao_energia; 09_cons_mineral_ano; 12_interface_squad1_squad2 |
| `ANM - Anuário Mineral Brasileiro (AMB)` | **SRC_ANM_PROD_BENEF** — ANM — Anuário Mineral Brasileiro (AMB): produção beneficiada | oficial | 2010–2025 | 2026-09-10 | 01_dim_minerais; 08_fato_producao_energia; 09_cons_mineral_ano; 12_interface_squad1_squad2 |
| `ANM - CFEM` | **SRC_ANM_CFEM** — ANM — CFEM: arrecadação (recorte Goiás de CFEM_Arrecadacao_2022_2026) | oficial | 2022-01 a 2026-08 (registros criados até 2026-08-04) | 2026-09-10 | 01_dim_minerais; 02_dim_empresas; 03_dim_operacoes; 04_dim_projetos; 08_fato_producao_energia; 09_cons_mineral_ano; 10_cons_municipio_ano; 11_cons_empresa_ano_mineral; 12_interface_squad1_squad2; 13_mapas_camadas |
| `ANM - Cadastro Mineiro` | **SRC_ANM_CADASTRO** — ANM — Cadastro Mineiro (SCM): títulos e requerimentos | oficial | fotografia da situação cadastral na data dos arquivos | 2026-09-10 | 01_dim_minerais; 02_dim_empresas; 03_dim_operacoes; 04_dim_projetos; 09_cons_mineral_ano; 10_cons_municipio_ano; 11_cons_empresa_ano_mineral; 12_interface_squad1_squad2; 13_mapas_camadas |
| `ANM - Investimento em pesquisa mineral` | **SRC_ANM_INVEST_PESQUISA** — ANM — Investimento em pesquisa mineral por UF | oficial | 2001–2025 | 2026-09-10 | disponível em dados/, ainda não usada |
| `ANM - Planilhas derivadas` | **SRC_ANM_PANORAMA_DERIVADO** — Panorama da Mineração em Goiás (análise derivada de dados ANM, extração de 04/08/2026) | derivada | 2007–2026 conforme a aba | 2026-08-27 | usada só como validação cruzada |
| `ANM - Planilhas derivadas` | **SRC_ANM_MINERADORAS_DERIVADO** — Mineradoras de Goiás: operação atual e potencial (análise derivada de SIGMINE, CFEM, TAH e REPEM da ANM) | derivada | CFEM de 2022 a 2026 nas colunas da planilha; 'operação atual' = CFEM positiva em 2025 ou 2026 (critério da própria planilha) | 2026-08-27 | disponível em dados/, ainda não usada |
| `ANM - SIGMINE` | **SRC_ANM_SIGMINE** — ANM — SIGMINE: polígonos dos processos minerários de Goiás | oficial | fotografia na data do arquivo | 2026-09-10 | 01_dim_minerais; 02_dim_empresas; 03_dim_operacoes; 04_dim_projetos; 06_dim_ocorrencias_geologicas; 09_cons_mineral_ano; 11_cons_empresa_ano_mineral; 12_interface_squad1_squad2; 13_mapas_camadas |
| `IBGE - Malha municipal 2025` | **SRC_IBGE_MALHA_2025** — IBGE — Malha Municipal Digital 2025 (Goiás) | oficial | limites vigentes em 2025 (arquivo publicado em 26/02/2026) | 2026-09-10 | 03_dim_operacoes; 04_dim_projetos; 05_dim_municipios; 06_dim_ocorrencias_geologicas; 10_cons_municipio_ano; 12_interface_squad1_squad2; 13_mapas_camadas |
| `IBGE - População e PIB (SIDRA)` | **SRC_IBGE_POP** — IBGE — Estimativas de população (SIDRA, tabela 6579, variável 9324) | oficial | 2025 (5571 municípios do Brasil no arquivo; mais 1 linha(s) de nível Unidade da Federação) | 2026-08-27 | 10_cons_municipio_ano; 13_mapas_camadas |
| `IBGE - População e PIB (SIDRA)` | **SRC_IBGE_PIB** — IBGE — PIB dos Municípios (SIDRA, tabela 5938, variável 37) | oficial | 2023 (5570 municípios do Brasil no arquivo; mais 1 linha(s) de nível Unidade da Federação) | 2026-08-27 | 10_cons_municipio_ano; 13_mapas_camadas |
| `IBGE - População e PIB (SIDRA)` | **SRC_IBGE_POP_UF** — IBGE — Estimativa de população de Goiás (SIDRA, tabela 6579, variável 9324, nível UF) | oficial | 2025 (Goiás: 7.423.629 pessoas) | 2026-08-27 | disponível em dados/, ainda não usada |
| `IMB - Goiás em Dados` | **SRC_IMB_GOIAS_EM_DADOS** — IMB — Goiás em Dados (4 consultas: energia elétrica e produção mineral estadual) | oficial | consulta (1).csv: colunas 2005–2025, último ano com valor 2025 / consulta (2).csv: colunas 2005–2025, último ano com valor 2025 / consulta (3).csv: colunas 2005–2025, último ano com valor 2016 / consulta.csv: colunas 2005–2025, último ano com valor 2025 | 2026-09-10 | usada só como validação cruzada (14b: produção do estado × AMB) |
| `SGB - GeoSGB geoquímica` | **SRC_SGB_GEOSGB** — SGB — GeoSGB: pacotes de geoquímica (Oeste de Goiás, Noroeste de Goiás/Bonópolis, Folha Goiás PLGB) | oficial | Folha Goiás - PLGB (1991): coleta 1991–1997; Geologia e Metalogenia do Oeste de Goiás (2017): coleta 1916–2017; Noroeste de Goiás - Folha Bonópolis (2007): coleta 2007–2008 | 2026-09-10 | 13_mapas_camadas |
| `SGB - RECMIN` | **SRC_SGB_RECMIN** — SGB — GeoSGB: Ocorrências de Recursos Minerais (RECMIN), recorte de Goiás pelo WFS oficial | oficial | cadastros no GeoSGB de 2001-10-21 a 2020-02-03 (68% em 2003, carga do banco); baixado em 2026-09-12 | 2026-09-12 | 01_dim_minerais; 06_dim_ocorrencias_geologicas; 13_mapas_camadas |

Links oficiais:

- **SRC_ANM_PROD_BRUTA**: https://dadosabertos.anm.gov.br/AMB/Producao_Bruta.csv (metadados: https://dadosabertos.anm.gov.br/AMB/metadados-amb.ods (cópia em dados/ANM/producao_amb_ral/))
- **SRC_ANM_PROD_BENEF**: https://dadosabertos.anm.gov.br/AMB/Producao_Beneficiada.csv (metadados: https://dadosabertos.anm.gov.br/AMB/metadados-amb.ods (cópia local))
- **SRC_ANM_CFEM**: https://dadosabertos.anm.gov.br/CFEM/CFEM_Arrecadacao_2022_2026.csv (metadados: https://dadosabertos.anm.gov.br/CFEM/metadados-cfem.ods (cópia em dados/ANM/cfem/))
- **SRC_ANM_CADASTRO**: https://dadosabertos.anm.gov.br/SCM/<arquivo>.csv — 13 arquivos (Alvara_de_Pesquisa, Cessoes_de_Direitos, Guia_de_Utilizacao_Autorizada, Licenciamento, PLG, Portaria_de_Lavra, …) (metadados: https://dadosabertos.anm.gov.br/SCM/metadados-scm.ods (cópia em dados/ANM/cadastro_mineiro/))
- **SRC_ANM_INVEST_PESQUISA**: não verificada
- **SRC_ANM_PANORAMA_DERIVADO**: —
- **SRC_ANM_MINERADORAS_DERIVADO**: —
- **SRC_ANM_SIGMINE**: https://dadosabertos.anm.gov.br/SIGMINE/PROCESSOS_MINERARIOS/GO.zip (metadados: https://dadosabertos.anm.gov.br/SIGMINE/metadados-sigmine.ods (NÃO baixado))
- **SRC_IBGE_MALHA_2025**: https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/malhas_municipais/municipio_2025/UFs/GO/GO_Municipios_2025.zip (metadados: Nota metodológica da Malha Municipal (leitura exigida pelo leia-me do arquivo))
- **SRC_IBGE_POP**: https://apisidra.ibge.gov.br/values/t/6579/n6/all/v/9324/p/2025 (consulta equivalente ao arquivo local) (metadados: https://apisidra.ibge.gov.br/desctabapi.aspx?c=6579)
- **SRC_IBGE_PIB**: https://apisidra.ibge.gov.br/values/t/5938/n6/all/v/37/p/2023 (consulta equivalente ao arquivo local) (metadados: https://apisidra.ibge.gov.br/desctabapi.aspx?c=5938)
- **SRC_IBGE_POP_UF**: https://apisidra.ibge.gov.br/values/t/6579/n3/52/v/9324/p/2025 (consulta conferida em 12/09/2026: mesmo valor do arquivo local) (metadados: https://apisidra.ibge.gov.br/desctabapi.aspx?c=6579)
- **SRC_IMB_GOIAS_EM_DADOS**: exportação manual do Goiás em Dados (parâmetros da consulta não registrados)
- **SRC_SGB_GEOSGB**: não verificável automaticamente (o portal é uma aplicação JavaScript) — registrar o link de download à mão
- **SRC_SGB_RECMIN**: https://geoservicos.sgb.gov.br/geoserver/ows?service=WFS&version=2.0.0&request=GetFeature&typeNames=geosgb:ocorrencias_recursos_minerais&outputFormat=application/json&bbox=-19.7,-53.4,-12.2,-45.8,urn:ogc:def:crs:EPSG::4326 (metadados: DescribeFeatureType do WFS (geosgb:ocorrencias_recursos_minerais); ArcGIS REST: https://geoportal.sgb.gov.br/server/rest/services/geologia/ocorrencias/MapServer/0)

## Arquivos

### ANM - Anuário Mineral Brasileiro (AMB)

| Arquivo | Tamanho | sha256 |
|---|---:|---|
| `Producao_Beneficiada.csv` | 0,7 MB | `027cde9a3bec8d016f67bf5cdebfcfeaf4efaefb1dc7a0f4254d67725e324616` |
| `Producao_Bruta.csv` | 1,0 MB | `6fca5e529bee0b1e7a6822802ba2e19cb6b8109f83707913e4254086ef4a2894` |
| `metadados-amb.ods` | 0,0 MB | `4028572f4f5d345912e7143e126ecb12adfa249fe33ae6f614b8553ed215926c` |

### ANM - CFEM

| Arquivo | Tamanho | sha256 |
|---|---:|---|
| `CFEM_Arrecadacao_2022_2026_GO.csv` | 3,9 MB | `bc86b23e7347adcf03609e889b237984ba952c7799ccae3850e11d7a8e3db339` |
| `metadados-cfem.ods` | 0,0 MB | `87cbdbbbc852c9cf83ef0bbe3114e85c259a0e9808b106c191611b7b9bfd7902` |

### ANM - Cadastro Mineiro

| Arquivo | Tamanho | sha256 |
|---|---:|---|
| `Alvara_de_Pesquisa.csv` | 1,9 MB | `c4360a30ce9bb1ee3933914a733153e025bffd6ec68f1ef0dfde416728b90423` |
| `Cessoes_de_Direitos.csv` | 1,0 MB | `5a893a7ec26130421930380541742208815dfcc78221ef338bd9b662cbe31228` |
| `Guia_de_Utilizacao_Autorizada.csv` | 0,1 MB | `1d5a1d82b95282c032f8708e862f9acb1ee8cb46dbb3ee39e85d99e804f68e10` |
| `Licenciamento.csv` | 0,3 MB | `ee47e23b9e7dbf442f879cf5175657e91f8f212dca89d9abe1f7c90f626a7abd` |
| `PLG.csv` | 0,0 MB | `cc7dc11802bceb26373fccecb476ec83aa1e53baae87772c1e03aa7c4de6e18a` |
| `Portaria_de_Lavra.csv` | 0,3 MB | `f5805f5addd0e77f560a8f1943387169e9d1014f066dbb74509e9643a491f1be` |
| `Registro_de_Extracao_Publicado.csv` | 0,0 MB | `a44cf6559887b35db73a09b639d9d85c85392821cf9c75610ed8801dd22eb8b9` |
| `Relatorio_de_Pesquisa_Aprovado.csv` | 0,3 MB | `fbfaec42ef30e61885cf4a14cc1365beff2cd68ae9aaec07e673b0cb799fbc1f` |
| `Requerimento_de_Lavra.csv` | 0,3 MB | `c1add5e59592c033a4792dca47861d51bb295c870ef43329c2f956804f1d08a5` |
| `Requerimento_de_Licenciamento.csv` | 0,2 MB | `f867df3a64f9a16ad821f7e56e4d8cb5e6f4e92c09c7a31fe9e78aaffd61abaa` |
| `Requerimento_de_PLG.csv` | 0,2 MB | `6d017c4784a84d39f118e603ca605b5e0f7b770dfe0c0d1892d1a940876e5aa3` |
| `Requerimento_de_Pesquisa.csv` | 0,2 MB | `5bdc41cf3def3771a64bea62ea515e02e4509a672b3e825a3517bc2c24e1e4c9` |
| `Requerimento_de_Registro_de_Extracao_Protocolizado.csv` | 0,0 MB | `040335d8a42993beee7b76d8b130af275aa45d9a7b06b4ff542e9c044fc7da3d` |
| `mer-microdados-scm.pdf` | 0,2 MB | `25c441c6eaefcc232448ef18d05f863dc91b31a4d22f17a10e944378fdd7927b` |
| `metadados-microdados-scm.ods` | 0,0 MB | `e0d80cf6e750061d508991ebdc4454b5c5bcb363af6da71db15f7f8253b5e06e` |
| `metadados-scm.ods` | 0,0 MB | `6dc51381dd00a7ea36e3da329a3bac5438e45f5ad795908d85b4aee89ea50abb` |
| `recorte_goias.json` | 0,0 MB | `e29e3271c18c5f04fd2d5194f257c7264e22b617516ba1fec07fe1508a3a0c35` |

Recorte de Goiás (linhas no arquivo nacional → aqui):

| Arquivo | Regra | Linhas nacionais | Linhas aqui | sha256 do arquivo nacional |
|---|---|---:|---:|---|
| `Alvara_de_Pesquisa.csv` | municipio_ou_processo | 111.614 | 8.130 | `2c3bd1bae003ec47dd91c55dab949c4781df7c15638fcd71f4daa81ee35efaf1` |
| `Cessoes_de_Direitos.csv` | municipio_ou_processo | 55.081 | 4.022 | `59d9482213b73ea9966820761cea1602c49a95ddeb86e972d0ab607461a1ebe2` |
| `Guia_de_Utilizacao_Autorizada.csv` | processo | 12.260 | 652 | `35ca5577cef7a14dde44f0bc8c80c9b7a81fe63a9d0cd03d1b53f843041d4ff6` |
| `Licenciamento.csv` | municipio_ou_processo | 21.553 | 1.652 | `40058091fc646e6bd14e49800c51ccc431cf48adc6751a437cda3ef44910a2ce` |
| `PLG.csv` | municipio_ou_processo | 3.244 | 103 | `6ad95b893823ea20a3efd44f4a4404c870d250d2f5fbf75044975a32e5ad5e88` |
| `Portaria_de_Lavra.csv` | municipio_ou_processo | 15.493 | 1.136 | `382c0e28fd1df469ea8646f103c57dccc14d6c90621210b5f91f17328a933cd9` |
| `Registro_de_Extracao_Publicado.csv` | municipio_ou_processo | 3.968 | 43 | `1f58d82f59c7cd5c36dde5decad34e2a7f62288139cb2d5db22ced5bb2718f60` |
| `Relatorio_de_Pesquisa_Aprovado.csv` | municipio_ou_processo | 15.695 | 1.179 | `bb69c04de5d69d07308cfb2317a3ac6460fa10f3d8d3f234b60a814db30be3fd` |
| `Requerimento_de_Lavra.csv` | municipio_ou_processo | 21.371 | 1.237 | `bbfa50fe50f2361b2ad5fb7b0c2423ecae06136cb03002a9609f171bb678d7dc` |
| `Requerimento_de_Licenciamento.csv` | municipio_ou_processo | 9.136 | 916 | `7fff5438a2d9c0fe4aa897c6d5819c8d4c386b615df1f243e372bf66832c011f` |
| `Requerimento_de_PLG.csv` | municipio_ou_processo | 19.317 | 1.000 | `1cbb63b6967a135856fd97191f4b834f373b11d3c3d9e1a7715e258964bd9390` |
| `Requerimento_de_Pesquisa.csv` | municipio_ou_processo | 18.916 | 954 | `0d8e3c1bc45d00eb2e656070b2f4db868ea3338ddb6449387128e2f343eada64` |
| `Requerimento_de_Registro_de_Extracao_Protocolizado.csv` | municipio_ou_processo | 2.302 | 24 | `bb1fc4347a4510121ac520d87a6a181d814bb273254460b388ff600e36189dfe` |

### ANM - Investimento em pesquisa mineral

| Arquivo | Tamanho | sha256 |
|---|---:|---|
| `InvestimentoPesquisaMineralUf.csv` | 1,3 MB | `1e15bc35c5af92f5285d0de2ccc28b2b2d3c503976eeb00be512839fd802f315` |

### ANM - Planilhas derivadas

| Arquivo | Tamanho | sha256 |
|---|---:|---|
| `Mineradoras_Goias_operacao_e_potencial.xlsx` | 4,8 MB | `6298f68de1a362ad60c80e7e8c545dcd59aeaa0ac740cc9c09998a632216a10a` |
| `Panorama_Mineracao_Goias_ANM.xlsx` | 0,4 MB | `74cb13306d38f2c8baa6bf8c5b4dbbf4b3a5d3c83d2ce632577935f29516c694` |

### ANM - SIGMINE

| Arquivo | Tamanho | sha256 |
|---|---:|---|
| `GO.zip` | 10,3 MB | `f6a43c2aef6adfeb71734573b638a070711e6244214f3cd6030b2d32e0379bbb` |

### IBGE - Malha municipal 2025

| Arquivo | Tamanho | sha256 |
|---|---:|---|
| `GO_Municipios_2025.zip` | 17,4 MB | `56c41ceb00692f0bb2171ed688289c58c076621983eeaa8981071a79f64de86a` |

### IBGE - População e PIB (SIDRA)

| Arquivo | Tamanho | sha256 |
|---|---:|---|
| `pib_municipal_goias_ultimo_ano.json` | 1,6 MB | `4033d9c02d3bb49e5f8bb6128feaa6e40ee2e1f556a1d7251133ee332106237c` |
| `populacao_goias_ultimo_ano.json` | 0,0 MB | `283a2e45946d943ee3d977452c06de8d78b5d3998f045e180daebe67dbb533db` |
| `populacao_municipal_goias_ultimo_ano.json` | 1,5 MB | `70dd0b961e2eaa28932bd74b4763f396d32e8fa2508cd1df66491aff0d833653` |

### IMB - Goiás em Dados

| Arquivo | Tamanho | sha256 |
|---|---:|---|
| `consulta (1).csv` | 0,3 MB | `34d29a7c9e131136081913ce9af395e400a6a3d1cedf72582afbff034cc43963` |
| `consulta (2).csv` | 0,2 MB | `22d65b3e0c9b66ad84ffc986098343fabd01bf5bb854e11d60a6f267c761e10a` |
| `consulta (3).csv` | 0,4 MB | `39e69b432f429cc624d8bf30e64556fb7654adb40873438fdf1915a3c848ae82` |
| `consulta.csv` | 0,6 MB | `af6261768442d2a8b53b52b481d3f0cec1a1e931a87fef60c0edf7fdcdfeaac8` |

### SGB - GeoSGB geoquímica

| Arquivo | Tamanho | sha256 |
|---|---:|---|
| `geoquimica_Fl_goias_PLGB_1999_vr1.zip` | 0,5 MB | `0ab0fc15ff9accf8d711a6e6895fd610fa2a8da4ee0390c1a95e25a214e852cc` |
| `geoquimica_metalogenia_oeste_de_goias_2017.zip` | 0,6 MB | `168375816b50a22e74706db0884f2296461bc77961ce3c65ee276ed8b0be3300` |
| `geoquimica_noroeste_de_goias.zip` | 0,2 MB | `4115a6833e468e3f5d14ab090986ee497a0d9b07192ce617561fb7a3c0a46ce0` |

### SGB - RECMIN

| Arquivo | Tamanho | sha256 |
|---|---:|---|
| `ocorrencias_recursos_minerais_GO.geojson` | 2,9 MB | `9449760936e4ed8477840da7fe8036a41d932e7eae4ae9d876057997e868bc35` |
| `ocorrencias_recursos_minerais_GO.metadados.json` | 0,0 MB | `31c932292405a5663399413c453a9e5b758256068839bee73ee3b265c9569bfb` |

## Fontes catalogadas que não estão aqui

Não alimentam as abas de dados da base consolidada; ficam só na cópia de trabalho do Estudante 1, com link e sha256 na aba 07.

- **SRC_ANM_AGUA_MINERAL** — ANM — AMB: produção de água mineral (disponível em dados/, ainda não usada).
- **SRC_IBGE_MALHA_2024** — IBGE — Malha Municipal Digital 2024 (Goiás) (disponível em dados/, não usada (o pipeline usa a malha 2025)).
- **SRC_SGB_GEOQUIMICA_NAZARIO** — SGB — Geoquímica do Projeto Sudeste de Goiás, Folha Nazário (resultados analíticos em planilha) (disponível em dados/, ainda não usada).
- **SRC_SGB_SIG_GEOLOGIA** — SGB — SIG geológicos 1:250.000 (ARIM Centro-Norte da Faixa Brasília, Oeste de Goiás integrado, Folha Barro Alto) (disponível em dados/, ainda não usada).
- **SRC_SGB_MAPAS_REFERENCIA** — SGB — mapas de referência de Goiás em PDF (recursos minerais, favorabilidade, metalogenético, geológico-geofísico, agrominerais, geotécnico) (referência (PDF, não estruturado)).

## Fontes de energia ainda não usadas pela base consolidada

Coletadas pelo Eliel em 27/08/2026 na cópia de trabalho (`Squad 1/Dados/EPE/` e `Squad 1/Dados/energia/`) e nunca enviadas ao GitHub; entraram aqui em 08/10/2026, byte a byte. **Nenhum código do repositório as lê ainda** e elas não constam da aba `07_dim_fontes` da v17. São o lado da energia que o projeto vai precisar — demanda projetada (PDE), balanço por estado (BEN), geração (ANEEL) e rede (ONS) —, e o módulo de preços arquivado na tag `archive/claude-price-overview-20260914` listava PDE e ONS entre o que faltava coletar.

Ao contrário do Cadastro Mineiro, **não foram recortadas para Goiás**: os arquivos são pequenos e linhas e subestações de divisa ligam Goiás a outros estados. Filtrar por UF é tarefa de quem for usá-los. A data de cada arquivo é a da coleta (27/08/2026), salvo quando o próprio arquivo traz outra.

| Pasta | Fonte | Página oficial | Observação |
|---|---|---|---|
| `EPE - Balanço Energético Nacional (BEN)` | EPE — BEN 2026 (ano-base 2025): capítulo 2 (oferta e demanda por fonte, 1970–2025), capítulo 8 (dados estaduais, 2000–2025), matriz energética 2026 e matriz de autoprodução de eletricidade por setor e fonte | https://www.epe.gov.br/pt/publicacoes-dados-abertos/publicacoes/balanco-energetico-nacional-ben | a cópia local tinha o capítulo 2 duplicado (`(1)`), idêntico byte a byte; só uma cópia entrou |
| `EPE - Plano Decenal de Energia (PDE 2035)` | EPE — PDE 2035: painel de resultados (dados abertos), caderno de demanda de energia e eficiência, e dados do relatório final (12 planilhas, uma por capítulo) | https://www.epe.gov.br/pt/publicacoes-dados-abertos/publicacoes/plano-decenal-de-expansao-de-energia-2035 | planilhas do zip datadas de 17/07/2026 |
| `ANEEL - SIGA` | ANEEL — SIGA: empreendimentos de geração (25.133 linhas, todas as UFs) | https://dadosabertos.aneel.gov.br/dataset/siga-sistema-de-informacoes-de-geracao-da-aneel | `DatGeracaoConjuntoDados` = 2026-08-25 |
| `ONS - Dados abertos` | ONS — linhas de transmissão (2.330) e subestações (1.687) da Rede Básica, todas as UFs | https://dados.ons.org.br/dataset/linha-transmissao · https://dados.ons.org.br/dataset/subestacao | — |

| Arquivo | Tamanho | sha256 |
|---|---:|---|
| `EPE - Balanço Energético Nacional (BEN)/Capítulo 2 (Oferta e Demanda de Energia por Fonte) - 1970 a 2025.xlsx` | 0,3 MB | `7e03c244604e8ec8a63f0df2cdb7466ca89d33a0807cca11e0c61160dd51fdf3` |
| `EPE - Balanço Energético Nacional (BEN)/Capítulo 8 (Dados Estaduais) - 2000 a 2025.xlsx` | 1,3 MB | `9d33d2a572e76672eb707d5798d09b34eeb85cc4392970eb88628e3d2f1dce7d` |
| `EPE - Balanço Energético Nacional (BEN)/Matriz 2026 - ano-base 2025.xlsx` | 0,2 MB | `575d3739438bc109116b274c5e8c434c0c1e33a89f935caed2d6635f4f040e9b` |
| `EPE - Balanço Energético Nacional (BEN)/matriz_autoproducao_eletrecidade_setor_fonte.xlsx` | 0,0 MB | `aea097904560f06b0cfb0ccd9e06620e3745bfe5b1e391e556f21f6b572a8441` |
| `EPE - Plano Decenal de Energia (PDE 2035)/PDE 2035_Painel de Resultados_Dados Abertos.xlsx` | 0,2 MB | `7bcea0b7131cf311ba773ab5e79cad8231fcb1baf49c9d5db8077a3262028a20` |
| `EPE - Plano Decenal de Energia (PDE 2035)/epe_pde2035_caderno_demanda_energia_eficiencia.pdf` | 3,0 MB | `d544c1aa36629404f6ef0932925330c14cf5b090f246c052671802b77acdabda` |
| `EPE - Plano Decenal de Energia (PDE 2035)/epe_pde2035_dados_relatorio_final.zip` | 7,6 MB | `aac18732cc527fda40b6082593b53705eb596f7e443dd2a7aae81da5075c6f6f` |
| `ANEEL - SIGA/aneel_siga_empreendimentos_geracao.csv` | 8,1 MB | `fd5e0bb41d6017f5a2b9c0014486aef304ed911bb63e59c652a85c125ed642fe` |
| `ONS - Dados abertos/ons_linhas_transmissao.csv` | 0,7 MB | `cc27f9e38d59e7f0b3f70db50c7e227911180adc02822241e9f82c3228a25a03` |
| `ONS - Dados abertos/ons_subestacoes.csv` | 0,2 MB | `e2846a3446ba016e61182bf014f170811313653045d88d306c2f4050d097f6bc` |

O importador do site carrega os CSV e XLSX destas pastas no banco como fontes não validadas, como faz com o resto de `Dados brutos/`.
