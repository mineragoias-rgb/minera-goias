# Modelo econômico-energético da Squad 2

## Objetivo

Este diretório contém o modelo econômico-energético da Squad 2 para o projeto MINERA Goiás.

O modelo estima a demanda de energia elétrica associada à produção mineral de Goiás entre 2027 e 2040. Ele utiliza as séries históricas consolidadas pela Squad 1, aplica cenários explícitos de crescimento e eficiência energética e produz resultados por mineral, ano e cenário.

Esta é uma versão técnica, reproduzível e integrada aos dados atualmente disponíveis. Os resultados são cenários condicionais às hipóteses e às fontes documentadas; não constituem uma previsão oficial da mineração ou do consumo elétrico de Goiás.

A demonstração inicial da plataforma permanece preservada no repositório. Este diretório é um modelo separado, criado para trabalhar com dados reais consolidados no projeto.

## O que o modelo faz

O modelo realiza quatro funções separadas:

1. Lê e valida a produção mineral histórica consolidada pela Squad 1.
2. Executa um backtest histórico da projeção de produção.
3. Gera cenários futuros de produção e demanda estimada de energia para 2027–2040.
4. Executa uma análise de sensibilidade das intensidades energéticas, preparada para integração na plataforma.

Backtest, cenários futuros e análise de sensibilidade possuem outputs separados para não confundir validação histórica, projeção e teste de hipóteses.

## Cobertura atual

A versão cobre cinco minerais cujas séries de produção e intensidades energéticas puderam ser conciliadas:

| Mineral | Base de produção no modelo | Coeficiente base em 2025 | Natureza do coeficiente |
|---|---|---:|---|
| Cobre | Conteúdo mineral | 8,107848 MWh/t | Calculado |
| Alumínio (Bauxita) | Produção beneficiada | 1,40 MWh/t | Benchmark proxy |
| Níquel | Produção beneficiada | 11,674042 MWh/t | Estimado |
| Fosfato | Produção beneficiada | 0,121246 MWh/t | Estimado |
| Amianto | Produção beneficiada | 0,310942 MWh/t | Estimado |

O nióbio não é incluído nesta versão, porque as unidades e os conceitos de produção disponíveis ainda não puderam ser conciliados com segurança com um coeficiente energético compatível.

As toneladas dos minerais não são agregadas entre si: cobre utiliza conteúdo mineral, enquanto os demais utilizam produção beneficiada. A agregação do modelo é feita somente em demanda estimada de energia, expressa em MWh.

## Estrutura

```text
Squad 2/
├── intensidade_energetica/
│   ├── coeficiente_estadual_para_modelo_v1.csv
│   ├── base_intensidade_energetica_v1.csv
│   ├── build_intensidade.py
│   ├── test_intensidade.py
│   └── README.md
└── modello_reale/
    ├── parameters/
    │   ├── energy_intensity.csv
    │   └── scenarios.csv
    ├── src/
    │   ├── common.py
    │   ├── run_backtest.py
    │   ├── run_future_scenarios.py
    │   └── run_intensity_sensitivity.py
    ├── outputs/
    │   ├── backtest/
    │   ├── future/
    │   └── sensitivity/
    ├── requirements.txt
    └── README.md
```

Os arquivos em `outputs/` são gerados pelos scripts e publicados como artefatos da GitHub Actions.

## Dados de entrada e rastreabilidade

### Produção histórica: Squad 1

O modelo lê diretamente os outputs consolidados pela Squad 1; não cria cópias da base de produção.

| Uso | Arquivo de origem |
|---|---|
| Bauxita, níquel, fosfato e amianto | `Squad 1/Bases consolidadas/documentacao/pacote_squad2/interface_squad1_squad2.csv` |
| Cobre | `Squad 1/Bases consolidadas/documentacao/prototipo_bases_consolidadas_v17.xlsx`, aba `08_fato_producao_energia` |

O cobre é lido diretamente da planilha consolidada porque a medida compatível, `contido_beneficiada`, ainda não está no arquivo de interface utilizado para os outros quatro minerais.

Durante a leitura, o modelo preserva os campos:

- `mineral_id`
- `mineral_name`
- `production_basis`
- `source_id`
- `status_validacao`
- `periodo_referencia`

A execução é interrompida caso existam observações duplicadas, produção ausente ou produção negativa.

### Intensidades energéticas: componente da Squad 2

A entrada ativa do modelo é:

```text
Squad 2/intensidade_energetica/coeficiente_estadual_para_modelo_v1.csv
```

Esse arquivo contém exatamente um coeficiente estadual por mineral e pela mesma base de produção utilizada pelo motor. O modelo lê o contrato de seis colunas:

```text
mineral_id
mineral_name
production_basis
energy_intensity_mwh_t
source_id
data_nature
```

As colunas adicionais do arquivo final preservam rastreabilidade metodológica: ano, operações utilizadas, consumo CCEE, produção, cobertura da produção estadual, intervalo observado, nível de confiança, coeficiente anterior e observações.

O arquivo `parameters/energy_intensity.csv` permanece no diretório do modelo apenas como referência do benchmark anterior. Ele não é mais a entrada ativa do motor e não deve ser sobrescrito.

#### Método de agregação

Para cobre, níquel, fosfato e amianto, os coeficientes foram calculados ou estimados a partir de consumo elétrico observado na CCEE em 2025 dividido pela produção de 2025 das operações cobertas. Quando há mais de uma operação, a agregação é:

```text
coeficiente estadual =
soma da energia observada das operações
÷
soma da produção das operações
```

Isso equivale a uma média ponderada pela produção e evita dupla contagem entre planta e empresa.

| Mineral | Cobertura da produção estadual | Observação |
|---|---:|---|
| Cobre | 100,0% | Chapada/Maracá é a única mina de cobre coberta |
| Bauxita | 0,0% | Sem produtor identificado na CCEE; mantém benchmark proxy |
| Níquel | 97,65% | A parcela não coberta recebe a mesma intensidade estimada |
| Fosfato | 100,0% | Agregação de Mosaic e CMOC/Copebrás |
| Amianto | 100,0% | SAMA é a única operação produtora |

#### Correção de compatibilidade do níquel

O coeficiente anterior de níquel, `45,551351 MWh/t`, referia-se a toneladas de níquel contido. Porém, o modelo projeta produção beneficiada de ferroníquel, que possui uma escala de toneladas aproximadamente quatro vezes maior.

Aplicar o coeficiente anterior diretamente à produção beneficiada superestimava a demanda energética de níquel. O coeficiente de `11,674042 MWh/t` utiliza a mesma base de produção do modelo e elimina essa incompatibilidade de unidade.

A bauxita continua explicitamente identificada como `benchmark_proxy`, pois ainda não há consumo elétrico próprio observado na CCEE para os produtores cobertos.

Detalhes completos da construção, fontes e testes da base estão em:

```text
Squad 2/intensidade_energetica/README.md
```

### Cenários

As hipóteses estão em:

```text
parameters/scenarios.csv
```

| Cenário | Ajuste sobre o crescimento histórico | Melhoria anual de eficiência energética |
|---|---:|---:|
| Conservador | -2,0 pontos percentuais | 0,4% |
| Referência | 0,0 pontos percentuais | 0,9% |
| Expansão | +2,0 pontos percentuais | 1,4% |

Essas hipóteses são `illustrative`: permitem comparar trajetórias de forma transparente, mas não são previsões oficiais.

## Método de projeção

Para cada mineral, o modelo calcula a taxa média anual de crescimento a partir da série histórica disponível.

```text
produção projetada =
produção no último ano observado
× (1 + crescimento histórico + ajuste do cenário)^n
```

A intensidade energética evolui de acordo com a melhoria anual de eficiência definida para cada cenário:

```text
intensidade projetada =
intensidade base
× (1 - melhoria anual de eficiência)^n
```

Por fim:

```text
demanda estimada de energia em MWh =
produção projetada em toneladas
× intensidade energética em MWh/t
```

Os cenários futuros cobrem 2027–2040.

## Backtest histórico

O backtest avalia a projeção de **produção**, não a intensidade energética. Por isso, a atualização dos coeficientes energéticos não altera seus resultados.

Para cada mineral, os dois últimos anos disponíveis são reservados como teste. O modelo estima a tendência apenas com os anos anteriores e compara a projeção com a produção observada. O indicador é o erro percentual absoluto médio, ou MAPE.

| Mineral | Anos testados | MAPE |
|---|---:|---:|
| Fosfato | 2 | 2,3% |
| Cobre | 2 | 3,0% |
| Níquel | 2 | 7,8% |
| Amianto | 2 | 8,6% |
| Alumínio (Bauxita) | 2 | 44,3% |

A bauxita exige cautela: a série apresentava crescimento até 2023, mas houve queda relevante em 2024 e recuperação apenas parcial em 2025. O erro elevado evidencia o limite de uma projeção baseada apenas em tendência histórica. O modelo não consegue antecipar interrupções operacionais, decisões empresariais, licenciamento ou mudanças estruturais sem dados adicionais.

| Arquivo | Conteúdo |
|---|---|
| `outputs/backtest/backtest_detail.csv` | Previsões e valores observados por mineral e ano |
| `outputs/backtest/backtest_summary.csv` | MAPE por mineral |

## Cenários futuros

Os outputs futuros são:

| Arquivo | Conteúdo |
|---|---|
| `outputs/future/future_projection_by_mineral.csv` | Produção, intensidade e demanda de energia por mineral, ano e cenário |
| `outputs/future/future_energy_summary.csv` | Demanda total estimada dos cinco minerais por ano e cenário |

Com os coeficientes finais integrados, no cenário de referência a demanda estimada dos cinco minerais cobertos evolui de aproximadamente:

- **5,10 TWh em 2027**
- **11,57 TWh em 2040**

O valor de 2040 é composto principalmente por bauxita, com cerca de 8,47 TWh, e níquel, com cerca de 2,62 TWh.

Esses valores não representam consumo observado nem previsão oficial. São o resultado do modelo sob hipóteses explícitas de produção, eficiência e intensidade energética.

## Análise de sensibilidade

A análise de sensibilidade é separada do backtest e dos cenários futuros. Ela não altera a produção projetada: mede somente o impacto de incertezas ou hipóteses alternativas nas intensidades energéticas.

O intervalo permitido é de **−10% a +10%**, com passos de **1%**.

```text
energia ajustada do mineral =
energia base do mineral
× (1 + ajuste percentual / 100)
```

A energia total ajustada é a soma da energia ajustada de todos os minerais.

| Arquivo | Conteúdo |
|---|---|
| `outputs/sensitivity/intensity_global_range.csv` | Variação igual da intensidade de todos os minerais |
| `outputs/sensitivity/intensity_one_way.csv` | Variação de um mineral por vez, mantendo os demais fixos |
| `outputs/sensitivity/intensity_sensitivity_contract.json` | Contrato de dados para integração interativa |
| `outputs/sensitivity/custom_intensity_result.json` | Resultado de uma combinação específica de ajustes |

O contrato JSON inclui a energia base por mineral, ano e cenário. A plataforma pode receber um ajuste independente para cada mineral sem pré-calcular todas as combinações possíveis.

Exemplo:

```text
Cobre: +3%
Bauxita: 0%
Níquel: -5%
Fosfato: +1%
Amianto: 0%
```

## Integração entre squads

```text
Squad 1: produção histórica consolidada
    ↓
Squad 2 / intensidade_energetica: coeficientes estaduais e rastreabilidade
    ↓
Squad 2 / modello_reale: backtest, cenários e sensitivity analysis
    ↓
Squad 3: visualização e interação do utilizador
```

A Squad 3 pode utilizar:

- `outputs/future/` para gráficos e tabelas;
- `outputs/sensitivity/intensity_sensitivity_contract.json` para controles interativos de sensibilidade.

Uma evolução futura poderá incorporar dados estruturados de oferta, como capacidade, novos projetos, expansões, início de operação e grau de certeza.

## Execução local

A partir da raiz do repositório:

```bash
python -m pip install -r "Squad 2/modello_reale/requirements.txt"
```

Validar a leitura dos dados e dos coeficientes:

```bash
python "Squad 2/modello_reale/src/common.py"
```

Executar o backtest:

```bash
python "Squad 2/modello_reale/src/run_backtest.py"
```

Executar cenários futuros:

```bash
python "Squad 2/modello_reale/src/run_future_scenarios.py"
```

Executar análise de sensibilidade:

```bash
python "Squad 2/modello_reale/src/run_intensity_sensitivity.py"
```

## Automação e verificação

O workflow abaixo executa o modelo automaticamente:

```text
.github/workflows/validate-modelo-real.yml
```

Ele é acionado quando há alterações relevantes no modelo, nos coeficientes de intensidade da Squad 2, nos dados de produção da Squad 1 ou no próprio workflow.

O workflow:

1. instala as dependências;
2. valida a leitura dos dados e coeficientes;
3. executa o backtest;
4. executa os cenários futuros;
5. executa a análise de sensibilidade;
6. publica os três grupos de outputs como artefatos da GitHub Actions.

## Limitações atuais

- A bauxita continua dependente de benchmark proxy, pois não há consumo CCEE observado para os produtores identificados.
- Os coeficientes observados ou estimados referem-se a 2025; mudanças futuras de tecnologia ou de operação podem modificá-los.
- O modelo não incorpora ainda capacidade, novos projetos, expansões, encerramentos ou atrasos operacionais.
- Não há camada macroeconômica ou elasticidade entre demanda global e produção de Goiás.
- Não foi realizado backtest de consumo elétrico agregado, porque ainda não existe uma série histórica com o mesmo perímetro de operações e produção.
- Mudanças estruturais, como a queda de bauxita em 2024, não podem ser antecipadas somente por uma tendência histórica.
- A cobertura está limitada a cinco minerais.
