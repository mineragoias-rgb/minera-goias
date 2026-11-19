# -*- coding: utf-8 -*-
"""Frente 8 · família de índices e cenários: IVFM (vulnerabilidade fiscal), IPMM (pipeline), tipologia, cenários de estresse e prospectivos.
Limiares de validação fixados ANTES de rodar (ver LIM). Uso: python3 run_extra.py -> extra.json"""
import sys, json
import numpy as np, pandas as pd
from scipy import stats
sys.path.insert(0, __file__.rsplit("/", 1)[0] if "/" in __file__ else ".")
exec(compile(open(__file__.replace("run_extra.py", "run_indices.py"), encoding="utf-8").read().split('R["empates_base"] = ties')[0], "setup", "exec"))
import cenarios as cn
X = {"seed": SEED}
LIM = {"estab": .80, "loo": .85, "nulo": .20, "indep": .60, "pred_ivfm": .20, "pred_ipmm": .30, "univ_min": 250_000}
X["limiares"] = LIM
nm = ind.nome

# ============================================================ IVFM: vulnerabilidade fiscal mineral
U = ind[ind.cfem_med >= LIM["univ_min"]].copy()
cm = c[c.mun.isin(U.index)].copy(); cm["t"] = (cm.ano - ANOS[0]) * 12 + cm.mes - 1
mt = cm.groupby(["mun", "t"]).valor.sum().unstack(fill_value=0).reindex(columns=range(NA * 12), fill_value=0)
U["cv_mes"] = (mt.std(axis=1, ddof=0) / mt.mean(axis=1)).reindex(U.index)
U["hhi_sub"] = 1 - U.div_sub; U["hhi_emp"] = 1 - U.div_emp
SV = {"Dependência": [dict(col="cfem_pib", log=True)], "Concentração": [dict(col="hhi_sub"), dict(col="hhi_emp")], "Volatilidade": [dict(col="cv_mes", log=True)]}
WV = ic.weights_equal(SV.keys())
iv, nzv = ic.compute_index(U, SV, WV); iv["nome"] = nm[U.index]
dv, _ = ic.build_dims(U, SV)
X["ivfm"] = {"n": int(len(U)), "linhas": [{"nome": iv.nome[i], "pos": int(iv.posicao[i]), "nota": float(iv.nota[i]), **{k: float(dv.loc[i, k] * 100) for k in dv.columns}} for i in iv.sort_values("posicao").index]}
mcv, _ = ic.mc_weights(U, SV, WV, n=5000, conc=None, seed=SEED)
sv = ic.rank_summary(mcv, iv.posicao, 10)
X["ivfm"]["mc"] = {"amplitude_mediana": float(sv.amplitude.median()), "top10_p90": int((sv.prob_topk >= .9).sum()),
                   "intervalos": [{"nome": nm[i], "base": int(iv.posicao[i]), "p5": float(sv.p5[i]), "p50": float(sv.p50[i]), "p95": float(sv.p95[i]), "top10": float(sv.prob_topk[i])} for i in iv.sort_values("posicao").index[:12]]}
# validação IVFM
def ivfm_de(cj, n_anos, Uidx):
    d = cn.ind_from_cfem(cj, n_anos, ind[["nome", "pop", "pib", "cod", "lavra", "prelavra"]]); d = d.loc[d.index.intersection(Uidx)].copy()
    t = cj[cj.mun.isin(d.index)].copy(); t["t"] = (t.ano - t.ano.min()) * 12 + t.mes - 1
    m_ = t.groupby(["mun", "t"]).valor.sum().unstack(fill_value=0).reindex(columns=range(n_anos * 12), fill_value=0)
    d["cv_mes"] = (m_.std(axis=1, ddof=0) / m_.mean(axis=1)).reindex(d.index)
    d["hhi_sub"] = 1 - d.div_sub; d["hhi_emp"] = 1 - d.div_emp
    return d
a1, a2 = ivfm_de(c[c.ano <= 2023], 2, U.index), ivfm_de(c[c.ano >= 2024], 2, U.index)
com = a1.index.intersection(a2.index)
r1 = ic.compute_index(a1.loc[com], SV, WV)[0].nota; r2 = ic.compute_index(a2.loc[com], SV, WV)[0].nota
est = float(stats.spearmanr(r1, r2)[0])
v1 = c[c.ano <= 2023].groupby("mun").valor.sum().reindex(com).fillna(0) / 2; v2 = c[c.ano >= 2024].groupby("mun").valor.sum().reindex(com).fillna(0) / 2
mov = ((v2 - v1).abs() / v1).replace([np.inf], np.nan)
ok_ = mov.notna(); pred = float(stats.spearmanr(r1[ok_], mov[ok_])[0])
rng = np.random.default_rng(SEED + 11); nul = []
for _ in range(500):
    sh = U.copy()
    for k in ["cfem_pib", "hhi_sub", "hhi_emp", "cv_mes"]: sh[k] = rng.permutation(sh[k].values)
    nul.append(stats.spearmanr(ic.compute_index(sh, SV, WV)[0].nota, iv.nota)[0])
loo = {}
for dn, lst in SV.items():
    for k, it in enumerate(lst):
        sp_ = {d: [x for j, x in enumerate(v) if not (d == dn and j == k)] for d, v in SV.items()}; sp_ = {d: v for d, v in sp_.items() if v}
        loo[it["col"]] = float(stats.spearmanr(ic.compute_index(U, sp_, ic.weights_equal(sp_.keys()))[0].nota, iv.nota)[0])
irm_u = base.nota[U.index]; ind_irmm = float(stats.spearmanr(irm_u, iv.nota)[0])
sens_univ = {}
for lim in (250_000, 500_000, 1_000_000):
    Ul = ind[ind.cfem_med >= lim].copy(); Ul["cv_mes"] = U.cv_mes.reindex(Ul.index); Ul["hhi_sub"] = 1 - Ul.div_sub; Ul["hhi_emp"] = 1 - Ul.div_emp
    r = ic.compute_index(Ul, SV, WV)[0].nota; k_ = r.index.intersection(iv.index)
    sens_univ[str(lim)] = {"n": int(len(Ul)), "spearman": float(stats.spearmanr(r[k_], iv.nota[k_])[0])}
V = []
def add(i, n, val, crit, ok, nota=""): V.append({"id": i, "nome": n, "valor": val, "criterio": crit, "passou": bool(ok), "nota": nota})
add("A1", "Estabilidade temporal (2022–23 x 2024–25)", {"spearman": round(est, 3), "n": int(len(com))}, f"Spearman ≥ {LIM['estab']}", est >= LIM["estab"])
add("A2", "Valor preditivo: IVFM 2022–23 x oscilação da CFEM até 2024–25", {"spearman": round(pred, 3), "n": int(ok_.sum())}, f"Spearman ≥ {LIM['pred_ivfm']}", pred >= LIM["pred_ivfm"], "vulnerável deve oscilar mais")
add("A3", "Modelo nulo (indicadores embaralhados, 500x)", {"abs_p95": round(float(np.percentile(np.abs(nul), 95)), 3)}, f"P95 de |Spearman| < {LIM['nulo']}", np.percentile(np.abs(nul), 95) < LIM["nulo"])
add("A4", "Remover um indicador por vez", {"spearman_min": round(min(loo.values()), 3), "pior": min(loo, key=loo.get)}, f"mínimo ≥ {LIM['loo']}", min(loo.values()) >= LIM["loo"])
add("A5", "Não redundante com o IRMM", {"spearman": round(ind_irmm, 3)}, f"|Spearman| ≤ {LIM['indep']}", abs(ind_irmm) <= LIM["indep"], "se alto, os índices contam a mesma história")
X["ivfm"]["validacao"] = V; X["ivfm"]["sens_universo"] = sens_univ; X["ivfm"]["loo"] = loo

# ============================================================ tipologia IRMM x IVFM
ti = pd.DataFrame({"irmm": irm_u, "ivfm": iv.nota, "nome": nm[U.index]})
mi_, mv_ = ti.irmm.median(), ti.ivfm.median()
def tip(r): return ("Âncora exposta" if r.ivfm >= mv_ else "Âncora resiliente") if r.irmm >= mi_ else ("Pequeno e exposto" if r.ivfm >= mv_ else "Pequeno e estável")
ti["tipo"] = ti.apply(tip, axis=1)
X["tipologia"] = {"corte_irmm": float(mi_), "corte_ivfm": float(mv_), "contagem": ti.tipo.value_counts().to_dict(),
                  "linhas": [{"nome": r.nome, "irmm": float(r.irmm), "ivfm": float(r.ivfm), "tipo": r.tipo, "pos_irmm": int(base.posicao[i])} for i, r in ti.sort_values("irmm", ascending=False).iterrows()]}

# ============================================================ IPMM: pipeline minerário
p3 = pr[pr.status.isin([3, 4, 5])]
rdd = pd.DataFrame(P["rod"]["rows"], columns=P["rod"]["cols"]); rdd = rdd[rdd.mun >= 0]
def pipe(pp):
    g = pp.groupby("mun")
    d = pd.DataFrame({"pesq_n": pp[pp.status == 4].groupby("mun").size(), "pesq_ha": pp[pp.status == 4].groupby("mun").area_ha.sum(), "pre_n": pp[pp.status == 3].groupby("mun").size(),
                      "req_n": pp[pp.status == 5].groupby("mun").size(), "n_tit": g.emp.nunique(), "n_sub": g["min"].nunique()})
    return d.fillna(0)
Pp = pipe(p3)
Pp["arrem_ha"] = rdd[rdd.situacao.isin([0, 3])].groupby("mun").area_ha.sum().reindex(Pp.index).fillna(0)
Pp["disp_ha"] = rdd[rdd.situacao.isin([1, 2])].groupby("mun").area_ha.sum().reindex(Pp.index).fillna(0)
Pp = Pp.join(mun[["nome"]]); Pp = Pp[Pp.nome.notna()]
SP = {"Volume de títulos": [dict(col="pesq_n", log=True), dict(col="pre_n", log=True), dict(col="req_n", log=True)],
      "Área": [dict(col="pesq_ha", log=True), dict(col="arrem_ha", log=True), dict(col="disp_ha", log=True)],
      "Diversidade": [dict(col="n_tit", log=True), dict(col="n_sub", log=True)]}
WP = ic.weights_equal(SP.keys())
ip_, _ = ic.compute_index(Pp, SP, WP); ip_["nome"] = Pp.nome
dp, _ = ic.build_dims(Pp, SP)
X["ipmm"] = {"n": int(len(Pp)), "linhas": [{"nome": ip_.nome[i], "pos": int(ip_.posicao[i]), "nota": float(ip_.nota[i]), **{k: float(dp.loc[i, k] * 100) for k in dp.columns}, "irmm_pos": (int(base.posicao[i]) if i in base.index else None)} for i in ip_.sort_values("posicao").index[:15]]}
mcp, _ = ic.mc_weights(Pp, SP, WP, n=5000, conc=None, seed=SEED)
sp_ = ic.rank_summary(mcp, ip_.posicao, 10)
X["ipmm"]["mc"] = {"amplitude_mediana": float(sp_.amplitude.median()), "top10_p90": int((sp_.prob_topk >= .9).sum()),
                   "intervalos": [{"nome": Pp.nome[i], "base": int(ip_.posicao[i]), "p5": float(sp_.p5[i]), "p50": float(sp_.p50[i]), "p95": float(sp_.p95[i]), "top10": float(sp_.prob_topk[i])} for i in ip_.sort_values("posicao").index[:12]]}
# validação IPMM
VP = []
def addp(i, n, val, crit, ok, nota=""): VP.append({"id": i, "nome": n, "valor": val, "criterio": crit, "passou": bool(ok), "nota": nota})
h1, h2 = Pp[Pp.index.isin(p3[p3.ano_processo <= 2018].mun)], None
pa = pipe(p3[p3.ano_processo <= 2018]).join(mun[["nome"]]); pa = pa[pa.nome.notna()]
for k_ in ["arrem_ha", "disp_ha"]: pa[k_] = Pp[k_].reindex(pa.index).fillna(0)
ia = ic.compute_index(pa, SP, WP)[0].nota
novo = pr[(pr.ano_processo >= 2019) & pr.status.isin([0, 1, 3])].groupby("mun").size().reindex(pa.index).fillna(0)
rp, pp_ = stats.spearmanr(ia, novo)
addp("B1", "Valor preditivo: IPMM só com processos até 2018 x novos processos de lavra e pré-lavra de 2019 em diante", {"spearman": round(float(rp), 3), "n": int(len(pa)), "p": float(pp_)}, f"Spearman ≥ {LIM['pred_ipmm']}", rp >= LIM["pred_ipmm"], "processos mais antigos em pesquisa devem anteceder novos títulos")
rng = np.random.default_rng(SEED + 13); nul = []
for _ in range(500):
    sh = Pp.copy()
    for k in sum([[i['col'] for i in v] for v in SP.values()], []): sh[k] = rng.permutation(sh[k].values)
    nul.append(stats.spearmanr(ic.compute_index(sh, SP, WP)[0].nota, ip_.nota)[0])
addp("B2", "Modelo nulo (indicadores embaralhados, 500x)", {"abs_p95": round(float(np.percentile(np.abs(nul), 95)), 3)}, f"P95 de |Spearman| < {LIM['nulo']}", np.percentile(np.abs(nul), 95) < LIM["nulo"])
loo = {}
for dn, lst in SP.items():
    for k, it in enumerate(lst):
        s_ = {d: [x for j, x in enumerate(v) if not (d == dn and j == k)] for d, v in SP.items()}; s_ = {d: v for d, v in s_.items() if v}
        loo[it["col"]] = float(stats.spearmanr(ic.compute_index(Pp, s_, ic.weights_equal(s_.keys()))[0].nota, ip_.nota)[0])
addp("B3", "Remover um indicador por vez", {"spearman_min": round(min(loo.values()), 3), "pior": min(loo, key=loo.get)}, f"mínimo ≥ {LIM['loo']}", min(loo.values()) >= LIM["loo"])
ci = ip_.nota.reindex(base.index).dropna().index
rr = float(stats.spearmanr(ip_.nota[ci], base.nota[ci])[0])
addp("B4", "Não redundante com o IRMM (municípios em comum)", {"spearman": round(rr, 3), "n": int(len(ci))}, f"|Spearman| ≤ {LIM['indep']}", abs(rr) <= LIM["indep"])
X["ipmm"]["validacao"] = VP; X["ipmm"]["loo"] = loo
X["ipmm"]["fora_irmm"] = [{"nome": r["nome"], "pos": r["pos"]} for r in [{"nome": ip_.nome[i], "pos": int(ip_.posicao[i])} for i in ip_.sort_values("posicao").index[:30] if i not in base.index]][:8]

# ============================================================ cenários de estresse
nomes = nm.to_dict()
base_cols = ind[["nome", "pop", "pib", "cod", "lavra", "prelavra", "energia_mwh"]]
mn_names = {i: n for i, n in enumerate(mn.nome)}  # cfem["min"] é a posição na tabela de substâncias
by_name = {v: k for k, v in mn_names.items()}
def run_cen(cj):
    d = cn.ind_from_cfem(cj, NA, base_cols); r = ic.compute_index(d, SPEC, W0)[0]
    return d, r
CEN = []
def reg(cod, nome, desc, cj, tipo):
    d, r = run_cen(cj); e = cn.efeito(base.posicao, r.posicao, nomes)
    e.update({"cod": cod, "nome": nome, "descricao": desc, "tipo": tipo, "d_cfem_pct": float((cj.valor.sum() / c.valor.sum() - 1) * 100), "n_universo": int(len(d))})
    CEN.append(e)
shock = [("E1", "Cobre −30%", {"Cobre": .7}), ("E2", "Níquel −30%", {"Níquel": .7}), ("E3", "Ouro +30%", {"Ouro": 1.3}), ("E4", "Fosfato e nióbio −20%", {"Fosfato": .8, "Nióbio": .8}),
         ("E5", "Cobre, níquel e ouro −20%", {"Cobre": .8, "Níquel": .8, "Ouro": .8})]
for cod, nome, m in shock:
    reg(cod, nome, "CFEM da substância varia com o valor da produção (alíquota fixa)", cn.choque_preco(c, {by_name[k]: v for k, v in m.items()}), "preço")
top5 = base.sort_values("posicao").head(5).index
for k, mu in enumerate(top5):
    g = c[(c.mun == mu) & c.ano.between(*ANOS)].groupby("emp").valor.sum().sort_values(ascending=False); e0 = g.index[0]
    reg(f"P{k+1}", f"Paralisação do maior titular de {nm[mu]}", f"Zera a CFEM de {D['emp'][e0][1]} ({g.iloc[0]/g.sum()*100:.0f}% da CFEM do município)", cn.remover_titular(c[c.ano.between(*ANOS)], mu, e0), "paralisação")
X["cenarios_estresse"] = CEN
X["cenarios_nota"] = "Choques de preço e paralisações são testes de estresse ilustrativos, não previsões."

# exposição: parcela da CFEM em cada substância (top 8) e exposição dos 10 primeiros
sh = c.groupby("min").valor.sum().sort_values(ascending=False); X["cfem_por_substancia"] = [{"nome": mn_names[int(i)], "pct": float(v / sh.sum() * 100)} for i, v in sh.head(8).items()]
# ============================================================ cenários prospectivos (previsão v1; ilustrativo)
PV = json.load(open(__import__("pathlib").Path(__file__).resolve().parents[2] / "public/data/previsao/previsao_v1.json"))
nmid = {n: i for i, n in mun.nome.items()}
proj = [{"mun": nmid.get(p["municipio"]), "muni": p["municipio"], "mat": p["maturidade"], "w": p["pesos"], "modelo": p["no_modelo"]} for p in PV["carteira"]["projetos"]]
cenv = [x["cenario"] for x in PV["cenarios"]]
pros = {}
for cv in cenv:
    s = pd.Series(0.0, index=ind.index)
    for p in proj:
        if p["mun"] in s.index: s[p["mun"]] += p["w"][cv]
    d5 = ind.copy(); d5["proj"] = s
    SP5 = {**SPEC, "Projetos": [dict(col="proj")]}; W5 = ic.weights_equal(SP5.keys())
    r5 = ic.compute_index(d5, SP5, W5)[0]
    e = cn.efeito(base.posicao, r5.posicao, nomes)
    pros[cv] = {"projetos_ponderados": float(s.sum()), "municipios_com_projeto": [nomes[i] for i in s[s > 0].index], **e}
X["prospectivo"] = {"cenarios": pros, "n_projetos": len(proj), "n_com_peso": sum(1 for p in proj if max(p["w"].values()) > 0), "natureza": "illustrative (SRC_S2_ASSUMPTION_001); previsão v1 não validada pela frente 7",
                    "total_mwh": [{"ano": t["ano"], "cenario": t["cenario"], "mwh": t["energia_mwh"]} for t in PV["total"]]}
json.dump(X, open("extra.json", "w"), ensure_ascii=False, indent=1, default=float)
print("IVFM", X["ivfm"]["n"], [ (v["id"], v["passou"], v["valor"]) for v in V]); print("tip", X["tipologia"]["contagem"])
print("IPMM", X["ipmm"]["n"], [(v["id"], v["passou"], v["valor"]) for v in VP])
for e in CEN: print(e["cod"], e["nome"], round(e["d_cfem_pct"], 1), round(e["spearman"], 3), e["top10_comum"], e["entrou"], e["saiu"], e["maior_queda"][:2], e["saiu_universo"])
for k, v in pros.items(): print(k, v["projetos_ponderados"], v["municipios_com_projeto"], round(v["spearman"], 4), v["entrou"], v["saiu"])
