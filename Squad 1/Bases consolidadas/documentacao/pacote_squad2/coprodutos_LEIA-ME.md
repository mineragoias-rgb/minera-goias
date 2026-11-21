# Coprodutos — rateio da energia por valor (2025)

Gerado por `base_consolidada_work/scripts/gerar_coprodutos.py` (chamado no fim de `gerar_pacote_squad2.py`). Tabela:
`coprodutos_rateio_valor_2025.csv` (`;`, UTF-8), uma linha por operação × carga da CCEE × produto.

## Regra
1. **Separação física:** carga da CCEE dedicada a um produto fica inteira nele.
2. **Carga compartilhada:** energia do produto *i* = energia da carga × valor*ᵢ* / Σ valor.
3. **Materialidade:** coproduto com menos de 5% do valor da operação fica no produto principal.
4. **Preço:** realizado pela empresa > valor separado no AMB > referência do ano (LME/LBMA × PTAX).
5. **Preços fixos de 2025** para a projeção: a intensidade não oscila com a cotação.
6. **Conservação:** a energia rateada soma exatamente a carga medida (o script para se não somar).
7. **O coproduto que recebe energia precisa de série de produção própria no motor**; senão a energia dele some da previsão.

## Resultado
| Operação | Produto | Parcela do valor (carga compartilhada) | Energia rateada (MWh) | Intensidade rateada | Intensidade no motor hoje |
|---|---|---|---|---|---|
| Chapada (Alto Horizonte) | Cobre | 67,9% | 242.239 | 5,51 MWh/t | 8,11 MWh/t (conteudo_mineral) |
| Chapada (Alto Horizonte) | Ouro | 32,1% | 114.296 | 1,86 MWh/oz | fora do motor |
| Complexo Catalão/Ouvidor (CMOC) | Nióbio | 54,9% | 115.813 | 11,19 MWh/t | fora do motor |
| Complexo Catalão/Ouvidor (CMOC) | Fosfato | 45,1% | 177.203 | 0,11 MWh/t | 0,12 MWh/t (beneficiada) |

## Leitura para o Squad 2
- **Chapada:** hoje toda a energia vai para o cobre. Pelo valor, o ouro leva cerca de 1/3. Usar a intensidade rateada do cobre **sem** criar a linha
  do ouro de Chapada no motor tira essa energia da previsão. As duas formas coerentes: (a) cobre e ouro de Chapada como linhas separadas, cada um
  com a sua intensidade rateada; ou (b) manter "cobre equivalente" (toda a energia no cobre), como está, e registrar isso.
- **CMOC:** só a carga de rejeitos é compartilhada; o efeito no fosfato é pequeno. O nióbio está fora do motor: as cargas dele não entram na previsão.
- **Mosaic, Anglo e Serra Grande:** coproduto abaixo de 5% do valor; nada muda.
- **Bário:** o ROM de bário do AMB (~5,6 Mt/ano, sem valor) é a rocha que a CMOC lavra para nióbio e fosfato contada de novo — na base, status `rom_minerio_associado`, fora das somas de ROM e da abertura por operação. A barita está no contido (60 a 196 mil t de BaSO4/ano, 1–3,5% do minério); só 0 a 5 mil t/ano viram produto vendido (CFEM de barita da CMOC). Pouca massa e sem carga própria na CCEE: a energia fica com nióbio e fosfato. O mesmo vale para o cobalto do minério de níquel e a prata do minério de ouro e cobre.

Decidir entre (a) e (b) é do Squad 2: mexe na lista de minerais do motor. Esta tabela não altera nenhum parâmetro deles.
