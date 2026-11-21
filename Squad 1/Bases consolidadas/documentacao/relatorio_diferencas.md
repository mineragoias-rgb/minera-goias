# Relatório de diferenças da base consolidada

Gerado em 21/11/2026 por `relatorio_diferencas.py`.

- antes: `prototipo_bases_consolidadas_v19.xlsx` do commit 7b5a879 (v19 publicada em 21/11/2026)
- depois: `prototipo_bases_consolidadas_v19.xlsx` do commit b18040a (ROM do ouro sem o minério da Chapada)
- limiar para "mudou": 5% (e diferença absoluta > 0,01)

## 1. Dados brutos desde o manifesto

Brutos (github): 50 arquivos; desde o manifesto: 0 novos, 0 removidos, 0 alterados, 50 iguais.


## 2. Linhas preenchidas por aba

| Aba | Antes | Depois | Diferença |
|---|---:|---:|---:|
| 00_LEIA-ME | 93 | 93 | +0 |
| 01_dim_minerais | 70 | 70 | +0 |
| 01b_crosswalk_pente_fino | 370 | 370 | +0 |
| 01c_rochas_por_tipo_de_uso | 225 | 225 | +0 |
| 02_dim_empresas | 5,080 | 5,080 | +0 |
| 02b_crosswalk_empresas | 197 | 197 | +0 |
| 03_dim_operacoes | 16,878 | 16,878 | +0 |
| 04_dim_projetos | 3,406 | 3,406 | +0 |
| 04b_eventos_anm_classificados | 295 | 295 | +0 |
| 05_dim_municipios | 249 | 249 | +0 |
| 05b_crosswalk_municipios | 479 | 479 | +0 |
| 06_dim_ocorrencias_geologicas | 1,799 | 1,799 | +0 |
| 06b_crosswalk_recmin | 82 | 82 | +0 |
| 07_dim_fontes | 23 | 23 | +0 |
| 08_fato_producao_energia | 158,268 | 158,268 | +0 |
| 09_cons_mineral_ano | 1,359 | 1,359 | +0 |
| 09b_auditoria_cfem_quantidade | 92 | 92 | +0 |
| 09c_alertas_cfem_processo | 40 | 40 | +0 |
| 10_cons_municipio_ano | 967 | 967 | +0 |
| 11_cons_empresa_ano_mineral | 10,246 | 10,246 | +0 |
| 12_interface_squad1_squad2 | 5,567 | 5,577 | +10 |
| 13_mapas_camadas | 14 | 14 | +0 |
| 13b_auditoria_mapas | 55 | 55 | +0 |
| 14_dicionario_dados | 534 | 534 | +0 |
| 14b_validacoes_governanca | 45 | 45 | +0 |
| 15a_repositorio_erros | 48 | 48 | +0 |
| 15b_bario_niobio | 19 | 19 | +0 |
| 15c_bario_niobio_processos | 42 | 42 | +0 |
| 15d_contido_vs_bruto | 810 | 810 | +0 |
| 15e_tonelagens_repetidas | 173 | 173 | +0 |
| 15f_amb_x_cfem | 126 | 126 | +0 |

## 3. IDs que entraram e saíram das dimensões

| Aba | Antes | Depois | Entraram | Saíram | Exemplos |
|---|---:|---:|---:|---:|---|
| 01_dim_minerais | 67 | 67 | 0 | 0 |  |
| 02_dim_empresas | 5,077 | 5,077 | 0 | 0 |  |
| 03_dim_operacoes | 16,875 | 16,875 | 0 | 0 |  |
| 04_dim_projetos | 3,403 | 3,403 | 0 | 0 |  |
| 05_dim_municipios | 246 | 246 | 0 | 0 |  |
| 06_dim_ocorrencias_geologicas | 1,796 | 1,796 | 0 | 0 |  |

## 4a. Aba 09 — mineral × UF × ano

0 combinações (mineral_name, uf, year) entraram, 0 saíram e 0 valores mudaram mais que 5%.

## 4b. Aba 12 — entrega ao Squad 2: mineral × nível (estado/operação) × base × ano

0 combinações (mineral_name, nivel_agregacao, production_basis, year) entraram, 0 saíram e 0 valores mudaram mais que 5%.

Totais de Goiás por ano (soma da aba 09):

| Ano | ROM antes (t) | ROM depois (t) | CFEM antes (R$) | CFEM depois (R$) |
|---|---:|---:|---:|---:|
| 2010 | 99,155,719 | 99,155,719 | 0.00 | 0.00 |
| 2011 | 125,680,547 | 125,680,547 | 0.00 | 0.00 |
| 2012 | 124,569,471 | 124,569,471 | 0.00 | 0.00 |
| 2013 | 124,396,498 | 124,396,498 | 0.00 | 0.00 |
| 2014 | 116,361,066 | 116,361,066 | 0.00 | 0.00 |
| 2015 | 118,632,904 | 118,632,904 | 0.00 | 0.00 |
| 2016 | 96,481,891 | 96,481,891 | 0.00 | 0.00 |
| 2017 | 159,984,589 | 159,984,589 | 0.00 | 0.00 |
| 2018 | 135,233,459 | 135,233,459 | 0.00 | 0.00 |
| 2019 | 139,644,392 | 139,644,392 | 0.00 | 0.00 |
| 2020 | 121,277,092 | 121,277,092 | 0.00 | 0.00 |
| 2021 | 141,119,124 | 141,119,124 | 0.00 | 0.00 |
| 2022 | 121,397,711 | 121,397,711 | 176,327,340.17 | 176,327,340.17 |
| 2023 | 123,359,805 | 123,359,805 | 161,644,783.89 | 161,644,783.89 |
| 2024 | 113,251,004 | 113,251,004 | 183,775,760.08 | 183,775,760.08 |
| 2025 | 113,669,670 | 113,669,670 | 229,927,025.69 | 229,927,025.69 |
| 2026 | 0 | 0 | 116,202,989.53 | 116,202,989.53 |

## 5. Aba 14b e travas

Nenhuma verificação mudou de status.

| Verificação | Status | n | Nível | Decisão |
|---|---|---|---|---|
| Arquivos de dados/ sem source_id no catálogo 07 (fora a documentação: LEIA-ME, metadados . | ALERTA | 12 | bloqueia | aceito (n ≤ 12) |
| Plausibilidade: CFEM comercializada (t) ÷ produção do AMB na base mais próxima (bruta ou b | ALERTA | 30 | avisa | aceito (n ≤ 30) |
| Processos com quantidade na CFEM implausível frente ao AMB do estado (acima do total ou, e | ALERTA | 37 | avisa | aceito (n ≤ 37) |
| 08: mesma tonelagem de produção em linhas diferentes da mesma UF e ano no AMB (co-produto, | ALERTA | 170 | avisa | aceito (n ≤ 170) |


travas: nenhuma verificação de nível 'bloqueia' com ALERTA — pode seguir
