# Camadas do P3M com dados de Goiás

Baixadas em 21/10/2026 do GeoServer do Serviço Geológico do Brasil (`https://opendata.sgb.gov.br/geoserver/wfs`), o mesmo serviço que o
site P3M (https://p3mgeo.sgb.gov.br/#/map) usa para desenhar e exportar as camadas, no mesmo formato dos zips já existentes na pasta acima
(SHAPE-ZIP do GeoServer: .shp, .shx, .dbf, .prj, .cst). Nenhum arquivo foi editado depois do download.

## Como foi feito o recorte

- A lista de camadas veio do catálogo do próprio site (`https://p3mgeo.sgb.gov.br/api/camadas/`): 444 entradas, 344 camadas distintas.
- Cada camada foi pedida com o retângulo que envolve Goiás (`bbox=-53.3,-19.6,-45.8,-12.3`, longitude/latitude). **Por isso os zips
  trazem também feições das bordas dos estados vizinhos** (MT, MS, MG, BA, TO, DF). A coluna `registros_que_tocam_goias` do
  `_indice_camadas.csv` diz quantas feições de cada camada tocam o polígono de Goiás (`../GO_UF_2024.zip`); para usar só Goiás,
  recorte pelo polígono no QGIS (Vetor → Geoprocessamento → Recortar).
- Para cada camada, o número de registros baixados bate com o que o servidor informa para o mesmo retângulo.
- Camadas de malha municipal do IBGE (PIB, IDH, renda, densidade, regiões) vêm com os 394 municípios que tocam o retângulo; os de Goiás
  são 246.

## O que não foi baixado, e por quê

- **Já estavam na pasta** (os 19 zips do P3M acima, conferidos: mesmo número de registros que o site hoje): as 8 camadas `vw_cprm_go_*`
  e as nacionais Distritos Auríferos, Folhas 1:100.000, Geocronologia, Levantamentos Aerogeofísicos 1000 a 4000, Ocorrências Minerais,
  Recursos Minerais PDAC 2024, Lítio e Urânio. Essas nacionais estão inteiras (Brasil todo), não recortadas.
- **Sem nenhuma feição em Goiás**: 108 camadas estaduais de outras UFs (`vw_cprm_<uf>_*`), a geologia marinha (`geomar`) e outras
  11 que só tinham feições no retângulo, fora do estado (Batimetria: Curvas Batimétricas, Batimetria: Áreas Batimétricas, Impact Crater SIG, Impact Craters SIG, Kimberlite SIG, Levantamento Litoestratigráfico Escala 1:50.000, Ocean Crust Age SIG, Ocean Features SIG, Oceanic Crust Ages SIG, Oceanic Features SIG, Solar Fotovoltaica).
- **SIGEF Total** (`vw_incra_sigef_total`): é a soma exata de SIGEF Público + SIGEF Privado, que estão aqui.
- **Só existem como imagem no site, sem dado vetorial para baixar**: a geofísica (Anomalias Magnéticas, Primeira Derivada, Contagem
  Total, Potássio, Equivalente Tório e Urânio, Razão Tório/Potássio, Ternário, Anomalia de Bouguer, Gradiente Total), Grupamentos
  Mineiros, SNCI (público, privado e total) e Cadastro Nacional de Florestas Públicas.

## Camadas

No repositório, `SIGEF Público (vw_incra_sigef_pbl).zip` está dividido em `parte 1 de 2` e `parte 2 de 2` (limite de 100 MB do GitHub);
veja o LEIA-ME de `Squad 1/P3M`.

138 zips, 932,3 MB. Detalhe e link de metadados de cada uma em `_indice_camadas.csv`.

### 1. Mineração (ANM e SGB)

| Arquivo | Registros baixados | Tocam Goiás |
|---|---:|---:|
| Ativos SGB (projetos CINFO) (mvw_ativos_sgb_cinfo).zip | 14 | 8 |
| Barragens de Mineração (vw_anm_barg_min).zip | 52 | 22 |
| Guia de Utilização (mvw_guia_utilizacao).zip | 1.116 | 652 |
| Minas Ativas (mvw_minas_ativas_grp).zip | 1.159 | 749 |
| Processos Minerários ativos (mvw_processos_minerarios_ativos).zip | 25.631 | 17.060 |
| Reservas Garimpeiras (vw_anm_reserv_garip).zip | 2 | 2 |
| Servidões Minerárias (vw_anm_svd_min).zip | 355 | 200 |

### 2. Geoquímica e diamante

| Arquivo | Registros baixados | Tocam Goiás |
|---|---:|---:|
| Afloramentos de Kimberlito (vw_cprm_aflor_kimb).zip | 744 | 199 |
| Concentrado de bateia (vw_cprm_geoq_concentrado_de_bateia).zip | 1.838 | 500 |
| Contagem de Pintas Au (vw_cprm_geoq_contagem_de_pintas_au).zip | 431 | 295 |
| Geoquímica (vw_cprm_geoquimica).zip | 10.770 | 3.403 |
| Geoquímica de Baixa Densidade (vw_cprm_geoq_b_d).zip | 1.740 | 515 |
| Minerais Indicadores (vw_cprm_min_indic_d).zip | 2.483 | 642 |
| Mineralometria (vw_cprm_geoq_mineralometria).zip | 4.310 | 1.496 |
| Ocorrências de Diamantes (vw_cprm_ocorr_diamante).zip | 375 | 114 |
| Outros (vw_cprm_geoq_outros).zip | 204 | 4 |
| Química Mineral (vw_cprm_quim_min_d).zip | 5.388 | 2.062 |
| Rocha (vw_cprm_geoq_rocha).zip | 7.057 | 5.391 |
| Sedimento de Corrente (vw_cprm_geoq_sedimento_de_corrente).zip | 18.365 | 3.869 |
| Solo (vw_cprm_geoq_solo).zip | 2.012 | 107 |

### 3. Geologia, mapeamentos e hidrogeologia (SGB)

| Arquivo | Registros baixados | Tocam Goiás |
|---|---:|---:|
| Afloramentos Geológicos (vw_cprm_aflor_geo).zip | 41.677 | 36.124 |
| Cenozoic Inset SIG (vw_cprm_tmsa_cenoz_inset).zip | 3 | 1 |
| Contato Atlas Hidrogeológico (vw_cprm_cont_a_hidrog).zip | 1.661 | 989 |
| Continent Structure Inset SIG (vw_cprm_tmsa_cont_str_inset).zip | 25 | 21 |
| Continent Structure SIG (vw_cprm_tmsa_cont_str).zip | 148 | 113 |
| Craton Terranes Limits Inset SIG (vw_cprm_tmsa_crat_terr_lim_inset).zip | 6 | 4 |
| Craton Terranes Limits SIG (vw_cprm_tmsa_crat_terr_lim).zip | 6 | 4 |
| Fauts SIG (vw_cprm_gmsa_fauts).zip | 135 | 114 |
| Furos de sondagem (vw_cprm_furos_sondagem).zip | 227 | 10 |
| Geology SIG (vw_cprm_gmsa_geology).zip | 200 | 139 |
| Isopachs SIG (vw_cprm_tmsa_isopacjs).zip | 4 | 3 |
| Kimberlite Clusters SIG (vw_cprm_gmsa_kimb_cluster).zip | 5 | 3 |
| Kimberlites SIG (vw_cprm_tmsa_kimberlits).zip | 197 | 59 |
| Levantamento Litoestratigráfico Escala 1-1.000.000 (vw_cprm_lev_litostrat_1000000).zip | 5.702 | 4.133 |
| Levantamento Litoestratigráfico Escala 1-100.000 (vw_cprm_lev_litostrat_100000).zip | 5.312 | 2.306 |
| Levantamento Litoestratigráfico Escala 1-2.500.000 (vw_cprm_lev_litostrat_2500000).zip | 232 | 158 |
| Levantamento Litoestratigráfico Escala 1-250.000 (vw_cprm_lev_litostrat_250000).zip | 1.673 | 69 |
| Mapa Índice dos Mapas Geológicos Estaduais (vw_crpm_mapa_indc_geologico_est).zip | 7 | 7 |
| Mapeamentos 1-1.000.000 (vw_cprm_map_geo_1m).zip | 4 | 4 |
| Mapeamentos 1-100.000 (vw_cprm_map_geo_100k).zip | 112 | 63 |
| Mapeamentos 1-25.000 (vw_cprm_map_geo_25k).zip | 13 | 13 |
| Mapeamentos 1-250.000 (vw_cprm_map_geo_250k).zip | 25 | 15 |
| Mapeamentos 1-50.000 (vw_cprm_map_geo_50k).zip | 31 | 28 |
| Modelamento 3d (vw_cprm_modelamento_3d).zip | 2 | 2 |
| Ocorrências Fossilíferas (vw_cprm_ocorr_fossi).zip | 142 | 66 |
| Petrografia (vw_cprm_petrogf).zip | 1.888 | 1.024 |
| Plate SIG (vw_cprm_gmsa_plate).zip | 1 | 1 |
| Polígono Atlas Hidrogeológico (vw_cprm_pol_a_hidrog).zip | 656 | 389 |
| Províncias Auríferas (vw_cprm_au_prov_br).zip | 6 | 4 |
| Províncias Estruturais (vw_cprm_provincias_estruturais).zip | 6 | 3 |
| Rimas (vw_cprm_pocos_rima).zip | 45 | 6 |
| Siagas (vw_cprm_pocos_siagas).zip | 10.118 | 6.133 |
| Suture Zones Inset (vw_cprm_tmsa_sutures_zones_inset).zip | 5 | 4 |
| Suture Zones SIG (vw_cprm_tmsa_suture_zones).zip | 7 | 7 |
| Tec Units SIG (vw_cprm_tmsa_tec_units).zip | 194 | 138 |
| Tectonic Units Inset SIG (vw_cprm_tmsa_tec_units_inset).zip | 4 | 3 |

### 4. Energia, combustíveis e transporte

| Arquivo | Registros baixados | Tocam Goiás |
|---|---:|---:|
| Aeroportos (vw_ibge_complex_aero).zip | 8 | 5 |
| Aeródromos (vw_ibge_aerodromo).zip | 95 | 40 |
| Base de Combustíveis Líquidos (vw_epe_base_combust).zip | 21 | 9 |
| Base de Gás Liquefeito de Petróleo (vw_epe_bases_glp).zip | 11 | 5 |
| Biodiesel (vw_epe_plt_biod).zip | 9 | 9 |
| Biogás (vw_epe_plt_met).zip | 2 | 2 |
| Blocos Exploratórios (vw_anp_bloco_expl).zip | 2 | 1 |
| Central Geradora Hidrelétrica (vw_epe_cgh_exist).zip | 15 | 3 |
| Estadual e Distrital (vw_ibge_rdv_est_dist).zip | 3.021 | 1.949 |
| Etanol (vw_epe_plt_et).zip | 73 | 48 |
| Existentes (vw_epe_lin_trans_exist).zip | 156 | 112 |
| Federal (vw_ibge_rdv_fed).zip | 1.418 | 629 |
| Ferrovias (vw_infra_ferrov).zip | 92 | 42 |
| Helipontos (vw_ibge_helipt).zip | 25 | 15 |
| Hidrovias Vias Economicamente Navegáveis - VEN (vw_antaq_ven).zip | 3 | 2 |
| Limite das Bacias Sedimentares (vw_anp_bac_sed).zip | 4 | 3 |
| Municipal (vw_ibge_rdv_mun).zip | 1.767 | 553 |
| Oleodutos (vw_infra_dutovia_oldt).zip | 5 | 4 |
| Outras (vw_ibge_rdv_out).zip | 4.764 | 2.519 |
| Pequena Central Hidrelétrica (vw_epe_pch_exist).zip | 44 | 23 |
| Pista de Pouso (vw_ibge_pista_pouso).zip | 39 | 21 |
| Portos (vw_antaq_inst_portu).zip | 16 | 8 |
| Poços (vw_anp_pocos).zip | 72 | 4 |
| Subestação (vw_epe_sub_exist).zip | 53 | 35 |
| Termelétrica a Biomassa (vw_epe_ute_bio_exist).zip | 44 | 23 |
| Termelétrica a Combustível Fóssil (vw_epe_ute_fos_exist).zip | 5 | 4 |
| Terminais Ferroviários (vw_infra_term_ferrov).zip | 33 | 10 |
| Terminais Portuários (vw_infra_term_portu).zip | 3 | 3 |
| Terminal de Armazenamento e Distribuição de Petróleo e Derivados (vw_epe_term_petro_deri).zip | 5 | 1 |
| Usina Hidrelétrica (vw_epe_uhe_exist).zip | 26 | 16 |

### 5. Territórios e restrições socioambientais

| Arquivo | Registros baixados | Tocam Goiás |
|---|---:|---:|
| Aldeias Indígenas (vw_funai_aldeias).zip | 200 | 3 |
| Cavidades Naturais Subterrâneas (vw_icmbio_cav_nat).zip | 2.048 | 1.051 |
| Projetos de Assentamento Federal (vw_incra_ast_fed).zip | 619 | 403 |
| Projetos de Assentamento Reconhecimento (vw_incra_ast_rec).zip | 1 | 1 |
| Projetos de Assentamento Total (vw_incra_ast).zip | 621 | 405 |
| Proteção Integral (vw_mma_uc_pi).zip | 55 | 25 |
| SIGEF Privado (vw_incra_sigef_prv).zip | 25.241 | 15.459 |
| SIGEF Público (vw_incra_sigef_pbl).zip | 157.747 | 90.682 |
| Sítios Arqueológicos (vw_iphan_sitio_arq).zip | 1.449 | 925 |
| Terras Indígenas (vw_funai_ter_indg).zip | 17 | 7 |
| Uso Sustentável (vw_mma_uc_us).zip | 205 | 139 |
| Áreas de Quilombolas (vw_incra_area_qlb).zip | 13 | 9 |

### 6. IBGE, água, solos e vegetação

| Arquivo | Registros baixados | Tocam Goiás |
|---|---:|---:|
| Amazônia Legal (vw_ibge_amaz_legal).zip | 394 | 298 |
| Bacias Hidrográficas - Nível 1 (vw_ana_bho_ach_lv3).zip | 38 | 21 |
| Bacias Hidrográficas - Nível 2 (vw_ibge_bacia_hidro_2).zip | 3 | 2 |
| Bacias Hidrográficas - Nível 3 (vw_ibge_bacia_hidro_3).zip | 5 | 3 |
| Bacias Hidrográficas - Nível 4 (vw_ibge_bacia_hidro_4).zip | 16 | 8 |
| Bacias Hidrográficas - Nível 5 (vw_ibge_bacia_hidro_5).zip | 92 | 46 |
| Bacias Hidrográficas - Nível 6 (vw_ibge_bacia_hidro_6).zip | 421 | 218 |
| Barragens (vw_ibge_hid_barg).zip | 17 | 3 |
| Base Contínua de Vegetação do Brasil (vw_ibge_veg_br).zip | 16.949 | 9.180 |
| Biomas (vw_ibge_biomas).zip | 3 | 2 |
| Cobertura e Uso do Solo (vw_ibge_cob_uso_ter).zip | 649.839 | 343.083 |
| Com 100 mil a 300 mil Habitantes (vw_ibge_aurb_100a300hab).zip | 75 | 44 |
| Com Mais de 300 mil Habitantes (vw_ibge_aurb_mais300hab).zip | 537 | 301 |
| Densidade Populacional (vw_ibge_dens_pop).zip | 393 | 298 |
| Desenvolvimento Humano (IDH) (vw_ibge_idh).zip | 7 | 7 |
| Faixa de Fronteira (vw_ibge_faixa_front).zip | 394 | 298 |
| Gini (vw_ibge_ind_gini).zip | 7 | 7 |
| Ilhas (vw_ibge_ilhas).zip | 291 | 156 |
| Macrorregiões Hidrográficas (vw_ibge_macro_hidro).zip | 6 | 3 |
| Malha Estadual (vw_ibge_lim_uf).zip | 7 | 7 |
| Malha Municipal (vw_ibge_lim_mun).zip | 394 | 298 |
| MATOPIBA (vw_ibge_matopiba).zip | 394 | 298 |
| Mensal (vw_ibge_valor_rend_nom_med_mensal).zip | 393 | 298 |
| Mensal das Pessoas Maiores de 10 Anos (vw_ibge_valor_rend_nom_med_mensal_10_mais).zip | 393 | 298 |
| Mensal das Pessoas Maiores de 10 Anos Com Rendimento no Trabalho Principal (vw_ibge_valor_rend_nom_med_mensal_10_mais_rend_trab_princ).zip | 392 | 297 |
| Mensal dos Domicílios Particulares Permanentes (vw_ibge_valor_rend_nom_med_mens_mun_par_perm).zip | 393 | 298 |
| Mesorregião Geográfica (vw_ibge_lim_mesor).zip | 394 | 298 |
| Mesorregiões Hidrográficas (vw_ibge_meso_hidro).zip | 9 | 5 |
| Microrregião Geográfica (vw_ibge_lim_micror).zip | 394 | 298 |
| Microrregiões Hidrográficas (vw_ibge_micro_hidro).zip | 29 | 20 |
| Produto Interno Bruto (vw_ibge_pib).zip | 394 | 298 |
| Região Geográfica Imediata (vw_ibge_lim_imed).zip | 394 | 298 |
| Região Geográfica Intermediária (vw_ibge_lim_intermed).zip | 394 | 298 |
| Regiões (vw_ibge_lim_macror).zip | 4 | 4 |
| Rios - Massa D'água (vw_ibge_m_dagua).zip | 3.205 | 1.729 |
| Rios - Trechos (vw_ibge_rios).zip | 95.894 | 53.142 |
| Semiárido (vw_ibge_semiarido).zip | 394 | 298 |
| Solos (vw_embrapa_solos).zip | 259 | 156 |
| Zonas Climáticas (vw_ibge_zon_clim).zip | 27 | 10 |
| Área de Atuação da SUDENE (vw_ibge_sudene).zip | 394 | 298 |
