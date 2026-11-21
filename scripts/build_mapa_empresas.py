# -*- coding: utf-8 -*-
"""Pacote do mapa de empresas (data/empresas/mapa_empresas.json), lido pela aba Empresas pela API autenticada (/api/empresas/mapa).

    python scripts/build_mapa_empresas.py

Para cada empresa (pessoa jurídica) com processo minerário em Goiás ou CFEM recolhida:
  - onde ela minera: o centro de cada processo (polígonos do SIGMINE do atlas, data/atlas/processes.json), com fase, substância e área;
  - o ponto da empresa no mapa: o processo dela que mais recolheu CFEM em 2022–2026; sem CFEM, o maior título de lavra; senão, o maior processo;
  - arrecadação: CFEM por ano e por mineral (data/panorama/panorama.json, tabela cfem);
  - energia: carga na CCEE em Goiás por ano, pelo CNPJ raiz (tabela ccee do mesmo pacote);
  - notícias: matérias do radar de notícias (public/data/noticias/meses) cujo título cita a empresa por um nome conhecido (ALIASES)
    ou pela razão social inteira.
Produção e coeficiente energético vêm do bloco "estimada" de data/empresas/empresas.json, que a página já carrega.

Nomeia empresas: fica atrás da API autenticada, nunca em public/. Pessoa física não entra (não tem nome publicado).
"""
import base64
import glob
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
REPO = Path(__file__).resolve().parents[1]
PANORAMA = REPO / "data" / "panorama" / "panorama.json"
PROCESSOS = REPO / "data" / "atlas" / "processes.json"
NOTICIAS = REPO / "public" / "data" / "noticias" / "meses"
SAIDA = REPO / "data" / "empresas" / "mapa_empresas.json"

# Nomes pelos quais a imprensa chama a empresa (grupo, marca, operação). Só nomes que não confundem com outra coisa.
ALIASES = {
    "86902053": ["Lundin", "Mineração Maracá", "Chapada (GO)", "mina de Chapada"],
    "42445403": ["Serra Grande", "AngloGold", "Aura Minerals"],
    "42799486": ["Hochschild", "Mara Rosa", "Amarillo"],
    "26108898": ["CMOC", "Niobras", "Copebras"],
    "33931486": ["Mosaic"],
    "42184226": ["Anglo American", "Codemin"],
    "15104599": ["SAMA", "Eternit", "Cana Brava"],
    "08842895": ["Serra Verde"],
    "61409892": ["CBA", "Companhia Brasileira de Alumínio"],
    "01637895": ["Votorantim Cimentos"],
    "62258884": ["InterCement", "Intercement"],
    "00057240": ["Ciplan"],
}
LAVRA = {"CONCESSÃO DE LAVRA", "LICENCIAMENTO", "LAVRA GARIMPEIRA", "REGISTRO DE EXTRAÇÃO"}
GRUPO = {"CONCESSÃO DE LAVRA": 0, "LICENCIAMENTO": 0, "LAVRA GARIMPEIRA": 0, "REGISTRO DE EXTRAÇÃO": 0,
         "AUTORIZAÇÃO DE PESQUISA": 1, "DIREITO DE REQUERER A LAVRA": 1,
         "REQUERIMENTO DE LAVRA": 2, "REQUERIMENTO DE PESQUISA": 2, "REQUERIMENTO DE LICENCIAMENTO": 2,
         "REQUERIMENTO DE LAVRA GARIMPEIRA": 2, "REQUERIMENTO DE REGISTRO DE EXTRAÇÃO": 2}
GRUPOS = ["lavra", "pesquisa", "requerimento", "outros"]


def sem_acento(s):
    return "".join(c for c in unicodedata.normalize("NFD", str(s)) if unicodedata.category(c) != "Mn").upper()


def b64(s, dtype):
    return np.frombuffer(base64.b64decode(s), dtype=dtype)


pan = json.loads(PANORAMA.read_text(encoding="utf-8"))
dims = pan["dims"]
emp, fases, mins, muns = dims["emp"], dims["fase"], dims["min"], dims["mun"]

# --------------------------------------------------------------------------------- centro de cada processo (polígonos do atlas)
pr = json.loads(PROCESSOS.read_text(encoding="utf-8"))
xy = b64(pr["xy"], "<u2").astype(float).reshape(-1, 2)
inicio, dono = b64(pr["ringStart"], "<u4"), b64(pr["ringPoly"], "<u2")
bd = pr["bounds"]
soma, cont = np.zeros((pr["n"], 2)), np.zeros(pr["n"])
for k, p in enumerate(dono):
    pts = xy[inicio[k]:inicio[k + 1]]
    soma[p] += pts.sum(axis=0)
    cont[p] += len(pts)
cent = soma / np.maximum(cont, 1)[:, None]
lon = bd["lon0"] + cent[:, 0] / 65535 * (bd["lon1"] - bd["lon0"])
lat = bd["lat1"] - cent[:, 1] / 65535 * (bd["lat1"] - bd["lat0"])
pos = {proc: (round(float(lat[i]), 5), round(float(lon[i]), 5)) for i, proc in enumerate(pr["processo"].split("\x01")) if cont[i]}

# ------------------------------------------------------------------------------------------------------- processos por empresa
pcols = {c: i for i, c in enumerate(pan["proc"]["cols"])}
processos, por_emp = [], defaultdict(list)
for r in pan["proc"]["rows"]:
    e = r[pcols["emp"]]
    if e < 0 or emp[e][3] != "pj" or not emp[e][1] or r[pcols["processo"]] not in pos:
        continue
    la, lo = pos[r[pcols["processo"]]]
    fase = fases[r[pcols["fase"]]]
    linha = [e, la, lo, r[pcols["fase"]], GRUPO.get(fase, 3), r[pcols["min"]], r[pcols["mun"]], round(r[pcols["area_ha"]] or 0, 1),
             r[pcols["processo"]], round(r[pcols["cfem_2022_2026"]] or 0, 2)]
    processos.append(linha)
    por_emp[e].append(linha)

# --------------------------------------------------------------------------------------------------- CFEM e CCEE por empresa
ccols = {c: i for i, c in enumerate(pan["cfem"]["cols"])}
cfem_ano, cfem_min, cfem_mun = defaultdict(Counter), defaultdict(Counter), defaultdict(Counter)
for r in pan["cfem"]["rows"]:
    e = r[ccols["emp"]]
    if e >= 0 and emp[e][3] == "pj" and emp[e][1]:
        cfem_ano[e][r[ccols["ano"]]] += r[ccols["valor"]]
        cfem_min[e][r[ccols["min"]]] += r[ccols["valor"]]
        if r[ccols["mun"]] >= 0:
            cfem_mun[e][r[ccols["mun"]]] += r[ccols["valor"]]
eecols = {c: i for i, c in enumerate(pan["ccee"]["cols"])}
raiz_de_ce = [c[0] for c in dims["ce"]]
ccee = defaultdict(Counter)  # raiz -> ano -> MWh
ccee_meses = defaultdict(set)
for r in pan["ccee"]["rows"]:
    ano = r[eecols["mes"]] // 100
    ccee[raiz_de_ce[r[eecols["empresa"]]]][ano] += r[eecols["total_mwh"]]
    ccee_meses[ano].add(r[eecols["mes"]])

# ---------------------------------------------------------------------------------------------------------------- notícias
noticias = []
for arq in sorted(glob.glob(str(NOTICIAS / "*.json"))):
    for it in json.loads(Path(arq).read_text(encoding="utf-8")).get("itens", []):
        # só o que é do Brasil ou de Goiás: a mesma empresa tem operações no exterior (AngloGold na Colômbia, CMOC no Congo)
        if it.get("title") and it.get("link") and (str(it.get("brasil")) == "1" or str(it.get("regional")) == "1"):
            noticias.append(it)
vistos = set()
noticias = [n for n in sorted(noticias, key=lambda n: n.get("published_at") or "", reverse=True)
            if not (sem_acento(n["title"])[:80] in vistos or vistos.add(sem_acento(n["title"])[:80]))]  # a mesma matéria em vários agregadores
tit = [sem_acento(n["title"]) for n in noticias]


def noticias_de(raiz, nome):
    termos = [sem_acento(a) for a in ALIASES.get(raiz, [])]
    nome_limpo = re.sub(r"\s+(LTDA\.?|S\.?/?A\.?|EIRELI|ME|EPP)$", "", sem_acento(nome)).strip()
    if len(nome_limpo) >= 12:
        termos.append(nome_limpo)
    out = []
    for n, tt in zip(noticias, tit):
        if any(re.search(r"(?<![A-Z0-9])" + re.escape(x) + r"(?![A-Z0-9])", tt) for x in termos):
            out.append({"data": (n.get("published_at") or "")[:10], "titulo": n["title"], "link": n["link"], "fonte": n.get("fonte") or ""})
        if len(out) >= 15:
            break
    return out


# ----------------------------------------------------------------------------------------------------------------- empresas
empresas = []
for e in sorted(set(por_emp) | set(cfem_ano)):
    cid, nome, raiz, _ = emp[e]
    ps = por_emp.get(e, [])
    if ps:
        ponto = max(ps, key=lambda p: (p[9], p[4] == 0, p[7]))
        la, lo = ponto[1], ponto[2]
    else:
        la = lo = None
    n_g = Counter(p[4] for p in ps)
    empresas.append({
        "i": e, "id": cid, "nome": nome, "cnpj_raiz": raiz, "lat": la, "lon": lo,
        "cfem_total": round(sum(cfem_ano[e].values()), 2),
        "cfem_ano": {str(a): round(v, 2) for a, v in sorted(cfem_ano[e].items())},
        "cfem_mineral": [[mins[m][1] if m >= 0 else "não informado", round(v, 2)] for m, v in cfem_min[e].most_common(6)],
        "cfem_municipios": [muns[m][1] for m, _ in cfem_mun[e].most_common(8)],
        "ccee_mwh": {str(a): round(v, 1) for a, v in sorted(ccee.get(raiz, {}).items())},
        "titulos": {GRUPOS[g]: n_g.get(g, 0) for g in range(4)},
        "area_lavra_ha": round(sum(p[7] for p in ps if p[4] == 0), 1),
        "area_pesquisa_ha": round(sum(p[7] for p in ps if p[4] == 1), 1),
        "noticias": noticias_de(raiz, nome),
    })
empresas.sort(key=lambda x: -x["cfem_total"])

pacote = {
    "meta": {"built_on": date.today().isoformat(), "gerado_por": "scripts/build_mapa_empresas.py",
             "fontes": ["data/atlas/processes.json (SIGMINE)", "data/panorama/panorama.json (CFEM, Cadastro Mineiro, CCEE)",
                        "public/data/noticias (radar de notícias)"],
             "ccee_meses": {str(a): len(m) for a, m in sorted(ccee_meses.items())},
             "nota": ("Ponto da empresa: o processo dela que mais recolheu CFEM em 2022–2026 (sem CFEM, o maior título de lavra; senão, o maior "
                      "processo). Centro do processo = média dos vértices do polígono do SIGMINE. CCEE: carga do CNPJ raiz em Goiás, sem anualizar.")},
    "dims": {"fase": fases, "grupo": GRUPOS, "min": [m[1] for m in mins], "mun": [m[1] for m in muns]},
    "processos": {"cols": ["empresa", "lat", "lon", "fase", "grupo", "min", "mun", "area_ha", "processo", "cfem_2022_2026"], "rows": processos},
    "empresas": empresas,
}
SAIDA.parent.mkdir(parents=True, exist_ok=True)
SAIDA.write_text(json.dumps(pacote, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
com_noticia = sum(1 for x in empresas if x["noticias"])
print(f"empresas: {len(empresas)} (com ponto {sum(1 for x in empresas if x['lat'] is not None)}, com CFEM {sum(1 for x in empresas if x['cfem_total'] > 0)}, "
      f"com notícia {com_noticia}) · processos: {len(processos)}")
print(f"SALVO: {SAIDA} ({SAIDA.stat().st_size / 1e3:.0f} kB)")
