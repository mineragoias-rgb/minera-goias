# Nota ao Squad 2 — produção estimada sem coordenadas (aba 12, v17)

Gerada por `gerar_nota_sem_coordenadas.py` a partir da planilha; a lista completa está em `operacoes_sem_coordenadas.csv`, na mesma pasta.

## O que é

No nível `operacao` da aba `12_interface_squad1_squad2`, a produção observada do AMB em Goiás é aberta por processo pela participação na CFEM recolhida. Das 4.831 linhas desse nível, **457 (9,5%) não têm `operation_id`, `latitude` nem `longitude`**. Elas vêm de 112 processos que recolhem CFEM mas não têm poligonal no SIGMINE de Goiás (86 da série 96xxxx, 25 da série 86xxxx, 1 da série 92xxxx); nenhum está na aba 03.

A produção dessas linhas **não se perde**: o total de cada mineral e ano continua igual ao do estado. Só a localização da operação fica desconhecida. 457 das 457 linhas trazem o município de arrecadação da CFEM (`municipality_id`).

## Quanto pesa

Parcela da produção estimada por operação que fica sem coordenadas (soma entre minerais; co-produtos, como ouro e cobre, contam nos dois):

| Base | 2022 | 2023 | 2024 | 2025 |
|---|---:|---:|---:|---:|
| ROM | 25,4% | 23,5% | 16,5% | 17,8% |
| beneficiada | 10,2% | 8,4% | 6,8% | 9,9% |

Minerais mais afetados (produção bruta, ROM):

| Mineral | Ano | Sem coordenadas | % do mineral no ano |
|---|---:|---:|---:|
| Ouro | 2022 | 26,46 Mt | 91,8% |
| Ouro | 2023 | 25,49 Mt | 81,2% |
| Ouro | 2024 | 14,52 Mt | 55,8% |
| Ouro | 2025 | 13,06 Mt | 57,6% |
| Calcário | 2022 | 3,38 Mt | 22,1% |
| Calcário | 2025 | 2,90 Mt | 20,3% |
| Calcário | 2024 | 2,85 Mt | 21,0% |
| Calcário | 2023 | 2,19 Mt | 15,9% |
| Areia | 2025 | 2,10 Mt | 37,3% |
| Areia | 2024 | 1,14 Mt | 39,7% |
| Areia | 2023 | 0,97 Mt | 35,3% |
| Rochas (Britadas) e Cascalho | 2025 | 0,79 Mt | 5,8% |
| Areia | 2022 | 0,48 Mt | 13,8% |
| Argilas | 2022 | 0,27 Mt | 36,2% |

## Maiores processos

| Processo | Minerais | Anos | ROM estimada no período | Titular |
|---|---|---|---:|---|
| 960658/1987 | Ouro, Prata | 2022–2025 | 70,29 Mt | COM_NAO_IDENTIFICADO |
| 960657/1987 | Ouro | 2022–2024 | 9,03 Mt | COM_NAO_IDENTIFICADO |
| 960079/1988 | Calcário | 2022–2025 | 4,62 Mt | COM_NAO_IDENTIFICADO |
| 960993/2007 | Calcário | 2022–2025 | 4,29 Mt | COM_NAO_IDENTIFICADO |
| 961799/2009 | Calcário | 2022–2025 | 1,62 Mt | COM_CNPJ_62258884 |
| 960442/2012 | Areia | 2023–2025 | 0,81 Mt | COM_NAO_IDENTIFICADO |
| 960317/2017 | Rochas (Britadas) e Cascalho | 2025–2025 | 0,79 Mt | COM_NAO_IDENTIFICADO |
| 960704/2008 | Areia, Rochas Ornamentais, Saibro | 2022–2025 | 0,58 Mt | COM_NAO_IDENTIFICADO |
| 860906/2007 | Calcário | 2022–2025 | 0,37 Mt | COM_NAO_IDENTIFICADO |
| 860713/2003 | Areia | 2022–2023 | 0,32 Mt | COM_NAO_IDENTIFICADO |
| 860607/2015 | Argilas | 2022–2022 | 0,26 Mt | COM_NAO_IDENTIFICADO |
| 962157/2010 | Areia | 2022–2024 | 0,26 Mt | COM_NAO_IDENTIFICADO |
| 960444/2012 | Areia | 2023–2025 | 0,24 Mt | COM_NAO_IDENTIFICADO |
| 960571/2019 | Ouro | 2022–2024 | 0,19 Mt | COM_NAO_IDENTIFICADO |
| 860450/2008 | Rochas (Britadas) e Cascalho | 2023–2023 | 0,19 Mt | COM_NAO_IDENTIFICADO |

## Por que acontece

- Esses processos aparecem na CFEM, mas não no SIGMINE nem no Cadastro Mineiro de Goiás usados na base (arquivo do SIGMINE de 2026-10-24). Sem poligonal não há coordenada nem município pela geometria, e sem Cadastro não há titular: 108 dos 112 processos ficam em `COM_NAO_IDENTIFICADO`.
- A base não inventa coordenada nem titular (Contrato de Dados: nada é preenchido sem fonte).

## Sugestões de uso (a decidir com o Squad 2)

1. Para totais do estado por mineral e ano, use o nível `estado` da aba 12, que é observado e não depende de coordenada.
2. Em cálculos por operação ou por território, trate essa parcela como **não localizada**; não a distribua para operações vizinhas.
3. Se precisar de território, use o município de arrecadação da CFEM (aba 08) como localização aproximada, marcada como estimada.
4. No ouro, os processos da série 96xxxx concentram a maior parte: vale confirmar a localização em fonte oficial da ANM antes de atribuir coordenada.
