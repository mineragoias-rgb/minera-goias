# -*- coding: utf-8 -*-
"""Gera data/comex/comex.json e data/comex/comex.csv a partir de comex/base_curada.json e do bruto em comex/bruto/.

    python3 comex/coleta.py            # baixa o bruto do Comex Stat
    python3 scripts/build_comex_base.py

O que esta base é: o que foi DESPACHADO na aduana, por mineral de Goiás, mês a mês, em dólares FOB e em quilos.
O que ela não é: produção, consumo, faturamento nem estoque. Uma mina pode produzir num ano e embarcar no outro;
um embarque pode sair por Goiás sem ter sido lavrado em Goiás. A base diz despacho, e só.

O gerador recusa a base — em vez de publicar um número torto — quando:
  · uma NCM curada não aparece no bruto (a curadoria descolou da fonte);
  · um mineral do recorte crítico perdeu o vínculo com a aba Mercado;
  · um mineral marcado como do vocabulário do projeto não está nas bases de produção ou de projetos;
  · o bruto traz uma NCM que a curadoria não mapeia;
  · soma de meses e total do ano não batem.
"""
import argparse
import csv
import json
import subprocess
import sys
import unicodedata
from collections import defaultdict
from datetime import date
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ap = argparse.ArgumentParser(description="Gera o pacote data/comex a partir do bruto do Comex Stat.")
ap.add_argument("--repo", default=str(Path(__file__).resolve().parents[1]))
ap.add_argument("--saida")
args = ap.parse_args()
REPO = Path(args.repo)
SAIDA = Path(args.saida) if args.saida else REPO / "data" / "comex" / "comex.json"
VERSAO = "v1"
problemas = []


def erro(msg):
    """Cada problema aparece uma vez: a mesma NCM errada repete em 90 meses e isso esconderia os outros problemas."""
    if msg not in problemas:
        problemas.append(msg)


def carrega(rel):
    caminho = REPO / rel
    if not caminho.exists():
        erro(f"arquivo ausente: {rel} — rode antes `python3 comex/coleta.py`")
        return None
    return json.loads(caminho.read_text(encoding="utf-8"))


def dobra(texto):
    """Minúsculas sem acento: comparar 'Níquel' com 'niquel laterítico' não pode depender de acentuação."""
    return "".join(c for c in unicodedata.normalize("NFD", str(texto).lower())
                   if unicodedata.category(c) != "Mn")


curada = carrega("comex/base_curada.json")
coleta = carrega("comex/bruto/coleta.json")
bruto = {"export": carrega("comex/bruto/mensal_export.json"),
         "import": carrega("comex/bruto/mensal_import.json")}
destinos_bruto = carrega("comex/bruto/destinos.json")
municipios_bruto = carrega("comex/bruto/municipios.json")
if problemas:
    print("\n".join(problemas), file=sys.stderr)
    raise SystemExit(1)

# ------------------------------------------------------------------- mapa NCM → mineral, e o que a curadoria promete
# A chave é a NCM, não o par NCM+fluxo: uma NCM é sempre o mesmo mineral, entre ou saia. O `fluxo_principal` da curadoria
# diz qual sentido interessa àquele mineral, e o pacote publica os sentidos que o bruto realmente trouxe.
de_ncm = {}
for m in curada["minerais"]:
    for n in m["ncms"]:
        if n["codigo"] in de_ncm:
            erro(f"NCM {n['codigo']} mapeada duas vezes")
        de_ncm[n["codigo"]] = (m["mineral"], n["forma"])

# ------------------------------------------------------------------- a curadoria tem de continuar presa às outras bases
mercado = carrega("public/data/mercado/mercado_v1.json")
texto_mercado = dobra(json.dumps(mercado.get("operacoes", []), ensure_ascii=False)) if mercado else ""
producao = carrega("data/producao/producao.json")
projetos = carrega("data/projetos/projetos.json")
vocabulario = set()
if producao:
    vocabulario |= {r["mineral"] for r in producao["registros"] if r.get("mineral")}
if projetos:
    vocabulario |= {p["mineral"] for p in projetos["projetos"] if p.get("mineral")}
    vocabulario |= {p["outros"] for p in projetos["projetos"] if p.get("outros") not in (None, "NA")}

CLASSES = set(curada["criticidade"]["classes"])
for m in curada["minerais"]:
    if m["criticidade"] not in CLASSES:
        erro(f"{m['mineral']}: criticidade '{m['criticidade']}' fora das classes declaradas")
    if m["criticidade"] == "marco_estadual":
        termo = m.get("termo_no_mercado")
        if not termo:
            erro(f"{m['mineral']}: entra no recorte crítico sem dizer por qual termo o marco estadual o nomeia")
        elif dobra(termo) not in texto_mercado:
            erro(f"{m['mineral']}: o termo '{termo}' sumiu das operações da aba Mercado — o recorte crítico perdeu o "
                 f"fundamento declarado e a base não deve mais chamá-lo de crítico")
    if m["no_vocabulario_do_projeto"] and m["mineral"] not in vocabulario:
        erro(f"{m['mineral']}: marcado como do vocabulário do projeto, mas não aparece nem na base de produção "
             f"nem na de projetos")
    if not m["no_vocabulario_do_projeto"] and m["mineral"] in vocabulario:
        erro(f"{m['mineral']}: marcado como fora do vocabulário do projeto, mas as outras bases o registram")

# ------------------------------------------------------------------- série mensal
ANO_PUBLICADO, MES_PUBLICADO = coleta["publicado_ate"]["ano"], coleta["publicado_ate"]["mes"]
serie = defaultdict(lambda: [0, 0])
descricao_oficial = {}
vistos = set()
for fluxo, linhas in bruto.items():
    for r in linhas:
        vistos.add(r["coNcm"])
        if r["coNcm"] not in de_ncm:
            erro(f"o bruto traz a NCM {r['coNcm']} e a curadoria não a mapeia")
            continue
        mineral, _ = de_ncm[r["coNcm"]]
        descricao_oficial[r["coNcm"]] = r["ncm"]
        ano, mes = int(r["year"]), int(r["monthNumber"])
        bucket = serie[(mineral, fluxo, ano, mes)]
        bucket[0] += int(r["metricFOB"])
        bucket[1] += int(r["metricKG"])
for codigo in de_ncm:
    if codigo not in vistos:
        erro(f"a curadoria mapeia a NCM {codigo}, mas ela não aparece no bruto baixado")

if problemas:
    print("A base não foi gerada:", file=sys.stderr)
    print("\n".join(" · " + p for p in problemas), file=sys.stderr)
    raise SystemExit(1)

linhas_serie = [{"mineral": k[0], "fluxo": k[1], "ano": k[2], "mes": k[3],
                 "usd_fob": v[0], "kg": v[1]}
                for k, v in sorted(serie.items())]

# ------------------------------------------------------------------- agregado anual, com o ano parcial marcado na cara
anual = defaultdict(lambda: {"usd_fob": 0, "kg": 0, "meses": set()})
for l in linhas_serie:
    b = anual[(l["mineral"], l["fluxo"], l["ano"])]
    b["usd_fob"] += l["usd_fob"]
    b["kg"] += l["kg"]
    b["meses"].add(l["mes"])
linhas_anual = []
for (mineral, fluxo, ano), b in sorted(anual.items()):
    meses = len(b["meses"])
    linhas_anual.append({
        "mineral": mineral, "fluxo": fluxo, "ano": ano,
        "usd_fob": b["usd_fob"], "kg": b["kg"],
        # Preço implícito, não cotação: é o valor declarado dividido pelo peso declarado, teor e forma incluídos.
        "usd_por_kg": round(b["usd_fob"] / b["kg"], 4) if b["kg"] else None,
        "meses_com_embarque": meses,
        # O ano só é cheio quando o Comex Stat já publicou dezembro dele. Sem isso, nenhuma comparação com outro ano vale.
        "ano_completo": ano < ANO_PUBLICADO or (ano == ANO_PUBLICADO and MES_PUBLICADO == 12),
        "meses_publicados": 12 if ano < ANO_PUBLICADO else (MES_PUBLICADO if ano == ANO_PUBLICADO else 0),
    })

# conferência: mês a mês tem de somar o mesmo que o ano
for l in linhas_anual:
    soma = sum(s["usd_fob"] for s in linhas_serie
               if s["mineral"] == l["mineral"] and s["fluxo"] == l["fluxo"] and s["ano"] == l["ano"])
    if soma != l["usd_fob"]:
        erro(f"{l['mineral']} {l['fluxo']} {l['ano']}: soma dos meses ({soma}) difere do total do ano ({l['usd_fob']})")

# ------------------------------------------------------------------- destinos
destinos = defaultdict(lambda: [0, 0])
for r in destinos_bruto:
    if r["coNcm"] not in de_ncm:
        continue
    mineral, _ = de_ncm[r["coNcm"]]
    b = destinos[(mineral, int(r["year"]), r["country"])]
    b[0] += int(r["metricFOB"])
    b[1] += int(r["metricKG"])
total_destino = defaultdict(int)
for (mineral, ano, _), v in destinos.items():
    total_destino[(mineral, ano)] += v[0]
linhas_destinos = [{"mineral": k[0], "ano": k[1], "pais": k[2], "usd_fob": v[0], "kg": v[1],
                    "participacao": round(v[0] / total_destino[(k[0], k[1])], 6) if total_destino[(k[0], k[1])] else None}
                   for k, v in sorted(destinos.items())]

# conferência: destinos de um mineral num ano têm de somar a exportação daquele mineral naquele ano
anual_export = {(l["mineral"], l["ano"]): l["usd_fob"] for l in linhas_anual if l["fluxo"] == "export"}
for (mineral, ano), soma in total_destino.items():
    esperado = anual_export.get((mineral, ano))
    if esperado is not None and soma != esperado:
        erro(f"{mineral} {ano}: destinos somam {soma} e a exportação do ano é {esperado} — "
             f"período que cruza anos devolve só o acumulado; cada ano tem de ser um pedido")

# ------------------------------------------------------------------- municípios (granularidade: capítulo da NCM, não mineral)
capitulos = curada["capitulos"]
municipios = defaultdict(lambda: [0, 0])
for r in municipios_bruto:
    municipios[(r["noMunMinsgUf"], r["chapterCode"], int(r["year"]))][0] += int(r["metricFOB"])
    municipios[(r["noMunMinsgUf"], r["chapterCode"], int(r["year"]))][1] += int(r["metricKG"])
linhas_municipios = [{"municipio": k[0].replace(" - GO", ""), "capitulo": k[1],
                      "capitulo_nome": capitulos.get(k[1], "NA"), "ano": k[2],
                      "usd_fob": v[0], "kg": v[1]}
                     for k, v in sorted(municipios.items())]

if problemas:
    print("A base não foi gerada:", file=sys.stderr)
    print("\n".join(" · " + p for p in problemas), file=sys.stderr)
    raise SystemExit(1)

# ------------------------------------------------------------------- minerais, com a descrição oficial vinda da própria API
minerais = []
for m in curada["minerais"]:
    minerais.append({
        "mineral": m["mineral"],
        "criticidade": m["criticidade"],
        "termo_no_mercado": m.get("termo_no_mercado"),
        "no_vocabulario_do_projeto": m["no_vocabulario_do_projeto"],
        "operacoes_em_goias": m["operacoes_em_goias"],
        "fluxo_principal": m["fluxo_principal"],
        "fluxos": sorted({l["fluxo"] for l in linhas_serie if l["mineral"] == m["mineral"]}),
        "ncms": [{"codigo": n["codigo"], "fluxo_principal": n["fluxo_principal"], "forma": n["forma"],
                  "descricao_oficial": descricao_oficial.get(n["codigo"], "NA"),
                  "capitulo": n["codigo"][:2]} for n in m["ncms"]],
    })

pacote = {
    "meta": {
        "built_on": date.today().isoformat(),
        "versao_base": VERSAO,
        "gerado_por": "scripts/build_comex_base.py",
        "curadoria": curada["curadoria"],
        "fonte": curada["fonte"],
        "uf": curada["uf"],
        "coleta": coleta,
        "periodo": [min(l["ano"] for l in linhas_anual), max(l["ano"] for l in linhas_anual)],
        "publicado_ate": {"ano": ANO_PUBLICADO, "mes": MES_PUBLICADO},
        "criticidade": curada["criticidade"],
        "regras": curada["regras"],
        "o_que_a_base_mede": "Despacho aduaneiro declarado à Receita Federal: valor FOB em dólares e peso líquido em "
                             "quilos, por NCM, por mês, com Goiás como UF da operação.",
        "o_que_a_base_nao_mede": [
            "Produção: o que embarca num mês pode ter sido lavrado meses antes, e o que foi lavrado pode não ter embarcado.",
            "Consumo e faturamento: o valor FOB é o preço declarado na saída, não a receita reconhecida pela empresa.",
            "Teor: o peso é do produto embarcado, não do metal contido. O ferro-níquel não é níquel, e o concentrado de cobre não é cobre.",
            "Mercado interno: o fosfato de Catalão abastece a indústria nacional de fertilizantes e por isso quase não aparece na exportação.",
            "Empresa: o Comex Stat não publica quem exportou. A atribuição a uma operação nesta base vem do município e das outras bases do projeto, nunca da aduana.",
        ],
        "avisos": [
            "Ano parcial: o último ano só tem os meses que o Comex Stat publicou. O campo `ano_completo` diz quando o ano fecha; comparar um ano parcial com um ano cheio superestima a queda.",
            "US$/kg é preço implícito — valor declarado dividido por peso declarado. Muda com teor, forma e contrato, e não é cotação de mercado.",
            "Município só existe por capítulo da NCM: a API recusa detalhar município por produto. O capítulo 72 reúne ferro-níquel e ferro-nióbio, que só se separam porque saem de municípios diferentes.",
        ],
    },
    "minerais": minerais,
    "serie": linhas_serie,
    "anual": linhas_anual,
    "destinos": linhas_destinos,
    "municipios": linhas_municipios,
}

SAIDA.parent.mkdir(parents=True, exist_ok=True)
SAIDA.write_text(json.dumps(pacote, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

csv_caminho = SAIDA.with_suffix(".csv")
with csv_caminho.open("w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f, delimiter=";")
    w.writerow(["mineral", "criticidade", "fluxo", "ano", "mes", "usd_fob", "kg", "usd_por_kg"])
    criticidade = {m["mineral"]: m["criticidade"] for m in minerais}
    for l in linhas_serie:
        w.writerow([l["mineral"], criticidade[l["mineral"]], l["fluxo"], l["ano"], l["mes"],
                    l["usd_fob"], l["kg"], round(l["usd_fob"] / l["kg"], 4) if l["kg"] else ""])

def curto(caminho):
    """--saida pode apontar para fora do repositório (o teste de reprodutibilidade faz isso): relative_to erraria ali."""
    try:
        return caminho.relative_to(REPO)
    except ValueError:
        return caminho


print(f"{curto(SAIDA)}: {len(minerais)} minerais, {len(linhas_serie)} linhas mensais, "
      f"{len(linhas_anual)} anuais, {len(linhas_destinos)} destinos, {len(linhas_municipios)} municípios "
      f"({SAIDA.stat().st_size/1e3:.0f} kB)")
print(f"{curto(csv_caminho)}: {len(linhas_serie)} linhas ({csv_caminho.stat().st_size/1e3:.0f} kB)")
