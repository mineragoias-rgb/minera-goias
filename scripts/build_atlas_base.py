# -*- coding: utf-8 -*-
"""Atualiza o atlas (data/atlas/atlas.json e processes.json) com a base consolidada do Squad 1 / Estudante 1.

Mantém exatamente o formato lido por public/atlas.js. Vêm da base consolidada (v19):
  municipalities   malha IBGE 2025 (camada municipios_go da Base 4), processos do SIGMINE que tocam cada município e CFEM 2022–2026
  cfem             CFEM por município e ano para os 246 municípios (aba 08 da planilha; 2026 até o último mês do arquivo)
  production       quantidade comercializada em t e CFEM por substância × município em 2025 — é CFEM declarada, não produção
  cfem_years       CFEM por ano: valor, linhas do arquivo, municípios e titulares distintos (company_id)
  cfem_comparable  CFEM de janeiro a julho de cada ano
  beneficiated     valor de venda da produção beneficiada de Goiás (Anuário Mineral Brasileiro)
  investment       investimento declarado em pesquisa mineral em Goiás (arquivo da ANM catalogado na aba 07)
  processes.json   os processos do SIGMINE em Goiás (camada processos_minerarios_go), geometria simplificada e quantizada
  projects         um ponto por projeto que ainda não produz (camada projetos_futuros = aba 04); titular só quando é CNPJ
  occurrences      um ponto por ocorrência ou depósito do RECMIN (camada ocorrencias_minerais_recmin = aba 06)
  charts           gráficos das séries: CFEM por substância e ano, concentração da CFEM (abas 10 e 11), produção bruta por
                   mineral (aba 09), produção atribuída a operações (aba 12), projetos por mineral e ocorrências por substância
Continuam do retrato anterior (eliel.html), porque a base consolidada não os cobre: energy, energy_months (CCEE) e dams (SIGBM).

Uso, fora da VPS (precisa de geopandas/pyogrio, shapely >= 2.1 e openpyxl):
    python scripts/build_atlas_base.py --base "<pasta do projeto do Squad 1>"
A pasta do projeto contém outputs/mapas/minera_goias_mapas_v1.gpkg, documentacao/prototipo_bases_consolidadas_v19.xlsx e
dados/ANM/investimento_pesquisa/InvestimentoPesquisaMineralUf.csv — é o que o pipeline de
Squad 1/Bases consolidadas/ gera e lê.
"""
import argparse
import base64
import csv
import hashlib
import io
import json
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

import numpy as np
import openpyxl
import pyogrio
import shapely

ROOT = Path(__file__).resolve().parents[1]
ANOS = [2022, 2023, 2024, 2025, 2026]  # os mesmos passos do seletor de ano do atlas (YEARS em public/atlas.js)
GRUPOS = ["Lavra / extração autorizada", "Pesquisa autorizada", "Requerimento em análise", "Disponibilidade", "Outros"]
GRUPO_DA_FASE = {  # a mesma divisão do retrato anterior; public/atlas.js tem uma cor para cada um dos cinco grupos
    "CONCESSÃO DE LAVRA": 0, "LAVRA GARIMPEIRA": 0, "LICENCIAMENTO": 0, "REGISTRO DE EXTRAÇÃO": 0,
    "AUTORIZAÇÃO DE PESQUISA": 1,
    "DIREITO DE REQUERER A LAVRA": 2, "REQUERIMENTO DE LAVRA": 2, "REQUERIMENTO DE LAVRA GARIMPEIRA": 2,
    "REQUERIMENTO DE LICENCIAMENTO": 2, "REQUERIMENTO DE PESQUISA": 2, "REQUERIMENTO DE REGISTRO DE EXTRAÇÃO": 2,
    "APTO PARA DISPONIBILIDADE": 3, "DISPONIBILIDADE": 3,
}
MANTIDAS = ["energy", "energy_months", "dams", "coef"]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def b64(array, dtype):
    return base64.b64encode(np.asarray(array, dtype=dtype).tobytes()).decode("ascii")


def ler_planilha(caminho):
    """Uma passada na aba 08 (fato longo): CFEM e venda beneficiada; e a data do SIGMINE e o total da aba 10 para conferência."""
    wb = openpyxl.load_workbook(caminho, read_only=True)
    linhas = wb["08_fato_producao_energia"].iter_rows(min_row=4, values_only=True)
    ix = {c: i for i, c in enumerate(next(linhas))}
    cfem_mun_ano, cfem_ano, jan_jul, cfem_sub_ano = defaultdict(int), defaultdict(int), defaultdict(int), defaultdict(int)  # centavos: somas exatas
    registros, muns_ano, titulares_ano = Counter(), defaultdict(set), defaultdict(set)
    producao = defaultdict(lambda: [0.0, 0, set()])  # (SUBSTÂNCIA, município) em 2025 -> [t, centavos, titulares]
    venda, subs_venda, periodos = defaultdict(float), defaultdict(set), set()
    for r in linhas:
        fonte, metrica = r[ix["source_id"]], r[ix["metrica"]]
        if fonte == "SRC_ANM_CFEM":
            ano, mun, periodo = int(r[ix["year"]]), str(r[ix["municipality_id"]]), str(r[ix["periodo_referencia"]])
            substancia = str(r[ix["mineral_name"]] or "NÃO CLASSIFICADO").upper()
            nome_mineral = r[ix["mineral_name"]] or "Não classificado"
            if metrica == "cfem_recolhido":
                c = round(float(r[ix["valor_tratado"]] or 0) * 100)
                periodos.add(periodo)
                cfem_mun_ano[(mun, ano)] += c
                cfem_ano[ano] += c
                cfem_sub_ano[(nome_mineral, ano)] += c
                registros[ano] += 1
                muns_ano[ano].add(mun)
                titulares_ano[ano].add(r[ix["company_id"]])
                if int(periodo[5:7]) <= 7:
                    jan_jul[ano] += c
                if ano == 2025:
                    producao[(substancia, mun)][1] += c
                    producao[(substancia, mun)][2].add(r[ix["company_id"]])
            elif (metrica == "quantidade_comercializada_cfem" and ano == 2025 and r[ix["unidade_padrao"]] == "t"
                  and r[ix["status_validacao"]] != "quantidade_excluida_da_soma_09b"):  # a mesma exclusão da aba 09b
                producao[(substancia, mun)][0] += float(r[ix["valor_tratado"]] or 0)
        elif fonte == "SRC_ANM_PROD_BENEF" and metrica == "valor_venda_beneficiada" and r[ix["uf"]] == "GO":
            v, ano = float(r[ix["valor_tratado"]] or 0), int(r[ix["year"]])
            venda[ano] += v
            if v > 0:
                subs_venda[ano].add(r[ix["mineral_id"]])
    fontes = wb["07_dim_fontes"].iter_rows(min_row=4, values_only=True)
    cab07 = list(next(fontes))
    fontes07 = {r[0]: dict(zip(cab07, r)) for r in fontes if r and r[0]}
    sigmine = fontes07["SRC_ANM_SIGMINE"]
    aba10 = wb["10_cons_municipio_ano"].iter_rows(min_row=4, values_only=True)
    cab10 = list(next(aba10))
    total10 = sum(round(float(r[cab10.index("cfem_recolhido_brl")] or 0) * 100) for r in aba10 if r and r[0])

    def aba(nome):
        it = wb[nome].iter_rows(min_row=4, values_only=True)
        cab = list(next(it))
        return [dict(zip(cab, r)) for r in it if r and r[0] is not None]

    abas = {n: aba(n) for n in ("09_cons_mineral_ano", "10_cons_municipio_ano", "11_cons_empresa_ano_mineral",
                                "12_interface_squad1_squad2", "13_mapas_camadas")}
    wb.close()
    return dict(cfem_mun_ano=cfem_mun_ano, cfem_ano=cfem_ano, jan_jul=jan_jul, cfem_sub_ano=cfem_sub_ano, registros=registros,
                muns_ano=muns_ano, titulares_ano=titulares_ano, producao=producao, venda=venda, subs_venda=subs_venda,
                periodos=sorted(periodos), data_sigmine=sigmine["data_arquivo_local"],
                data_recmin=fontes07.get("SRC_SGB_RECMIN", {}).get("data_arquivo_local"), total10=total10, abas=abas)


def investimento(caminho):
    texto = Path(caminho).read_bytes().decode("cp1252")
    linhas = list(csv.reader(io.StringIO(texto), delimiter=";"))
    cab = linhas[0]
    valores = [i for i, c in enumerate(cab) if c.startswith("Valor")]
    numero = lambda s: float(s.strip().replace(".", "").replace(",", ".")) if s.strip() not in ("", "-") else 0.0
    total = defaultdict(float)
    for r in linhas[1:]:
        if r and r[0].strip() == "GO":
            total[int(r[cab.index("Ano")])] += sum(numero(r[i]) for i in valores)
    return [{"Ano": a, "TOTAL": round(total[a], 2)} for a in sorted(total)]


CLASSES = ["provável", "possível", "sinal"]  # classificacao_maturidade da aba 04, na ordem da legenda
IMPORTANCIA = ["Depósito", "Ocorrência", "Indício", "Indeterminado"]  # importancia do RECMIN (aba 06)


def _vazio(v):
    return v is None or v != v or str(v) in ("", "NaT", "None", "nan")


def pontos(gpkg, catalogo13):
    """Camadas CAM_06 (projetos, aba 04) e CAM_05 (ocorrências, aba 06), gravadas por build_mapas_04_06.py."""
    n13 = {r["camada_id"]: r["n_feicoes"] for r in catalogo13}
    pj = pyogrio.read_dataframe(gpkg, layer="projetos_futuros", read_geometry=False, columns=[
        "project_id", "company_id", "razao_social", "mineral_name", "municipality_id", "latitude", "longitude",
        "classificacao_maturidade", "estagio", "tipo_projeto", "processo_ancora", "qtd_processos", "area_ha", "data_evidencia"])
    assert len(pj) == n13["CAM_06"], ("projetos", len(pj), n13["CAM_06"])
    ordem = {c: i for i, c in enumerate(CLASSES)}
    linhas = []
    for _, r in pj.iterrows():
        # titular só quando é pessoa jurídica identificada pelo CNPJ; pessoa física e nome sem CNPJ ficam fora do pacote
        titular = r["razao_social"] if str(r["company_id"]).startswith("COM_CNPJ_") and not _vazio(r["razao_social"]) and "***" not in str(r["razao_social"]) else None
        linhas.append([r["project_id"], r["processo_ancora"], titular, r["mineral_name"] or "Não classificado", str(r["municipality_id"]),
                       round(float(r["latitude"]), 5), round(float(r["longitude"]), 5), r["classificacao_maturidade"], r["estagio"],
                       str(r["tipo_projeto"]).startswith("brownfield"), int(r["qtd_processos"]),
                       None if _vazio(r["area_ha"]) else round(float(r["area_ha"]), 2), None if _vazio(r["data_evidencia"]) else str(r["data_evidencia"])[:10]])
    linhas.sort(key=lambda x: (ordem.get(x[7], 9), x[3], x[0]))
    projects = {"cols": ["id", "processo", "titular", "mineral", "mun", "lat", "lon", "classe", "estagio", "brownfield", "processos", "area_ha", "evidencia"],
                "rows": linhas}

    oc = pyogrio.read_dataframe(gpkg, layer="ocorrencias_minerais_recmin", read_geometry=False, columns=[
        "occurrence_id", "nome_local", "mineral_names", "substancias_original", "classe_utilitaria", "importancia", "status_economico",
        "municipality_id", "latitude", "longitude", "metodo_geoposicionamento", "categoria_anm_sobreposta", "data_cadastro"])
    assert len(oc) == n13["CAM_05"], ("ocorrências", len(oc), n13["CAM_05"])
    ordem = {c: i for i, c in enumerate(IMPORTANCIA)}
    texto = lambda v: None if _vazio(v) else str(v)
    linhas = []
    for _, r in oc.iterrows():
        categoria = None if _vazio(r["categoria_anm_sobreposta"]) else str(r["categoria_anm_sobreposta"]).split("_", 1)[-1].replace("_", " ")
        linhas.append([r["occurrence_id"], texto(r["nome_local"]), texto(r["mineral_names"]) or texto(r["substancias_original"]),
                       texto(r["classe_utilitaria"]), r["importancia"], texto(r["status_economico"]), str(r["municipality_id"]),
                       round(float(r["latitude"]), 5), round(float(r["longitude"]), 5), texto(r["metodo_geoposicionamento"]), categoria,
                       None if _vazio(r["data_cadastro"]) else str(r["data_cadastro"])[:10]])
    linhas.sort(key=lambda x: (ordem.get(x[4], 9), x[0]))
    occurrences = {"cols": ["id", "local", "substancias", "classe_util", "importancia", "status", "mun", "lat", "lon", "posicionamento",
                            "categoria_anm", "cadastro"], "rows": linhas}
    return projects, occurrences


def graficos(dados, projects, occurrences):
    """Gráficos novos das séries; cada um carrega rótulos, grupos e valores já calculados a partir da planilha."""
    abas, sub_ano, ch = dados["abas"], dados["cfem_sub_ano"], {}
    milhoes = lambda centavos: round(centavos / 1e8, 6)

    # 1) CFEM de 2025 por substância: as 12 maiores e o restante
    s25 = {s: c for (s, a), c in sub_ano.items() if a == 2025 and c}
    top = sorted(s25, key=lambda s: -s25[s])[:12]
    resto = sum(c for s, c in s25.items() if s not in top)
    ch["cfem_substances"] = dict(type="hbar", labels=top + (["outras"] if resto else []), groups=["valor"],
                                 values=[[milhoes(s25[s]) for s in top] + ([milhoes(resto)] if resto else [])], decimals=1, params={"n": len(top)})

    # 2) CFEM por substância e ano: as 6 maiores no acumulado e o restante
    anos = sorted({a for _, a in sub_ano})
    acumulado = Counter()
    for (sub, _), c in sub_ano.items():
        acumulado[sub] += c
    top6 = [sub for sub, _ in sorted(acumulado.items(), key=lambda x: -x[1])[:6]]
    valores = [[milhoes(sub_ano.get((g, a), 0)) for a in anos] for g in top6]
    valores.append([milhoes(sum(c for (sub, aa), c in sub_ano.items() if aa == a and sub not in top6)) for a in anos])
    ch["cfem_substance_years"] = dict(type="stack", labels=[str(a) for a in anos], groups=top6 + ["outras"], values=valores,
                                      partial=["2026"], decimals=1, params={"n": len(top6)})

    # 3) concentração da CFEM de 2025 nos maiores municípios (aba 10) e titulares (aba 11)
    mun25 = sorted((float(r["cfem_recolhido_brl"] or 0) for r in abas["10_cons_municipio_ano"] if r["year"] == 2025), reverse=True)
    emp = defaultdict(float)
    for r in abas["11_cons_empresa_ano_mineral"]:
        if r["year"] == 2025:
            emp[r["company_id"]] += float(r["cfem_recolhido_brl"] or 0)
    total_emp = sum(emp.values())
    total25 = dados["cfem_ano"][2025] / 100
    assert abs(sum(mun25) - total25) < 1 and abs(total_emp - total25) < 1, (sum(mun25), total_emp, total25)
    sem_titular = emp.pop("COM_NAO_IDENTIFICADO", 0.0)
    emp25 = sorted(emp.values(), reverse=True)
    ks = [1, 3, 5, 10, 20]
    ch["cfem_concentration"] = dict(type="group", labels=[f"top{k}" for k in ks], groups=["municipios", "titulares"],
                                    values=[[round(100 * sum(mun25[:k]) / total25, 4) for k in ks], [round(100 * sum(emp25[:k]) / total25, 4) for k in ks]],
                                    decimals=1, params={"pct": round(100 * sem_titular / total25)})

    # 4) produção bruta (ROM) de Goiás por mineral no ano mais recente do AMB (aba 09); co-produtos não se somam
    # ROM de minério associado (bário, cobalto, prata com a massa do minério de outro mineral) não é produção do mineral
    go = [r for r in abas["09_cons_mineral_ano"] if r["uf"] == "GO" and (r["production_t_rom"] or 0) > 0
          and "rom_minerio_associado" not in str(r.get("status_validacao") or "")]
    ano_rom = max(r["year"] for r in go)
    rom = sorted(((r["mineral_name"], float(r["production_t_rom"])) for r in go if r["year"] == ano_rom), key=lambda x: -x[1])[:12]
    ch["rom_minerals"] = dict(type="hbar", labels=[m for m, _ in rom], groups=["valor"], values=[[round(t / 1e6, 4) for _, t in rom]],
                              decimals=1, params={"year": str(ano_rom)})  # texto: o JS formata parâmetros numéricos com separador de milhar

    # 5) produção bruta do AMB aberta por operação (aba 12): com coordenadas, sem poligonal e sem CFEM para ratear
    cob = defaultdict(lambda: [0.0, 0.0, 0.0])
    for r in abas["12_interface_squad1_squad2"]:
        if r["production_basis"] != "ROM" or r["status_validacao"] == "rom_minerio_associado":
            continue
        e, t = cob[r["year"]], float(r["production_t"] or 0)
        if r["nivel_agregacao"] == "estado":
            e[2] += t
        elif not _vazio(r["latitude"]):
            e[0] += t
        else:
            e[1] += t
    anos12 = sorted(a for a in cob if cob[a][0] + cob[a][1] > 0)
    partes = [[round(100 * cob[a][0] / cob[a][2], 6) for a in anos12], [round(100 * cob[a][1] / cob[a][2], 6) for a in anos12]]
    partes.append([round(100 - p0 - p1, 6) for p0, p1 in zip(*partes)])
    assert all(p >= -1e-4 for p in partes[2]), partes[2]
    ch["operation_coverage"] = dict(type="stack", labels=[str(a) for a in anos12], groups=["com_coordenadas", "sem_coordenadas", "sem_cfem"],
                                    values=partes, decimals=1)

    # 6) projetos (aba 04) por mineral e classificação
    pr = [dict(zip(projects["cols"], r)) for r in projects["rows"]]
    top_p = [m for m, _ in sorted(Counter(p["mineral"] for p in pr).items(), key=lambda x: -x[1])[:12]]
    rot = top_p + ["outras"]
    ch["projects_minerals"] = dict(type="hstack", labels=rot, groups=CLASSES, decimals=0, params={"n": len(pr)},
                                   values=[[sum(1 for p in pr if p["classe"] == c and (p["mineral"] == m if m != "outras" else p["mineral"] not in top_p))
                                            for m in rot] for c in CLASSES])

    # 7) ocorrências (aba 06) por substância e importância; ocorrência com várias substâncias conta em cada uma
    oc = [dict(zip(occurrences["cols"], r)) for r in occurrences["rows"]]
    subs = {o["id"]: [x.strip() for x in str(o["substancias"] or "Não informada").split(";") if x.strip()] for o in oc}
    top_o = [x for x, _ in sorted(Counter(x for o in oc for x in subs[o["id"]]).items(), key=lambda x: -x[1])[:12]]
    rot = top_o + ["outras"]
    ch["occurrences_substances"] = dict(type="hstack", labels=rot, groups=IMPORTANCIA, decimals=0,
                                        params={"n": len(oc), "multi": sum(1 for o in oc if len(subs[o["id"]]) > 1)},
                                        values=[[sum((m in subs[o["id"]]) if m != "outras" else sum(1 for x in subs[o["id"]] if x not in top_o)
                                                     for o in oc if o["importancia"] == imp) for m in rot] for imp in IMPORTANCIA])
    return ch


def aneis_municipio(geom, casas=5):
    partes = list(geom.geoms) if geom.geom_type == "MultiPolygon" else [geom]
    aneis = []
    for p in partes:
        for anel in [p.exterior, *p.interiors]:
            pts = []
            for lon, lat in anel.coords:
                ponto = [round(lat, casas), round(lon, casas)]
                if not pts or pts[-1] != ponto:
                    pts.append(ponto)
            if pts[0] != pts[-1]:
                pts.append(pts[0])
            if len(pts) >= 4:
                aneis.append(pts)
    return aneis


def municipios(gpkg, dados, tolerancia):
    mun = pyogrio.read_dataframe(gpkg, layer="municipios_go", columns=["municipality_id", "municipio_nome", "qtd_processos_sigmine"])
    geoms = mun.geometry.values
    try:  # simplifica a cobertura inteira: vizinhos continuam com a mesma fronteira, sem frestas nem sobreposição
        simples = shapely.coverage_simplify(geoms, tolerancia)
    except Exception as e:
        print(f"coverage_simplify indisponível ({e}); usando simplify por polígono", file=sys.stderr)
        simples = shapely.simplify(geoms, tolerancia, preserve_topology=True)
    saida = []
    for (_, m), g in zip(mun.iterrows(), simples):
        code = str(m["municipality_id"])
        centavos = sum(dados["cfem_mun_ano"].get((code, a), 0) for a in ANOS)
        aneis = aneis_municipio(g)
        assert aneis, f"município sem geometria depois da simplificação: {code}"
        saida.append({"code": code, "name": m["municipio_nome"], "rings": aneis,
                      "processes": int(m["qtd_processos_sigmine"] or 0), "cfem_total": centavos / 100, "_centavos": centavos})
    return sorted(saida, key=lambda x: x["code"])


def processos(gpkg, tolerancia):
    pr = pyogrio.read_dataframe(gpkg, layer="processos_minerarios_go",
                                columns=["processo_anm", "fase_atual", "substancias_sigmine", "area_ha_declarada", "area_ha_calculada"])
    originais = shapely.force_2d(pr.geometry.values)
    simples = shapely.simplify(originais, tolerancia, preserve_topology=True)
    ruins = shapely.is_empty(simples) | ~shapely.is_valid(simples)
    simples[ruins] = originais[ruins]
    lon0, lat0, lon1, lat1 = shapely.total_bounds(originais)
    q = lambda lon, lat: (int(round((lon - lon0) / (lon1 - lon0) * 65535)), int(round((lat1 - lat) / (lat1 - lat0) * 65535)))

    def aneis(geom):
        partes = list(geom.geoms) if geom.geom_type == "MultiPolygon" else [geom]
        saida = []
        for p in partes:
            for anel in [p.exterior, *p.interiors]:
                pts = []
                for lon, lat in anel.coords:
                    k = q(lon, lat)
                    if not pts or pts[-1] != k:
                        pts.append(k)
                if len(pts) > 1 and pts[0] == pts[-1]:
                    pts.pop()
                if len(pts) >= 3:
                    saida.append(pts)
        return saida

    xy, inicio, dono = [], [0], []
    for i, (g, orig) in enumerate(zip(simples, originais)):
        lista = aneis(g) or aneis(orig)
        if not lista:  # polígono menor que o passo da quantização (~12 m): mantém o contorno original, mesmo com pontos repetidos
            lista = [[q(lon, lat) for lon, lat in orig.geoms[0].exterior.coords[:-1]] if orig.geom_type == "MultiPolygon"
                     else [q(lon, lat) for lon, lat in orig.exterior.coords[:-1]]]
        for pts in lista:
            for x, y in pts:
                xy.extend((x, y))
            inicio.append(inicio[-1] + len(pts))
            dono.append(i)
    fases = pr["fase_atual"].fillna("").astype(str)
    subs = pr["substancias_sigmine"].fillna("").astype(str)
    d_fase, d_subs = sorted(set(fases)), sorted(set(subs))
    area = pr["area_ha_declarada"].where(pr["area_ha_declarada"].notna(), pr["area_ha_calculada"]).fillna(0.0)
    grupo = [GRUPO_DA_FASE.get(f, 4) for f in fases]
    n = len(pr)
    assert n < 65536 and len(d_fase) < 256 and len(d_subs) < 65536
    resumo = []
    for gi, nome in enumerate(GRUPOS):
        sel = [k for k in range(n) if grupo[k] == gi]
        resumo.append({"grupo": nome, "n": len(sel), "area": round(float(area.iloc[sel].sum()), 2)})
    return {"n": n, "xy": b64(xy, "<u2"), "ringStart": b64(inicio, "<u4"), "ringPoly": b64(dono, "<u2"),
            "g": b64(grupo, "u1"), "fase": b64([d_fase.index(f) for f in fases], "u1"), "subs": b64([d_subs.index(s) for s in subs], "<u2"),
            "area": b64(area.to_numpy(), "<f4"), "processo": "\x01".join(pr["processo_anm"].astype(str)),
            "dFase": d_fase, "dSubs": d_subs, "grupos": GRUPOS, "resumo": resumo,
            "bounds": {"lon0": round(float(lon0), 6), "lon1": round(float(lon1), 6), "lat0": round(float(lat0), 6), "lat1": round(float(lat1), 6)}}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--base", required=True, help="pasta do projeto do Squad 1 (com outputs/, documentacao/ e dados/)")
    ap.add_argument("--planilha", help="planilha consolidada (padrão: <base>/documentacao/prototipo_bases_consolidadas_v19.xlsx)")
    ap.add_argument("--tolerancia-municipios", type=float, default=0.003, help="graus; padrão 0,003 (~330 m)")
    ap.add_argument("--tolerancia-processos", type=float, default=0.0004, help="graus; padrão 0,0004 (~45 m)")
    args = ap.parse_args()
    base = Path(args.base)
    planilha = Path(args.planilha) if args.planilha else base / "documentacao" / "prototipo_bases_consolidadas_v19.xlsx"
    gpkg = base / "outputs" / "mapas" / "minera_goias_mapas_v1.gpkg"
    invest = base / "dados" / "ANM" / "investimento_pesquisa" / "InvestimentoPesquisaMineralUf.csv"
    if not invest.exists():  # arranjo do GitHub: Squad 1/Dados brutos/<fonte>/, ao lado de Squad 1/Bases consolidadas/
        invest = base.parent / "Dados brutos" / "ANM - Investimento em pesquisa mineral" / "InvestimentoPesquisaMineralUf.csv"
    destino = ROOT / "data" / "atlas"
    anterior = json.loads((destino / "atlas.json").read_text(encoding="utf-8"))
    retido = anterior["meta"].get("retained_from_artifact") or {"artifact": anterior["meta"]["artifact"], "sha256": anterior["meta"]["sha256"],
                                                                "periods": {k: anterior["meta"]["periods"][k] for k in ("energy", "dams")}}
    retido["layers"] = MANTIDAS

    dados = ler_planilha(planilha)
    projects, occurrences = pontos(gpkg, dados["abas"]["13_mapas_camadas"])
    charts = graficos(dados, projects, occurrences)
    anos = sorted(dados["cfem_ano"])
    assert set(anos) <= set(ANOS), f"anos de CFEM fora do seletor do atlas: {anos}"
    mun = municipios(gpkg, dados, args.tolerancia_municipios)
    assert len(mun) == 246
    total_mun = sum(m.pop("_centavos") for m in mun)
    total_ano = sum(dados["cfem_ano"].values())
    assert total_mun == total_ano == dados["total10"], (total_mun, total_ano, dados["total10"])
    for m in mun:
        for anel in m["rings"]:
            for lat, lon in anel:
                assert -19.51 < lat < -12.38 and -53.26 < lon < -45.89, (m["code"], lat, lon)
    por_nome = {m["code"]: m["name"] for m in mun}

    prod, agregado = defaultdict(dict), defaultdict(lambda: [0.0, 0, set()])
    for (sub, code), (t, c, titulares) in dados["producao"].items():
        if c <= 0 and t <= 0:
            continue
        prod[sub][code] = [round(t, 2), round(c / 100, 2), len(titulares)]
        agregado[sub][0] += t
        agregado[sub][1] += c
        agregado[sub][2].add(code)
    subs = sorted(({"sub": s, "ton": round(v[0], 2), "cfem": round(v[1] / 100, 2), "municipios": len(v[2])} for s, v in agregado.items()),
                  key=lambda x: (-x["municipios"], -x["cfem"]))
    data_sigmine = "/".join(reversed(str(dados["data_sigmine"]).split("-")))
    ultimo = dados["periodos"][-1]
    packet = {
        "meta": {
            "artifact": "base consolidada do Squad 1 / Estudante 1 — prototipo_bases_consolidadas_v19.xlsx",
            "sha256": sha256(planilha),
            "integrated_on": date.today().isoformat(),
            "status": "snapshot_unvalidated",
            "note": ("Retrato da base consolidada do Squad 1 (v19), gerado por scripts/build_atlas_base.py; não é consulta em tempo real à ANM. "
                     "Energia (CCEE) e barragens (SIGBM) seguem do retrato anterior (eliel.html). Geometrias simplificadas e quantizadas para "
                     "o mapa: não usar como limite cadastral."),
            "sources": ["ANM / CFEM", "Anuário Mineral Brasileiro", "Cadastro Mineiro", "SIGMINE", "SGB — RECMIN", "IBGE — malha municipal 2025",
                        "SIGBM (retrato anterior)", "CCEE (retrato anterior)"],
            "periods": {"cfem": f"{dados['periodos'][0]} a {ultimo}", "production": "2025 — quantidade comercializada declarada na CFEM",
                        "energy": retido["periods"]["energy"], "dams": retido["periods"]["dams"],
                        "processes": f"arquivo do SIGMINE de {data_sigmine}",
                        "projects": f"situação dos processos no arquivo do SIGMINE de {data_sigmine} (aba 04)",
                        "occurrences": "RECMIN do SGB baixado em " + "/".join(reversed(str(dados["data_recmin"] or "")[:10].split("-"))) + " (aba 06)"},
            "base": {"planilha": "Squad 1/Bases consolidadas/documentacao/prototipo_bases_consolidadas_v19.xlsx",
                     "sha256_planilha": sha256(planilha), "sha256_gpkg": sha256(gpkg), "sha256_investimento": sha256(invest)},
            "retained_from_artifact": retido,
        },
        "municipalities": mun,
        "cfem": {"anos": ANOS, "linhas": [{"Município": por_nome[m["code"]], **{str(a): dados["cfem_mun_ano"].get((m["code"], a), 0) / 100 for a in ANOS}}
                                          for m in mun]},
        "production": {"subs": subs, "dados": {s["sub"]: prod[s["sub"]] for s in subs}},
        "energy": anterior["energy"],
        "coef": anterior["coef"],
        "dams": anterior["dams"],
        "cfem_years": [{"Ano": a, "valor": dados["cfem_ano"][a] / 100, "registros": dados["registros"][a],
                        "municipios": len(dados["muns_ano"][a]), "empresas": len(dados["titulares_ano"][a])} for a in anos],
        "cfem_comparable": [{"Ano": a, "v": dados["jan_jul"][a] / 100} for a in anos],
        "energy_months": anterior["energy_months"],
        "beneficiated": [{"ano": a, "venda_rs": round(dados["venda"][a], 2), "substancias": len(dados["subs_venda"][a])} for a in sorted(dados["venda"])],
        "investment": investimento(invest),
        "projects": projects,
        "occurrences": occurrences,
        "charts": charts,
    }
    proc = processos(gpkg, args.tolerancia_processos)
    for nome, obj in [("atlas.json", packet), ("processes.json", proc)]:
        (destino / nome).write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{len(mun)} municípios · CFEM {dados['periodos'][0]} a {ultimo}: R$ {total_ano / 100:,.2f} · {len(subs)} substâncias em 2025 · "
          f"{proc['n']} processos ({len(base64.b64decode(proc['ringPoly'])) // 2} anéis)")
    print(f"  {len(projects['rows'])} projetos · {len(occurrences['rows'])} ocorrências · gráficos: {', '.join(charts)}")
    for nome in ("atlas.json", "processes.json"):
        print(f"  {nome}: {(destino / nome).stat().st_size / 1e6:.2f} MB")


if __name__ == "__main__":
    main()
