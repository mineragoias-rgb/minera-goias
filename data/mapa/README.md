# Mapa Mineral de Goiás — dados

Dados da aba "Mapa Mineral de Goiás" (inspirada no P3M do SGB). Tudo aqui sai de `scripts/build_mapa_base.py`, que lê o catálogo
editável `scripts/mapa_camadas.json`. Nenhum número é digitado à mão. A pasta vai para a VPS (o `git archive` inclui `data/`); os zips do P3M
não vão (`Squad 1/P3M/.gitattributes` tem `export-ignore`). Por isso as camadas já saem prontas daqui.

Gerar de novo (precisa de `pyshp`, `shapely` >= 2 e `openpyxl`; leva uns 15 s):

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

## Camadas (versão de 21/10/2026)

38 camadas em 7 grupos, na ordem do painel. As 33 próprias somam 2,8 MB; as 5 do Atlas reaproveitam `atlas.json` (2,1 MB) e
`processes.json` (2,6 MB). O nginx não comprime e a API manda `no-store`. Por isso só três camadas são de carga inicial:
`limite_goias` (54 KB), `minas_ativas` (172 KB) e `municipios` (do Atlas). O resto é sob demanda.

O catálogo também diz, para cada camada, que campo responde a cada filtro da aba (`papeis`):
- `titulo`: o nome mostrado no painel de detalhes;
- `municipio`, `mineral`, `titular` e `id` (processo ou outro identificador): os filtros que valem para todas as camadas;
- `situacao` e `data`: os filtros que valem só para a camada em análise.

`@processo` quer dizer "pelo processo, na tabela `processos_complemento`". Uma camada sem o papel não é filtrada por ele, e a aba
diz isso. `ponto_ate_zoom` é uma dica de desenho: abaixo desse zoom, as áreas pequenas da ANM aparecem como ponto. A geometria
publicada não muda.

| Grupo | Camada | Origem | Geometria | Feições | Tamanho | Na divisa | Retrato |
|---|---|---|---|---:|---:|---:|---|
| Base territorial | `limite_goias` | P3M | polígono | 1 | 54 KB | — | 21/10/2026 |
| Base territorial | `municipios` | Atlas | polígono | 246 | (atlas.json) | — | 10/09/2026 |
| Mineração · direitos (ANM) | `processos` | Atlas | polígono | 16.656 | 2,6 MB | — | 10/09/2026 |
| Mineração · direitos (ANM) | `minas_ativas` | P3M | polígono | 689 (de 743 registros) | 172 KB | 77 | 21/10/2026 |
| Mineração · direitos (ANM) | `guias_utilizacao` | P3M | polígono | 445 (de 646 guias) | 191 KB | 34 | 21/10/2026 |
| Mineração · direitos (ANM) | `servidoes` | P3M | polígono | 200 | 36 KB | 3 | 21/10/2026 |
| Mineração · direitos (ANM) | `reservas_garimpeiras` | P3M | polígono | 2 | 1 KB | 0 | 21/10/2026 |
| Mineração · direitos (ANM) | `barragens` | Atlas | ponto | 23 | (atlas.json) | — | não registrado |
| Mineração · direitos (ANM) | `ativos_sgb` | P3M | polígono | 8 | 2 KB | 0 | 21/10/2026 |
| Mineração · projetos | `projetos_anm` | Atlas | ponto | 3.377 | (atlas.json) | — | 10/09/2026 |
| Mineração · projetos | `empreendimentos_sig` | P3M | ponto | 1.374 | 130 KB | — | out/2026 |
| Mineração · ocorrências | `ocorrencias` | Atlas | ponto | 1.796 | (atlas.json) | — | 12/09/2026 |
| Mineração · ocorrências | `depositos_pdac` | P3M | ponto | 34 | 8 KB | — | out/2026 |
| Mineração · ocorrências | `uranio` | P3M | ponto | 18 | 2 KB | — | out/2026 |
| Mineração · ocorrências | `potencial_mineral` | P3M | polígono | 146 | 81 KB | 16 | out/2026 |
| Mineração · ocorrências | `distritos_auriferos` | P3M | polígono | 14 | 6 KB | 0 | out/2026 |
| Mineração · ocorrências | `provincias_auriferas` | P3M | polígono | 4 | 1 KB | 0 | 21/10/2026 |
| Mineração · ocorrências | `ocorrencias_diamante` | P3M | ponto | 114 | 7 KB | — | 21/10/2026 |
| Geociências | `litoestratigrafia` | P3M | polígono | 4.124 | 1,1 MB | 177 | 21/10/2026 |
| Geociências | `estruturas` | P3M | linha | 7.065 | 342 KB | 59 | out/2026 |
| Geociências | `provincias_estruturais` | P3M | polígono | 3 | 40 KB | 3 | 21/10/2026 |
| Infraestrutura | `linhas_transmissao` | P3M | linha | 112 | 21 KB | 58 | 21/10/2026 |
| Infraestrutura | `subestacoes` | P3M | ponto | 35 | 3 KB | — | 21/10/2026 |
| Infraestrutura | `hidreletricas` (UHE, PCH, CGH) | P3M | ponto | 42 | 6 KB | — | 21/10/2026 |
| Infraestrutura | `termeletricas` | P3M | ponto | 27 | 4 KB | — | 21/10/2026 |
| Infraestrutura | `ferrovias` | P3M | linha | 42 | 10 KB | 6 | 21/10/2026 |
| Infraestrutura | `terminais_ferroviarios` | P3M | ponto | 10 | 1 KB | — | 21/10/2026 |
| Infraestrutura | `rodovias_federais` | P3M | linha | 629 | 40 KB | 19 | 21/10/2026 |
| Infraestrutura | `rodovias_estaduais` | P3M | linha | 1.949 | 146 KB | 44 | 21/10/2026 |
| Infraestrutura | `aeroportos` (e aeródromos) | P3M | ponto | 45 | 3 KB | — | 21/10/2026 |
| Contexto socioambiental | `uc_protecao_integral` | P3M | polígono | 25 | 19 KB | 4 | 21/10/2026 |
| Contexto socioambiental | `uc_uso_sustentavel` | P3M | polígono | 137 | 68 KB | 10 | 21/10/2026 |
| Contexto socioambiental | `terras_indigenas` | P3M | polígono | 6 | 3 KB | 0 | 21/10/2026 |
| Contexto socioambiental | `quilombolas` | P3M | polígono | 8 | 5 KB | 2 | 21/10/2026 |
| Contexto socioambiental | `assentamentos` | P3M | polígono | 401 | 140 KB | 25 | 21/10/2026 |
| Contexto socioambiental | `cavidades` | P3M | ponto | 1.051 | 84 KB | — | 21/10/2026 |
| Contexto socioambiental | `sitios_arqueologicos` | P3M | ponto | 925 | 62 KB | — | 21/10/2026 |
| Contexto socioambiental | `biomas` | P3M | polígono | 2 | 27 KB | 2 | 21/10/2026 |

"Retrato" é o dia em que o arquivo foi baixado (`data_retrato` no catálogo). O período a que o dado se refere (`periodo_referencia`) é
outra coisa e, na maioria das camadas do P3M, a fonte não informa: fica `null`. Toda camada é um retrato (`temporalidade: "retrato"`).
Escolher um ano anterior no mapa não a transforma em histórico. Séries anuais só existem na tabela `municipios`.

## O que o gerador faz

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
   - O que sobra sem código está em `validacao.json` (`municipio_sem_codigo`): Unaí, Buritis, Ponte Branca e "Distrito Federal",
     todos fora de Goiás.
6. **Mineral.** As substâncias passam pela aba `01b_crosswalk_pente_fino` da base consolidada v17: grafia da ANM → categoria da ANM.
   - Grafia com mais de uma categoria fica sem mineral.
   - O que não casou fica contado em `validacao.json` (`mineral_sem_categoria`). Nas guias, são substâncias em texto livre, como
     "AREIA (agregado)".
7. **Titular.**
   - Pelo processo, com o Cadastro Mineiro e o SIGMINE, pela regra do Radar de Projetos (`titular_por_processo` e `titular_publico`).
   - Nome sem marca de empresa vira "Titular individual (nome não publicado)", e o mesmo vale para nome com CPF.
   - `nm_pessoa`, `cpf_cnpj`, endereço e telefone nunca entram.
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
- **Geofísica:** o P3M só a oferece como imagem.
- **Volume:** SIGEF (125 MB), cobertura do solo, rios e afloramentos ficaram de fora pelo tamanho. Os zips continuam no repositório.
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
