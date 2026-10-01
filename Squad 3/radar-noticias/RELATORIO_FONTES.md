# Relatório de verificação das fontes

Cerca de **150 endereços** foram buscados contra a rede em 17–19/09/2026. Nenhuma URL deste módulo entrou por dedução de padrão: cada uma foi requisitada, devolveu itens e teve a data da matéria mais recente conferida.

A coluna "itens" é o que o feed devolveu no momento do teste; "última" é a matéria mais recente que ele trazia.

**Resultado da última rodada de `py radar.py --check`, em 19/09/2026: 63/63 fontes responderam.** Para efeito de comparação, a mesma lista rodada com o `news/radar.py` antigo dava 53/63 — a diferença era defeito do coletor, não das fontes. Ver [RELATORIO_REVISAO.md](RELATORIO_REVISAO.md).

---

## Fontes aprovadas — 63

### Setoriais de mineração (Brasil) — 7

| Veículo | URL | Itens | Última |
|---|---|---|---|
| Brasil Mineral | `brasilmineral.com.br/feed` | 40 | 17/09 |
| Revista Minérios | `revistaminerios.com.br/feed/` | 10 | 16/09 |
| Revista Mineração | `revistamineracao.com.br/feed/` | 10 | 16/09 |
| Minera Brasil | `minerabrasil.com.br/feed/` | 10 | 17/09 |
| ADIMB | `adimb.org.br/feed/` | 10 | 18/09 |
| IBRAM | `ibram.org.br/feed/` | 10 | **26/06** |
| Mineração Brasil | `mineracaobrasil.com/feed/` | 40 | **19/05** |

As duas últimas respondem, mas estão paradas. Ficaram na lista com `nota` no `feeds.json` — são institucionais e podem voltar a publicar. Se continuarem assim na próxima revisão, saem.

### Jornais de Goiás — 10

| Veículo | URL | Itens | Última |
|---|---|---|---|
| **G1 Goiás** | `g1.globo.com/rss/g1/go/goias/` | **76–100** | diário |
| Jornal Opção | `jornalopcao.com.br/feed/` | 25 | 17/09 |
| Mais Goiás | `maisgoias.com.br/feed/` | 10 | 18/09 |
| O Hoje | `ohoje.com/feed/` | 12 | 18/09 |
| Portal 6 (Anápolis) | `portal6.com.br/feed/` | 10 | 18/09 |
| Diário de Goiás | `diariodegoias.com.br/feed/` | 10 | 18/09 |
| Sagres Online | `sagresonline.com.br/feed/` | 10 | 18/09 |
| A Redação | `aredacao.com.br/feed/` | 10 | 17/09 |
| Diário da Manhã | `dm.com.br/feed/` | 2 | 17/09 |
| Governo de Goiás | `goias.gov.br/feed/` | 10 | 15/09 |

O G1 Goiás sozinho tem mais volume que todas as outras fontes regionais somadas. É a principal adição desta revisão.

### Nacionais / economia — 10

| Veículo | URL | Itens |
|---|---|---|
| G1 Economia | `g1.globo.com/rss/g1/economia/` | 100 |
| G1 Brasil | `g1.globo.com/rss/g1/brasil/` | 100 |
| Folha · Mercado | `feeds.folha.uol.com.br/mercado/rss091.xml` | 100 |
| Folha · Ambiente | `feeds.folha.uol.com.br/ambiente/rss091.xml` | 100 |
| Agência Brasil · economia | `agenciabrasil.ebc.com.br/rss/economia/feed.xml` | 10 |
| Agência Brasil · últimas | `agenciabrasil.ebc.com.br/rss/ultimasnoticias/feed.xml` | 10 |
| Exame | `exame.com/feed/` | 25 |
| InfoMoney | `infomoney.com.br/feed/` | 10 |
| Poder360 | `poder360.com.br/feed/` | 10 |
| Diário do Comércio (MG) | `diariodocomercio.com.br/feed/` | 10 |

### Internacionais — 11

| Veículo | URL | Itens |
|---|---|---|
| Mining.com | `mining.com/feed/` | 36 |
| Stockhead | `stockhead.com.au/feed/` | 50 |
| The Northern Miner | `northernminer.com/feed/` | 20 |
| International Mining | `im-mining.com/feed/` | 12 |
| Canadian Mining Journal | `canadianminingjournal.com/feed/` | 12 |
| Resource World | `resourceworld.com/feed/` | 12 |
| Mining Technology | `mining-technology.com/feed/` | 10 |
| MiningWatch Canada | `miningwatch.ca/rss.xml` | 10 |
| MetalMiner | `agmetalminer.com/feed/` | 10 |
| Australian Mining | `australianmining.com.au/feed/` | 5 |
| Investing.com · commodities | `investing.com/rss/news_11.rss` | 10 |

A Resource World responde no navegador, mas é lenta e já estourou o timeout de 25 s. Está marcada com `nota` no `feeds.json`.

### Mining.com por substância — 6

Padrão `mining.com/commodity/<nome>/feed/`, 36 itens cada. Foi confirmado que **filtram de verdade**, e não redirecionam para o feed principal: o canal vem como "Nickel Archives", "Gold Archives", com matérias distintas.

`nickel` · `copper` · `gold` · `lithium` · `uranium` · `rare-earth`

As seis escolhidas são as que correspondem ao bloco `commodities` do `feeds.json`. Existem também `iron-ore`, `silver`, `cobalt` e `graphite`, todas testadas e funcionando, caso o escopo aumente.

**`niobium` e `phosphate` não existem** — devolvem "Page not found". Como nióbio é justamente Catalão/Ouvidor, ele só é coberto pelas buscas agregadas.

### Energia — 2

| Veículo | URL | Itens |
|---|---|---|
| MegaWhat | `megawhat.energy/feed/` | 10 |
| Power Technology | `power-technology.com/feed/` | 10 |

Marcadas com `tema: energia`. Para tirar do ar, filtre `tema != 'energia'` — junto com as três buscas de energia, são 5 fontes.

### Buscas agregadas — 17

Padrão do Google News: `news.google.com/rss/search?q=<query>&hl=pt-BR&gl=BR&ceid=BR:pt-419`. Devolvem até 100 itens cada.

**Goiás:** mineração Goiás · níquel e nióbio em Goiás · Niquelândia/Barro Alto/Alto Horizonte · Catalão/Ouvidor · Mara Rosa/Serra Verde · Anglo American/Vale/CMOC em Goiás

**Nacional e regulatório:** terras raras · lítio Brasil · CFEM · ANM lavra/outorga · `site:gov.br/anm`

**Internacional** (`hl=en-US&gl=US&ceid=US:en`): `"rare earth" Brazil` · `mining Brazil source:Reuters`

**Energia:** preço da energia elétrica · energia em Goiás · `site:gov.br/mme energia`

**Bing:** `bing.com/news/search?q=<query>&format=RSS`, 12 itens. Entrou como segundo agregador, independente do Google.

---

## Fontes descartadas — e por quê

Registrado aqui e no bloco `fontes_descartadas` do `feeds.json`, para ninguém repetir o trabalho.

### Todo o RSS do gov.br morreu

Testadas **12 variantes** de caminho em ANM, MME, ANEEL e MDIC — `/RSS`, `/@@rss`, `/rss`, `/feed`, `/rss.xml`, `/@@search_rss` e outras. Todas devolvem 404 com o mesmo corpo:

```
{"error_type": "NotFound"}
```

Não é erro de digitação: a plataforma tirou os feeds do ar. **Contorno adotado:** busca `site:gov.br/anm` no Google News, que responde com 100 itens.

### Sem RSS público

| Fonte | Situação |
|---|---|
| Mining Weekly | 404 em 5 variantes, incluindo `/page/rss-feed/feed:latest-news`, que devolve HTML |
| Notícias de Mineração Brasil | Produto pago da BNamericas |
| O Popular, Curta Mais, Tribuna do Planalto, Folha de Goiás, Investe Goiás | 404 ou HTML |
| Kitco, Fastmarkets, Argus, S&P Global, Reuters (direto), Mining Journal, MINING Magazine, Bloomberg Línea | Sem feed público ou 403 |
| CCEE, ONS, EPE, Senado, Câmara, SGB/CPRM, In-Mine | Sem feed público |

### Respondem, mas não servem

| Fonte | Situação |
|---|---|
| CanalEnergia | XML válido, porém **sem nenhum item** |
| epbr | HTTP 522 — fora do ar nas duas tentativas |
| Brasil Energia, Energia Hoje | HTTP 403 |
| Mining.com · `niobium`, `phosphate` | "Page not found" |

---

## Duas armadilhas de rede que valem registro

Nenhuma das duas tem a ver com a qualidade das fontes — são comportamento de servidor que quebra coletor ingênuo. As duas estão tratadas no `radar.py` desta pasta e detalhadas em [RELATORIO_REVISAO.md](RELATORIO_REVISAO.md).

**1. Não existe user-agent única que atenda a lista.** Os publishers discordam, e discordam em sentidos opostos:

| Site | UA de robô | UA de navegador |
|---|---|---|
| mining.com | 403 | 200 |
| mining-technology.com | 200 | 403 |
| power-technology.com | 200 | 403 |

**2. O G1 devolve gzip de forma intermitente.** Em três tentativas seguidas na mesma URL, duas vieram compactadas e uma veio limpa. É o pior tipo de falha: funciona num dia, some no outro, sem explicação no log.

---

## Como revalidar

```sh
py radar.py --check
```

Imprime uma linha por fonte com tema, escopo, status e contagem de itens, e **não grava nada**. É o primeiro comando a rodar depois de mexer no `feeds.json`, e vale repetir a cada poucos meses: feed morre em silêncio.
