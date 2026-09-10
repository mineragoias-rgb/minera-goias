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

## Contrato dos dados reais para integração

Esta seção define o formato que a camada de integração deve fornecer ao motor. Os dados podem ser entregues em arquivos CSV ou por uma consulta ao banco/API; o meio de entrega pode mudar, mas os campos e os significados abaixo devem ser preservados.

Os arquivos demo em `data/demo/` são o exemplo executável deste contrato. Eles não devem ser usados como dados reais.

### 1. Catálogo de minerais (`minerals`)

| Campo | Obrigatório | Descrição |
|---|---:|---|
| `mineral_id` | Sim | Identificador estável e único do mineral. |
| `mineral_name` | Sim | Nome padronizado usado nas projeções. |
| `source_mineral_name` | Sim | Nome do mineral como aparece na fonte original. |
| `production_basis` | Sim | Base física: `rom`, `beneficiada` ou `conteudo_mineral`. |
| `catalog_status` | Sim | Situação da classificação/catálogo. |
| `notes` | Não | Observações sobre padronização ou limitações. |

### 2. Produção histórica (`production_history`)

Uma linha representa a produção de uma operação em um ano.

| Campo | Obrigatório | Descrição |
|---|---:|---|
| `mineral_id` | Sim | Mineral do catálogo. |
| `company_id` | Sim | Identificador estável da empresa. |
| `operation_id` | Sim | Identificador estável da operação existente. |
| `year` | Sim | Ano de referência. |
| `production_t` | Sim | Produção em toneladas, coerente com `production_basis`. |
| `production_basis` | Sim | Não pode ser misturada na mesma série com outra base. |
| `data_nature` | Sim | Natureza do dado, por exemplo observado ou estimado. |
| `source_id` | Sim | Fonte correspondente no catálogo de fontes. |

### 3. Projetos e expansões (`projects`)

Uma linha representa um projeto futuro ou uma expansão que pode entrar na projeção.

| Campo | Obrigatório | Descrição |
|---|---:|---|
| `project_id` | Sim | Identificador estável e único do projeto. |
| `mineral_id` | Sim | Mineral do catálogo. |
| `company_id` | Sim | Empresa responsável pelo projeto. |
| `capacity_tpy` | Sim | Capacidade anual em toneladas por ano. |
| `start_year` | Sim | Ano previsto para início da operação. |
| `project_stage` | Sim | Apenas `definido`, `provavel` ou `possivel`. |
| `production_basis` | Sim | Base física da capacidade informada. |
| `data_nature` | Sim | Natureza do dado, por exemplo observado ou estimado. |
| `source_id` | Sim | Fonte correspondente no catálogo de fontes. |

### 4. Intensidade energética (`energy_intensity`)

| Campo | Obrigatório | Descrição |
|---|---:|---|
| `mineral_id` | Sim | Mineral do catálogo. |
| `operation_id` | Sim | Operação à qual a intensidade se refere; pode ser um identificador agregado quando a fonte não permitir detalhamento. |
| `year` | Sim | Ano de referência. |
| `energy_intensity_mwh_t` | Sim | Consumo de energia em MWh por tonelada. |
| `production_basis` | Sim | Deve ser compatível com a base da produção usada no cálculo. |
| `data_nature` | Sim | Natureza do dado, por exemplo observado ou estimado. |
| `source_id` | Sim | Fonte correspondente no catálogo de fontes. |

### 5. Parâmetros de cenário (`scenario_parameters`)

Deve haver cobertura anual para cada mineral e para os três cenários: `conservador`, `referencia` e `expansao`.

| Campo | Obrigatório | Descrição |
|---|---:|---|
| `mineral_id` | Sim | Mineral do catálogo. |
| `year` | Sim | Ano da projeção. |
| `scenario` | Sim | `conservador`, `referencia` ou `expansao`. |
| `parameter_name` | Sim | `existing_production_growth_rate`, `project_utilization_rate`, `market_capture_factor` ou `annual_efficiency_improvement_rate`. |
| `parameter_value` | Sim | Valor numérico do parâmetro. Taxas devem ser registradas em formato decimal, por exemplo `0.05` para 5%. |
| `source_id` | Sim | Fonte ou registro metodológico da hipótese. |

### 6. Regras de inclusão de projetos (`scenario_project_rules`)

| Campo | Obrigatório | Descrição |
|---|---:|---|
| `scenario` | Sim | `conservador`, `referencia` ou `expansao`. |
| `project_stage` | Sim | `definido`, `provavel` ou `possivel`. |
| `include_project` | Sim | `true` ou `false`, conforme o projeto entra ou não no cenário. |
| `start_delay_years` | Sim | Atraso adicional inteiro em anos aplicado ao `start_year`. |
| `source_id` | Sim | Fonte ou registro metodológico da regra. |

### 7. Catálogo de fontes (`sources`)

| Campo | Obrigatório | Descrição |
|---|---:|---|
| `source_id` | Sim | Identificador estável e único da fonte. |
| `source_name` | Sim | Nome da instituição, documento ou base. |
| `source_url` | Não | Link para a fonte original, quando disponível. |
| `reference_period` | Sim | Período coberto pela fonte. |
| `data_nature` | Sim | Natureza dos dados fornecidos pela fonte. |
| `notes` | Não | Limitações, método e observações relevantes. |

### Regras de validação antes da entrega

- Os IDs devem ser estáveis entre atualizações e as chaves de referência devem existir nos catálogos correspondentes.
- Não misturar `rom`, `beneficiada` e `conteudo_mineral` em uma mesma série ou cálculo sem conversão documentada.
- `capacity_tpy`, `production_t` e `energy_intensity_mwh_t` não podem ser negativos.
- Toda observação deve ter uma fonte identificável por `source_id`.
- Ausências devem ser mantidas como ausências; não preencher valores desconhecidos com zero.
- O motor só deve receber dados reais após validação técnica da Squad 1 e confirmação metodológica da equipe.

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
