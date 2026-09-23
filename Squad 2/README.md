# Squad 2 — Motor econômico-energético

## Visão geral

A Squad 2 desenvolve o componente econômico-energético do projeto MINERA Goiás.

O objetivo é transformar dados de produção mineral em estimativas transparentes de demanda de energia elétrica para Goiás. A estrutura foi construída para evoluir gradualmente: hoje utiliza as séries históricas disponíveis e, quando houver dados validados, poderá incorporar operações, projetos, expansões e capacidade produtiva.

A Squad 2 possui três componentes complementares:

| Componente | Função | Dados |
|---|---|---|
| `data/demo/` e notebook demo | Demonstra a arquitetura física futura do motor | Sintéticos |
| `intensidade_energetica/` | Calcula e documenta coeficientes estaduais de intensidade energética | CCEE, ANM e fontes empresariais |
| `modello_reale/` | Executa backtest, projeções 2027–2040 e sensitivity analysis | Dados consolidados da Squad 1 e coeficientes da Squad 2 |

A demo permanece no repositório como referência de arquitetura. Os resultados atuais do projeto devem utilizar o **modelo real**.

## Estado atual

O modelo real está integrado e validado automaticamente. Ele:

- lê dados históricos consolidados pela Squad 1;
- cobre cobre, bauxita, níquel, fosfato e amianto;
- utiliza um coeficiente estadual de energia por mineral e base de produção;
- executa backtest de produção;
- projeta três cenários para 2027–2040;
- calcula demanda estimada de energia por mineral, ano e cenário;
- executa análise de sensibilidade das intensidades energéticas;
- publica os resultados como artefatos da GitHub Actions.

## Estrutura

```text
Squad 2/
├── data/
│   └── demo/                         # dados sintéticos da demonstração
├── notebooks/
│   └── Motor_Economico_Energetico_MINERA_Goias.ipynb
├── intensidade_energetica/           # coeficientes e documentação técnica
│   ├── coeficiente_estadual_para_modelo_v1.csv
│   ├── base_intensidade_energetica_v1.csv
│   ├── build_intensidade.py
│   ├── test_intensidade.py
│   └── README.md
├── modello_reale/                    # modelo usado para outputs reais
│   ├── parameters/
│   ├── src/
│   ├── outputs/
│   └── README.md
└── README.md
```

## Fluxo de dados

```text
Squad 1
dados históricos de produção consolidados
    ↓
Squad 2 / intensidade_energetica
coeficientes estaduais e rastreabilidade
    ↓
Squad 2 / modello_reale
backtest, cenários futuros e sensitivity analysis
    ↓
Squad 3
visualização, filtros e interação do utilizador
```

A Squad 1 fornece os dados de produção. A Squad 2 transforma esses dados em resultados econômicos e energéticos. A Squad 3 pode utilizar os outputs para gráficos, tabelas e controles interativos.

## Modelo real

A documentação completa está em:

```text
Squad 2/modello_reale/README.md
```

### Produção histórica

| Mineral | Origem |
|---|---|
| Bauxita, níquel, fosfato e amianto | Interface consolidada da Squad 1 |
| Cobre | Planilha consolidada da Squad 1, aba `08_fato_producao_energia` |

O cobre utiliza conteúdo mineral. Os demais minerais utilizam produção beneficiada. Por esse motivo, as toneladas não são agregadas entre minerais; somente a energia estimada é agregada.

### Coeficientes de intensidade energética

A entrada ativa do modelo é:

```text
Squad 2/intensidade_energetica/coeficiente_estadual_para_modelo_v1.csv
```

Ela contém um coeficiente estadual por mineral, compatível com a base de produção do motor.

| Mineral | Base de produção | Coeficiente de 2025 |
|---|---|---:|
| Cobre | Conteúdo mineral | 8,107848 MWh/t |
| Alumínio (Bauxita) | Produção beneficiada | 1,40 MWh/t |
| Níquel | Produção beneficiada | 11,674042 MWh/t |
| Fosfato | Produção beneficiada | 0,121246 MWh/t |
| Amianto | Produção beneficiada | 0,310942 MWh/t |

Cobre, níquel, fosfato e amianto foram calculados ou estimados a partir de energia observada na CCEE e produção das operações cobertas em 2025. A bauxita permanece identificada como `benchmark_proxy`, pois ainda não há consumo CCEE observado para os produtores identificados.

A correção mais relevante foi a do níquel: o coeficiente anterior estava na base de níquel contido, enquanto o modelo utiliza produção beneficiada de ferroníquel. O novo coeficiente é compatível com a base do modelo.

### Cenários

| Cenário | Ajuste sobre crescimento histórico | Melhoria anual de eficiência |
|---|---:|---:|
| Conservador | -2,0 pontos percentuais | 0,4% |
| Referência | 0,0 pontos percentuais | 0,9% |
| Expansão | +2,0 pontos percentuais | 1,4% |

As hipóteses são explícitas e ilustrativas; não constituem previsão oficial.

## Resultados validados

### Backtest

O backtest avalia a projeção de produção, reservando os dois últimos anos disponíveis como teste.

| Mineral | MAPE |
|---|---:|
| Fosfato | 2,3% |
| Cobre | 3,0% |
| Níquel | 7,8% |
| Amianto | 8,6% |
| Alumínio (Bauxita) | 44,3% |

O resultado da bauxita requer cautela: a queda observada em 2024 não poderia ser antecipada apenas com uma tendência histórica.

### Cenário de referência

Com os coeficientes finais integrados, a demanda estimada de energia dos cinco minerais cobertos é aproximadamente:

- **5,10 TWh em 2027**
- **11,57 TWh em 2040**

Esses resultados representam cenários condicionais às hipóteses do modelo, não consumo observado ou previsão oficial do setor mineral de Goiás.

## Outputs para a Squad 3

| Grupo | Arquivo | Uso |
|---|---|---|
| Backtest | `outputs/backtest/backtest_summary.csv` | Mostrar desempenho por mineral |
| Cenários futuros | `outputs/future/future_projection_by_mineral.csv` | Gráficos por mineral, ano e cenário |
| Cenários futuros | `outputs/future/future_energy_summary.csv` | Total energético por cenário |
| Sensibilidade | `outputs/sensitivity/intensity_sensitivity_contract.json` | Controles interativos por mineral |

A sensitivity analysis permite ajustes de intensidade entre **−10% e +10%**, em passos de 1%, tanto para todos os minerais simultaneamente como para um mineral por vez.

## Demo e futura integração física

A demo representa a arquitetura prevista quando houver dados estruturados de operações e projetos. Ela inclui capacidade, utilização, início de operação, atrasos e captura de mercado, mas utiliza dados totalmente sintéticos.

Para substituir a demo por uma camada física real, serão necessários dados validados de:

- operações existentes;
- capacidade anual;
- projetos e expansões;
- ano de início;
- estágio do projeto: definido, provável ou possível;
- base física da produção;
- fontes e identificadores estáveis.

Esses dados devem respeitar a mesma base de produção do mineral: `rom`, `beneficiada` ou `conteudo_mineral`. Não devem ser combinados sem conversão documentada.

## Automação

A demo é validada por:

```text
.github/workflows/validate-squad2-model.yml
```

O modelo real é validado por:

```text
.github/workflows/validate-modelo-real.yml
```

O workflow do modelo real é acionado quando mudam:

- os scripts ou parâmetros do modelo;
- os coeficientes em `intensidade_energetica/`;
- os dados relevantes da Squad 1;
- o próprio workflow.

Ele executa backtest, cenários futuros e sensitivity analysis, depois publica os três grupos de resultados como artefatos na aba **Actions**.

## Limitações atuais

- A bauxita ainda utiliza benchmark proxy.
- Os coeficientes observados ou estimados referem-se a 2025.
- O modelo ainda não incorpora projetos, expansões, capacidade ou encerramentos reais.
- Não há ainda uma camada macroeconômica de elasticidade entre demanda global e produção de Goiás.
- Não foi realizado backtest de consumo elétrico agregado, pois não existe uma série histórica com o mesmo perímetro de produção.
- A cobertura atual está limitada a cinco minerais.
