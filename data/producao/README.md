# Base de produção por empresa

Números de produção mineral **por empresa**, cada um com o que mede, em que unidade, de que período e de qual fonte. Preenche a lacuna que o
`METODOLOGIA.md` declarava: a CFEM dá quantidade comercializada declarada para fins de arrecadação, e isso **não é produção**.

| Arquivo | Conteúdo |
|---|---|
| `producao.json` | Pacote completo: `meta` (vocabulário, avisos, limitações), `registros` (as linhas) e `referencia_amb_go` (produção de Goiás por substância, da ANM) |
| `producao.csv` | As mesmas linhas em CSV com `;`, para planilha |

Gerado por `python scripts/build_producao_base.py` a partir da curadoria em `producao/base_curada.json`. Conferido por `tests/test_producao.py`.

## O que é uma linha

Uma linha é **um número publicado por uma fonte**, nunca um cálculo. Os quatro campos pedidos — empresa, produção, mineral e unidade — vêm
acompanhados da proveniência sem a qual o número não significa nada aqui:

| Campo | Para quê |
|---|---|
| `medida` | O que o número mede: `minerio_rom`, `contido`, `metal_em_concentrado`, `produto_acabado`, `embarque`, `capacidade`, `meta` |
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

**Embarque não é produção.** As 169 mil t de crisotila da SAMA e as 678 t de terras raras da Serra Verde são volume embarcado: pode sair de
estoque e pode deixar produção em pátio.

**Capacidade e meta não são realização.** Os 80.000 t/ano da Brasil Minérios e os 6.400 t de TREO da Serra Verde são projeto, não produção.

## Como conferir contra a ANM

`referencia_amb_go` traz, por ano e substância, a produção bruta (ROM) e o contido de Goiás, do Anuário Mineral Brasileiro versionado no
repositório. Serve para conferir **ordem de grandeza**, não para atribuir produção a titular — o Anuário é por estado e substância, sem empresa.

A comparação entre as duas é útil justamente onde diverge. Em 2025, para Goiás:

| Substância | Anuário (contido, estado) | Empresa na base | Por que divergem |
|---|---|---|---|
| Níquel | 35.487,71 t Ni | Anglo American, 39.700 t | O Anuário mede o contido no minério lavrado; a empresa publica níquel contido no ferroníquel que saiu das plantas, que também processam estoque e minério de terceiros |
| Cobre | 51.937,85 t Cu | Chapada/Lundin, 43.974 t | Contido no minério contra metal pago no concentrado: a recuperação metalúrgica fica entre os dois |
| Nióbio | 62.626,53 t Nb₂O₅ | CMOC, 10.348 t | Óxido contido contra produto de nióbio vendável — grandezas químicas diferentes, não é diferença de desempenho |
| Ouro | 6.418,57 kg Au | Serra Grande 2024, 80 koz · Mara Rosa 2025-Q4, 7.067 oz | Unidades diferentes e recortes diferentes; o estado soma produtores que a base ainda não cobre |

Nenhuma dessas divergências foi "corrigida". Elas são o resultado e estão aqui para ser lidas.

## Limitações desta versão (v1)

- **Nenhuma linha foi lida no documento original.** A coleta saiu de busca na web, num ambiente cujo proxy de egresso bloqueia os sites de RI.
  `fonte_url` é o endereço que a busca atribuiu ao número. Conferir cada um é a primeira tarefa do agente semanal, que roda na VPS com rede.
- **Cobertura parcial.** Dez empresas, as de maior CFEM do estado. Calcário, brita, areia e água mineral — muitos titulares, nenhum com
  publicação de volume — ficaram de fora.
- **Buracos conhecidos**, já marcados nas observações: ouro anual de Chapada em 2025, realizado anual de Mara Rosa em 2025, bauxita de Barro
  Alto em 2025.
- **Mudança de controle no meio da série.** Serra Grande passou da AngloGold à Aura em 12/2025; a Serra Verde foi comprada pela USA Rare Earth
  em 04/2026; o níquel da Anglo American está em venda à MMG. Antes de montar série histórica, confira o operador do período.
