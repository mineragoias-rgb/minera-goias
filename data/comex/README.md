# Comércio exterior dos minerais de Goiás

O que Goiás embarcou para fora e o que trouxe de fora, mineral a mineral, mês a mês, **como foi declarado à aduana**.

| | |
|---|---|
| **Origem** | Comex Stat — Ministério do Desenvolvimento, Indústria, Comércio e Serviços (MDIC) / Secretaria de Comércio Exterior (SECEX) · <https://comexstat.mdic.gov.br/> |
| **Como chega** | `comex/coleta.py` consulta a API pública `api-comexstat.mdic.gov.br` |
| **Período** | 2019 a outubro de 2026 (o último mês é o que a própria fonte diz ter publicado) |
| **Onde vive** | `comex/bruto/*.json` → `data/comex/comex.json` e `.csv` · API autenticada `/api/comex` |
| **Aba no painel** | Comércio exterior, abaixo de Empresas |

## Como se reconstrói

```bash
python3 comex/coleta.py --check    # pergunta à API até que mês ela publicou
python3 comex/coleta.py            # regrava comex/bruto/
python3 scripts/build_comex_base.py
python3 -m unittest tests.test_comex
```

A coleta leva poucos minutos e não precisa de nada instalado: só biblioteca padrão, como o agente semanal de produção.

## O que a base mede

Valor FOB em dólares e peso líquido em quilos, por NCM, por mês, com Goiás como UF da operação. Nada mais.

**Despacho aduaneiro não é produção.** Uma mina pode lavrar num ano e embarcar no outro; um embarque pode sair por Goiás
sem ter sido lavrado em Goiás. O peso é o do **produto embarcado**, não o do metal contido: ferro-níquel não é níquel, e
concentrado de cobre não é cobre. O valor FOB é o preço declarado na saída, não a receita reconhecida pela empresa. E o
Comex Stat **não publica quem exportou** — a ligação com uma operação, nesta base, vem do município e das outras bases do
projeto, nunca da aduana.

O `US$/kg` que a base calcula é **preço implícito**: valor declarado dividido por peso declarado. Ele se move com teor,
forma e contrato, e não é cotação de mercado.

## O recorte crítico, e por que a classificação federal está como NA

A base **não atribui a nenhum mineral uma classificação legal que não leu**.

O texto oficial da lista federal — a Resolução da Secretaria de Geologia, Mineração e Transformação Mineral do MME
nº 2, de 18 de junho de 2021, e a Política Nacional de Minerais Críticos e Estratégicos — não pôde ser lido do ambiente
em que esta base foi montada: o Diário Oficial (`in.gov.br`) e o Planalto recusam cliente automatizado, e as duas vias de
leitura disponíveis aqui falharam. Resumos de busca davam listas que não batiam entre si. Por isso
`meta.criticidade.classificacao_federal` vale **`NA`**, e isso aparece na tela, não só aqui.

O recorte crítico desta base é, então, **o do próprio projeto**: um mineral entra como crítico quando o marco estadual de
minerais críticos, como a aba Mercado o registra (`public/data/mercado/mercado_v1.json`), nomeia uma operação ou um alvo
daquele mineral em Goiás. São seis: **cobre, níquel, nióbio, terras raras, titânio e fosfato**. O gerador confere esse
vínculo mineral a mineral e **recusa a base** se o termo sumir do arquivo do Mercado — a afirmação "este mineral é
crítico" não pode sobreviver à fonte que a sustenta.

Os demais ficam em duas classes declaradas: `produzido_em_goias` (ouro, amianto, vermiculita, manganês, bauxita) e
`insumo_importado` (enxofre).

Quando o texto oficial estiver legível, a classificação federal entra como um campo a mais — não substitui este recorte,
que continua sendo o do projeto.

## Duas armadilhas da API, e o que as trava

**1. Período que cruza anos devolve só o acumulado — calado.**
Pedir de `2019-01` a `2026-10` faz a API responder, para **todo** ano, apenas janeiro a outubro. Ela não avisa.
Conferido: a NCM 26030010 (concentrado de cobre) em 2024 volta com **US$ 378,6 mi** nesse formato e com
**US$ 500,3 mi** quando 2024 é pedido sozinho — a diferença é exatamente novembro e dezembro. Por isso `coleta.py` faz
**um pedido por ano**, e `test_os_destinos_somam_a_exportacao_do_ano` fecha destino contra total para que a armadilha não
volte numa recoleta futura.

**2. O detalhe `economicBlock` dobra a soma.**
Um país pertence a mais de um bloco econômico, então a mesma venda volta repetida uma vez por bloco. Conferido no mesmo
recorte: US$ 1.000,6 mi contra os US$ 500,3 mi corretos. A coleta não usa esse detalhe, e um teste garante que ela
continue não usando.

Uma terceira observação, menos armadilha e mais limite: **o código da UF no Comex Stat não é o do IBGE.** Goiás é **53**
na API e 52 no IBGE; 52 na API é Mato Grosso. O código foi descoberto varrendo a API e conferindo o nome devolvido, não
suposto.

## O que ficou deliberadamente de fora

- **Capítulo 31 (adubos e fertilizantes).** São produtos industriais, não minério. Goiás importa cloreto de potássio e
  fosfatos de amônio em volume muito maior que todo o seu comércio mineral — somar os dois leria indústria química como
  mineração e enterraria o nióbio num número de adubo.
- **NCM 26169000, "minérios de outros metais preciosos".** A posição não nomeia o mineral; atribuí-la seria inventar.
- **Platina, paládio e ródio (7110).** Goiás não lavra metais do grupo da platina. O embarque sai de Anápolis e Goiânia e
  é compatível com recuperação industrial, não com mina.
- **Compostos de ouro (2843.30).** Produto químico-farmacêutico, não ouro de lavra.
- **Sucata (7404, 7602, 7204).** Metal que volta, não metal que sai da mina.

## Granularidade do município

A API **recusa** detalhar município por produto: em `/cities`, `ncm` não é um detalhe aceito. O que existe é município ×
**capítulo da NCM**. A base publica isso como é, e a tela diz o capítulo no rótulo. O capítulo 72 reúne ferro-níquel e
ferro-nióbio — eles só se separam porque saem de municípios diferentes (Barro Alto e Niquelândia de um lado, Ouvidor e
Catalão do outro), e essa separação é leitura do município, não medida da fonte.

## O que a base mostrou que o projeto não tinha

A base de produção só registrava embarque onde a imprensa publicou um número avulso. O Comex Stat fecha essa lacuna com
registro oficial e mensal:

- **Terras raras de Minaçu.** Primeira exportação em 2024 (60,3 t, US$ 2,17 mi), salto para **679,0 t e US$ 11,96 mi em
  2025** — número que confirma, por fonte independente, as ~678 t que a imprensa havia atribuído à Serra Verde. Nos dez
  primeiros meses de 2026 são 35,9 t e US$ 1,10 mi. **91,7% do valor foi para a China.**
- **Ilmenita (titânio).** Primeiro embarque em 2025: 500 t. Antes disso, nada — o titânio era alvo, não produto.
- **Concentração de destino.** Nióbio: 49,5% para a China. Amianto: 84,7% para a Índia. Cobre: 42,6% para a Espanha —
  o concentrado vai para fundição europeia, não para a China.
- **Dependência importada.** Goiás trouxe **1,33 milhão de toneladas de enxofre** (US$ 297 mi) no período — insumo da
  cadeia de fertilizantes, maior em peso que a exportação de nióbio e de terras raras somadas.

## Relação com as outras bases

| Base | Relação |
|---|---|
| `data/producao` | O mineral é o mesmo vocabulário. O Comex traz embarque; a produção traz o que a empresa declarou produzir. Não se somam, e nem sempre coincidem no tempo. |
| `data/projetos` | Um projeto que começa a exportar aparece aqui antes de aparecer em relatório anual. A ilmenita de 2025 é o exemplo. |
| `public/data/mercado` | É a fonte declarada do recorte crítico. Se a aba Mercado deixar de nomear um mineral, o gerador recusa a base. |
| `data/panorama` (CFEM) | A CFEM mede quantidade **comercializada declarada para arrecadação**; o Comex mede **despacho**. São duas declarações a órgãos diferentes, com finalidade diferente. Divergência entre elas é esperada e não é erro de nenhuma das duas. |

## Atualização

O Comex Stat publica mensalmente. `comex/coleta.py --check` diz, em uma linha, até que mês a fonte chegou — é a maneira
barata de saber se vale recoletar. O ano corrente fica marcado como **aberto** (`ano_completo: false`) até a fonte
publicar dezembro, e a tela sinaliza isso em toda comparação: **comparar um ano parcial com um ano cheio superestima a
queda.**
