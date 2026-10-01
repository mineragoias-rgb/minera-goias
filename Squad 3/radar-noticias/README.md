# Radar de notícias — MINERA Goiás

Coleta diária de notícias sobre mineração e energia, guarda cada matéria com sua origem, data e link, e marca quais substâncias cada uma cita e se fala de Goiás.

> ## Este módulo é o sucessor de `news/`
>
> Ele substitui `news/radar.py` e `news/feeds.json`. Enquanto os dois existirem no repositório, **o que vale é este**.
>
> O módulo antigo não foi apagado de propósito: ele está instalado na VPS e só deve sair depois que este for validado em produção. Quando isso acontecer, `news/` é removido de uma vez — ver [CONTEXTO.md](CONTEXTO.md).
>
> Não corrija bug nos dois. Corrija aqui.

## O que ele entrega

Um acervo de notícias com procedência. Para cada matéria: título, link, data de publicação, o veículo que publicou, quais substâncias ela cita, e se ela fala de Goiás.

Tudo isso é **fato verificável**. A matéria existe, o link abre, a data é a que o veículo declarou, e a substância está escrita no texto ou não está. Não há interpretação nessa camada — é por isso que ela pode ir para a página sem ressalva.

O radar **não produz série de preços**. Ele não cota commodity, não consulta bolsa e não substitui fonte de mercado.

> ### A camada de alta/baixa está desligada
>
> O protótipo antigo também tentava ler nas manchetes se a imprensa apontava preço para cima ou para baixo. Essa camada está **desligada** (`"sinais_de_direcao": false` no `feeds.json`).
>
> Dois motivos. Ninguém pediu: nem a rubrica, nem outro squad. E ela erra de forma medida — a manchete *"copper, silver prices plummet and gold slides"* foi arquivada como **cobre em alta e ouro em alta**, porque `rally` está na lista de palavras de alta e `plummet` e `slides` não estão em lista nenhuma.
>
> O código continua no `radar.py`, adormecido, para a decisão poder ser revista. Antes de ligar, leia os limites no fim deste documento.

## Fontes

`feeds.json` traz **63 fontes**, todas buscadas contra a rede em 17–18/09/2026. O que responde, com contagem de itens, e o que foi testado e descartado estão em [RELATORIO_FONTES.md](RELATORIO_FONTES.md).

| Bloco | Fontes |
|---|---|
| Setoriais de mineração (Brasil) | 7 |
| Jornais de Goiás | 10 |
| Nacionais / economia | 10 |
| Internacionais | 11 |
| Mining.com por substância | 6 |
| Energia | 2 |
| Buscas agregadas | 17 |

O arquivo também guarda um bloco `fontes_descartadas`, com 10 entradas e o motivo de cada uma. É para ninguém reinserir daqui a três meses achando que faltou.

## Os eixos de filtro

Cada fonte declara três campos. Eles existem para a página poder filtrar sem precisar de nova coleta.

| Campo | Valores | Para quê |
|---|---|---|
| `tipo` | `editor`, `busca` | Separa feed do próprio veículo de consulta agregada do Google/Bing |
| `escopo` | `regional`, `nacional`, `setorial`, `internacional` | Alcance geográfico da fonte |
| `tema` | `mineracao`, `energia`, `geral` | Assunto da fonte |

Os três chegam ao banco, na tabela `news_sources`, e são atualizados a cada rodada. Editar `feeds.json` muda o que a página filtra — o radar antigo não fazia isso, ver [RELATORIO_REVISAO.md](RELATORIO_REVISAO.md).

**Para tirar energia do ar**, é `tema != 'energia'`. São 5 fontes: MegaWhat, Power Technology e três buscas. Nada mais depende delas.

Há ainda dois eixos que não vêm da fonte e sim da matéria: a **substância**, em `news_item_commodities`, e o **município**, no campo `regiao_termo` de `news_items`, que guarda qual nome casou.

Na linha de comando dá para restringir a rodada:

```sh
py radar.py --check --tema mineracao --tema geral
```

## O que a página mostra

A aba **Radar** do painel abre com quatro números do acervo, no mesmo estilo dos cartões que já existem ali:

| | |
|---|---|
| Matérias do setor | o acervo publicado, todo ele de mineração |
| Citam Goiás | quantas citam o estado ou um município — **é este o número defensável** |
| Substâncias citadas | quantas substâncias distintas aparecem |
| Veículos citados | quantos veículos diferentes há no acervo |

Abaixo, a lista das mais relevantes, com quatro controles:

- **Busca no título**
- **Mês** — traz o arquivo daquele mês sob demanda, sem recarregar a página
- **Município** — Catalão, Alto Horizonte, Barro Alto, Mara Rosa, Ouvidor e os demais que aparecerem
- **Substância** — níquel, terras raras, lítio…
- **Só Goiás**

Não há filtro de "só mineração" porque não é preciso: nada fora do setor é publicado.

Cada matéria mostra o município (ou "GOIÁS", quando casou só o estado), as substâncias citadas, a data, o veículo e um aviso **via busca** quando o link passa por uma tela do Google antes de chegar ao veículo.

A lista desenha 40 linhas por vez. O resto sai pelos filtros — cento e oitenta linhas dentro de um painel viram rolagem sem fim.

**O que a página deliberadamente não mostra:** gráfico de matérias por mês. Chegou a ser construído e foi descartado — todo o acervo foi coletado de uma vez em setembro de 2026, então um gráfico temporal seria lido como volume de notícia quando é artefato de coleta. Ver a decisão 10 em [CONTEXTO.md](CONTEXTO.md). Só faz sentido depois de alguns meses de coleta diária de verdade.

## Como funciona

1. **Coleta** — lê os feeds RSS/Atom de `feeds.json`. Cada matéria é identificada pelo hash do link, então reexecutar no mesmo dia não duplica nada. Um feed fora do ar não derruba os outros: a execução termina como `partial` e registra o erro na fonte.
2. **Marca a substância** — procura no título e no resumo os termos do bloco `commodities` (níquel, nióbio, terras raras, lítio…), por palavra inteira. Uma matéria pode citar várias, e cada par matéria–substância vira uma linha em `news_item_commodities`.
3. **Marca se é de Goiás e se é do setor** — duas marcas separadas, ver a seção abaixo.

Só isso. Nenhuma etapa interpreta o que a notícia quer dizer.

O casamento é por palavra inteira, e isso importa: com busca por trecho, `ouro` casaria dentro de "tes**ouro**" e uma notícia sobre Tesouro Direto viraria notícia de ouro.

## Duas marcas, e por que são duas

Cada matéria recebe duas marcas independentes. **Elas não significam a mesma coisa, e confundir as duas produz número errado no relatório.**

**`regional`** — a matéria cita o estado (Goiás, goiano, Goiânia…), ou cita um dos vinte municípios mineradores da lista **junto de** um termo do setor. Município sozinho não basta: "Barro Alto" também existe na Bahia.

**`setorial`** — a matéria cita uma substância mineral **ou** um termo de `contexto_mineracao` (mineração, mineradora, minério, lavra, jazida, garimpo, CFEM, ANM, minerais críticos…).

Por que separar: `regional` só pergunta se o estado foi citado. Um veículo estadual como o G1 Goiás publica futebol, política e polícia, e tudo isso vira "regional". Medido na coleta de 19/09/2026:

| | |
|---|---|
| Coletadas | 2.562 |
| Citam Goiás | 487 |
| **Citam Goiás e são do setor** | **174** |

**Use o cruzamento das duas marcas.** "487 notícias de Goiás" é número errado para falar de mineração — entre elas está *"Leonardo fica 21 dias sem beber e Poliana comemora"*.

**Energia fica de fora da marca `setorial`**, de propósito. `energia` e `elétrica` são palavras do cotidiano: com elas dentro, entravam *"Mais de 60 cabeças de gado morrem após fio de energia se soltar"* e um alerta de tempestade. Os termos energéticos continuam em `contexto_energia`, usados pela regra do município, e as substâncias `energia_eletrica` e `gas_natural` estão listadas em `substancias_energeticas` como excluídas da marca.

A comparação é sempre por palavra inteira, e hífen conta como espaço — sem isso "terras-raras" não casava com "terras raras", e uma matéria sobre venda de terras raras em Goiás passava batido.

**A marca `setorial` lê só o título.** O resumo do Google News vem com entulho raspado da página, e uma matéria da Lotofácil entrou na contagem de mineração por causa de uma "casa lotérica Águia de Ouro" citada ali. Medido: descartar o resumo custou 2 matérias em 176 — essa e um banner de "crie uma conta para salvar localizações". A marcação de substância em `news_item_commodities` continua lendo título e resumo, porque ali cobertura vale mais que precisão.

## Tabelas

| Tabela | Conteúdo | |
|---|---|---|
| `news_runs` | Histórico das execuções, versão do radar e relatório completo | em uso |
| `news_sources` | Feeds configurados, último status, última leitura e os três campos de filtro | em uso |
| `news_items` | Matérias com título, link, resumo, data, execução de origem, as marcas `regional` e `setorial`, e `regiao_termo` com o município que casou | em uso |
| `news_item_commodities` | Uma linha por matéria e substância citada | em uso |
| `news_signals` | Um sinal por substância e frase: direção, confiança, evidência e preço citado | **vazia** |
| `news_trends` | Balanço semanal por substância, com score e veredito | **vazia** |

As duas últimas continuam sendo criadas, mas nada escreve nelas enquanto `sinais_de_direcao` for `false`.

## Ver o que foi coletado, antes de qualquer coisa subir

```sh
py preview.py --db radar.sqlite --out preview.html
```

Gera uma página que abre no navegador, offline, com busca por título e filtro por substância, escopo, tema, só do setor, só Goiás e só link direto. O filtro "só do setor" já vem ligado.

É por onde se confere o resultado sem abrir o banco na mão — e serve de imagem para o relatório.

## Executar localmente

```sh
py radar.py --check
```

Testa se cada feed responde e não grava nada. É o primeiro comando a rodar depois de mexer em `feeds.json`.

```sh
py radar.py --db radar.sqlite --report relatorio.json
```

Roda a coleta de verdade num banco local.

```sh
py radar.py --db radar.sqlite --offline-dir ../../tests/fixtures/news
```

Roda sem rede, com as fixtures dos testes.

Só biblioteca padrão do Python — nenhuma dependência para instalar.

## Como isso chega ao site

**Sem ninguém entrar na VPS.** O caminho é o mesmo que `data/atlas/processes.json` já percorre:

```
GitHub Actions roda o radar  →  commita public/data/noticias/  →  a VPS baixa
o commit em até 2 min  →  a API lê  →  aba Radar do painel
```

### Só notícia do setor é publicada

O coletor lê os feeds inteiros — um veículo regional publica futebol e polícia junto com mineração, e não há como pedir só uma parte. Mas **o que não é do setor não é publicado**: não vira arquivo, não chega ao navegador e não entra em contagem nenhuma.

Medido na coleta de 20/09/2026: 2.923 matérias vistas, **1.209 publicadas**, 1.714 descartadas. O campo `descartadas` no `latest.json` registra quantas cada execução deixou de fora.

Antes isso era filtro de tela, com uma caixa marcada por padrão — e bastava desmarcar para ver "Cosplayers e gamers combatem caretice goiana" no painel de mineração.

**O que isso custa:** o descartado não volta. Se o critério do setor ficar mais largo depois, essas matérias não estarão lá para reclassificar, porque feed RSS é janela rolante e não dá para recoletar o passado.

### O acervo são os arquivos, não o banco

Feed RSS é janela rolante: a matéria que sai dele **não pode ser recoletada**. Por isso nada é sobrescrito — cada execução lê os arquivos já commitados, funde o que coletou pelo link e grava de volta. O banco SQLite é só aceleração; se o cache do Actions sumir, o acervo sobrevive e a coleta seguinte soma a ele.

Isso foi testado: exportando com um banco vazio, as 2.562 matérias continuaram lá.

**E o léxico de hoje vale para o acervo inteiro.** A cada exportação as marcas de substância e de setor são recalculadas a partir do título guardado, então corrigir o léxico corrige o passado também — antes, uma correção só alcançava o que fosse coletado depois, e o acervo ficava com dois critérios misturados.

### Como os arquivos são organizados

```
public/data/noticias/
  latest.json              o que a API serve na abertura: 180 matérias + índice
  meses/2026-09.json       um arquivo por mês
  meses/2026-08.json
  …
  meses/anteriores.json    tudo mais antigo que a janela, num arquivo só
```

**A janela é rolante: doze meses individuais, o resto consolidado.** Sem isso o acervo virava 113 arquivos, a maioria com menos de um kilobyte, porque os feeds carregam material de décadas atrás. Com a janela, a pasta nunca passa de treze arquivos, por mais tempo que o radar rode — e quando a janela anda, o mês que saiu dela se funde em `anteriores` sozinho, sem migração manual.

Os arquivos ficam em `public/` porque é o único diretório servido pelo Nginx: o navegador busca `/data/noticias/meses/2026-04.json` direto quando alguém escolhe um mês antigo na tela.

### A abertura não é por data

Os arquivos de mês ficam em ordem cronológica, mas o pacote de abertura não. O painel é de mineração, e por data pura ele encheria de concurso público e futebol do dia — medido: das 180 matérias mais recentes, **6** eram do setor. A abertura ordena por Goiás + setor primeiro.

### As três peças

1. **`radar.py --export-dir public/data/noticias`** monta o acervo e o pacote de abertura, no formato que a API já serve em `/api/radar`.
2. **`.github/workflows/coletar-noticias.yml`** roda a coleta todo dia às 04:00 UTC (01:00 em Brasília) e commita. Dá para disparar à mão pela aba Actions.
3. **`Squad 3/backend/radar_api.py`** lê `latest.json` quando ele existe. Quando não existe, ou está ilegível, cai no comportamento antigo e a aba mostra "coletor não instalado" em vez de quebrar.

O `--db` continua existindo para rodar na mão, com padrão em `/var/lib/minera-goias-radar/`.

## Limites conhecidos

Da camada que está ligada:

- **Homônimo ainda engana, mas menos.** "A regra **cobre** 30% dos contratos" marca a matéria como sendo de cobre, porque ali `cobre` é palavra inteira — é o verbo. Há uma defesa parcial: quando o título traz um termo de `commodities_excecoes` (medalha, olímpico, campeonato…) e nenhum termo de mineração, as substâncias ambíguas `ouro` e `cobre` são descartadas. Foi medido: pegou "Flávia Saraiva é ouro nas assimétricas" e deixou "Gold heads for weekly gain" de pé. Resolver o caso geral exige classe gramatical, não lista de palavras.
- **Título e resumo apenas.** O radar não abre a matéria. O RSS do Google News traz resumo curto, o que reduz o texto disponível.
- **A marca regional é lexical.** Não lê negação nem contexto: "sem relação com a mineração em Catalão" ainda seria marcada como regional. Ela ordena a leitura, não decide relevância.
- **Metade dos links passa pelo Google.** As 17 fontes do tipo `busca` guardam endereço do Google News, que redireciona por JavaScript. Quem clica chega na matéria, mas passa por uma tela antes. O endereço original do veículo não é recuperável: o token do link é opaco. As 46 fontes `editor` têm link direto.
- **Matéria replicada conta mais de uma vez,** e filtro nenhum resolve isso. Medido: 45 repetidas em 2.562, ou 1,8%. Resolver exige comparar títulos por similaridade.

Da camada desligada, se alguém pensar em ligar:

- **O léxico erra de forma comprovada.** "copper, silver prices plummet and gold slides" vira cobre em alta e ouro em alta. Faltam palavras na lista de baixa.
- **Ampliar o léxico sozinho piora outra coisa.** Testado: acrescentando as palavras que faltam, "preço do lítio **não deve subir**" passa a gerar sinal de alta. Cobertura e negação têm que ser resolvidas juntas.
- **Matéria já gravada nunca é relida.** Mudar o léxico só afeta matérias novas, então o banco fica com dois critérios misturados. Não existe comando de reprocessamento.
- **Nunca foi medido.** Ninguém rotulou uma amostra à mão, então não existe taxa de acerto conhecida.
