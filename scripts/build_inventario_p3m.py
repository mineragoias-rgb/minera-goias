# -*- coding: utf-8 -*-
"""Inventário das camadas do P3M em `Squad 1/P3M` (inventario_p3m.csv) e organização por pasta temática.

    python scripts/build_inventario_p3m.py                        # refaz o inventário a partir do que está no repositório
    python scripts/build_inventario_p3m.py --mover                # também põe cada zip na pasta temática dele (git mv)
    python scripts/build_inventario_p3m.py --verificar            # só confere: sai com 1 se o inventário ou alguma pasta destoar
    python scripts/build_inventario_p3m.py --atualizar-catalogo   # baixa de novo o catálogo do site (precisa de internet)

As pastas seguem a organização do Squad 1 (Eliel), encaixada na classificação do próprio site P3M (categoria → tema →
subtema, em `Squad 1/P3M/catalogo_p3m/categorias.json`):

    1- Geologia            Geologia (mapa estadual, afloramentos, petrografia, estruturas, geologia da América do Sul…),
                           Geocronologia e Hidrogeologia; as Folhas 1:100.000 (cartas de anomalias) também, como o Squad 1 pôs
    2- Geofísica           Geofísica (levantamentos aerogeofísicos)
    3- Geoquímica          Geoquímica
    4- Recursos minerais   Recursos Minerais e Principais Classes de Commodities (ocorrências, distritos, potencial, PDAC, lítio,
                           urânio, gemas e diamante)
    5- Atividade mineira   Economia Mineral (processos, minas ativas, guias, servidões, reservas garimpeiras, barragens de
                           mineração), Ativos Minerários do SGB e empreendimentos mineiros
    6- Cartografia         Conhecimento do Território (limites, regiões, hidrografia, uso do solo, socioeconômico, áreas especiais)
    7- Pesquisa            mapas índices de mapeamento, levantamentos litoestratigráficos, furos de sondagem e modelamento 3D
    8- Infraestrutura      Infraestrutura (energia, combustíveis, transportes)

O inventário guarda o que não se recalcula — data em que o arquivo foi baixado, extensão pedida ao site e URL do download — e
refaz o resto a cada execução: classificação, metadados do site, registros e tamanho dos zips, registros em Goiás do recorte.
"""
import argparse
import csv
import html
import io
import json
import re
import struct
import subprocess
import sys
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
P3M = RAIZ / "Squad 1" / "P3M"
ORIGINAL, RECORTADO = P3M / "Original", P3M / "Recortado pelo polígono de Goiás"
CATALOGO = P3M / "catalogo_p3m"
INVENTARIO = P3M / "inventario_p3m.csv"
INDICE_RECORTE = RECORTADO / "_indice_recorte.csv"

PASTAS = {1: "1- Geologia", 2: "2- Geofísica", 3: "3- Geoquímica", 4: "4- Recursos minerais", 5: "5- Atividade mineira",
          6: "6- Cartografia", 7: "7- Pesquisa", 8: "8- Infraestrutura"}
# Camadas que a regra geral põe em outro lugar: as do mapa geológico de Goiás, que o site junta num subtema só, vão para o
# assunto de cada uma (como o Squad 1 organizou), e as que o Squad 1 já tinha posto numa pasta continuam lá.
FIXAS = {
    "vw_cprm_go_rec_min": 4, "vw_cprm_go_pot_min": 4, "vw_cprm_go_geoquim": 3, "vw_cprm_go_emprend_mineiro": 5,
    "vw_cprm_cartas_anomalia": 1, "vw_cprm_furos_sondagem": 7, "vw_cprm_modelamento_3d": 7,
    "vw_cprm_geoq_b_d": 3, "GO_UF_2024": 6,
}
TITULOS_FORA_DO_P3M = {"GO_UF_2024": "Limite estadual de Goiás (IBGE, malha 2024)"}
RESUMOS_FORA_DO_P3M = {"GO_UF_2024": "Polígono do estado usado para recortar todas as camadas da pasta Recortado. Não vem do P3M."}
SUBTEMAS_PESQUISA = {"Mapas Índices de Mapeamento Geológico", "Levantamentos Litoestratigráficos Sistemáticos"}
POR_TEMA = {"Geologia": 1, "Geocronologia": 1, "Hidrogeologia": 1, "Geofísica": 2, "Geoquímica": 3, "Recursos Minerais": 4}
POR_CATEGORIA = {"Principais Classes de Commodities": 4, "Economia Mineral": 5, "Ativos Minerários SGB": 5,
                 "Conhecimento do Território": 6, "Infraestrutura": 8}
ORDEM_CATEGORIAS = ["Conhecimento Geocientífico", "Economia Mineral", "Ativos Minerários SGB", "Principais Classes de Commodities",
                    "Infraestrutura", "Conhecimento do Território"]
ORGAO_POR_PREFIXO = [("vw_cprm_", "SGB (CPRM)"), ("vw_crpm_", "SGB (CPRM)"), ("vw_ibge_", "IBGE"), ("vw_anm_", "ANM"),
                     ("mvw_processos", "ANM (SIGMINE)"), ("mvw_minas", "ANM"), ("mvw_guia", "ANM"), ("mvw_ativos_sgb", "SGB"),
                     ("vw_epe_", "EPE"), ("vw_anp_", "ANP"), ("vw_antaq_", "ANTAQ"), ("vw_ana_", "ANA"), ("vw_funai_", "FUNAI"),
                     ("vw_incra_", "INCRA"), ("vw_mma_", "MMA"), ("vw_icmbio_", "ICMBio"), ("vw_iphan_", "IPHAN"),
                     ("vw_embrapa_", "Embrapa"), ("vw_infra_", "Ministério dos Transportes"), ("GO_UF_", "IBGE")]
CAMPOS = ["camada", "titulo_p3m", "pasta_tematica", "categoria_p3m", "tema_p3m", "subtema_p3m", "outras_classificacoes_p3m",
          "orgao", "geometria", "extensao_original", "registros_original", "registros_goias", "fiapos_removidos_no_recorte",
          "data_download", "data_atualizacao_sgb", "fonte_data_sgb", "arquivo_original", "mb_original", "arquivo_recortado",
          "mb_recortado", "url_download", "metadado_url", "resumo"]
GUARDADOS = ("data_download", "extensao_original", "url_download")


def git(*args):
    return subprocess.run(["git", "-C", str(RAIZ), *args], check=True, capture_output=True).stdout.decode("utf-8")


def camada_do_zip(caminho):
    m = re.search(r"\(((?:vw|mvw)_\w+)\)\s*(?:- parte \d+ de \d+)?\.zip$", caminho.name)
    if m:
        return m.group(1)
    with zipfile.ZipFile(caminho) as z:
        return next(Path(n).stem for n in z.namelist() if n.lower().endswith(".shp"))


def registros(caminho):
    with zipfile.ZipFile(caminho) as z:
        return sum(struct.unpack("<I", z.read(n)[4:8])[0] for n in z.namelist() if n.lower().endswith(".dbf"))


def texto_limpo(t):
    """O resumo do site vem em HTML: tira as marcas e as entidades (&ccedil; vira ç)."""
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t or ""))).strip()


def data_iso(d):
    if not d:
        return ""
    m = re.match(r"(\d{2})/(\d{2})/(\d{4})", d)
    return f"{m.group(3)}-{m.group(2)}-{m.group(1)}" if m else d[:10]


def ler_catalogo():
    categorias = json.loads((CATALOGO / "categorias.json").read_text(encoding="utf-8"))
    camadas = json.loads((CATALOGO / "camadas.json").read_text(encoding="utf-8"))
    opendata = json.loads((CATALOGO / "opendata_datasets.json").read_text(encoding="utf-8"))
    onde, meta = {}, {}
    for c in categorias:
        for t in c["temas"]:
            grupos = [(None, t.get("layers") or [])] + [(s, s["layers"]) for s in t["subtema"]]
            for s, layers in grupos:
                for l in layers:
                    nome = l["layername"].split(":")[-1]
                    onde.setdefault(nome, []).append((c["nm_categoria"], t["nm_tema"], s["nm_subtema"] if s else ""))
                    m = {**(l.get("metadados") or {}), "link_shapefile": l.get("link_shapefile"), "titulo": l.get("layertitle")}
                    if nome not in meta or (m.get("data") and not meta[nome].get("data")):
                        meta[nome] = m
    for l in camadas:
        nome = l["layername"].split(":")[-1]
        meta.setdefault(nome, {}).setdefault("titulo", l["layertitle"])
        meta[nome]["metadado_url"] = l.get("metadado_url")
        meta[nome]["geometria"] = (l.get("layer_order") or {}).get("layertype", "").replace("layer ", "")
    return onde, meta, opendata


def classificar(nome, onde):
    lugares = sorted(set(map(tuple, onde.get(nome, []))),
                     key=lambda o: (ORDEM_CATEGORIAS.index(o[0]) if o[0] in ORDEM_CATEGORIAS else 9, o[1], o[2]))
    principal = lugares[0] if lugares else ("", "", "")
    if nome in FIXAS:
        pasta = FIXAS[nome]
    elif nome.startswith("vw_cprm_go_"):
        pasta = 1
    elif principal[1] == "Geologia" and principal[2] in SUBTEMAS_PESQUISA:
        pasta = 7
    elif principal[0] == "Conhecimento Geocientífico" and principal[1] in POR_TEMA:
        pasta = POR_TEMA[principal[1]]
    elif principal[0] in POR_CATEGORIA:
        pasta = POR_CATEGORIA[principal[0]]
    else:
        raise SystemExit(f"{nome}: sem regra de pasta (classificação do site: {principal})")
    return PASTAS[pasta], principal, lugares[1:]


def atualizar_catalogo():
    def baixar(url):
        return json.loads(urllib.request.urlopen(url, timeout=120).read())
    CATALOGO.mkdir(exist_ok=True)
    for nome, url in (("categorias.json", "https://p3mgeo.sgb.gov.br/api/categorias/?lang=pt-BR"),
                      ("camadas.json", "https://p3mgeo.sgb.gov.br/api/camadas/?lang=pt-BR")):
        (CATALOGO / nome).write_text(json.dumps(baixar(url), ensure_ascii=False, separators=(",", ":")), encoding="utf-8", newline="\n")
    nomes = sorted({camada_do_zip(z) for z in P3M.rglob("*.zip")} - {"GO_UF_2024"})
    opendata = {}
    for n in nomes:
        d = baixar("https://opendata.sgb.gov.br/api/v2/datasets?" + urllib.parse.urlencode({"filter{alternate}": f"p3m:{n}"}))
        if d.get("datasets"):
            r = d["datasets"][0]
            opendata[n] = {k: r.get(k) for k in ("title", "abstract", "date", "date_type", "last_updated", "created",
                                                 "attribution", "maintenance_frequency", "srid", "detail_url")}
    (CATALOGO / "opendata_datasets.json").write_text(json.dumps(opendata, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    print(f"catálogo atualizado: {len(nomes)} camadas consultadas, {len(opendata)} com ficha no portal do SGB")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--mover", action="store_true", help="põe cada zip na pasta temática dele, com git mv")
    ap.add_argument("--verificar", action="store_true", help="não grava nada; sai com 1 se algo destoar")
    ap.add_argument("--atualizar-catalogo", action="store_true", help="baixa de novo o catálogo do site P3M")
    args = ap.parse_args()
    if args.atualizar_catalogo:
        atualizar_catalogo()
    onde, meta, opendata = ler_catalogo()

    anteriores = {}
    if INVENTARIO.exists():
        with open(INVENTARIO, encoding="utf-8-sig", newline="") as f:
            anteriores = {r["camada"]: r for r in csv.DictReader(f, delimiter=";")}
    with open(INDICE_RECORTE, encoding="utf-8-sig", newline="") as f:
        recorte = {r["arquivo"]: r for r in csv.DictReader(f, delimiter=";")}

    originais, recortados = {}, {}
    for z in sorted(ORIGINAL.rglob("*.zip")):
        originais.setdefault(camada_do_zip(z), []).append(z)
    for z in sorted(RECORTADO.rglob("*.zip")):
        recortados.setdefault(camada_do_zip(z), []).append(z)

    linhas, fora_do_lugar = [], []
    for nome in sorted(set(originais) | set(recortados)):
        pasta, (cat, tema, sub), outras = classificar(nome, onde)
        m, od, ant = meta.get(nome, {}), opendata.get(nome) or {}, anteriores.get(nome, {})
        orig, rec = originais.get(nome, []), recortados.get(nome, [])
        for z in orig + rec:
            if z.parent.name != pasta:
                fora_do_lugar.append((z, (ORIGINAL if z in orig else RECORTADO) / pasta / z.name))
        orgao = m.get("organizacao") or next((o for p, o in ORGAO_POR_PREFIXO if nome.startswith(p)), "")
        data_sgb, fonte_data = (od["last_updated"][:10], "portal de dados do SGB (última atualização)") if od.get("last_updated") \
            else ((data_iso(m["data"]), "catálogo do P3M (data do metadado)") if m.get("data") else ("", "o SGB não publica"))
        rel = lambda ps: ";".join(p.relative_to(P3M).as_posix() for p in ps)
        mb = lambda ps: f"{sum(p.stat().st_size for p in ps) / 1e6:.1f}"
        r_rec = [recorte[z.name] for z in rec if z.name in recorte]
        linhas.append({
            "camada": nome, "titulo_p3m": m.get("titulo") or od.get("title") or TITULOS_FORA_DO_P3M.get(nome, ""), "pasta_tematica": pasta,
            "categoria_p3m": cat, "tema_p3m": tema, "subtema_p3m": sub,
            "outras_classificacoes_p3m": " | ".join(" / ".join(x for x in o if x) for o in outras),
            "orgao": orgao, "geometria": m.get("geometria", ""),
            "extensao_original": ant.get("extensao_original", ""),
            "registros_original": sum(registros(z) for z in orig) if orig else "",
            "registros_goias": sum(int(r["registros_em_goias"]) for r in r_rec) if r_rec else
                               (sum(registros(z) for z in orig) if nome in TITULOS_FORA_DO_P3M else (0 if orig and not rec else "")),
            "fiapos_removidos_no_recorte": sum(int(r["fiapos_de_divisa_removidos"]) for r in r_rec) if r_rec else "",
            "data_download": ant.get("data_download", ""), "data_atualizacao_sgb": data_sgb, "fonte_data_sgb": fonte_data,
            "arquivo_original": rel(orig), "mb_original": mb(orig) if orig else "",
            "arquivo_recortado": rel(rec), "mb_recortado": mb(rec) if rec else "",
            "url_download": ant.get("url_download") or m.get("link_shapefile") or "",
            "metadado_url": m.get("metadado_url") or "",
            "resumo": texto_limpo(m.get("resumo") or od.get("abstract") or "") or RESUMOS_FORA_DO_P3M.get(nome, ""),
        })

    faltando = [l["camada"] for l in linhas if not all(l[c] for c in ("data_download", "extensao_original"))]
    if faltando:
        sys.exit(f"sem data de download ou extensão registradas no inventário: {faltando}")

    saida = io.StringIO()
    w = csv.DictWriter(saida, fieldnames=CAMPOS, delimiter=";", lineterminator="\r\n")
    w.writeheader()
    w.writerows(linhas)
    novo = saida.getvalue()
    atual = open(INVENTARIO, encoding="utf-8-sig", newline="").read() if INVENTARIO.exists() else ""

    if args.verificar:
        problemas = []
        if novo != atual:
            problemas.append("inventario_p3m.csv desatualizado (rode scripts/build_inventario_p3m.py)")
        problemas += [f"{z.relative_to(P3M).as_posix()} deveria estar em {d.parent.relative_to(P3M).as_posix()}" for z, d in fora_do_lugar]
        print("\n".join(problemas) or f"ok: {len(linhas)} camadas, todas na pasta temática")
        sys.exit(1 if problemas else 0)

    if fora_do_lugar and not args.mover:
        print(f"aviso: {len(fora_do_lugar)} zips fora da pasta temática; rode com --mover")
    if args.mover:
        for z, destino in fora_do_lugar:
            destino.parent.mkdir(parents=True, exist_ok=True)
            git("mv", str(z.relative_to(RAIZ)), str(destino.relative_to(RAIZ)))
        if fora_do_lugar:
            print(f"movidos: {len(fora_do_lugar)} zips; refazendo o inventário com os caminhos novos")
            return main_sem_mover()
    INVENTARIO.write_text(novo, encoding="utf-8-sig", newline="")
    por_pasta = {}
    for l in linhas:
        por_pasta[l["pasta_tematica"]] = por_pasta.get(l["pasta_tematica"], 0) + 1
    print(f"{INVENTARIO.relative_to(RAIZ)}: {len(linhas)} camadas — " + ", ".join(f"{p} {n}" for p, n in sorted(por_pasta.items())))


def main_sem_mover():
    sys.argv = [a for a in sys.argv if a not in ("--mover", "--atualizar-catalogo")]
    main()


if __name__ == "__main__":
    main()
