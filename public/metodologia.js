/* Metodologia: one sub-tab per product of the panel, each with the same five blocks — what it measures, sources and period,
   how it is calculated, what it does not measure, and how to rebuild and test it. The text summarises METODOLOGIA.md and the
   READMEs of each data packet (data/<produto>/README.md); when a rule changes, change it there and here in the same commit.
   Every prose field carries both languages; the page reloads on a language switch, so a single render is enough. */
(()=>{'use strict';
const el=id=>document.getElementById(id);
const E=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const L=v=>v&&typeof v==='object'&&!Array.isArray(v)?(v[I18N.lang]??v.pt):v;
// Prose may carry <b>, <i> and <code>; everything else is escaped.
const R=v=>E(L(v)).replace(/&lt;(\/?)(b|i|code)&gt;/g,'<$1$2>');
const STORAGE='minera-mt-tab';
const REPO='https://github.com/mineragoias-rgb/minera-goias/blob/main/';

const BLOCOS=[
  ['mede',{pt:'O que mede',en:'What it measures'}],
  ['fontes',{pt:'Fontes e período',en:'Sources and period'}],
  ['calculo',{pt:'Como é calculado',en:'How it is calculated'}],
  ['limites',{pt:'O que não mede e limites',en:'What it does not measure, and limits'}],
  ['refazer',{pt:'Como refazer e o que é testado',en:'How to rebuild it and what is tested'}]
];

const PRODUTOS=[
{id:'principios',view:null,
 nome:{pt:'Princípios comuns',en:'Common principles'},
 resumo:{pt:'Regras que valem para todos os produtos do painel. Cada produto, nas outras abas, aplica essas regras à sua própria fonte.',
         en:'Rules that hold for every product in the panel. Each product, in the other tabs, applies them to its own source.'},
 mede:[
  {pt:'<b>Contagem não é consumo nem produção.</b> Um registro é uma linha de uma fonte: "8 mil registros da CCEE" é número de linhas, não de empresas, minas ou MWh.',
   en:'<b>A count is neither consumption nor production.</b> A record is one row of a source: "8 thousand CCEE records" is a number of rows, not of companies, mines or MWh.'},
  {pt:'<b>Quando a fonte não diz, o sistema não inventa.</b> Sem CNPJ na origem, o titular fica sem documento; sem série anual, o município fica sem série.',
   en:'<b>When the source is silent, the system does not invent.</b> No CNPJ at the source means no document for the holder; no yearly detail means no series.'}],
 fontes:[
  {pt:'Fontes oficiais (ANM, IBGE, SGB, CCEE, MapBiomas) entram como foram publicadas, com URL, data de acesso e SHA-256 registrados na aba 07 da base consolidada do Squad 1.',
   en:'Official sources (ANM, IBGE, SGB, CCEE, MapBiomas) come in as published, with URL, access date and SHA-256 recorded in tab 07 of the Squad 1 consolidated base.'},
  {pt:'Fontes não oficiais (relatórios de empresas, imprensa, estudos setoriais) ficam em produtos separados e marcadas como tal: nunca corrigem nem substituem um número oficial.',
   en:'Non-official sources (company reports, press, sector studies) stay in separate products and are labelled as such: they never correct or replace an official figure.'}],
 calculo:[
  {pt:'<b>Unidade nunca é convertida por inferência.</b> Nada é somado entre unidades diferentes (t, kg, m³, l, ct…).',
   en:'<b>Units are never converted by inference.</b> Nothing is added across different units (t, kg, m³, l, ct…).'},
  {pt:'<b>Fontes sobrepostas não se somam</b>, e co-produtos do mesmo minério (ouro e cobre, bário e nióbio) não se somam entre si: a mesma tonelagem seria contada duas vezes.',
   en:'<b>Overlapping sources are not added up</b>, nor are co-products of the same ore (gold and copper, barium and niobium): the same tonnage would be counted twice.'},
  {pt:'Todo valor carrega os campos de governança: <code>source_id</code>, <code>valor_observado_estimado</code> (observado, calculado, estimado, benchmark), <code>metodo_estimacao</code> e <code>status_validacao</code>.',
   en:'Every value carries the governance fields: <code>source_id</code>, <code>valor_observado_estimado</code> (observed, calculated, estimated, benchmark), <code>metodo_estimacao</code> and <code>status_validacao</code>.'}],
 limites:[
  {pt:'<b>Importar não é validar.</b> Linha carregada nasce <code>nao_validado</code>; validar é ato humano, registrado em <code>responsavel_validacao</code>.',
   en:'<b>Importing is not validating.</b> A loaded row starts as <code>nao_validado</code>; validation is a human act, recorded in <code>responsavel_validacao</code>.'},
  {pt:'Erros encontrados na fonte são sinalizados (alerta), não corrigidos por suposição. O original é preservado ao lado do valor tratado.',
   en:'Errors found in a source are flagged, not corrected by guesswork. The original is kept next to the treated value.'}],
 refazer:[
  {pt:'Uma regra de cálculo só muda junto com três coisas: o código que a implementa, o teste que a fixa e o documento de metodologia.',
   en:'A calculation rule only changes together with three things: the code that implements it, the test that pins it and the methodology document.'},
  {pt:'Toda medição pode ser refeita a partir do repositório; os comandos de cada produto estão na sua aba.',
   en:'Every measurement can be rebuilt from the repository; each product\'s commands are in its own tab.'}],
 docs:['METODOLOGIA.md','HANDOFF.md']},

{id:'atlas',view:'atlas',
 nome:{pt:'Atlas e panorama',en:'Atlas and overview'},
 resumo:{pt:'Mapa por município e processo minerário, com séries e gráficos do setor em Goiás, gerado da base consolidada do Squad 1.',
         en:'Map by municipality and mining title, with series and charts of the sector in Goiás, generated from the Squad 1 consolidated base.'},
 mede:[
  {pt:'<b>Atlas:</b> CFEM por município (R$), quantidade comercializada declarada na CFEM, processos do SIGMINE, projetos que ainda não produzem, ocorrências geológicas do RECMIN, energia da cadeia mineral e barragens. Cada camada tem unidade e período próprios e elas não se comparam entre si.',
   en:'<b>Atlas:</b> CFEM by municipality (R$), quantity sold as declared to CFEM, SIGMINE titles, projects not yet producing, RECMIN geological occurrences, energy of the mining chain and dams. Each layer has its own unit and period and they are not comparable with each other.'},
  {pt:'<b>Panorama:</b> gráficos e tabelas da arrecadação, território, produção, pesquisa, empresas, energia e barragens, com filtros de ano, mês, município, mineral, titular, fase, tipo de gasto e ramo da CCEE.',
   en:'<b>Overview:</b> charts and tables on royalties, territory, production, exploration, companies, energy and dams, filtered by year, month, municipality, mineral, holder, phase, spending type and CCEE activity.'}],
 fontes:[
  {pt:'Base consolidada do Squad 1 (planilha v18 e GeoPackage): CFEM 2022 até o arquivo mais recente (2026 parcial), Anuário Mineral Brasileiro 2010–2025, SIGMINE, Cadastro Mineiro, malha municipal do IBGE, RECMIN do SGB.',
   en:'Squad 1 consolidated base (workbook v18 and GeoPackage): CFEM from 2022 to the latest file (2026 partial), Brazilian Mineral Yearbook 2010–2025, SIGMINE, Mining Register, IBGE municipal grid, SGB RECMIN.'},
  {pt:'Investimento em pesquisa mineral (ANM), rodadas de disponibilidade e parcelas de carga da CCEE (abril/2024 em diante; a CCEE não publica antes).',
   en:'Mineral exploration investment (ANM), availability rounds and CCEE load records (April 2024 onward; CCEE does not publish earlier).'},
  {pt:'Energia por município e barragens (SIGBM) ainda vêm do retrato anterior recebido pela equipe, com origem registrada em <code>meta.retained_from_artifact</code>.',
   en:'Energy by municipality and dams (SIGBM) still come from the earlier snapshot received by the team, with origin recorded in <code>meta.retained_from_artifact</code>.'}],
 calculo:[
  {pt:'CFEM de um intervalo = soma dos anos cobertos. A soma dos 246 municípios fecha com o arquivo bruto: R$ 867.578.398,91 no período completo.',
   en:'CFEM for a span = sum of the years it covers. The 246 municipalities add up to the raw file: R$ 867,578,398.91 for the full period.'},
  {pt:'Escala de cores por quantis dos valores positivos; cinza é "sem registro ou zero", que a fonte não separa.',
   en:'Colour scale by quantiles of positive values; grey means "no record or zero", which the source does not distinguish.'},
  {pt:'Na CCEE, cargas sem ramo de atividade são das distribuidoras (mercado cativo) e ficam separadas; rankings por ramo usam só o mercado livre. A ligação carga → titular é pela raiz do CNPJ.',
   en:'In CCEE data, loads without an activity are the distribution utilities (captive market) and are kept apart; rankings by activity use only the free market. Load is linked to the holder by the CNPJ root.'}],
 limites:[
  {pt:'Quantidade comercializada na CFEM <b>não é produção</b>; quantidades em m³, l e m² e as linhas excluídas na aba 09b ficam fora das toneladas.',
   en:'Quantity sold in CFEM <b>is not production</b>; quantities in m³, l and m² and the rows excluded in tab 09b stay out of the tonnes.'},
  {pt:'Produção bruta não se soma entre minerais (co-produtos repetem a tonelagem). Geometrias são simplificadas: não servem como limite cadastral nem para somar áreas.',
   en:'Run-of-mine production is not added across minerals (co-products repeat the tonnage). Geometries are simplified: not cadastral limits and not for adding areas.'},
  {pt:'Intensidade energética municipal é razão do retrato recebido, não medição por operação. Pessoa física nunca aparece com nome.',
   en:'Municipal energy intensity is a ratio from the received snapshot, not a per-operation measurement. Individuals never appear by name.'}],
 refazer:[
  {pt:'<code>python scripts/build_atlas_base.py --base "&lt;pasta do Squad 1&gt;"</code> e <code>python scripts/build_panorama_base.py</code>.',
   en:'<code>python scripts/build_atlas_base.py --base "&lt;Squad 1 folder&gt;"</code> and <code>python scripts/build_panorama_base.py</code>.'},
  {pt:'<code>tests/test_atlas.py</code> confere que os gráficos de CFEM somam o total de cada ano e que projetos e ocorrências batem com as abas 04 e 06; <code>tests/test_panorama.py</code> guarda o pacote do panorama.',
   en:'<code>tests/test_atlas.py</code> checks that the CFEM charts add up to each year\'s total and that projects and occurrences match tabs 04 and 06; <code>tests/test_panorama.py</code> guards the overview packet.'}],
 docs:['data/atlas/README.md','data/panorama/README.md']},

{id:'mapa',view:'mapa',
 nome:{pt:'Mapa mineral',en:'Mineral map'},
 resumo:{pt:'Mapa temático no estilo do P3M do SGB, com camadas geológicas, de recursos minerais, de vegetação e as camadas do Atlas, todas recortadas para Goiás.',
         en:'Thematic map in the style of the SGB P3M, with geological, mineral-resource and vegetation layers plus the Atlas layers, all clipped to Goiás.'},
 mede:[
  {pt:'Onde estão as feições de cada camada (pontos, linhas, polígonos) e seus atributos, com indicadores por município que dizem unidade, período e se podem ser somados entre municípios.',
   en:'Where each layer\'s features are (points, lines, polygons) and their attributes, with municipal indicators that state unit, period and whether they can be added across municipalities.'},
  {pt:'Vegetação nativa do MapBiomas em série anual 1985–2025, um ano por vez.',
   en:'MapBiomas native vegetation as a yearly series 1985–2025, one year at a time.'}],
 fontes:[
  {pt:'Camadas do P3M (SGB) organizadas nas pastas temáticas do Squad 1, pacote de vegetação e rios do Squad 1, MapBiomas Coleção 11 e as camadas do Atlas (processos, municípios, projetos da ANM, ocorrências e barragens), reaproveitadas sem cópia.',
   en:'P3M (SGB) layers organised in the Squad 1 thematic folders, the Squad 1 vegetation and rivers package, MapBiomas Collection 11 and the Atlas layers (titles, municipalities, ANM projects, occurrences and dams), reused without copying.'},
  {pt:'Radar de Projetos (levantamento da equipe), ligado ao mapa pelos processos da ANM.',
   en:'Project Radar (team survey), linked to the map through ANM titles.'}],
 calculo:[
  {pt:'Tudo sai de <code>scripts/build_mapa_base.py</code>, que lê o catálogo editável <code>scripts/mapa_camadas.json</code>; nenhum número é digitado à mão e as mesmas entradas gravam os mesmos bytes.',
   en:'Everything comes from <code>scripts/build_mapa_base.py</code>, which reads the editable catalogue <code>scripts/mapa_camadas.json</code>; no figure is typed by hand and the same inputs write the same bytes.'},
  {pt:'Geometria quantizada (passo de ~12 m numa camada do tamanho de Goiás). Ausência é <code>null</code> e nunca vira zero.',
   en:'Quantised geometry (~12 m step on a Goiás-sized layer). Absence is <code>null</code> and never becomes zero.'},
  {pt:'A vegetação é imagem na grade do MapBiomas na web (~150 m): cada pixel fica com o grupo que cobre a maior parte da sua área nos pixels de 30 m, sem simplificar nem omitir fragmentos.',
   en:'Vegetation is an image on the MapBiomas web grid (~150 m): each pixel takes the group covering most of its area in the 30 m pixels, with nothing simplified or dropped.'},
  {pt:'Filtros: valores de um mesmo filtro combinam com OU; filtros diferentes, com E.',
   en:'Filters: values of one filter combine with OR; different filters, with AND.'}],
 limites:[
  {pt:'Goiás é um recorte fixo; o mapa-base mostra o entorno só para orientação.',
   en:'Goiás is a fixed cut; the basemap shows the surroundings only for orientation.'},
  {pt:'Geometrias simplificadas para a web: servem para localizar, não como limite oficial.',
   en:'Geometries simplified for the web: they locate, they are not official limits.'}],
 refazer:[
  {pt:'<code>python scripts/build_mapa_base.py</code> (ou <code>--checar</code> para só validar); na main, o fluxo de derivados refaz a etapa quando o P3M, o MapBiomas ou o gerador mudam.',
   en:'<code>python scripts/build_mapa_base.py</code> (or <code>--checar</code> to validate only); on main, the derived-data workflow rebuilds it when P3M, MapBiomas or the generator change.'},
  {pt:'<code>tests/test_mapa.py</code> refaz tudo e compara com o publicado; <code>tests/mapa-dados.test.js</code> e <code>tests/mapa-shp.test.js</code> testam o carregador e o shapefile baixado.',
   en:'<code>tests/test_mapa.py</code> rebuilds everything and compares it with what is published; <code>tests/mapa-dados.test.js</code> and <code>tests/mapa-shp.test.js</code> test the loader and the downloaded shapefile.'}],
 docs:['data/mapa/README.md']},

{id:'previsao',view:'previsao',
 nome:{pt:'Previsão de demanda',en:'Demand forecast'},
 resumo:{pt:'Demanda de energia elétrica da mineração de Goiás de 2027 a 2040, em três cenários, pelo modelo do Squad 2. A aba Previsão tem a metodologia detalhada, com equações e backtest.',
         en:'Electricity demand of mining in Goiás from 2027 to 2040, in three scenarios, from the Squad 2 model. The Forecast tab has the detailed methodology, with equations and backtest.'},
 mede:[
  {pt:'Energia projetada (MWh/TWh) por mineral e no total, nos cenários conservador, referência e expansão, com faixa baixa–alta.',
   en:'Projected energy (MWh/TWh) by mineral and in total, in the conservative, reference and expansion scenarios, with a low–high band.'},
  {pt:'Cobre, bauxita, níquel, fosfato e amianto; nióbio e outras substâncias ainda ficam de fora por falta de dados conciliáveis.',
   en:'Copper, bauxite, nickel, phosphate and asbestos; niobium and other substances are still out for lack of reconcilable data.'}],
 fontes:[
  {pt:'Produção histórica estadual do Squad 1 (Anuário Mineral, 2010–2025; bauxita desde 2014), via aba 08 e pacote de interface com o Squad 2.',
   en:'Squad 1 state production history (Mineral Yearbook, 2010–2025; bauxite since 2014), via tab 08 and the Squad 2 interface packet.'},
  {pt:'Intensidade energética de 2025 do Squad 2: carga na CCEE ÷ produção da mesma entidade; mineral sem carga na CCEE usa referência externa (benchmark).',
   en:'Squad 2 2025 energy intensity: CCEE load ÷ production of the same entity; a mineral without CCEE load uses an external benchmark.'},
  {pt:'Carteira de projetos da curadoria do Squad 1, com peso por maturidade e cenário.',
   en:'Project portfolio from the Squad 1 curation, weighted by maturity and scenario.'}],
 calculo:[
  {pt:'Produção(m,t) = Produção(m,2025) × (1 + g(m) + ajuste do cenário)^(t − 2025); Intensidade cai com o ganho anual de eficiência; Energia = Produção × Intensidade.',
   en:'Production(m,t) = Production(m,2025) × (1 + g(m) + scenario adjustment)^(t − 2025); intensity falls with the yearly efficiency gain; Energy = Production × Intensity.'},
  {pt:'Backtest esconde os últimos anos de cada série e escolhe entre tendência e persistência pelo erro (MAPE).',
   en:'The backtest hides the last years of each series and picks between trend and persistence by error (MAPE).'},
  {pt:'Faixa = energia × (1 ∓ MAPE) × (1 ∓ 10% na intensidade). Toneladas não se somam entre minerais; só a energia é agregada.',
   en:'Band = energy × (1 ∓ MAPE) × (1 ∓ 10% on intensity). Tonnes are not added across minerals; only energy is aggregated.'}],
 limites:[
  {pt:'São cenários condicionais às hipóteses (ajustes de cenário são ilustrativos), não previsão oficial nem consumo medido; as faixas não são intervalos estatísticos de confiança.',
   en:'These are scenarios conditional on assumptions (scenario adjustments are illustrative), not an official forecast nor measured consumption; bands are not statistical confidence intervals.'},
  {pt:'A carteira só soma projetos com incremento e ano de entrada nas fontes; encerramentos não são modelados. A CCEE não inclui autoprodução.',
   en:'The portfolio only adds projects whose sources give an increment and a start year; closures are not modelled. CCEE excludes self-generation.'}],
 refazer:[
  {pt:'Modelo em <code>Squad 2/modello_reale</code>; pacote da aba com <code>python scripts/build_previsao_base.py</code>.',
   en:'Model in <code>Squad 2/modello_reale</code>; tab packet with <code>python scripts/build_previsao_base.py</code>.'},
  {pt:'<code>tests/test_previsao.py</code> e <code>tests/test_simulador.py</code>.',
   en:'<code>tests/test_previsao.py</code> and <code>tests/test_simulador.py</code>.'}],
 docs:['Squad 3/documentacao/simulador/README.md']},

{id:'mercado',view:'mercado',
 nome:{pt:'Mercado',en:'Market'},
 resumo:{pt:'Leitura do mercado de minerais críticos em torno de Goiás: operações, transações, mineradoras de referência, regulação, notícias e a carteira de projetos.',
         en:'Reading of the critical-minerals market around Goiás: operations, transactions, reference miners, regulation, news and the project portfolio.'},
 mede:[
  {pt:'O que as fontes públicas dizem sobre quem produz, quanto valem os ativos negociados e como se saem empresas comparáveis.',
   en:'What public sources say about who produces, how much traded assets are worth and how comparable companies perform.'},
  {pt:'Carteira de projetos em Goiás, da pesquisa inicial à operação, classificada pela maturidade (operação, expansão, construção, definido, provável, possível, sinal).',
   en:'Project portfolio in Goiás, from early exploration to operation, classified by maturity (operation, expansion, construction, defined, probable, possible, signal).'}],
 fontes:[
  {pt:'Imprensa especializada, resultados divulgados por empresas de capital aberto e estudos setoriais, com link de cada fonte. Valores são os últimos publicados até a data indicada na aba.',
   en:'Trade press, results disclosed by listed companies and sector studies, each with its link. Figures are the latest published up to the date shown in the tab.'},
  {pt:'Carteira: levantamento do Squad 1 (Lucas Maia) em relatórios corporativos, órgãos públicos (ANM, SEMAD-GO) e imprensa.',
   en:'Portfolio: Squad 1 survey (Lucas Maia) of corporate reports, public bodies (ANM, SEMAD-GO) and the press.'}],
 calculo:[
  {pt:'Nada é recalculado: cada valor fica na moeda e no período em que foi divulgado, sem conversão, por isso não se somam entre si.',
   en:'Nothing is recalculated: each value stays in the currency and period in which it was disclosed, without conversion, so they do not add up.'},
  {pt:'Maturidade mede o grau de comprovação econômica do projeto, não a etapa administrativa; cada classificação traz as notícias que a sustentam.',
   en:'Maturity measures how proven a project is economically, not its administrative stage; each classification lists the news that supports it.'}],
 limites:[
  {pt:'Não vem da base consolidada do Squad 1: contextualiza o que os dados da ANM e da CCEE mostram, não os substitui.',
   en:'It does not come from the Squad 1 consolidated base: it contextualises what ANM and CCEE data show, it does not replace them.'},
  {pt:'Valores financeiros podem já ter sido revisados pelas empresas; linguagem especulativa não vira capacidade ou CAPEX.',
   en:'Financial figures may already have been revised by the companies; speculative wording does not become capacity or CAPEX.'}],
 refazer:[
  {pt:'Arquivos em <code>public/data/mercado/</code>; a carteira é gerada por <code>scripts/build_projetos_go.py</code> a partir da planilha do levantamento.',
   en:'Files in <code>public/data/mercado/</code>; the portfolio is generated by <code>scripts/build_projetos_go.py</code> from the survey workbook.'},
  {pt:'<code>tests/test_mercado.py</code> e <code>tests/test_projetos.py</code>.',
   en:'<code>tests/test_mercado.py</code> and <code>tests/test_projetos.py</code>.'}],
 docs:['METODOLOGIA.md']},

{id:'empresas',view:'empresas',
 nome:{pt:'Empresas',en:'Companies'},
 resumo:{pt:'O que cada empresa declarou produzir em Goiás, quanta carga da CCEE puxou e o coeficiente de energia entre os dois.',
         en:'What each company declared it produced in Goiás, how much CCEE load it drew and the energy coefficient between the two.'},
 mede:[
  {pt:'<b>Produção declarada</b> pela empresa, não medida na mina, com quatro qualificadores: medida (ROM, contido, produto, venda…), escopo (Goiás, Brasil, global), tipo (realizado, guidance, capacidade, meta) e período.',
   en:'<b>Production declared</b> by the company, not measured at the mine, with four qualifiers: measure (ROM, contained, product, sales…), scope (Goiás, Brazil, global), type (actual, guidance, capacity, target) and period.'},
  {pt:'<b>Coeficiente</b> = energia (kWh) ÷ produção, na unidade que a empresa publica (kWh/t ou kWh/oz).',
   en:'<b>Coefficient</b> = energy (kWh) ÷ production, in the unit the company publishes (kWh/t or kWh/oz).'}],
 fontes:[
  {pt:'Releases de resultados e relatórios anuais das empresas (ou o que imprensa e agregadores reproduzem deles); parcelas de carga da CCEE ligadas pela raiz do CNPJ.',
   en:'Company results releases and annual reports (or what press and aggregators reproduce from them); CCEE load records linked by the CNPJ root.'}],
 calculo:[
  {pt:'Anualização pro rata e declarada: observado ÷ meses observados × 12, com qualidade (completo, alto, médio, baixo); o coeficiente herda a qualidade do lado mais fraco.',
   en:'Pro-rata, declared annualisation: observed ÷ months observed × 12, with a quality grade (complete, high, medium, low); the coefficient inherits the weaker side\'s grade.'},
  {pt:'A carga de uma empresa com vários minerais só é separada pelo que a CCEE declara (ramo e município), nunca por proporção arbitrada; quando não separa (cobre e ouro de Chapada), cada metal carrega a energia inteira e isso é marcado.',
   en:'A multi-mineral company\'s load is split only by what CCEE declares (activity and municipality), never by an arbitrary share; when it cannot be split (Chapada copper and gold), each metal carries the whole energy and this is flagged.'},
  {pt:'Produção, embarque e venda são números diferentes e nenhum substitui o outro; trimestres não são somados para formar o ano.',
   en:'Production, shipments and sales are different figures and none replaces another; quarters are not added to make a year.'}],
 limites:[
  {pt:'É o que foi publicado, não o que foi medido: toda linha nasce <code>nao_validado</code> até ser conferida no documento original.',
   en:'It is what was published, not what was measured: every row starts as <code>nao_validado</code> until checked against the original document.'},
  {pt:'Não é intensidade medida na planta: a carga da CCEE pode incluir consumo administrativo e não inclui autoprodução.',
   en:'It is not plant-measured intensity: CCEE load may include administrative use and excludes self-generation.'}],
 refazer:[
  {pt:'<code>python scripts/build_producao_base.py</code> e <code>python scripts/build_empresas_base.py</code>; o agente semanal (<code>producao/agente.py</code>) propõe candidatos sem escrever na base.',
   en:'<code>python scripts/build_producao_base.py</code> and <code>python scripts/build_empresas_base.py</code>; the weekly agent (<code>producao/agente.py</code>) proposes candidates without writing to the base.'},
  {pt:'<code>tests/test_producao.py</code> e <code>tests/test_empresas.py</code> (inclui a regra de que a carga é particionada sem sobra nem sobreposição).',
   en:'<code>tests/test_producao.py</code> and <code>tests/test_empresas.py</code> (including the rule that load is partitioned with no leftover or overlap).'}],
 docs:['data/producao/README.md','data/empresas/README.md']},

{id:'radar',view:'radar',
 nome:{pt:'Radar',en:'Radar'},
 resumo:{pt:'O que já está autorizado, o que está em análise e quais áreas a ANM pode reabrir, mais as notícias do setor coletadas diariamente.',
         en:'What is already authorised, what is under review and which areas ANM may reopen, plus sector news collected daily.'},
 mede:[
  {pt:'Processos por fase no cadastro da ANM e situação das áreas das rodadas de disponibilidade em Goiás. Todo número é contagem de registros, nunca previsão.',
   en:'Titles by phase in the ANM register and status of availability-round areas in Goiás. Every figure is a count of records, never a forecast.'},
  {pt:'Notícias com procedência: título, link, data, veículo, substâncias citadas e se falam de Goiás.',
   en:'News with provenance: title, link, date, outlet, substances cited and whether they mention Goiás.'}],
 fontes:[
  {pt:'SIGMINE e Cadastro Mineiro (ANM), resultado das rodadas de disponibilidade (ANM) e feeds RSS/Atom de veículos setoriais, regionais, nacionais e internacionais listados em <code>feeds.json</code>.',
   en:'SIGMINE and Mining Register (ANM), availability-round results (ANM) and RSS/Atom feeds from sector, regional, national and international outlets listed in <code>feeds.json</code>.'}],
 calculo:[
  {pt:'Substância e município são marcados por palavra inteira (assim "ouro" não casa dentro de "tesouro"); município só conta junto de um termo do setor.',
   en:'Substance and municipality are matched by whole word (so "ouro" does not match inside "tesouro"); a municipality only counts together with a sector term.'},
  {pt:'Duas marcas independentes: <b>regional</b> (cita Goiás) e <b>setorial</b> (cita mineração ou substância, só no título). O número defensável é o cruzamento das duas.',
   en:'Two independent tags: <b>regional</b> (mentions Goiás) and <b>sector</b> (mentions mining or a substance, title only). The defensible number is where both meet.'}],
 limites:[
  {pt:'O radar não produz série de preços e a leitura de "alta/baixa" nas manchetes está desligada, porque erra de forma medida.',
   en:'The radar produces no price series and the headline "up/down" reading is switched off, because it errs in a measured way.'},
  {pt:'Não há gráfico de notícias por mês: o acervo inicial foi coletado de uma vez, e o gráfico mediria a coleta, não o volume de notícia.',
   en:'There is no news-per-month chart: the initial archive was collected at once, and the chart would measure collection, not news volume.'}],
 refazer:[
  {pt:'Coletor em <code>Squad 3/radar-noticias/radar.py</code>; a API do painel está em <code>Squad 3/backend/radar_api.py</code>.',
   en:'Collector in <code>Squad 3/radar-noticias/radar.py</code>; the panel API is in <code>Squad 3/backend/radar_api.py</code>.'},
  {pt:'<code>tests/test_radar_api.py</code>, <code>tests/test_radar_noticias.py</code>, <code>tests/test_radar_projetos.py</code> e <code>tests/test_news.py</code>.',
   en:'<code>tests/test_radar_api.py</code>, <code>tests/test_radar_noticias.py</code>, <code>tests/test_radar_projetos.py</code> and <code>tests/test_news.py</code>.'}],
 docs:['Squad 3/radar-noticias/README.md','Squad 1/Radar de Projetos/LEIA-ME.md']},

{id:'bases',view:'bases',
 nome:{pt:'Base de dados',en:'Data bases'},
 resumo:{pt:'Catálogo de todas as bases que o sistema usa, com nome, origem, última atualização, volume e o que cada uma mede e não mede.',
         en:'Catalogue of every data base the system uses, with name, origin, last update, volume and what each one measures and does not.'},
 mede:[
  {pt:'Procedência e cobertura das bases, não os dados em si.',en:'Provenance and coverage of the bases, not the data itself.'}],
 fontes:[
  {pt:'Os próprios pacotes gerados (data de <code>built_on</code>) e os arquivos brutos do repositório (data do último commit que os tocou).',
   en:'The generated packets themselves (<code>built_on</code> date) and the raw files in the repository (date of the last commit that touched them).'}],
 calculo:[
  {pt:'Nenhuma data é digitada; volume e período são contados abrindo o arquivo. Se uma base sumir, a linha some com ela.',
   en:'No date is typed; volume and period are counted by opening the file. If a base disappears, its row disappears with it.'},
  {pt:'Base consolidada do Squad 1: pipeline <code>rodar_pipeline.py</code> com 18 etapas, cada valor rastreável até arquivo, linha e coluna de origem (aba 08) e validações automáticas na aba 14b.',
   en:'Squad 1 consolidated base: <code>rodar_pipeline.py</code> pipeline with 18 steps, each value traceable to source file, row and column (tab 08) and automatic checks in tab 14b.'}],
 limites:[
  {pt:'Cada base declara o que não mede: a CCEE não mede consumo da mineração, a CFEM não mede produção, o Anuário não mede produção por empresa, a base de produção das empresas não é auditada.',
   en:'Each base states what it does not measure: CCEE does not measure mining consumption, CFEM does not measure production, the Yearbook does not measure production by company, the company production base is not audited.'}],
 refazer:[
  {pt:'<code>python scripts/build_catalogo_painel.py</code>; base consolidada com <code>python base_consolidada_work/scripts/rodar_pipeline.py</code> (pasta <code>Squad 1/Bases consolidadas</code>).',
   en:'<code>python scripts/build_catalogo_painel.py</code>; consolidated base with <code>python base_consolidada_work/scripts/rodar_pipeline.py</code> (folder <code>Squad 1/Bases consolidadas</code>).'},
  {pt:'Os testes acusam quando o catálogo deixa de bater com o pacote que descreve; <code>tests/test_dados_corrigidos.py</code> e <code>tests/test_derivados.py</code> guardam as bases corrigidas e os derivados.',
   en:'Tests fail when the catalogue stops matching the packet it describes; <code>tests/test_dados_corrigidos.py</code> and <code>tests/test_derivados.py</code> guard the corrected bases and derived data.'}],
 docs:['Squad 1/Bases consolidadas/LEIA-ME.md','Squad 1/Dados brutos/LEIA-ME.md']},

{id:'territorio',view:'territorio',
 nome:{pt:'Território e emissões',en:'Land and emissions'},
 resumo:{pt:'Relatório do Squad 2 "Mineração e Cerrado em Goiás": área minerada de 1985 a 2025, emissões, efeito no entorno, cenários e risco por projeto. A aba Território tem a sub-aba Método completa.',
         en:'Squad 2 report "Mining and the Cerrado in Goiás": mined area 1985–2025, emissions, effect on the surroundings, scenarios and risk by project. The Land tab has the full Method sub-tab.'},
 mede:[
  {pt:'Área minerada e o uso anterior de cada pixel que vira mina; emissões de biomassa e de solo; efeito da abertura de minas na vegetação do entorno; impacto potencial de projetos novos.',
   en:'Mined area and the previous use of each pixel that becomes a mine; biomass and soil emissions; effect of mine openings on surrounding vegetation; potential impact of new projects.'}],
 fontes:[
  {pt:'MapBiomas Coleção 11 (cobertura, desmatamento, vegetação secundária, substância), MapBiomas Solo Coleção 2, SEEG 12, ANM (SIGMINE, Cadastro Mineiro, Anuário), P3M do SGB e Radar de Projetos do Squad 1.',
   en:'MapBiomas Collection 11 (cover, deforestation, secondary vegetation, substance), MapBiomas Soil Collection 2, SEEG 12, ANM (SIGMINE, Mining Register, Yearbook), SGB P3M and the Squad 1 Project Radar.'}],
 calculo:[
  {pt:'Área = classe Mineração do MapBiomas; onde ela não é usada (Catalão e Ouvidor), área dos títulos da ANM.',
   en:'Area = MapBiomas Mining class; where it is not used (Catalão and Ouvidor), the area of ANM titles.'},
  {pt:'Emissões pelos estoques de carbono do SEEG para Goiás; entorno por estudo de evento (40 minas abertas entre 1991 e 2015 contra títulos sem mina, pareados pela vegetação 6 e 11 anos antes), com 300 placebos por permutação.',
   en:'Emissions from SEEG carbon stocks for Goiás; surroundings by event study (40 mines opened 1991–2015 against titles without a mine, matched on vegetation 6 and 11 years before), with 300 permutation placebos.'},
  {pt:'Risco = nível de impacto (quartis) cruzado com a probabilidade dada pela maturidade do projeto.',
   en:'Risk = impact level (quartiles) crossed with the probability given by the project\'s maturity.'}],
 limites:[
  {pt:'Minas subterrâneas e dragagem quase não aparecem no satélite; o efeito no entorno vem de minas pequenas e médias e aplicá-lo a projetos grandes é extrapolação.',
   en:'Underground mines and dredging barely show in satellite data; the surroundings effect comes from small and medium mines, so applying it to large projects is extrapolation.'},
  {pt:'A vegetação em volta dos projetos foi interpolada de pontos amostrais; o carbono do solo assume que todo o carbono removido é emitido.',
   en:'Vegetation around projects was interpolated from sample points; soil carbon assumes all removed carbon is emitted.'}],
 refazer:[
  {pt:'Arquivos entregues pelo Squad 2 em <code>Squad 2/mineracao_cerrado/</code>, servidos por <code>Squad 3/backend/territorio.py</code>; a aba só conta e filtra.',
   en:'Files delivered by Squad 2 in <code>Squad 2/mineracao_cerrado/</code>, served by <code>Squad 3/backend/territorio.py</code>; the tab only counts and filters.'},
  {pt:'<code>tests/test_territorio.py</code>.',en:'<code>tests/test_territorio.py</code>.'}],
 docs:['METODOLOGIA.md']}
];

let built=false;

function tabs(){
  return PRODUTOS.map(p=>`<button type="button" role="tab" class="pn-tab" data-mt="${p.id}" aria-selected="false">${E(L(p.nome))}</button>`).join('');
}

function render(id){
  const p=PRODUTOS.find(x=>x.id===id)||PRODUTOS[0];
  el('mt-tabs').querySelectorAll('[data-mt]').forEach(b=>{const on=b.dataset.mt===p.id;b.classList.toggle('active',on);b.setAttribute('aria-selected',String(on))});
  const ir=p.view?`<button type="button" class="btn outline" data-goto="${p.view}">${E(t('mt.abrir'))}</button>`:'';
  const blocos=BLOCOS.filter(([k])=>p[k]&&p[k].length).map(([k,titulo])=>
    `<article class="panel mt-bloco mt-${k}"><h3>${E(L(titulo))}</h3><ul>${p[k].map(x=>`<li>${R(x)}</li>`).join('')}</ul></article>`).join('');
  const docs=(p.docs||[]).map(d=>`<a href="${E(REPO+encodeURI(d))}" target="_blank" rel="noopener">${E(d)} ↗</a>`).join(' · ');
  el('mt-content').innerHTML=
    `<div class="notice mt-resumo"><b>${E(L(p.nome))}.</b> ${R(p.resumo)} ${ir}</div>`+
    `<div class="mt-grid">${blocos}</div>`+
    (docs?`<p class="source-line">${E(t('mt.docs'))} ${docs}</p>`:'');
  el('mt-content').querySelectorAll('[data-goto]').forEach(b=>b.onclick=()=>{
    const nav=document.querySelector(`.sidebar [data-view="${b.dataset.goto}"]`);if(nav)nav.click();
  });
  try{localStorage.setItem(STORAGE,p.id)}catch{}
}

window.showMetodologia=()=>{
  if(built)return;built=true;
  el('mt-tabs').innerHTML=tabs();
  el('mt-tabs').querySelectorAll('[data-mt]').forEach(b=>b.onclick=()=>render(b.dataset.mt));
  let first=PRODUTOS[0].id;
  try{const s=localStorage.getItem(STORAGE);if(PRODUTOS.some(p=>p.id===s))first=s}catch{}
  render(first);
};
window.MetodologiaProdutos=PRODUTOS;
})();
