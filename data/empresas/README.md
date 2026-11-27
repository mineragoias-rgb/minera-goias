# Empresas: produção, energia e coeficiente

Cruza o que cada empresa **declarou produzir** com a **carga de energia** que ela puxou da CCEE em Goiás, e divide uma pela outra. Serve a aba
`Empresas` do painel, em `/api/empresas`.

| Arquivo | Conteúdo |
|---|---|
| `empresas.json` | `meta` (fontes, chave de ligação, avisos) e `linhas` — uma por empresa, mineral e ano |

Gerado por `python scripts/build_empresas_base.py`. Conferido por `tests/test_empresas.py`.

## A ligação entre as duas bases

**CNPJ raiz, não nome.** A tabela `ccee` do panorama já traz o CNPJ raiz do agente; a base de produção traz o do titular. Nove das dez empresas
casam. A CBA fica de fora: sua unidade de bauxita em Barro Alto não aparece com carga própria sob o CNPJ raiz da companhia na base do estado.

Cada empresa declara, na curadoria, **quais minerais estão por trás da sua carga** (`minerais_na_carga_ccee`). É isso que decide se o
coeficiente é exclusivo daquele mineral ou não — e não uma inferência do código.

## Anualização: o que é medido e o que é estimado

Nenhum dos dois lados cobre doze meses de todos os anos, então cada linha traz **o observado e o anualizado**, lado a lado, nunca um por cima do
outro.

**Energia.** A CCEE versionada no repositório cobre abr.–dez. de 2024 (a CCEE não publica o conjunto antes de abril de 2024), jan.–dez. de
2025 e jan.–jul. de 2026. O anualizado é `observado ÷ meses observados × 12`. Em 2025 a carga é observada nos doze meses e não há estimativa;
em 2024 são oito ou nove meses por empresa e em 2026 sete, e a linha sai marcada com a qualidade da estimativa, que aparece no painel.

**Produção.** Quando a empresa publicou o ano, é o ano. Quando só há trimestres ou semestres, o anualizado é
`soma dos períodos ÷ meses cobertos × 12`. Períodos que se sobrepõem **nunca somam** — um S1 já contém Q1 e Q2 —, e linha de planta isolada
(`nivel='operacao'`, como Barro Alto e Codemin separados) fica fora, para não duplicar a linha da empresa.

| Qualidade | Quando |
|---|---|
| `observado_completo` | doze meses observados |
| `estimado_alto` | nove a onze meses |
| `estimado_medio` | seis a oito meses |
| `estimado_baixo` | menos de seis meses |

O coeficiente herda **a qualidade do lado mais fraco**: energia estimada de quatro meses não vira número confiável só porque a produção do ano
foi publicada.

## O coeficiente

`energia anualizada (kWh) ÷ produção anualizada`, **na unidade em que a empresa publica** — kWh/t ou kWh/oz. Nada é convertido: onça não vira
quilo para o gráfico ficar bonito, e os dois grupos aparecem em blocos separados no painel justamente porque não se comparam.

Só entra produção **realizada**, do recorte **de Goiás**, no **nível da empresa** e com medida de produção. Embarque, venda, capacidade, meta e
consolidado do Brasil ficam fora do numerador.

**Quando a empresa move mais de um mineral, a carga é separada pelo que a própria CCEE declara** — nunca por proporção arbitrada. A curadoria
guarda a regra em `rateio_ccee`:

| Critério | Quando | Caso |
|---|---|---|
| `unico` | A empresa tem um mineral só em Goiás | Anglo American, SAMA, Serra Grande, Mara Rosa, Mosaic, Serra Verde, Brasil Minérios |
| `ramo` | A CCEE declara a carga em ramos de atividade distintos, e cada ramo pertence a um mineral | **CMOC** |
| `municipio` / `ramo_municipio` | Cada operação está em município diferente | nenhum caso hoje |
| `nao_separavel` | Nem município nem ramo separam | **Chapada** |

A CMOC é o caso em que isso muda o número. A carga dela vem em três ramos: **extração de minerais metálicos** (mina de nióbio, Catalão e
Ouvidor) e **metalurgia** (planta de ferronióbio, Ouvidor) são o nióbio; **minerais não-metálicos** (Ouvidor) é o fosfato. Como nióbio é
substância metálica e fosfato não é, o ramo separa os dois negócios sem inventar rateio. Em 2025 o nióbio ficou com 42% da carga — 122.022 MWh
dos 293.016 MWh da empresa —, e o coeficiente caiu de 28.316 para **11.792 kWh/t**, que é a ordem de grandeza do ferronióbio.

Um teste guarda o invariante que isso exige: **as regras têm de particionar a carga**. Cada parcela da CCEE tem de cair em exatamente um
mineral — sobra viraria energia perdida, sobreposição viraria dupla contagem.

**Chapada é o caso que a separação não resolve.** Cobre e ouro saem do mesmo minério, da mesma usina, no mesmo município e sob o mesmo ramo.
Separá-los exigiria um critério de alocação entre co-produtos — por receita, por valor do metal contido —, que é convenção de inventário e não
medição. Nada foi alocado: o coeficiente de cada metal sai com `energia_exclusiva: false`, em outra cor no gráfico, e significa *toda a energia
da operação por unidade daquele metal*.

## O que a própria empresa publica

Quando a separação não resolve, o segundo caminho é o que a empresa divulga. `notas_energia` guarda isso, com o **efeito** de cada fato sobre o
número da CCEE:

| Empresa | Efeito | Fato |
|---|---|---|
| CMOC | **a CCEE subestima** | 35% da eletricidade das operações da Copebras em Catalão e Ouvidor — o negócio de fosfato — é gerada internamente e não passa pela CCEE |
| CMOC | contexto | 74,7% da energia veio de fontes renováveis em 2025 e o Escopo 2 foi zerado com I-REC; a companhia não publica MWh por operação |
| Anglo American | contexto | Barro Alto opera dois fornos elétricos de 83 MW pela rota RKEF. Os 166 MW de placa dão ~1,45 TWh/ano em regime contínuo, a mesma ordem da carga anualizada da unidade na CCEE — conferência independente do número |
| Lundin | não localizado | A companhia publica energia consolidada no Relatório de Sustentabilidade, sem abrir por operação nem por metal |

## Os dois papéis no painel

O **gráfico de energia** mostra sempre a **carga inteira da empresa** no ano; a **tabela e o coeficiente** mostram a **parcela do mineral**.
Misturar os dois na mesma escala compararia parte com todo.

Ordens de grandeza que o cruzamento produziu, e que servem de conferência de sanidade:

| Operação | Ano | Coeficiente | Leitura |
|---|---|---|---|
| Anglo American · níquel | 2025 | ~45.000 kWh/t | Compatível com ferroníquel em forno elétrico, que é o processo de Barro Alto e Codemin |
| Chapada · cobre | 2025 | ~8.350 kWh/t | Compatível com concentrador de cobre de teor baixo |
| Serra Grande · ouro | 2025 | ~1.850 kWh/oz | — |
| SAMA · crisotila | 2024 | ~320 kWh/t | Mina e beneficiamento, sem etapa metalúrgica |
| CMOC · nióbio | 2025 | ~27.800 kWh/t | **Superestimado**: carrega a energia do fosfato junto |

## Limites

- **A carga é do agente, não da planta.** Pode incluir consumo administrativo, e não inclui autoprodução nem geração própria.
- **Nenhum número de produção foi conferido no documento de origem** (ver `data/producao/README.md`). Toda linha herda essa limitação.
- **2022 e 2023 não têm energia**: a base CCEE do repositório começa em abril de 2024. As linhas desses anos aparecem com produção e sem
  coeficiente, de propósito.
- **Quatro empresas têm energia e nenhum coeficiente** — Mosaic, Serra Verde, Brasil Minérios e, em alguns anos, outras — porque não há produção
  publicada no recorte de Goiás para o ano. É onde a base de produção precisa crescer, e o painel mostra isso em vez de esconder.

## Atlas Empresarial (`atlas_empresas.json`)

O pacote do **Atlas Empresarial** alimenta as áreas Explorar, Dossiê e Comparar da aba `Empresas` (ver a seção seguinte), servido em `/api/empresas/atlas` (atrás da sessão, como o resto da aba). O pacote sai de
`python scripts/build_atlas_empresas.py` e é conferido por `tests/test_atlas_empresas.py`. A curadoria manual fica em `curadoria_atlas.json`.

| Bloco | Conteúdo | De onde vem |
|---|---|---|
| `empresas` | Uma linha por **CNPJ raiz de titular PJ** com processo, CFEM ou carga CCEE em Goiás (2.261), com o processo de referência do ponto no mapa (`pt`) | `data/panorama/panorama.json` (`dims.emp`) |
| `processos` | Os 16.875 processos do SIGMINE: fase, situação, mineral, uso, municípios IBGE intersectados, área, CFEM 2022–26, centroide e marca "Minas ativas (SGB)" | panorama `proc`, `data/mapa/tabelas/processos_complemento.json`, `data/atlas/processes.json`, `data/mapa/camadas/minas_ativas.json` |
| `cfem` | CFEM por titular, ano, município e mineral | panorama `cfem` |
| `cfem_processo_ano` | CFEM por processo e ano (só PJ) | `Squad 1/Dados corrigidos/ANM - CFEM/CFEM_Arrecadacao_2022_2026_GO.csv` |
| `detalhes` | As 10 empresas da base de produção: grupo, operações, registros de produção, RI, rateio e notas de energia | `data/producao/producao.json`, `data/empresas/empresas.json` |
| `projetos` | Base de projetos, carteira do Mercado e Radar de Projetos, com o método do vínculo e a localização que a fonte sustenta (`loc`) | `data/projetos`, `public/data/mercado`, `data/mapa/tabelas/radar_projetos.json` |
| `noticias` | Matérias do acervo do coletor ligadas a uma empresa, com alias, método, confiança e tipo | `public/data/noticias/meses/*.json` |
| `criticos` | Minerais estratégicos (federal) e críticos (Goiás), separados, com norma e link | `curadoria_atlas.json` |

### Regras

- **Identidade = CNPJ raiz.** Nome não é chave. Pessoa física não é nomeada (4.817 processos entram só na contagem), como no Mapa mineral.
- **Fase em grupo jurídico**, pelo mesmo critério do Radar (`Squad 3/backend/radar_api.py`): lavra autorizada (concessão de lavra, lavra
  garimpeira, licenciamento, registro de extração) — que **autoriza, não comprova operação** —, requerimento de lavra, pesquisa e disponibilidade.
- **"O que já explora"** só com evidência: produção declarada pela empresa (realizada, medida como produção, no recorte de Goiás) e processos com
  título de lavra e CFEM recolhida em 2024–2026 (situação do Panorama). Embarque e venda **não** são produção; capacidade, meta e guidance não são realizado.
- **Ponto no mapa = centroide do polígono do processo**, calculado da mesma geometria que `/api/atlas/processes` serve: indica o direito,
  não a mina. Nas 10 empresas enriquecidas, o município da operação declarada aparece como referência **aproximada**. Não há coordenada de
  mina ou planta documentada nas fontes, e nenhuma é desenhada.
- **Projetos**: o Radar se liga pelos processos ANM que o projeto cita (só o titular desses processos); a base de projetos e o Mercado, pela
  lista revisada `projetos_cnpj` (confiança `alta` = mesma razão social; `media` = subsidiária brasileira compatível, revisão humana pendente).
  Projeto sem correspondência fica sem vínculo (21).
- **Notícias**: alias revisado, palavra inteira, sem acento, ignorando o nome do veículo no fim do título. Nome de **grupo** exige contexto de Goiás
  no título; título de outra UF/país sem Goiás é descartado; entidade que opera em várias UFs (Mosaic, CBA, Nexa, Votorantim) também exige contexto;
  ex-funcionários e "próximo da mina" viram **menção indireta**. Exemplos de descarte vão no próprio pacote.
- **Top N e puxadores** são calculados no navegador sobre o recorte: métrica (CFEM, nº de processos, área, carga CCEE), período e universo
  aparecem na tela e na exportação. **Puxadores** = menor grupo de empresas que soma 80% da CFEM do recorte no período.
- **Minerais estratégicos/críticos**: lista federal da Resolução MME/CTAPME nº 2/2021 (a Lei nº 15.506/2026 não traz lista própria) e rol da
  Lei estadual nº 23.597/2025, art. 3º. As duas não se fundem. Incisos VII e VIII da lei estadual (remineralizadores e agrominerais) são
  definidos pelo uso declarado na ANM.

### Limites

- O pacote **não** entra em `scripts/atualizar_derivados.py`: depois de refazer o panorama, a produção ou o acervo de notícias, rode o gerador à mão.
- A ligação de notícias é por nome: pode omitir matérias que citam a empresa por outro nome, e a ausência de notícia não é ausência de fato.
- Vínculos de projeto com confiança `media` e todos os números de produção seguem pendentes de conferência humana na origem.

## Atlas Empresarial: aba Empresas consolidada (26/11/2026)

A aba `Empresas` reúne a versão anterior (commit `bb87b53`: mapa de empresas, produção por empresa, produção declarada e energia,
arrecadação/títulos/consumo) e o Atlas Empresarial numa experiência só, em quatro áreas com **uma seleção de empresa para a aba inteira**:

| Área | O que faz | Fonte |
|---|---|---|
| Explorar empresas | Mapa único em três modos (Empresas, Processos, Projetos), busca, filtros, indicadores, Top N, puxadores | `atlas_empresas.json` |
| Dossiê empresarial | Perfil, território e processos, economia e energia (resumo executivo), projetos, notícias, histórico | `atlas_empresas.json` + `empresas.json` |
| Análises | Produção estimada (AMB × CFEM), produção declarada e energia, arrecadação/títulos/consumo — cada uma com escopo "empresa selecionada" ou "todas as empresas" | `empresas.json` (`estimada`, `linhas`) e `data/panorama/panorama.json` |
| Comparar empresas | Até três empresas, por grupos de indicador e em unidades separadas | as mesmas |

- **Uma fonte por número.** O dossiê e a comparação leem as mesmas linhas das análises (`EmpresasAnalises.estimadaDe/declaradaDe`);
  o resumo do dossiê não repete gráficos nem tabelas da análise — oferece "Aprofundar".
- **Empresa sem dado numa análise** mostra "Dados não disponíveis para esta empresa", o porquê e o que a base tem dela (CFEM, títulos,
  carga do agente CCEE). O painel nunca volta silenciosamente para o agregado de todas as empresas (defeito da integração anterior, em que a
  sincronização por nome limpava o filtro). Ver `tests/js/analises_escopo.js`.
- **Arrecadação, títulos e consumo** é a instância do motor do Panorama na aba (`panorama.js`, prefixo `epn-`), agora em três sub-abas e com
  filtro exato pelo **CNPJ raiz** da empresa selecionada (titular em `dims.emp`, agente CCEE em `dims.ce`). Quadros que não leem o filtro de
  empresa (líder por mineral, curva de concentração) dizem "Todas as empresas".
- `mapa_empresas.json` e `scripts/build_mapa_empresas.py` continuam gerados e servidos em `/api/empresas/mapa` (legado), mas a aba não os
  carrega: o modo Empresas do mapa usa o ponto calculado em `atlas_empresas.json` pela mesma regra (2.249 de 2.250 empresas no mesmo processo
  de referência; a diferença é um par de títulos com o mesmo centroide antigo).

### Mapa: o que cada símbolo representa

| Modo | Símbolo | Posição | Precisão |
|---|---|---|---|
| Empresas | círculo, tamanho pela métrica, cor pela fase mais avançada | centroide do processo da empresa que mais recolheu CFEM 2022–2026 (sem CFEM, maior título de lavra; senão, maior processo) — `empresas[].pt` | indicativa: um direito minerário de referência, não a sede nem a mina |
| Processos | ponto fino por título; polígono ANM a partir do zoom 11,5 | centroide do polígono SIGMINE | indicativa |
| Projetos | losango cheio | centroide do maior processo ANM citado pelo projeto — `projetos[].loc = {t:'p', k:[...]}` | indicativa |
| Projetos | losango vazado | referência do município informado — `projetos[].loc = {t:'m', m:[...]}` | aproximada |
| Projetos | — | sem processo nem município de Goiás reconhecido: só na lista (`loc = null`) | sem localização inventada |
| (todos) | quadrado vazado | município da operação declarada (10 empresas) | aproximada |

Nenhuma fonte do projeto traz coordenada documentada de mina ou planta; nenhum símbolo é apresentado como tal. A camada "Minas ativas"
do SGB marca processos (polígonos), não pontos de mina.

## Produção estimada por empresa (AMB × CFEM, bloco `estimada` de `empresas.json`)

Gerado por `scripts/build_empresas_base.py` a partir de `Squad 1/Bases consolidadas/documentacao/base_producao/` (`gerar_base_producao.py`
do Squad 1): o total do estado do **Anuário Mineral Brasileiro** (ANM) por mineral, ano (2022 em diante) e base (ROM, beneficiada, conteúdo
mineral) é dividido entre as empresas pela parcela dos processos delas na **CFEM paga em R$** no mineral e ano. É **estimativa**, nunca
produção observada; onde a empresa publica a mesma medida, os dois números ficam lado a lado (`publicado_t`, `diferenca_vs_publicado`).
Energia (2024–2025): carga do agente na CCEE pelo CNPJ raiz, separada entre minerais pelo Squad 2 ou pela produção × coeficiente médio;
sem carga na CCEE, estimada pela média dos coeficientes do mineral.

- **Não somar o que não se soma:** toneladas de minerais diferentes, bases diferentes (ROM × beneficiada × contido) e anos diferentes ficam
  em linhas separadas. Sem mineral escolhido, as barras usam a CFEM (R$), que é comparável entre minerais.
- **Correção (26/11/2026):** a linha de ROM e a de beneficiada de uma empresa repetem a mesma CFEM. Com "Todas as bases", a versão anterior
  somava as duas e a CFEM do recorte saía em dobro (R$ 1,45 bi em vez de R$ 0,73 bi em 2022–2025); as barras de produção com "Todas as
  bases" somavam toneladas de ROM e de beneficiada. Agora cada empresa, mineral e ano entra uma vez, na base preferida (beneficiada → contido
  → ROM). Os dados do pacote não mudaram.
- Pessoa física aparece como "pessoa física (nome não publicado)", sem CPF, como no resto da plataforma.
- Numa cópia sem `Squad 1/.../base_producao` o gerador não roda; `tests/test_empresas.py` pula o teste de reprodutibilidade dizendo por quê.

## Mapa das empresas (`mapa_empresas.json`)

Este pacote descreve, para cada empresa (pessoa jurídica) com processo minerário em Goiás ou CFEM recolhida, onde ela minera e o
que recolheu. Até 27/11/2026 alimentava a sub-aba **Mapa das empresas**; desde a aba Empresas consolidada, o ponto por empresa é o
modo Empresas do mapa único (calculado do `atlas_empresas.json` pela mesma regra), e a página não carrega mais este pacote.
Ele continua gerado, versionado e disponível para download. O pacote é servido em `/api/empresas/mapa`, atrás da sessão, e sai de
`python scripts/build_mapa_empresas.py`. Pessoa física não entra, porque não tem nome publicado.

| Bloco | Conteúdo | De onde vem |
|---|---|---|
| `empresas` | Uma linha por empresa (2.261): nome, CNPJ raiz, ponto no mapa, CFEM total, por ano, por mineral e por município, carga na CCEE por ano, títulos por fase, área de lavra e de pesquisa, e notícias | SIGMINE (`data/atlas/processes.json`); CFEM, Cadastro Mineiro e CCEE (`data/panorama/panorama.json`); radar de notícias (`public/data/noticias/meses`) |
| `processos` | Um processo por linha (11.144): empresa, centro do processo, fase, grupo, mineral, município, área, número do processo e CFEM de 2022 a 2026 | os mesmos |
| `dims` | Os vocabulários das colunas: 16 fases, 4 grupos, 67 minerais e 246 municípios | os mesmos |

### Regras

- **Onde fica a empresa no mapa:** no processo dela que mais recolheu CFEM em 2022–2026; sem CFEM, no maior título de lavra; senão, no
  maior processo.
- **Centro do processo:** a média dos vértices do polígono do SIGMINE.
- **Energia:** a carga da CCEE do CNPJ raiz em Goiás, por ano, sem anualizar (em 2024 e 2026 os meses são incompletos).
- **Notícias:** matérias do radar cujo título cita a empresa por um nome conhecido ou pela razão social inteira.
- **Produção e coeficiente energético** não estão neste pacote: vêm do bloco "estimada" de `empresas.json`, que a página já carrega.
