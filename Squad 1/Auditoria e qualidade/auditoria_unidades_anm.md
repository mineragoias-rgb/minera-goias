# Auditoria de unidades de medida — AMB e CFEM (ANM)

Squad 1 / Estudante 1 — Frente 1, 18/11/2026. Script: `Squad 1/Bases consolidadas/base_consolidada_work/scripts/auditoria_unidades_anm.py`.
Lista completa (506 suspeitas, uma por linha, com fator, leitura e R$ envolvido): `auditoria_unidades_anm.csv`.

Os arquivos brutos da ANM foram lidos como vieram (`Squad 1/Dados brutos`). **Nada foi corrigido**: a lista é para revisão e
para a pergunta à ANM. CPF de pessoa física não aparece na saída.

## Como a verificação funciona

Unidade trocada tem uma assinatura: **a quantidade pula uma potência de 10 e o valor em R$ não acompanha** — o preço
implícito (R$ ÷ quantidade) muda pelo mesmo fator. Quando quantidade e valor sobem juntos, é produção real e não entra.

| Código | Base | O que procura |
|---|---|---|
| U1 | AMB | mesma substância declarada em unidades diferentes |
| U2 | AMB, todas as UFs | ano com quantidade 10^k fora da mediana dos outros anos (≥ 3 anos) e valor em R$ na escala usual; contido, sem valor, só com fator ≥ 1000 |
| U3 | AMB | preço da venda 100x ou mais fora do próprio histórico da UF |
| U4 | AMB | preço da UF 1000x ou mais fora da mediana das outras UFs no mesmo ano |
| U5 | AMB | incoerências: venda > 5x a produção; contido > produção; beneficiada > 2x o ROM |
| C1 | CFEM GO | o mesmo processo e substância declarado em mais de uma unidade |
| C2 | CFEM GO | mês com preço implícito 100x ou mais fora da mediana do próprio processo |
| C3 | CFEM GO | a mesma substância em unidades diferentes entre processos |

"Potência de 10" = fator a menos de ±40% de 10, 100, 1000…; maior que isso e sem fator redondo é "salto".

## Resultado

| Verificação | Suspeitas | Em Goiás |
|---|---:|---:|
| U2 quantidade fora de escala (AMB) | 97 | 15 |
| U3 preço fora do histórico (AMB) | 23 | 1 |
| U4 preço fora das outras UFs (AMB) | 4 | 1 |
| U5 incoerências internas (AMB) | 128 | 9 |
| U1 unidade diferente (AMB) | 2 | 0 |
| C1 processo com mais de uma unidade (CFEM) | 128 | 128 |
| C2 mês fora de escala no processo (CFEM) | 101 meses em 41 processos (R$ 17,3 mi recolhidos) | todos |
| C3 substância em várias unidades (CFEM) | 23 | 23 |

## O que importa para Goiás

**AMB**

| Caso | O que o arquivo diz | Leitura |
|---|---|---|
| Nióbio, beneficiada 2024–2025 | 3,56 e 3,28 Mt, contra ~25 kt nos anos anteriores; valor só 1,7x maior | fator 10^2: a CMOC passou a declarar outra coisa (minério tratado, não concentrado). Já sinalizado no Panorama |
| Talco, ROM 2025 | 565.010 t vendidas por R$ 108 mil = R$ 0,19/t (histórico ~R$ 110/t) | kg declarado como t (fator 10^3): o certo seria ~565 t. Hoje entra nos 5,9% do ROM "sem empresa" |
| Ferro, beneficiada 2024 | 1,22 Mt por R$ 274 mil, contra 16–72 kt por R$ 15–39 mi nos outros anos | quantidade fora de escala; valor não acompanha |
| Dolomito, beneficiada 2021 e 2024 | 1,7 e 2,3 Mt beneficiadas contra 0,55 e 0,81 Mt de ROM | usina com mais produto que a mina: compra de outra UF, estoque ou unidade |
| Areias industriais 2016–2019 | ~100–145 kt beneficiadas para 0,1–9 kt de ROM | idem |
| Titânio, contido 2022 e ROM 2023 | 1 t e 25 t contra ~1.000 e ~28.600 t | fator 10^-3 |
| Gemas 2019 | R$ 1.569/t contra R$ 1,3 mi/t nas outras UFs | quantidade em kg como t (10^-3) |
| Bário, ROM | 5,6 Mt/ano com valor zero; em 2023 idêntico ao ROM do nióbio | o mesmo minério de Catalão contado de novo (ver a tabela de coprodutos) |

**CFEM (quantidade comercializada)**

| Processo | Caso | Leitura |
|---|---|---|
| Ouro 861241/1980 (Mara Rosa) | 2024: 150–235 kg/mês, coerente com o R$; a partir de jan/2025: milhões de "kg" por mês (até 210 mi em 2026) | a unidade mudou em 2025 sem mudar o rótulo; a quantidade de 2025–2026 não serve |
| Amianto 850037/1975 (SAMA) | meses com 0,01 t pagando R$ 0,9–1,2 mi | quantidade de preenchimento; o amianto aparece com 6 t na CFEM de 2025 |
| Calcário 960993/2007, 860669/1986, 860670/1986 | meses com 10^5 a 10^8 vezes a quantidade usual | digitação; a 09b já tira os piores da soma |
| Vermiculita 807299/1977 e 811652/1975 | o mesmo processo em kg (~49 meses) e em t (~6 meses) | somar meses mistura unidades |
| 23 substâncias (areia, argila, granito, gnaisse, quartzito, água…) | t, kg, m3, m2 e l para a mesma substância entre processos | somar entre processos exige converter (m3 → t pede densidade) |

## Efeito na base consolidada e no site

- **Divisão da produção por empresa (aba 12): sem efeito.** A divisão usa a CFEM em R$, não a quantidade; foi escolhida
  exatamente por isso.
- **Auditoria 09b:** já tira da soma em t 89 linhas com fator > 1000 contra a mediana do mineral. A verificação nova, por
  processo, pega casos que a 09b não pega (Mara Rosa 2025, amianto 0,01 t).
- **Mapa de produção do Atlas (CFEM 2025 em t por substância e município): afetado.** Mostra amianto com 6 t (o AMB tem
  179 mil t beneficiadas) e ouro com 15 t (o AMB tem 3 t). Proposta: marcar no Atlas que a quantidade da CFEM não é
  confiável para essas substâncias, ou trocar a quantidade pelo AMB rateado (aba 12).
- **Totais do AMB:** talco 2025 (565 kt) e bário (5,6 Mt) inflam o ROM de Goiás em ~5%; nióbio 2024–2025 distorce o preço
  implícito da beneficiada no Panorama.

## Para perguntar à ANM

1. Nióbio, Goiás, beneficiada 2024–2025: o que passou a ser declarado (3,3–3,6 Mt contra ~30 kt antes)?
2. Talco, Goiás, ROM 2025: 565.010 t ou 565 t?
3. Bário, Goiás, ROM: é o mesmo minério da mina de nióbio declarado de novo?
4. CFEM do processo 861241/1980: em que unidade está a quantidade a partir de jan/2025?
