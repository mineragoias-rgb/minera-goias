# Indicadores municipais de mineração

Os 20 indicadores de mineração de cada um dos 246 municípios de Goiás, com ano-base 2025, que a aba **Ranking por Indicador** do painel
mostra no mapa e no ranking. O painel lê o pacote atrás do login, pela rota `/api/indicadores`; o arquivo não fica na pasta pública.

| Arquivo | Conteúdo |
|---|---|
| `indicadores_municipais.json` | `meta` (versão, ano, número de municípios, fonte e ressalvas), `indicadores` (a descrição de cada um), `cols` e `rows` (um município por linha), `cfem_anual` (CFEM por ano) e `presets` (as 8 composições prontas) |

Gerado por `python scripts/build_indicadores_municipais.py` a partir do banco de 20 indicadores por município (planilha
`Squad 2/indicadores_compostos/entregas/MINERA_Goias_Indicadores_2025.xlsx`, aba Indicadores, com os valores já calculados).
Conferido por `tests/test_indicadores.py`.

## Os 20 indicadores

Cada indicador vem com família, unidade, fórmula e leitura, em português e inglês.

| Código | Família | Indicador | Unidade |
|---|---|---|---|
| R1 | Receita | CFEM 2025 | R$ |
| R2 | Receita | Crescimento da CFEM | % |
| R3 | Receita | CFEM per capita | R$/hab. |
| R4 | Receita | CFEM/PIB (dependência da receita minerária) | % |
| R5 | Receita | Volatilidade da CFEM | desvio-padrão |
| R6 | Receita | Sharpe da CFEM | razão |
| P1 | Processos por fase | Processos de lavra | nº |
| P2 | Processos por fase | Processos em pré-lavra | nº |
| P3 | Processos por fase | Processos em pesquisa | nº |
| P4 | Processos por fase | Requerimentos | nº |
| A1 | Área por fase | Área em pesquisa | ha |
| A2 | Área por fase | Área arrematada | ha |
| A3 | Área por fase | Área ofertada | ha |
| A4 | % da área do município | % da área em pesquisa | % |
| A5 | % da área do município | % da área arrematada | % |
| A6 | % da área do município | % da área ofertada | % |
| S1 | Substâncias | Quantidade de substâncias | nº |
| S2 | Substâncias | HHI por substância | 0 a 1 |
| T1 | Titulares | Quantidade de titulares | nº |
| T2 | Titulares | HHI por titular | 0 a 1 |

As fontes são a ANM (CFEM, Cadastro Mineiro e rodadas de disponibilidade) e o IBGE (população). O PIB municipal é o que já estava no
repositório (2023); não foi baixado de novo do IBGE.

## O que o pacote calcula e o que só repete

Os valores dos indicadores vêm prontos da planilha. O pacote só soma a **CFEM por ano** (`cfem_anual`), para o painel recalcular o
crescimento da CFEM (R2) entre os dois anos que o usuário escolhe na tela.

## Composições prontas

Oito composições de indicadores, com pesos de 0 a 1: Arrecadação, Dependência fiscal, Risco da receita, Dinâmica e regularidade,
Atividade minerária, Ocupação do território, Diversidade de substâncias e titulares, e Concentração (HHI).

## Ressalvas

- A população é a estimativa do IBGE para 1º de julho de 2025. O PIB é o de 2023, não o de 2022; por isso, CFEM/PIB mistura a CFEM de 2025
  com um PIB defasado.
- Processos e áreas são o estoque atual (fase = situação atual) dos processos abertos até 2025. Não há histórico de fase.
- O % da área usa a área territorial do município e pode passar de 100% por sobreposição de processos.
- Volatilidade e Sharpe usam os 12 meses de 2025 e só existem onde há CFEM.
- As composições são exploratórias: o ranking depende dos pesos e da normalização escolhidos. Nenhum indicador ou composição foi validado
  por testes de índice.
