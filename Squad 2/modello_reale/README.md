# Modelo econômico-energético da Squad 2

## Objetivo

Este diretório contém o modelo econômico-energético da Squad 2 para o projeto MINERA Goiás.

O modelo estima a demanda de energia elétrica associada à produção mineral de Goiás entre 2027 e 2040. Ele utiliza as séries históricas consolidadas pela Squad 1, aplica cenários explícitos de produção e eficiência energética e produz resultados por mineral, ano e cenário.

Esta é uma versão técnica, reproduzível e integrada aos dados atualmente disponíveis. Os resultados são cenários condicionais às hipóteses e às fontes documentadas; não constituem uma previsão oficial da mineração ou do consumo elétrico de Goiás.

## O que o modelo faz

1. Lê e valida a produção mineral histórica consolidada pela Squad 1.
2. Executa um backtest histórico da projeção de produção.
3. Compara a tendência histórica com uma referência simples de persistência.
4. Gera cenários futuros de produção e demanda estimada de energia para 2027–2040.
5. Executa análise de sensibilidade das intensidades energéticas.
6. Gera faixas baixa, base e alta e gráficos prontos para apresentação.

Backtest, cenários futuros, sensibilidade, faixas de incerteza e materiais de apresentação possuem outputs separados para não confundir validação histórica, projeção e teste de hipóteses.

## Cobertura atual

A versão cobre cinco minerais cujas séries de produção e intensidades energéticas puderam ser conciliadas:

| Mineral | Base de produção no modelo | Coeficiente base em 2025 | Natureza do coeficiente |
|---|---|---:|---|
| Cobre | Conteúdo mineral | 8,107848 MWh/t | Calculado |
| Alumínio (Bauxita) | Produção beneficiada | 1,40 MWh/t | Benchmark proxy |
| Níquel | Produção beneficiada | 11,400041 MWh/t | Estimado |
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
    │   ├── run_intensity_sensitivity.py
    │   ├── run_uncertainty_bands.py
    │   ├── build_presentation_summary.py
    │   └── build_presentation_charts.py
    ├── outputs/
    │   ├── backtest/
    │   ├── future/
    │   ├── sensitivity/
    │   ├── uncertainty/
    │   └── presentation/
    │       └── charts/
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

As colunas adicionais preservam rastreabilidade metodológica: ano, operações utilizadas, consumo CCEE, produção, cobertura da produção estadual, intervalo observado, nível de confiança, coeficiente anterior e observações.

O arquivo `parameters/energy_intensity.csv` permanece no diretório do modelo apenas como referência do benchmark anterior. Ele não é mais a entrada ativa do motor e não deve ser sobrescrito.

### Método de agregação

Para cobre, níquel, fosfato e amianto, os coeficientes foram calculados ou estimados a partir de consumo elétrico observado na CCEE em 2025 dividido pela produção de 2025 das operações cobertas.

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
| Níquel | 100,0% | Barro Alto e Codemin (Anglo American) cobrem toda a produção estadual |
| Fosfato | 100,0% | Agregação de Mosaic e CMOC/Copebrás |
| Amianto | 100,0% | SAMA é a única operação produtora |

### Correção de compatibilidade do níquel

O coeficiente anterior de níquel, `45,551351 MWh/t`, referia-se a toneladas de níquel contido. Porém, o modelo projeta produção beneficiada de ferroníquel, que possui uma escala de toneladas aproximadamente quatro vezes maior.

Aplicar o coeficiente anterior diretamente à produção beneficiada superestimava a demanda energética de níquel. O coeficiente de `11,400041 MWh/t` utiliza a mesma base de produção do modelo e elimina essa incompatibilidade de unidade.

A bauxita continua explicitamente identificada como `benchmark_proxy`, pois ainda não há consumo elétrico próprio observado na CCEE para os produtores cobertos.

Detalhes completos da construção, fontes e testes da base estão em:

```text
Squad 2/intensidade_energetica/README.md
```

## Cenários

As hipóteses gerais estão em:

```text
parameters/scenarios.csv
```

| Cenário | Ajuste sobre o crescimento histórico | Melhoria anual de eficiência energética |
|---|---:|---:|
| Conservador | -2,0 pontos percentuais | 0,4% |
| Referência | 0,0 pontos percentuais | 0,9% |
| Expansão | +2,0 pontos percentuais | 1,4% |

Essas hipóteses são `illustrative`: permitem comparar trajetórias de forma transparente, mas não são previsões oficiais.

Para cobre, níquel, fosfato e amianto, o cenário parte da taxa de crescimento calculada sobre toda a série histórica e aplica o ajuste acima.

A bauxita recebe tratamento separado, pois o backtest mostrou que persistir o último valor observado é mais adequado para o cenário de referência do que extrapolar uma tendência histórica.

| Cenário | Crescimento anual da produção de bauxita | Justificativa |
|---|---:|---|
| Conservador | -2,0% | Contração operacional explícita |
| Referência | 0,0% | Persistência da produção de 2025, selecionada pelo backtest |
| Expansão | +5,07% | CAGR recente de 2018–2025, após o período de ramp-up |

## Método de projeção

Para cobre, níquel, fosfato e amianto:

```text
produção projetada =
produção no último ano observado
× (1 + crescimento histórico + ajuste do cenário)^n
```

A intensidade energética evolui de acordo com a melhoria anual de eficiência:

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

A bauxita não usa a regra de tendência histórica no cenário de referência: sua produção permanece no último valor observado de 2025. Essa escolha evita transformar um período de crescimento excepcional em expansão automática de longo prazo. O cenário de expansão mantém separadamente a hipótese de crescimento recente.

## Backtest histórico

O backtest avalia a projeção de **produção**, não a intensidade energética.

Para cada mineral, os dois últimos anos disponíveis são reservados como teste. O modelo compara:

1. tendência composta estimada com os anos anteriores;
2. referência simples, que mantém a última observação disponível.

O indicador é o erro percentual absoluto médio, ou MAPE.

| Mineral | Anos testados | MAPE da tendência | MAPE da referência simples | Regra usada no cenário de referência |
|---|---:|---:|---:|---|
| Fosfato | 2 | 2,3% | 1,4% | Tendência histórica |
| Cobre | 2 | 3,0% | 5,4% | Tendência histórica |
| Níquel | 2 | 7,8% | 1,7% | Tendência histórica |
| Amianto | 2 | 8,6% | 2,7% | Tendência histórica |
| Alumínio (Bauxita) | 2 | 34,1% | 18,2% | Referência simples |

A bauxita exige cautela: a série apresentava crescimento até 2023, mas houve queda relevante em 2024 e recuperação parcial em 2025. A referência simples teve menor erro no backtest e, por isso, é a regra selecionada para o cenário de referência.

Para níquel, amianto e fosfato, a referência simples também apresenta menor MAPE nos dois anos de teste. O modelo mantém a tendência histórica como mecanismo de cenário, mas comunica essa comparação como limitação. Com somente dois anos reservados, a evidência não é suficiente para afirmar superioridade geral de uma regra em todos os contextos.

| Arquivo | Conteúdo |
|---|---|
| `outputs/backtest/backtest_detail.csv` | Previsões e valores observados por mineral e ano |
| `outputs/backtest/backtest_summary.csv` | MAPE da tendência, da referência simples e método selecionado por mineral |

## Cenários futuros

| Arquivo | Conteúdo |
|---|---|
| `outputs/future/future_projection_by_mineral.csv` | Produção, intensidade e demanda de energia por mineral, ano e cenário |
| `outputs/future/future_energy_summary.csv` | Demanda total estimada dos cinco minerais por ano e cenário |

Com os coeficientes finais integrados e a regra de referência da bauxita ajustada pelo backtest, a demanda estimada dos cinco minerais cobertos evolui de aproximadamente:

- **4,59 TWh em 2027**
- **4,84 TWh em 2040**

Em 2040, os principais componentes são níquel, com cerca de 2,56 TWh, e bauxita, com cerca de 1,81 TWh.

| Cenário | Demanda elétrica em 2040 |
|---|---:|
| Conservador | 3,87 TWh |
| Referência | 4,84 TWh |
| Expansão | 7,28 TWh |

Esses valores não representam consumo observado nem previsão oficial. São o resultado do modelo sob hipóteses explícitas de produção, eficiência e intensidade energética.

## Análise de sensibilidade

A análise de sensibilidade é separada do backtest e dos cenários futuros. Ela não altera a produção projetada: mede o impacto de hipóteses alternativas nas intensidades energéticas.

O intervalo permitido é de **−10% a +10%**, com passos de **1%**.

```text
energia ajustada do mineral =
energia base do mineral
× (1 + ajuste percentual / 100)
```

| Arquivo | Conteúdo |
|---|---|
| `outputs/sensitivity/intensity_global_range.csv` | Variação igual da intensidade de todos os minerais |
| `outputs/sensitivity/intensity_one_way.csv` | Variação de um mineral por vez, mantendo os demais fixos |
| `outputs/sensitivity/intensity_sensitivity_contract.json` | Contrato de dados para integração interativa |
| `outputs/sensitivity/custom_intensity_result.json` | Resultado de uma combinação específica de ajustes |

O contrato JSON permite que a plataforma receba um ajuste independente para cada mineral, sem pré-calcular todas as combinações possíveis.

## Faixas de incerteza

Além dos cenários e da análise de sensibilidade, o modelo gera faixas **baixa / base / alta** para cada mineral, ano e cenário.

As faixas combinam:

1. o MAPE de produção observado no backtest para cada mineral;
2. a variação de **−10% a +10%** das intensidades energéticas.

```text
faixa baixa = energia base × (1 - MAPE do backtest) × 0,90
faixa alta  = energia base × (1 + MAPE do backtest) × 1,10
```

As faixas são **intervalos de cenário**, não intervalos estatísticos de confiança. Elas mostram como a projeção varia quando se combinam o erro da regra selecionada no backtest e a incerteza dos coeficientes energéticos.

| Arquivo | Conteúdo |
|---|---|
| `outputs/uncertainty/uncertainty_by_mineral.csv` | Faixa baixa, base e alta por mineral, ano e cenário |
| `outputs/uncertainty/uncertainty_total_goias.csv` | Faixa baixa, base e alta para o total dos cinco minerais |

## Materiais para apresentação

| Arquivo | Conteúdo e uso sugerido |
|---|---|
| `outputs/presentation/scenario_summary_2035_2040.csv` | Faixas baixa, base e alta para os três cenários em 2035 e 2040 |
| `outputs/presentation/reference_breakdown_2040.csv` | Demanda por mineral em 2040 no cenário de referência |
| `outputs/presentation/bauxite_scope_diagnostic.csv` | Diagnóstico transparente do efeito da bauxita no total |
| `outputs/presentation/backtest_quality_summary.csv` | MAPE da regra selecionada e comparação com a referência simples |

### Gráficos

| Arquivo | Mensagem principal |
|---|---|
| `outputs/presentation/charts/scenario_paths_with_uncertainty.png` | Trajetórias de 2027–2040 para os três cenários e suas faixas |
| `outputs/presentation/charts/reference_2040_mineral_breakdown.png` | Composição da demanda em 2040; níquel e bauxita são os principais componentes |
| `outputs/presentation/charts/backtest_quality_by_mineral.png` | Comparação entre tendência e referência simples na validação retrospectiva |

No cenário de referência, a demanda dos cinco minerais cobertos chega a **4,84 TWh em 2040**, com faixa de cenário de **3,87 a 5,92 TWh**.

A bauxita representa aproximadamente 37% da projeção central de 2040. A redução em relação à versão anterior decorre de uma escolha metodológica mais conservadora e validada: a bauxita deixa de extrapolar automaticamente uma tendência de crescimento e passa a manter a produção de 2025 no cenário de referência.

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
- `outputs/sensitivity/intensity_sensitivity_contract.json` para controles interativos;
- `outputs/uncertainty/uncertainty_total_goias.csv` para faixas baixa, base e alta.

## Execução local

A partir da raiz do repositório:

```bash
python -m pip install -r "Squad 2/modello_reale/requirements.txt"
python "Squad 2/modello_reale/src/common.py"
python "Squad 2/modello_reale/src/run_backtest.py"
python "Squad 2/modello_reale/src/run_future_scenarios.py"
python "Squad 2/modello_reale/src/run_intensity_sensitivity.py"
python "Squad 2/modello_reale/src/run_uncertainty_bands.py"
python "Squad 2/modello_reale/src/build_presentation_summary.py"
python "Squad 2/modello_reale/src/build_presentation_charts.py"
```

## Automação e verificação

O workflow abaixo executa o modelo automaticamente:

```text
.github/workflows/validate-modelo-real.yml
```

Ele:

1. instala as dependências;
2. valida os dados e coeficientes;
3. executa o backtest;
4. executa os cenários;
5. executa a análise de sensibilidade;
6. gera as faixas de incerteza;
7. gera as tabelas e gráficos de apresentação;
8. publica os outputs como artefatos da GitHub Actions.

## Limitações atuais

- A bauxita depende de benchmark proxy, pois não há consumo CCEE observado para os produtores identificados.
- Os coeficientes observados ou estimados referem-se a 2025; mudanças futuras de tecnologia ou operação podem modificá-los.
- O modelo não incorpora capacidade, novos projetos, expansões, encerramentos ou atrasos operacionais.
- Não há camada macroeconômica ou elasticidade entre demanda global e produção de Goiás.
- Não foi realizado backtest de consumo elétrico agregado, porque ainda não existe uma série histórica com o mesmo perímetro de operações e produção.
- O backtest possui apenas dois anos de teste por mineral; a comparação com a referência simples é evidência útil, mas ainda não demonstra superioridade estatística generalizável entre métodos.
- Mudanças estruturais, como a queda de bauxita em 2024, não podem ser antecipadas somente por uma tendência histórica.
- A cobertura está limitada a cinco minerais.
- As faixas baixa, base e alta são cenários de sensibilidade; não devem ser interpretadas como intervalos estatísticos de confiança.
