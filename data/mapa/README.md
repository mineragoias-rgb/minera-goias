# Mapa Mineral de Goiás — dados

Dados da aba "Mapa Mineral de Goiás" (inspirada no P3M do SGB). Tudo aqui sai de `scripts/build_mapa_base.py`, que lê o catálogo
editável `scripts/mapa_camadas.json`. Nenhum número é digitado à mão. A pasta vai para a VPS (o `git archive` inclui `data/`); os zips do P3M
não vão (`Squad 1/P3M/.gitattributes` tem `export-ignore`). Por isso as camadas já saem prontas daqui.

Gerar de novo (precisa de `pyshp`, `shapely` >= 2 e `openpyxl`; leva uns 40 s). Na main, a etapa `mapa` de `scripts/atualizar_derivados.py`
(workflow `atualizar-derivados.yml`) refaz tudo sozinha quando o P3M, o inventário ou o gerador mudam, logo depois da etapa
`inventario_p3m`, com pyshp 3.1.6 e shapely 2.2.0 (outra versão do GEOS simplifica diferente):

    python scripts/build_mapa_base.py            # grava data/mapa/
    python scripts/build_mapa_base.py --checar   # só valida e mostra o resumo
    python -m unittest discover -s tests -p test_mapa.py -v
    node tests/mapa-dados.test.js

A saída não tem data de geração: as mesmas entradas gravam os mesmos bytes. O teste `GeradorTests` refaz tudo e compara com o que está aqui
(no CI ele é pulado, porque o job web não instala `pyshp`, `shapely` nem `openpyxl`).

## Arquivos e API

| Arquivo | Endpoint (sessão de leitor) | O que é |
|---|---|---|
| `catalogo.json` | `GET /api/mapa/catalogo` | Grupos, camadas e tabelas: origem, campos com rótulo PT/EN, tipo e unidade, datas, legenda, carga, filtros, tamanho e contagens |
| `camadas/<id>.json` | `GET /api/mapa/camadas/<id>` | Geometria quantizada e atributos em colunas (formato `mapa-v1`) |
| `tabelas/municipios.json` | `GET /api/mapa/tabelas/municipios` | Indicadores por município, cada medida com unidade, período e se pode ser somada entre municípios |
| `tabelas/radar_projetos.json` | `GET /api/mapa/tabelas/radar_projetos` | Os 1.040 projetos do Radar, com os processos da ANM que os ligam ao mapa |
| `tabelas/processos_complemento.json` | `GET /api/mapa/tabelas/processos_complemento` | Titular (só pessoa jurídica), municípios IBGE e mineral de cada processo do Atlas |
| `validacao.json` | — (não é servido) | Contagens, chaves, junções, divisa, simplificação e tamanhos de cada camada |

A API (`Squad 3/backend/mapa.py`) só entrega os ids que o catálogo publica. Sem sessão, responde 401; com id desconhecido, 404.
Camadas que já existem no Atlas **não são copiadas**: o catálogo aponta `processos` para `/api/atlas/processes`, e `municipios`,
`projetos_anm`, `ocorrencias` e `barragens` para `/api/atlas`.

No navegador, `public/mapa-dados.js` (`window.MapaDados`) lê o catálogo e busca cada camada só quando é pedida, com cache. A aba
"Mapa mineral" do painel (`public/mapa.js` e `public/mapa.css`) é quem usa esse carregador.
Todas as camadas viram o mesmo objeto: `{entrada, geometria, n, partes[i], valor(i, campo), atributos(i)}`. `partes[i]` é a lista de
pontos, linhas ou anéis da feição `i` em `[lat, lon]`. Os anéis de uma feição desenham-se juntos com `fillRule: 'evenodd'`. A camada de
processos sai de `loadProcesses()`, o mesmo cache da aba Atlas.

### Formato `mapa-v1`

O mesmo de `data/atlas/processes.json`, generalizado para pontos e linhas:

- `xy`: pares Uint16 little-endian em base64. `x` é a longitude e `y` a latitude invertida, na caixa `bounds` da camada:
  `lat = lat1 − y/65535 · (lat1 − lat0)` e `lon = lon0 + x/65535 · (lon1 − lon0)`, em graus.
  Numa camada do tamanho de Goiás (cerca de 7,3° de largura), o passo é de uns 12 m.
- `partStart` (Uint32): onde começa cada parte, mais o total. `partFeat` (Uint32): a que feição pertence cada parte. Uma parte é um ponto,
  uma linha ou um anel.
- `campos`, `valores[campo][i]`: o valor da feição `i`. Para os campos em `dic`, o valor (ou cada item, se for lista) é o índice em
  `dic[campo]`. `null` é ausência: nunca vira zero.

## Camadas (versão de 22/10/2026)

44 camadas: 39 do P3M e 5 reaproveitadas do Atlas. Os grupos do painel são as 8 pastas temáticas do Squad 1
(`Squad 1/P3M/<pasta>`, encaixadas na classificação do site P3M). O grupo de cada camada do P3M sai do inventário, pela pasta do seu
zip; as do Atlas ficam na pasta da camada equivalente do P3M. No painel vêm as camadas do P3M pasta por pasta, depois o Radar de
Projetos ("Levantamento da equipe") e por último as 5 reaproveitadas ("Também na aba Atlas e panorama"). Cada camada pode ser
baixada inteira como shapefile (.zip montado no navegador por `public/mapa-shp.js`).

As 39 camadas próprias somam 4,0 MB (1,9 MB na rede); as 5 do Atlas reaproveitam `atlas.json` (2,1 MB) e
`processes.json` (2,6 MB). A API manda esses arquivos em gzip quando o navegador aceita (`Squad 3/backend/compressed.py`): na rede,
`atlas.json` tem 520 KB e `processes.json`, 1,7 MB. A API também manda `no-store`, então cada abertura do painel baixa de novo. Por isso só
três camadas são de carga inicial: `limite_goias` (54 KB, 40 KB na rede), `minas_ativas` (172 KB, 94 KB na rede) e `municipios` (do
Atlas). O resto é sob demanda. A coluna Tamanho abaixo é a do arquivo, sem compressão.

O catálogo também diz, para cada camada, que campo responde a cada filtro da aba (`papeis`):
- `titulo`: o nome mostrado no painel de detalhes;
- `municipio`, `mineral`, `titular` e `id` (processo ou outro identificador): os filtros que valem para todas as camadas;
- `situacao` e `data`: os filtros que valem só para a camada em análise.

`@processo` quer dizer "pelo processo, na tabela `processos_complemento`". Uma camada sem o papel não é filtrada por ele, e a aba
diz isso. `ponto_ate_zoom` é uma dica de desenho: abaixo desse zoom, as áreas pequenas da ANM aparecem como ponto. A geometria
publicada não muda.

| Grupo (pasta) | Camada | Feições | Tamanho | Na divisa | Baixada em | Atualização no SGB |
|---|---|---:|---:|---:|---|---|
| 1 · Geologia | `estruturas` | 7.065 | 342 KB | 59 | 19/10/2026 | não publica |
| 1 · Geologia | `provincias_estruturais` | 3 | 40 KB | 3 | 21/10/2026 | não publica |
| 1 · Geologia | `pocos_siagas` | 6.133 | 456 KB | — | 21/10/2026 | não publica |
| 2 · Geofísica | `levantamentos_aerogeofisicos` | 39 | 58 KB | 35 | 19/10/2026 | não publica |
| 3 · Geoquímica | `amostras_geoquimicas` | 3.980 (de 9.867 registros) | 348 KB | — | 21/10/2026 | 02/10/2026 (portal de dados do SGB) |
| 4 · Recursos minerais | `depositos_pdac` | 34 | 8 KB | — | 19/10/2026 | não publica |
| 4 · Recursos minerais | `uranio` | 18 | 2 KB | — | 19/10/2026 | não publica |
| 4 · Recursos minerais | `potencial_mineral` | 146 | 81 KB | 16 | 19/10/2026 | não publica |
| 4 · Recursos minerais | `distritos_auriferos` | 14 | 6 KB | 0 | 19/10/2026 | não publica |
| 4 · Recursos minerais | `provincias_auriferas` | 4 | 1 KB | 0 | 21/10/2026 | não publica |
| 4 · Recursos minerais | `ocorrencias_diamante` | 114 | 7 KB | — | 21/10/2026 | não publica |
| 4 · Recursos minerais | `recursos_minerais_go` | 1.673 | 200 KB | — | 19/10/2026 | não publica |
| 5 · Atividade mineira | `minas_ativas` | 689 (de 743 registros) | 172 KB | 77 | 21/10/2026 | 19/10/2026 (catálogo do P3M) |
| 5 · Atividade mineira | `guias_utilizacao` | 445 (de 646 registros) | 191 KB | 34 | 21/10/2026 | 19/10/2026 (catálogo do P3M) |
| 5 · Atividade mineira | `servidoes` | 200 | 36 KB | 3 | 21/10/2026 | não publica |
| 5 · Atividade mineira | `reservas_garimpeiras` | 2 | 1 KB | 0 | 21/10/2026 | 05/01/2024 (catálogo do P3M) |
| 5 · Atividade mineira | `ativos_sgb` | 8 | 2 KB | 0 | 21/10/2026 | 15/04/2026 (catálogo do P3M) |
| 5 · Atividade mineira | `empreendimentos_sig` | 1.374 | 130 KB | — | 19/10/2026 | não publica |
| 6 · Cartografia: território e áreas especiais | `limite_goias` | 1 | 54 KB | 1 | 21/10/2026 | não publica |
| 6 · Cartografia: território e áreas especiais | `uc_protecao_integral` | 25 | 19 KB | 4 | 21/10/2026 | não publica |
| 6 · Cartografia: território e áreas especiais | `uc_uso_sustentavel` | 137 | 68 KB | 10 | 21/10/2026 | não publica |
| 6 · Cartografia: território e áreas especiais | `terras_indigenas` | 6 | 3 KB | 0 | 21/10/2026 | não publica |
| 6 · Cartografia: território e áreas especiais | `quilombolas` | 8 | 5 KB | 2 | 21/10/2026 | não publica |
| 6 · Cartografia: território e áreas especiais | `assentamentos` | 401 | 140 KB | 25 | 21/10/2026 | não publica |
| 6 · Cartografia: território e áreas especiais | `cavidades` | 1.051 | 84 KB | — | 21/10/2026 | não publica |
| 6 · Cartografia: território e áreas especiais | `sitios_arqueologicos` | 925 | 62 KB | — | 21/10/2026 | não publica |
| 6 · Cartografia: território e áreas especiais | `biomas` | 2 | 27 KB | 2 | 21/10/2026 | não publica |
| 7 · Pesquisa: levantamentos e mapeamentos | `litoestratigrafia` | 4.124 | 1,1 MB | 177 | 21/10/2026 | não publica |
| 7 · Pesquisa: levantamentos e mapeamentos | `mapeamentos_geologicos` | 106 | 99 KB | 30 | 21/10/2026 | não publica |
| 8 · Infraestrutura: energia e transporte | `linhas_transmissao` | 112 | 21 KB | 58 | 21/10/2026 | não publica |
| 8 · Infraestrutura: energia e transporte | `subestacoes` | 35 | 3 KB | — | 21/10/2026 | não publica |
| 8 · Infraestrutura: energia e transporte | `hidreletricas` | 42 | 6 KB | — | 21/10/2026 | não publica |
| 8 · Infraestrutura: energia e transporte | `termeletricas` | 27 | 4 KB | — | 21/10/2026 | não publica |
| 8 · Infraestrutura: energia e transporte | `ferrovias` | 42 | 10 KB | 6 | 21/10/2026 | não publica |
| 8 · Infraestrutura: energia e transporte | `terminais_ferroviarios` | 10 | 1 KB | — | 21/10/2026 | não publica |
| 8 · Infraestrutura: energia e transporte | `rodovias_federais` | 629 | 40 KB | 19 | 21/10/2026 | não publica |
| 8 · Infraestrutura: energia e transporte | `rodovias_estaduais` | 1.949 | 146 KB | 44 | 21/10/2026 | não publica |
| 8 · Infraestrutura: energia e transporte | `aeroportos` | 45 | 3 KB | — | 21/10/2026 | não publica |
| 8 · Infraestrutura: energia e transporte | `usinas_etanol` | 48 | 4 KB | — | 21/10/2026 | não publica |

| Grupo (pasta) | Camada reaproveitada do Atlas | Feições | Arquivo | Retrato |
|---|---|---:|---|---|
| 6 · Cartografia: território e áreas especiais | `municipios` | 246 | `atlas.json` | 10/09/2026 |
| 5 · Atividade mineira | `processos` | 16.656 | `processes.json` | 10/09/2026 |
| 5 · Atividade mineira | `barragens` | 23 | `atlas.json` | não registrado |
| 5 · Atividade mineira | `projetos_anm` | 3.377 | `atlas.json` | 10/09/2026 |
| 4 · Recursos minerais | `ocorrencias` | 1.796 | `atlas.json` | 12/09/2026 |

"Baixada em" é o retrato da camada (`data_retrato` no catálogo): o dia em que o Squad 1 baixou o zip, tirado da coluna `data_download`
do inventário. "Atualização no SGB" é a última atualização que o próprio SGB publica para a camada (portal de dados do SGB ou metadado
do catálogo do P3M); para a maioria, ele não publica. O período a que o dado se refere (`periodo_referencia`) é
outra coisa e, na maioria das camadas do P3M, a fonte não informa: fica `null`. Toda camada é um retrato (`temporalidade: "retrato"`).
Escolher um ano anterior no mapa não a transforma em histórico. Séries anuais só existem na tabela `municipios`.

## Inventário do P3M e o que ficou de fora

O mapa lê `Squad 1/P3M/inventario_p3m.csv` (gerado por `scripts/build_inventario_p3m.py`): de cada zip, a data de download (o retrato),
a data de atualização no SGB quando ele publica, a pasta temática (o grupo do painel), a classificação no site P3M (categoria › tema ›
subtema e as outras classificações), o órgão, o resumo do site e o link da ficha de metadados. O catálogo publica isso em `p3m` de cada
camada, e o painel "i" da aba mostra. O link do inventário no GitHub (`p3m.inventario.url`) aparece no painel "i", na linha de fontes do
mapa, no CSV, no GeoJSON, no LEIAME do shapefile e na seção Fontes da página inicial.

Das 158 camadas do inventário, 53 estão no mapa (algumas camadas do mapa juntam várias do P3M: hidrelétricas, termelétricas,
aeroportos, levantamentos aerogeofísicos, amostras geoquímicas e mapeamentos geológicos). Entraram em 22/10/2026, por serem úteis para
mineração e energia em Goiás e leves: poços do SIAGAS (sem proprietário, perfurador e endereço), levantamentos aerogeofísicos (área
coberta), amostras geoquímicas do SGB (sedimento de corrente, solo, rocha e concentrado de bateia, uma feição por amostra), recursos
minerais do mapa geológico estadual (SIG, 2008), mapeamentos geológicos (índice das folhas, com link para o relatório no RIGEO) e usinas
de etanol da EPE. Potencial mineral e PDAC já estavam no mapa.

As outras 105 ficaram de fora:

- **Já estão no mapa por outra fonte, repetem outra camada ou não têm nada em Goiás** (8): Limite estadual de Goiás (IBGE, malha 2024) (limite usado para recortar; o mapa desenha a Malha Estadual do P3M); Processos Minerários (o mapa usa os processos do SIGMINE pelo Atlas; o zip traz nome e CPF de pessoa física); Barragens de Mineração (o mapa usa as barragens do Atlas (SIGBM); a do P3M traz os campos de risco vazios); Ocorrências Minerais (mesmas 1.796 ocorrências do RECMIN que o mapa usa pelo Atlas); Malha Municipal (o mapa usa a malha municipal do Atlas); Projetos de Assentamento Federal e Projetos de Assentamento Reconhecimento (os 398 e o 1 projeto já estão, pelo código SIPRA, na camada de assentamentos do INCRA que o mapa usa); Recursos Minerais SIG Lítio (nenhum ponto em Goiás).
- **Pesadas demais para o mapa na web (os zips continuam no repositório)** (13): Litologia SIG (27,5 MB); Cobertura e Uso do Solo (19,5 MB, 342.763 polígonos); Rios - Trechos (19,2 MB, 53.142 trechos); SIGEF Público (85,6 MB); SIGEF Privado (4,7 MB, 15.449 imóveis); Base Contínua de Vegetação do Brasil (18,5 MB); Afloramentos Geológicos (36.124 pontos); Afloramentos SIG (32.557 pontos); Polígono Atlas Hidrogeológico (6,2 MB); Contato Atlas Hidrogeológico (2,5 MB); Levantamento Litoestratigráfico Escala 1:100.000 (7,2 MB; o mapa traz a 1:1.000.000); Levantamento Litoestratigráfico Escala 1:2.500.000 (8,0 MB; o mapa traz a 1:1.000.000); Geoquímica SIG (26.979 pontos com teores de cerca de 30 elementos, sem unidade nem método no arquivo; o mapa traz as amostras do SGB com método e laboratório).
- **Divisões territoriais, hidrografia e estatísticas do IBGE (Goiás inteiro ou dado municipal que o site já tem)** (33): Amazônia Legal; Faixa de Fronteira; MATOPIBA; Semiárido; Área de Atuação da SUDENE; Região Geográfica Imediata; Região Geográfica Intermediária; Mesorregião Geográfica; Microrregião Geográfica; Regiões; Com 100 mil a 300 mil Habitantes; Com Mais de 300 mil Habitantes; Produto Interno Bruto; Desenvolvimento Humano (IDH); Gini; Densidade Populacional; rendimento nominal médio Mensal, dos Domicílios Particulares Permanentes, das Pessoas Maiores de 10 Anos e das Com Rendimento no Trabalho Principal; Bacias Hidrográficas - Nível 1; Bacias Hidrográficas - Nível 2; Bacias Hidrográficas - Nível 3; Bacias Hidrográficas - Nível 4; Bacias Hidrográficas - Nível 5; Bacias Hidrográficas - Nível 6; Macrorregiões Hidrográficas; Mesorregiões Hidrográficas; Microrregiões Hidrográficas; Rios - Massa D'água; Zonas Climáticas; Ilhas; Solos.
- **Pouco ligadas a mineração e energia em Goiás, ou com quase nada no estado** (20): Furos de sondagem (3 furos (10 trechos), todos de um estudo hidrogeológico da Bacia do Urucuia); Rimas (6 poços); Limite das Bacias Sedimentares, Blocos Exploratórios (1) e Poços (4) da ANP; Biodiesel (9 usinas, outro formato de campos); Biogás (2 usinas); Base de Combustíveis Líquidos; Base de Gás Liquefeito de Petróleo; Terminal de Armazenamento e Distribuição de Petróleo e Derivados; Oleodutos; Terminais Portuários; Portos; Hidrovias Vias Economicamente Navegáveis - VEN; Helipontos; Pista de Pouso; Barragens do IBGE (3); rodovias Municipal e Outras do IBGE; Aldeias Indígenas.
- **Geologia de escala continental ou de nicho** (31): Geology SIG; Plate SIG; Fauts SIG; Kimberlite Clusters SIG; Tec Units SIG; Tectonic Units Inset SIG; Suture Zones SIG; Suture Zones Inset; Craton Terranes Limits SIG; Craton Terranes Limits Inset SIG; Continent Structure SIG; Continent Structure Inset SIG; Isopachs SIG; Cenozoic Inset SIG; Kimberlites SIG; Afloramentos de Kimberlito; Minerais Indicadores; Química Mineral; Geocronologia; Petrografia; Petrografia SIG; Ocorrências Fossilíferas; Geoquímica de Baixa Densidade; Mineralometria; Contagem de Pintas Au; Outros (geoquímica); Geoquímica (as mesmas amostras com teores, com coordenada em texto); Folhas 1:100.000; Mapa Índice dos Mapas Geológicos Estaduais; Modelamento 3d; Levantamento Litoestratigráfico Escala 1:250.000.

## O que o gerador faz

0. **Inventário.** Cada zip é procurado no inventário do P3M pelo nome. Sem linha ou sem data de download, a camada não é gravada.
   O grupo da camada é a pasta temática do zip, e todos os zips de uma camada têm de estar na mesma pasta.
1. **Território.** Usa os zips de `Squad 1/P3M/Recortado pelo polígono de Goiás`, já cortados pelo limite estadual do IBGE (`GO_UF_2024`).
   - Pontos ficam se estão dentro ou na divisa.
   - Linhas e polígonos que cruzam a divisa foram cortados no limite e mantêm os atributos da feição inteira. Área, extensão,
     potência e contagens **não são rateadas** pela parte em Goiás.
   - Cada linha ou polígono ganha `na_divisa`: encosta no limite estadual (a menos de cerca de 1 m) e pode ter sido cortado.
   - O processo da ANM continua com o polígono inteiro, como no Atlas.
2. **Conferência de entrada.**
   - O `.prj` tem de ser SIRGAS 2000 geográfico (EPSG:4674).
   - A extensão tem de cair na caixa de Goiás. Latitude e longitude trocadas são detectadas.
   - Cada ponto tem de estar a menos de 0,01° do polígono do estado.
   - O número de registros tem de bater com `_indice_recorte.csv`.
   - O campo pedido no catálogo tem de existir na fonte.
   - Qualquer falha impede a gravação.
3. **Grão e chave.** Cada camada declara a chave, e a validação conta chaves distintas e repetidas.
   - **Minas Ativas:** o SGB repete o polígono uma vez por substância. O gerador junta por processo: 743 registros viram 689 processos,
     com a lista de substâncias e `n_registros_fonte`.
   - **Guias de utilização:** juntadas por processo (646 guias em 445 processos), com número, substância, quantidade e prazo de cada guia
     em listas alinhadas.
   - **Hidrelétricas e termelétricas:** juntam vários arquivos da EPE e usam o código CEG como chave, porque o `gid` se repete entre eles.
   - **Amostras geoquímicas:** o SGB repete a amostra uma vez por análise (método ou lote). O gerador junta pelo número de campo:
     9.867 análises viram 3.980 amostras, com datas, laboratórios e métodos em listas.
   - **Chave de processo:** normalizada como número sem zeros à esquerda e ano (`860.337/2020` → `860337/2020`), a mesma dos arquivos do Atlas.
4. **Atributos.**
   - Só os campos listados no catálogo, com rótulo PT/EN, tipo e unidade.
   - Os campos deixados de fora ficam em `omitidos`, com o motivo.
   - Marcadores de ausência (`Not Available`, `Não informado`, `-`, `0` em `ano_opera`…) viram `null`.
   - Datas viram AAAA-MM-DD.
   - A potência das usinas sai em MW: potência_MW = potência da fonte (kW) ÷ 1.000. A unidade foi conferida com Serra da Mesa:
     1.275.000 kW = 1.275 MW.
   - Quantidade autorizada de guia, produção declarada do levantamento e recurso declarado do PDAC ficam como **texto da fonte**: têm
     unidades misturadas e não são somáveis.
5. **Municípios em texto.** Camadas que só trazem o nome do município ganham o campo `municipios_ibge`, com os códigos do IBGE.
   - O nome é casado com a malha sem acento e sem a UF. Nome de outra UF não é casado com Goiás.
   - Grafias da fonte que não são o nome do IBGE estão listadas em `apelidos_municipios`, no catálogo editável. Hoje são quatro,
     como "SAO LUIZ DE MONTES BELOS" e "PIRACAMJUBA". Não há aproximação automática de nomes.
   - O que sobra sem código está em `validacao.json` (`municipio_sem_codigo`): Unaí, Buritis, Ponte Branca, "Distrito Federal" e
     "Brasília" (2 recursos minerais do SIG), todos fora de Goiás. No SIAGAS, 6 poços têm a coordenada no recorte de Goiás e o
     município de outro estado (4 São Desidério, 1 Jaborandi, 1 Goianésia do Pará): ficam sem código, como vieram.
6. **Mineral.** As substâncias passam pela aba `01b_crosswalk_pente_fino` da base consolidada v17: grafia da ANM → categoria da ANM.
   - Grafia com mais de uma categoria fica sem mineral.
   - Um campo pode ter `apelidos` no catálogo, lidos antes do crosswalk. Nos recursos minerais do SIG estadual, a substância vem como
     símbolo químico (Au, Mn, Sn…) ou com grafia própria (Brita, Água Termal): com os apelidos, 1.625 dos 1.673 registros ganham categoria.
   - O que não casou fica contado em `validacao.json` (`mineral_sem_categoria`). Nas guias, são substâncias em texto livre, como
     "AREIA (agregado)".
7. **Titular.**
   - Pelo processo, com o Cadastro Mineiro e o SIGMINE, pela regra do Radar de Projetos (`titular_por_processo` e `titular_publico`).
   - Nome sem marca de empresa vira "Titular individual (nome não publicado)", e o mesmo vale para nome com CPF.
   - `nm_pessoa`, `cpf_cnpj`, endereço e telefone nunca entram. No SIAGAS, proprietário, perfurador e local do poço também não.
   - Nos 16.656 processos do Atlas: 10.725 titulares pessoa jurídica e 5.931 sem nome.
   - Antes de aplicar a regra, o texto é reparado quando a fonte gravou UTF-8 lido como Latin-1 (`reparar_codificacao`, 953
     processos). Exemplo: "INÃ¡CIA", em que o "CIA" isolado fazia nome de pessoa passar por empresa. O mesmo reparo vale para todo
     texto lido das camadas do P3M, e `tests/test_mapa.py` barra qualquer texto estragado nos dados publicados.
8. **Simplificação.**
   - Douglas-Peucker preservando topologia, com tolerância por camada no catálogo: 0,0002° (~22 m) nas áreas da ANM, 0,0005° nas áreas
     protegidas, nas rodovias e nas linhas de transmissão, e 0,002° (~220 m) na litoestratigrafia 1:1.000.000. Esta última fica abaixo
     da precisão gráfica da escala, que é de 250 m.
   - Depois vem a quantização.
   - O polígono detalhado e o identificador original ficam no zip de origem.
   - As contagens de vértices antes e depois estão em `validacao.json`.

## Tabelas

- **`municipios`** (246 linhas, código IBGE). Uma medida não se soma com outra.
  - `cfem_recolhida`: R$ correntes por ano, 2022–2026, como no Atlas. É o valor recolhido e atribuído ao município de origem, não a CFEM
    distribuída.
    - 2026 vai de janeiro a agosto e está marcado em `periodo_incompleto`. O período padrão é 2025, o último ano completo.
    - 0 = nenhum recolhimento no arquivo.
  - `processos_que_tocam`: processos distintos que tocam o município, do Atlas.
  - `minas_ativas_que_tocam`: processos distintos, pelo código de município da camada.
    - Nas duas medidas "que tocam", um processo em vários municípios conta em cada um, e o catálogo marca
      `aditiva_entre_municipios: false`.
  - `radar_projetos`: projetos por maturidade, cada um contado só no município principal. A soma dá os 1.039 projetos com município.
  - `projetos_anm` e `ocorrencias`: contagens dos pontos do Atlas.
- **`radar_projetos`.** O Radar não tem coordenadas, e nenhum projeto ganha ponto em centroide.
  - 1.027 projetos se ligam ao mapa pelos polígonos dos seus processos (`ligacao: "processos"`).
  - 12 projetos ficam só no nível do município.
  - 1 não tem processo nem município.
  - Dos 5.434 processos citados, 7 não estão na camada de processos: o grupamento 960.658/1987 e seis processos que não estão no
    arquivo do SIGMINE de 10/09/2026.
- **`processos_complemento`.** Na mesma ordem de `/api/atlas/processes`.
  - Titular: só pessoa jurídica, como antes.
  - Municípios e mineral vêm da aba `03_dim_operacoes` da base consolidada v17 (`municipios_intersectados` e `mineral_ids`). É a junção
    espacial do polígono com a malha do IBGE 2025 em resolução total, a mesma base das contagens do Atlas.
    - Por isso o filtro por município, o perfil do município e a aba Atlas contam os mesmos processos, como confere um teste.
    - Todos os 16.656 processos têm município. O processo que cruza a divisa leva só os municípios de Goiás que toca.
  - Os 381 processos com substância "DADO NÃO CADASTRADO" no SIGMINE ficam sem mineral.
  - Nenhum processo tem mais de um mineral nesta base.

## Limitações

- **Produção por mina ou por município:** não existe nas fontes. O AMB é estadual, e a quantidade da CFEM não é produção. O mapa não
  mostra produção. Também não há dado de CFEM distribuída.
- **Mineral crítico ou estratégico:** o mapa não classifica minerais assim. Nenhuma taxonomia documentada existe no repositório: a
  `01_dim_minerais` não tem esse campo, e a lista usada nos portfólios do Radar é um recorte do próprio gerador.
- **Geofísica:** os dados (magnetometria, gamaespectrometria) o P3M só oferece como imagem; o mapa mostra a área coberta pelos
  levantamentos aerogeofísicos.
- **Camadas do P3M fora do mapa:** a lista, com o motivo, está em "Inventário do P3M e o que ficou de fora". Os zips continuam no repositório.
- **Amostras geoquímicas:** o arquivo do P3M corta os teores em 254 caracteres; o mapa mostra onde há amostra e por que método, não o teor.
- **`empreendimentos_sig`** é um levantamento antigo do SGB.
  - 852 dos 1.374 pontos são o centro das áreas requeridas ao DNPM, como diz a própria fonte. Cada um está marcado em `posicionamento`,
    e o total está em `n_posicao_aproximada`.
  - A situação ("em atividade"…) é a da época do levantamento.
  - 10 números de processo vêm truncados na fonte e ficam sem chave.
- **Barragens:** são as do Atlas (SIGBM, retrato anterior), sem data de extração. A camada de barragens do P3M foi descartada porque
  traz os campos de risco vazios.
- **Cavidades:** a camada não traz o grau de relevância.
- **Sítios arqueológicos:** os acentos já vêm perdidos na fonte.
- **Assentamentos:** a fase é um código do INCRA sem legenda na camada.
