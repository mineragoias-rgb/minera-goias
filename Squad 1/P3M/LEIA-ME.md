# P3M — camadas do Serviço Geológico do Brasil para Goiás

Camadas do **P3M** (https://p3mgeo.sgb.gov.br/#/map), o portal de dados geocientíficos do Serviço Geológico do Brasil (SGB), baixadas do
GeoServer que o próprio site usa (`https://opendata.sgb.gov.br/geoserver/wfs`, formato SHAPE-ZIP). Coletadas pelo Squad 1 (Estudante 1)
em outubro de 2026 e organizadas por tema em 22/10/2026.

## Como está organizado

```
Squad 1/P3M/
  inventario_p3m.csv                  uma linha por camada: tudo o que se sabe dela (ver abaixo)
  catalogo_p3m/                       retrato do catálogo do site P3M, usado para classificar e descrever as camadas
  Original/<pasta temática>/          zips como saíram do site
  Recortado pelo polígono de Goiás/<pasta temática>/   as mesmas camadas cortadas pelo limite de Goiás, em UTF-8 com .cpg
```

As pastas temáticas são as do Squad 1, encaixadas na classificação do próprio site (categoria → tema → subtema). A regra está no
cabeçalho de `scripts/build_inventario_p3m.py`.

| Pasta | Camadas | MB original | MB recortado | Maiores em Goiás |
|---|---:|---:|---:|---|
| `1- Geologia` | 29 | 65 | 55 | Afloramentos Geológicos, Afloramentos SIG, Estruturas SIG (Mapa Geológico Estadual Goiás (2008)), Litologia SIG (Mapa Geológico Estadual Goiás (2008)) |
| `2- Geofísica` | 4 | 1 | 3 | Levantamento Aerogeofísico 1000, Levantamento Aerogeofísico 3000, Levantamento Aerogeofísico 4000, Levantamento Aerogeofísico 2000 |
| `3- Geoquímica` | 10 | 9 | 3 | Geoquímica SIG (Mapa Geológico Estadual Goiás (2008)), Rocha (Amostras analisadas), Sedimento de Corrente, Geoquímica |
| `4- Recursos minerais` | 12 | 6 | 1 | Química Mineral, Ocorrências Minerais, Recursos Minerais SIG, Minerais Indicadores |
| `5- Atividade mineira` | 8 | 14 | 10 | Processos Minerários, Empreendimento Mineiro SIG, Minas Ativas, Guia de Utilização |
| `6- Cartografia` | 52 | 802 | 401 | Cobertura e Uso do Solo, SIGEF Público (Governança Fundiária), Rios - Trechos (Hidrografia), SIGEF Privado (Governança Fundiária) |
| `7- Pesquisa` | 12 | 75 | 37 | Levantamento Litoestratigráfico Escala 1:1.000.000, Levantamento Litoestratigráfico Escala 1:100.000, Levantamento Litoestratigráfico Escala 1:2.500.000, Levantamento Litoestratigráfico Escala 1:250.000 |
| `8- Infraestrutura` | 31 | 6 | 3 | Outras (Rodoviário), Estadual e Distrital, Federal (Rodoviário), Municipal (Rodoviário) |

## O inventário (`inventario_p3m.csv`)

Separador `;`, UTF-8. Uma linha por camada (158), com: pasta temática; categoria, tema e subtema do P3M (e outras classificações em
que o site também a põe); órgão de origem; geometria; extensão pedida ao site (Brasil inteiro, só Goiás, ou o retângulo em volta de
Goiás); registros no arquivo original e em Goiás; fiapos de divisa removidos no recorte; caminhos e tamanhos do original e do recortado;
URL do download e da ficha de metadados; resumo do site.

**Datas.** `data_download` é quando o Squad 1 baixou o arquivo (2026-10-07: 1, 2026-10-19: 19, 2026-10-21: 138).
`data_atualizacao_sgb` é a última atualização da camada no SGB, quando ele publica: só 16 das 158 têm essa data (pelo portal de
dados do SGB ou pelo metadado do próprio P3M; a coluna `fonte_data_sgb` diz qual). As demais o SGB não informa.

Para refazer depois de acrescentar ou trocar um zip: `python scripts/build_inventario_p3m.py` (com `--mover` ele também põe o zip na
pasta temática). `--verificar` confere sem gravar nada. Camada nova precisa ter a data de download e a extensão registradas no
inventário; o script avisa quando falta. `--atualizar-catalogo` baixa de novo o catálogo do site.

## Observações

- **Codificação dos originais**: os zips do SGB são UTF-8, mas isso só vem num `.cst`, que o QGIS não lê; ao abrir, escolha a codificação
  UTF-8 na camada (senão aparece "SÃ£o"). Os recortados já vêm com `.cpg` e abrem certos.
- **Retângulo de Goiás**: as camadas baixadas em 21/10/2026 foram pedidas com o retângulo lon −53,3 a −45,8, lat −19,6 a −12,3; trazem
  também as bordas de MT, MS, MG, BA, TO e DF. Para usar só Goiás, use a pasta Recortado.
- **SIGEF Público original** (159 MB) passa do limite de 100 MB por arquivo do GitHub: está em duas partes baixadas do mesmo serviço,
  divididas pelo campo `id` (`id <= 556559` e `id > 556559`), 78.874 + 78.873 = 157.747 registros.
- **Dados pessoais**: Processos Minerários, Minas Ativas e Guia de Utilização trazem, como o SGB publica, nomes de pessoas físicas titulares
  e, em alguns registros, o CPF junto do nome. Ao usar estes dados no painel ou em relatórios, siga a regra do projeto: pessoa física sem nome
  e CPF mascarado.
- **O que não foi baixado**: as 108 camadas estaduais de outras UFs (`vw_cprm_<uf>_*`), a geologia marinha e 11 camadas que só tinham feições
  fora de Goiás; SIGEF Total (é a soma de Público + Privado); e o que o site só oferece como imagem, sem dado vetorial — a geofísica
  (magnetometria, gamaespectrometria, Bouguer, gradiente), Grupamentos Mineiros, SNCI e Cadastro Nacional de Florestas Públicas.
- `Recursos Minerais SIG Lítio` não tem nenhum ponto em Goiás (os 46 ficam em Minas Gerais): está só em Original.
- Não estão aqui os mapas em imagem, PDFs e o projeto QGIS da pasta P3M local.
