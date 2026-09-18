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

**Energia.** A CCEE versionada no repositório cobre ago. e out.–dez. de 2024, jun.–dez. de 2025 e jan.–jul. de 2026. O anualizado é
`observado ÷ meses observados × 12`. Em 2024 isso significa multiplicar quatro meses por três: a linha sai marcada como estimativa frágil, e a
marca aparece no painel.

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

**Quando a carga move mais de um mineral, a energia não é rateada.** Chapada faz cobre e ouro do mesmo minério e da mesma usina; a CMOC move
nióbio e fosfato em Catalão e Ouvidor. Nesses casos o coeficiente sai com `energia_exclusiva: false` e significa *toda a energia da empresa por
unidade daquele mineral* — não a energia daquele circuito. O painel pinta essas barras em outra cor e escreve isso embaixo.

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
- **2022 e 2023 não têm energia**: a base CCEE do repositório começa em agosto de 2024. As linhas desses anos aparecem com produção e sem
  coeficiente, de propósito.
- **Quatro empresas têm energia e nenhum coeficiente** — Mosaic, Serra Verde, Brasil Minérios e, em alguns anos, outras — porque não há produção
  publicada no recorte de Goiás para o ano. É onde a base de produção precisa crescer, e o painel mostra isso em vez de esconder.
