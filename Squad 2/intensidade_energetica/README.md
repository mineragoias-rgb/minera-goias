# Base de Intensidade Energética do Setor Mineral de Goiás — v1

Squad 2 / Estudante 2: rotas tecnológicas e intensidade energética. Responsável: **Sarah Lattouf**.

## Arquivos

| Arquivo | O que é |
|---|---|
| `base_intensidade_energetica_v1.csv` | A base: 24 linhas por mineral, operação e tecnologia, com energia, produção, intensidade, natureza do dado e fontes |
| `energy_intensity_para_motor_v1.csv` | Saída para o motor 2027–2040: as linhas que seguem o contrato "Intensidade energética" do `Squad 2/README (1).md` |
| `coeficiente_estadual_para_modelo_v1.csv` | **Entrada final do modelo:** um coeficiente estadual por mineral (cobre, bauxita, níquel, fosfato, amianto), na mesma base de produção que o modelo usa |
| `dicionario_intensidade_v1.csv` | Uma linha por campo da base |
| `build_intensidade.py` | Gera os três CSV a partir de arquivos que já estão no repositório |
| `test_intensidade.py` | 11 checagens: fórmula, unidades, campos exigidos pelo PDF da entrega, domínios, benchmarks, contrato do motor, ausência de dupla contagem e coeficiente estadual recalculado a partir da base |

Para gerar a base de novo e testar (Python 3, sem bibliotecas externas):

```
python "Squad 2/intensidade_energetica/build_intensidade.py"
cd "Squad 2/intensidade_energetica" && python test_intensidade.py
```

Os scripts só leem arquivos de outras pastas; não alteram nenhum arquivo fora desta pasta.

## Entrada e saída (integração)

| | O quê | De / para quem | Onde |
|---|---|---|---|
| **Entrada** | Energia de 2025 por unidade consumidora (CCEE, 12 meses) e produção declarada pelas empresas | Squad 1: painel "Panorama Mineração Goiás" | `Squad 1/dados/Panorama Mineracao Goias.html` (payload: `ee_cargas`, `coef`) |
| **Entrada** | CCEE bruta jun–dez/2025, usada só para conferir a energia | Squad 1 | `Squad 1/dados/CCEE/parcela_carga_consumo_2025_GO.csv` |
| **Entrada** | Produção beneficiada 2025 por titular e operação (ANM, rateada pela CFEM) e IDs `mineral_id`, `company_id`, `operation_id` | Squad 1 / Estudante 1 (aba 12) | `Squad 1/Bases consolidadas/documentacao/pacote_squad2/interface_squad1_squad2.csv` |
| **Entrada** | Parâmetros de intensidade do motor, incluídos como `benchmark` | Squad 2 / Estudante 3 | `Squad 2/modello_reale/parameters/energy_intensity.csv` (só leitura) |
| **Saída** | Intensidade por operação no formato do contrato do motor | Squad 2 / Estudante 3 (motor 2027–2040) | `energy_intensity_para_motor_v1.csv` |
| **Saída** | Um coeficiente estadual por mineral, pronto para substituir `parameters/energy_intensity.csv` | Squad 2 / Estudante 3 (backtest, cenários e sensibilidade) | `coeficiente_estadual_para_modelo_v1.csv` |
| **Saída** | Base completa com rastreabilidade | Squad 3 (banco/API e simulador) | `base_intensidade_energetica_v1.csv` + dicionário |

## Coeficiente estadual para o modelo

O modelo usa **um coeficiente por mineral e base de produção**, aplicado à produção total de Goiás. O arquivo
`coeficiente_estadual_para_modelo_v1.csv` resume a base nesse formato. A base e a saída por operação não mudam.

As seis primeiras colunas são as mesmas de `Squad 2/modello_reale/parameters/energy_intensity.csv`
(`mineral_id, mineral_name, production_basis, energy_intensity_mwh_t, source_id, data_nature`), na mesma ordem e com as mesmas
linhas. As demais colunas dão o rastro: `aggregation_method`, `intensity_ids` (linhas da base usadas), `energy_mwh`,
`production_t`, `coverage_share` (parcela da produção beneficiada estadual de 2025 coberta pela energia observada),
`range_min_mwh_t`/`range_max_mwh_t`, `confianca`, `valor_modelo_atual_mwh_t`, `variacao_vs_modelo_pct` e `observacao`.

**Agregação:** Σ energia CCEE 2025 ÷ Σ produção 2025 das operações cobertas, na base de produção do modelo. É a média das
intensidades ponderada pela produção. Não se somam a planta e o agregado da mesma empresa, e benchmarks nunca entram na conta.

| Mineral | Base | Coeficiente | Modelo atual | Natureza | Cobertura | Linhas da base |
|---|---|---:|---:|---|---:|---|
| Cobre | conteúdo mineral | 8,108 MWh/t Cu | 11,20 | calculado | 100% | INT_004 |
| Bauxita | beneficiada | 1,40 MWh/t | 1,40 | benchmark_proxy | 0% | INT_021 (parâmetro atual) |
| Níquel | beneficiada | 11,674 MWh/t | 45,55 | estimado | 97,7% | INT_012 |
| Fosfato | beneficiada | 0,1212 MWh/t | 0,15 | estimado | 100% | INT_015 + INT_016 |
| Amianto | beneficiada | 0,3109 MWh/t | 0,32 | estimado | 100% | INT_018 |

Observações:

- **Níquel:** o valor atual do modelo (45,55) está em MWh por tonelada de **Ni contido**, mas é aplicado à produção
  **beneficiada** (ferroníquel), que é cerca de 4 vezes maior. Na base beneficiada, o coeficiente é 11,67. Com o valor atual, a
  energia do níquel sai cerca de 4 vezes maior.
- **Cobre:** a produção declarada pela Lundin (43.974 t Cu) confere com a série da ANM que o modelo lê
  (43.983,55 t em 2025, v17 aba 08): diferença de 0,02%.
- **Bauxita:** nenhum dos 3 titulares de bauxita aparece na CCEE. Sem energia observada, fica o parâmetro atual do modelo,
  marcado como `benchmark_proxy`.
- **Fosfato:** Mosaic (0,089) e Copebrás (0,169) somados. Como as duas cobrem 100% da produção estadual, a soma dos
  denominadores é o total do estado e a incerteza do rateio da CFEM some no agregado (faixa = valor central).
- **Circularidade:** a base copia `parameters/energy_intensity.csv` como benchmark (INT_020–024). Se o modelo substituir esse
  arquivo por este, os benchmarks da base passam a repetir os valores daqui ao gerar de novo.

## Fórmula e unidades

Segue o consumo específico do Manual Metodológico do Atlas da Eficiência Energética (EPE):

```
intensidade (MWh/t) = energia elétrica consumida no ano (MWh) ÷ produção física do mesmo ano (t)
```

- **Energia:** `CONSUMO_TOTAL` da CCEE (Parcela de Carga, consumo mensal), somado de janeiro a dezembro de 2025 por unidade consumidora (`SIGLA_PARCELA_CARGA`), em MWh.
- **Produção:** em toneladas (`production_t`). Ouro vem em kg e é dividido por 1.000; a base também mostra o ouro em MWh/kg (`intensidade_valor`).
- **Pareamento energia × operação:** pela **raiz do CNPJ** (8 primeiros dígitos) da carga na CCEE, a mesma chave do `company_id` do Squad 1 (`COM_CNPJ_<raiz>`). Não se usa o nome da empresa. Quando o mesmo CNPJ tem mais de um produto (CMOC), as cargas são separadas pela sigla e pelo ramo de atividade informados pela CCEE, e a base mantém também a versão sem separação (teto).
- **Mesmo período:** numerador e denominador são de 2025. As duas exceções têm produção publicada apenas para 2024 (Serra Grande e SAMA). Elas estão marcadas em `compatibilidade_temporal` e ficam fora da saída para o motor.

## Natureza dos dados

| `nivel` | Linhas | Denominador | `natureza_dado` |
|---|---:|---|---|
| `operacao_empresa` / `unidade_consumidora` | 11 | Produção declarada pela empresa (metal contido ou produto) | `calculado`: energia observada ÷ produção declarada. `estimado` quando o denominador é capacidade (Mosaic) ou exportação (Serra Verde) |
| `titular_mineral_ano` | 8 | Produção **beneficiada** da ANM atribuída ao titular pela aba 12 do Squad 1 | `estimado`: a ANM não publica produção por operação e o Squad 1 rateia o total do estado pela CFEM; a faixa de erro está em `erro_estimativa_intervalo` |
| `benchmark_mineral` | 5 | — | `benchmark`: parâmetros do motor, copiados sem alteração; não são observação de operação |

`valor_observado_estimado` repete `natureza_dado` com o nome do padrão de rastreabilidade da Entrega 1 (§3).
`project_id` fica vazio porque todas as linhas são operações em produção.

## Rotas tecnológicas

A rota só foi preenchida onde há fonte documental. Nas outras linhas, `tecnologia = nao_levantada_v1`, e a base traz o
ramo de atividade que a própria CCEE informa para a carga (`ramo_atividade_ccee`).

| Operação | Rota (fonte: painel Panorama Mineração Goiás, Squad 1) | Ramo na CCEE | Intensidade |
|---|---|---|---:|
| Anglo American — Barro Alto e Codemin (níquel) | Metalurgia: forno elétrico reduzindo laterita a ferroníquel | Metalurgia e produtos de metal | 45,0 MWh/t Ni |
| Maracá (Lundin) — Chapada (cobre) | Concentra por flotação e embarca o concentrado | Extração de minerais metálicos | 8,1 MWh/t Cu |

**Diferença tecnológica entre as duas:** a operação com metalurgia no site (níquel) gasta cerca de 5,5 vezes mais energia por tonelada de metal do que a operação que só concentra (cobre). As duas plantas da Anglo, com a mesma rota, ficam no mesmo patamar (44,95 e 45,49 MWh/t Ni).

## Resultados

Energia da CCEE 2025 ÷ produção declarada pela empresa:

| Mineral | Operação | Intensidade | Natureza | Confiança | Observação |
|---|---|---:|---|---|---|
| Níquel | Anglo — Barro Alto | 44,95 MWh/t Ni | calculado | alta | |
| Níquel | Anglo — Codemin | 45,49 MWh/t Ni | calculado | alta | |
| Cobre | Maracá — Chapada | 8,11 MWh/t Cu | calculado | alta | ouro sai como subproduto no mesmo concentrado |
| Nióbio | CMOC — cargas de nióbio | 10,46 MWh/t Nb | calculado | média | separação pela sigla e pelo ramo da CCEE |
| Nióbio | CMOC — CNPJ inteiro (teto) | 28,32 MWh/t Nb | calculado | média | inclui a carga Copebrás |
| Fosfato | Mosaic — Catalão | 0,127 MWh/t | estimado | baixa | denominador é capacidade |
| Ouro | Serra Grande — Crixás | 46,0 MWh/kg | calculado | baixa | produção de 2024 |
| Ouro | Amarillo — Mara Rosa | 66,6 MWh/kg | calculado | alta | ano de ramp-up com parada de 4 semanas |
| Amianto | SAMA — Minaçu | 0,334 MWh/t | calculado | média | produção de 2024 |
| Terras raras | Serra Verde — Minaçu | 10,06 MWh/t TREO | estimado | baixa | denominador é exportação; fator de carga de 6,5% |

Energia da CCEE 2025 ÷ produção beneficiada da ANM 2025 (estimada pelo Squad 1), que é a mesma base de produção usada pelo motor: Níquel 11,67; Cobre 1,76; Nióbio 0,033; Fosfato 0,089 (Mosaic) e 0,169 (Copebrás); Ouro 58,8 MWh/kg; Amianto 0,311; Terras raras 20,93 MWh/t.

## Limitações

1. **Só energia elétrica do mercado livre:** a CCEE traz consumo individual apenas de quem está no ACL. Diesel, outros combustíveis, autoprodução e compras no mercado cativo não entram. Mineradoras que compram da distribuidora não aparecem; esta versão cobre 8 empresas.
2. **Energia de 12 meses vem do painel do Squad 1:** o arquivo bruto no repositório tem só jun–dez/2025. A coluna `checagem_ccee_bruta` compara os dois: diferença de −7% a +3%, e −19% em Mara Rosa, que teve parada no ano.
3. **Denominador da ANM é estimado:** as linhas `titular_mineral_ano` usam o rateio da CFEM do Squad 1, que o próprio Squad 1 indica não usar como denominador observado. Por isso estão marcadas como `estimado`, com faixa de erro.
4. **Rotas tecnológicas:** levantadas para 2 das 8 empresas. As demais ficam como `nao_levantada_v1` até haver fonte documental.
5. **Nióbio na ANM:** a produção "beneficiada" da ANM para a CMOC (cerca de 3,3 Mt) é massa processada, não Nb contido. A intensidade nessa base (0,033 MWh/t) só vale aplicada à mesma série da ANM.
6. **Base de produção dos benchmarks:** a base de produção a que cada parâmetro do motor se refere (`conteudo_mineral` ou `beneficiada`) deve ser a mesma da série de produção a que ele é aplicado. Nesta base, a intensidade do níquel é 45,05 MWh/t de Ni contido e 11,67 MWh/t de produção beneficiada (ferroníquel). O alinhamento com o motor fica a cargo do Estudante 3.

## Próximos passos

- Levantar as rotas tecnológicas das 6 empresas restantes em relatórios de sustentabilidade, com link.
- Incluir diesel e outros combustíveis quando houver dado, para chegar à energia total.
- Atualizar Serra Grande e SAMA quando a produção de 2025 for publicada.
