# Camadas do P3M recortadas pelo polígono de Goiás

156 camadas (513,6 MB), uma por zip, com o mesmo nome do zip de origem, na mesma pasta temática que ele tem em `Original/`.
Recorte feito em 21/10/2026 com `Original/6- Cartografia/GO_UF_2024.zip` (limite estadual do IBGE), sobre os zips de `Original/` —
os baixados com o Brasil inteiro ou só com Goiás e os baixados com o retângulo em volta de Goiás (a coluna `extensao_original` de
`../inventario_p3m.csv` diz qual é qual).

**Os originais não foram alterados.** Fica de fora `Recursos Minerais SIG Lítio.zip`: os 46 pontos ficam todos em Minas Gerais.

## Como foi o recorte

- Pontos: ficam os que estão dentro ou na divisa de Goiás.
- Linhas e polígonos: o que está inteiro dentro de Goiás fica como veio; o que cruza a divisa tem a geometria cortada no limite do
  estado (como o *Recortar* do QGIS). Atributos não mudam — inclusive área, comprimento e contagens gravados nas tabelas, que continuam
  valendo para a feição inteira, não para o pedaço recortado.
- **Fiapos de divisa**: o limite do IBGE e o das outras bases não coincidem exatamente, então um polígono que só encosta em Goiás (um
  município vizinho, por exemplo) sobraria como uma tira finíssima. Polígonos cujo pedaço em Goiás tem menos de 1% da área original
  **e** menos de 10 km² foram descartados (1721 no total; coluna `fiapos_de_divisa_removidos`). Com isso as camadas municipais do IBGE
  ficam com os 246 municípios de Goiás.
- Polígonos com geometria inválida na origem foram corrigidos (`make_valid`) antes do recorte, mantendo só a parte poligonal.
- Codificação: os zips do P3M são UTF-8 (indicado no `.cst`, que o QGIS não lê). Aqui cada shapefile vem com `.cpg` = UTF-8, então
  acentos abrem certos sem configurar nada. Sistema de coordenadas: SIRGAS 2000 (EPSG:4674), igual à origem.
- Alguns pontos dentro do limite do IBGE trazem outra UF no atributo (ex.: 2 das 1.796 ocorrências minerais), por diferença entre os
  limites usados pelo SGB e pelo IBGE; foram mantidos como estão.

Contagem de registros antes e depois, por camada, em `_indice_recorte.csv` (o gerador do Mapa mineral confere o recorte por ele) e,
junto com o resto da descrição de cada camada, em `../inventario_p3m.csv`.
