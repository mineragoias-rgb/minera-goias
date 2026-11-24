# Fechamento da atualização v19

Este roteiro fecha a última atualização solicitada após a entrega da base v19 do Squad 1 e da curadoria ampliada de projetos.

Regra central: dados novos de produção não são convertidos automaticamente em TWh sem uma intensidade energética compatível.

## O que a v19 efetivamente adiciona

- Produção observada estadual para 33 minerais, de 2010 a 2025.
- Abertura estimada por operação de 2022 a 2025 para 931 processos.
- Curadoria com 37 projetos, em vez de uma carteira restrita aos cinco minerais do modelo.

O modelo elétrico continua com cinco minerais porque o arquivo de coeficientes contém somente cobre, bauxita, níquel, fosfato e amianto.

A execução com a v19 mantém o cenário de referência de 2040 em **4,84 TWh**. Não houve mudança numérica apenas por substituir a base de produção.

## Resultado da auditoria da carteira atual

Para gerar a auditoria:

```bash
cd "Squad 2/modello_reale"
python src/audit_project_readiness.py
```

O script produz:

```text
outputs/project_audit/project_readiness.csv
outputs/project_audit/README.md
```

A auditoria classifica os 37 projetos sem inferir números ausentes.

No retrato atual:

- 17 são operações e não devem ser adicionados novamente à tendência.
- 8 são sinais iniciais, cujo peso já é zero em todos os cenários.
- 1 já está quantificado e entra no modelo: Chapada/Saúva, cobre, +15 mil t/ano entre 2029 e 2032.
- 1 é candidato com quantidade e data, mas ainda fora do total em TWh: expansão de Serra Verde, terras raras, 6.500 t/ano em 2027.
- Os demais não têm coeficiente energético utilizável e/ou ainda não trazem quantidade e período suficientes.

## Como incluir legitimamente um novo mineral ou projeto

1. Escolher um mineral com série observada estadual e definir uma única base produtiva: ROM, beneficiada ou conteúdo mineral.
2. Ligar a carga CCEE de 2025 à operação ou às operações que usam essa mesma base produtiva.
3. Calcular e documentar o coeficiente MWh/t no diretório `Squad 2/intensidade_energetica/`.
4. Só então acrescentar o coeficiente final ao modelo e executar um backtest próprio.
5. Para um projeto, confirmar incremento líquido anual — não apenas capacidade total —, ano de início/fim e unidade compatível.
6. Adicionar a linha ao arquivo `parameters/project_pipeline.csv`.
7. Rodar todas as verificações antes de publicar.

## Sequência de execução final

```bash
cd "Squad 2/modello_reale"

python src/audit_project_readiness.py
python src/common.py
python src/run_backtest.py
python src/run_future_scenarios.py
python src/run_intensity_sensitivity.py
python src/run_uncertainty_bands.py
python src/build_presentation_summary.py
python src/build_presentation_charts.py
python src/build_energy_comparison.py
python src/build_production_benchmark.py
```

Depois, no GitHub, executar:

```text
Validate real model prototype
Generate energy comparison
```

O primeiro valida e publica os artefatos técnicos. O segundo atualiza o benchmark produtivo do painel.

Não alterar manualmente os TWh no site.

## Texto curto para a apresentação

> A v19 ampliou a cobertura de produção e da carteira de projetos. Mantivemos o total elétrico restrito aos cinco minerais com coeficiente MWh/t reconciliado, para não transformar toneladas em TWh por hipótese. A auditoria separa operações já incluídas no histórico, sinais sem base quantitativa e candidatos que poderão entrar assim que consumo e base produtiva forem conciliados. Atualmente, Chapada/Saúva continua sendo o único projeto adicional plenamente quantificado no total elétrico.
