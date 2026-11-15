# -*- coding: utf-8 -*-
"""Estimativa da produção de 2026 pela CFEM (Squad 1 / Estudante 1 — Frente 1).

    python "Squad 1/Bases consolidadas/base_consolidada_work/scripts/gerar_estimativa_2026.py"

O AMB de 2026 só sai em 2027; a CFEM é mensal. Para cada mineral e empresa da aba 12:

    produção 2026 estimada = produção 2025 (aba 12) × CFEM do período comparável de 2026 ÷ CFEM do mesmo período de 2025

- período comparável: os meses de 2026 já fechados na CFEM (hoje jan–jun), contra os mesmos meses de 2025;
- medida: quantidade comercializada em t quando o mineral tem quantidade em t nos dois anos (o preço não entra); senão R$
  (aí a variação inclui preço, e a linha avisa);
- um semestre não vê o que acontece depois dele: a paralisação da Mosaic em Catalão (jul/2026), por exemplo, fica fora.

Grava documentacao/pacote_squad2/estimativa_2026_pela_cfem.csv. É chamado no fim de gerar_pacote_squad2.py.
"""
import csv
import os
import sys
from collections import Counter, defaultdict

sys.stdout.reconfigure(encoding="utf-8")
from caminhos import BASE, arquivo  # noqa: E402

PACOTE = os.path.join(BASE, "documentacao", "pacote_squad2")
INTERFACE = os.path.join(PACOTE, "interface_squad1_squad2.csv")
CFEM = arquivo("dados/ANM/cfem/CFEM_Arrecadacao_2022_2026_GO.csv")
BASE_ANO, ANO = "2025", "2026"
MIN_LINHAS_MES = 0.5  # um mês está fechado quando tem pelo menos metade das linhas do mesmo mês do ano-base


def num_br(s):
    s = (s or "").strip()
    if not s or s == "-":
        return 0.0
    return float(s.replace(".", "").replace(",", ".")) if ("," in s and "." in s) else float(s.replace(",", "."))


def proc_canon(p, a):
    """Mesmo formato da aba 12 (canon_processo da Base 3): número sem zeros à esquerda / ano."""
    num = "".join(ch for ch in str(p) if ch.isdigit()).lstrip("0") or "0"
    return f"{num}/{''.join(ch for ch in str(a) if ch.isdigit())[:4]}"


# --- aba 12: produção de 2025 por operação e o mineral de cada processo ------------------------------------------------
prod = defaultdict(float)            # (mineral_id, company_id, base) -> t em 2025
nome_min, nome_emp = {}, {}
minerais_do_proc = defaultdict(set)
estado = {}                          # (mineral_id, base) -> t do estado em 2025
with open(INTERFACE, encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        if r["year"] != BASE_ANO:
            continue
        nome_min[r["mineral_id"]] = r["mineral_name"]
        if r["nivel_agregacao"] == "estado":
            estado[(r["mineral_id"], r["production_basis"])] = float(r["production_t"] or 0)
            continue
        prod[(r["mineral_id"], r["company_id"], r["production_basis"])] += float(r["production_t"] or 0)
        minerais_do_proc[r["processo_anm"]].add(r["mineral_id"])

# --- CFEM: substância -> mineral, aprendido dos processos da aba 12 -------------------------------------------
linhas = []
with open(CFEM, encoding="cp1252") as f:
    for r in csv.DictReader(f, delimiter=";"):
        if r["Ano"] in (BASE_ANO, ANO):
            linhas.append(r)
votos = defaultdict(Counter)
for r in linhas:
    ms = minerais_do_proc.get(proc_canon(r["Processo"], r["AnoDoProcesso"]))
    for m in ms or ():  # processo com dois minerais vota meio para cada; a substância fica com o mineral mais votado
        votos[r["Substância"].strip().upper()][m] += 1 / len(ms)
sub2min = {s: min(c.items(), key=lambda kv: (-round(kv[1], 9), kv[0]))[0] for s, c in votos.items()}  # empate: menor mineral_id (estável entre execuções)

# meses de 2026 já fechados
n_mes = Counter((r["Ano"], int(r["Mês"])) for r in linhas)
meses = [m for m in range(1, 13) if n_mes[(BASE_ANO, m)] and n_mes[(ANO, m)] >= MIN_LINHAS_MES * n_mes[(BASE_ANO, m)]]
meses = [m for i, m in enumerate(meses, 1) if m == i]  # só a sequência contínua a partir de janeiro
if not meses:
    raise SystemExit("CFEM de 2026 sem nenhum mês fechado")
periodo = f"jan–{['', 'jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez'][meses[-1]]}"

# --- CFEM por mineral e empresa, período comparável ------------------------------------------------------------------
# A quantidade comercializada da CFEM muda de base entre declarações (ex.: Maracá, cobre: 90 mil t no 1º semestre de 2025 e
# 1,75 Mt no de 2026 com R$ +46%; amianto declarado em 4 t). Por isso a tonelada só é usada quando o R$/t da empresa no
# mineral fica estável entre os dois períodos (±30%); senão a variação sai do R$ e inclui preço.
ESTAVEL = 0.30
t = defaultdict(float)
rs = defaultdict(float)
for r in linhas:
    if int(r["Mês"]) not in meses:
        continue
    proc = proc_canon(r["Processo"], r["AnoDoProcesso"])
    ms = minerais_do_proc.get(proc, set())
    mid = sub2min.get(r["Substância"].strip().upper())
    if mid is None or (ms and mid not in ms):
        continue
    raiz = "".join(ch for ch in r["CPF_CNPJ"] if ch.isdigit())
    cid = f"COM_CNPJ_{raiz[:8]}" if len(raiz) == 14 else "COM_NAO_IDENTIFICADO"
    rs[(mid, cid, r["Ano"])] += num_br(r["ValorRecolhido"])
    if r["UnidadeDeMedida"].strip() == "t":
        t[(mid, cid, r["Ano"])] += num_br(r["QuantidadeComercializada"])

CAMPOS = ["nivel", "mineral_id", "mineral_name", "company_id", "production_basis", "producao_2025_t", "medida_cfem", "cfem_periodo",
          "cfem_2025_periodo", "cfem_2026_periodo", "variacao_pct", "producao_2026_estimada_t", "observacao"]
saida = []


def razao(mid, cid):
    a, b = rs.get((mid, cid, BASE_ANO), 0.0), rs.get((mid, cid, ANO), 0.0)
    qa, qb = t.get((mid, cid, BASE_ANO), 0.0), t.get((mid, cid, ANO), 0.0)
    if a <= 0:
        return None, "", 0.0, 0.0
    if qa > 0 and qb > 0 and abs((b / qb) / (a / qa) - 1) <= ESTAVEL:
        return qb / qa, "t comercializadas (R$/t estável)", qa, qb
    return b / a, "R$ recolhidos (inclui variação de preço)", a, b


for (mid, base), p in sorted(estado.items(), key=lambda kv: nome_min[kv[0][0]]):
    if p <= 0:
        continue
    filhos, soma_est, soma_base, usou = [], 0.0, 0.0, Counter()
    for (m2, cid, b2), pe in sorted(prod.items(), key=lambda kv: -kv[1]):
        if m2 != mid or b2 != base or pe <= 0:
            continue
        k2, med2, a2, bb2 = razao(mid, cid)
        if k2 is None:
            obs, est = "empresa sem CFEM no período de 2025: mantida a produção de 2025", pe
        elif k2 == 0:
            obs, est = "sem CFEM no período de 2026: parou de vender ou deixou de recolher", 0.0
        else:
            obs, est = "", pe * k2
        usou[med2.split(" ")[0] or "mantida"] += pe
        soma_est += est
        soma_base += pe
        filhos.append(dict(nivel="empresa", mineral_id=mid, mineral_name=nome_min[mid], company_id=cid, production_basis=base,
                           producao_2025_t=round(pe, 3), medida_cfem=med2, cfem_periodo=periodo, cfem_2025_periodo=round(a2, 2),
                           cfem_2026_periodo=round(bb2, 2), variacao_pct=round(100 * (k2 - 1), 1) if k2 is not None else "",
                           producao_2026_estimada_t=round(est, 3), observacao=obs))
    if not filhos:
        continue  # mineral sem abertura por operação na aba 12
    k = soma_est / soma_base if soma_base else None
    saida.append(dict(nivel="estado", mineral_id=mid, mineral_name=nome_min[mid], company_id="", production_basis=base,
                      producao_2025_t=round(p, 3), medida_cfem="; ".join(f"{m}: {100 * v / soma_base:.0f}% da produção" for m, v in usou.most_common()),
                      cfem_periodo=periodo, cfem_2025_periodo="", cfem_2026_periodo="", variacao_pct=round(100 * (k - 1), 1) if k is not None else "",
                      producao_2026_estimada_t=round(p * k, 3) if k is not None else "",
                      observacao="soma das estimativas por empresa; onde a medida é R$, a variação inclui preço"))
    saida.extend(filhos)

with open(os.path.join(PACOTE, "estimativa_2026_pela_cfem.csv"), "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=CAMPOS, delimiter=";", lineterminator="\r\n")
    w.writeheader()
    w.writerows(saida)
print(f"SALVO: {PACOTE} (estimativa_2026_pela_cfem.csv: {len(saida)} linhas; período {periodo} de 2026 contra 2025)")
for s in saida:
    if s["nivel"] == "estado" and s["production_basis"] == "beneficiada" and s["mineral_id"] in ("MIN_005", "MIN_011", "MIN_022", "MIN_033", "MIN_049"):
        print(f"  {s['mineral_name']}: {s['variacao_pct']}% ({s['medida_cfem']})")
