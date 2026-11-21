# Repositório de erros — bases do Squad 1

Squad 1 / Estudante 1 (Frente 1). Gerado em 2026-11-21 por `Squad 1/Bases consolidadas/base_consolidada_work/scripts/gerar_repositorio_erros.py`,
a partir de `Squad 1/Dados brutos/` e da planilha `prototipo_bases_consolidadas_v18.xlsx`. Planilha completa: [`repositorio_erros.xlsx`](repositorio_erros.xlsx).
Todo número abaixo é recalculado a cada execução. **Regra do projeto:** divergência é registrada, não corrigida.

| Aba | O que tem |
|---|---|
| `erros` | catálogo com 45 erros (ERR_001…), com fonte, exemplo, número medido, impacto, regra adotada, checagem e status |
| `bario_niobio`, `bario_niobio_processos` | bário × nióbio em Goiás: AMB (bruta, beneficiada, contido) e CFEM por substância e processo |
| `contido_vs_bruto` | todos os minerais de Goiás: teor implícito e alertas C1…C8 |
| `tonelagens_repetidas` | mesma tonelagem em linhas diferentes, todas as UFs (76 grupos, 170 linhas) |
| `amb_x_cfem` | Goiás 2022–2025: produção e valor no AMB × CFEM, comparados com a alíquota legal |

Lista de suspeitas de unidade trocada no AMB e na CFEM: [`auditoria_unidades_anm.md`](auditoria_unidades_anm.md).

## 1. Bário × nióbio: dá para separar?

| O que | Separa? | Por quê |
|---|---|---|
| Produção bruta (ROM) no AMB | **Não de verdade** | Cada mineral tem sua linha, mas o ROM do bário é a rocha lavrada para nióbio e fosfato. Em 2023 os dois têm exatamente **5.526.825,44 t** (linhas 5180 e 5187 do `Producao_Bruta.csv`). Na base, esse ROM tem status `rom_minerio_associado` e não é aberto por operação. |
| Contido | **Sim** | BaSO₄ para o bário e Nb₂O₅ para o nióbio. |
| Produção beneficiada | **Sim**, com cuidado | O nióbio mudou de conceito em 2024 (ver abaixo). |
| CFEM | **Sim** | `BARITA` × `NIÓBIO` / `MINÉRIO DE NIÓBIO`; os mesmos processos pagam as duas. |

**Nióbio beneficiado:** 31.010 t em 2023 → 3.562.063 t em 2024 → 3.280.805 t em 2025, com o teor
caindo de ~50% para ~1,4% Nb₂O₅ (a ANM passou a registrar a massa que entra na usina). **Decidido em 19/11/2026 e aplicado na v18:** a série é o contido
em Nb₂O₅ — 15.449 t (2023), 49.890 t (2024), 44.523 t (2025). Na aba 09,
`serie_beneficiada = contido`; na 12, `production_basis = conteudo_mineral`.

## 2. "O contido é sempre verdadeiro?" — Não

807 linhas mineral-base-ano de Goiás; 260 com alerta (verificar 111,
lacuna 97, informativo 52). Os principais: ERR_004 (ouro 2022:
2.799 t de ouro contido no ROM), ERR_005 (nióbio), ERR_003 (contido com unidade '-'), ERR_008 (contido sem indicação), ERR_007 (lacunas).

## 3. Royalties: CFEM paga num mineral e não em outro

CFEM somada por ano (2022–2025): 2022: R$ 176,3 mi; 2023: R$ 161,6 mi; 2024: R$ 183,8 mi; 2025: R$ 229,9 mi. A CFEM foi dividida pelo valor do AMB de
duas formas (só vendas; vendas + consumo + transferência) e comparada com a alíquota da Lei 8.001/1990 (redação da Lei 13.540/2017).

| Classe | Mineral-anos | Quais |
|---|---|---|
| Compatível com a alíquota | 69 | — |
| **R1** — produção no AMB sem CFEM | 17 | Areias Industriais 2022; Areias Industriais 2023; Areias Industriais 2024; Areias Industriais 2025; Bário 2025; Diamante 2023; Diamante 2025; Feldspato, Leucita e Nefelina-Sienito 2022; Feldspato, Leucita e Nefelina-Sienito 2023; Feldspato, Leucita e Nefelina-Sienito 2024; Feldspato, Leucita e Nefelina-Sienito 2025; Fluorita e Criolita 2024; Monazita e Terras-Raras 2023; Talco e outras Cargas Minerais 2022; Talco e outras Cargas Minerais 2023; Talco e outras Cargas Minerais 2024; Talco e outras Cargas Minerais 2025 |
| **R2** — CFEM sem produção no AMB | 16 | Minerais Industriais (Outros) 2022; Minerais Industriais (Outros) 2023; Minerais Industriais (Outros) 2024; Minerais Industriais (Outros) 2025; Potássio 2022; Potássio 2023; Potássio 2024; Potássio 2025; Quartzo (Cristal) e outros Piezelétricos 2024; Rochas Ornamentais - Outras 2023; Rochas Ornamentais - Outras 2024; Rochas Ornamentais - Outras 2025; Água Mineral 2022; Água Mineral 2023; Água Mineral 2024; Água Mineral 2025 |
| **R4** — CFEM acima de 2× a alíquota | 11 | Dolomito e Magnesita 2023; Dolomito e Magnesita 2025; Ferro 2024; Manganês 2024; Manganês 2025; Monazita e Terras-Raras 2024; Prata 2024; Rochas Ornamentais 2022; Rochas Ornamentais - Outras 2022; Titânio 2024; Titânio 2025 |
| **R5** — CFEM abaixo de 1/4 da alíquota | 2 | Gemas 2024; Níquel 2022 |
| **R6** — AMB com valor menor que a CFEM | 4 | Amianto 2024; Diamante 2024; Manganês 2023; Saibro 2022 |

## 4. Catálogo (45 erros)

| Código | Fonte | Erro | Status |
|---|---|---|---|
| ERR_001 | ANM — AMB (Produção Bruta/Beneficiada) | A mesma tonelagem aparece em linhas de minerais diferentes da mesma UF e ano (co-produto que sai do mesmo minério: Chumbo+Zinco, Ouro+Prata, Bário+Nióbio). | sinalizado |
| ERR_002 | ANM — AMB (Produção Bruta/Beneficiada) | A mesma declaração aparece em duas categorias do mesmo grupo. | sinalizado |
| ERR_003 | ANM — AMB (Produção Bruta/Beneficiada) | Contido com unidade '-': quase sempre zero (não se aplica), mas às vezes com valor. | tratado |
| ERR_004 | ANM — AMB (Produção Bruta/Beneficiada) | Contido do ouro na produção bruta de GO em 2022 implica teor de 97,1 g/t, contra mediana de 0,41 g/t nos outros anos. | sinalizado |
| ERR_005 | ANM — AMB (Produção Bruta/Beneficiada) | A produção beneficiada de nióbio muda de ordem de grandeza em 2024, com o teor caindo de ~50% para ~1,4% Nb2O5: passou a declarar a massa que entra na usina, não o concentrado. | tratado (v18) |
| ERR_006 | ANM — AMB (Produção Bruta/Beneficiada) | Para ouro e prata, a bruta é tonelada de MINÉRIO e a beneficiada é kg de METAL | tratado (v14) |
| ERR_007 | ANM — AMB (Produção Bruta/Beneficiada) | Minerais somem do AMB em alguns anos (sem linha) ou vêm com zero entre anos com produção. | sinalizado |
| ERR_008 | ANM — AMB (Produção Bruta/Beneficiada) | Contido informado sem dizer o que é (óxido, metal ou o próprio produto). | sinalizado |
| ERR_009 | ANM — AMB (Produção Bruta/Beneficiada) | Em minas integradas (nióbio, fosfato) a venda da produção bruta é zero: o valor está em consumo/transferência para a usina. | tratado |
| ERR_010 | ANM — AMB (Produção Bruta/Beneficiada) | A ANM republica produção e CFEM com frequência (dados preliminares). | tratado |
| ERR_011 | ANM — CFEM (arrecadação GO) | Unidades misturadas para a mesma substância (t, kg, g, ct, m³, l, m²). | tratado |
| ERR_012 | ANM — CFEM (arrecadação GO) | Quantidade em notação científica ou inflada ~1000× (R$/unidade absurdo). | tratado |
| ERR_013 | ANM — CFEM (arrecadação GO) | No arquivo baixado em 09/2026, o CNPJ vinha como número em notação científica (34.212 de 38.854 linhas) e não identificava a empresa | resolvido na fonte (download atual com CNPJ completo) |
| ERR_014 | ANM — CFEM (arrecadação GO) | Processos da série 96xxxx não existem no Cadastro Mineiro nem no SIGMINE (sem titular e sem poligonal). | sinalizado |
| ERR_015 | ANM — CFEM (arrecadação GO) | Processo declara mais toneladas que o estado inteiro produziu no AMB, ou R$/t incompatível. | sinalizado |
| ERR_016 | ANM — CFEM (arrecadação GO) | Minério declarado como ouro (t de minério com preço de minério). | sinalizado |
| ERR_017 | ANM — CFEM (arrecadação GO) | Linhas iguais no grão são recolhimentos distintos, não duplicatas. | tratado |
| ERR_018 | ANM — CFEM (arrecadação GO) | A CFEM não traz o uso | tratado (v7) |
| ERR_019 | ANM — CFEM (arrecadação GO) | O último ano da CFEM é parcial. | tratado |
| ERR_020 | ANM — CFEM (arrecadação GO) | A CFEM usa nomes próprios, diferentes das categorias do AMB. | tratado |
| ERR_021 | ANM — Cadastro Mineiro | Campo multivalorado e nacional | tratado |
| ERR_022 | ANM — Cadastro Mineiro | 'Situação' = 'Sim' em todas as linhas (os dados abertos só têm processos ativos). | tratado |
| ERR_023 | ANM — Cadastro Mineiro | Jurisdição regional da ANM não segue a fronteira do estado. | tratado |
| ERR_024 | ANM — Cadastro Mineiro | Aspas dentro de campos sem escape quebram a linha | pendente — novo |
| ERR_025 | ANM — Cadastro Mineiro | Titular pessoa física aparece com CPF no nome. | tratado (v12) |
| ERR_026 | ANM — Cadastro Mineiro | Processo que cruza a divisa às vezes só cita o município do outro estado. | tratado (v16) |
| ERR_027 | ANM — SIGMINE | Campo UF não é recorte territorial (processos com UF=MG parcialmente em GO, UF=PA 100% em GO). | tratado |
| ERR_028 | ANM — SIGMINE | Polígonos com autointerseção e processos fragmentados em várias feições. | tratado |
| ERR_029 | ANM — SIGMINE | SIGMINE não tem município | tratado |
| ERR_030 | ANM — SIGMINE | SIGMINE mantém processos encerrados (indeferimento, caducidade, renúncia…). | tratado |
| ERR_031 | ANM — SIGMINE | Simplificar poligonais de título deforma polígonos pequenos. | tratado |
| ERR_032 | SGB — RECMIN (ocorrências) | Campos preenchidos com valor padrão: localização genérica, situação do garimpo copiada da mina, data de cadastro = data da carga. | tratado |
| ERR_033 | SGB — RECMIN (ocorrências) | Substâncias em ordem alfabética, sem principal | tratado |
| ERR_034 | IBGE — SIDRA e malha | Os JSON 'municipais' trazem também a linha da UF (D1C=52). | tratado |
| ERR_035 | IBGE — SIDRA e malha | PIB vem em mil reais. | tratado |
| ERR_036 | IBGE — SIDRA e malha | Centro da caixa envolvente cai fora do município. | tratado |
| ERR_037 | IMB — Goiás em Dados | Produção do IMB parece contido para cobre, nióbio e níquel (sempre abaixo do AMB) | tratado (v17) |
| ERR_038 | CCEE — consumo de energia | Cargas sem ramo são as distribuidoras (mercado cativo), não um setor | tratado |
| ERR_039 | Pipeline (reprodutibilidade) | A ordem de um set muda a cada execução do Python | tratado |
| ERR_040 | Pipeline (reprodutibilidade) | core.autocrlf trocava CRLF↔LF nos brutos e o sha256 deixava de bater. | tratado |
| ERR_041 | Pipeline (reprodutibilidade) | Windows apaga de %TEMP% arquivos com data antiga | tratado |
| ERR_042 | Pipeline (reprodutibilidade) | Nome de aba > 31 caracteres e cabeçalho renomeado sem atualizar a Tabela corrompem o xlsx. | tratado |
| ERR_043 | Cruzamento AMB × CFEM | Produção no AMB sem nenhuma CFEM no ano. | sinalizado |
| ERR_044 | Cruzamento AMB × CFEM | CFEM paga sem produção no AMB. | sinalizado |
| ERR_045 | Cruzamento AMB × CFEM | CFEM incompatível com o valor declarado no AMB e a alíquota legal (Lei 8.001/1990, Anexo, redação da Lei 13.540/2017). | sinalizado |

Por status: sinalizado 11, tratado 32, resolvido 1, pendente 1. A coluna `onde_foi_conferido` diz de onde veio cada número; os marcados
"registro do projeto" foram medidos num arquivo ou momento que não está no repositório (com a data).

**Pendente:** ERR_024 — os CSV nacionais do Cadastro Mineiro têm aspas sem escape, e o leitor com `on_bad_lines="skip"` descarta essas linhas sem aviso
(1.184 no download nacional de 09/2026, nenhuma de Goiás; 0 no recorte do repositório). Proposta: contar as descartadas e falhar se alguma citar "- GO".
