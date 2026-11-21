# -*- coding: utf-8 -*-
"""Normaliza a chave 'mineral' entre ANM Producao_Bruta/Beneficiada, CFEM, Cadastro Mineiro
e SIGMINE (todos em dados/), faz o cruzamento 1 a 1 (pente fino) e monta a Base 1
(mineral x ano, Goias e Brasil) do prototipo. Salva um JSON intermediario para o
gerador da planilha e imprime o relatorio de cobertura (nada pode ficar sem mapear).
"""
import glob, json, re, struct, sys, unicodedata, zipfile
from collections import Counter, defaultdict
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
from caminhos import BASE, TMP, arquivo  # caminhos relativos ao projeto — ver caminhos.py


def norm(s):
    s = re.sub(r"\s+", " ", str(s)).strip().upper()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s


def read_csv(path, sep=",", encoding="cp1252"):
    return pd.read_csv(path, sep=sep, encoding=encoding, encoding_errors="replace",
                        dtype=str, keep_default_na=False, engine="python", on_bad_lines="skip")


def split_multi(v):
    v = re.sub(r"\s+", " ", str(v)).strip()
    return [x.strip() for x in re.split(r"[,;]", v) if x.strip()]


def read_dbf_bytes(data, encoding="cp1252"):
    n_records = struct.unpack("<I", data[4:8])[0]
    header_len = struct.unpack("<H", data[8:10])[0]
    record_len = struct.unpack("<H", data[10:12])[0]
    fields, pos = [], 32
    while data[pos] != 0x0D:
        desc = data[pos:pos + 32]
        name = desc[:11].split(b"\x00", 1)[0].decode("ascii", "replace")
        fields.append((name, desc[16]))
        pos += 32
    rows, pos = [], header_len
    for _ in range(n_records):
        raw = data[pos:pos + record_len]
        pos += record_len
        if not raw or raw[0:1] == b"*":
            continue
        rpos, row = 1, {}
        for name, length in fields:
            row[name] = raw[rpos:rpos + length].decode(encoding, "replace").strip()
            rpos += length
        rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# 1) Dimensao canonica de minerais (resultado do "pente fino")
#    key -> (mineral_id, nome_padronizado, classe, grupo_pai, categoria_agregada_anm,
#            status_producao_go, observacao)
# ---------------------------------------------------------------------------
#  IMPORTANTE: a 1a passagem deste script revelou que a ANM já publica uma lista OFICIAL de 57
#  categorias de substância (Produção Bruta + Beneficiada, todos os estados) -- ver
#  "ANM_CATEGORY_TO_KEY" abaixo. Adotamos essa lista como espinha do mineral_id (é o padrão
#  que a própria agência usa para publicar t/ano) e corrigimos, à luz dela, 6 decisões da
#  1a passagem: Columbita (não é sinônimo de Nióbio -- a ANM tem categoria própria
#  "Columbita-Tantalita"), Calcedônia (não é "quartzo" -- categoria própria "Geodos, Ágatas,
#  Calcedônia, etc"), Cianita (não é gema -- categoria própria "Cianita e outros minerais
#  refratários"), Diatomita (não é "Argilas" -- categoria própria), Gipsita (categoria própria,
#  só aparece em título de GO, não em produção) e Paládio (funde em "Platina (Grupo da)", que é
#  a nomenclatura oficial do grupo da platina, PGE).
MIN_DEF = {
    "ouro":              ("Ouro", "Metálicos", "", False, "confirmada", ""),
    "cobre":              ("Cobre", "Metálicos", "", False, "confirmada", ""),
    "niquel":             ("Níquel", "Metálicos", "", False, "confirmada", ""),
    "niobio":             ("Nióbio", "Metálicos", "", False, "confirmada", "Inclui PIROCLORO (mineral-minério do nióbio nos carbonatitos de Catalão). COLUMBITA foi retirada daqui: a ANM tem categoria oficial própria 'Columbita-Tantalita' (ver chave columbita_tantalita)."),
    "manganes":           ("Manganês", "Metálicos", "", False, "confirmada", ""),
    "ferro":              ("Ferro", "Metálicos", "", False, "confirmada", "Inclui HEMATITA e LIMONITA (minerais-minério do ferro)."),
    "prata":              ("Prata", "Metálicos", "", False, "confirmada", ""),
    "aluminio_bauxita":   ("Alumínio (Bauxita)", "Metálicos", "", True, "confirmada", "Categoria já composta pelo próprio ANM. Inclui BAUXITA, GIBBSITA e HIDRARGILITA (minerais que compõem a bauxita)."),
    "cobalto":            ("Cobalto", "Metálicos", "", False, "confirmada", ""),
    "estanho":            ("Estanho", "Metálicos", "", False, "confirmada", "Inclui CASSITERITA (mineral-minério do estanho)."),
    "titanio":            ("Titânio", "Metálicos", "", False, "confirmada", "Inclui ILMENITA, RUTILO e ILMENO MAGNETITA (minerais-minério do titânio)."),
    "bario":              ("Bário", "Não-Metálicos", "", False, "confirmada", "Inclui BARITA (mineral-minério do bário)."),
    "fosfato":            ("Fosfato", "Não-Metálicos", "", False, "confirmada", "Inclui APATITA (mineral-minério do fósforo)."),
    "amianto":            ("Amianto", "Não-Metálicos", "", False, "confirmada", "Inclui CRISOTILA (nome mineralógico do amianto) e ANTOFILITA (variedade de amianto anfibólico) — REVISAR: pipeline anterior tratava antofilita como mineral à parte."),
    "calcario":           ("Calcário", "Não-Metálicos", "", False, "confirmada", "Mineral-pai da família calcário (ver grupo)."),
    "calcario_calcitico": ("Calcário Calcítico", "Não-Metálicos", "calcario", False, "confirmada", "Inclui CALCITA. Variante rica em cálcio, mantida como item próprio (não fundida em Calcário) por ter uso econômico distinto (corretivo de solo/cal)."),
    "calcario_dolomitico":("Calcário Dolomítico", "Não-Metálicos", "calcario", False, "confirmada", "AMBÍGUO — revisar: pode ser a mesma coisa reportada como 'Dolomito' na estatística ANM (produção agrícola/industrial), ou um produto distinto dentro da família calcário. Mantido separado de 'Dolomito e Magnesita' até confirmação."),
    "calcario_industrial":("Calcário Industrial", "Não-Metálicos", "calcario", False, "confirmada", ""),
    "dolomito_magnesita": ("Dolomito e Magnesita", "Não-Metálicos", "", True, "confirmada", "Categoria já composta pelo próprio ANM. Só encontramos 'DOLOMITO' nas fontes de título/CFEM — nenhuma ocorrência do termo 'MAGNESITA' em Goiás nas bases atuais; a produção pode ser 100% dolomito. Revisar com metadados ANM."),
    "areia":              ("Areia", "Não-Metálicos", "", False, "confirmada", ""),
    "areias_industriais": ("Areias Industriais", "Não-Metálicos", "", False, "confirmada", "Mapeado a partir de 'AREIA DE FUNDIÇÃO' (areia para moldes de fundição = uso industrial) — revisar se há outros usos industriais de areia agrupados aqui."),
    "argilas":            ("Argilas", "Não-Metálicos", "", True, "confirmada", "Categoria ANM já agregada. Inclui ARGILA, ARGILA REFRATÁRIA, ARGILITO (rocha argilosa) e BENTONITA (argila industrial esmectítica). DIATOMITO foi retirado daqui: a ANM tem categoria oficial própria 'Diatomita'."),
    "cascalho":           ("Rochas (Britadas) e Cascalho", "Não-Metálicos", "", True, "confirmada", "Categoria ANM já agregada. Inclui CASCALHO, BASALTO (a principal rocha usada como brita/agregado no Brasil) e CONGLOMERADO (rocha sedimentar também lavrada como agregado)."),
    "rochas_ornamentais": ("Rochas Ornamentais", "Não-Metálicos", "", True, "confirmada", "Categoria ANM já agregada. Mapeado a partir de GRANITO, GRANITO P/ REVESTIMENTO, MÁRMORE, QUARTZITO, QUARTZITO INDUSTRIAL, SIENITO, GNAISSE, ARDÓSIA — tipos de rocha classicamente usados como pedra ornamental/revestimento. NÃO confirmado linha a linha pelo campo 'Tipo(s) de Uso' do Cadastro Mineiro (próximo passo)."),
    "rochas_ornamentais_outras": ("Rochas Ornamentais - Outras", "Não-Metálicos", "", True, "confirmada", "Categoria OFICIAL da ANM (catch-all para tipos de rocha ornamental não itemizados à parte). Usada aqui para ARENITO, DIORITO, XISTO, MICAXISTO, FILITO, GRANULITO, GRANODIORITO, MONZONITO, GABRO, SERPENTINITO, DIABÁSIO, MIGMATITO, ANFIBOLITO, SILTITO, PIROXENITO, CANGA e MARGA — rochas de título minerário sem uso declarado claramente ornamental nem de brita; revisar com o campo 'Tipo(s) de Uso' do Cadastro Mineiro antes de publicar valores agregados."),
    "rocha_ou_material_nc": ("Material/rocha não classificado (contexto geológico)", "Não-Metálicos", "", False, "revisar", "RESIDUAL DE PROPÓSITO. Agrupa DUNITO (rocha-mãe comum dos depósitos lateríticos de níquel — pode estar relacionado a 'niquel', não confirmado) e LATERITA (termo de perfil de intemperismo, não uma substância comercial específica). Não classificado em nenhuma categoria oficial da ANM."),
    "saibro":             ("Saibro", "Não-Metálicos", "", False, "confirmada", ""),
    "vermiculita_perlita":("Vermiculita e Perlita", "Não-Metálicos", "", True, "confirmada", "Categoria ANM já agregada. Só 'VERMICULITA' encontrado nas fontes de título/CFEM em GO; 'Perlita' não aparece — revisar."),
    "talco_cargas":       ("Talco e outras Cargas Minerais", "Não-Metálicos", "", True, "confirmada", "Categoria ANM já agregada. Inclui TALCO e ESTEATITO (rocha rica em talco)."),
    "caulim":             ("Caulim", "Não-Metálicos", "", False, "confirmada", ""),
    "turfa":              ("Turfa", "Não-Metálicos", "", False, "confirmada", ""),
    "feldspato_grupo":    ("Feldspato, Leucita e Nefelina-Sienito", "Não-Metálicos", "", True, "confirmada", "Categoria ANM já agregada. Só 'FELDSPATO' encontrado nas fontes de título em GO; leucita/nefelina-sienito não aparecem à parte."),
    "quartzo_piezo":      ("Quartzo (Cristal) e outros Piezelétricos", "Não-Metálicos", "", True, "confirmada", "Categoria ANM já agregada. Inclui QUARTZO e QUARTZO INDUSTRIAL. CALCEDÔNIA foi retirada daqui: a ANM tem categoria oficial própria 'Geodos, Ágatas, Calcedônia, etc'."),
    "geodos_agatas_calcedonia": ("Geodos, Ágatas, Calcedônia, etc", "Gemas e Diamantes", "", True, "confirmada", "Categoria OFICIAL da ANM. Mapeada a partir de CALCEDÔNIA (variedade criptocristalina de quartzo, comercializada como geodo/ágata ornamental)."),
    "columbita_tantalita": ("Columbita-Tantalita", "Metálicos", "", True, "confirmada", "Categoria OFICIAL da ANM (mistura de minérios da série columbita-tantalita, Nb+Ta — por isso não é fundida nem em Nióbio nem em Tântalo). Mapeada a partir de COLUMBITA."),
    "cianita_refratarios": ("Cianita e outros minerais refratários", "Não-Metálicos", "", True, "confirmada", "Categoria OFICIAL da ANM. Mapeada a partir de CIANITA — retirada de Gemas porque o uso econômico dominante da cianita é como matéria-prima refratária (alta alumina), não como gema."),
    "diatomita":          ("Diatomita", "Não-Metálicos", "", False, "confirmada", "Categoria OFICIAL da ANM, distinta de Argilas. Mapeada a partir de DIATOMITO."),
    "gipsita":            ("Gipsita", "Não-Metálicos", "", False, "exploracao", "Categoria OFICIAL da ANM. Só aparece em título minerário no Cadastro Mineiro de GO (5 processos) — nenhuma linha de produção (Bruta/Beneficiada) para GO nesta base."),
    "fluorita_criolita":  ("Fluorita e Criolita", "Não-Metálicos", "", True, "confirmada", "Categoria ANM já agregada. Só 'FLUORITA' encontrado em título de GO (Produção Beneficiada); criolita não aparece."),
    "gemas":              ("Gemas", "Gemas e Diamantes", "", True, "confirmada", "Categoria ANM já agregada (exclui diamante, que o ANM reporta à parte). Inclui ESMERALDA, TURMALINA, AMETISTA, BERILO, GRANADA, ZIRCÃO, JADEÍTA, SODALITA, ÁGUA MARINHA (gema berilo-família — NÃO é água) e AGALMATOLITO. BERILO e ZIRCÃO são casos AMBÍGUOS (ver observações em berilio/zirconio) — mantidos aqui por contexto regional (distrito esmeraldífero de Goiás/Santa Terezinha de Goiás), mas podem também representar declaração para uso industrial (berílio/zircônio). CIANITA foi retirada daqui — ver 'cianita_refratarios'."),
    "diamante":           ("Diamante", "Gemas e Diamantes", "", False, "confirmada", "O próprio ANM reporta Diamante separado de Gemas. Inclui DIAMANTE INDUSTRIAL e CASCALHO DIAMANTÍFERO (cascalho associado à extração de diamante)."),
    "monazita_terras_raras": ("Monazita e Terras-Raras", "Metálicos", "", True, "confirmada", "Categoria ANM já agregada. Inclui TERRAS RARAS e MONAZITA. Alto número de títulos/processos em GO (Nova Roma etc.) — ver 04_dim_projetos (Aclara Resources)."),
    # --- exploração / titulos, sem categoria de producao ANM confirmada em GO ---
    "litio":              ("Lítio", "Metálicos", "", False, "exploracao", "NÃO aparece na produção ANM (Bruta/Beneficiada) de GO — apenas títulos minerários. Inclui MINÉRIO DE LÍTIO, ESPODUMÊNIO e LEPIDOLITA (minerais-minério do lítio; espodumênio tem variedade gema 'kunzita', mas o uso dominante declarado aqui é minério)."),
    "zinco":              ("Zinco", "Metálicos", "", False, "exploracao", "Sem produção ANM registrada em GO. Inclui MINÉRIO DE ZINCO."),
    "chumbo":             ("Chumbo", "Metálicos", "", False, "exploracao", "Sem produção ANM registrada em GO. Inclui MINÉRIO DE CHUMBO e GALENA (mineral-minério do chumbo)."),
    "tantalo":            ("Tântalo", "Metálicos", "", False, "exploracao", "Categoria oficial ANM, sem produção registrada em GO (só título). Inclui MINÉRIO DE TÂNTALO e TANTALITA. COLUMBITA NÃO entra aqui — vai para a categoria oficial própria 'Columbita-Tantalita'."),
    "cromo":              ("Cromo", "Metálicos", "", False, "exploracao", "Sem produção ANM registrada em GO. Inclui CROMITA (mineral-minério do cromo) e MINÉRIO DE CROMO."),
    "grafita":            ("Grafita", "Não-Metálicos", "", False, "exploracao", "Sem produção ANM registrada em GO — apenas títulos minerários."),
    "potassio_grupo":     ("Potássio", "Não-Metálicos", "", True, "exploracao", "Categoria OFICIAL da ANM ('Potássio'), sem produção registrada em GO (só título). Agrupa ROCHA POTÁSSICA, SAIS DE POTÁSSIO e NITRATO DE POTÁSSIO — mantidos juntos por afinidade de uso (insumo fertilizante), embora sejam substâncias quimicamente distintas; revisar se merece sub-entradas."),
    "bismuto":            ("Bismuto", "Metálicos", "", False, "exploracao", "NÃO consta nas 57 categorias oficiais da ANM (Bruta/Beneficiada) — registrado apenas como título minerário (1 ocorrência). Inclui MINÉRIO DE BISMUTO."),
    "antimonio":          ("Antimônio", "Metálicos", "", False, "exploracao", "NÃO consta nas 57 categorias oficiais da ANM — registrado apenas como título minerário (1 ocorrência). Inclui MINÉRIO DE ANTIMÔNIO."),
    "berilio":            ("Berílio", "Metálicos", "", False, "exploracao", "Categoria oficial ANM, sem produção registrada em GO (só título: MINÉRIO DE BERÍLIO). Distinto de 'BERILO' (mineral berilo, mapeado em Gemas) — mesma origem mineralógica, contextos de declaração diferentes; revisar se devem ser unificados."),
    "platina":            ("Platina (Grupo da)", "Metálicos", "", True, "exploracao", "Categoria OFICIAL da ANM (grupo do PGE — platina, paládio etc.), sem produção registrada em GO (só título). Inclui MINÉRIO DE PLATINA e MINÉRIO DE PALÁDIO (paládio é elemento do grupo da platina, por isso funde aqui em vez de ganhar entrada própria)."),
    "tungstenio":         ("Tungstênio", "Metálicos", "", False, "exploracao", "Categoria oficial ANM, sem produção registrada em GO (só título). Inclui MINÉRIO DE TUNGSTÊNIO e WOLFRAMITA (mineral-minério do tungstênio)."),
    "magnesio":           ("Magnésio", "Não-Metálicos", "", False, "exploracao", "NÃO consta como categoria própria nas 57 oficiais da ANM (só título: MINÉRIO DE MAGNÉSIO). Pode se relacionar à categoria oficial 'Dolomito e Magnesita' — revisar antes de decidir se funde."),
    "zirconio":           ("Zircônio", "Metálicos", "", False, "exploracao", "Categoria oficial ANM, sem produção registrada em GO (só título: MINÉRIO DE ZIRCÔNIO). AMBÍGUO com 'ZIRCÃO' (mapeado em Gemas) — zircão é o próprio mineral-minério do zircônio; pode ser a mesma substância declarada ora como gema, ora como minério industrial. Revisar antes de unificar."),
    "mica_grupo":         ("Mica", "Não-Metálicos", "", False, "exploracao", "Categoria oficial ANM, sem produção registrada em GO (só título). Inclui MICA e MOSCOVITA (variedade de mica) — distinto de Talco/Esteatito."),
    "sal":                ("Sal", "Não-Metálicos", "", False, "sem_titulo_ou_producao_go", "Categoria oficial da ANM a nível nacional; nenhuma ocorrência (título ou produção) encontrada em Goiás nas bases atuais. Mantida na dimensão para permitir comparação nacional (base Brasil)."),
    "uranio_radioativos": ("Urânio e outros Radioativos", "Metálicos", "", True, "sem_titulo_ou_producao_go", "Categoria oficial nacional; sem ocorrência em GO nas bases atuais."),
    "vanadio":            ("Vanádio", "Metálicos", "", False, "sem_titulo_ou_producao_go", "Categoria oficial nacional; sem ocorrência em GO nas bases atuais."),
    "molibdenio":         ("Molibdênio", "Metálicos", "", False, "sem_titulo_ou_producao_go", "Categoria oficial nacional; sem ocorrência em GO nas bases atuais."),
    "cadmio":             ("Cádmio", "Metálicos", "", False, "sem_titulo_ou_producao_go", "Categoria oficial nacional; sem ocorrência em GO nas bases atuais."),
    "enxofre":            ("Enxofre", "Não-Metálicos", "", False, "sem_titulo_ou_producao_go", "Categoria oficial nacional; sem ocorrência em GO nas bases atuais."),
    "carvao_mineral":     ("Carvão Mineral", "Energéticos", "", False, "sem_titulo_ou_producao_go", "Categoria oficial nacional; sem ocorrência em GO nas bases atuais (compatível com a geologia do estado, sem bacias carboníferas relevantes)."),
    "minerais_industriais_outros": ("Minerais Industriais (Outros)", "Não-Metálicos", "", True, "sem_titulo_ou_producao_go", "Categoria oficial nacional (catch-all); sem ocorrência em GO nas bases atuais."),
    "agua_mineral_grupo": ("Água Mineral", "Não-Metálicos", "", True, "confirmada", "Sistema de dados próprio da ANM (SAD), fora do AMB/RAL — ver dados/ANM/agua_mineral/. Agrupa ÁGUA MINERAL, ÁGUAS TERMAIS, ÁGUA POTÁVEL DE MESA e ÁGUA TERMO MINERAL. NÃO confundir com 'ÁGUA MARINHA' (gema), que foi mantida em Gemas."),
    "laterita_nc":        ("Laterita (perfil de intemperismo, não classificado)", "Não-Metálicos", "", False, "revisar", "Termo genérico de solo/perfil de alteração, não uma substância específica — pode estar associado a níquel, bauxita ou ferro laterítico conforme o contexto local. Mantido isolado até revisão caso a caso do processo."),
}

# raw (normalizado) -> key canonico. Fontes: CFEM, Cadastro Mineiro, SIGMINE (GO).
RAW2KEY = {
    "OURO": "ouro", "MINERIO DE OURO": "ouro",
    "COBRE": "cobre", "MINERIO DE COBRE": "cobre",
    "NIQUEL": "niquel", "MINERIO DE NIQUEL": "niquel", "SILICATOS DE NIQUEL": "niquel",
    "NIOBIO": "niobio", "MINERIO DE NIOBIO": "niobio", "PIROCLORO": "niobio",
    "MANGANES": "manganes", "MINERIO DE MANGANES": "manganes",
    "FERRO": "ferro", "MINERIO DE FERRO": "ferro", "HEMATITA": "ferro", "LIMONITA": "ferro",
    "PRATA": "prata", "MINERIO DE PRATA": "prata",
    "MINERIO DE ALUMINIO": "aluminio_bauxita", "BAUXITA": "aluminio_bauxita", "GIBBSITA": "aluminio_bauxita", "HIDRARGILITA": "aluminio_bauxita",
    "COBALTO": "cobalto", "MINERIO DE COBALTO": "cobalto",
    "ESTANHO": "estanho", "MINERIO DE ESTANHO": "estanho", "CASSITERITA": "estanho",
    "TITANIO": "titanio", "MINERIO DE TITANIO": "titanio", "ILMENITA": "titanio", "RUTILO": "titanio", "ILMENO MAGNETITA": "titanio",
    "BARIO": "bario", "BARITA": "bario",
    "FOSFATO": "fosfato", "APATITA": "fosfato",
    "AMIANTO": "amianto", "CRISOTILA": "amianto", "ANTOFILITA": "amianto",
    "CALCARIO": "calcario",
    "CALCARIO CALCITICO": "calcario_calcitico", "CALCITA": "calcario_calcitico",
    "CALCARIO DOLOMITICO": "calcario_dolomitico",
    "CALCARIO INDUSTRIAL": "calcario_industrial",
    "DOLOMITO": "dolomito_magnesita",
    "AREIA": "areia",
    "AREIA DE FUNDICAO": "areias_industriais",
    "ARGILA": "argilas", "ARGILA REFRATARIA": "argilas", "ARGILA P/CER. VERMELH": "argilas", "ARGILITO": "argilas", "BENTONITA": "argilas",
    "DIATOMITO": "diatomita",
    "CASCALHO": "cascalho", "BASALTO": "cascalho", "CONGLOMERADO": "cascalho",
    "GRANITO": "rochas_ornamentais", "GRANITO P/ REVESTIMENTO": "rochas_ornamentais", "MARMORE": "rochas_ornamentais",
    "QUARTZITO": "rochas_ornamentais", "QUARTZITO INDUSTRIAL": "rochas_ornamentais", "SIENITO": "rochas_ornamentais", "GNAISSE": "rochas_ornamentais", "ARDOSIA": "rochas_ornamentais",
    "ARENITO": "rochas_ornamentais_outras", "DIORITO": "rochas_ornamentais_outras", "XISTO": "rochas_ornamentais_outras", "MICAXISTO": "rochas_ornamentais_outras",
    "FILITO": "rochas_ornamentais_outras", "GRANULITO": "rochas_ornamentais_outras", "GRANODIORITO": "rochas_ornamentais_outras", "MONZONITO": "rochas_ornamentais_outras",
    "GABRO": "rochas_ornamentais_outras", "SERPENTINITO": "rochas_ornamentais_outras", "DIABASIO": "rochas_ornamentais_outras",
    "MIGMATITO": "rochas_ornamentais_outras", "ANFIBOLITO": "rochas_ornamentais_outras", "SILTITO": "rochas_ornamentais_outras", "PIROXENITO": "rochas_ornamentais_outras",
    "CANGA": "rochas_ornamentais_outras", "MARGA": "rochas_ornamentais_outras",
    "DUNITO": "rocha_ou_material_nc",
    "SAIBRO": "saibro",
    "VERMICULITA": "vermiculita_perlita",
    "TALCO": "talco_cargas", "ESTEATITO": "talco_cargas",
    "CAULIM": "caulim",
    "TURFA": "turfa",
    "FELDSPATO": "feldspato_grupo",
    "QUARTZO": "quartzo_piezo", "QUARTZO INDUSTRIAL": "quartzo_piezo", "CALCEDONIA": "geodos_agatas_calcedonia",
    "FLUORITA": "fluorita_criolita",
    "ESMERALDA": "gemas", "TURMALINA": "gemas", "AMETISTA": "gemas", "BERILO": "gemas", "GRANADA": "gemas",
    "ZIRCAO": "gemas", "JADEITA": "gemas", "SODALITA": "gemas", "AGUA MARINHA": "gemas", "AGALMATOLITO": "gemas",
    "CIANITA": "cianita_refratarios",
    "DIAMANTE": "diamante", "DIAMANTE INDUSTRIAL": "diamante", "CASCALHO DIAMANTIFERO": "diamante",
    "TERRAS RARAS": "monazita_terras_raras", "MONAZITA": "monazita_terras_raras",
    "MINERIO DE LITIO": "litio", "ESPODUMENIO": "litio", "LEPIDOLITA": "litio",
    "ZINCO": "zinco", "MINERIO DE ZINCO": "zinco",
    "MINERIO DE CHUMBO": "chumbo", "GALENA": "chumbo",
    "TANTALO": "tantalo", "MINERIO DE TANTALO": "tantalo", "TANTALITA": "tantalo",
    "COLUMBITA": "columbita_tantalita",
    "CROMITA": "cromo", "MINERIO DE CROMO": "cromo",
    "GRAFITA": "grafita",
    "ROCHA POTASSICA": "potassio_grupo", "SAIS DE POTASSIO": "potassio_grupo", "NITRATO DE POTASSIO": "potassio_grupo",
    "MINERIO DE BISMUTO": "bismuto",
    "MINERIO DE ANTIMONIO": "antimonio",
    "MINERIO DE BERILIO": "berilio",
    "MINERIO DE PALADIO": "platina",
    "MINERIO DE PLATINA": "platina",
    "GIPSITA": "gipsita",
    "MINERIO DE TUNGSTENIO": "tungstenio", "WOLFRAMITA": "tungstenio",
    "MINERIO DE MAGNESIO": "magnesio",
    "MINERIO DE ZIRCONIO": "zirconio",
    "MICA": "mica_grupo", "MOSCOVITA": "mica_grupo",
    "AGUA MINERAL": "agua_mineral_grupo", "AGUAS TERMAIS": "agua_mineral_grupo", "AGUA POTAVEL DE MESA": "agua_mineral_grupo", "AGUA TERMO MINERAL": "agua_mineral_grupo",
    "LATERITA": "laterita_nc",
    "DADO NAO CADASTRADO": None,  # sem substancia informada -- nao e um mineral
    "NAO SE APLICA": None,
}

# ANM (Producao_Bruta/Beneficiada) ja usa o nome padronizado como categoria -- mapeamento direto por nome exibido.
ANM_CATEGORY_TO_KEY = {
    "Ouro": "ouro", "Cobre": "cobre", "Níquel": "niquel", "Nióbio": "niobio", "Manganês": "manganes",
    "Ferro": "ferro", "Prata": "prata", "Alumínio (Bauxita)": "aluminio_bauxita", "Cobalto": "cobalto",
    "Estanho": "estanho", "Titânio": "titanio", "Bário": "bario", "Fosfato": "fosfato", "Amianto": "amianto",
    "Calcário": "calcario", "Dolomito e Magnesita": "dolomito_magnesita", "Areia": "areia",
    "Areias Industriais": "areias_industriais", "Argilas": "argilas", "Rochas (Britadas) e Cascalho": "cascalho",
    "Rochas Ornamentais": "rochas_ornamentais", "Rochas Ornamentais - Outras": "rochas_ornamentais_outras",
    "Saibro": "saibro", "Vermiculita e Perlita": "vermiculita_perlita", "Talco e outras Cargas Minerais": "talco_cargas",
    "Caulim": "caulim", "Turfa": "turfa", "Feldspato, Leucita e Nefelina-Sienito": "feldspato_grupo",
    "Quartzo (Cristal) e outros Piezelétricos": "quartzo_piezo", "Fluorita e Criolita": "fluorita_criolita",
    "Gemas": "gemas", "Diamante": "diamante", "Monazita e Terras-Raras": "monazita_terras_raras",
    "Columbita-Tantalita": "columbita_tantalita", "Zircônio": "zirconio", "Gipsita": "gipsita", "Cromo": "cromo",
    "Diatomita": "diatomita", "Geodos, Ágatas, Calcedônia, etc": "geodos_agatas_calcedonia", "Grafita": "grafita",
    "Urânio e outros Radioativos": "uranio_radioativos", "Mica": "mica_grupo", "Cádmio": "cadmio", "Chumbo": "chumbo",
    "Enxofre": "enxofre", "Zinco": "zinco", "Cianita e outros minerais refratários": "cianita_refratarios",
    "Potássio": "potassio_grupo", "Lítio": "litio", "Tungstênio": "tungstenio", "Carvão Mineral": "carvao_mineral",
    "Minerais Industriais (Outros)": "minerais_industriais_outros", "Berílio": "berilio", "Vanádio": "vanadio",
    "Molibdênio": "molibdenio", "Platina (Grupo da)": "platina", "Sal": "sal",
}

print("Definições carregadas:", len(MIN_DEF), "minerais canônicos;", len(RAW2KEY), "sinônimos brutos mapeados.")

# ---------------------------------------------------------------------------
# 1b) Rochas: a categoria da ANM depende do USO, nao so do tipo de rocha (v7)
# ---------------------------------------------------------------------------
# O mesmo granito e 'Rochas (Britadas) e Cascalho' quando e brita e 'Rochas Ornamentais' quando e revestimento.
# Para as substancias de ROCHA_KEYS a chave do mapeamento passa a ser (substancia, tipo de uso). O uso vem:
#  - do Cadastro Mineiro: 'Tipo(s) de Uso', alinhado posicao a posicao com 'Substancia(s)' (20.360 de 20.360 linhas de GO);
#  - do SIGMINE: campo USO (um por poligono);
#  - na CFEM, que nao tem uso: pelo numero do processo -> Cadastro Mineiro, depois SIGMINE;
#  - uso nao informativo ('Demais substancias' etc.): o uso mais frequente da rocha nos titulos e poligonos de GO.
# Validado contra o AMB antes de implementar: Rochas Ornamentais saiu de 35-191x para 0,5-1,3x; Britadas de 0,26x para 0,6-1,1x.
ROCHA_KEYS = {"rochas_ornamentais", "rochas_ornamentais_outras", "cascalho", "rocha_ou_material_nc"}
ROCHAS_ORNAMENTAIS_PRINCIPAIS = {"GRANITO", "GRANITO P/ REVESTIMENTO", "MARMORE", "QUARTZITO", "QUARTZITO INDUSTRIAL",
                                 "GNAISSE", "SIENITO", "ARDOSIA"}
USO_NAO_INFORMATIVO = {"", "DEMAIS SUBSTANCIAS", "DADO NAO CADASTRADO", "NAO SE APLICA", "ENGARRAFAMENTO",
                       "BALNEOTERAPIA", "OURIVESARIA", "ENERGETICO"}
USO_INDUSTRIAL = {"INDUSTRIAL", "FABRICACAO DE CIMENTO", "FABRICACAO DE CAL", "CORRETIVO DE SOLO", "FERTILIZANTES",
                  "INSUMO AGRICOLA", "METALURGIA", "ABRASIVO"}


def norm_uso(u):
    """Normaliza o tipo de uso (o SIGMINE grafa 'Artesanato  mineral' com espaco duplo)."""
    return re.sub(r"\s+", " ", norm(u)).strip()


def eh_rocha(raw):
    return RAW2KEY.get(norm(raw)) in ROCHA_KEYS


def categoria_rocha_por_uso(rocha_norm, uso_norm):
    """Chave (MIN_DEF) da categoria ANM para a rocha nesse uso; None se o uso nao for informativo."""
    u = uso_norm
    if rocha_norm == "CASCALHO":
        return "cascalho"  # o proprio nome da categoria ANM
    if u in USO_NAO_INFORMATIVO:
        return None
    if u in ("BRITA", "CONSTRUCAO CIVIL"):
        return "cascalho"
    if u == "REVESTIMENTO":
        return "rochas_ornamentais" if rocha_norm in ROCHAS_ORNAMENTAIS_PRINCIPAIS else "rochas_ornamentais_outras"
    if u in ("PEDRA DE TALHE", "PEDRA DECORATIVA", "ARTESANATO MINERAL", "PEDRA DE COLECAO"):
        return "rochas_ornamentais_outras"
    if rocha_norm == "MARMORE" and u in ("FABRICACAO DE CAL", "FABRICACAO DE CIMENTO", "CORRETIVO DE SOLO"):
        return "calcario"  # carbonato de calcio usado como calcario
    if rocha_norm == "SIENITO" and u == "INDUSTRIAL":
        return "feldspato_grupo"  # categoria oficial 'Feldspato, Leucita e Nefelina-Sienito'
    if u == "CERAMICA VERMELHA":
        return "argilas"
    if u == "GEMA":
        return "gemas"
    if u in USO_INDUSTRIAL:
        return "minerais_industriais_outros"  # catch-all oficial; sem contraparte no AMB de GO para validar
    return None


def mineral_key_com_uso(raw, uso=None, uso_padrao_rocha=None):
    """(chave do mineral, regra). Nao-rocha: igual ao RAW2KEY. Rocha: decide pelo uso, depois pelo uso majoritario."""
    sn = norm(raw)
    k = RAW2KEY.get(sn)
    if k not in ROCHA_KEYS:
        return k, "substancia"
    cat = categoria_rocha_por_uso(sn, norm_uso(uso)) if uso is not None else None
    if cat:
        return cat, ("rocha_fixa" if sn == "CASCALHO" else "uso_declarado")
    padrao = (uso_padrao_rocha or {}).get(sn)
    cat = categoria_rocha_por_uso(sn, padrao) if padrao else None
    if cat:
        return cat, "uso_majoritario_da_rocha_em_GO"
    return k, "sem_uso_informativo_mapeamento_por_tipo_de_rocha"


def canon_proc(p, ano=""):
    """Numero de processo canonico '<numero sem zeros a esquerda>/<ano>' (mesmo formato da Base 3)."""
    p = str(p).strip()

    def dig(x):
        return re.sub(r"\D", "", str(x))

    if "/" in p:
        esq, dir_ = p.split("/", 1)
        return (dig(esq).lstrip("0") or "0") + "/" + dig(dir_)[:4]
    a = dig(ano)[:4]
    return (dig(p).lstrip("0") or "0") + ("/" + a if a else "")

# ---------------------------------------------------------------------------
# 2) Carregar as fontes
# ---------------------------------------------------------------------------
pb = read_csv(arquivo("dados/ANM/producao_amb_ral/Producao_Bruta.csv"))
pf = read_csv(arquivo("dados/ANM/producao_amb_ral/Producao_Beneficiada.csv"))
cfem = read_csv(arquivo("dados/ANM/cfem/CFEM_Arrecadacao_2022_2026_GO.csv"), sep=";")

# Dimensao canonica de municipios de Goias (malha IBGE 2025) -- necessaria para filtrar
# corretamente o Cadastro Mineiro, que e um arquivo NACIONAL.
with zipfile.ZipFile(arquivo("dados/IBGE/GO_Municipios_2025.zip")) as z:
    _dbf = z.read([n for n in z.namelist() if n.lower().endswith(".dbf")][0])
    GO_MUN_BY_NORM = {norm(r["NM_MUN"]): r["CD_MUN"] for r in read_dbf_bytes(_dbf, "utf-8")}


def go_municipio_id(token):
    """Codigo IBGE se o token e um municipio de Goias; None caso contrario.

    CORRECAO (v2): a versao anterior deste filtro tinha dois defeitos:
      (a) testava se a STRING INTEIRA de 'Municipio(s)' terminava em '- GO'. Como o campo e
          multivalorado, isso perdia processos de divisa em que Goias nao e o ultimo item
          (ex.: 'CACHOEIRA DOURADA - GO, CACHOEIRA DOURADA - MG');
      (b) aceitava a linha quando a Superintendencia regional da ANM era a de Goias, o que
          deixava entrar processos inteiramente em outros estados (a jurisdicao administrativa
          nao segue a fronteira estadual).
    Alem disso, NAO basta remover qualquer sufixo '- UF' e casar pelo nome: 24 municipios de
    outros estados sao homonimos de municipios goianos (MUNDO NOVO - MS, SANTA ISABEL - SP,
    CACHOEIRA DOURADA - MG, BARRO ALTO - BA, ...). Por isso, se houver sufixo de UF e ele nao
    for 'GO', o token e rejeitado sem tentar casar pelo nome.
    """
    t = str(token).strip()
    m = re.search(r"-\s*([A-Za-z]{2})\s*$", t)
    if m:
        if m.group(1).upper() != "GO":
            return None
        t = t[:m.start()].strip()
    return GO_MUN_BY_NORM.get(norm(t))


cad_rows = []  # (raw_subst, processo, titular, cpf_cnpj, tipo_de_uso)
cad_linhas_go = 0
cad_desalinhadas = 0
cad_sem_coluna_uso = []  # arquivos do Cadastro sem 'Tipo(s) de Uso'
uso_proc_subst = defaultdict(Counter)  # (processo canonico, rocha) -> usos informativos (arquivo nacional)
uso_proc_rocha = defaultdict(Counter)  # processo canonico -> usos informativos de qualquer rocha do processo
uso_rocha_go = defaultdict(Counter)    # rocha -> usos informativos nos titulos (Cadastro) e poligonos (SIGMINE) de GO
rochas_audit = defaultdict(lambda: dict(contagem=0, valor_recolhido_brl=0.0, cfem_t=0.0))  # aba 01c
for path in sorted(glob.glob(arquivo("dados/ANM/cadastro_mineiro/*.csv"))):
    df = read_csv(path)
    subcol = next((c for c in df.columns if "ubst" in c), None)
    muncol = next((c for c in df.columns if "unicipio" in c.lower()), None)
    proccol = next((c for c in df.columns if c.strip() == "Processo"), None)
    titcol = next((c for c in df.columns if c.strip() == "Titular"), None)
    doccol = next((c for c in df.columns if "CPF/CNPJ" in c), None)
    usocol = next((c for c in df.columns if "Uso" in c), None)
    if not usocol:
        cad_sem_coluna_uso.append(path.replace("\\", "/").rsplit("/", 1)[-1])  # Guia_de_Utilizacao_Autorizada nao tem 'Tipo(s) de Uso'
    for _, r in df.iterrows():
        subs = split_multi(r.get(subcol, ""))
        usos = split_multi(r.get(usocol, "")) if usocol else [""] * len(subs)
        if len(usos) != len(subs):  # alinhamento posicional: 0 linhas de GO desalinhadas; 5 no resto do Brasil
            usos = [""] * len(subs)
            cad_desalinhadas += 1
        cp = canon_proc(r.get(proccol, ""))
        for s, u in zip(subs, usos):
            if eh_rocha(s) and norm_uso(u) not in USO_NAO_INFORMATIVO:
                uso_proc_subst[(cp, norm(s))][norm_uso(u)] += 1
                uso_proc_rocha[cp][norm_uso(u)] += 1
        # a linha e de Goias se QUALQUER municipio do campo multivalorado for goiano
        if not any(go_municipio_id(t) for t in split_multi(r.get(muncol, ""))):
            continue
        cad_linhas_go += 1
        for s, u in zip(subs, usos):
            cad_rows.append((s, r.get(proccol, ""), r.get(titcol, ""), r.get(doccol, ""), u))
            if eh_rocha(s) and norm_uso(u) not in USO_NAO_INFORMATIVO:
                uso_rocha_go[norm(s)][norm_uso(u)] += 1

with zipfile.ZipFile(arquivo("dados/ANM/sigmine/GO.zip")) as z:
    dbf = z.read("GO.dbf")
    sig_rows = read_dbf_bytes(dbf, "utf-8")

uso_sig_proc_subst = defaultdict(Counter)
for r in sig_rows:
    for s in re.split(r"[,;]", r.get("SUBS", "")):
        s = s.strip()
        if s and eh_rocha(s) and norm_uso(r.get("USO", "")) not in USO_NAO_INFORMATIVO:
            uso_sig_proc_subst[(canon_proc(r.get("PROCESSO", "")), norm(s))][norm_uso(r.get("USO", ""))] += 1
            uso_rocha_go[norm(s)][norm_uso(r.get("USO", ""))] += 1
USO_PADRAO_ROCHA = {rocha: c.most_common(1)[0][0] for rocha, c in uso_rocha_go.items() if c}
print(f"Rochas: uso majoritário em GO para {len(USO_PADRAO_ROCHA)} tipos; linhas do Cadastro (Brasil) com substância×uso desalinhados: {cad_desalinhadas}; "
      f"arquivos sem coluna de uso (uso tratado como não informativo): {cad_sem_coluna_uso}")


def uso_do_processo(proc_canon, rocha_norm):
    """Tipo de uso de uma rocha num processo, para a fonte que nao tem campo de uso (CFEM)."""
    if (proc_canon, rocha_norm) in uso_proc_subst:
        return uso_proc_subst[(proc_canon, rocha_norm)].most_common(1)[0][0], "Cadastro Mineiro (processo + substância)"
    if (proc_canon, rocha_norm) in uso_sig_proc_subst:
        return uso_sig_proc_subst[(proc_canon, rocha_norm)].most_common(1)[0][0], "SIGMINE (processo + substância)"
    if proc_canon in uso_proc_rocha:
        return uso_proc_rocha[proc_canon].most_common(1)[0][0], "Cadastro Mineiro (outra rocha do mesmo processo)"
    return None, "sem uso no processo"

print(f"Carregado: PB={len(pb)} linhas, PF={len(pf)} linhas, CFEM={len(cfem)} linhas, "
      f"Cadastro(GO)={len(cad_rows)} substância-linhas, SIGMINE(GO)={len(sig_rows)} processos.")

# ---------------------------------------------------------------------------
# 3) Verificacao de cobertura -- pente fino: nada pode ficar sem mapear
# ---------------------------------------------------------------------------
crosswalk = []  # linhas para a aba de auditoria da planilha
problemas = []


def check_source(nome_fonte, valores_com_contagem, use_anm_categories=False):
    lookup = ANM_CATEGORY_TO_KEY if use_anm_categories else None
    for raw, contagem in valores_com_contagem.items():
        key_norm = norm(raw)
        if use_anm_categories:
            mapped = ANM_CATEGORY_TO_KEY.get(raw, "___MISSING___")
        else:
            mapped = RAW2KEY.get(key_norm, "___MISSING___")
        if mapped == "___MISSING___":
            problemas.append((nome_fonte, raw, contagem))
            mineral_id_final, tipo = "SEM_MAPEAMENTO", "sem_correspondencia"
        elif mapped is None:
            mineral_id_final, tipo = "(excluído — não é substância)", "excluido_nao_mineral"
        else:
            nome_pad = MIN_DEF[mapped][0]
            tipo = "identico" if norm(nome_pad) == key_norm else (
                "fusao_minerio_forma_pura" if key_norm.startswith("MINERIO DE") or norm(nome_pad).replace(" ", "") in key_norm.replace(" ", "")
                else "fusao_mineralogica_ou_grupo")
            mineral_id_final = nome_pad
            if mapped in ROCHA_KEYS and not use_anm_categories:
                tipo = "rocha_categoria_pelo_tipo_de_uso_ver_01c"  # nome_pad e so a categoria sem uso informativo
        crosswalk.append(dict(fonte=nome_fonte, valor_original=raw, valor_normalizado=key_norm,
                               contagem=contagem, mineral_atribuido=mineral_id_final, tipo_correspondencia=tipo))


check_source("ANM_Producao_Bruta(GO)", pb.loc[pb.UF == "GO", "Substância Mineral"].value_counts().to_dict(), use_anm_categories=True)
check_source("ANM_Producao_Beneficiada(GO)", pf.loc[pf.UF == "GO", "Substância Mineral"].value_counts().to_dict(), use_anm_categories=True)
check_source("CFEM(GO)", cfem["Substância"].value_counts().to_dict())
check_source("Cadastro_Mineiro(GO)", Counter(r[0] for r in cad_rows))
sig_subs = Counter()
for r in sig_rows:
    for s in re.split(r"[,;]", r.get("SUBS", "")):
        s = s.strip()
        if s:
            sig_subs[s] += 1
check_source("SIGMINE(GO)", sig_subs)

# as 2 fontes ANM usam o proprio nome da categoria -- confirmar que bate com ANM_CATEGORY_TO_KEY tambem
for raw in list(pb["Substância Mineral"].unique()) + list(pf["Substância Mineral"].unique()):
    if raw not in ANM_CATEGORY_TO_KEY:
        problemas.append(("ANM_categoria_nao_mapeada", raw, "-"))

print(f"\n=== VERIFICAÇÃO DE COBERTURA ===")
print(f"Linhas de crosswalk geradas: {len(crosswalk)}")
if problemas:
    print(f"!!! {len(problemas)} valores SEM correspondência encontrada (revisar manualmente):")
    for p in problemas:
        print("   ", p)
else:
    print("Nenhum valor ficou sem correspondência -- cobertura de 100% confirmada nas 5 fontes verificadas.")

with open(f"{TMP}/_crosswalk.json", "w", encoding="utf-8") as f:
    json.dump(crosswalk, f, ensure_ascii=False)
print("crosswalk salvo:", len(crosswalk), "linhas")

# ---------------------------------------------------------------------------
# 4) Cruzamento real -- Base 1 (mineral x ano, GO e BR)
# ---------------------------------------------------------------------------

def key_of_anm(raw):
    return ANM_CATEGORY_TO_KEY[raw]


def key_of_raw(raw):
    return RAW2KEY.get(norm(raw))


def to_num(s):
    s = str(s).strip()
    if not s or s in {"-", ",00"}:
        return None
    s = s.replace(".", "").replace(",", ".") if "," in s else s
    try:
        return float(s)
    except ValueError:
        return None


# --- producao (GO e BR) a partir de PB/PF ---
prod = defaultdict(lambda: defaultdict(lambda: defaultdict(float)))  # prod[uf][(key,ano)][campo] = soma
qtd_col_pb = "Quantidade Produção - Minério ROM (t)"
for _, r in pb.iterrows():
    k = key_of_anm(r["Substância Mineral"]); ano = int(r["Ano base"]); v = to_num(r[qtd_col_pb])
    if v is None:
        continue
    for uf in (r["UF"], "BR"):
        prod[uf][(k, ano)]["rom_t"] += v

for _, r in pf.iterrows():
    k = key_of_anm(r["Substância Mineral"]); ano = int(r["Ano base"]); v = to_num(r["Quantidade Produção"])
    unidade = r["Unidade de Medida - Produção"].strip()
    if v is None:
        continue
    for uf in (r["UF"], "BR"):
        prod[uf][(k, ano)]["beneficiada"] += v
        prod[uf][(k, ano)]["beneficiada_unidade"] = unidade

# valor de venda (beneficiada) -- soma tambem, e mesma unidade de origem (R$)
for _, r in pf.iterrows():
    k = key_of_anm(r["Substância Mineral"]); ano = int(r["Ano base"]); v = to_num(r["Valor Venda (R$)"])
    if v is None:
        continue
    for uf in (r["UF"], "BR"):
        prod[uf][(k, ano)]["valor_venda_benef_brl"] += v

# contido da produção beneficiada (v18) -- só unidades de massa, convertidas para t como na 08 (unidade '-' não é medida);
# é a série a usar nos minerais de regras_series.SERIE_BENEF_POR_CONTIDO (nióbio: a quantidade mudou de conceito em 2024)
_PARA_T_CONTIDO = {"t": 1.0, "kg": 1e-3, "g": 1e-6, "ct": 2e-7}  # o mesmo PARA_T da CFEM e da 08
contido_ind = defaultdict(set)  # (uf, key, ano) -> indicações do contido
for _, r in pf.iterrows():
    k = key_of_anm(r["Substância Mineral"]); ano = int(r["Ano base"]); v = to_num(r["Quantidade Contido"])
    un = str(r["Unidade de Medida - Contido"]).strip().lower()
    if v is None or un not in _PARA_T_CONTIDO:
        continue
    ind = str(r.get("Indicação Contido", "")).strip()
    for uf in (r["UF"], "BR"):
        prod[uf][(k, ano)]["contido_benef_t"] += v * _PARA_T_CONTIDO[un]
        if ind:
            contido_ind[(uf, k, ano)].add(ind)

# --- CFEM (GO apenas) ---
cfem["_ano"] = pd.to_numeric(cfem["Ano"], errors="coerce")
cfem_agg = defaultdict(lambda: defaultdict(float))  # cfem_agg[(key,ano)][campo]
cfem_titulares = defaultdict(set)  # (key) -> set(cpf_cnpj)
cfem_outras = defaultdict(lambda: defaultdict(float))  # (key,ano) -> unidade que nao e massa -> quantidade
cfem_excl = Counter()  # (key,ano) -> linhas cuja quantidade saiu da soma
cfem_qtd_excluidas = []  # auditoria linha a linha (aba 09b)

# CORRECAO (v6): a quantidade comercializada era somada sem olhar a unidade (t, kg, g, ct, m3, l e m2 aparecem no
# mesmo mineral) e sem filtrar valores corrompidos -- Calcario chegava a 3,35 TRILHOES de t em 2022-2026.
# O grosso do dado e bom (Calcario 2022: CFEM 14,9 Mt x AMB 15,3 Mt), mas poucas linhas destroem a soma:
#  (a) quantidades em notacao cientifica ('7,23824E+12'): a mesma corrupcao de exportacao do CPF_CNPJ;
#  (b) quantidades infladas em milhares de vezes (ex.: 9.226.138.104 t de calcario pagando R$ 54 mil).
# Regra: massa convertida para t; m3, l e m2 ficam fora da soma em t (sem densidade nao ha conversao).
# A linha sai da soma de QUANTIDADE -- nunca do valor em R$ -- se (a), ou se o R$ por unidade for mais de
# 1.000x menor que a mediana do mesmo mineral e unidade. Cada exclusao vai para a aba de auditoria 09b.
PARA_T = {"t": 1.0, "kg": 1e-3, "g": 1e-6, "ct": 2e-7}
_linhas_cfem = []
for _idx, r in cfem.iterrows():
    # rochas: a categoria depende do uso, que a CFEM nao tem -> vem do processo (Cadastro Mineiro / SIGMINE)
    _pc = canon_proc(r["Processo"], r["AnoDoProcesso"])
    uso_l, origem_uso = uso_do_processo(_pc, norm(r["Substância"])) if eh_rocha(r["Substância"]) else (None, "")
    k, regra_l = mineral_key_com_uso(r["Substância"], uso_l, USO_PADRAO_ROCHA)
    if k is None or pd.isna(r["_ano"]):
        continue
    ano = int(r["_ano"])
    v_val = to_num(r["ValorRecolhido"])
    if v_val is not None:
        cfem_agg[(k, ano)]["cfem_recolhido_brl"] += v_val
    doc = re.sub(r"\D", "", str(r["CPF_CNPJ"]))
    if doc:
        cfem_titulares[k].add(doc)
    bruto = str(r["QuantidadeComercializada"]).strip()
    un = str(r["UnidadeDeMedida"]).strip().lower()
    cientifica = bool(re.search(r"[eE][+-]?\d+$", bruto))
    v_qt = None if cientifica else to_num(bruto)
    massa = un in PARA_T
    conv = None if v_qt is None else (v_qt * PARA_T[un] if massa else v_qt)
    _linhas_cfem.append(dict(idx=int(_idx), k=k, ano=ano, mes=r["Mês"], processo=r["Processo"], ano_proc=r["AnoDoProcesso"],
                             subst=r["Substância"], un=un, massa=massa, bruto=bruto, conv=conv, valor=v_val, cientifica=cientifica,
                             proc_canon=_pc, uso=uso_l, origem_uso=origem_uso, regra=regra_l))

_rpu = defaultdict(list)  # (mineral, unidade padronizada) -> R$ por unidade das linhas validas
for l in _linhas_cfem:
    if not l["cientifica"] and l["conv"] and l["conv"] > 0 and l["valor"] and l["valor"] > 0:
        _rpu[(l["k"], "t" if l["massa"] else l["un"])].append(l["valor"] / l["conv"])
_mediana = {g: float(pd.Series(v).median()) for g, v in _rpu.items() if len(v) >= 5}

for l in _linhas_cfem:
    grupo = (l["k"], "t" if l["massa"] else l["un"])
    motivo = ""
    if l["cientifica"]:
        motivo = "quantidade em notação científica (valor corrompido na exportação)"
    elif l["conv"] and l["conv"] > 0 and l["valor"] and l["valor"] > 0 and grupo in _mediana \
            and l["valor"] / l["conv"] < _mediana[grupo] / 1000:
        motivo = "quantidade implausível: R$ por unidade mais de 1.000× abaixo da mediana do mesmo mineral e unidade"
    l["excluida"], l["motivo"] = bool(motivo), motivo
    if motivo:
        cfem_excl[(l["k"], l["ano"])] += 1
        cfem_qtd_excluidas.append(dict(
            mineral_key=l["k"], year=l["ano"], month=int(l["mes"]), processo_anm=f"{l['processo']}/{l['ano_proc']}",
            substancia_original=l["subst"], unidade_original=l["un"], quantidade_bruta=l["bruto"], quantidade_convertida=l["conv"],
            unidade_convertida=grupo[1], valor_recolhido_brl=l["valor"],
            r_por_unidade=(l["valor"] / l["conv"]) if (l["conv"] and l["valor"]) else None,
            mediana_r_por_unidade_mineral=_mediana.get(grupo), motivo=motivo))
        continue
    if l["conv"] is None:
        continue
    if l["massa"]:
        cfem_agg[(l["k"], l["ano"])]["cfem_qtd_comercializada_t"] += l["conv"]
    else:
        cfem_outras[(l["k"], l["ano"])][l["un"]] += l["conv"]
print(f"CFEM quantidade: {len(cfem_qtd_excluidas)} linhas excluídas da soma de quantidade (valores em R$ mantidos).")

# alertas (aba 09c): UM processo com quantidade declarada na CFEM implausivel frente ao AMB do estado inteiro na categoria.
# NAO exclui da soma (o AMB tambem e declaratorio) -- sinaliza para revisao da declaracao ou do tipo de uso.
# CORRECAO (v14): o limite era o maior entre producao bruta e beneficiada, e a beneficiada so entrava se estivesse em t. No ouro o
# AMB mede a bruta em toneladas de MINERIO (22-31 Mt/ano em GO) e a beneficiada em kg de METAL (3-5 t/ano), enquanto a CFEM declara
# metal (kg/g): o limite virava o minerio e nenhum processo de ouro era sinalizado; na prata (sem bruta) nao havia limite nenhum.
# Para minerais cuja beneficiada o AMB mede em kg/g, o limite passa a ser a beneficiada convertida para t. O contido do AMB nao
# serve de limite: oscila demais (ouro contido no ROM de 2022 = 2.799 t, erro na fonte). E, como o preco do metal e bem definido,
# nesses minerais o alerta tambem dispara quando o R$/t do processo fica mais de 10x abaixo da mediana do mineral, mesmo abaixo do
# total estadual -- e o caso de minerio declarado como ouro (860567/2021: 3,2 t em 2025 com R$ 287 mil). A mediana desses metais e
# PONDERADA PELO R$ RECOLHIDO: a mediana por linha ficava puxada pelas proprias declaracoes erradas (o 860567/2021 tem dezenas de
# linhas por ano) e caia para R$ 177 mil/t no ouro, contra R$ 6,4 mi/t ponderada -- com ela o minerio declarado como ouro escapava.
# Metal = beneficiada em kg/g no AMB de GO em pelo menos 3 anos e na maior parte dos anos com producao (ouro e prata: 16 de 16;
# gemas e estanho tem um unico ano em kg, e o preco por peso das gemas varia demais para servir de referencia).
_anos_benef, _anos_kg = Counter(), Counter()
for (_k, _a), _pg in prod["GO"].items():
    if (_pg.get("beneficiada") or 0) > 0:
        _anos_benef[_k] += 1
        _anos_kg[_k] += str(_pg.get("beneficiada_unidade", "")).strip().lower() in ("kg", "g")
METAL_KG = {k for k, n in _anos_kg.items() if n >= 3 and 2 * n >= _anos_benef[k]}


def _mediana_ponderada(pares):
    """pares (valor, peso): o valor em que o peso acumulado passa da metade do total."""
    pares = sorted(pares)
    total, acumulado = sum(p for _, p in pares), 0.0
    for v, p in pares:
        acumulado += p
        if acumulado >= total / 2:
            return v


_rpt_metal = defaultdict(list)
for l in _linhas_cfem:
    if l["k"] in METAL_KG and not l.get("excluida") and l["massa"] and l["conv"] and l["conv"] > 0 and l["valor"] and l["valor"] > 0:
        _rpt_metal[l["k"]].append((l["valor"] / l["conv"], l["valor"]))
_mediana_metal = {k: _mediana_ponderada(v) for k, v in _rpt_metal.items() if len(v) >= 5}
_t_proc, _rs_proc = defaultdict(float), defaultdict(float)
_subs_proc, _usos_proc = defaultdict(set), defaultdict(set)
for l in _linhas_cfem:
    if l.get("excluida") or not l["massa"] or not l["conv"]:
        continue
    g = (l["k"], l["ano"], l["proc_canon"])
    _t_proc[g] += l["conv"]
    _rs_proc[g] += l["valor"] or 0.0
    _subs_proc[g].add(str(l["subst"]).strip())
    if l.get("uso"):
        _usos_proc[g].add(l["uso"])
cfem_alertas_processo = []
for (k, ano, p), t in _t_proc.items():
    pg = prod["GO"].get((k, ano), {})
    un_b = str(pg.get("beneficiada_unidade", "")).strip().lower()
    metal = k in METAL_KG
    if metal:  # limite = metal beneficiado (a bruta e minerio)
        total = (pg.get("beneficiada") or 0.0) * PARA_T[un_b] if un_b in ("kg", "g") else 0.0
        base = "beneficiada do AMB em kg (metal), convertida para t"
    else:
        benef_t = pg.get("beneficiada") if un_b == "t" else None
        total = max([v for v in (pg.get("rom_t"), benef_t) if v] or [0.0])
        base = "maior entre produção bruta e beneficiada (t)"
    if not total:
        base += " — sem AMB no ano"
    rpt = (_rs_proc[(k, ano, p)] / t) if t else None
    med = _mediana_metal.get(k) if metal else _mediana.get((k, "t"))
    acima = bool(total) and t > total
    barato = rpt is not None and bool(med) and rpt < med / 10
    if not (acima or (metal and barato)):
        continue
    razao = t / total if total else None
    # severidade: duas evidencias independentes -- volume acima do estado inteiro e tonelagem "barata" demais frente aos pares
    motivos = []
    if razao and razao > 2:
        motivos.append("mais de 2× o total estadual (inconsistência forte)")
    if barato:
        motivos.append("R$/t mais de 10× abaixo da mediana do mineral (indício de tonelagem inflada ou de minério declarado como metal)")
    if motivos:
        sev, obs = "alta", "; ".join(motivos) + ". Revisar a declaração ou o tipo de uso."
        obs = obs[0].upper() + obs[1:]
    else:
        sev = "moderada"
        obs = ("Entre 1 e 2× o total estadual, com R$/t " + ("compatível com a mediana do mineral" if med else "sem mediana para comparar")
               + ": pode ser venda de estoque de anos anteriores, AMB ainda preliminar ou diferença de base (bruta × beneficiada).")
    criterio = "; ".join(c for c, ok in (("tonelagem acima do total estadual", acima),
                                          ("R$/t mais de 10× abaixo da mediana do metal", metal and barato)) if ok)
    abertura = (f"Um único processo declara mais toneladas comercializadas do que o AMB registra para o estado inteiro na categoria ({base}); "
                "mantido na soma. " if acima else
                f"Tonelagem abaixo do limite do AMB ({base}), mas incompatível com o valor recolhido para um metal; mantido na soma. ")
    cfem_alertas_processo.append(dict(
        mineral_key=k, year=ano, processo_anm=p, substancias="; ".join(sorted(_subs_proc[(k, ano, p)])),
        usos="; ".join(sorted(_usos_proc[(k, ano, p)])), cfem_t_processo=t, amb_total_uf_t=total or None, amb_base=base, razao=razao,
        criterio=criterio, severidade=sev, valor_recolhido_brl=_rs_proc[(k, ano, p)], r_por_t=rpt, mediana_r_por_t_mineral=med,
        observacao=abertura + obs))
cfem_alertas_processo.sort(key=lambda a: (a["severidade"] != "alta", -(a["razao"] or 0)))
print(f"CFEM: {len(cfem_alertas_processo)} processo-anos com quantidade implausível (sinalizados na 09c; "
      f"{sum(a['severidade'] == 'alta' for a in cfem_alertas_processo)} de severidade alta; limite em metal para: {sorted(METAL_KG)}).")

for l in _linhas_cfem:
    sn = norm(l["subst"])
    if not eh_rocha(sn):
        continue
    if l["regra"] == "uso_majoritario_da_rocha_em_GO":
        uso_exib, origem = USO_PADRAO_ROCHA.get(sn, ""), "uso majoritário da rocha em GO"
    else:
        uso_exib, origem = (l.get("uso") or "(sem uso)"), (l.get("origem_uso") or "—")
    a = rochas_audit[("CFEM (GO)", sn, uso_exib, origem, l["k"], l["regra"])]
    a["contagem"] += 1
    a["valor_recolhido_brl"] += l["valor"] or 0.0
    if l["massa"] and l["conv"] and not l.get("excluida"):
        a["cfem_t"] += l["conv"]

# --- Cadastro Mineiro (GO) -- titulos e titulares por mineral (acumulado, sem ano confiavel) ---
cad_processos = defaultdict(set)
cad_titulares = defaultdict(set)
for raw, proc, tit, doc, uso in cad_rows:
    k, regra = mineral_key_com_uso(raw, uso, USO_PADRAO_ROCHA)
    if eh_rocha(raw):
        sn = norm(raw)
        maj = regra == "uso_majoritario_da_rocha_em_GO"
        rochas_audit[("Cadastro Mineiro (GO)", sn, USO_PADRAO_ROCHA.get(sn, "") if maj else (norm_uso(uso) or "(sem uso)"),
                      "uso majoritário da rocha em GO" if maj else "declarado no título", k, regra)]["contagem"] += 1
    if k is None:
        continue
    if proc:
        cad_processos[k].add(proc)
    ident = re.sub(r"\D", "", str(doc)) or norm(tit)
    if ident:
        cad_titulares[k].add(ident)

# --- SIGMINE (GO) -- processos com geometria (proxy de "operacoes" mapeadas) ---
sig_processos = defaultdict(set)
for r in sig_rows:
    procs_subs = re.split(r"[,;]", r.get("SUBS", ""))
    for s in procs_subs:
        s = s.strip()
        if not s:
            continue
        k, regra = mineral_key_com_uso(s, r.get("USO", ""), USO_PADRAO_ROCHA)
        if eh_rocha(s):
            sn = norm(s)
            maj = regra == "uso_majoritario_da_rocha_em_GO"
            rochas_audit[("SIGMINE (GO)", sn, USO_PADRAO_ROCHA.get(sn, "") if maj else (norm_uso(r.get("USO", "")) or "(sem uso)"),
                          "uso majoritário da rocha em GO" if maj else "campo USO do SIGMINE", k, regra)]["contagem"] += 1
        if k:
            sig_processos[k].add(r.get("PROCESSO", ""))

print(f"\nAgregado: {len(prod['GO'])} combinações (mineral,ano) com produção GO; "
      f"{len(prod['BR'])} com produção BR; {len(cfem_agg)} combinações (mineral,ano) com CFEM GO; "
      f"{len(cad_processos)} minerais com processos no Cadastro Mineiro GO; "
      f"{len(sig_processos)} minerais com processos no SIGMINE GO.")

# --- montar as linhas finais da Base 1 ---
from regras_series import SERIE_BENEF_POR_CONTIDO  # v18: série do beneficiado pelo contido (nióbio)
all_years = sorted(set(int(y) for y in pb["Ano base"].unique()) | set(int(y) for y in pf["Ano base"].unique()))
base1_rows = []
for key, (nome, classe, grupo, agregada, status_previsto, obs) in MIN_DEF.items():
    tem_titulo_go = key in cad_processos or key in sig_processos or key in cfem_titulares
    tem_ano_go = bool({a for (k, a) in prod["GO"] if k == key} | {a for (k, a) in cfem_agg if k == key})
    # status_producao_go e SEMPRE derivado da evidencia agregada (nao do texto digitado em MIN_DEF),
    # para nao correr o risco de descrever como "confirmada" algo que so tem titulo minerario.
    status = "confirmada" if tem_ano_go else ("exploracao" if tem_titulo_go else "sem_titulo_ou_producao_go")
    if status != status_previsto:
        obs = (obs + f" [status recalculado automaticamente para '{status}'; rascunho inicial dizia '{status_previsto}']").strip()
    anos_com_dado = sorted({a for (k, a) in prod["GO"] if k == key} | {a for (k, a) in prod["BR"] if k == key} | {a for (k, a) in cfem_agg if k == key})
    if tem_titulo_go and not tem_ano_go:
        anos_com_dado = [None] + anos_com_dado  # GO só tem título (Cadastro/SIGMINE/CFEM-titular), sem ano de produção/CFEM -- linha "snapshot"
    if not anos_com_dado:
        anos_com_dado = [None]  # nem produção, nem título, nem CFEM em GO -- ainda entra na dimensao (comparação nacional)
    for ano in anos_com_dado:
        for uf in ("GO", "BR"):
            if ano is None and uf == "BR":
                continue
            p = prod[uf].get((key, ano), {}) if ano is not None else {}
            c = cfem_agg.get((key, ano), {}) if (ano is not None and uf == "GO") else {}
            if uf == "GO" and not p and not c and not (ano is None and tem_titulo_go):
                continue
            if uf == "BR" and not p:
                continue
            base1_rows.append(dict(
                uf=uf, mineral_id=key, mineral_nome=nome, classe_substancia=classe, mineral_grupo=grupo, ano=ano,
                producao_rom_t=p.get("rom_t"), producao_beneficiada=p.get("beneficiada"),
                unidade_beneficiada=p.get("beneficiada_unidade", ""), valor_venda_beneficiada_brl=p.get("valor_venda_benef_brl"),
                contido_beneficiada_t=p.get("contido_benef_t"),
                contido_indicacao="; ".join(sorted(contido_ind.get((uf, key, ano), ()))),
                serie_beneficiada=(("contido" if key in SERIE_BENEF_POR_CONTIDO else "quantidade")
                                   if (p.get("beneficiada") is not None or p.get("contido_benef_t") is not None) else ""),
                cfem_qtd_comercializada_t=c.get("cfem_qtd_comercializada_t"),
                cfem_qtd_outras_unidades=("; ".join(f"{u}: {q:.3f}" for u, q in sorted(cfem_outras[(key, ano)].items()))
                                          if (uf == "GO" and ano is not None and (key, ano) in cfem_outras) else ""),
                cfem_qtd_linhas_excluidas=(cfem_excl.get((key, ano), 0) if (uf == "GO" and ano is not None and c) else None),
                cfem_recolhido_brl=c.get("cfem_recolhido_brl"),
                qtd_titulares_cfem=len(cfem_titulares.get(key, [])) if uf == "GO" else None,
                qtd_processos_cadastro_mineiro=len(cad_processos.get(key, [])) if uf == "GO" else None,
                qtd_titulares_cadastro_mineiro=len(cad_titulares.get(key, [])) if uf == "GO" else None,
                qtd_processos_sigmine=len(sig_processos.get(key, [])) if uf == "GO" else None,
                categoria_agregada_anm=agregada, status_producao_go=status,
                # CORRECAO (v6): citava so producao/CFEM -- e com '; ' sobrando no inicio quando so havia CFEM --,
                # embora as colunas qtd_* venham do Cadastro Mineiro e do SIGMINE. Agora cada fonte entra
                # se, e somente se, alguma coluna da linha veio dela.
                source_ids="; ".join(s for s, usa in [
                    ("SRC_ANM_PROD_BRUTA", p.get("rom_t") is not None),
                    ("SRC_ANM_PROD_BENEF", p.get("beneficiada") is not None or p.get("valor_venda_benef_brl") is not None),
                    ("SRC_ANM_CFEM", bool(c) or (uf == "GO" and key in cfem_titulares)),
                    ("SRC_ANM_CADASTRO", uf == "GO" and key in cad_processos),
                    ("SRC_ANM_SIGMINE", uf == "GO" and key in sig_processos)] if usa),
                observacao=(obs + (" Série do beneficiado = contido em " + SERIE_BENEF_POR_CONTIDO[key]["indicacao"] + " (contido_beneficiada_t): "
                                   + SERIE_BENEF_POR_CONTIDO[key]["motivo"] + "; producao_beneficiada fica como registro."
                                   if key in SERIE_BENEF_POR_CONTIDO and ano is not None else "")).strip(),
            ))

print(f"\nBase 1 (mineral x ano, GO+BR): {len(base1_rows)} linhas geradas.")
with open(f"{TMP}/_base1_rows.json", "w", encoding="utf-8") as f:
    json.dump(base1_rows, f, ensure_ascii=False)
with open(f"{TMP}/_min_def.json", "w", encoding="utf-8") as f:
    json.dump({k: list(v) for k, v in MIN_DEF.items()}, f, ensure_ascii=False)
with open(f"{TMP}/_rochas_uso.json", "w", encoding="utf-8") as f:
    json.dump([dict(fonte=fo, substancia=sn, tipo_de_uso=u, origem_do_uso=o, mineral_key=kk, regra=rg, **v)
               for (fo, sn, u, o, kk, rg), v in rochas_audit.items()], f, ensure_ascii=False)
with open(f"{TMP}/_uso_rochas.json", "w", encoding="utf-8") as f:
    _ps = {f"{p}|{s}": c.most_common(1)[0][0] for (p, s), c in uso_sig_proc_subst.items()}
    _ps.update({f"{p}|{s}": c.most_common(1)[0][0] for (p, s), c in uso_proc_subst.items()})  # Cadastro tem prioridade
    json.dump(dict(padrao=USO_PADRAO_ROCHA, proc_subst=_ps,
                   proc={p: c.most_common(1)[0][0] for p, c in uso_proc_rocha.items()}), f, ensure_ascii=False)
with open(f"{TMP}/_cfem_linhas.json", "w", encoding="utf-8") as f:  # tratamento linha a linha, para a aba 08
    json.dump([{c: l[c] for c in ("idx", "k", "ano", "subst", "un", "massa", "conv", "cientifica", "excluida", "motivo",
                                  "proc_canon", "uso", "origem_uso", "regra")} for l in _linhas_cfem], f, ensure_ascii=False)
with open(f"{TMP}/_cfem_alertas_processo.json", "w", encoding="utf-8") as f:
    json.dump(cfem_alertas_processo, f, ensure_ascii=False)
with open(f"{TMP}/_cfem_qtd_excluidas.json", "w", encoding="utf-8") as f:
    json.dump(cfem_qtd_excluidas, f, ensure_ascii=False)
print("Arquivos intermediários salvos para o gerador da planilha.")
