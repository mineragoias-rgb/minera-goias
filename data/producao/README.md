# Base de produção por empresa

Números de produção mineral **por empresa**, cada um com o que mede, em que unidade, de que período e de qual fonte. Preenche a lacuna que o
`METODOLOGIA.md` declarava: a CFEM dá quantidade comercializada declarada para fins de arrecadação, e isso **não é produção**.

| Arquivo | Conteúdo |
|---|---|
| `producao.json` | Pacote completo: `meta` (vocabulário, avisos, limitações) e `registros` (as linhas) |
| `producao.csv` | As mesmas linhas em CSV com `;`, para planilha |

Gerado por `python scripts/build_producao_base.py` a partir da curadoria em `producao/base_curada.json`. Conferido por `tests/test_producao.py`.

## O que é uma linha

Uma linha é **um número publicado por uma fonte**, nunca um cálculo. Os quatro campos pedidos — empresa, produção, mineral e unidade — vêm
acompanhados da proveniência sem a qual o número não significa nada aqui:

| Campo | Para quê |
|---|---|
| `medida` | O que o número mede: `minerio_rom`, `contido`, `metal_em_concentrado`, `produto_acabado`, `embarque`, `venda`, `capacidade`, `meta` |
| `escopo` | `operacao_goias`, `consolidado_brasil` ou `consolidado_global` |
| `tipo_valor` | `realizado`, `guidance`, `capacidade` ou `meta` |
| `periodo` / `periodo_tipo` | `2025`, `2025-S1`, `2025-Q3` — e o que essa marca significa |
| `fonte_nome` / `fonte_url` / `fonte_tipo` | De onde veio, com endereço |
| `confianca` | `alta` (número repetido em consultas independentes), `media`, `baixa` |
| `status_validacao` | Nasce `nao_validado`. Validar é ato humano |

## Regras que a base não quebra

**Nada é convertido.** Onça troy, tonelada e quilo convivem sem fator. `kt`, `Mt` e `koz` são lidos como prefixo da mesma grandeza — isso é
definição, não conversão. Ouro em onça nunca vira ouro em quilo.

**Trimestres não somam para formar o ano.** A empresa revisa número no fechamento; três trimestres publicados não são nove meses auditados.

**Consolidado não é Goiás.** Os 4,2 Mt de rocha fosfática da Mosaic e o 1,21 Mt de fertilizantes da CMOC agregam unidades fora do estado, e
estão marcados `consolidado_brasil` justamente para não serem somados ao estado.

**Embarque e venda não são produção.** As 169 mil t de crisotila da SAMA e as 678 t de terras raras da Serra Verde são volume embarcado; as
5.462 t de nióbio da CMOC no 1S25 são volume vendido — e são mais do que as 5.231 t que a mesma empresa produziu no semestre, porque a diferença
saiu de estoque. Embarque e venda podem sair de estoque e podem deixar produção em pátio.

**A regra de corte do produto.** Entra o que sai do minério da própria empresa até o primeiro produto metalúrgico ou químico: minério,
concentrado, ferroníquel, ferronióbio, alumina, ácido fosfórico, fertilizante, fibra. O passo seguinte — alumínio primário e transformados —
fica fora, porque já mistura insumo de terceiros e importado.

**Capacidade e meta não são realização.** Os 80.000 t/ano da Brasil Minérios e os 6.400 t de TREO da Serra Verde são projeto, não produção.

## Por que a ANM não está aqui

**Esta base só traz valor reportado pela própria empresa** — release de resultados, relatório anual, ou o que imprensa e agregadores de mercado
reproduzem dessas publicações. Número apurado por agência reguladora não entra, e `agencia_oficial` nem existe no vocabulário de `fonte_tipo`:
a curadoria que o declarar é recusada na geração.

Não é desconfiança da ANM — é que os dois medem coisas diferentes e a diferença é grande:

| Substância, Goiás, 2025 | Anuário Mineral (ANM) | O que a empresa publica |
|---|---|---|
| Níquel | 35.487,71 t de Ni **contido no minério lavrado** | Anglo American: 39.700 t de **níquel contido no ferroníquel** que saiu das plantas |
| Cobre | 51.937,85 t de Cu **contido** | Chapada/Lundin: 43.974 t de **metal pago no concentrado** |
| Nióbio | 62.626,53 t de **Nb₂O₅ contido** | CMOC: 10.348 t de **produto de nióbio vendável** |

Contido no minério, metal recuperado no concentrado e produto químico acabado são três grandezas: entre elas estão a recuperação metalúrgica e
a estequiometria do óxido. Colocar as duas colunas lado a lado sugeriria que uma corrige a outra, e nenhuma corrige.

O Anuário Mineral continua versionado no repositório, em `Squad 1/Dados brutos/ANM - Anuário Mineral Brasileiro (AMB)/`, e é o que o atlas e o
panorama usam. Quem quiser a visão do estado por substância vai lá — não a esta base.

## Limitações desta versão (v1)

- **Nenhuma linha foi lida no documento original.** A coleta saiu de busca na web, num ambiente cujo proxy de egresso bloqueia os sites de RI.
  `fonte_url` é o endereço que a busca atribuiu ao número. Conferir cada um é a primeira tarefa do agente semanal, que roda na VPS com rede.
- **Cobertura parcial.** 78 registros de dez empresas, as de maior CFEM do estado, cobrindo 2022 a 2027 (realizado, guidance, capacidade e
  meta). Calcário, brita, areia e água mineral — muitos titulares, nenhum com publicação de volume — ficaram de fora.
- **A série de cada empresa tem densidade diferente.** Chapada e CMOC têm ano e trimestre desde 2022; Mara Rosa só existe desde 2024; a Serra
  Verde era fechada e não publicava volume, então o que há dela é embarque noticiado.
- **Buracos conhecidos**, já marcados nas observações: ouro anual de Chapada em 2025, realizado anual de Mara Rosa em 2025, bauxita de Barro
  Alto em 2025 e produção (não embarque) da Serra Verde em qualquer ano.
- **Mudança de controle no meio da série.** Serra Grande passou da AngloGold à Aura em 12/2025; a Serra Verde foi comprada pela USA Rare Earth
  em 04/2026; o níquel da Anglo American está em venda à MMG. Antes de montar série histórica, confira o operador do período.
