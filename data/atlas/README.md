# Atlas — retrato da base consolidada do Squad 1 (13/09/2026)

Os dados do atlas vêm da base consolidada do Squad 1 / Estudante 1 (v19), em `Squad 1/Bases consolidadas/`; os arquivos brutos que ela usa estão em `Squad 1/Dados brutos/`.
O SHA-256 da planilha está em `atlas.json` → `meta.sha256`; os do GeoPackage e do arquivo de investimento, em `meta.base`.
Para gerar de novo, fora da VPS (precisa de geopandas, shapely ≥ 2.1 e openpyxl):

    python scripts/build_atlas_base.py --base "<pasta do projeto do Squad 1>"

O script mantém o formato lido por `public/atlas.js` e troca só os dados. Depois de gerar, revise o diff e rode `tests/test_atlas.py`.

## O que vem da base consolidada

- **246 municípios**: malha municipal do IBGE 2025 (camada `municipios_go` da Base 4), simplificada como cobertura — municípios vizinhos
  compartilham a mesma fronteira, sem frestas. `processes` = processos do SIGMINE que tocam o município; `cfem_total` = CFEM de janeiro
  de 2022 até o fim do arquivo da CFEM.
- **CFEM por município e ano** (`cfem.linhas`): os 246 municípios, com zero onde não houve arrecadação no ano. A soma bate com o arquivo
  bruto da CFEM: R$ 867.578.398,91 (conciliação na aba 14b da planilha). 2026 é parcial: o arquivo usado tem janeiro a julho e os
  registros de agosto criados até 04/08/2026 (período exato em `meta.periods.cfem` e na aba 07).
- **Quantidade comercializada** (`production`): toneladas e CFEM declaradas em 2025, por substância (categoria da ANM) e município. É a
  quantidade comercializada informada na CFEM, não produção. Quantidades em m³, litros e m² ficam fora, assim como as linhas que a base
  exclui da soma de toneladas (aba 09b). "Titulares distintos" conta o `company_id` da base; processos que não estão no Cadastro Mineiro
  aparecem como um único titular não identificado.
- **Ouro — quantidade inconsistente na fonte**: em 2025, os processos de Mara Rosa declaram 9,7 t de ouro na CFEM, enquanto o Anuário
  Mineral registra 3,4 t de ouro beneficiado em Goiás inteiro; e o processo 860567/2021 declara 3,2 t com CFEM de R$ 287 mil, valor de
  minério e não de metal. O atlas mostra o que foi declarado, sem corrigir, com a unidade "kg declarados". Desde a v14 da base, a aba
  09c sinaliza esses casos: em ouro e prata compara com a produção beneficiada do Anuário (metal, em kg) e também acusa R$/t mais de 10×
  abaixo da mediana do metal — 861241/1980 (Mara Rosa) em 2025, com 8,8 t contra 3,4 t do estado, e 860567/2021 de 2023 a 2026.
- **Séries**: CFEM por ano e de janeiro a julho (`cfem_years`, `cfem_comparable`); valor de venda da produção beneficiada de Goiás no
  Anuário Mineral Brasileiro (`beneficiated`); investimento declarado em pesquisa mineral em Goiás (`investment`, arquivo
  `InvestimentoPesquisaMineralUf.csv` da ANM, que reproduz exatamente a série do retrato anterior).
- **16.875 processos** (`processes.json`): um por processo do SIGMINE em Goiás (camada `processos_minerarios_go`), com os fragmentos de
  cada processo unidos; o retrato anterior tinha 17.402 polígonos. Geometria simplificada (tolerância de ~45 m) e quantizada em UInt16;
  os cinco grupos de fase são os mesmos do retrato anterior. Não há titular, CPF ou CNPJ no pacote.
- **3.377 projetos** (`projects`): um ponto por projeto que ainda não produz (aba 04, camada `projetos_futuros` do GeoPackage), com
  classificação (provável, possível, sinal), estágio na ANM e marca de brownfield. O ponto fica dentro dos processos do projeto: 73 caem
  fora de Goiás porque os processos cruzam a divisa, e o município é o da aba 04. O titular só aparece quando é empresa com CNPJ; pessoa
  física e titular sem CNPJ ficam de fora (estão na aba 04 da base, com CPF mascarado).
- **1.796 ocorrências** (`occurrences`): um ponto por ocorrência ou depósito do RECMIN do SGB dentro de Goiás (aba 06, camada
  `ocorrencias_minerais_recmin`). É evidência geológica, não projeto nem mina: 83% dos pontos foram posicionados em carta 1:250.000 e a
  situação é a do cadastro, em geral de 2003.
- **Gráficos das séries** (`charts`), calculados da planilha e conferidos em `tests/test_atlas.py`: CFEM de 2025 por substância e CFEM
  por substância e ano (aba 08; somam o total da CFEM de cada ano); concentração da CFEM de 2025 nos maiores municípios e titulares
  (abas 10 e 11; processos sem titular identificado ficam fora do ranking, mas no total); produção bruta de Goiás por mineral no ano mais
  recente do Anuário (aba 09; as barras não se somam, porque co-produtos repetem a mesma tonelagem); parcela da produção bruta que a aba
  12 atribui a operações com e sem coordenadas; projetos por mineral e classificação (aba 04); ocorrências por substância e importância
  (aba 06; ocorrência com mais de uma substância conta em cada uma).

## O que continua do retrato anterior (`eliel.html`)

A base consolidada do Squad 1 não cobre energia nem barragens. Por isso `energy`, `energy_months` (CCEE, abril/2024 a junho/2026) e
`dams` (23 barragens do SIGBM, data de extração não informada) foram mantidos como estavam; a origem e o SHA-256 do artefato ficam em
`meta.retained_from_artifact`. O extrator do retrato anterior continua em `scripts/extract_atlas.py`. Do `rodrigo.zip` foram adaptados
conceitos de navegação por território, filtros, mapa Leaflet e radar; os registros e cenários demonstrativos foram descartados.

## Limites

Não se mistura este retrato com a importação MySQL: as coberturas diferem. As geometrias são simplificadas — não usar como limite
cadastral nem somar áreas de processos, que podem se sobrepor. As intensidades municipais da camada de energia são razões do artefato,
não parâmetros validados por operação.

Os arquivos ficam fora de `public/` e são servidos só pelos endpoints autenticados `/api/atlas` e `/api/atlas/processes`. O repositório é
público: a autenticação do portal não o torna privado.

Leaflet 1.9.4 é servido localmente, com licença em `public/vendor/leaflet/LICENSE`. Os tiles de mapa-base do OpenStreetMap são carregados
sob demanda, sem cache offline; os polígonos e indicadores locais continuam utilizáveis se os tiles falharem.
