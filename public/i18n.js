/* Bilingual UI layer for the Minera Goias portal. Static dictionaries only: no user
   or database content is ever routed through t(), so values stay safe to inject. */
(()=>{'use strict';
const SUPPORTED=['pt','en'],STORAGE='minera-lang';
const DICT={pt:{
'lang.label':'Idioma','lang.pt':'PT','lang.en':'EN','lang.aria':'Selecionar idioma',
'brand.tagline':'Mineração · Energia · Território','brand.platform':'Plataforma de dados','brand.home':'Minera Goiás, início',
'title.index':'Minera Goiás | Mineração, energia e território','title.login':'Entrar | Minera Goiás','title.painel':'Painel de dados | Minera Goiás',
'meta.description':'Portal de acompanhamento de dados, indicadores, mapas e fontes de mineração e energia em Goiás.',
'nav.main':'Menu principal','nav.scope':'Escopo do portal','nav.indicators':'Indicadores e consultas','nav.sources':'Fontes','nav.access':'Acessar plataforma',
'hero.eyebrow':'Gestão de informações · Minera Goiás',
'hero.title':'Mineração e energia.<br>Dados do território.<br><em>Acompanhamento integrado.</em>',
'hero.lead':'Portal de consulta e acompanhamento das bases de mineração e energia de Goiás. Reúne indicadores, mapas, fontes e registros de qualidade para uso da equipe do projeto.',
'hero.cta1':'Acessar os indicadores','hero.cta2':'Escopo do portal','hero.foot1':'GOIÁS, BRASIL','hero.foot2':'INDICADORES · MAPAS · FONTES',
'terrain.aria':'Ilustração abstrata de relevo e conexões de dados','terrain.coord':'16°40′ S   49°15′ O   /   GOIÁS',
'terrain.svgtitle':'Território conectado — ilustração conceitual','terrain.energy':'ENERGIA','terrain.mining':'MINERAÇÃO',
'terrain.label':'VISÃO TERRITORIAL DO PROJETO','terrain.labelb':'Mineração, energia e cobertura das bases.',
'stats.aria':'Acervo importado','stats.files':'arquivos de origem importados','stats.datasets':'abas e tabelas catalogadas',
'stats.records':'linhas de dados no acervo','stats.scope':'abrangência territorial','stats.note':'Fontes em processo de validação','stats.unavailable':'Indisponível',
'scope.eyebrow':'Escopo do portal','scope.title':'Consulta, acompanhamento<br>e rastreabilidade.',
'scope.lead':'O portal organiza as bases disponíveis e permite acompanhar sua cobertura, distribuição territorial e situação de validação. Cada consulta identifica a fonte utilizada.',
'card1.num':'01 / TERRITÓRIO','card1.title':'Consulta territorial','card1.text':'Consulte os municípios, os polígonos de processos minerários e as barragens. Selecione camadas de CFEM, quantidade comercializada e energia.','card1.link':'Abrir atlas mineral   ↗',
'card2.num':'02 / ENERGIA','card2.title':'Indicadores e séries','card2.text':'Consulte séries temporais e a cobertura dos registros da CCEE. Os filtros permitem selecionar ano e ramo de atividade para análise.','card2.link':'Consultar indicadores   ↗',
'card3.num':'03 / CONFIANÇA','card3.title':'Qualidade e origem','card3.text':'Consulte o catálogo de arquivos e abas, os registros importados e os alertas de qualidade das fontes.','card3.link':'Consultar o acervo   ↗',
'intel.eyebrow':'Indicadores e consultas','intel.title':'Ambiente de consulta<br>para a equipe do projeto.',
'intel.lead':'O acesso autenticado reúne o painel do banco, o atlas mineral e o catálogo de fontes. Administradores também gerenciam as contas da equipe.',
'intel.li1':'Indicadores e mapas com filtros de consulta','intel.li2':'Rastreabilidade até o arquivo de origem','intel.li3':'Acesso individual para a equipe do projeto',
'intel.cta':'Abrir o painel de dados   ↗',
'preview.head':'Do acervo à visualização','preview.tag':'COMO FUNCIONA','preview.svgtitle':'Diagrama: fontes organizadas, filtros e visualizações',
'preview.ccee':'CCEE','preview.mineral':'Bases minerais','preview.sheets':'Bases de dados','preview.collection':'Acervo','preview.traceable':'rastreável','preview.panel':'Painel',
'preview.note':'O painel CCEE consulta as versões importadas no banco. O atlas utiliza os dados do artefato recebido, com períodos e limitações identificados.',
'srcs.eyebrow':'Fontes e método','srcs.title':'Referências e situação das bases.',
'srcs.lead':'Arquivos originais são preservados e alterações mantêm histórico. A importação não substitui a validação técnica das bases.',
'cta.title':'Acesso ao ambiente de gestão','cta.text':'Consulte indicadores, mapas e fontes do projeto.','cta.button':'Acessar o portal   ↗',
'footer.identity':'Identidade própria do projeto Minera Goiás.','footer.repo':'Repositório do projeto ↗',
'login.back':'← Voltar ao início','login.arteyebrow':'Conhecimento conectado','login.arttitle':'Uma nova perspectiva<br>sobre os dados<br>de Goiás.',
'login.artlead':'Explore informações, conheça as fontes e acompanhe a evolução do acervo do projeto.','login.artfoot':'MINERA GOIÁS / PLATAFORMA DE DADOS',
'login.eyebrow':'Área de acesso','login.title':'Bem-vindo ao Minera Goiás.','login.desc':'Entre com sua conta para explorar o painel de dados.',
'login.user':'Usuário','login.userph':'Seu usuário','login.pass':'Senha','login.passph':'Sua senha','login.show':'Mostrar','login.hide':'Ocultar',
'login.submit':'Entrar na plataforma   ↗','login.current':'Senha atual','login.new':'Nova senha · mínimo de 12 caracteres','login.confirm':'Confirme a nova senha','login.save':'Salvar nova senha',
'login.note':'O acesso é individual. Para solicitar uma conta ou recuperar o acesso, procure o administrador do projeto.',
'login.setTitle':'Defina sua senha.','login.setDesc':'Escolha uma senha pessoal para proteger seu acesso.',
'login.updatedTitle':'Senha atualizada.','login.updatedDesc':'Entre novamente com sua nova senha.','login.mismatch':'As senhas não coincidem.',
'app.loading':'Carregando seu ambiente…','app.loadingUser':'Carregando','app.logout':'Sair ↗','app.nav':'Navegação do painel','app.env':'AMBIENTE DE PESQUISA',
'nav.overview':'Visão geral','nav.atlas':'Atlas mineral','nav.sourcescat':'Catálogo de fontes','nav.admin':'Gerenciar acessos','nav.changepw':'Alterar minha senha',
'app.footer':'MINERA GOIÁS<br>Dados com origem.<br>Conhecimento em construção.','role.admin':'Administrador','role.user':'Usuário',
'ov.eyebrow':'Energia e território','ov.title':'Visão geral dos dados','ov.lead':'Explore a cobertura das parcelas de carga da CCEE em Goiás.','ov.tag':'BASE IMPORTADA',
'ov.year':'Ano da fonte','ov.activity':'Ramo de atividade','ov.allActivities':'Todas as atividades','ov.apply':'Aplicar filtros ↗','ov.export':'Exportar resumo ↓',
'ov.mRecords':'Registros no recorte','ov.mRecordsSub':'Linhas da fonte selecionada','ov.mCities':'Municípios representados','ov.mCitiesSub':'Na seleção atual',
'ov.mMonths':'Meses com registros','ov.mMonthsSub':'Cobertura da fonte','ov.mFiles':'Arquivos no acervo','ov.mFilesSub':'Total geral · todos os filtros',
'ov.chart1':'Cobertura ao longo do ano','ov.chart1sub':'Registros por mês de referência','ov.tableToggle':'Ver valores em tabela',
'ov.chart2':'Municípios com mais registros','ov.chart2sub':'10 maiores contagens · pode haver várias parcelas por município',
'ov.chart3':'Distribuição por ramo de atividade','ov.chart3sub':'8 maiores contagens na seleção',
'ov.thMonth':'Mês','ov.thRecords':'Registros','ov.empty':'Nenhum registro para este recorte.','ov.chartAria':'Registros mensais da CCEE. Valores disponíveis na tabela abaixo.',
'ov.sourcePrefix':'Fonte: ','ov.sourceSuffix':' · Versão atual importada no banco. Uma linha representa um registro, não uma empresa única.',
'ov.exportFirst':'Carregue os dados antes de exportar.','ov.csvAll':'Todas',
'ov.csvSource':'fonte','ov.csvYear':'ano','ov.csvActivity':'atividade','ov.csvMonth':'mes','ov.csvRecords':'registros','ov.csvName':'minera-goias-ccee-{year}-resumo.csv',
'at.eyebrow':'Mineração · Energia · Território','at.title':'Atlas mineral de Goiás','at.lead':'Explore municípios, processos minerários e barragens em um mapa integrado.',
'at.tag':'ARTEFATO RECEBIDO · RETRATO',
'at.loading':'Preparando o atlas…','at.layer':'Camada temática','at.layer.cfem':'CFEM por município','at.layer.production':'Quantidade comercializada por mineral',
'at.layer.energy':'Energia da cadeia mineral','at.layer.coefficient':'Intensidade energética','at.layer.processes':'Polígonos dos processos minerários','at.layer.dams':'Barragens de mineração',
'at.period':'Período da CFEM','at.accum':'2022–2026 · acumulado','at.substance':'Substância','at.group':'Grupo de fase','at.allGroups':'Todos os grupos','at.reset':'Enquadrar Goiás ↗',
'at.mapAria':'Mapa interativo de Goiás','at.geoRef':'Geometrias de referência · Leaflet','at.readTerritory':'Leitura do território','at.selectMun':'Selecione um município',
'at.selectRecord':'Selecione um registro','at.detailHint':'Clique no mapa ou em uma linha da tabela para ver os detalhes.','at.legend':'Legenda',
'at.tableTitle':'Dados da camada','at.searchPh':'Buscar município, processo ou substância','at.searchAria':'Buscar no mapa e tabela','at.exportCut':'Exportar recorte ↓','at.more':'Mostrar mais 50 registros',
'at.seriesEyebrow':'Séries do artefato','at.seriesTitle':'Perspectivas de mineração e energia','at.indicator':'Indicador',
'at.series.cfem_years':'CFEM anual · R$ milhões','at.series.cfem_comparable':'CFEM janeiro–julho · R$ milhões','at.series.energy_months':'Energia mensal · GWh',
'at.series.beneficiated':'Produção beneficiada · R$ bilhões','at.series.investment':'Pesquisa mineral · R$ milhões','at.seriesTableToggle':'Consultar valores da série',
'at.footSources':'Fontes declaradas no artefato: ANM/CFEM, Anuário Mineral Brasileiro, Cadastro Mineiro, SIGBM e CCEE. Mapas convertidos da projeção e quantização originais; limites não cadastrais. Dados demonstrativos e cenários fictícios não foram importados.',
'at.noRecord':'Sem registro','at.notInformed':'Não informado','at.leafletFail':'Não foi possível carregar o Leaflet. Atualize a página.',
'at.tileFail':'Mapa-base indisponível. Os limites e dados locais continuam disponíveis.','at.loadingPolys':'Carregando polígonos…',
'at.quantileNote':'Cores por faixas de quantis dos valores positivos. Cinza: sem registro ou valor zero.',
'at.processNote':'Processo minerário não equivale a mina em operação. Áreas podem se sobrepor. Geometria quantizada do artefato.',
'at.damNote':'Risco, dano potencial e nível de emergência são classificações distintas. Não consultar este retrato para avaliar condições atuais.',
'at.cfemYearNote':'O artefato só detalha 8 municípios por ano. Cinza indica ausência de detalhamento, não arrecadação zero. O acumulado cobre os 246 municípios.',
'at.ibge':'Código IBGE','at.process':'Processo','at.phase':'Fase','at.areaDeclared':'Área declarada','at.extractDate':'Data da extração','at.notInArtefact':'Não informada no artefato',
'at.polyContext':'{n} polígonos de processos · retrato do cadastro','at.radarTitle':'Radar de processos minerários','at.processLabel':'Processo {id}',
'at.riskHigh':'Risco alto (na extração)','at.riskMed':'Risco médio (na extração)','at.riskLow':'Risco baixo (na extração)',
'at.damsContext':'23 barragens · classificação do arquivo recebido','at.damsTitle':'Barragens no artefato','at.thDam':'Barragem','at.thMun':'Município',
'at.thRisk':'Risco na extração','at.thDamage':'Dano potencial','at.emergency':'Emergência na extração','at.operation':'Operação na extração','at.refDate':'Data de referência',
'at.cfemCollected':'CFEM arrecadada','at.periodField':'Período','at.accumShort':'2022–jul/2026','at.janJul2026':'Janeiro–julho de 2026','at.noYearDetail':'Sem detalhamento anual no artefato',
'at.qtySold':'Quantidade comercializada','at.cfem':'CFEM','at.companies':'Empresas declaradas','at.energyChain':'Energia da cadeia mineral','at.artefactClass':'Classificação do artefato',
'at.coefficient':'Coeficiente','at.notComparable':'Não comparável ou sem registro','at.limitLabel':'Limite','at.limitNote':'Razão municipal do artefato; não é intensidade validada por operação',
'at.munIndicators':'Indicadores por município','at.thValue':'Valor','at.thRefClass':'Referência / classe','at.thSubstance':'Substância','at.thArea':'Área declarada',
'at.recordsHint':'{n} registros · clique em uma linha para localizar no mapa','at.noneInCut':'Nenhum registro no recorte.','at.locate':'Localizar {name}',
'at.unitGold':'kg de ouro','at.unitTons':'t comercializadas','at.from':'A partir de','at.noneZero':'Sem registro / zero','at.cfemPrefix':'CFEM · ',
'at.onlyEight':' · somente 8 municípios detalhados na fonte','at.ref2025':'Referência 2025 · ','at.chartAria':'{title}. Valores disponíveis na tabela abaixo.',
'at.csvSource':'Fonte','at.csvArtefact':'Artefato recebido','at.csvLayer':'Camada','at.csvRef':'Referência','at.thPeriod':'Período',
'at.s.cfem_years.title':'CFEM arrecadada por ano','at.s.cfem_years.note':'2026 cobre apenas janeiro–julho. Use a série comparável para avaliar o mesmo período.','at.s.cfem_years.unit':'R$ milhões',
'at.s.cfem_comparable.title':'CFEM de janeiro a julho','at.s.cfem_comparable.note':'Mesmo recorte de meses em todos os anos; valores do artefato.','at.s.cfem_comparable.unit':'R$ milhões',
'at.s.energy_months.title':'Energia mensal de empresas com título minerário','at.s.energy_months.note':'Universo definido no artefato. 2024 começa em abril; 2026 termina em junho. Não misturar com a base da visão geral.','at.s.energy_months.unit':'GWh',
'at.s.beneficiated.title':'Valor da produção beneficiada','at.s.beneficiated.note':'Valor de venda nominal; série recebida, sem correção monetária.','at.s.beneficiated.unit':'R$ bilhões',
'at.s.investment.title':'Investimento declarado em pesquisa mineral','at.s.investment.note':'Série nominal recebida, sem correção monetária.','at.s.investment.unit':'R$ milhões',
'sv.eyebrow':'Rastreabilidade','sv.title':'Catálogo de fontes','sv.lead':'Abas e tabelas das versões atuais do acervo. Independente dos filtros da CCEE.',
'sv.notice':'Bases originais e corrigidas podem se sobrepor. A soma das linhas do acervo não equivale a observações independentes. Alertas indicam pontos para revisão técnica.',
'sv.search':'Buscar arquivo ou aba','sv.searchPh':'Ex.: CCEE, CFEM ou nome da planilha','sv.thFile':'Arquivo de origem','sv.thSheet':'Aba / tabela',
'sv.thRows':'Linhas de dados','sv.thQuality':'Qualidade','sv.count':'{n} abas/tabelas encontradas','sv.alerts':'{n} tipos de alerta','sv.noAlert':'Sem alerta do importador',
'ad.eyebrow':'Administração','ad.title':'Gerenciar acessos','ad.lead':'Contas individuais e permissões da plataforma.',
'ad.notice':'Administradores gerenciam acessos. Usuários consultam gráficos, catálogo e exportam resumos. Novas contas precisam alterar a senha inicial.',
'ad.accounts':'Contas da equipe','ad.thPerson':'Pessoa','ad.thProfile':'Perfil','ad.thAccess':'Acesso','ad.thAction':'Ação','ad.create':'Criar acesso',
'ad.name':'Nome','ad.user':'Usuário','ad.userPh':'letras minúsculas, números, ponto ou hífen','ad.role':'Perfil','ad.roleUser':'Usuário · consulta',
'ad.roleAdmin':'Administrador · gestão de acessos','ad.initialPw':'Senha inicial · mínimo de 12 caracteres','ad.submit':'Criar conta',
'ad.active':'Ativo','ad.inactive':'Desativado','ad.yourAccount':'Sua conta','ad.disable':'Desativar','ad.enable':'Reativar',
'ad.created':'Conta criada. Entregue a senha inicial diretamente à pessoa.',
'c.sessionEnded':'Sessão encerrada.','at.municipality':'Município','at.selectMunicipality':'— Selecione o município —',
'mun.eyebrow':'Perfil do município','mun.clear':'Limpar seleção','mun.subsTitle':'Substâncias declaradas · 2025',
'mun.subsNote':'Quantidade comercializada e CFEM do artefato, por substância.','mun.damsTitle':'Barragens no município',
'mun.damsNote':'Classificação registrada no artefato recebido.','mun.evoTitle':'Evolução ao longo do tempo',
'mun.tag':'IBGE {code}','mun.processes':'Processos minerários','mun.processesSub':'Polígonos no cadastro',
'mun.cfemTotal':'CFEM acumulada','mun.cfemTotalSub':'2022–julho/2026','mun.share':'Participação no estado',
'mun.shareSub':'Da CFEM acumulada de Goiás','mun.production':'Quantidade comercializada · 2025',
'mun.productionSub':'Soma das substâncias declaradas','mun.energy':'Energia · 2025','mun.energySub':'Cadeia mineral no artefato',
'mun.cfemYear':'CFEM em {year}','mun.noSubs':'Sem substâncias declaradas no artefato para 2025.',
'mun.noDams':'Nenhuma barragem registrada neste município.','mun.thSub':'Substância','mun.thQty':'Quantidade',
'mun.thCfem':'CFEM','mun.thCompanies':'Empresas','mun.damRisk':'Risco: {risk} · dano potencial: {damage}',
'mun.evoAvailable':'CFEM arrecadada por ano, em R$ milhões. 2026 cobre janeiro a julho.',
'mun.evoMissing':'O artefato detalha a CFEM ano a ano apenas para oito municípios. Para {name} há somente o valor acumulado de 2022 a julho de 2026.',
'mun.evoUnit':'R$ milhões','mun.hint':'Selecione um município na lista ou clique no mapa.',
'mun.classe':'Classificação do artefato','mun.mainSub':'Substância principal',
'c.failed':'Não foi possível concluir. Confira os campos.','c.checkFields':'Confira os campos informados.'
},en:{
'lang.label':'Language','lang.pt':'PT','lang.en':'EN','lang.aria':'Select language',
'brand.tagline':'Mining · Energy · Territory','brand.platform':'Data platform','brand.home':'Minera Goiás, home',
'title.index':'Minera Goiás | Mining, energy and territory','title.login':'Sign in | Minera Goiás','title.painel':'Data dashboard | Minera Goiás',
'meta.description':'Portal for tracking data, indicators, maps and sources on mining and energy in Goiás, Brazil.',
'nav.main':'Main menu','nav.scope':'Portal scope','nav.indicators':'Indicators and queries','nav.sources':'Sources','nav.access':'Access the platform',
'hero.eyebrow':'Information management · Minera Goiás',
'hero.title':'Mining and energy.<br>Data from the territory.<br><em>Integrated tracking.</em>',
'hero.lead':'Portal for consulting and tracking the mining and energy datasets of Goiás. It brings together indicators, maps, sources and quality records for the project team.',
'hero.cta1':'Open the indicators','hero.cta2':'Portal scope','hero.foot1':'GOIÁS, BRAZIL','hero.foot2':'INDICATORS · MAPS · SOURCES',
'terrain.aria':'Abstract illustration of terrain and data connections','terrain.coord':'16°40′ S   49°15′ W   /   GOIÁS',
'terrain.svgtitle':'Connected territory — conceptual illustration','terrain.energy':'ENERGY','terrain.mining':'MINING',
'terrain.label':'TERRITORIAL VIEW OF THE PROJECT','terrain.labelb':'Mining, energy and dataset coverage.',
'stats.aria':'Imported collection','stats.files':'source files imported','stats.datasets':'sheets and tables catalogued',
'stats.records':'data rows in the collection','stats.scope':'territorial coverage','stats.note':'Sources still under validation','stats.unavailable':'Unavailable',
'scope.eyebrow':'Portal scope','scope.title':'Consultation, tracking<br>and traceability.',
'scope.lead':'The portal organises the available datasets and lets you follow their coverage, territorial distribution and validation status. Every query identifies the source it used.',
'card1.num':'01 / TERRITORY','card1.title':'Territorial consultation','card1.text':'Browse municipalities, mining claim polygons and tailings dams. Switch between CFEM royalties, quantity sold and energy layers.','card1.link':'Open the mineral atlas   ↗',
'card2.num':'02 / ENERGY','card2.title':'Indicators and series','card2.text':'Consult time series and the coverage of CCEE load records. Filters let you select the year and activity sector for analysis.','card2.link':'Open the indicators   ↗',
'card3.num':'03 / TRUST','card3.title':'Quality and provenance','card3.text':'Consult the catalogue of files and sheets, the imported records and the quality alerts raised for each source.','card3.link':'Browse the collection   ↗',
'intel.eyebrow':'Indicators and queries','intel.title':'A consultation workspace<br>for the project team.',
'intel.lead':'Authenticated access brings together the database dashboard, the mineral atlas and the source catalogue. Administrators also manage the team accounts.',
'intel.li1':'Indicators and maps with query filters','intel.li2':'Traceability down to the source file','intel.li3':'Individual access for the project team',
'intel.cta':'Open the data dashboard   ↗',
'preview.head':'From collection to visualisation','preview.tag':'HOW IT WORKS','preview.svgtitle':'Diagram: organised sources, filters and visualisations',
'preview.ccee':'CCEE','preview.mineral':'Mineral datasets','preview.sheets':'Databases','preview.collection':'Traceable','preview.traceable':'collection','preview.panel':'Dashboard',
'preview.note':'The CCEE dashboard queries the versions imported into the database. The atlas uses the artefact received, with its periods and limitations stated.',
'srcs.eyebrow':'Sources and method','srcs.title':'References and dataset status.',
'srcs.lead':'Original files are preserved and every change keeps its history. Importing does not replace technical validation of the datasets.',
'cta.title':'Access the management workspace','cta.text':'Consult the project indicators, maps and sources.','cta.button':'Open the portal   ↗',
'footer.identity':'Independent visual identity of the Minera Goiás project.','footer.repo':'Project repository ↗',
'login.back':'← Back to home','login.arteyebrow':'Connected knowledge','login.arttitle':'A new perspective<br>on the data<br>of Goiás.',
'login.artlead':'Explore the information, get to know the sources and follow how the collection evolves.','login.artfoot':'MINERA GOIÁS / DATA PLATFORM',
'login.eyebrow':'Access area','login.title':'Welcome to Minera Goiás.','login.desc':'Sign in with your account to explore the data dashboard.',
'login.user':'Username','login.userph':'Your username','login.pass':'Password','login.passph':'Your password','login.show':'Show','login.hide':'Hide',
'login.submit':'Sign in   ↗','login.current':'Current password','login.new':'New password · at least 12 characters','login.confirm':'Confirm the new password','login.save':'Save new password',
'login.note':'Access is individual. To request an account or recover access, contact the project administrator.',
'login.setTitle':'Set your password.','login.setDesc':'Choose a personal password to protect your access.',
'login.updatedTitle':'Password updated.','login.updatedDesc':'Sign in again with your new password.','login.mismatch':'The passwords do not match.',
'app.loading':'Loading your workspace…','app.loadingUser':'Loading','app.logout':'Sign out ↗','app.nav':'Dashboard navigation','app.env':'RESEARCH WORKSPACE',
'nav.overview':'Overview','nav.atlas':'Mineral atlas','nav.sourcescat':'Source catalogue','nav.admin':'Manage access','nav.changepw':'Change my password',
'app.footer':'MINERA GOIÁS<br>Data with provenance.<br>Knowledge under construction.','role.admin':'Administrator','role.user':'User',
'ov.eyebrow':'Energy and territory','ov.title':'Data overview','ov.lead':'Explore the coverage of CCEE load records in Goiás.','ov.tag':'IMPORTED DATASET',
'ov.year':'Source year','ov.activity':'Activity sector','ov.allActivities':'All sectors','ov.apply':'Apply filters ↗','ov.export':'Export summary ↓',
'ov.mRecords':'Records in selection','ov.mRecordsSub':'Rows from the selected source','ov.mCities':'Municipalities represented','ov.mCitiesSub':'In the current selection',
'ov.mMonths':'Months with records','ov.mMonthsSub':'Source coverage','ov.mFiles':'Files in the collection','ov.mFilesSub':'Overall total · all filters',
'ov.chart1':'Coverage across the year','ov.chart1sub':'Records per reference month','ov.tableToggle':'View the values as a table',
'ov.chart2':'Municipalities with the most records','ov.chart2sub':'10 largest counts · a municipality may hold several load parcels',
'ov.chart3':'Distribution by activity sector','ov.chart3sub':'8 largest counts in the selection',
'ov.thMonth':'Month','ov.thRecords':'Records','ov.empty':'No records for this selection.','ov.chartAria':'Monthly CCEE records. Values available in the table below.',
'ov.sourcePrefix':'Source: ','ov.sourceSuffix':' · Current version imported into the database. One row is one record, not one distinct company.',
'ov.exportFirst':'Load the data before exporting.','ov.csvAll':'All',
'ov.csvSource':'source','ov.csvYear':'year','ov.csvActivity':'sector','ov.csvMonth':'month','ov.csvRecords':'records','ov.csvName':'minera-goias-ccee-{year}-summary.csv',
'at.eyebrow':'Mining · Energy · Territory','at.title':'Mineral atlas of Goiás','at.lead':'Explore municipalities, mining claims and tailings dams on one integrated map.',
'at.tag':'ARTEFACT RECEIVED · SNAPSHOT',
'at.loading':'Preparing the atlas…','at.layer':'Thematic layer','at.layer.cfem':'CFEM royalties by municipality','at.layer.production':'Quantity sold by mineral',
'at.layer.energy':'Mineral chain energy','at.layer.coefficient':'Energy intensity','at.layer.processes':'Mining claim polygons','at.layer.dams':'Mining tailings dams',
'at.period':'CFEM period','at.accum':'2022–2026 · cumulative','at.substance':'Substance','at.group':'Phase group','at.allGroups':'All groups','at.reset':'Fit Goiás ↗',
'at.mapAria':'Interactive map of Goiás','at.geoRef':'Reference geometries · Leaflet','at.readTerritory':'Reading the territory','at.selectMun':'Select a municipality',
'at.selectRecord':'Select a record','at.detailHint':'Click the map or a table row to see the details.','at.legend':'Legend',
'at.tableTitle':'Layer data','at.searchPh':'Search municipality, claim or substance','at.searchAria':'Search the map and table','at.exportCut':'Export selection ↓','at.more':'Show 50 more records',
'at.seriesEyebrow':'Artefact series','at.seriesTitle':'Mining and energy perspectives','at.indicator':'Indicator',
'at.series.cfem_years':'CFEM per year · R$ millions','at.series.cfem_comparable':'CFEM January–July · R$ millions','at.series.energy_months':'Monthly energy · GWh',
'at.series.beneficiated':'Processed output · R$ billions','at.series.investment':'Mineral exploration · R$ millions','at.seriesTableToggle':'View the series values',
'at.footSources':'Sources declared in the artefact: ANM/CFEM, Brazilian Mineral Yearbook, Mining Register, SIGBM and CCEE. Maps converted from the original projection and quantisation; boundaries are not cadastral. Demonstration data and fictional scenarios were not imported.',
'at.noRecord':'No record','at.notInformed':'Not informed','at.leafletFail':'Leaflet could not be loaded. Please refresh the page.',
'at.tileFail':'Base map unavailable. Boundaries and local data remain available.','at.loadingPolys':'Loading polygons…',
'at.quantileNote':'Colours follow quantile bands of the positive values. Grey: no record or zero value.',
'at.processNote':'A mining claim is not the same as an operating mine. Areas may overlap. Geometry quantised from the artefact.',
'at.damNote':'Risk, potential damage and emergency level are distinct classifications. Do not use this snapshot to assess current conditions.',
'at.cfemYearNote':'The artefact details only 8 municipalities per year. Grey means no yearly detail, not zero collection. The cumulative view covers all 246 municipalities.',
'at.ibge':'IBGE code','at.process':'Claim','at.phase':'Phase','at.areaDeclared':'Declared area','at.extractDate':'Extraction date','at.notInArtefact':'Not stated in the artefact',
'at.polyContext':'{n} claim polygons · register snapshot','at.radarTitle':'Mining claim radar','at.processLabel':'Claim {id}',
'at.riskHigh':'High risk (at extraction)','at.riskMed':'Medium risk (at extraction)','at.riskLow':'Low risk (at extraction)',
'at.damsContext':'23 dams · classification from the file received','at.damsTitle':'Dams in the artefact','at.thDam':'Dam','at.thMun':'Municipality',
'at.thRisk':'Risk at extraction','at.thDamage':'Potential damage','at.emergency':'Emergency at extraction','at.operation':'Operation at extraction','at.refDate':'Reference date',
'at.cfemCollected':'CFEM collected','at.periodField':'Period','at.accumShort':'2022–Jul 2026','at.janJul2026':'January–July 2026','at.noYearDetail':'No yearly detail in the artefact',
'at.qtySold':'Quantity sold','at.cfem':'CFEM','at.companies':'Companies declared','at.energyChain':'Mineral chain energy','at.artefactClass':'Artefact classification',
'at.coefficient':'Coefficient','at.notComparable':'Not comparable or no record','at.limitLabel':'Limitation','at.limitNote':'Municipal ratio from the artefact; not an operation-validated intensity',
'at.munIndicators':'Indicators by municipality','at.thValue':'Value','at.thRefClass':'Reference / class','at.thSubstance':'Substance','at.thArea':'Declared area',
'at.recordsHint':'{n} records · click a row to locate it on the map','at.noneInCut':'No records in this selection.','at.locate':'Locate {name}',
'at.unitGold':'kg of gold','at.unitTons':'t sold','at.from':'From','at.noneZero':'No record / zero','at.cfemPrefix':'CFEM · ',
'at.onlyEight':' · only 8 municipalities detailed in the source','at.ref2025':'2025 reference · ','at.chartAria':'{title}. Values available in the table below.',
'at.csvSource':'Source','at.csvArtefact':'Artefact received','at.csvLayer':'Layer','at.csvRef':'Reference','at.thPeriod':'Period',
'at.s.cfem_years.title':'CFEM collected per year','at.s.cfem_years.note':'2026 covers January–July only. Use the comparable series to assess the same period.','at.s.cfem_years.unit':'R$ millions',
'at.s.cfem_comparable.title':'CFEM from January to July','at.s.cfem_comparable.note':'The same months in every year; values as received in the artefact.','at.s.cfem_comparable.unit':'R$ millions',
'at.s.energy_months.title':'Monthly energy of companies holding mining titles','at.s.energy_months.note':'Universe defined in the artefact. 2024 starts in April; 2026 ends in June. Do not mix with the overview dataset.','at.s.energy_months.unit':'GWh',
'at.s.beneficiated.title':'Value of processed output','at.s.beneficiated.note':'Nominal sales value; series as received, not inflation-adjusted.','at.s.beneficiated.unit':'R$ billions',
'at.s.investment.title':'Declared investment in mineral exploration','at.s.investment.note':'Nominal series as received, not inflation-adjusted.','at.s.investment.unit':'R$ millions',
'sv.eyebrow':'Traceability','sv.title':'Source catalogue','sv.lead':'Sheets and tables of the current versions in the collection. Independent of the CCEE filters.',
'sv.notice':'Original and corrected datasets may overlap. Summing the rows of the collection does not yield independent observations. Alerts point to items for technical review.',
'sv.search':'Search file or sheet','sv.searchPh':'e.g. CCEE, CFEM or a spreadsheet name','sv.thFile':'Source file','sv.thSheet':'Sheet / table',
'sv.thRows':'Data rows','sv.thQuality':'Quality','sv.count':'{n} sheets/tables found','sv.alerts':'{n} alert types','sv.noAlert':'No importer alert',
'ad.eyebrow':'Administration','ad.title':'Manage access','ad.lead':'Individual accounts and platform permissions.',
'ad.notice':'Administrators manage access. Users consult charts and the catalogue and export summaries. New accounts must change the initial password.',
'ad.accounts':'Team accounts','ad.thPerson':'Person','ad.thProfile':'Profile','ad.thAccess':'Access','ad.thAction':'Action','ad.create':'Create access',
'ad.name':'Name','ad.user':'Username','ad.userPh':'lowercase letters, digits, dot or hyphen','ad.role':'Profile','ad.roleUser':'User · read only',
'ad.roleAdmin':'Administrator · access management','ad.initialPw':'Initial password · at least 12 characters','ad.submit':'Create account',
'ad.active':'Active','ad.inactive':'Disabled','ad.yourAccount':'Your account','ad.disable':'Disable','ad.enable':'Re-enable',
'ad.created':'Account created. Hand the initial password to the person directly.',
'c.sessionEnded':'Session ended.','at.municipality':'Municipality','at.selectMunicipality':'— Select a municipality —',
'mun.eyebrow':'Municipality profile','mun.clear':'Clear selection','mun.subsTitle':'Substances declared · 2025',
'mun.subsNote':'Quantity sold and CFEM royalties from the artefact, by substance.','mun.damsTitle':'Dams in the municipality',
'mun.damsNote':'Classification as recorded in the artefact received.','mun.evoTitle':'Change over time',
'mun.tag':'IBGE {code}','mun.processes':'Mining claims','mun.processesSub':'Polygons in the register',
'mun.cfemTotal':'CFEM accumulated','mun.cfemTotalSub':'2022–July 2026','mun.share':'Share of the state',
'mun.shareSub':'Of the accumulated CFEM of Goiás','mun.production':'Quantity sold · 2025',
'mun.productionSub':'Sum of the declared substances','mun.energy':'Energy · 2025','mun.energySub':'Mineral chain in the artefact',
'mun.cfemYear':'CFEM in {year}','mun.noSubs':'No substances declared in the artefact for 2025.',
'mun.noDams':'No dam recorded in this municipality.','mun.thSub':'Substance','mun.thQty':'Quantity',
'mun.thCfem':'CFEM','mun.thCompanies':'Companies','mun.damRisk':'Risk: {risk} · potential damage: {damage}',
'mun.evoAvailable':'CFEM collected per year, in R$ millions. 2026 covers January to July.',
'mun.evoMissing':'The artefact details CFEM year by year for eight municipalities only. For {name} just the accumulated 2022–July 2026 value is available.',
'mun.evoUnit':'R$ millions','mun.hint':'Select a municipality from the list or click the map.',
'mun.classe':'Artefact classification','mun.mainSub':'Main substance',
'c.failed':'Could not complete the request. Check the fields.','c.checkFields':'Check the fields you entered.'
}};
function pick(){
  const asked=new URLSearchParams(location.search).get('lang');
  let saved=null;try{saved=localStorage.getItem(STORAGE)}catch{}
  const browser=(navigator.language||'pt').slice(0,2).toLowerCase();
  // A ?lang= link is a deliberate choice: keep it for the next page too.
  if(SUPPORTED.includes(asked)&&asked!==saved){try{localStorage.setItem(STORAGE,asked)}catch{}}
  return [asked,saved,browser].find(l=>SUPPORTED.includes(l))||'pt';
}
let lang=pick();
function t(key,vars){
  let text=DICT[lang][key];
  if(text==null)text=DICT.pt[key];
  if(text==null)return key;
  if(vars)for(const name of Object.keys(vars))text=text.split('{'+name+'}').join(vars[name]);
  return text;
}
const locale=()=>lang==='en'?'en-US':'pt-BR';
const num=(value,options)=>Number(value).toLocaleString(locale(),options);
function apply(root){
  const scope=root||document;
  scope.querySelectorAll('[data-i18n]').forEach(node=>{node.textContent=t(node.dataset.i18n)});
  // Dictionary values only; never user or database content.
  scope.querySelectorAll('[data-i18n-html]').forEach(node=>{node.innerHTML=t(node.dataset.i18nHtml)});
  scope.querySelectorAll('[data-i18n-attr]').forEach(node=>{
    for(const pair of node.dataset.i18nAttr.split(',')){
      const at=pair.indexOf(':');
      node.setAttribute(pair.slice(0,at).trim(),t(pair.slice(at+1).trim()));
    }
  });
  document.documentElement.lang=lang==='en'?'en':'pt-BR';
}
function set(next){
  if(!SUPPORTED.includes(next)||next===lang)return;
  try{localStorage.setItem(STORAGE,next)}catch{}
  const url=new URL(location.href);
  url.searchParams.delete('lang');
  // Reload so charts, tables and map labels are all rebuilt in the new language.
  location.replace(url.pathname+url.search+url.hash);
}
function markSwitch(){
  document.querySelectorAll('[data-lang]').forEach(button=>{
    button.classList.toggle('active',button.dataset.lang===lang);
    button.setAttribute('aria-pressed',String(button.dataset.lang===lang));
    button.onclick=()=>set(button.dataset.lang);
  });
}
window.I18N={t,num,locale,apply,set,keys:()=>Object.keys(DICT.pt),get lang(){return lang}};
window.t=t;
apply();markSwitch();
})();
