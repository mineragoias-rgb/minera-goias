# -*- coding: utf-8 -*-
"""Catálogo de todas as bases que a plataforma MINERA Goiás usa: nome, origem, abas/camadas, campos e unidades de medida.

    python scripts/build_catalogo_bases.py          # grava Squad 1/Auditoria e qualidade/catalogo_bases.xlsx e os CSVs

Lê os arquivos de verdade (cabeçalho, contagem de linhas, amostra de valores) — nada é digitado à mão, exceto a lista de
bases abaixo (BASES), que diz o que é cada arquivo, de que órgão vem e onde o site o usa. A origem, a URL e a frequência saem de
`docs/fontes_de_dados.csv` quando a base está lá. As unidades vêm, nesta ordem de preferência:
  1. do dicionário oficial da base consolidada (aba 14_dicionario_dados, coluna unidade_ou_dominio);
  2. de UNIDADES_CONHECIDAS, conferidas no metadado da fonte ou no próprio arquivo (ex.: coluna de unidade ao lado);
  3. do nome da coluna (ex.: "(t)", "_mwh", "ValorRecolhido") — marcadas "pelo nome do campo";
  4. "a confirmar" quando não dá para saber; texto e códigos ficam "— (texto/código)".
"""
import csv
import glob
import io
import json
import re
import sys
import unicodedata
import zipfile
from collections import Counter
from pathlib import Path

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

RAIZ = Path(__file__).resolve().parents[1]
SAIDA = RAIZ / "Squad 1" / "Auditoria e qualidade"
S1 = "Squad 1"
DB = "Squad 1/Dados brutos"

# id, nível, nome, origem (quando não está em docs/fontes_de_dados.csv), arquivos (globs a partir da raiz), nota
BASES = [
    # 1 — fontes brutas (como o órgão publica, às vezes recortadas para Goiás)
    ("ANM_AMB_PROD_BRUTA", "1 Fonte bruta", None, None, [f"{DB}/ANM - Anuário Mineral Brasileiro (AMB)/Producao_Bruta.csv"], ""),
    ("ANM_AMB_PROD_BENEF", "1 Fonte bruta", None, None, [f"{DB}/ANM - Anuário Mineral Brasileiro (AMB)/Producao_Beneficiada.csv"], ""),
    ("ANM_CFEM", "1 Fonte bruta", None, None, [f"{DB}/ANM - CFEM/*.csv"], ""),
    ("ANM_SCM", "1 Fonte bruta", None, None, [f"{DB}/ANM - Cadastro Mineiro/*.csv"], ""),
    ("ANM_SIGMINE", "1 Fonte bruta", None, None, [f"{DB}/ANM - SIGMINE/GO.zip"], ""),
    ("ANM_INVEST_PESQUISA", "1 Fonte bruta", None, None, [f"{DB}/ANM - Investimento em pesquisa mineral/*.csv"], ""),
    ("ANM_RODADAS", "1 Fonte bruta", None, None, [f"{S1}/dados/ResultadoRodadaDisponibilidade (1).csv"], ""),
    ("ANM_SIGBM", "1 Fonte bruta", None, None, [], "Sem arquivo próprio no repositório: o Atlas usa as 23 barragens do retrato antigo (data/atlas/atlas.json, chave dams)."),
    ("ANM_PLANILHAS_DERIVADAS", "1 Fonte bruta", "Planilhas derivadas da ANM (operação e potencial; panorama)", "ANM (dados reorganizados por terceiros)",
     [f"{DB}/ANM - Planilhas derivadas/*.xlsx"], "Origem exata das planilhas a confirmar."),
    ("IBGE_MALHA_MUN", "1 Fonte bruta", None, None, [f"{DB}/IBGE - Malha municipal 2025/*.zip"], ""),
    ("IBGE_LIMITE_UF", "1 Fonte bruta", None, None, [f"{S1}/P3M/Original/6- Cartografia/GO_UF_2024.zip"], ""),
    ("IBGE_POP", "1 Fonte bruta", None, None, [f"{DB}/IBGE - População e PIB (SIDRA)/populacao_*.json"], ""),
    ("IBGE_PIB", "1 Fonte bruta", None, None, [f"{DB}/IBGE - População e PIB (SIDRA)/pib_*.json"], ""),
    ("SGB_RECMIN", "1 Fonte bruta", None, None, [f"{DB}/SGB - RECMIN/*.geojson"], ""),
    ("SGB_GEOSGB_GEOQUIMICA", "1 Fonte bruta", None, None, [f"{DB}/SGB - GeoSGB geoquímica/*.zip"], ""),
    ("SGB_P3M", "1 Fonte bruta", None, None, [f"{S1}/P3M/Original/*/*.zip"],
     "Uma aba por camada (157). Descrição completa de cada camada em Squad 1/P3M/inventario_p3m.csv; a versão recortada por Goiás tem os mesmos campos."),
    ("CCEE_CARGA", "1 Fonte bruta", None, None, [f"{S1}/dados/CCEE/*.csv"], ""),
    ("ANEEL_SIGA", "1 Fonte bruta", None, None, [f"{DB}/ANEEL - SIGA/*.csv"], ""),
    ("ONS_LT_SE", "1 Fonte bruta", None, None, [f"{DB}/ONS - Dados abertos/*.csv"], ""),
    ("EPE_BEN", "1 Fonte bruta", None, None, [f"{DB}/EPE - Balanço Energético Nacional (BEN)/*.xlsx"], ""),
    ("EPE_PDE", "1 Fonte bruta", None, None, [f"{DB}/EPE - Plano Decenal de Energia (PDE 2035)/*"], ""),
    ("IMB_GOIAS_EM_DADOS", "1 Fonte bruta", None, None, [f"{DB}/IMB - Goiás em Dados/*.csv"], ""),
    ("MAPBIOMAS_COBERTURA", "1 Fonte bruta", "MapBiomas Coleção 11 — cobertura e uso da terra (vegetação nativa 1985–2025)", "MapBiomas",
     [f"{S1}/MapBiomas/cobertura_colecao11/metadados.json"],
     "A série anual entra no Mapa como data/mapa/camadas/vegetacao_nativa_<ano>.json (gerada pelo robô)."),
    ("MAPA_VEGETACAO_RIOS_2025", "1 Fonte bruta", "Mapa de vegetação nativa e hidrografia de Goiás (2025)", "MapBiomas Col. 11; OpenStreetMap; IBGE",
     [f"{S1}/Mapa vegetação e rios 2025/*.zip", f"{S1}/Mapa vegetação e rios 2025/*.csv"], "Pacote montado pelo Squad 1 em 22/10/2026."),
    # 2 — curadoria da equipe e retratos
    ("RADAR_CURADORIA", "2 Curadoria", None, None, [f"{S1}/Radar de Projetos/*.json", f"{S1}/Radar de Projetos/*.xlsx"], ""),
    ("PROJETOS_LUCAS", "2 Curadoria", None, None, [f"{DB}/Aluno Lucas Maia/*.xlsx"], ""),
    ("LUCAS_CORRIGIDAS", "2 Curadoria", "Planilhas corrigidas do Lucas (arrecadação e produção)", "Equipe (Squad 1, Lucas) a partir de ANM",
     [f"{S1}/dados/*LUCAS V1.xlsx"], "A coluna de correção não é documentada (relatório de conformidade v1, §3.4)."),
    ("BASE_PROD_ENERGIA_2023_2026", "2 Curadoria", "Base Mineração Goiás — produção e energia 2023–2026", "a confirmar",
     [f"{S1}/dados/Base_Mineracao_Goias_Producao_Energia_2023_2026.xlsx"], "Autoria e método a confirmar."),
    ("PANORAMA_HTML", "2 Curadoria", "Panorama Mineração Goiás (HTML original com dados embutidos)", "Equipe (retrato anterior, eliel.html)",
     [f"{S1}/dados/Panorama Mineracao Goias.html"], "Retrato congelado: a energia e as barragens do Atlas ainda vêm daqui."),
    ("PRODUCAO_EMPRESAS", "2 Curadoria", None, None, ["producao/base_curada.json"], ""),
    ("MERCADO_LEITURA", "2 Curadoria", None, None, ["public/data/mercado/mercado_v1.json", "public/data/mercado/projetos_go_v1.json"], ""),
    ("NOTICIAS_RSS", "2 Curadoria", None, None, ["public/data/noticias/latest.json"], "Um arquivo por mês em public/data/noticias/meses/."),
    ("SQUAD2_PARAMETROS", "2 Curadoria", None, None, ["Squad 2/modello_reale/parameters/*.csv"], ""),
    ("SQUAD2_INTENSIDADE", "2 Curadoria", "Base de intensidade energética do Squad 2 (v1)", "Equipe (Squad 2, Sarah Lattouf)",
     ["Squad 2/intensidade_energetica/*.csv"], "Gerada por build_intensidade.py; refeita pela automação de derivados."),
    # 3 — base consolidada do Squad 1
    ("BASE_CONSOLIDADA", "3 Base consolidada", "Base Mineral de Goiás — planilha consolidada", "Squad 1 (Eliel) a partir de ANM, IBGE, SGB e IMB",
     [f"{S1}/Bases consolidadas/documentacao/prototipo_bases_consolidadas_v*.xlsx"], "Campos e unidades pelo dicionário oficial (aba 14_dicionario_dados)."),
    ("PACOTE_SQUAD2", "3 Base consolidada", "Pacote da aba 12 para o Squad 2", "Squad 1 (gerado da planilha consolidada)",
     [f"{S1}/Bases consolidadas/documentacao/pacote_squad2/*.csv"], ""),
    # 4 — pacotes que o site lê
    ("SITE_ATLAS", "4 Pacote do site", "Atlas (data/atlas)", "Gerado da base consolidada (+ retrato antigo para energia e barragens)", ["data/atlas/atlas.json"], ""),
    ("SITE_PANORAMA", "4 Pacote do site", "Panorama (data/panorama)", "Gerado da base consolidada, CCEE, rodadas e DIPEM", ["data/panorama/panorama.json"], ""),
    ("SITE_EMPRESAS", "4 Pacote do site", "Empresas (data/empresas)", "Gerado de produção declarada + CCEE", ["data/empresas/empresas.json"], ""),
    ("SITE_PRODUCAO", "4 Pacote do site", "Produção declarada (data/producao)", "Gerado de producao/base_curada.json", ["data/producao/producao.json"], ""),
    ("SITE_MAPA", "4 Pacote do site", "Mapa mineral (data/mapa)", "Gerado do P3M, da base consolidada, do Radar e do MapBiomas",
     ["data/mapa/catalogo.json", "data/mapa/tabelas/*.json"], "As camadas em data/mapa/camadas/ estão descritas em catalogo.json."),
    ("SITE_SIMULADOR", "4 Pacote do site", "Simulador (parâmetros)", "Gerado do modelo do Squad 2", ["public/data/simulador/parametros_v1.json"], ""),
]

# Unidades conferidas na fonte (metadado ou coluna de unidade). Chave: (id da base ou "*", nome do campo).
UNIDADES_CONHECIDAS = {
    ("ANM_AMB_PROD_BENEF", "Quantidade Produção"): "conforme a coluna 'Unidade de Medida - Produção' (t, kg, m³, ct…)",
    ("ANM_AMB_PROD_BENEF", "Quantidade Contido"): "conforme a coluna 'Unidade de Medida - Contido'",
    ("ANM_AMB_PROD_BENEF", "Quantidade Venda"): "conforme a coluna 'Unidade de Medida - Venda'",
    ("ANM_AMB_PROD_BENEF", "Quantidade Consumo/Utilização na Usina"): "conforme a coluna de unidade ao lado",
    ("ANM_AMB_PROD_BENEF", "Quantidade Transferência para Transformação / Utilização / Consumo"): "conforme a coluna de unidade ao lado",
    ("ANM_AMB_PROD_BRUTA", "Quantidade Contido"): "conforme a coluna 'Unidade de Medida - Contido'",
    ("ANM_CFEM", "QuantidadeComercializada"): "conforme a coluna UnidadeDeMedida (t, kg, g, l, m³, m², ct — misturadas no mesmo mineral)",
    ("ANM_CFEM", "ValorRecolhido"): "R$ (valores correntes)",
    ("ANM_CFEM", "Mês"): "mês (1–12)",
    ("ANM_RODADAS", "AreaPoligonal"): "ha",
    ("ANM_RODADAS", "ValorLanceVencedorReais"): "R$",
    ("CCEE_CARGA", "MES_REFERENCIA"): "AAAAMM",
    ("CCEE_CARGA", "CAPACIDADE_CARGA"): "MW",
    ("CCEE_CARGA", "CONSUMO_ACL"): "MWh no mês",
    ("CCEE_CARGA", "CONSUMO_CATIVO_PARC_LIVRE"): "MWh no mês",
    ("CCEE_CARGA", "CONSUMO_TOTAL"): "MWh no mês",
    ("ANEEL_SIGA", "MdaPotenciaOutorgadaKw"): "kW", ("ANEEL_SIGA", "MdaPotenciaFiscalizadaKw"): "kW",
    ("ANEEL_SIGA", "MdaGarantiaFisicaKw"): "kW médio",
    ("ANEEL_SIGA", "NumCoordNEmpreendimento"): "graus decimais (latitude)", ("ANEEL_SIGA", "NumCoordEEmpreendimento"): "graus decimais (longitude)",
    ("ONS_LT_SE", "val_niveltensao_kv"): "kV", ("ONS_LT_SE", "val_niveltensao"): "kV", ("ONS_LT_SE", "val_comprimento"): "km",
    ("ONS_LT_SE", "val_resistencia"): "% na base do sistema (pu ×100; a confirmar no metadado do ONS)",
    ("ONS_LT_SE", "val_reatancia"): "% na base do sistema (a confirmar no metadado do ONS)", ("ONS_LT_SE", "val_shunt"): "Mvar",
    ("IMB_GOIAS_EM_DADOS", "*ano*"): "unidade escrita no texto da coluna 'Variável' (ex.: 'Produção de Ouro (kg)')",
    ("IBGE_PIB", "V"): "mil R$ (campo MN = 'Mil Reais')", ("IBGE_POP", "V"): "pessoas (campo MN)",
    ("ANM_INVEST_PESQUISA", "Valor*"): "R$",
    ("MAPA_VEGETACAO_RIOS_2025", "area_ha"): "ha", ("MAPA_VEGETACAO_RIOS_2025", "pct_do_estado"): "% da área do estado",
    ("MAPA_VEGETACAO_RIOS_2025", "comp_km"): "km",
}


def sem_acento(s):
    return unicodedata.normalize("NFD", str(s)).encode("ascii", "ignore").decode().lower()


def unidade_pelo_nome(campo):
    n = sem_acento(campo).strip()
    if re.search(r"^(gid|id|fid|objectid|ogc_fid|pos|rodada|numero|nc|mc|d\dc|id_.*|.*_id|cod.*|.*codigo.*|cd_.*|nr_.*|num_.*|niv_.*|ordem_.*)$|\(.*codigo\)", n):
        return "— (código/identificador)"
    if re.search(r"cnpj|cpf|^processo$|^guia$|ceg$|^classe_mapbiomas$|^d\dn \(ano\)$|^numeroarea$|^centro_cus$|^precisao$", n):
        return "— (código/identificador)"
    sufixos = [(r"(^|[_\s(])kg($|[_\s)])", "kg"), (r"__gw_|\(gw\)|(^|_)gw$", "GW"), (r"\(mw\)|(^|_)mw$", "MW"),
               (r"r__bilh|r\$ ?bilh", "R$ bilhões"), (r"mtco2", "MtCO2e"), (r"milivol|(^|_)mv$", "mV"),
               (r"(^|_)m$", "m"), (r"(^|_)l$", "l"), (r"(^|_)g$", "g")]
    for padrao, un in sufixos:
        if re.search(padrao, n):
            return un
    if re.search(r"^(processos|registros|municipios|titulares|titulos|itens|areas|substancias|empresas|numcursos|nrpistas|nrfaixas|n|n_.*|qtd_.*|qt_.*_n)$", n):
        return "contagem (nº)"
    regras = [
        (r"idade_m(ax|in)", "Ma (milhões de anos)"), (r"^escala$", "denominador da escala (1:N)"), (r"^ph$", "pH (adimensional)"),
        (r"altitude", "m"), (r"limitevelo", "km/h"), (r"^litros$", "l"), (r"orcamento", "R$"),
        (r"^long$|^x$", "graus decimais (longitude)"), (r"^y$", "graus decimais (latitude)"),
        (r"(^|_)lat(itude)?($|_)|coordn", "graus decimais (latitude)"), (r"(^|_)lon(gitude)?($|_)|^lng$|coorde", "graus decimais (longitude)"),
        (r"kwh_?/?t", "kWh/t"), (r"mwh_?/?kg", "MWh/kg"), (r"mwh_?/?t|intensity_mwh_t", "MWh/t"), (r"twh", "TWh"),
        (r"mwh|consumo_(acl|total|cativo)", "MWh"), (r"capacidade_mw|_mw$", "MW"), (r"kw$", "kW"), (r"kv$|niveltensao", "kV"),
        (r"\(r\$\)|_brl|valor|recolhid|lance|reais|_rs$|venda_rs|cfem_total|capex", "R$"), (r"usd", "US$"),
        (r"area_?ha|\(ha\)|^qt_area$|areapoligonal|hectare", "ha"), (r"km2|area_km", "km²"), (r"comp_km|_km$|comprimento", "km"),
        (r"pct|percent|\(%\)|_share|fracao", "% ou fração (ver campo)"), (r"populacao|habitantes", "pessoas"),
        (r"\(t\)|_t$|toneladas|production_t|_ton$|^ton$", "t"), (r"\(kg\)|_kg$", "kg"), (r"\(g\)", "g"), (r"ppm", "ppm"), (r"ppb", "ppb"),
        (r"^(ano|year|ano base|ano_base|anodoprocesso)$|_ano$|^ano_", "ano (AAAA)"), (r"mes_referencia|aaaamm", "AAAAMM"), (r"^m[eê]s$|^mes$", "mês (1–12)"),
        (r"^dat|data|_data|date|_em$", "data"),
        (r"quantidade|qtd|^v$|^valor$", "a confirmar (quantidade sem unidade no nome)"),
    ]
    for padrao, un in regras:
        if re.search(padrao, n):
            return un
    return None


def unidade(base_id, campo, tipo):
    for chave in ((base_id, campo), ("*", campo)):
        if chave in UNIDADES_CONHECIDAS:
            return UNIDADES_CONHECIDAS[chave], "metadado da fonte / conferido no arquivo"
    for (b, c), un in UNIDADES_CONHECIDAS.items():
        if b == base_id and "*" in c:
            if c == "*ano*" and re.fullmatch(r"\d{4}", str(campo)):
                return un, "metadado da fonte / conferido no arquivo"
            if c.endswith("*") and str(campo).startswith(c[:-1]):
                return un, "metadado da fonte / conferido no arquivo"
    un = unidade_pelo_nome(campo)
    if un:
        if un.startswith("— ") or un.startswith("contagem"):
            return un, "não se aplica"
        return un, ("a confirmar" if un.startswith("a confirmar") else "pelo nome do campo")
    if tipo in ("número inteiro", "número decimal"):
        return "a confirmar", "a confirmar"
    return "— (texto/código)", "não se aplica"


def tipo_de(valores):
    vs = [str(v).strip() for v in valores if v not in (None, "") and str(v).strip() not in ("", "-")]
    if not vs:
        return "vazio na amostra"
    def num(v):
        v2 = v.replace(".", "").replace(",", ".") if re.fullmatch(r"-?[\d.]*,\d*", v) else v
        try:
            float(v2); return True
        except ValueError:
            return False
    if all(num(v) for v in vs):
        return "número inteiro" if all(re.fullmatch(r"-?\d+", v) for v in vs) else "número decimal"
    if all(re.fullmatch(r"\d{1,4}[-/]\d{1,2}[-/]\d{1,4}.*", v) for v in vs):
        return "data"
    return "texto"


def exemplo(valores):
    for v in valores:
        if v not in (None, "") and str(v).strip() not in ("", "-"):
            return str(v).strip()[:80]
    return ""


def ler_texto(b):
    for enc in ("utf-8-sig", "cp1252"):
        try:
            return b.decode(enc), enc
        except UnicodeDecodeError:
            continue
    return b.decode("latin-1"), "latin-1"


# ------------------------------------------------------------------------------------------------ leitores por formato
def ler_csv(caminho, base_id):
    texto, enc = ler_texto(Path(caminho).read_bytes())
    primeira = texto.splitlines()[0] if texto else ""
    sep = max(";,\t|", key=primeira.count)
    linhas = list(csv.reader(io.StringIO(texto), delimiter=sep))
    cab, corpo = linhas[0], [l for l in linhas[1:] if any(c.strip() for c in l)]
    amostra = corpo[:3000]
    campos = []
    for i, c in enumerate(cab):
        vals = [l[i] for l in amostra if i < len(l)]
        t = tipo_de(vals)
        campos.append((c, t, exemplo(vals), *unidade(base_id, c, t)))
    return [{"aba": "(arquivo único)", "linhas": len(corpo), "colunas": len(cab), "detalhe": f"CSV, {enc}, separador '{sep}'", "campos": campos}]


def ler_xlsx(caminho, base_id):
    wb = openpyxl.load_workbook(caminho, read_only=True, data_only=True)
    abas = []
    for ws in wb.worksheets:
        linhas = []
        for i, r in enumerate(ws.iter_rows(values_only=True)):
            linhas.append(r)
            if i >= 400:
                break
        cab_i = next((i for i, r in enumerate(linhas[:15]) if r and sum(v not in (None, "") for v in r) >= max(2, 0.5 * len([v for v in r if v is not None] or [0]))
                      and sum(isinstance(v, str) for v in r if v is not None) >= 0.6 * sum(v is not None for v in r)), None)
        campos = []
        if cab_i is not None:
            cab = linhas[cab_i]
            corpo = linhas[cab_i + 1:]
            for j, c in enumerate(cab):
                if c in (None, ""):
                    continue
                vals = [r[j] for r in corpo if r and j < len(r)]
                t = tipo_de(vals)
                campos.append((str(c), t, exemplo(vals), *unidade(base_id, str(c), t)))
        abas.append({"aba": ws.title, "linhas": max(0, (ws.max_row or 0) - (cab_i + 1 if cab_i is not None else 0)),
                     "colunas": ws.max_column or 0, "detalhe": "planilha Excel", "campos": campos})
    return abas


def ler_dbf_zip(z, nome_shp, base_id):
    import shapefile
    stem = nome_shp[:-4]
    membros = {Path(n).suffix.lower(): n for n in z.namelist() if n.startswith(stem + ".") or n[:-4] == stem}
    if ".dbf" not in membros:
        return None
    cpg = z.read(membros[".cpg"]).decode("ascii", "ignore").strip() if ".cpg" in membros else ""
    cst = z.read(membros[".cst"]).decode("ascii", "ignore").strip() if ".cst" in membros else ""
    enc = (cpg or cst or "latin-1")
    enc = "cp1252" if enc in ("1252",) else enc
    r = shapefile.Reader(dbf=io.BytesIO(z.read(membros[".dbf"])), encoding=enc, encodingErrors="replace")
    regs = [r.record(i) for i in range(min(len(r), 2000))]
    campos = []
    for k, f in enumerate(r.fields[1:]):
        vals = [rec[k] for rec in regs]
        tipo = {"N": "número", "F": "número decimal", "D": "data", "L": "lógico"}.get(f[1], "texto")
        if tipo == "número":
            tipo = "número decimal" if f[3] else "número inteiro"
        campos.append((f[0], tipo, exemplo(vals), *unidade(base_id, f[0], tipo)))
    geom = {1: "pontos", 3: "linhas", 5: "polígonos", 8: "multipontos", 11: "pontos", 13: "linhas", 15: "polígonos"}
    tipo_geo = ""
    if ".shp" in membros:
        h = z.read(membros[".shp"])[:36]
        tipo_geo = geom.get(int.from_bytes(h[32:36], "little"), "")
    return {"aba": Path(nome_shp).stem, "linhas": len(r), "colunas": len(r.fields) - 1,
            "detalhe": f"shapefile de {tipo_geo}, codificação {enc}".strip(), "campos": campos}


def ler_zip(caminho, base_id):
    abas = []
    with zipfile.ZipFile(caminho) as z:
        nomes = z.namelist()
        for n in nomes:
            if n.lower().endswith(".shp"):
                a = ler_dbf_zip(z, n, base_id)
                if a:
                    abas.append(a)
        for n in nomes:
            if n.lower().endswith((".csv", ".geojson", ".xlsx", ".pdf", ".png")) and not n.endswith("/"):
                if n.lower().endswith(".csv"):
                    texto, _ = ler_texto(z.read(n))
                    tmp = SAIDA / "_tmp.csv"
                    tmp.write_text(texto, encoding="utf-8")
                    a = ler_csv(tmp, base_id)[0]
                    tmp.unlink()
                    a["aba"] = n
                    abas.append(a)
                elif n.lower().endswith(".geojson"):
                    continue  # mesmas camadas do shapefile
                else:
                    abas.append({"aba": n, "linhas": "", "colunas": "", "detalhe": "documento/imagem dentro do zip", "campos": []})
    return abas or [{"aba": "(zip)", "linhas": "", "colunas": "", "detalhe": f"{len(nomes)} arquivos", "campos": []}]


def ler_geojson(caminho, base_id):
    d = json.loads(Path(caminho).read_text(encoding="utf-8"))
    feats = d.get("features", [])
    chaves = list(feats[0]["properties"]) if feats else []
    campos = []
    for c in chaves:
        vals = [f["properties"].get(c) for f in feats[:3000]]
        t = tipo_de(vals)
        campos.append((c, t, exemplo(vals), *unidade(base_id, c, t)))
    geo = Counter(f["geometry"]["type"] for f in feats if f.get("geometry")).most_common(1)
    return [{"aba": "features", "linhas": len(feats), "colunas": len(chaves), "detalhe": f"GeoJSON ({geo[0][0] if geo else ''})", "campos": campos}]


def ler_json(caminho, base_id):
    d = json.loads(Path(caminho).read_text(encoding="utf-8"))
    abas = []

    def campos_de_lista(lst):
        chaves = []
        for x in lst[:200]:
            if isinstance(x, dict):
                for k in x:
                    if k not in chaves:
                        chaves.append(k)
        out = []
        for c in chaves:
            vals = [x.get(c) if isinstance(x, dict) else None for x in lst[:3000]]
            vals = [v if not isinstance(v, (dict, list)) else json.dumps(v, ensure_ascii=False)[:60] for v in vals]
            t = tipo_de(vals)
            out.append((c, t, exemplo(vals), *unidade(base_id, c, t)))
        return out

    if isinstance(d, list):  # SIDRA: a primeira linha é o cabeçalho (código -> nome)
        if d and isinstance(d[0], dict) and all(isinstance(v, str) for v in d[0].values()) and "V" in d[0]:
            cab, corpo = d[0], d[1:]
            campos = []
            for k, nome in cab.items():
                vals = [x.get(k) for x in corpo[:3000]]
                t = tipo_de(vals)
                campos.append((f"{k} ({nome})", t, exemplo(vals), *unidade(base_id, k, t)))
            unid = Counter(x.get("MN") for x in corpo).most_common(1)
            abas.append({"aba": "valores (API SIDRA)", "linhas": len(corpo), "colunas": len(cab),
                         "detalhe": f"JSON do SIDRA; unidade publicada: {unid[0][0] if unid else ''}", "campos": campos})
        else:
            abas.append({"aba": "(lista)", "linhas": len(d), "colunas": "", "detalhe": "JSON", "campos": campos_de_lista(d)})
        return abas
    for k, v in d.items():
        if isinstance(v, dict) and "cols" in v and "rows" in v:
            rows = v["rows"]
            campos = []
            for i, c in enumerate(v["cols"]):
                vals = [r[i] for r in rows[:3000] if i < len(r)]
                t = tipo_de(vals)
                campos.append((c, t, exemplo(vals), *unidade(base_id, c, t)))
            abas.append({"aba": k, "linhas": len(rows), "colunas": len(v["cols"]), "detalhe": "tabela (cols/rows)", "campos": campos})
        elif isinstance(v, list) and v and isinstance(v[0], dict):
            abas.append({"aba": k, "linhas": len(v), "colunas": len(campos_de_lista(v)), "detalhe": "lista de registros", "campos": campos_de_lista(v)})
        elif isinstance(v, dict) and k not in ("meta",) and v and all(isinstance(x, dict) for x in v.values()):
            abas.append({"aba": k, "linhas": len(v), "colunas": "", "detalhe": "dicionário de blocos: " + ", ".join(list(v)[:8]), "campos": []})
    if not abas:
        abas.append({"aba": "(documento)", "linhas": "", "colunas": len(d), "detalhe": "JSON: " + ", ".join(list(d)[:10]), "campos": []})
    return abas


def ler_consolidada(caminho, base_id):
    wb = openpyxl.load_workbook(caminho, read_only=True)
    dic = {}
    linhas = list(wb["14_dicionario_dados"].iter_rows(values_only=True))
    cab_i = next(i for i, r in enumerate(linhas) if r and r[0] == "aba")
    cab = linhas[cab_i]
    for r in linhas[cab_i + 1:]:
        if r and r[0]:
            x = dict(zip(cab, r))
            dic.setdefault(x["aba"], []).append(x)
    abas = []
    for ws in wb.worksheets:
        campos = []
        for x in dic.get(ws.title, []):
            un = str(x.get("unidade_ou_dominio") or "").strip()
            campos.append((x["campo"], x.get("tipo") or "", str(x.get("exemplo") or "")[:80], un or "— (texto/código)",
                           "dicionário oficial (aba 14)", (x.get("descricao") or "")[:300]))
        abas.append({"aba": ws.title, "linhas": max(0, (ws.max_row or 0) - 4), "colunas": ws.max_column or 0,
                     "detalhe": ("auditoria/apoio" if re.match(r"\d+[a-z]_", ws.title) else "dados") if ws.title != "00_LEIA-ME" else "explicação da planilha",
                     "campos": campos})
    return abas


def ler(caminho, base_id):
    s = caminho.suffix.lower()
    if base_id == "BASE_CONSOLIDADA":
        return ler_consolidada(caminho, base_id)
    if s == ".csv" or s == ".txt":
        return ler_csv(caminho, base_id)
    if s == ".xlsx":
        return ler_xlsx(caminho, base_id)
    if s == ".zip":
        return ler_zip(caminho, base_id)
    if s == ".geojson":
        return ler_geojson(caminho, base_id)
    if s == ".json":
        return ler_json(caminho, base_id)
    return [{"aba": "(arquivo)", "linhas": "", "colunas": "", "detalhe": f"formato {s} não lido pelo catálogo", "campos": []}]


# ------------------------------------------------------------------------------------------------ montagem
def main():
    SAIDA.mkdir(parents=True, exist_ok=True)
    with open(RAIZ / "docs" / "fontes_de_dados.csv", encoding="utf-8-sig", newline="") as f:
        fontes = {r["id"]: r for r in csv.DictReader(f, delimiter=";")}
    bases, abas_out, campos_out, avisos = [], [], [], []
    for bid, nivel, nome, origem, padroes, nota in BASES:
        fo = fontes.get(bid, {})
        arquivos = sorted({Path(p) for pad in padroes for p in glob.glob(str(RAIZ / pad))})
        if padroes and not arquivos:
            avisos.append(f"{bid}: nenhum arquivo para {padroes}")
        n_abas = n_campos = 0
        unidades = Counter()
        for arq in arquivos:
            rel = arq.relative_to(RAIZ).as_posix()
            try:
                lidas = ler(arq, bid)
            except Exception as e:  # um arquivo ilegível não derruba o catálogo: fica registrado
                lidas = [{"aba": "(erro de leitura)", "linhas": "", "colunas": "", "detalhe": f"{type(e).__name__}: {e}"[:200], "campos": []}]
                avisos.append(f"{rel}: {type(e).__name__}: {e}")
            for a in lidas:
                n_abas += 1
                abas_out.append({"base_id": bid, "arquivo": rel, "aba_camada_tabela": a["aba"], "linhas": a["linhas"], "colunas": a["colunas"],
                                 "detalhe": a["detalhe"]})
                for c in a["campos"]:
                    campo, tipo, ex, un, como = c[:5]
                    desc = c[5] if len(c) > 5 else ""
                    n_campos += 1
                    if not re.match(r"(— |contagem|texto|url|booleano|a confirmar|sim/n|aaaa|ano |data|mês|id |mun_|min_|src_|true|false)", un.lower()) and len(un) < 40:
                        unidades[un] += 1
                    campos_out.append({"base_id": bid, "arquivo": rel, "aba_camada_tabela": a["aba"], "campo": campo, "tipo": tipo, "exemplo": ex,
                                       "unidade": un, "unidade_obtida_por": como, "descricao": desc})
        bases.append({
            "base_id": bid, "nivel": nivel, "nome": nome or fo.get("fonte", bid), "origem": origem or fo.get("orgao", ""),
            "o_que_e": fo.get("o_que_e", ""), "arquivos": "; ".join(a.relative_to(RAIZ).as_posix() for a in arquivos) or fo.get("arquivo_no_repositorio", ""),
            "n_arquivos": len(arquivos), "n_abas_camadas": n_abas, "n_campos": n_campos,
            "principais_unidades": "; ".join(u for u, _ in unidades.most_common(6)),
            "formato": fo.get("formato", ""), "url_download": fo.get("url_download", ""), "url_pagina": fo.get("url_pagina", ""),
            "frequencia_na_fonte": fo.get("frequencia_na_fonte", ""), "retrato_atual": fo.get("retrato_atual", ""),
            "usado_no_site": fo.get("usado_no_site", ""), "atualizacao": fo.get("automatizavel", ""), "observacao": " ".join(x for x in (nota, fo.get("observacoes", "")) if x),
        })

    escrever(bases, abas_out, campos_out)
    a_confirmar = sum(1 for c in campos_out if c["unidade_obtida_por"] == "a confirmar")
    print(f"{len(bases)} bases, {len(abas_out)} abas/camadas/tabelas, {len(campos_out)} campos ({a_confirmar} com unidade a confirmar)")
    for a in avisos:
        print("aviso:", a)


def escrever(bases, abas, campos):
    for nome, linhas in (("catalogo_bases_1_bases.csv", bases), ("catalogo_bases_2_abas.csv", abas), ("catalogo_bases_3_campos.csv", campos)):
        with open(SAIDA / nome, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(linhas[0]), delimiter=";", lineterminator="\r\n")
            w.writeheader()
            w.writerows(linhas)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "LEIA-ME"
    resumo = Counter(b["nivel"] for b in bases)
    texto = [
        ["Catálogo das bases da plataforma MINERA Goiás"],
        ["Frente 1 — Auditoria e qualidade dos dados (Eliel). Gerado por scripts/build_catalogo_bases.py a partir dos arquivos do repositório."],
        [""],
        ["Abas deste catálogo"],
        ["1_Bases", "uma linha por base: nome, nível, órgão de origem, arquivos, formato, links, frequência, uso no site e principais unidades"],
        ["2_Abas_camadas", "cada aba (planilha), camada (shapefile/GeoJSON) ou tabela (JSON) de cada base, com linhas e colunas"],
        ["3_Campos", "cada campo: tipo, exemplo, unidade de medida e de onde a unidade foi tirada"],
        [""],
        ["Níveis"],
        *[[k, f"{v} bases"] for k, v in sorted(resumo.items())],
        [""],
        ["De onde vem a unidade (coluna unidade_obtida_por)"],
        ["dicionário oficial (aba 14)", "unidade_ou_dominio do dicionário da base consolidada"],
        ["metadado da fonte / conferido no arquivo", "conferida no metadado do órgão ou na coluna de unidade do próprio arquivo"],
        ["pelo nome do campo", "deduzida do nome (ex.: '(t)', '_mwh', 'Valor…'); vale conferir"],
        ["a confirmar", "número sem unidade identificável: item da lista de correções da Frente 1"],
        ["não se aplica", "texto, código ou identificador"],
    ]
    for r in texto:
        ws.append(r)
    ws["A1"].font = Font(bold=True, size=14)
    for c in ("A4", "A9", "A" + str(10 + len(resumo) + 1)):
        ws[c].font = Font(bold=True)
    ws.column_dimensions["A"].width = 42
    ws.column_dimensions["B"].width = 120
    for titulo, linhas, larguras in (("1_Bases", bases, {}), ("2_Abas_camadas", abas, {}), ("3_Campos", campos, {})):
        w = wb.create_sheet(titulo)
        cab = list(linhas[0])
        w.append(cab)
        for l in linhas:
            w.append([l[c] for c in cab])
        for i, c in enumerate(cab, 1):
            w.cell(1, i).font = Font(bold=True, color="FFFFFF")
            w.cell(1, i).fill = PatternFill("solid", fgColor="123B66")
            w.cell(1, i).alignment = Alignment(wrap_text=True, vertical="top")
            larg = max([len(str(c))] + [min(60, len(str(l[c]))) for l in linhas[:500]])
            w.column_dimensions[get_column_letter(i)].width = min(60, max(10, larg + 2))
        w.freeze_panes = "B2" if titulo == "1_Bases" else "A2"
        w.auto_filter.ref = w.dimensions
        if titulo == "3_Campos":
            col = cab.index("unidade_obtida_por") + 1
            for r in range(2, w.max_row + 1):
                if w.cell(r, col).value == "a confirmar":
                    w.cell(r, col).fill = PatternFill("solid", fgColor="FCE4D6")
    wb.save(SAIDA / "catalogo_bases.xlsx")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
