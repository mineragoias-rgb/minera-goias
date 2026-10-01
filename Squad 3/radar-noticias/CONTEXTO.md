# Contexto — por que esta pasta existe

Registro das decisões tomadas na sessão de 17–19/09/2026, para quem pegar isto depois (inclusive eu mesmo daqui a um mês) entender o porquê de cada escolha.

Responsável: Kayo Silva, Estudante 1 da Squad 3 (S3-E1) — banco, arquitetura de dados e API.

## O problema que deu origem a tudo

O repositório já tinha um radar de notícias em `news/`, com 22 fontes em `news/feeds.json`. O README daquele módulo avisava, com todas as letras, que **nenhuma das 22 tinha sido testada contra a rede** — foram montadas a partir do padrão de URL de cada veículo.

O aviso estava certo em desconfiar. Testando as 22:

- **3 estavam mortas:** ANM (404), MME (404) e Mining Weekly (404).
- **1 estava parada:** IBRAM, com a matéria mais recente de quase três meses antes.
- **1 falharia em produção:** Mining.com respondia no navegador, mas devolvia 403 para a user-agent do radar.

Ou seja: o módulo que deveria alimentar a leitura de notícias apontava para fontes inexistentes, e ninguém saberia até alguém abrir o log.

## Decisão 1 — validar tudo contra a rede, sem exceção

Foram testados **cerca de 150 endereços** com requisição real: as 22 existentes e os candidatos novos. Nenhuma URL nesta pasta entrou por dedução de padrão. Cada uma foi buscada, devolveu itens e teve a data da matéria mais recente conferida.

O registro completo está em [RELATORIO_FONTES.md](RELATORIO_FONTES.md), incluindo o que **não** serve e por quê. Isso é deliberado: sem esse registro, daqui a três meses alguém reinsere a ANM achando que faltou.

**Achado estrutural:** todo o padrão de RSS do `gov.br` saiu do ar. Foram testadas 12 variantes de caminho em ANM, MME, ANEEL e MDIC — todas devolvem 404 com o mesmo `{"error_type": "NotFound"}`. Não é erro de digitação de ninguém; a plataforma tirou os feeds. O contorno adotado foi uma busca do Google News com `site:gov.br/anm`, que responde.

## Decisão 2 — manter energia, mas etiquetada

A lista cobre mineração e também energia, porque o projeto tem o motor econômico-energético da Squad 2. A dúvida era se energia poluiria o escopo.

Decisão: **manter, com o campo `tema`**. São 5 fontes num conjunto de 63 — ruído desprezível — e a Squad 2 precisa do dado. Etiquetadas, saem com um filtro (`tema != 'energia'`) sem reprocessar nada.

Daí nasceu o terceiro eixo de filtro. Já existiam `tipo` (editor/busca) e `escopo` (regional/nacional/setorial/internacional); `tema` (mineracao/energia/geral) foi acrescentado nesta sessão.

## Decisão 3 — aproveitar o código, não reescrever

O `news/radar.py` foi revisado linha a linha. Veredito: **arquitetura boa, quatro defeitos pontuais**. Os quatro estão documentados com evidência em [RELATORIO_REVISAO.md](RELATORIO_REVISAO.md).

O `radar.py` desta pasta é uma **cópia corrigida**, não uma reescrita. Cerca de 10 linhas mudaram num arquivo de 371. Se o desenho fosse ruim, aí sim teria sido do zero — não era o caso.

## Decisão 4 — pasta separada, declarada sucessora

O trabalho não foi aplicado por cima de `news/`. Motivos:

1. O `news/` está instalado na VPS. Mexer nele sem querer afeta o que já roda.
2. Aquele código veio do mesmo lote não auditado que gerou a lista de fontes furada. Uma cópia revisada e assinada é diferente de um patch sobre código que ninguém conferiu.
3. Na rubrica da Entrega 1, `Squad 3/radar-noticias/` é contribuição identificável do S3-E1. Commit em `news/` na raiz se dilui.

**O custo, que é real:** duas cópias do mesmo programa no mesmo repositório divergem. Daqui a três semanas ninguém lembra qual a VPS roda, e alguém corrige um bug na errada.

Por isso a escolha foi **sucessora declarada**, não convivência indefinida: o README diz explicitamente que este módulo substitui o `news/`, e quando este for validado em produção, o `news/` é removido de uma vez. A duplicação é temporária e datada, não permanente.

## Decisão 5 — desligar a leitura de alta/baixa

O protótipo antigo tentava ler nas manchetes se a imprensa apontava preço para cima ou para baixo, e gerava um veredito semanal por substância. Essa camada foi **desligada**.

O que levou a isso, em ordem:

1. Rodando a coleta real, apareceu um erro claro: a manchete *"copper, silver prices plummet and gold slides"* foi arquivada como **cobre em alta e ouro em alta**. A causa é mecânica — `rally` está na lista de palavras de alta, e `plummet` e `slides` não estão em lista nenhuma.
2. Investigando o conserto, ficou claro que ampliar o léxico **cria outro erro**: com as palavras que faltam acrescentadas, "preço do lítio não deve subir" passa a gerar sinal de alta. Cobertura e negação teriam que ser resolvidas juntas.
3. Aí veio a pergunta certa, do Kayo: **alguém pediu isso?** Não. Nem a rubrica, nem outro squad. O que a rubrica pede é rastreabilidade até a fonte, e o acervo de matérias já entrega isso sozinho.
4. O léxico e a própria ideia de classificar direção **não foram criados nesta sessão** — vieram inteiros do `news/feeds.json` antigo, do mesmo lote gerado por IA que motivou toda a revisão. Eu tinha preservado o desenho sem questionar se o objetivo fazia sentido.

Então a camada saiu. Mas **não foi apagada**: `analyse()` e `trends()` continuam no `radar.py`, sob um interruptor `sinais_de_direcao` no `feeds.json`, hoje `false`. Se um dia a direção for pedida, o código está meio caminho andado — e o README lista o que precisa ser arrumado antes de ligar.

**O que ficou no lugar:** a marcação de substância, que antes só existia como efeito colateral da direção. Agora é coisa própria, na tabela `news_item_commodities`. Ela diz que a matéria cita níquel ou terras raras — isso é fato, está escrito no texto, e serve de filtro na página. Como não depende mais de haver palavra de direção na mesma frase, a cobertura até melhorou: o nióbio, por exemplo, passou a ser marcado.

A régua que sobrou é simples: **o que está ligado é verificável, o que interpreta está desligado.**

## Decisão 6 — separar "cita Goiás" de "é do setor"

Ao olhar o preview pela primeira vez, a primeira matéria listada como regional era *"Leonardo fica 21 dias sem beber e Poliana comemora"*. O radar contava **487 matérias de Goiás**, e esse número teria ido para o relatório.

A causa: a marca `regional` só exige o nome do estado no texto, e o G1 Goiás publica futebol, polícia e celebridade. Das 487, só 96 citavam alguma substância.

Foram medidos quatro critérios antes de escolher:

| Critério | Resultado | Veredito |
|---|---|---|
| Goiás + substância | 96 | Estrito demais: perde "protestam pelos riscos das empresas de mineração" |
| Goiás + fonte setorial (`tema`) | 336 | Circular: usa o julgamento do Google, não o texto. Difícil de defender |
| Goiás + termo do setor no texto | 185 | Bom, mas poluído pelos termos de energia |
| **Goiás + (substância mineral OU termo de mineração)** | **174** | **Escolhido.** Só o título é lido; ver abaixo |

`tema` foi descartado como critério apesar de ser o de maior cobertura: ele é propriedade da **fonte**, não da matéria. Dizer "é notícia de mineração porque veio de uma busca por mineração" é circular, e num relatório isso não se sustenta.

Energia ficou de fora da marca `setorial` por medição, não por gosto: `energia` e `elétrica` são palavras do cotidiano e traziam alerta de tempestade e gado eletrocutado para a contagem de mineração. Os termos continuam em `contexto_energia`, e as substâncias energéticas em `substancias_energeticas`.

**Três falhas de léxico foram encontradas e corrigidas no caminho:**

1. `terras-raras` com hífen não casava com `terras raras`. O `fold()` passou a tratar hífen como espaço.
2. `garimpo` e `minerais críticos` não estavam em lugar nenhum — matéria sobre garimpo ilegal em Goiás e sobre o marco dos minerais críticos passava batido.
3. `minerais` sozinho foi testado e **rejeitado**: casava com "formações geológicas raras" numa matéria de turismo.

O resultado virou coluna `setorial` em `news_items`, calculada na coleta, para a API e a página poderem filtrar sem refazer conta.

**Correção posterior, com o site já no ar:** a marca lia título e resumo, e uma matéria da Lotofácil apareceu no painel como notícia de mineração. A causa era uma "casa lotérica Águia de Ouro Goiânia" no resumo — entulho que o Google News raspa da página. A marca passou a ler só o título. Medido: 176 para 174, e as duas perdidas eram essa e um banner de "crie uma conta para salvar localizações".

## Decisão 7 — publicar por arquivo no repositório, não por instalação na VPS

O desenho inicial copiava o módulo antigo: SQLite em `/var/lib/`, serviço systemd, instalação manual como root. Isso estava errado para este projeto, e o motivo é simples: **ninguém da equipe tem acesso à VPS.**

O mecanismo certo já existia e estava à vista. A VPS baixa o **commit inteiro** de `main` a cada dois minutos para uma pasta de versão, e a API já lê um arquivo do repositório — `phase_counts()`, em `radar_api.py`, carrega `data/atlas/processes.json`, 2,6 MB commitados, recacheando quando o `mtime` muda.

Ou seja: para o dado subir, basta ele ser um arquivo no Git.

O fluxo passou a ser:

```
GitHub Actions roda o radar  →  commita data/noticias/latest.json
      →  VPS baixa o commit  →  API lê  →  aba Radar
```

Três mudanças:

1. `radar.py --export` monta o pacote no formato que a API já serve.
2. `.github/workflows/coletar-noticias.yml` roda a coleta diariamente e commita o arquivo.
3. `Squad 3/backend/radar_api.py` lê o arquivo quando existe — **este é arquivo de outra pessoa**, e foram ~25 linhas, com fallback para o comportamento antigo quando o arquivo falta ou está ilegível.

O risco de mexer no `radar_api.py` é contido pelo próprio deploy: ele testa as rotas antes de trocar a versão e restaura a anterior se falhar, conforme `deploy/README.md`. Os três casos foram testados à mão — arquivo ausente, presente e corrompido — e em nenhum a rota quebra.

## Decisão 8 — arrumar a apresentação no painel

Com o site já mostrando as notícias, duas coisas ficaram evidentes: a lista estava feia e não tinha filtro nenhum.

A feiura era **defeito antigo, não da coleta**: o `public/radar.js` sempre emitiu `<b class="rd-tag-go">GOIÁS</b>`, mas `.rd-tag-go` nunca existiu no `style.css`. O gancho estava lá e ninguém escreveu o estilo, então a etiqueta saía como texto colado no título — "GOIÁSAgro, terras raras…".

Foram tocados três arquivos de outras pessoas, com autorização explícita:

| Arquivo | O quê |
|---|---|
| `public/style.css` | Bloco novo no fim, no padrão do bloco de idioma que já existia |
| `public/radar.js` | Busca por título, filtro por substância e por Goiás; etiquetas; corte em 40 linhas |
| `public/i18n.js` | 19 chaves novas, em português e inglês |
| `tests/test_radar_api.py` | Dois testes precisavam saber do arquivo publicado; mais dois acrescentados |

**Três escolhas foram medidas, não chutadas:**

1. **A API manda 180 matérias, não 12.** Com 12 não havia o que filtrar. Foi medido: em 60, o seletor de substância tinha uma opção só; em 180 cabem as 174 de Goiás do setor e sete substâncias diferentes.
2. **A lista desenha 40 por vez.** Cento e oitenta linhas dentro de um painel viram rolagem sem fim.
3. **O filtro "só mineração" só aparece quando há o que filtrar.** Como a seleção já vem ordenada pelo setor, normalmente tudo que chega é do setor e o controle seria um botão morto.

A seção de tendências deixou de ser desenhada quando não há tendência — com a direção desligada, ela era um bloco permanentemente vazio.

**Sobre não quebrar nada:** a mudança em `radar_api.py` fazia dois testes existentes falharem, porque eles verificam o comportamento quando não há coletor e agora existe o arquivo publicado. Os testes foram ajustados para apontar o arquivo para um caminho vazio, que é o que eles de fato querem testar, e ganharam dois casos novos: pacote publicado tem prioridade, e pacote corrompido cai na reserva sem quebrar. A bateria inteira do CI foi executada localmente num ambiente isolado — 55 testes, todos passando.

## Decisão 9 — o acervo passa a ser os arquivos, e a página navega por mês

O desenho da decisão 7 tinha um furo que só apareceu quando o Kayo perguntou se dava para ver as notícias antigas: **o histórico não estava guardado em lugar nenhum durável.** O `latest.json` era sobrescrito a cada coleta, e o banco com as 2.562 matérias vivia só no cache do GitHub Actions, que expira.

Isso importa porque feed RSS é janela rolante. A matéria que sai do feed **não pode ser recoletada** — se o cache sumisse, aquele histórico estaria perdido para sempre.

A correção inverte quem manda: **os arquivos commitados são o acervo**. Cada execução lê o que está lá, funde pelo link e grava de volta. O banco virou só otimização. Testado com banco vazio: as 2.562 sobreviveram.

**Sobre não poluir o repositório.** A primeira tentativa agrupou por mês e gerou **113 arquivos**, a maioria com menos de 1 KB, voltando até 1970 — os feeds carregam material arquivado de décadas atrás. A solução foi uma janela rolante de doze meses: cada um desses tem arquivo próprio, todo o resto se consolida em `anteriores.json`. A pasta nunca passa de treze arquivos, e quando a janela anda o mês que saiu se funde sozinho.

Os arquivos ficam em `public/data/noticias/` porque **só `public/` é servido pelo Nginx**. Isso foi verificado contra o site: caminho fora de `public/` devolve a landing page, não o arquivo. É o que permite a página buscar `/data/noticias/meses/2026-04.json` direto quando alguém escolhe um mês antigo, sem passar pela API.

**Uma regressão apanhada no caminho:** ao reorganizar, o pacote de abertura passou a ser "as 180 mais recentes por data" — e como o G1 Goiás publica de tudo, só **6** delas eram do setor. A abertura voltou a ordenar por Goiás + setor primeiro; os arquivos de mês é que ficam em ordem cronológica.

## Decisão 10 — filtro por município, cartões, e um gráfico que foi descartado

Três coisas foram pedidas para a página analisar melhor. Duas entraram.

**Filtro por município.** O campo `regiao_termo` já viajava até o navegador guardando **qual município casou**, e não aparecia em lugar nenhum. Na abertura de hoje há 21 matérias de Catalão, 5 de Alto Horizonte, 1 de Barro Alto, 1 de Mara Rosa, 1 de Ouvidor. Era o recorte mais valioso do projeto sendo jogado fora. A etiqueta da matéria passou a mostrar o município em vez do "GOIÁS" genérico, e `feeds.json` ganhou `municipios_nome` para a tela escrever "Catalão" e não o termo dobrado "catalao".

**Cartões.** Quatro números no estilo `.metric` que o painel já usa: guardadas, do setor, citam Goiás, Goiás e setor. A frase de texto que repetia os mesmos números foi enxugada.

**O gráfico por mês foi descartado, e vale registrar por quê.** Antes de construir, medi quando cada matéria foi coletada: **todo o acervo tem `first_seen` em setembro de 2026**. Os meses antigos não vieram de coleta diária — vieram de uma varredura única, do que os buscadores ainda guardavam. Setembro aparecia com 16 matérias de Goiás+setor e abril com 37, o que seria lido como "abril foi mais movimentado" quando é puro artefato de coleta.

Eu ia publicar mesmo assim, com uma nota de ressalva. O Kayo mandou cancelar, e estava certo: nota de rodapé não conserta gráfico que induz a conclusão errada. Um gráfico temporal só passa a fazer sentido depois de alguns meses de coleta diária de verdade.

Ficaram de fora também, por decisão de escopo: filtro por veículo e exportação do recorte filtrado.

## Decisão 11 — só notícia do setor é publicada

Ao escolher um mês no painel, apareciam "Cosplayers e gamers combatem caretice goiana", "Comida jogada por visitantes tem causado a morte de peixes" e "Deathground Crack Fix". O Kayo apontou o que eu tinha desenhado errado: **aquilo nunca devia ter chegado ao site.**

Eu estava publicando o acervo inteiro — 2.923 matérias — e filtrando na tela com uma caixa marcada por padrão. Isso é maquiagem: as 1.714 matérias que não são do setor viajavam até o navegador e bastava desmarcar uma caixa para vê-las. E entravam na contagem de "matérias guardadas".

Agora a separação é entre **coletar** e **publicar**. O coletor continua lendo os feeds inteiros, porque veículo regional publica futebol e polícia junto com mineração e não há como pedir só uma parte. Mas o que não é do setor não vira arquivo, não chega ao navegador e não conta em lugar nenhum. É a mesma separação que o projeto já faz entre a zona bruta e a zona tratada.

Resultado: o acervo publicado caiu de 2.923 para **1.209**, todas do setor, 200 delas de Goiás. Nenhuma das manchetes que ele mandou sobreviveu.

Com isso o filtro "Só mineração" perdeu a função e saiu — não há mais o que filtrar. Os cartões passaram a descrever o que existe de fato: matérias do setor, citam Goiás, substâncias citadas, veículos citados. O contador de veículos é lido do acervo, e não do banco, porque o banco é cache e pode estar vazio.

**O custo, que é real:** o que foi descartado não volta. Se um dia o critério do setor ficar mais largo, as matérias que ficaram de fora não estarão lá para serem reclassificadas — feed RSS é janela rolante e não dá para recoletar o passado. Foi decisão consciente: o Kayo foi explícito em que esse material não deveria existir no site.

## O que foi feito nesta sessão

- Validação das 22 fontes antigas e de ~130 candidatas.
- `feeds.json` com 63 fontes verificadas e 10 descartadas com motivo.
- Campo `tema` criado, chegando até o banco.
- Revisão completa do `news/radar.py`, com os 4 defeitos provados por execução.
- `radar.py` corrigido, com a opção `--tema` para restringir a rodada.
- Camada de alta/baixa desligada, com o código preservado sob interruptor.
- Marcação de substância separada e promovida a tabela própria.
- Marca `setorial`, para separar notícia do setor de notícia que só cita Goiás.
- `preview.py`, que gera uma página para conferir a coleta antes de subir qualquer coisa.
- Este conjunto de documentos.

Nada em `news/` foi alterado. O diretório está como estava.

## O que ficou pendente

- **Instalar na VPS** — descartado pela decisão 7. A publicação é por arquivo commitado, sem acesso ao servidor.
- **Confirmar a primeira execução do workflow.** Ele só roda sozinho às 04:00 UTC. Até lá, dá para disparar à mão pela aba Actions. Se o repositório tiver proteção de branch na `main`, o push do robô falha e é preciso liberar o `github-actions[bot]`.
- **Remover o `news/`** depois que este módulo rodar em produção.
- **O texto da contagem na página** vem de `public/radar.js`, que não foi tocado: ele exibe "487 de 2.562 matérias citam Goiás". A frase está correta, mas não é o número de mineração — esse é 174, e está no arquivo exportado como `regionais_setoriais`, ainda sem uso na tela.
- **Filtro por substância e por tema na tela.** O arquivo exportado já leva `tema`, `setorial` e a contagem por substância; falta a página usar.

Deixaram de ser pendência com a decisão 5, e só voltam a ser se a direção for religada: medir o acerto do léxico e deduplicar matéria replicada. A duplicação medida foi de 1,8%, que não atrapalha contagem de acervo.

## Ordem sugerida para retomar

1. Rodar `py radar.py --check` e confirmar que a lista continua de pé.
2. Rodar a coleta num banco local e olhar `news_signals` com olho crítico — é ali que se vê se o léxico presta.
3. Só então pensar em VPS e em página.
