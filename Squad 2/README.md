# Squad 2 — Motor Econômico-Energético

## Objetivo

Desenvolver o motor econômico-energético do projeto MINERA Goiás. O modelo projeta, para cada mineral e para o total do estado de Goiás, a produção mineral e a demanda de energia elétrica no período de 2027 a 2040.

O motor utiliza um pipeline físico de operações existentes e projetos futuros. A futura camada de demanda e elasticidade deverá complementar essa projeção como explicação macroeconômica ou restrição de mercado, sem substituir a lógica física de oferta.

## Estado atual

O repositório contém uma versão demo, executável e reproduzível do motor:

- dados integralmente sintéticos, identificados como `estimated_demo`;
- três cenários: `conservador`, `referencia` e `expansao`;
- projeção de produção existente, entrada de projetos, utilização, atrasos e captura de mercado;
- conversão da produção em demanda de energia elétrica por intensidade energética;
- análise de sensibilidade para atraso, utilização e eficiência;
- validações automáticas e execução pelo GitHub Actions.

Os dados demo não representam valores reais de empresas, minas, produção ou intensidade energética.

## Estrutura

```text
Squad 2/
├── data/demo/                 # entradas sintéticas e documentação dos dados
├── notebooks/
│   └── Motor_Economico_Energetico_MINERA_Goias.ipynb
└── outputs/demo/              # resultados gerados durante a execução
```

## Como o modelo funciona

1. Usa a produção observada em 2025 como baseline por mineral e base de produção.
2. Projeta as operações existentes com `existing_production_growth_rate`.
3. Inclui projetos conforme estágio, cenário, ano de início e atraso.
4. Calcula a produção de cada projeto:

   `capacidade × utilização × captura de mercado`

5. Calcula a demanda de energia:

   `produção projetada × intensidade energética`

6. Agrega os resultados por mineral para obter o total anual de Goiás.

## Dados de entrada

O notebook lê os arquivos da pasta `data/demo/`:

- `minerals_demo.csv`;
- `production_history_demo.csv`;
- `projects_demo.csv`;
- `energy_intensity_demo.csv`;
- `scenario_parameters_demo.csv`;
- `scenario_project_rules_demo.csv`;
- `sources_demo.csv`.

Para substituir o demo por dados reais, a equipe deve manter a mesma estrutura de colunas, IDs estáveis e a mesma `production_basis`. Esta regra evita misturar produção ROM, produção beneficiada e conteúdo mineral.

## Cenários e parâmetros

Os cenários aceitos são `conservador`, `referencia` e `expansao`. Os parâmetros anuais ficam fora da lógica do código:

- `existing_production_growth_rate`;
- `project_utilization_rate`;
- `market_capture_factor`;
- `annual_efficiency_improvement_rate`.

Assim, é possível alterar hipóteses sem alterar o código do motor.

## Resultados

Cada execução produz seis arquivos CSV:

- `projecao_por_mineral_demo.csv`;
- `projecao_total_goias_demo.csv`;
- `contribuicao_projetos_demo.csv`;
- `sensibilidade_detalhada_demo.csv`;
- `sensibilidade_total_goias_demo.csv`;
- `sensibilidade_resumo_demo.csv`.

## Execução e validação automática

O workflow `.github/workflows/validate-squad2-model.yml` executa automaticamente o notebook quando arquivos da Squad 2, as dependências ou o workflow são alterados.

A execução:

1. instala as dependências de `requirements.txt`;
2. executa o notebook;
3. interrompe em caso de falha de consistência;
4. publica os resultados e o notebook executado como artefato no GitHub Actions.

Os artefatos podem ser baixados pela aba **Actions** e ficam disponíveis por 30 dias.

## Controles de consistência

Antes de exportar os resultados, o notebook verifica:

- cobertura completa de 2027 a 2040 para cada mineral e cenário;
- presença dos três cenários obrigatórios;
- ausência de valores ausentes;
- produção e demanda de energia não negativas;
- igualdade entre o total de Goiás e a soma dos minerais.

## Próximas etapas

1. Receber e validar dados reais de operações e projetos da Squad 1.
2. Receber intensidades energéticas e hipóteses de cenário da Squad 2.
3. Substituir os dados demo pelos dados reais.
4. Realizar backtest com dados observados.
5. Incorporar a camada de demanda/elasticidade após definição metodológica.
6. Reexecutar a análise de sensibilidade com parâmetros reais.

## Governança de dados

Antes de publicar dados reais, a equipe deve confirmar que a divulgação em um repositório público é permitida. Caso existam restrições de confidencialidade, os dados devem permanecer em armazenamento privado.
