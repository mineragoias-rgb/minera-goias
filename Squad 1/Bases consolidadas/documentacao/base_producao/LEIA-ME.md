# Base de produção mineral de Goiás por empresa

Gerada por `base_consolidada_work/scripts/gerar_base_producao.py` a partir da aba 12 da base consolidada (pacote do Squad 2), dos nomes das abas 02 e 05 e da produção publicada pelas empresas (`Squad 1/Auditoria e qualidade/producao_empresas_ri_2025_2026.csv`). Não editar à mão: a cadeia `scripts/atualizar_derivados.py` refaz os arquivos quando a base muda.

## Como a produção é dividida

- **Total do estado:** Anuário Mineral Brasileiro (ANM), por mineral e ano, em ROM e beneficiada. É o controle: a soma das empresas fecha nele.
- **Parcela de cada empresa (2022 em diante):** a parcela dos processos dela na CFEM paga em R$ naquele mineral e ano. A CFEM em t não é usada (unidades trocadas e quantidades implausíveis — ver `Squad 1/Dados corrigidos/REGISTRO_DE_ALTERACOES.md`). Meses de pagamento atípico entram pela mediana do processo. Margem de ±10%, medida contra o que as empresas publicam.
- **Minério associado** (bário, cobalto, prata declarados com a massa do minério de outro mineral) não é dividido nem somado.
- **Pessoa física:** sem nome nem CPF.

## Arquivos

| Arquivo | Uma linha por | Colunas principais |
|---|---|---|
| `base_producao_empresa_ano.csv` | ano × mineral × base × empresa | produção dividida (t), parcela do estado, processos, municípios, CFEM, número publicado pela empresa e diferença |
| `base_producao_estado_ano.csv` | ano × mineral × base | total do estado, parte dividida por empresa, parte com número publicado, situação |

## Cobertura (2022–2025, sem o minério associado)

| Ano | Base | Total do estado | Dividido por empresa | Linhas de empresa |
|---|---|---:|---:|---:|
| 2022 | ROM | 116,0 Mt | 99,7% | 318 |
| 2022 | beneficiada | 28,0 Mt | 98,8% | 295 |
| 2023 | ROM | 117,8 Mt | 99,6% | 333 |
| 2023 | beneficiada | 30,1 Mt | 99,9% | 320 |
| 2024 | ROM | 107,6 Mt | 99,7% | 369 |
| 2024 | beneficiada | 30,8 Mt | 99,4% | 358 |
| 2025 | ROM | 108,1 Mt | 99,0% | 351 |
| 2025 | beneficiada | 32,2 Mt | 99,9% | 338 |

## Divisão × número publicado (mesma medida)

| Ano | Mineral | Empresa | Base de produção | Publicado | Diferença |
|---|---|---|---:|---:|---:|
| 2022 | Amianto | SAMA S.A. - MINERACOES ASSOCIADAS EM RECUPERACAO JUDICIAL | 182.965 t | 182.965 t | +0% |
| 2022 | Fosfato | MOSAIC FERTILIZANTES P&K LTDA. | 1.100.000 t | 1.100.000 t | -0% |
| 2022 | Ouro | MINERACAO SERRA GRANDE S A | 3,93 t | 2,74 t | +44% |
| 2023 | Amianto | SAMA S.A. - MINERACOES ASSOCIADAS EM RECUPERACAO JUDICIAL | 189.340 t | 188.813 t | +0% |
| 2023 | Fosfato | MOSAIC FERTILIZANTES P&K LTDA. | 1.000.000 t | 1.000.000 t | -0% |
| 2023 | Ouro | MINERACAO SERRA GRANDE S A | 3,24 t | 2,67 t | +21% |
| 2024 | Fosfato | MOSAIC FERTILIZANTES P&K LTDA. | 900.000 t | 900.000 t | +0% |
| 2024 | Ouro | MINERACAO SERRA GRANDE S A | 2,78 t | 2,49 t | +12% |
| 2024 | Ouro | AMARILLO MINERACAO DO BRASIL LTDA | 1,80 t | 1,98 t | -9% |
| 2025 | Amianto | SAMA S.A. - MINERACOES ASSOCIADAS EM RECUPERACAO JUDICIAL | 179.184 t | 169.000 t | +6% |
| 2025 | Fosfato | MOSAIC FERTILIZANTES P&K LTDA. | 900.000 t | 900.000 t | +0% |
| 2025 | Ouro | AMARILLO MINERACAO DO BRASIL LTDA | 1,34 t | 1,24 t | +8% |

Diferenças acima de ±10% indicam onde a CFEM não representa bem a produção (ex.: Mosaic 2024–25 no fosfato; Serra Grande 2022 no ouro, em que o AMB tem ouro de outra origem). Nenhum número publicado substitui a divisão: ficam lado a lado.
