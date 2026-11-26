# Lista de pendências do MINERA Goiás

Frente 10 · Validação geral e implantação · atualizada em 26/11/2026

## Como usar esta lista

Esta lista reúne tudo o que a homologação do site encontrou para corrigir, desenvolver ou decidir. Ela é de todos: quem pegar uma pendência anota o nome no campo Responsável, e quem resolver atualiza o Status.

Cada pendência tem uma ficha com:

- **Onde:** a página, a aba ou a parte do sistema em que o problema aparece.
- **Tipo:** Problema (algo errado ou faltando no que já existe), A desenvolver (função que ainda não existe), Decisão do grupo (precisa de acordo antes de mexer) ou Sugestão.
- **Urgência:** Alta, Média ou Baixa, como foi avaliada na homologação. A única que bloqueia a entrega é a p12.
- **O que acontece:** o erro, descrito com o que se vê na tela e os valores certos quando há número envolvido.
- **Como foi conferido:** a página, o arquivo ou o teste que mostra o problema, com a data.
- **Situação em 25/11/2026:** o que se viu na 2ª rodada de avaliação.
- **Possibilidades de melhora:** ideias para começar a conversa. Não são decisões: o grupo pode escolher outra saída.

**Status:** toda pendência tem um Status, na ficha e na tabela da visão geral. Use sempre um destes:

- **Aberta:** ninguém está mexendo ainda.
- **Em andamento (nome):** alguém pegou e está trabalhando nela.
- **Resolvida em parte em dd/mm/aaaa:** parte foi corrigida; a ficha diz o que ainda falta.
- **Resolvida em dd/mm/aaaa:** está corrigida e conferida no site.

**Ao resolver uma pendência:** não mude nada de lugar. Risque o número e o título na tabela da visão geral e o título da ficha (no GitHub, o texto entre ~~ e ~~ aparece riscado), mude o Status nos dois lugares, anote o commit e acrescente na ficha "O que foi feito": o que mudou e em quais arquivos.

As avaliações foram feitas em 19/11/2026 (1ª rodada) e 25/11/2026 (2ª rodada), no site labfgv.com.br e numa cópia local com o código do commit 2906ce9.

## Visão geral

São 57 pendências: 40 abertas e 17 resolvidas (duas delas por decisão de não fazer: p38 e p56). Das abertas, 4 têm urgência alta, 20 média e 16 baixa, e 9 já estão resolvidas em parte (p10, p14, p23, p24, p30, p34, p46, p53 e p57). Por tipo: 27 problemas, 3 a desenvolver, 9 decisões do grupo e 1 sugestão. Só uma bloqueia a entrega: a p12, área das rodadas 100 vezes maior, porque mostra um número errado na tela. A p40 só se resolve no servidor, que a equipe não acessa: depende do professor.

| Nº | Pendência | Área | Tipo | Urgência | Status |
| --- | --- | --- | --- | --- | --- |
| p11 | Definir quem é o cliente e como vai usar a plataforma | Site como um todo | Decisão do grupo | Alta | Aberta |
| p25 | Cinco listas de 'projetos' diferentes no site | Site como um todo | Decisão do grupo | Alta | Aberta |
| p30 | Informação interna da equipe espalhada pelas abas | Site como um todo | Problema | Média | Resolvida em parte em 26/11/2026 |
| ~~p38~~ | ~~Nenhum link abre uma aba específica do painel~~ | Site como um todo | Problema | Média | Resolvida em 26/11/2026 (decidido não fazer) |
| p10 | Links do site para o GitHub | Site como um todo | Problema | Baixa | Resolvida em parte em 26/11/2026 |
| ~~p06~~ | ~~Página inicial não diz o que a plataforma faz~~ | Página inicial | Problema | Média | Resolvida em 26/11/2026 |
| p05 | Contadores de dados não informam nada | Página inicial | Problema | Baixa | Aberta |
| p07 | Juntar página inicial e login | Página inicial | Decisão do grupo | Baixa | Aberta |
| p12 | Área das rodadas de disponibilidade 100 vezes maior | Atlas e panorama | Problema | Alta | Aberta |
| ~~p01~~ | ~~Nas sub-abas Empresas e Notas o mapa some e o topo fica em branco~~ | Atlas e panorama | Problema | Média | Resolvida em 26/11/2026 |
| p03 | Alcance dos filtros não é visível | Atlas e panorama | Problema | Média | Aberta |
| p04 | Sem hierarquia clara entre as seções | Atlas e panorama | Problema | Média | Aberta |
| ~~p02~~ | ~~Sub-aba Notas é recado interno da equipe~~ | Atlas e panorama | Problema | Baixa | Resolvida em 26/11/2026 |
| p13 | Energia e barragens sem data na tela (Atlas e Mapa mineral) | Atlas e panorama | Problema | Baixa | Aberta |
| ~~p17~~ | ~~Fontes das 47 camadas do Mapa mineral fora da Base de dados~~ | Mapa mineral | Problema | Média | Resolvida em 26/11/2026 |
| p20 | Mapa mineral repete camadas do Atlas, com outro retrato do SIGMINE | Mapa mineral | Decisão do grupo | Média | Aberta |
| ~~p08~~ | ~~Documentação das bases fica no GitHub~~ | Base de dados | Problema | Média | Resolvida em 26/11/2026 |
| ~~p09~~ | ~~Sem botão de download das bases~~ | Base de dados | A desenvolver | Média | Resolvida em 26/11/2026 |
| p14 | IBGE não aparece na Base de dados; barragens sem fonte | Base de dados | Problema | Média | Resolvida em parte em 26/11/2026 |
| p34 | Cartões das bases não dizem onde a base é usada nem como é atualizada | Base de dados | A desenvolver | Média | Resolvida em parte em 26/11/2026 |
| ~~p36~~ | ~~Pasta do servidor exposta na Base de dados~~ | Base de dados | Problema | Média | Resolvida em 26/11/2026 |
| p35 | Base de dados em português na versão em inglês | Base de dados | Problema | Baixa | Aberta |
| p21 | Dados e páginas abertos sem login | Previsão de demanda e Simulador | Problema | Média | Aberta |
| p23 | Insumos da Previsão fora da Base de dados | Previsão de demanda e Simulador | Problema | Média | Resolvida em parte em 26/11/2026 |
| p39 | Simulador fora do padrão do site e sem inglês | Previsão de demanda e Simulador | Problema | Média | Aberta |
| p49 | Simulador mostra outro número ao trocar de cenário | Previsão de demanda e Simulador | Problema | Média | Aberta |
| p57 | Tabela 'Carteira ampliada' da Previsão com informação interna, sem inglês e com outra lista de projetos | Previsão de demanda e Simulador | Problema | Média | Resolvida em parte em 26/11/2026 |
| p22 | Notas em português na versão em inglês da Previsão | Previsão de demanda e Simulador | Problema | Baixa | Aberta |
| p24 | Instruções internas na Metodologia da Previsão | Previsão de demanda e Simulador | Problema | Baixa | Resolvida em parte em 26/11/2026 |
| p26 | Indicador '609 mil ha sob requerimento' não confere e não tem fonte | Mercado, Empresas e Comércio exterior | Problema | Média | Aberta |
| p27 | Operações sem data e sem fonte; notícia antiga em 'doze meses' | Mercado, Empresas e Comércio exterior | Problema | Baixa | Aberta |
| p28 | Carteira de projetos do Mercado em português na versão em inglês | Mercado, Empresas e Comércio exterior | Problema | Baixa | Aberta |
| ~~p29~~ | ~~Nomes de alunos e caminhos internos na tela do Mercado~~ | Mercado, Empresas e Comércio exterior | Problema | Baixa | Resolvida em 26/11/2026 |
| p52 | Empresas com valores em português na versão em inglês | Mercado, Empresas e Comércio exterior | Problema | Baixa | Aberta |
| p51 | Comércio exterior com texto em português na versão em inglês | Mercado, Empresas e Comércio exterior | Problema | Baixa | Aberta |
| p53 | Ranking por Indicador sem fonte, sem data e fora da Base de dados | Ranking por Indicador, Radar, Território e Metodologia | Problema | Média | Resolvida em parte em 26/11/2026 |
| ~~p37~~ | ~~Bases do Território fora da Base de dados~~ | Ranking por Indicador, Radar, Território e Metodologia | Problema | Média | Resolvida em 26/11/2026 |
| p50 | Metodologia com links para o GitHub e informação interna | Ranking por Indicador, Radar, Território e Metodologia | Problema | Média | Aberta |
| p54 | Indicadores por município em dois lugares | Ranking por Indicador, Radar, Território e Metodologia | Decisão do grupo | Baixa | Aberta |
| p31 | Rodadas e fases do Radar sem data do retrato | Ranking por Indicador, Radar, Território e Metodologia | Problema | Baixa | Aberta |
| p32 | Radar repete fases e rodadas do Panorama | Ranking por Indicador, Radar, Território e Metodologia | Decisão do grupo | Baixa | Aberta |
| ~~p56~~ | ~~Radar com textos explicativos em português na versão em inglês~~ | Ranking por Indicador, Radar, Território e Metodologia | Problema | Baixa | Resolvida em 26/11/2026 (decidido não fazer) |
| p55 | Metodologia repetida em três lugares | Ranking por Indicador, Radar, Território e Metodologia | Decisão do grupo | Baixa | Aberta |
| p44 | Não há como recuperar senha esquecida | Gerenciar acessos | A desenvolver | Média | Aberta |
| p45 | Conta genérica num sistema de 'contas individuais' | Gerenciar acessos | Decisão do grupo | Média | Aberta |
| p46 | Desativar sem confirmação e sem como excluir conta | Gerenciar acessos | Sugestão | Baixa | Resolvida em parte em 26/11/2026 |
| p41 | Rotas do banco devolvem lista vazia (a "API que não foi criada") | Servidor, API e robôs | Decisão do grupo | Alta | Aberta |
| p40 | Cabeçalhos de segurança ausentes e página 404 inexistente | Servidor, API e robôs | Problema | Média | Aberta |
| p42 | Robô mensal das bases falhou em 01/11 | Servidor, API e robôs | Problema | Média | Aberta |
| p47 | Nenhum robô avisa quando falha | Servidor, API e robôs | A desenvolver | Média | Aberta |
| p48 | Teste de troca de versão do site é fraco | Servidor, API e robôs | Problema | Média | Aberta |
| ~~p15~~ | ~~Aba sem descrição geral~~ | Resolvidas | Problema | Média | Resolvida em 19/11/2026 |
| ~~p16~~ | ~~Informação interna da equipe aparece na tela~~ | Resolvidas | Problema | Baixa | Resolvida em 19/11/2026 |
| ~~p18~~ | ~~Mapa mineral sem descrição da aba~~ | Resolvidas | Problema | Média | Resolvida em 19/11/2026 |
| ~~p19~~ | ~~Link para o GitHub e arquivo interno citado no Mapa mineral~~ | Resolvidas | Problema | Baixa | Resolvida em 19/11/2026 |
| ~~p33~~ | ~~Data do SIGMINE errada na Base de dados~~ | Resolvidas | Problema | Média | Resolvida em 19/11/2026 |
| ~~p43~~ | ~~Biblioteca com falhas conhecidas nos robôs~~ | Resolvidas | Problema | Baixa | Resolvida em 19/11/2026 |

## Site como um todo (5)

### p11 · Definir quem é o cliente e como vai usar a plataforma

**Onde:** Site como um todo  
**Tipo:** Decisão do grupo · **Urgência:** Alta · **Status:** Aberta · **Responsável:** a definir

**O que acontece**

Ainda não está definido quem é o cliente da plataforma nem como ele vai usá-la. O mais provável é a FGV Energia e a empresa que a contrata. Sem essa definição, não dá para avaliar se cada informação é útil nem decidir o que vem primeiro. Várias pendências dependem disso, por exemplo p06, p20, p25 e p32.

**Como foi conferido**

Observado pelo Kayo em 18/11/2026.

**Situação em 25/11/2026**

Decisão ainda não tomada em 25/11/2026.

**Possibilidades de melhora** (ideias para discutir, não decisões)

- Levar a pergunta ao professor.
- Escrever em uma frase quem é o público e as duas ou três tarefas principais que ele faz no site, e usar isso como critério nas outras decisões.

### p25 · Cinco listas de 'projetos' diferentes no site

**Onde:** Mercado, Previsão, Território, Atlas e Base de dados  
**Tipo:** Decisão do grupo · **Urgência:** Alta · **Status:** Aberta · **Responsável:** a definir

**O que acontece**

Cada aba usa uma lista de projetos própria, vinda de um arquivo diferente: Mercado (carteira, 15 projetos, planilha de 04/10), Previsão (13 projetos), Território (1.046 "projetos do Radar"), Atlas (camada de 3.403 projetos da ANM) e a base "Projetos minerais de Goiás" do catálogo (37 projetos, 06/11). Os nomes não coincidem entre a carteira do Mercado e a base do catálogo. Para o cliente, a pergunta "quantos projetos há em Goiás" tem cinco respostas.

**Como foi conferido**

public/data/mercado/projetos_go_v1.json, public/data/previsao/previsao_v1.json, Squad 2/mineracao_cerrado (geojson), data/atlas/atlas.json, data/projetos/projetos.json (19/11).

**Situação em 25/11/2026**

Decisão ainda não tomada em 25/11/2026.

**Possibilidades de melhora** (ideias para discutir, não decisões)

- Definir uma lista oficial de projetos.
- Manter as listas, mas dar a cada uma um nome que diga o recorte (ex.: "carteira acompanhada", "projetos cadastrados na ANM").
- Uma nota curta explicando a diferença entre elas.

### p30 · Informação interna da equipe espalhada pelas abas

**Onde:** Várias abas do painel  
**Tipo:** Problema · **Urgência:** Média · **Status:** Resolvida em parte em 26/11/2026 (commit b54b079) · **Responsável:** a definir

**O que acontece**

Em várias abas a tela mostra coisas que são da equipe, não do cliente: pastas do repositório, nomes de scripts, "Squad 1/2", nomes de alunos e instruções como "rode python …". Em 25/11 isso aparece em: Empresas ("pipeline do Squad 1 (Squad 1/Bases consolidadas/…)", "data/producao", "data/panorama"); Comércio exterior ("public/data/mercado/mercado_v1.json"); Metodologia (ver p50); etiquetas "SQUAD 2" na Previsão e no Território; e a fonte da camada Municípios do Mapa mineral ("base consolidada do Squad 1 (v17)"). O Mercado tem pendência própria (p29). Atlas e Mapa mineral foram limpos em 19/11.

**Como foi conferido**

Pendências específicas de cada aba no quadro (19/11).

**Situação em 25/11/2026**

Continua, e se espalhou para as abas novas ou refeitas (lista acima). Atlas e Mapa mineral foram limpos em 19/11.

**Possibilidades de melhora** (ideias para discutir, não decisões)

- Combinar uma regra para o site todo: citar só a fonte pública e a data (ex.: "ANM — SIGMINE, 24/10/2026").
- Levar autoria, pastas e scripts para o manual técnico e o documento do trabalho.
- Corrigir aba por aba, junto com as pendências específicas (p29, p50).

**O que foi feito**

26/11/2026, commit b54b079, só texto, em PT e EN. Vários destes lugares não estavam listados nesta ficha: foram achados numa varredura da tela em 25/11.
- **Previsão:** etiqueta do topo sem "Squad 2"; "Observado (ANM)"; "Carteira de projetos" sem "(Squad 1)"; textos de método e de pesos sem "Squad 1"; gráfico de comparação com a EPE com "Modelo do projeto" e "Modelo · índice"; fonte do gráfico de intensidade como "base de intensidade energética do projeto".
- **Território:** etiqueta do topo sem "Squad 2"; "Próximos passos" sem "do Squad 2"; "Ligar à Previsão de demanda"; fonte "Radar de Projetos MINERA Goiás" sem "(Squad 1)".
- **Empresas:** fontes sem "pipeline do Squad 1 (…)", "data/producao" e "data/panorama"; "a base da CCEE usada" no lugar de "a CCEE do repositório".
- **Comércio exterior:** sem o caminho "public/data/mercado/mercado_v1.json" (em comex/base_curada.json e data/comex/comex.json).
- **Mapa mineral:** "base consolidada do projeto (v17)" na fonte da camada Municípios (em scripts/mapa_camadas.json e data/mapa/catalogo.json).
- **Base de dados:** a frase do fim da aba não cita mais o script que gera o catálogo.
- **Página inicial:** o texto do diagrama sem "Squad 1".
- **Simulador:** o texto de método sem "Squad 1" e "Squad 2", sem a pasta do modelo e sem o nome do script.

**O que ainda falta**

- **Previsão › Dados utilizados:** as fontes e notas que vêm do arquivo de dados (gerado por scripts/build_previsao_base.py), como "Squad 2 — base de intensidade energética v1", "É a tabela que o modelo do Squad 2 carrega" e caminhos como "Squad 2/intensidade_energetica/…" e "Squad 1/dados/CCEE".
- **Previsão › Metodologia:** a lista de arquivos de "Arquivos e reprodução" (ver p24).
- **Simulador › Fontes e premissas:** as fontes e notas que vêm de public/data/simulador/parametros_v1.json (gerado por scripts/build_simulador_base.py), como "Squad 2 — hipóteses de cenário do modelo real", "Squad 1 — bases públicas e diagnóstico mineral" e caminhos de pasta.
- ~~**Base de dados:** campo "Onde vive" e "Origem" com pastas, squad e scripts.~~ Resolvido em 26/11/2026 (commit 7a1c51f): "Onde vive" saiu do cartão, a origem não cita mais squad, pasta nem script, e a documentação do site vem sem anotação interna.
- **Empresas › Atlas empresarial** (sub-aba nova, commit fc8c2ad de 26/11): as fontes citam "base consolidada do Squad 1" (textos ea.fontePerfil e ea.fonteTerritorio do public/i18n.js, em PT e EN). Visto no dicionário, não conferido na tela.
- **Metodologia:** ver p50.

### ~~p38 · Nenhum link abre uma aba específica do painel~~

**Onde:** Endereços do painel (ex.: /painel.html#fontes) e links da página inicial  
**Tipo:** Problema · **Urgência:** Média · **Status:** Resolvida em 26/11/2026 (decidido não fazer) · **Responsável:** a definir

**O que acontece**

O painel ignora o que vem depois do # no endereço e abre sempre o Atlas. Na página inicial, "Consultar o acervo" (/painel.html#fontes) deveria levar à Base de dados e leva ao Atlas; "Abrir atlas" funciona só porque o Atlas é a aba que abre primeiro.

**Como foi conferido**

Site real, /painel.html#fontes abre o Atlas (19/11).

**Situação em 25/11/2026**

Continua: painel.js não lê o que vem depois do # no endereço; /painel.html#fontes abre o Atlas.

**Possibilidades de melhora** (ideias para discutir, não decisões)

- Fazer o painel abrir a aba indicada no endereço (#bases, #previsao…), para os links levarem direto ao lugar certo.

**Decisão**

26/11/2026: decidido não fazer. O Kayo avaliou que abrir uma aba específica por link é desnecessário agora.

### p10 · Links do site para o GitHub

**Onde:** Página inicial e aba Metodologia  
**Tipo:** Problema · **Urgência:** Baixa · **Status:** Resolvida em parte em 26/11/2026 (commit b54b079) · **Responsável:** a definir

**O que acontece**

O site ainda tem links que mandam o usuário ao GitHub: 2 na página inicial e 2 na aba Metodologia (ver p50). O GitHub documenta o processo para o professor; não é lugar para o usuário do site. O link do Mapa mineral já foi tirado em 19/11.

**Como foi conferido**

Observado pelo Kayo em 18/11/2026.

**Situação em 25/11/2026**

Continua na página inicial (2 links). O do Mapa mineral foi tirado em 19/11. Surgiram dois na aba nova Metodologia (ver p50).

**Possibilidades de melhora** (ideias para discutir, não decisões)

- Tirar os links.
- Quando o conteúdo do GitHub for útil ao usuário, trazê-lo para o site.

**O que foi feito**

26/11/2026, commit b54b079: saíram os dois links da página inicial (inventário do P3M e "Repositório do projeto"), em public/index.html.

**O que ainda falta**

- Os links da aba Metodologia (ver p50). Os "Abrir a documentação da base ↗" da Base de dados saíram em 26/11/2026 (commit 7a1c51f, ver p08).

## Página inicial (3)

### ~~p06 · Página inicial não diz o que a plataforma faz~~

**Onde:** Página inicial › texto de apresentação  
**Tipo:** Problema · **Urgência:** Média · **Status:** Resolvida em 26/11/2026 (commit b54b079) · **Responsável:** a definir

**O que acontece**

O texto da página inicial não explica o que a plataforma oferece nem para quem ela é. Em 25/11 ele ainda diz que o site é "para uso da equipe do projeto". Quem chega não sabe o que vai encontrar depois do login.

**Como foi conferido**

Observado pelo Kayo em 18/11/2026.

**Situação em 25/11/2026**

Conferido no site real: o texto continua "para uso da equipe do projeto".

**Possibilidades de melhora** (ideias para discutir, não decisões)

- Um parágrafo curto dizendo o que dá para fazer no site (mapa, previsão de demanda, mercado, radar…) e para quem ele é.
- Fica mais fácil depois de definir o cliente (p11).

**O que foi feito**

26/11/2026, commit b54b079: o texto de abertura agora diz o que a plataforma reúne (mapas, indicadores, previsão de demanda de energia, mercado de minerais críticos, empresas, comércio exterior e radar de projetos, com a fonte de cada número), e o bloco de acesso deixou de dizer "para a equipe do projeto". Em PT e EN, em public/i18n.js e public/index.html.

Quando o cliente for definido (p11), vale rever o texto.

### p05 · Contadores de dados não informam nada

**Onde:** Página inicial › contadores de dados  
**Tipo:** Problema · **Urgência:** Baixa · **Status:** Aberta · **Responsável:** a definir

**O que acontece**

Os contadores da página inicial (em 25/11: 84 arquivos de origem, 221 abas e tabelas, 584.376 linhas) não dizem nada a quem chega, não batem com a Base de dados (17 bases em 25/11) e mudam sozinhos (66 arquivos e 523.502 linhas em 18/11; 71 arquivos e 576.327 linhas em 19/11).

**Como foi conferido**

Site real, página inicial e /api/public/summary (18 e 19/11).

**Situação em 25/11/2026**

Conferido no site real: os contadores continuam (84 arquivos, 221 abas, 584.376 linhas).

**Possibilidades de melhora** (ideias para discutir, não decisões)

- Trocar por números de cobertura: período, municípios e minerais.
- Mostrar o mesmo número de bases da aba Base de dados.
- Tirar os contadores.

### p07 · Juntar página inicial e login

**Onde:** Página inicial e tela de login  
**Tipo:** Decisão do grupo · **Urgência:** Baixa · **Status:** Aberta · **Responsável:** a definir

**O que acontece**

Hoje a página inicial e a tela de login são páginas separadas. Foi levantada a ideia de a página inicial explicar a plataforma e já trazer o login, mantendo os fluxos de troca de senha. É uma mudança de navegação e envolve a frente 9.

**Como foi conferido**

Observado pelo Kayo em 18/11/2026.

**Situação em 25/11/2026**

Decisão ainda não tomada em 25/11/2026.

**Possibilidades de melhora** (ideias para discutir, não decisões)

- Juntar as duas páginas: a inicial explica e já traz o login.
- Manter separadas e só melhorar o texto da inicial (p06), com o botão de entrar em destaque.

## Atlas e panorama (6)

### p12 · Área das rodadas de disponibilidade 100 vezes maior

**Onde:** Painel › Atlas e panorama › sub-aba Pesquisa e direitos  
**Tipo:** Problema · **Urgência:** Alta (bloqueia: número errado na tela) · **Status:** Aberta · **Responsável:** a definir

**O que acontece**

O campo AreaPoligonal do arquivo de rodadas da ANM vem em centésimos de hectare, e o site lê como hectare, então a área aparece 100 vezes maior. Na tela (Atlas e panorama › Pesquisa e direitos): em "Situação das áreas ofertadas", Arrematada = 99.716.726 ha (o certo é 997.167 ha) e Livre = 46.084.526 ha (o certo é 460.845 ha); em "Maiores lances", o processo 860240/2007 aparece com 152.745 ha (o certo é 1.527 ha). Prova: nos 456 processos que estão nas rodadas e no SIGMINE, a área da rodada é exatamente 100 vezes a do SIGMINE. O total certo é 2.864.988 ha nas 3.632 áreas. O Radar não é afetado, porque conta as áreas e não soma hectares.

**Como foi conferido**

Site real, Atlas e panorama > Pesquisa e direitos (19/11); Squad 1/dados/ResultadoRodadaDisponibilidade (1).csv.

**Situação em 25/11/2026**

Conferido em 25/11: continua (Arrematada 99.716.726 ha; certo 997.167 ha). scripts/build_panorama_base.py ainda lê AreaPoligonal sem dividir por 100.

**Possibilidades de melhora** (ideias para discutir, não decisões)

- Dividir AreaPoligonal por 100 no gerador do Panorama (scripts/build_panorama_base.py, perto da linha 248) e gerar o pacote de novo.
- Depois, conferir os totais com o SIGMINE (2.864.988 ha nas 3.632 áreas).

### ~~p01 · Nas sub-abas Empresas e Notas o mapa some e o topo fica em branco~~

**Onde:** Painel › Atlas e panorama › sub-aba Notas  
**Tipo:** Problema · **Urgência:** Média · **Status:** Resolvida em 26/11/2026 (commit 84fdd26) · **Responsável:** a definir

**O que acontece**

Na sub-aba Notas do Atlas e panorama, o mapa do Atlas some (altura 0) e a parte de cima fica só com os filtros e a barra de sub-abas, parecendo vazia. O conteúdo existe, mas aparece mais abaixo, no Panorama. Em 19/11 o mesmo acontecia na sub-aba Empresas, que saiu do Panorama em 21/11 e foi para a aba Empresas.

**Como foi conferido**

Site real, aba Atlas e panorama, sub-abas Empresas e Notas (19/11).

**Situação em 25/11/2026**

A sub-aba Empresas saiu do Panorama em 21/11 (foi para a aba Empresas), então ali o problema acabou. Na sub-aba Notas o mapa continua sumindo (altura 0) e o topo fica só com os filtros.

**Possibilidades de melhora** (ideias para discutir, não decisões)

- Manter o mapa visível em todas as sub-abas.
- Ao abrir Notas, levar a tela direto ao conteúdo, mais abaixo.
- Se Notas sair da tela (ver p02), o problema acaba junto.

**O que foi feito**

26/11/2026, commit 84fdd26: a sub-aba Notas saiu do Atlas e panorama. Ela só listava o que o Panorama original tinha e não foi refeito, uma anotação da equipe; sem ela, não sobra sub-aba com o mapa sumindo e o topo vazio.

### p03 · Alcance dos filtros não é visível

**Onde:** Painel › Atlas e panorama › filtros do Atlas e do Panorama  
**Tipo:** Problema · **Urgência:** Média · **Status:** Aberta · **Responsável:** a definir

**O que acontece**

Há dois blocos de filtro na mesma aba: o do Atlas (período, município, mineral, substância, fase, classificação) e o do Panorama (ano inicial e final, mês, município, mineral, titular, fase, gasto em pesquisa, ramo da CCEE). O município sincroniza nos dois sentidos, mas o mineral não: mudar o mineral no Atlas não muda o Panorama. O bloco do Panorama fica separado dos gráficos e parece valer para a página toda, embora cada cartão já diga quais filtros valem nele ('Filtros que valem aqui').

**Como foi conferido**

Site real, Atlas e panorama (19/11): município Niquelândia e Catalão sincronizaram; mineral 'Areia' no Atlas não mudou o Panorama.

**Situação em 25/11/2026**

Sem mudança no desenho dos filtros do Atlas desde 19/11.

**Possibilidades de melhora** (ideias para discutir, não decisões)

- Fazer o mineral sincronizar entre Atlas e Panorama, como o município já faz.
- Juntar os dois blocos de filtro em um só.
- Escrever no topo de cada bloco a que parte da página ele vale.

### p04 · Sem hierarquia clara entre as seções

**Onde:** Painel › Atlas e panorama (estrutura da aba)  
**Tipo:** Problema · **Urgência:** Média · **Status:** Aberta · **Responsável:** a definir

**O que acontece**

A aba junta duas páginas, cada uma com seu título principal ('Atlas mineral de Goiás' e 'Panorama da mineração de Goiás'). A barra de sub-abas fica dentro do Atlas, mas troca a camada do mapa e também o conteúdo do Panorama, que está mais abaixo. Não fica claro o que pertence a quê.

**Como foi conferido**

Site real, Atlas e panorama (19/11).

**Situação em 25/11/2026**

Continua: duas páginas (Atlas e Panorama) com dois títulos principais na mesma aba.

**Possibilidades de melhora** (ideias para discutir, não decisões)

- Um título principal para a aba, com Atlas e Panorama como seções dele.
- Separar em duas abas.
- Pôr a barra de sub-abas acima das duas partes, para ficar claro que vale para ambas.

### ~~p02 · Sub-aba Notas é recado interno da equipe~~

**Onde:** Painel › Atlas e panorama › sub-aba Notas  
**Tipo:** Problema · **Urgência:** Baixa · **Status:** Resolvida em 26/11/2026 (commit b54b079) · **Responsável:** a definir

**O que acontece**

A sub-aba Notas ("O que não foi refeito") é informação para a equipe: lista 7 análises do Panorama original que não foram refeitas, diz que "a fonte precisa entrar em Squad 1/Dados brutos", fala em "cópia de trabalho" e que um pareamento "é do Estudante 3". Para quem usa o site, isso não ajuda.

**Como foi conferido**

Site real, Atlas e panorama > Notas (19/11).

**Situação em 25/11/2026**

Continua igual: a sub-aba Notas ainda é recado interno ("Para refazê-los, a fonte precisa entrar em Squad 1/Dados brutos…", "cópia de trabalho").

**Possibilidades de melhora** (ideias para discutir, não decisões)

- Trocar por uma nota curta para o usuário, do tipo "algumas análises do Panorama original ainda não foram refeitas".
- Levar a lista completa para o manual técnico ou para o GitHub.
- Tirar a sub-aba.

**O que foi feito**

26/11/2026, commit b54b079: a sub-aba Notas continua listando os quadros do Panorama original que não foram refeitos e o motivo de cada um, mas sem recado interno: saíram "Squad 1/Dados brutos" e "cópia de trabalho", e "bases do repositório" virou "bases do projeto". Em PT e EN, em public/i18n.js.

### p13 · Energia e barragens sem data na tela (Atlas e Mapa mineral)

**Onde:** Painel › Atlas e panorama (linha de fonte) e Mapa mineral (camada de barragens)  
**Tipo:** Problema · **Urgência:** Baixa · **Status:** Aberta · **Responsável:** a definir

**O que acontece**

No Atlas e panorama, a linha de fonte diz que energia (CCEE) e barragens (SIGBM) "seguem do retrato recebido anteriormente", sem dizer de quando. No Mapa mineral, a camada de barragens diz "retrato anterior do Atlas (data não registrada)". O pacote de dados confirma que a data de extração das barragens não foi informada.

**Como foi conferido**

Site real, Atlas e panorama, linha de fonte (19/11); data/atlas/atlas.json.

**Situação em 25/11/2026**

Continua: energia e barragens como "retrato recebido anteriormente", sem data.

**Possibilidades de melhora** (ideias para discutir, não decisões)

- Baixar o SIGBM atual da ANM e registrar a data.
- No mínimo, descobrir de quando é o retrato usado e escrever a data na tela.
- O mesmo para a CCEE.

## Mapa mineral (2)

### ~~p17 · Fontes das 47 camadas do Mapa mineral fora da Base de dados~~

**Onde:** Painel › Base de dados (catálogo) e Mapa mineral  
**Tipo:** Problema · **Urgência:** Média · **Status:** Resolvida em 26/11/2026 (commit 7a1c51f) · **Responsável:** a definir

**O que acontece**

O Mapa mineral usa camadas do P3M do SGB, EPE, Infra S.A., MMA/CNUC, FUNAI, INCRA, IPHAN, ICMBio, MapBiomas, OpenStreetMap e SIAGAS. Nenhuma dessas fontes aparece no catálogo da aba Base de dados (busca em todos os campos: zero ocorrências).

**Como foi conferido**

data/mapa/catalogo.json contra data/catalogo/catalogo.json (19/11).

**Situação em 25/11/2026**

Continua: as fontes das camadas do Mapa mineral não estão no catálogo.

**Possibilidades de melhora** (ideias para discutir, não decisões)

- Levar as fontes para a Base de dados aproveitando o catálogo do próprio mapa (data/mapa/catalogo.json), que já tem fonte, data e arquivo de cada camada.
- Ou um cartão "Camadas do Mapa mineral" que agrupe todas.

**O que foi feito**

26/11/2026, commit 7a1c51f: a aba Base de dados foi refeita. Cartões curtos, um quadro de detalhes com a documentação de cada base (tirada do README dela, sem anotação interna) e o botão Baixar, só para quem está logado. O catálogo passou de 17 para 25 bases.

Entrou o cartão "Camadas do Mapa mineral" (47 camadas em 8 grupos), com a documentação do Mapa, que lista as camadas e as fontes (SGB/P3M, MapBiomas, IBGE, INCRA, MMA, ANM, EPE), e o download do pacote.

### p20 · Mapa mineral repete camadas do Atlas, com outro retrato do SIGMINE

**Onde:** Painel › Mapa mineral e Atlas e panorama  
**Tipo:** Decisão do grupo · **Urgência:** Média · **Status:** Aberta · **Responsável:** a definir

**O que acontece**

Processos minerários, barragens, ocorrências (RECMIN) e projetos aparecem nos dois mapas: no Atlas e panorama e no Mapa mineral. O mesmo assunto fica em dois lugares, e quem usa o site não sabe qual olhar. Em 19/11 o Mapa mineral também dizia que o SIGMINE era de 10/09/2026, e o Atlas, de 24/10/2026; a data do Mapa mineral foi corrigida para 24/10/2026 em 19/11 (ver p33), mas as camadas continuam repetidas.

**Como foi conferido**

data/mapa/catalogo.json (Processos minerários: SIGMINE de 10/09/2026) e data/atlas/atlas.json (SIGMINE de 24/10/2026).

**Situação em 25/11/2026**

Decisão ainda não tomada em 25/11/2026.

**Possibilidades de melhora** (ideias para discutir, não decisões)

- Escolher um dos dois mapas para essas camadas.
- Manter nos dois, cuidando para que usem sempre o mesmo retrato do SIGMINE quando ele for atualizado.
- Mostrar a data em cada mapa, para explicar a diferença.

## Base de dados (6)

### ~~p08 · Documentação das bases fica no GitHub~~

**Onde:** Painel › Base de dados › link "Abrir a documentação da base" de cada cartão  
**Tipo:** Problema · **Urgência:** Média · **Status:** Resolvida em 26/11/2026 (commit 7a1c51f) · **Responsável:** a definir

**O que acontece**

Na aba Base de dados, 16 das 17 bases têm o link "Abrir a documentação da base ↗", que leva ao GitHub. Para ler a documentação, o usuário precisa sair do site e entrar no repositório de trabalho da equipe.

**Como foi conferido**

Observado pelo Kayo em 18/11/2026.

**Situação em 25/11/2026**

Continua: 16 das 17 bases têm "Abrir a documentação da base ↗" para o GitHub, incluindo as duas novas do Comércio exterior.

**Possibilidades de melhora** (ideias para discutir, não decisões)

- Mostrar a documentação no próprio site (por exemplo, ao abrir o cartão), conferida com os arquivos reais.
- Resumir no cartão o essencial e tirar o link.

**O que foi feito**

26/11/2026, commit 7a1c51f: a aba Base de dados foi refeita. Cartões curtos, um quadro de detalhes com a documentação de cada base (tirada do README dela, sem anotação interna) e o botão Baixar, só para quem está logado. O catálogo passou de 17 para 25 bases.

A documentação de cada base abre no próprio site, no quadro de detalhes; a aba não tem mais nenhum link para o GitHub.

### ~~p09 · Sem botão de download das bases~~

**Onde:** Painel › Base de dados  
**Tipo:** A desenvolver · **Urgência:** Média · **Status:** Resolvida em 26/11/2026 (commit 7a1c51f) · **Responsável:** a definir

**O que acontece**

A aba Base de dados descreve cada base, mas não tem como baixá-la. Quem precisa do dado tratado não consegue obtê-lo pelo site.

**Como foi conferido**

Observado pelo Kayo em 18/11/2026.

**Situação em 25/11/2026**

Continua sem botão de download.

**Possibilidades de melhora** (ideias para discutir, não decisões)

- Um botão para baixar a versão tratada de cada base, só para quem está logado.
- Começar pelas bases mais usadas.
- Combinar com a regra de acesso aos arquivos (p21).

**O que foi feito**

26/11/2026, commit 7a1c51f: a aba Base de dados foi refeita. Cartões curtos, um quadro de detalhes com a documentação de cada base (tirada do README dela, sem anotação interna) e o botão Baixar, só para quem está logado. O catálogo passou de 17 para 25 bases.

Botão Baixar em 24 das 25 bases: um arquivo vai como está, vários vão num .zip. Só com login (sem sessão, a rota devolve 401). A única sem download é o agente semanal de produção, cujos dados ficam só no banco do servidor.

### p14 · IBGE não aparece na Base de dados; barragens sem fonte

**Onde:** Painel › Base de dados (catálogo)  
**Tipo:** Problema · **Urgência:** Média · **Status:** Resolvida em parte em 26/11/2026 (commit 7a1c51f) · **Responsável:** a definir

**O que acontece**

O Atlas e panorama usa dados do IBGE (malha municipal 2025, população 2026 e PIB 2023 por município), mas o IBGE não aparece em nenhum campo do catálogo da Base de dados (busca por IBGE, população, PIB e malha: zero ocorrências). As barragens aparecem no catálogo só como uma das camadas do "Atlas mineral de Goiás", sem dizer que vêm do SIGBM nem de quando.

**Como foi conferido**

data/atlas/atlas.json (meta.sources) e data/panorama/panorama.json (dims, meta.periods) contra data/catalogo/catalogo.json.

**Situação em 25/11/2026**

Continua: o catálogo não cita IBGE nem SIGBM.

**Possibilidades de melhora** (ideias para discutir, não decisões)

- Incluir no catálogo as bases do IBGE usadas (malha, população e PIB).
- Um cartão para o SIGBM, com data.

**O que foi feito**

26/11/2026, commit 7a1c51f: a aba Base de dados foi refeita. Cartões curtos, um quadro de detalhes com a documentação de cada base (tirada do README dela, sem anotação interna) e o botão Baixar, só para quem está logado. O catálogo passou de 17 para 25 bases.

O IBGE aparece na origem dos Indicadores municipais e na documentação do Mapa mineral; a documentação do Atlas cita o SIGBM como fonte das barragens.

**O que ainda falta**

- O IBGE e o SIGBM não têm cartão próprio.
- A data das barragens continua sem aparecer (ver p13).

### p34 · Cartões das bases não dizem onde a base é usada nem como é atualizada

**Onde:** Painel › Base de dados › cartões das bases  
**Tipo:** A desenvolver · **Urgência:** Média · **Status:** Resolvida em parte em 26/11/2026 (commit 7a1c51f) · **Responsável:** a definir

**O que acontece**

Nos cartões das bases, o campo "Onde vive" mostra o caminho do arquivo no repositório, não as abas do site que usam a base. Só 2 cartões dizem como a base é atualizada (notícias: robô diário; agente de produção: semanal); para os outros não dá para saber se é robô, script ou alguém subindo arquivo, nem com que frequência. Três cartões têm o campo "O que não mede" vazio (investimento, rodadas, Panorama). Em 19/11 eram 15 bases; as duas novas do Comércio exterior têm o mesmo problema.

**Como foi conferido**

Site real, Base de dados (19/11); data/catalogo/catalogo.json.

**Situação em 25/11/2026**

Continua, e vale também para as duas bases novas do Comércio exterior.

**Possibilidades de melhora** (ideias para discutir, não decisões)

- Trocar "Onde vive" por "Usada em", com as abas do site.
- Um campo "Como é atualizada" (robô, script ou envio manual, e a frequência).
- Preencher "O que não mede" nos três cartões vazios.

**O que foi feito**

26/11/2026, commit 7a1c51f: a aba Base de dados foi refeita. Cartões curtos, um quadro de detalhes com a documentação de cada base (tirada do README dela, sem anotação interna) e o botão Baixar, só para quem está logado. O catálogo passou de 17 para 25 bases.

O campo "Onde vive", que mostrava o caminho do arquivo, saiu do cartão.

Decisão do Kayo em 26/11: "onde a base é usada" não será mostrado, porque o risco de informação errada é alto.

**O que ainda falta**

- Dizer em cada cartão como a base é atualizada (robô, script ou manual) e com que frequência.

### ~~p36 · Pasta do servidor exposta na Base de dados~~

**Onde:** Painel › Base de dados › cartão "Agente semanal de produção"  
**Tipo:** Problema · **Urgência:** Média · **Status:** Resolvida em 26/11/2026 (commit 7a1c51f) · **Responsável:** a definir

**O que acontece**

O cartão "Agente semanal de produção" mostra "banco em /var/lib/minera-goias-producao na VPS", ou seja, o caminho de uma pasta no servidor. É informação de infraestrutura que não precisa aparecer para o usuário.

**Como foi conferido**

Site real, Base de dados, cartão do agente de produção (19/11).

**Situação em 25/11/2026**

Continua: o cartão do agente de produção ainda mostra "/var/lib/minera-goias-producao na VPS".

**Possibilidades de melhora** (ideias para discutir, não decisões)

- Trocar por "banco no servidor do projeto", ou tirar.
- Deixar o caminho no manual técnico.

**O que foi feito**

26/11/2026, commit 7a1c51f: a aba Base de dados foi refeita. Cartões curtos, um quadro de detalhes com a documentação de cada base (tirada do README dela, sem anotação interna) e o botão Baixar, só para quem está logado. O catálogo passou de 17 para 25 bases.

O campo "Onde vive" saiu do cartão; a pasta do servidor não aparece mais na tela.

### p35 · Base de dados em português na versão em inglês

**Onde:** Painel › Base de dados (versão em inglês)  
**Tipo:** Problema · **Urgência:** Baixa · **Status:** Aberta · **Responsável:** a definir

**O que acontece**

Na versão em inglês, só os rótulos dos cartões são traduzidos ("ORIGIN", "LAST UPDATED"). O conteúdo dos 17 cartões fica em português: origem, volume, o que mede, o que não mede e a família ("Energia", "Mineração").

**Como foi conferido**

Site real, Base de dados em inglês (19/11).

**Situação em 25/11/2026**

Conferido em 25/11: os 17 cartões continuam em português na versão em inglês.

**Possibilidades de melhora** (ideias para discutir, não decisões)

- Ter o conteúdo do catálogo nos dois idiomas.
- Traduzir ao menos os campos que se repetem (família, origem).

## Previsão de demanda e Simulador (7)

### p21 · Dados e páginas abertos sem login

**Onde:** Pasta pública do site (`public/data/`) e página do Simulador  
**Tipo:** Problema · **Urgência:** Média · **Status:** Aberta · **Responsável:** a definir

**O que acontece**

A aba Previsão fica atrás do login, mas o arquivo que ela lê está na pasta pública do site: https://labfgv.com.br/data/previsao/previsao_v1.json abre sem login (status 200, 104 KB), com a previsão inteira e a carteira de projetos com o nome das empresas. O mesmo vale para /data/simulador/parametros_v1.json. A aba Território, ao contrário, só entrega os dados com login. Não há uma regra única sobre o que é público.

**Como foi conferido**

curl sem login em /data/previsao/previsao_v1.json e /data/simulador/parametros_v1.json: 200 (19/11).

**Situação em 25/11/2026**

Conferido em 25/11: /data/previsao/previsao_v1.json e /data/simulador/parametros_v1.json continuam abrindo sem login (200).

**Ampliada em 26/11/2026**

Regra definida pelo Kayo: **só a página inicial e a tela de login ficam abertas; todo o resto pede login.** Fechar o GitHub não resolve
isto: os arquivos de `public/` são servidos pelo próprio site, não pelo GitHub.

Conferido sem login no site real em 26/11 (todos responderam 200):

- `/data/previsao/previsao_v1.json` e `/data/previsao/production_benchmark_v1.json` (Previsão);
- `/data/simulador/parametros_v1.json` (Simulador);
- `/data/mercado/mercado_v1.json`, `/data/mercado/projetos_go_v1.json` e, a partir do commit 7c7c57f, `/data/mercado/README.md` (Mercado);
- `/data/noticias/latest.json` e `/data/noticias/meses/*.json` (notícias do Radar);
- a página `/simulador.html` inteira.

A página `/painel.html` abre, mas os dados das abas que vêm do servidor pedem login (ex.: `/api/atlas` e `/api/mapa/catalogo` devolvem 401).

**Possibilidades de melhora** (ideias para discutir, não decisões)

- Entregar esses arquivos por rotas com login, como já é feito no Território (/api/territorio), tirá-los da pasta pública e ajustar as
  telas que os leem (Mercado, Previsão, Simulador e Radar).
- Pôr a página do Simulador atrás do login.
- Fazer junto com a reforma da aba Base de dados, em que o download também vai pedir login.

### p23 · Insumos da Previsão fora da Base de dados

**Onde:** Painel › Base de dados (catálogo) e Previsão de demanda  
**Tipo:** Problema · **Urgência:** Média · **Status:** Resolvida em parte em 26/11/2026 (commit 7a1c51f) · **Responsável:** a definir

**O que acontece**

A Previsão usa a base de intensidade energética, as hipóteses de cenário, os pesos da carteira por maturidade, a curadoria do Radar de Projetos e o benchmark de intensidade da apresentação FGV Energia-EPGE. Nada disso aparece na aba Base de dados, nem a própria previsão (busca por previsão e modelo: zero ocorrências). A aba Previsão já lista as 10 fontes que usa.

**Como foi conferido**

public/data/previsao/previsao_v1.json (fontes) contra data/catalogo/catalogo.json (19/11).

**Situação em 25/11/2026**

Continua: os insumos da Previsão não estão no catálogo.

**Possibilidades de melhora** (ideias para discutir, não decisões)

- Incluir no catálogo as 10 fontes que a aba Previsão já lista.
- Ou um cartão "Insumos da Previsão" que agrupe todas.

**O que foi feito**

26/11/2026, commit 7a1c51f: a aba Base de dados foi refeita. Cartões curtos, um quadro de detalhes com a documentação de cada base (tirada do README dela, sem anotação interna) e o botão Baixar, só para quem está logado. O catálogo passou de 17 para 25 bases.

Entraram os cartões "Previsão de demanda de energia da mineração" (com a documentação do modelo e o download da previsão, do benchmark e dos parâmetros do Simulador) e "Intensidade energética do setor mineral".

**O que ainda falta**

- A curadoria do Radar de Projetos e o benchmark da apresentação FGV Energia-EPGE não têm cartão próprio.

### p39 · Simulador fora do padrão do site e sem inglês

**Onde:** Simulador (/simulador.html)  
**Tipo:** Problema · **Urgência:** Média · **Status:** Aberta · **Responsável:** a definir

**O que acontece**

O Simulador tem visual próprio (fundo bege, outro cabeçalho, sem o menu do painel), não tem botão PT/EN e fica em português mesmo com o inglês escolhido. Mostra também nome de pessoa ("Squad 2 — Federico Castro").

**Como foi conferido**

Site real, /simulador.html (19/11).

**Situação em 25/11/2026**

Conferido no site real em 25/11: continua sem PT/EN e com visual próprio.

**Possibilidades de melhora** (ideias para discutir, não decisões)

- Usar o cabeçalho, as cores e o menu do painel.
- Botão PT/EN usando o dicionário do site.
- Tirar o nome de pessoa (ver p30).

### p49 · Simulador mostra outro número ao trocar de cenário

**Onde:** Simulador › troca de cenário  
**Tipo:** Problema · **Urgência:** Média · **Status:** Aberta · **Responsável:** a definir

**O que acontece**

Ao trocar de cenário, o Simulador mantém a eficiência energética do cenário anterior (g = 0,9%), em vez da do cenário escolhido (Expansão 1,4%, Conservador 0,4%). Em 19/11, "Expansão" mostrou 7,85 ou 8,46 TWh em 2040, conforme a ordem dos cliques, enquanto a Previsão diz 7,28 TWh; "Conservador" mostrou 3,59 contra 3,87 TWh. Só depois de clicar em "Restaurar padrão do cenário" os números batem.

**Como foi conferido**

Site real, /simulador.html (19/11).

**Situação em 25/11/2026**

Conferido no site real em 25/11: trocar de cenário mantém g = 0,9% até clicar em "Restaurar padrão do cenário" (Expansão 1,4%, Conservador 0,4%).

**Possibilidades de melhora** (ideias para discutir, não decisões)

- Ao escolher um cenário, carregar a eficiência padrão dele.
- Ou avisar na tela que a eficiência do cenário anterior foi mantida.

### p57 · Tabela 'Carteira ampliada' da Previsão com informação interna, sem inglês e com outra lista de projetos

**Onde:** Painel › Previsão de demanda › Dados utilizados › tabela "Carteira ampliada: prontidão para o modelo energético"  
**Tipo:** Problema · **Urgência:** Média · **Status:** Resolvida em parte em 26/11/2026 (commit b54b079) · **Responsável:** a definir

**O que acontece**

Desde 24/11, a sub-aba Dados utilizados da Previsão tem a tabela "Carteira ampliada: prontidão para o modelo energético", com 37 projetos. Ela tem três problemas:

- **Informação interna na tela:** "Todos os projetos da curadoria do Squad 1", "Carteira completa do Squad 1" e, na coluna Leitura, "pipeline energético".
- **Sem inglês:** na versão em inglês o painel ao lado vira "Sources", mas o título e a explicação da tabela ficam em português. Os nomes dos indicadores e das colunas estão escritos em português direto no código (previsao.js), sem passar pelo dicionário de tradução.
- **Mais uma lista de projetos (ver p25):** a tabela vem de Squad 1/Radar de Projetos/curadoria_web.json (37 projetos). A base "Projetos minerais de Goiás" do catálogo também tem 37 projetos, mas vem de outro arquivo (projetos/base_curada.json, gerado em 10/11), e nenhum projeto tem o nome escrito igual nas duas (ex.: "Chapada" no catálogo e "Expansão de Chapada — moinho de bolas e depósito Saúva" na tabela). Na mesma aba, a carteira do modelo continua com 13 projetos.

**Como foi conferido**

Site real, Previsão de demanda > Dados utilizados, conta de administrador, em português e em inglês (25/11); public/painel.html e public/previsao.js (commits d9ea4fc e de29c45, 24/11); campo auditoria_projetos de public/data/previsao/previsao_v1.json.

**Situação em 25/11/2026**

Encontrada na 2ª rodada (25/11/2026).

**Possibilidades de melhora** (ideias para discutir, não decisões)

- Trocar as menções ao Squad 1 e ao pipeline por uma descrição do que a lista é, deixando a origem do arquivo para a documentação.
- Passar os textos da tabela pelo dicionário de tradução, como o resto da Previsão.
- Tratar junto com a p25: ver se essa lista e a do catálogo são a mesma; se forem, usar um arquivo só; se não, dar a cada uma um nome que mostre a diferença.
- Pôr a curadoria na Base de dados, junto com os outros insumos da Previsão (p23).

**O que foi feito**

26/11/2026, commit b54b079: a explicação e o indicador da tabela deixaram de citar o Squad 1 ("Todos os projetos da curadoria do Radar de Projetos", "Carteira completa da curadoria"), em public/painel.html e public/previsao.js.

**O que ainda falta**

- A coluna Leitura ainda diz "pipeline energético" (vem do arquivo de dados gerado por scripts/build_previsao_base.py).
- A tabela continua sem inglês.
- Continua a dúvida sobre a lista de projetos, junto com a p25.

### p22 · Notas em português na versão em inglês da Previsão

**Onde:** Painel › Previsão de demanda › Data used (versão em inglês)  
**Tipo:** Problema · **Urgência:** Baixa · **Status:** Aberta · **Responsável:** a definir

**O que acontece**

Na versão em inglês, na sub-aba "Data used", as observações de cada coeficiente, os métodos e os motivos de cada projeto aparecem em português (ex.: "sem dado próprio: mantido o parâmetro atual do modelo"), porque vêm direto do arquivo de origem.

**Como foi conferido**

Site real, Previsão em inglês > Data used (19/11).

**Situação em 25/11/2026**

Conferido em 25/11 (Previsão em inglês, Data used): as notas continuam em português.

**Possibilidades de melhora** (ideias para discutir, não decisões)

- Gerar as notas nos dois idiomas no pacote de dados.
- Traduzir pelo dicionário do site as notas que se repetem.

### p24 · Instruções internas na Metodologia da Previsão

**Onde:** Painel › Previsão de demanda › Metodologia › "Arquivos e reprodução"  
**Tipo:** Problema · **Urgência:** Baixa · **Status:** Resolvida em parte em 26/11/2026 (commit b54b079) · **Responsável:** a definir

**O que acontece**

A seção "Arquivos e reprodução" lista caminhos de scripts do repositório e diz "Para atualizar, rode python scripts/build_previsao_base.py". É instrução para a equipe, não para quem usa o site.

**Como foi conferido**

Site real, Previsão > Metodologia (19/11).

**Situação em 25/11/2026**

Continua: "Para atualizar, rode python scripts/build_previsao_base.py".

**Possibilidades de melhora** (ideias para discutir, não decisões)

- Tirar da tela a seção "Arquivos e reprodução" e levá-la ao manual técnico.
- Deixar na tela só o método e as fontes.

**O que foi feito**

26/11/2026, commit b54b079: saiu "Para atualizar, rode python scripts/build_previsao_base.py". O texto agora diz que a aba lê um único arquivo, gerado a partir do modelo de demanda, e que os arquivos usados estão listados abaixo. Em PT e EN, em public/i18n.js e public/painel.html.

**O que ainda falta**

- A lista de arquivos e scripts continua na seção "Arquivos e reprodução" (ex.: "Squad 2/modello_reale/src/run_backtest.py"). Ficou porque é informação de método; falta decidir se fica na tela ou vai para o manual técnico.

## Mercado, Empresas e Comércio exterior (6)

### p26 · Indicador '609 mil ha sob requerimento' não confere e não tem fonte

**Onde:** Painel › Mercado › indicadores do topo  
**Tipo:** Problema · **Urgência:** Média · **Status:** Aberta · **Responsável:** a definir

**O que acontece**

O indicador do topo diz "Área sob requerimento na ANM = 609 mil ha, 392 requerimentos protocolados". O SIGMINE usado no próprio site dá 124 requerimentos e 196 mil ha para terras raras, e 4.360 requerimentos e 1,57 milhão de ha somando tudo. Pode ser outro recorte (outros minerais críticos, outra data), mas a tela não diz qual nem de onde vem o número.

**Como foi conferido**

Site real, Mercado, indicadores do topo; data/panorama/panorama.json, seção proc (19/11).

**Situação em 25/11/2026**

Continua: o indicador "609 mil ha" segue na tela sem fonte que o confirme.

**Possibilidades de melhora** (ideias para discutir, não decisões)

- Descobrir de onde veio o número e citar a fonte e o recorte.
- Recalcular com o SIGMINE usado no site.

### p27 · Operações sem data e sem fonte; notícia antiga em 'doze meses'

**Onde:** Painel › Mercado › "Operações e alvos em Goiás" e "O que mexeu no setor"  
**Tipo:** Problema · **Urgência:** Baixa · **Status:** Aberta · **Responsável:** a definir

**O que acontece**

Em 'Operações e alvos em Goiás', nenhuma operação tem data nem fonte própria; os 4 indicadores do topo também não dizem a fonte de cada número. As fontes ficam só numa lista geral de 9 links. E 'O que mexeu no setor' diz 'movimentos dos últimos doze meses', mas inclui notícia de fev/2025. Os dados foram consultados até 17/09/2026.

**Como foi conferido**

Site real, Mercado (19/11); public/data/mercado/mercado_v1.json.

**Situação em 25/11/2026**

Sem mudança nos dados do Mercado desde 19/11.

**Possibilidades de melhora** (ideias para discutir, não decisões)

- Dar data e fonte a cada operação e a cada indicador.
- Trocar "últimos doze meses" pelo período real, ou tirar a notícia antiga.
- Mostrar até quando os dados foram consultados (17/09/2026).

### p28 · Carteira de projetos do Mercado em português na versão em inglês

**Onde:** Painel › Mercado › carteira de projetos (versão em inglês)  
**Tipo:** Problema · **Urgência:** Baixa · **Status:** Aberta · **Responsável:** a definir

**O que acontece**

Na versão em inglês, 44 trechos ficam em português, quase todos na carteira de projetos: evidências e situação (ex.: 'Ramp-up comercial concluído', 'Licença de Operação SEMAD-GO', 'A Hochschild confirmou o início da produção comercial...').

**Como foi conferido**

Site real, Mercado em inglês (19/11).

**Situação em 25/11/2026**

Conferido em 25/11 em inglês: a carteira continua em português.

**Possibilidades de melhora** (ideias para discutir, não decisões)

- Ter os campos da carteira nos dois idiomas no pacote de dados.
- Avisar, na versão em inglês, que o conteúdo da carteira está só em português.

### ~~p29 · Nomes de alunos e caminhos internos na tela do Mercado~~

**Onde:** Painel › Mercado › rodapé e fonte da carteira  
**Tipo:** Problema · **Urgência:** Baixa · **Status:** Resolvida em 26/11/2026 (commit b54b079) · **Responsável:** a definir

**O que acontece**

O rodapé e a fonte da carteira mostram "Squad 1 · Estudante 3 (Gabriel Gonçalves)", "Squad 1 · aluno Lucas Maia", o caminho "Squad 1/Dados brutos/Aluno Lucas Maia/projetos_minerais_goias.xlsx" e "Pacote gerado por scripts/build_projetos_go.py". É informação interna da equipe, com nome de pessoas, numa tela para o cliente.

**Como foi conferido**

Site real, Mercado, rodapé e fonte da carteira (19/11).

**Situação em 25/11/2026**

Conferido em 25/11: continuam "aluno Lucas Maia", "Estudante 3 (Gabriel Gonçalves)" e o nome do script.

**Possibilidades de melhora** (ideias para discutir, não decisões)

- Creditar "Equipe MINERA Goiás" e deixar a autoria no documento do trabalho.
- Tirar caminho de arquivo e nome de script (ver p30).

**O que foi feito**

26/11/2026, commit b54b079: as linhas de fonte do Mercado deixaram de mostrar nome de aluno, pasta e script. Agora dizem "Fonte: levantamento do projeto em fontes públicas, consultado até 04/10/2026" (carteira de projetos) e "Levantamento do projeto com dados públicos consultados até 2026-09-17. Não é recomendação de investimento." A nota do Mercado também deixou de citar o Squad 1. Em public/i18n.js (PT e EN) e public/data/mercado/mercado_v1.json.

Os nomes continuam no campo "autoria" dos arquivos de dados, mas não aparecem mais na tela.

### p52 · Empresas com valores em português na versão em inglês

**Onde:** Painel › Empresas (versão em inglês)  
**Tipo:** Problema · **Urgência:** Baixa · **Status:** Aberta · **Responsável:** a definir

**O que acontece**

Em inglês, a interface está traduzida, mas valores dos dados ficam em português: "beneficiada", "pessoa física (nome não publicado)", "(nome não informado no CFEM — CNPJ raiz …)" e notas como "A carga da CMOC na CCEE vem declarada em três ramos…".

**Como foi conferido**

Cópia do site com o código de 25/11, Empresas em inglês.

**Situação em 25/11/2026**

Encontrada na 2ª rodada (25/11/2026).

**Possibilidades de melhora** (ideias para discutir, não decisões)

- Traduzir pelo dicionário os valores que se repetem (ex.: "beneficiada", "pessoa física (nome não publicado)").
- Ter as notas longas nos dois idiomas no pacote de dados.

### p51 · Comércio exterior com texto em português na versão em inglês

**Onde:** Painel › Comércio exterior (versão em inglês)  
**Tipo:** Problema · **Urgência:** Baixa · **Status:** Aberta · **Responsável:** a definir

**O que acontece**

Em inglês, ficam em português a descrição da fonte ("Registro administrativo de despacho aduaneiro. É o que foi declarado à Receita…") e o quadro "O que esta base não mede" ("Produção: o que embarca num mês pode ter sido lavrado meses antes…").

**Como foi conferido**

Cópia do site com o código de 25/11, Comércio exterior em inglês.

**Situação em 25/11/2026**

Encontrada na 2ª rodada (25/11/2026).

**Possibilidades de melhora** (ideias para discutir, não decisões)

- Levar esses textos fixos para o dicionário de tradução do site.

## Ranking por Indicador, Radar, Território e Metodologia (8)

### p53 · Ranking por Indicador sem fonte, sem data e fora da Base de dados

**Onde:** Painel › Ranking por Indicador  
**Tipo:** Problema · **Urgência:** Média · **Status:** Resolvida em parte em 26/11/2026 (commit 7a1c51f) · **Responsável:** a definir

**O que acontece**

A aba diz só "ano-base 2025": não há linha de fonte (CFEM e processos da ANM, PIB e população do IBGE) nem data de atualização. Os dados (indicadores municipais e população estimada do IBGE) também não estão na aba Base de dados.

**Como foi conferido**

Cópia do site com o código de 25/11; data/catalogo/catalogo.json (17 bases, nenhuma de indicadores).

**Situação em 25/11/2026**

Encontrada na 2ª rodada (25/11/2026).

**Possibilidades de melhora** (ideias para discutir, não decisões)

- Uma linha de fonte e data na aba (CFEM e processos da ANM; PIB e população do IBGE).
- Cartões no catálogo da Base de dados para esses dados.

**O que foi feito**

26/11/2026, commit 7a1c51f: a aba Base de dados foi refeita. Cartões curtos, um quadro de detalhes com a documentação de cada base (tirada do README dela, sem anotação interna) e o botão Baixar, só para quem está logado. O catálogo passou de 17 para 25 bases.

Os indicadores municipais entraram na Base de dados, com documentação nova (data/indicadores/README.md) e download.

**O que ainda falta**

- A aba Ranking por Indicador continua sem linha de fonte e sem data de atualização.

### ~~p37 · Bases do Território fora da Base de dados~~

**Onde:** Painel › Base de dados (catálogo) e Território e emissões  
**Tipo:** Problema · **Urgência:** Média · **Status:** Resolvida em 26/11/2026 (commit 7a1c51f) · **Responsável:** a definir

**O que acontece**

Nenhuma base da aba Território e emissões aparece no catálogo da Base de dados: o relatório e a camada de risco (1.046 projetos), o MapBiomas (cobertura, Coleção 11, e Solo, Coleção 2) e o SEEG 12. A aba também não diz de quando é o material (novembro de 2026).

**Como foi conferido**

Site real, Território e emissões e Base de dados (19/11).

**Situação em 25/11/2026**

Continua: as bases do Território não estão no catálogo.

**Possibilidades de melhora** (ideias para discutir, não decisões)

- Cartões no catálogo para o relatório e a camada de risco, o MapBiomas e o SEEG.
- Escrever na aba de quando é o material.

**O que foi feito**

26/11/2026, commit 7a1c51f: a aba Base de dados foi refeita. Cartões curtos, um quadro de detalhes com a documentação de cada base (tirada do README dela, sem anotação interna) e o botão Baixar, só para quem está logado. O catálogo passou de 17 para 25 bases.

Entrou o cartão "Mineração e Cerrado em Goiás" (família Território e emissões), com a documentação do material e o download do relatório e da camada de risco.

### p50 · Metodologia com links para o GitHub e informação interna

**Onde:** Painel › Metodologia (aba e 9 sub-abas)  
**Tipo:** Problema · **Urgência:** Média · **Status:** Aberta · **Responsável:** a definir

**O que acontece**

A aba Metodologia, nova, tem dois links para o GitHub ("METODOLOGIA.md ↗" e "HANDOFF.md ↗") e, nas 9 sub-abas, cita "Squad 1/2/3", nomes de scripts (ex.: scripts/build_atlas_base.py), pastas ("Squad 1/Dados brutos", "public/data/mercado/") e "repositório".

**Como foi conferido**

Cópia do site com o código de 25/11 (commit 2906ce9), aba Metodologia; public/metodologia.js.

**Situação em 25/11/2026**

Encontrada na 2ª rodada (25/11/2026).

**Possibilidades de melhora** (ideias para discutir, não decisões)

- Tirar os dois links para o GitHub.
- Citar só as fontes públicas e o método; levar scripts e pastas para o manual técnico.

### p54 · Indicadores por município em dois lugares

**Onde:** Painel › Ranking por Indicador e Atlas e panorama  
**Tipo:** Decisão do grupo · **Urgência:** Baixa · **Status:** Aberta · **Responsável:** a definir

**O que acontece**

O Atlas e panorama tem o quadro "Indicadores por município" e a aba nova se chama Ranking por Indicador. É o mesmo assunto, com nome parecido, em dois lugares.

**Como foi conferido**

Site com o código de 25/11/2026 (commit 2906ce9).

**Situação em 25/11/2026**

Encontrada na 2ª rodada (25/11/2026).

**Possibilidades de melhora** (ideias para discutir, não decisões)

- Manter o assunto num lugar só e pôr um link no outro.
- Manter os dois, com nomes e papéis diferentes e explicados.

### p31 · Rodadas e fases do Radar sem data do retrato

**Onde:** Painel › Radar › rodadas e fases do cadastro  
**Tipo:** Problema · **Urgência:** Baixa · **Status:** Aberta · **Responsável:** a definir

**O que acontece**

A fonte das rodadas é só o caminho de um arquivo interno ("Squad 1/dados/ResultadoRodadaDisponibilidade (1).csv"), sem data de quando a ANM publicou nem de quando foi baixado. As fases do cadastro também não dizem de quando é o SIGMINE (no Atlas é 24/10/2026).

**Como foi conferido**

Site real, Radar (19/11).

**Situação em 25/11/2026**

Conferido no código de 25/11: as rodadas do Radar continuam citando só o caminho interno do arquivo, sem data.

**Possibilidades de melhora** (ideias para discutir, não decisões)

- Escrever "ANM — rodadas de disponibilidade, baixado em dd/mm/aaaa" e "ANM — SIGMINE, dd/mm/aaaa".

### p32 · Radar repete fases e rodadas do Panorama

**Onde:** Painel › Radar e Atlas e panorama › Pesquisa e direitos  
**Tipo:** Decisão do grupo · **Urgência:** Baixa · **Status:** Aberta · **Responsável:** a definir

**O que acontece**

"Processos por fase" e "Rodadas de disponibilidade" do Radar mostram os mesmos números que a sub-aba Pesquisa e direitos do Panorama (8.202 em autorização de pesquisa; 1.097 áreas livres). As notícias também aparecem no Mercado, com outra seleção.

**Como foi conferido**

Site real, Radar e Atlas e panorama > Pesquisa e direitos (19/11).

**Situação em 25/11/2026**

Decisão ainda não tomada em 25/11/2026.

**Possibilidades de melhora** (ideias para discutir, não decisões)

- Deixar fases e rodadas num só lugar e pôr um link no outro.
- Manter nos dois, com papéis diferentes e explicados (Radar para acompanhar mudanças, Panorama para o retrato do momento).

### ~~p56 · Radar com textos explicativos em português na versão em inglês~~

**Onde:** Painel › Radar (versão em inglês)  
**Tipo:** Problema · **Urgência:** Baixa · **Status:** Resolvida em 26/11/2026 (decidido não fazer) · **Responsável:** a definir

**O que acontece**

Em inglês, a interface do Radar está traduzida, mas dois textos explicativos ficam em português: a nota do Cadastro ANM ("Fases e rodadas vêm do cadastro e dos editais da ANM, não de previsão…") e a explicação do ANM × Notícias ("Três contagens da mesma substância, lado a lado…"). Os dois vêm da API (radar_api.py), não do dicionário de tradução.

**Como foi conferido**

Site real, Radar em inglês, conta de administrador (25/11).

**Situação em 25/11/2026**

Encontrada na 2ª rodada (25/11/2026).

**Possibilidades de melhora** (ideias para discutir, não decisões)

- Levar esses dois textos para o dicionário de tradução.
- Ou fazer a API do Radar devolver os textos nos dois idiomas.

**Decisão**

26/11/2026: decidido não fazer. O Kayo decidiu deixar esses dois textos do Radar em português na versão em inglês.

### p55 · Metodologia repetida em três lugares

**Onde:** Painel › Metodologia, Previsão e Território  
**Tipo:** Decisão do grupo · **Urgência:** Baixa · **Status:** Aberta · **Responsável:** a definir

**O que acontece**

A aba Metodologia tem sub-abas da Previsão e do Território, que já têm sub-abas próprias chamadas "Metodologia". O mesmo conteúdo pode ficar em lugares diferentes e sair de sincronia.

**Como foi conferido**

Site com o código de 25/11/2026 (commit 2906ce9).

**Situação em 25/11/2026**

Encontrada na 2ª rodada (25/11/2026).

**Possibilidades de melhora** (ideias para discutir, não decisões)

- Toda a metodologia na aba Metodologia, com links a partir das outras abas.
- Cada aba com a sua, e a aba Metodologia só com o que é geral.

## Gerenciar acessos (3)

### p44 · Não há como recuperar senha esquecida

**Onde:** Painel › Gerenciar acessos e tela de login  
**Tipo:** A desenvolver · **Urgência:** Média · **Status:** Aberta · **Responsável:** a definir

**O que acontece**

A tela de entrada diz "para recuperar o acesso, procure o administrador do projeto", mas Gerenciar acessos só cria e desativa contas: não redefine senha. A redefinição só existe como comando no servidor (deploy/manage-users.py --reset), e ninguém da equipe acessa o servidor. Quem esquecer a senha fica sem acesso.

**Como foi conferido**

Site real, Gerenciar acessos e login.html#senha (19/11); deploy/manage-users.py.

**Situação em 25/11/2026**

Continua: auth.py sem redefinição de senha pela tela.

**Possibilidades de melhora** (ideias para discutir, não decisões)

- Um botão "Redefinir senha" para o administrador, que gera uma senha inicial e obriga a troca no primeiro acesso.
- Recuperação por e-mail (dá mais trabalho).

### p45 · Conta genérica num sistema de 'contas individuais'

**Onde:** Painel › Gerenciar acessos  
**Tipo:** Decisão do grupo · **Urgência:** Média · **Status:** Aberta · **Responsável:** a definir

**O que acontece**

A tela diz "Contas individuais e permissões da plataforma" e "O acesso é individual", mas há só 3 contas e uma delas é genérica ("Usuário - Plataforma"). Conta compartilhada impede saber quem fez o quê e obriga a trocar a senha de todos quando alguém sai do projeto.

**Como foi conferido**

Site real, Gerenciar acessos (19/11).

**Situação em 25/11/2026**

Decisão ainda não tomada em 25/11/2026.

**Possibilidades de melhora** (ideias para discutir, não decisões)

- Uma conta por pessoa.
- Assumir que existe uma conta de consulta compartilhada e ajustar o texto da tela.

### p46 · Desativar sem confirmação e sem como excluir conta

**Onde:** Painel › Gerenciar acessos › botão "Desativar"  
**Tipo:** Sugestão · **Urgência:** Baixa · **Status:** Resolvida em parte em 26/11/2026 (commit 84fdd26) · **Responsável:** a definir

**O que acontece**

Um clique em "Desativar" desativa a conta na hora, sem perguntar. Dá para reativar, então não é grave, mas um clique errado tira o acesso de alguém. E não há opção de excluir conta: a conta de teste "teste.homologacao", criada na avaliação de 19/11, ficou desativada na lista.

**Como foi conferido**

Site real, Gerenciar acessos, teste de 19/11.

**Situação em 25/11/2026**

Continua: painel.js desativa a conta sem pedir confirmação.

**Possibilidades de melhora** (ideias para discutir, não decisões)

- Pedir confirmação antes de desativar.
- Se o grupo quiser, permitir excluir contas de teste.

**O que foi feito**

26/11/2026, commit 84fdd26: desativar uma conta agora pede confirmação, com o nome da pessoa. Reativar continua direto. Testado na cópia local: cancelar não desativa, confirmar desativa.

**O que ainda falta**

- Não há como excluir uma conta pela tela.

## Servidor, API e robôs (5)

### p41 · Rotas do banco devolvem lista vazia (a "API que não foi criada")

**Onde:** API › /api/projetos, /api/projecoes e /api/fontes  
**Tipo:** Decisão do grupo · **Urgência:** Alta · **Status:** Aberta · **Responsável:** a definir

**O que acontece**

/api/projetos, /api/projecoes e /api/fontes, as únicas rotas que leem as tabelas principais do banco, devolvem lista vazia ([]). As abas funcionam porque a API entrega arquivos JSON do repositório, não consultas ao banco. Isso explica o comentário do professor de que "não há API".

**Como foi conferido**

curl https://labfgv.com.br/api/projetos (19/11).

**Situação em 25/11/2026**

Decisão ainda não tomada em 25/11/2026.

**Possibilidades de melhora** (ideias para discutir, não decisões)

- Preencher as tabelas do banco com os dados que as abas já usam.
- Tirar essas rotas e deixar claro que a API entrega os pacotes de dados.
- A decisão também afeta o teste da atualização automática (p48).

### p40 · Cabeçalhos de segurança ausentes e página 404 inexistente

**Onde:** Servidor (VPS, configuração do Nginx)  
**Tipo:** Problema · **Urgência:** Média · **Status:** Aberta · **Responsável:** a definir

**O que acontece**

Faltam os cabeçalhos de segurança HSTS, Content-Security-Policy e X-Frame-Options, e um endereço que não existe devolve a página inicial com status 200 em vez de "página não encontrada" (404). As duas coisas se resolvem na configuração do Nginx na VPS, que a equipe não acessa. Em 19/11 a configuração guardada no repositório (deploy/labfgv.com.br.conf) passou a pedir 404, mas ainda não foi aplicada no servidor.

**Como foi conferido**

curl -I https://labfgv.com.br/ e /pagina-que-nao-existe (19/11).

**Situação em 25/11/2026**

Conferido no site real em 25/11: continuam faltando HSTS, CSP e X-Frame-Options, e endereço inexistente devolve 200. Novidade: em 19/11 a configuração do repositório (deploy/labfgv.com.br.conf) passou a pedir 404, mas ainda não foi aplicada na VPS.

**Possibilidades de melhora** (ideias para discutir, não decisões)

- Pedir ao professor que aplique na VPS a configuração que já está no repositório (deploy/labfgv.com.br.conf), que pede 404.
- No mesmo pedido, incluir os cabeçalhos HSTS, CSP e X-Frame-Options.

### p42 · Robô mensal das bases falhou em 01/11

**Onde:** GitHub Actions › robô mensal das bases (robo-bases.yml)  
**Tipo:** Problema · **Urgência:** Média · **Status:** Aberta · **Responsável:** a definir

**O que acontece**

A execução de 01/11 do robô mensal das bases parou porque o MapBiomas recusou o download (erro HTTP 401, acesso não autorizado). Não houve nova execução depois disso. A próxima é em 01/12 e deve falhar igual se nada mudar.

**Como foi conferido**

GitHub Actions, workflow robo-bases.yml, execução de 01/11.

**Situação em 25/11/2026**

Conferido no GitHub em 25/11: não houve nova execução depois da falha de 01/11; a próxima é em 01/12.

**Possibilidades de melhora** (ideias para discutir, não decisões)

- Verificar se o MapBiomas passou a exigir chave ou mudou o endereço, e ajustar antes de 01/12.
- Depois do ajuste, rodar o robô à mão para conferir.

### p47 · Nenhum robô avisa quando falha

**Onde:** GitHub Actions (todos os robôs)  
**Tipo:** A desenvolver · **Urgência:** Média · **Status:** Aberta · **Responsável:** a definir

**O que acontece**

Os robôs (notícias, bases, derivados) não têm aviso de falha. O robô das bases falhou em 01/11 e ninguém percebeu por 18 dias.

**Como foi conferido**

.github/workflows (19/11).

**Situação em 25/11/2026**

Conferido em 25/11: nenhum workflow tem aviso de falha.

**Possibilidades de melhora** (ideias para discutir, não decisões)

- Abrir uma issue no GitHub automaticamente quando um robô falhar.
- Mandar e-mail para a equipe.

### p48 · Teste de troca de versão do site é fraco

**Onde:** Atualização automática do site (deploy/deploy.sh)  
**Tipo:** Problema · **Urgência:** Média · **Status:** Aberta · **Responsável:** a definir

**O que acontece**

A atualização automática só troca o site para a versão nova se /api/projetos, /api/projecoes e /api/fontes responderem; senão volta à anterior. Mas essas rotas devolvem lista vazia e nenhuma aba as usa (ver p41): uma versão com o Atlas, a Previsão ou o login quebrado passaria no teste.

**Como foi conferido**

deploy/deploy.sh, linhas 16 a 33.

**Situação em 25/11/2026**

Continua: deploy/deploy.sh ainda testa só /api/projetos, /api/projecoes e /api/fontes.

**Possibilidades de melhora** (ideias para discutir, não decisões)

- Testar também /api/atlas e a página do painel (com login de teste) antes de trocar de versão.
- Ver junto com a decisão sobre as rotas do banco (p41).

## Resolvidas (6)

Ficam aqui para registro. Todas foram conferidas de novo em 25/11/2026 e continuam resolvidas.

### ~~p15 · Aba sem descrição geral~~

**Onde:** Painel › Atlas e panorama  
**Status:** Resolvida em 19/11/2026 · **Commit:** da344e1 · conferida de novo em 25/11/2026

**O que acontecia**

Não há um texto curto dizendo o que a aba Atlas e panorama traz e como usar. O topo fala só do mapa; o texto do Panorama diz que os gráficos foram 'refeitos com as bases do Squad 1 no GitHub', o que não explica nada ao cliente.

**O que foi feito**

Novo texto de topo da aba (at.lead, PT e EN): o que o mapa mostra, o perfil do município ao clicar, o Panorama por tema, as sub-abas e os filtros. O Panorama ganhou etiqueta "Mineração em números" e um texto que diz o que cada quadro traz. Arquivos: public/i18n.js e public/painel.html. Testes: test_i18n, test_atlas, test_panorama (19 ok) e test_web (8 ok). Conferido no servidor em 19/11.

### ~~p16 · Informação interna da equipe aparece na tela~~

**Onde:** Painel › Atlas e panorama  
**Status:** Resolvida em 19/11/2026 · **Commit:** da344e1 · conferida de novo em 25/11/2026

**O que acontecia**

A tela mostra nome de script ('Pacote gerado ... por scripts/build_panorama_base.py'), pastas do repositório ('Squad 1/Dados brutos'), 'Squad 1', 'GitHub' e 'Estudante 3'. Não é dado sensível, mas é detalhe interno que o cliente não precisa ver. Pessoa física já aparece como 'nome oculto', o que está certo.

**O que foi feito**

A tela da aba deixou de citar "Squad 1", "Estudante 3", "no GitHub", "dados brutos do repositório" e scripts/build_panorama_base.py; as fontes passam a dizer "base consolidada do projeto" e citam só ANM, CCEE e IBGE (public/i18n.js e public/painel.html, PT e EN). Sobra: duas notas da sub-aba Notas ("Squad 1/Dados brutos" e "cópia de trabalho"), que são parte da p02, ainda em decisão. Conferido no servidor em 19/11.

### ~~p18 · Mapa mineral sem descrição da aba~~

**Onde:** Painel › Mapa mineral  
**Status:** Resolvida em 19/11/2026 · **Commit:** 0d471ac · conferida de novo em 25/11/2026

**O que acontecia**

O topo mostra só a etiqueta e o título 'Mapa Mineral de Goiás'. Falta um texto curto dizendo o que o mapa reúne (camadas geológicas, minerárias, de infraestrutura e de áreas protegidas) e como usar (ligar camadas, escolher a camada em análise, filtrar).

**O que foi feito**

Novo texto de topo do Mapa mineral (mp.lead, PT e EN) abaixo do título: o que o mapa reúne (camadas por tema) e como usar (ligar camadas, camada em análise, tabela e indicadores com os filtros, exportação). Arquivos: public/painel.html, public/i18n.js e public/mapa.css. Testes: test_i18n, test_mapa, test_web (41 ok); mapa aberto numa cópia local com os dados reais em PT e EN. Conferido no servidor em 19/11: painel.html e i18n.js novos no ar.

### ~~p19 · Link para o GitHub e arquivo interno citado no Mapa mineral~~

**Onde:** Painel › Mapa mineral  
**Status:** Resolvida em 19/11/2026 · **Commit:** 0d471ac · conferida de novo em 25/11/2026

**O que acontecia**

A linha de fontes tem o link 'Inventário das camadas do P3M (CSV no GitHub)', que leva o usuário para fora do site, e a fonte das barragens cita 'eliel.html', um arquivo interno com nome de pessoa. O inventário pode virar uma tabela no próprio site; a citação deve dizer só 'SIGBM (ANM)' e a data.

**O que foi feito**

public/mapa.js: sem os links do inventário do P3M, do pacote e da série no GitHub (linha de fontes, fichas, CSV e LEIA-ME exportados), sem 'Pasta do Squad 1' e sem caminho de arquivo do repositório; 'Pacote de dados' no lugar de 'Pacote do Squad 1'. Fonte das barragens sem '(eliel.html)' em scripts/mapa_camadas.json e data/mapa/catalogo.json (mesmo texto nos dois, sem regerar). O inventário não virou tabela no site: só a nota '{n} camadas no inventário do P3M; {m} usadas no mapa'. Sobra: a fonte da camada Municípios ainda cita 'base consolidada do Squad 1 (v17)'. Conferido no servidor em 19/11: mapa.js novo no ar, sem nenhum link para o GitHub.

### ~~p33 · Data do SIGMINE errada na Base de dados~~

**Onde:** Painel › Base de dados e Mapa mineral  
**Status:** Resolvida em 19/11/2026 · **Commit:** 199f895 · conferida de novo em 25/11/2026

**O que acontecia**

O cartão do SIGMINE diz 'Extração de 10/09/2026', mas o robô baixou o arquivo em 24/10/2026 (commit 2376b6f) e o Atlas já informa 24/10. A camada de processos do Mapa mineral também diz 10/09. Além disso, o README do Atlas diz 16.656 processos e o arquivo tem 16.875. Corrigir a data no gerador do catálogo e no Mapa mineral, e o número no README.

**O que foi feito**

A data do retrato do SIGMINE passou de 10/09/2026 para 24/10/2026 no gerador do catálogo (scripts/build_catalogo_painel.py), no Mapa mineral (scripts/build_mapa_base.py e scripts/mapa_camadas.json: camadas Processos e Projetos da aba 04 e medidas por município), e o README do Atlas passou a dizer 16.875 processos. Pacotes regerados (data/catalogo e data/mapa). Testes: test_mapa e test_projetos (55 ok), mapa-dados e mapa-shp (573 + 88 ok), Validar plataforma web ok. Conferido no ar em 19/11: /api/catalogo diz 'Extração de 24/10/2026' e '16875 processos'; /api/mapa/catalogo diz 24/10/2026 nas duas camadas e nas medidas. Ficou de fora: os números do data/mapa/README.md calculados sobre o retrato antigo.

### ~~p43 · Biblioteca com falhas conhecidas nos robôs~~

**Onde:** Dependências dos robôs (requirements.txt)  
**Status:** Resolvida em 19/11/2026 (não procedia: nada precisou ser alterado) · conferida de novo em 25/11/2026

**O que acontecia**

O requirements.txt usa soupsieve 2.10, com 3 falhas conhecidas (CVE-2026-126190, -126191, -126193), corrigidas na 3.0.2 e na 4.0.0. Atualizar e rodar os testes dos robôs.

**O que foi feito**

Não procede, nada foi alterado. O soupsieve não aparece em nenhum arquivo de dependências do repositório, nem no código ou no histórico. Ele entra só por tabela (nbconvert → beautifulsoup4) e o GitHub Actions instala a versão mais nova: 4.1.2 no log de 19/11 (Validar motor econômico-energético da Squad 2), que já tem a correção. O 2.10 apontado veio do Python local da avaliação.
