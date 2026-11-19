# MapBiomas — vegetação nativa de Goiás, ano a ano

A camada "Vegetação nativa" do Mapa Mineral, com o seletor de ano, sai daqui. Quem grava esta pasta é o robô de atualização
(`robo/mapbiomas.py`, fonte `mapbiomas` de `robo/robo_bases.py`); nada aqui é editado à mão. Ver `robo/LEIA-ME.md`.

## De onde vem

**MapBiomas Brasil, Coleção 11: cobertura e uso da terra**, um GeoTIFF de 30 m por ano (1985 a 2025) para o Brasil inteiro, no
bucket público do MapBiomas: `https://storage.googleapis.com/mapbiomas-public/initiatives/brasil/collection11/lulc/coverage/brazil_coverage/`.
Licença CC BY 4.0 (citar o MapBiomas). Cada arquivo tem uns 700 MB; o robô lê só os ladrilhos da caixa de Goiás (uns 90 MB por ano),
por pedidos de faixa de bytes.

A legenda é a da Coleção 10 (aba `LEGEND_CODE` das estatísticas oficiais, no mesmo bucket), porque a Coleção 11 não publica
tabela de legenda. Classe que aparece no GeoTIFF e não está nessa legenda é contada como outro uso, e o robô avisa.

## Como cada ano vira um PNG

1. **Recorte.** Limite de Goiás do IBGE, o mesmo do Mapa Mineral (`Squad 1/P3M/Original/6- Cartografia/GO_UF_2024.zip`).
2. **Área por classe.** Em `metadados.json`, a área de cada classe do MapBiomas dentro de Goiás, contada nos pixels de 30 m
   (pixel com o centro dentro do limite, área na esfera de raio médio).
3. **Grade do mapa.** Pixels de Web Mercator do zoom 10 (uns 150 m), a mesma grade da camada da plataforma do MapBiomas. Cada pixel
   fica com o grupo que cobre a maior parte da sua área nos pixels de 30 m:
   - 1 = vegetação nativa florestal, "1. Floresta" da legenda (classes 3, 4, 5, 6 e 49);
   - 2 = vegetação nativa não florestal, "2. Vegetação Herbácea e Arbustiva" (classes 11, 12, 32, 29 e 50);
   - 0 = outro uso, ou fora de Goiás.
4. **Arquivo.** `cobertura_colecao11/vegetacao_nativa_goias_<ano>.png`, PNG de paleta com 2 bits por pixel e o índice 0
   transparente, e a linha do ano em `cobertura_colecao11/metadados.json`. A linha guarda a geração e o md5 do GeoTIFF no
   bucket, a data da leitura, o sha256 do PNG, os pixels de cada grupo e as áreas.

Numa execução, o robô só refaz o ano cujo GeoTIFF mudou no bucket (geração ou md5). Ele barra o ano que muda de forma, que tem
mais de 0,5% de Goiás sem classe ou em classe fora da legenda, ou que perde mais de 10% da vegetação nativa em relação ao mesmo
ano já gravado. Quando o MapBiomas publica uma coleção nova, ele avisa; a troca é no `robo/fontes.json`.

O site não lê esta pasta: `scripts/build_mapa_base.py` transforma cada PNG em `data/mapa/camadas/vegetacao_nativa_<ano>.json`. A
pasta fica fora do pacote do deploy (`.gitattributes`).
