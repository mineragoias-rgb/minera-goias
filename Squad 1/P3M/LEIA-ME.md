# P3M — camadas do Serviço Geológico do Brasil para Goiás

Camadas do **P3M** (https://p3mgeo.sgb.gov.br/#/map), o portal de dados geocientíficos do Serviço Geológico do Brasil (SGB), baixadas do
GeoServer que o próprio site usa (`https://opendata.sgb.gov.br/geoserver/wfs`, formato SHAPE-ZIP). Coletadas pelo Squad 1 (Estudante 1)
em outubro de 2026.

| Pasta | O que é |
|---|---|
| `Original/` | Zips como saíram do site. Os soltos aqui são os baixados primeiro (as 8 camadas `vw_cprm_go_*` e 11 nacionais com o Brasil inteiro), mais `GO_UF_2024.zip`, o limite de Goiás do IBGE usado no recorte. |
| `Original/Baixados do P3M - recorte Goiás/` | As demais 138 camadas do P3M com dados em Goiás, pedidas com o retângulo em volta do estado — trazem também as bordas dos estados vizinhos. LEIA-ME e índice próprios. |
| `Recortado pelo polígono de Goiás/` | As 156 camadas acima cortadas pelo limite estadual, em UTF-8 com `.cpg`. LEIA-ME e índice próprios. |

Observações:

- **Codificação dos originais**: os zips do SGB são UTF-8, mas isso só vem num `.cst`, que o QGIS não lê; ao abrir, escolha a codificação
  UTF-8 na camada (senão aparece "SÃ£o"). Os recortados já vêm com `.cpg` e abrem certos.
- **SIGEF Público original** (159 MB) passa do limite de 100 MB por arquivo do GitHub. Aqui ele está em duas partes baixadas do mesmo serviço,
  divididas pelo campo `id` (`id <= 556559` e `id > 556559`): 78.874 + 78.873 = 157.747 registros, exatamente o arquivo único.
- **Dados pessoais**: Processos Minerários, Minas Ativas e Guia de Utilização trazem, como o SGB publica, nomes de pessoas físicas titulares
  e, em alguns registros, o CPF junto do nome. Ao usar estes dados no painel ou em relatórios, siga a regra do projeto: pessoa física sem nome
  e CPF mascarado.
- Não estão aqui os mapas em imagem, PDFs e o projeto QGIS da pasta P3M local.
