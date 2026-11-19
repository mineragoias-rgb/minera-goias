# -*- coding: utf-8 -*-
"""Energia da CCEE nos projetos do Radar da Frente 6 (Squad 1 / Estudante 1 — Frente 1).

    python "Squad 1/Bases consolidadas/base_consolidada_work/scripts/gerar_energia_radar.py"

Entrada:
  - Squad 1/Auditoria e qualidade/insumos/radar_frente6_projetos.csv — retrato dos 29 projetos do Radar da Frente 6
    (tirado de radar_minera_goias.html, rodada 2, 9 a 13/11/2026);
  - Squad 1/dados/CCEE/parcela_carga_consumo_<ano>_GO.csv — consumo mensal por parcela de carga.

Regra de ligação: a carga da CCEE vai para o projeto com a mesma raiz de CNPJ (8 dígitos) e o mesmo município. Quando a
mesma empresa tem mais de um projeto no município (ex.: Chapada e as expansões dela), a carga vai para o que está em
operação; obras e projetos anunciados ainda não consomem como mina. Carga de uma empresa do radar num município sem projeto
dela fica registrada sem projeto (para revisão), não é empurrada para outro município.

Saída: Squad 1/Auditoria e qualidade/radar_frente6_energia_ccee.csv — uma linha por projeto, com consumo de 2025 (12 meses),
demanda média (MWh ÷ horas do período) e o parcial de 2026; mais as cargas sem projeto.
"""
import csv
import os
import sys
import unicodedata
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8")
AQUI = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(AQUI, "..", "..", "..", ".."))
AUD = os.path.join(REPO, "Squad 1", "Auditoria e qualidade")
RADAR = os.path.join(AUD, "insumos", "radar_frente6_projetos.csv")
CCEE = os.path.join(REPO, "Squad 1", "dados", "CCEE", "parcela_carga_consumo_{}_GO.csv")
SAIDA = os.path.join(AUD, "radar_frente6_energia_ccee.csv")
OPERANDO = {"operação", "suspenso/paralisado"}  # paralisado entra: a carga de 2025 é de quando operava


def norm(s):
    s = unicodedata.normalize("NFKD", str(s or "")).encode("ascii", "ignore").decode().upper()
    return " ".join(s.replace("-", " ").split())


with open(RADAR, encoding="utf-8-sig") as f:
    projetos = list(csv.DictReader(f, delimiter=";"))
por_chave = defaultdict(list)
raizes = set()
for p in projetos:
    raiz = "".join(ch for ch in (p["cnpj"] or "") if ch.isdigit())[:8]
    if len(raiz) == 8:
        raizes.add(raiz)
        por_chave[(raiz, norm(p["municipio"]))].append(p)

# Cargas com produto definido pela tabela de coprodutos (pacote do Squad 2): a sigla da carga diz o produto (CMOC: cargas
# "NIOBIO" -> nióbio, "COPEBRAS" -> fosfato) e a carga compartilhada (rejeitos) é rateada pelo valor. O projeto é o da mesma
# empresa com essa substância principal.
COPROD = os.path.join(REPO, "Squad 1", "Bases consolidadas", "documentacao", "pacote_squad2", "coprodutos_rateio_valor_2025.csv")
MIN2SUB = {"MIN_021": "nióbio", "MIN_049": "fosfato", "MIN_011": "cobre", "MIN_023": "ouro", "MIN_022": "níquel"}
partes = defaultdict(list)  # (raiz, sigla) -> [(substância, parcela)]
if os.path.exists(COPROD):
    with open(COPROD, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f, delimiter=";"):
            if r["carga_ccee"] != "todas as cargas do CNPJ" and r["mineral_id"] in MIN2SUB:
                partes[(r["cnpj_raiz"], r["carga_ccee"])].append((MIN2SUB[r["mineral_id"]], float(r["parcela_valor"])))
proj_da_raiz = defaultdict(list)
for p in projetos:
    raiz = "".join(ch for ch in (p["cnpj"] or "") if ch.isdigit())[:8]
    if len(raiz) == 8:
        proj_da_raiz[raiz].append(p)


def destino(raiz, cidade, sigla):
    """[(projeto, fração da carga, observação)] ou ([], motivo)."""
    ops_raiz = [p for p in proj_da_raiz[raiz] if p["estagio_projeto"] in OPERANDO]
    if (raiz, sigla) in partes:
        alvo = []
        for sub, parcela in partes[(raiz, sigla)]:
            ps = [p for p in ops_raiz if p["substancia_principal"] == sub]
            if not ps:  # coproduto sem projeto próprio no radar (ex.: ouro de Chapada): fica no projeto que o tem como secundária
                ps = [p for p in ops_raiz if sub in (p["substancias_secundarias"] or "")]
            if len(ps) != 1:
                return [], f"carga de {sub} sem projeto único da empresa"
            alvo.append((ps[0], parcela, "carga por produto (tabela de coprodutos)" if parcela == 1 else f"carga compartilhada: {parcela:.1%} pelo valor"))
        juntos = defaultdict(float)
        for p, parcela, _ in alvo:
            juntos[p["id_projeto"]] += parcela
        if len(juntos) == 1 and len(alvo) > 1:  # todos os produtos no mesmo projeto: a carga é dele inteira
            return [(alvo[0][0], 1.0, "carga com coproduto no mesmo projeto (energia inteira; rateio por valor na tabela de coprodutos)")], ""
        return alvo, ""
    cands = por_chave.get((raiz, norm(cidade)), [])
    ops = [p for p in cands if p["estagio_projeto"] in OPERANDO] or cands
    if len(ops) == 1:
        return [(ops[0], 1.0, "")], ""
    if ops:
        return [], "vários projetos em operação no município"
    if len(ops_raiz) == 1 and len(cidades_ccee[raiz]) == 1:  # empresa com um projeto e todas as cargas numa cidade só: mesmo complexo
        return [(ops_raiz[0], 1.0, f"carga em {cidade.title()}, projeto cadastrado em {ops_raiz[0]['municipio']}")], ""
    return [], "sem projeto da empresa no município"


cidades_ccee = defaultdict(set)
for _ano in ("2025", "2026"):
    if os.path.exists(CCEE.format(_ano)):
        with open(CCEE.format(_ano), encoding="utf-8-sig") as f:
            for r in csv.DictReader(f, delimiter=";"):
                cidades_ccee[r["CNPJ_CARGA"][:8]].add(norm(r["CIDADE"]))
energia = defaultdict(lambda: defaultdict(float))   # id_projeto -> ano -> MWh
notas = defaultdict(set)
meses = defaultdict(lambda: defaultdict(set))
cargas = defaultdict(set)
sem_projeto = defaultdict(float)
sem_projeto_ano = defaultdict(lambda: defaultdict(float))
for ano in ("2025", "2026"):
    caminho = CCEE.format(ano)
    if not os.path.exists(caminho):
        continue
    with open(caminho, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f, delimiter=";"):
            raiz = r["CNPJ_CARGA"][:8]
            if raiz not in raizes:
                continue
            sigla = r["SIGLA_PARCELA_CARGA"].strip()
            mwh = float(r["CONSUMO_TOTAL"] or 0)
            alvo, motivo = destino(raiz, r["CIDADE"], sigla)
            if not alvo:
                sem_projeto[(raiz, r["CIDADE"], sigla, motivo)] += 0.0
                sem_projeto_ano[(raiz, r["CIDADE"], sigla, motivo)][ano] += mwh
                continue
            for p, frac, nota in alvo:
                pid = p["id_projeto"]
                energia[pid][ano] += mwh * frac
                meses[pid][ano].add(r["MES_REFERENCIA"])
                cargas[pid].add(sigla if frac == 1 else f"{sigla} ({frac:.1%})")
                if nota:
                    notas[pid].add(nota)

CAMPOS = ["id_projeto", "nome_projeto", "empresa_operadora", "cnpj", "municipio", "estagio_projeto", "substancia_principal",
          "cargas_ccee", "consumo_mwh_2025", "meses_2025", "demanda_media_mw_2025", "consumo_mwh_2026_parcial", "meses_2026",
          "fonte", "observacao"]
linhas = []
for p in projetos:
    pid = p["id_projeto"]
    e25, m25 = energia[pid].get("2025"), sorted(meses[pid].get("2025", ()))
    e26, m26 = energia[pid].get("2026"), sorted(meses[pid].get("2026", ()))
    if e25 is not None and len(m25) < 12:
        obs = f"2025 com {len(m25)} meses na CCEE"
    elif e25 is None and p["estagio_projeto"] in OPERANDO:
        obs = "sem carga na CCEE: mercado cativo (distribuidora) ou CNPJ diferente do da carga"
    elif e25 is None:
        obs = "projeto ainda não opera"
    else:
        obs = ""
    obs = "; ".join(filter(None, [obs] + sorted(notas[pid])))
    linhas.append(dict(
        id_projeto=pid, nome_projeto=p["nome_projeto"], empresa_operadora=p["empresa_operadora"], cnpj=p["cnpj"],
        municipio=p["municipio"], estagio_projeto=p["estagio_projeto"], substancia_principal=p["substancia_principal"],
        cargas_ccee="; ".join(sorted(cargas[pid])), consumo_mwh_2025=round(e25, 3) if e25 is not None else "",
        meses_2025=len(m25) or "", demanda_media_mw_2025=round(e25 / (8760 * len(m25) / 12), 2) if e25 else "",
        consumo_mwh_2026_parcial=round(e26, 3) if e26 is not None else "",
        meses_2026=f"{m26[0][:4]}-{m26[0][4:]} a {m26[-1][:4]}-{m26[-1][4:]}" if m26 else "",
        fonte="CCEE — parcela de carga e consumo (CONSUMO_TOTAL), Squad 1/dados/CCEE" if e25 is not None or e26 is not None else "",
        observacao=obs))
for (raiz, cidade, sigla, motivo), por_ano in sorted(sem_projeto_ano.items()):
    linhas.append(dict(id_projeto="", nome_projeto="", empresa_operadora=proj_da_raiz[raiz][0]["empresa_operadora"] if proj_da_raiz[raiz] else "",
                       cnpj=raiz, municipio=cidade.title(), estagio_projeto="", substancia_principal="", cargas_ccee=sigla,
                       consumo_mwh_2025=round(por_ano["2025"], 3) if "2025" in por_ano else "", meses_2025="", demanda_media_mw_2025="",
                       consumo_mwh_2026_parcial=round(por_ano["2026"], 3) if "2026" in por_ano else "", meses_2026="", fonte="CCEE",
                       observacao=f"carga sem projeto no radar: {motivo} (outra unidade da empresa)"))
with open(SAIDA, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=CAMPOS, delimiter=";", lineterminator="\r\n")
    w.writeheader()
    w.writerows(linhas)
com = sum(1 for l in linhas if l["id_projeto"] and l["consumo_mwh_2025"] != "")
print(f"SALVO: {SAIDA} — {com} de {len(projetos)} projetos com consumo de 2025; "
      f"{sum(1 for l in linhas if not l['id_projeto'])} cargas sem projeto")
for l in linhas:
    print(f"  {l['id_projeto'] or '—':7s} {l['nome_projeto'][:34]:34s} {l['municipio'][:16]:16s} {l['consumo_mwh_2025']!s:>14} MWh "
          f"{l['demanda_media_mw_2025']!s:>7} MW  {l['observacao'][:60]}")
