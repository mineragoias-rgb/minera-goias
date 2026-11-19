# -*- coding: utf-8 -*-
"""Frente 8 · roda os índices compostos sobre os dados do repositório e grava resultados.
Uso: python3 run_indices.py [caminho-do-repositorio]   (semente fixa: resultado idêntico a cada execução)"""
import sys, json, hashlib
import numpy as np, pandas as pd
from scipy import stats
import indices_compostos as ic

from pathlib import Path
REPO = sys.argv[1] if len(sys.argv) > 1 else str(Path(__file__).resolve().parents[2])
SEED = 20261112
P = json.load(open(f"{REPO}/data/panorama/panorama.json"))
D = P["dims"]
mun = pd.DataFrame(D["mun"], columns=["cod", "nome", "pop", "pib"])
mn = pd.DataFrame(D["min"], columns=["id", "nome", "grupo"])
cf = pd.DataFrame(P["cfem"]["rows"], columns=P["cfem"]["cols"])
pr = pd.DataFrame(P["proc"]["rows"], columns=P["proc"]["cols"])
cc = pd.DataFrame(P["ccee"]["rows"], columns=P["ccee"]["cols"])
ag = pd.DataFrame(P["amb_go"]["rows"], columns=P["amb_go"]["cols"])
ab = pd.DataFrame(P["amb_br"]["rows"], columns=P["amb_br"]["cols"])
ST = D["status"]
ANOS = (2022, 2025)  # 2026 é parcial: fora
R = {"seed": SEED, "janela_cfem": list(ANOS)}

# ============================================================ A) ÍNDICE MUNICIPAL (IRMM)
c = cf[cf.ano.between(*ANOS)]
NA = ANOS[1] - ANOS[0] + 1
tot = c.groupby("mun").valor.sum()
def inv_hhi(g):
    s = g / g.sum()
    return 1 - float((s ** 2).sum())
sub = c.groupby(["mun", "min"]).valor.sum().groupby(level=0).apply(inv_hhi)
emp = c.groupby(["mun", "emp"]).valor.sum().groupby(level=0).apply(inv_hhi)
cnt = pr.groupby(["mun", "status"]).size().unstack(fill_value=0).reindex(columns=range(len(ST)), fill_value=0)
ind = pd.DataFrame({"cfem_med": tot / NA, "div_sub": sub, "div_emp": emp}).join(mun[["cod", "nome", "pop", "pib"]])
ind["cfem_pc"] = ind.cfem_med / ind["pop"]
ind["cfem_pib"] = ind.cfem_med / ind.pib * 100
ind["lavra"] = cnt[0].reindex(ind.index).fillna(0) + cnt[1].reindex(ind.index).fillna(0)  # operação ativa + lavra autorizada
ind["prelavra"] = cnt[3].reindex(ind.index).fillna(0)
# energia (variante): consumo medido de 'extração de minerais metálicos', média mensal x 12, meses completos
ex = cc[(cc.mes >= 202405) & (cc.mes <= 202606) & cc.ramo.map(lambda i: "EXTRA" in D["ramo"][i].upper() if isinstance(i, (int, np.integer)) else False)]
nm = cc[(cc.mes >= 202405) & (cc.mes <= 202606)].mes.nunique()
ind["energia_mwh"] = (ex.groupby("mun").total_mwh.sum() / nm * 12).reindex(ind.index).fillna(0)
ind = ind[ind.cfem_med > 0].copy()
ind.index.name = "idx"
R["n_municipios"] = int(len(ind))
R["n_com_energia"] = int((ind.energia_mwh > 0).sum())
R["indicadores_desc"] = {k: {"min": float(ind[k].min()), "mediana": float(ind[k].median()), "max": float(ind[k].max()), "assim": float(stats.skew(ind[k]))}
                         for k in ["cfem_med", "cfem_pc", "cfem_pib", "lavra", "prelavra", "div_sub", "div_emp", "energia_mwh"]}

SPEC = {
    "Arrecadação": [dict(col="cfem_med", log=True), dict(col="cfem_pc", log=True)],
    "Dependência local": [dict(col="cfem_pib", log=True)],
    "Estrutura minerária": [dict(col="lavra", log=True), dict(col="prelavra", log=True)],
    "Diversificação": [dict(col="div_sub"), dict(col="div_emp")],
}
W0 = ic.weights_equal(SPEC.keys())
LENTES = {
    "Equilibrado": W0,
    "Fiscal": ic.weights_custom({"Arrecadação": .40, "Dependência local": .30, "Estrutura minerária": .15, "Diversificação": .15}),
    "Estrutural": ic.weights_custom({"Arrecadação": .15, "Dependência local": .15, "Estrutura minerária": .40, "Diversificação": .30}),
    "Local": ic.weights_custom({"Arrecadação": .20, "Dependência local": .40, "Estrutura minerária": .20, "Diversificação": .20}),
}
base, nz = ic.compute_index(ind, SPEC, W0)
base["nome"] = ind.nome
dims0, _ = ic.build_dims(ind, SPEC)
base_rank = base.posicao
ties = int(base.posicao.duplicated(keep=False).sum())
R["empates_base"] = ties

# --- decomposição e diagnóstico de dupla contagem
corr_ind = nz.corr()
R["corr_indicadores"] = {"cols": list(nz.columns), "m": corr_ind.round(3).values.tolist()}
R["corr_dimensoes"] = {"cols": list(dims0.columns), "m": dims0.corr().round(3).values.tolist()}
R["pesos_alt"] = {"entropia": ic.weights_entropy(dims0).round(4).to_dict(), "critic": ic.weights_critic(dims0).round(4).to_dict()}

# --- 1) simulação de pesos: simplex uniforme e em torno do peso-base
mc_u, Wu = ic.mc_weights(ind, SPEC, W0, n=10000, conc=None, seed=SEED)
mc_n, Wn = ic.mc_weights(ind, SPEC, W0, n=10000, conc=40, seed=SEED)
K = 10
su = ic.rank_summary(mc_u, base_rank, K)
sn = ic.rank_summary(mc_n, base_rank, K)
top = base.sort_values("posicao").head(20).index
R["mc_pesos"] = [{"nome": ind.nome[i], "base": int(base_rank[i]), "uni_p5": float(su.p5[i]), "uni_p50": float(su.p50[i]), "uni_p95": float(su.p95[i]),
                  "uni_top10": float(su.prob_topk[i]), "loc_p5": float(sn.p5[i]), "loc_p50": float(sn.p50[i]), "loc_p95": float(sn.p95[i]), "loc_top10": float(sn.prob_topk[i]),
                  "nota": float(base.nota[i])} for i in top]
R["mc_resumo"] = {"amplitude_mediana_uni": float(su.amplitude.median()), "amplitude_mediana_loc": float(sn.amplitude.median()),
                  "top10_estavel_uni": int((su.prob_topk >= .9).sum()), "top10_estavel_loc": int((sn.prob_topk >= .9).sum()),
                  "top3_sempre_uni": [ind.nome[i] for i in base.sort_values("posicao").head(3).index if su.p95[i] <= 3]}
# pares: a unidade da posição 1 fica sempre à frente da 2? (reversão de ranking)
t5 = list(base.sort_values("posicao").head(6).index)
R["pares_top"] = [{"a": ind.nome[a], "b": ind.nome[b], "p_uni": ic.rank_reversal_pairs(mc_u, a, b), "p_loc": ic.rank_reversal_pairs(mc_n, a, b)}
                  for k, a in enumerate(t5) for b in t5[k + 1:]]

# --- 2) grade de métodos: normalização x agregação x pesos (36 combinações)
wsets = {"equilibrado": W0, "entropia": ic.weights_entropy(dims0), "critic": ic.weights_critic(dims0), **{f"lente_{k.lower()}": v for k, v in LENTES.items() if k != "Equilibrado"}}
G = ic.method_grid(ind, SPEC, wsets)
Gm = []
for k, rk in G.items():
    Gm.append({"cfg": k, "spearman": ic.spearman(rk, base_rank), "kendall": ic.kendall(rk, base_rank), "top10": ic.topk_overlap(rk, base_rank, 10), "top20": ic.topk_overlap(rk, base_rank, 20)})
Gd = pd.DataFrame(Gm)
R["grade"] = Gm
R["grade_resumo"] = {"n": len(Gd), "spearman_min": float(Gd.spearman.min()), "spearman_med": float(Gd.spearman.median()), "top10_min": float(Gd.top10.min()), "top10_med": float(Gd.top10.median()),
                     "pior": Gd.sort_values("spearman").iloc[0]["cfg"], "melhor": Gd.sort_values("spearman").iloc[-2]["cfg"]}
# por eixo
for eixo, pos in (("norm", 0), ("agg", 1), ("peso", 2)):
    Gd[eixo] = Gd.cfg.str.split("|").str[pos]
R["grade_eixos"] = {e: Gd.groupby(e)[["spearman", "top10"]].mean().round(4).reset_index().to_dict("records") for e in ("norm", "agg", "peso")}
# posição de cada município do top-10 base ao longo da grade
Gr = pd.DataFrame(G)
R["grade_rank_top"] = [{"nome": ind.nome[i], "base": int(base_rank[i]), "min": int(Gr.loc[i].min()), "med": float(Gr.loc[i].median()), "max": int(Gr.loc[i].max())} for i in top[:15]]

# --- 3) remover uma dimensão
L = ic.leave_one_dim_out(ind, SPEC, W0)
R["loo"] = [{"dim": d, "spearman": ic.spearman(rk, base_rank), "top10": ic.topk_overlap(rk, base_rank, 10), "top20": ic.topk_overlap(rk, base_rank, 20)} for d, rk in L.items()]

# --- 4) sentido da dependência (relevância x vulnerabilidade) e variante com energia
SPEC_inv = {**SPEC, "Dependência local": [dict(col="cfem_pib", log=True, dir=-1)]}
rk_inv = ic.compute_index(ind, SPEC_inv, W0)[0].posicao
SPEC_en = {**SPEC, "Energia": [dict(col="energia_mwh", log=True)]}
w_en = ic.weights_equal(SPEC_en.keys())
rk_en = ic.compute_index(ind, SPEC_en, w_en)[0].posicao
R["variantes"] = {"dep_invertida": {"spearman": ic.spearman(rk_inv, base_rank), "top10": ic.topk_overlap(rk_inv, base_rank, 10)},
                  "com_energia": {"spearman": ic.spearman(rk_en, base_rank), "top10": ic.topk_overlap(rk_en, base_rank, 10), "n_com_energia": R["n_com_energia"]}}

# --- 5) incerteza dos dados: reamostragem dos meses (bootstrap) refazendo os indicadores de CFEM
cm = c.copy()
cm["t"] = (cm.ano - ANOS[0]) * 12 + cm.mes - 1
nT = NA * 12
muns = ind.index.values
mi = {m: i for i, m in enumerate(muns)}
cm = cm[cm.mun.isin(mi)]
sub_idx = {m: i for i, m in enumerate(sorted(cm["min"].unique()))}
emp_idx = {m: i for i, m in enumerate(sorted(cm["emp"].unique()))}
T_sub = np.zeros((len(muns), len(sub_idx), nT)); T_emp = np.zeros((len(muns), len(emp_idx), nT))
np.add.at(T_sub, (cm.mun.map(mi).values, cm["min"].map(sub_idx).values, cm.t.values), cm.valor.values)
np.add.at(T_emp, (cm.mun.map(mi).values, cm["emp"].map(emp_idx).values, cm.t.values), cm.valor.values)
rng = np.random.default_rng(SEED + 1)
NB = 500
RB = np.zeros((NB, len(muns)), dtype=int)
ind_b = ind.copy()
def inv_h(M):
    s = M / M.sum(axis=1, keepdims=True)
    return 1 - (s ** 2).sum(axis=1)
for b in range(NB):
    wt = rng.multinomial(nT, np.ones(nT) / nT).astype(float)
    ms, me = T_sub @ wt, T_emp @ wt
    tt = ms.sum(axis=1)
    ok = tt > 0
    ind_b["cfem_med"] = tt / (nT / 12)  # soma dos nT meses sorteados, anualizada
    ind_b["cfem_pc"] = ind_b.cfem_med / ind_b["pop"]
    ind_b["cfem_pib"] = ind_b.cfem_med / ind_b.pib * 100
    ind_b["div_sub"] = np.where(ok, inv_h(np.where(ms.sum(axis=1, keepdims=True) > 0, ms, 1)), 0)
    ind_b["div_emp"] = np.where(ok, inv_h(np.where(me.sum(axis=1, keepdims=True) > 0, me, 1)), 0)
    # municípios sem CFEM na amostra: indicadores zerados (continuam na universe; nota baixa)
    res, _ = ic.compute_index(ind_b, SPEC, W0)
    RB[b] = res.posicao.values
RBd = pd.DataFrame(RB, columns=muns)
sb = ic.rank_summary(RBd, base_rank, K)
R["bootstrap"] = {"n": NB, "amplitude_mediana": float(sb.amplitude.median()), "top10_estavel": int((sb.prob_topk >= .9).sum()),
                  "linhas": [{"nome": ind.nome[i], "base": int(base_rank[i]), "p5": float(sb.p5[i]), "p50": float(sb.p50[i]), "p95": float(sb.p95[i]), "top10": float(sb.prob_topk[i])} for i in top[:15]],
                  "sp_med": float(np.median([ic.spearman(RBd.iloc[b], base_rank) for b in range(0, NB, 10)]))}

# --- 6) incerteza combinada do top-10: quantos municípios entram no top-10 em qualquer análise?
union = set(top[:10])
inn = set(sn.index[sn.prob_topk >= .05]) | set(su.index[su.prob_topk >= .05])
R["top10_firmeza"] = [{"nome": ind.nome[i], "base": int(base_rank[i]), "uni": float(su.prob_topk[i]), "loc": float(sn.prob_topk[i]), "boot": float(sb.prob_topk[i]),
                       "grade": float((Gr.loc[i] <= 10).mean())} for i in top[:15]]
R["n_candidatos_top10"] = int(len(inn))


# --- faixas de firmeza: o que se pode afirmar sobre o top 10 sem fingir precisão de posição
P4 = pd.DataFrame({"uni": su.prob_topk, "loc": sn.prob_topk, "boot": sb.prob_topk, "grade": (Gr <= 10).mean(axis=1)})
P4["min"] = P4.min(axis=1); P4["med"] = P4.mean(axis=1)
def _faixa(r):
    if r["min"] >= .5: return "A · firme"
    if r["med"] >= .5: return "B · provável"
    if r["med"] >= .2: return "C · sensível"
    return "D · fora do topo"
P4["faixa"] = P4.apply(_faixa, axis=1)
R["faixas"] = {k: int((P4.faixa == k).sum()) for k in sorted(P4.faixa.unique())}
R["faixas_lista"] = [{"nome": ind.nome[i], "base": int(base_rank[i]), "faixa": P4.faixa[i], **{k: float(P4[k][i]) for k in ("uni", "loc", "boot", "grade", "min", "med")}} for i in P4[P4.faixa != "D · fora do topo"].sort_values("med", ascending=False).index]


# --- passo a passo de duas unidades (demonstração)
def _demo(i):
    raw = {k: float(ind.loc[i, k]) for k in ["cfem_med", "cfem_pc", "cfem_pib", "lavra", "prelavra", "div_sub", "div_emp"]}
    return {"nome": ind.nome[i], "raw": raw, "norm": {k: float(nz.loc[i, k]) for k in nz.columns}, "dim": {k: float(v) for k, v in dims0.loc[i].items()},
            "nota": float(base.nota[i]), "posicao": int(base_rank[i])}
_top1 = base.sort_values("posicao").index[0]
_ah = [i for i in ind.index if ind.nome[i] == "Alto Horizonte"][0]
R["demo_calc"] = [_demo(_top1), _demo(_ah)]
R["norm_limites"] = {k: {"min": float(np.log1p(ind[k]).min()) if k in ("cfem_med", "cfem_pc", "cfem_pib", "lavra", "prelavra") else float(ind[k].min()), "max": float(np.log1p(ind[k]).max()) if k in ("cfem_med", "cfem_pc", "cfem_pib", "lavra", "prelavra") else float(ind[k].max())} for k in nz.columns}

# --- decomposição (contribuição por dimensão) do top 15
dec = (dims0.loc[top[:15]] * W0).mul(100)
R["decomp"] = [{"nome": ind.nome[i], **{k: float(v) for k, v in dec.loc[i].items()}, "nota": float(base.nota[i]), "posicao": int(base_rank[i])} for i in top[:15]]
R["ranking"] = [{"nome": ind.nome[i], "posicao": int(base_rank[i]), "nota": float(base.nota[i]), "cfem_mi": float(ind.cfem_med[i] / 1e6), "pop": int(ind["pop"][i]),
                 "cfem_pib": float(ind.cfem_pib[i]), "lavra": int(ind.lavra[i]), "prelavra": int(ind.prelavra[i]), "div_sub": float(ind.div_sub[i])} for i in base.sort_values("posicao").head(30).index]
# lentes: top 5 por lente e sobreposição
R["lentes"] = {}
for k, w in LENTES.items():
    r_, _ = ic.compute_index(ind, SPEC, w)
    R["lentes"][k] = {"top5": [ind.nome[i] for i in r_.sort_values("posicao").head(5).index], "spearman": ic.spearman(r_.posicao, base_rank), "top10": ic.topk_overlap(r_.posicao, base_rank, 10), "pesos": w.round(3).to_dict()}
# efeito de escala: correlação nota x população e nota x log CFEM
R["viés"] = {"spearman_nota_pop": float(stats.spearmanr(base.nota, ind["pop"]).correlation), "spearman_nota_cfem": float(stats.spearmanr(base.nota, ind.cfem_med).correlation),
             "pequenos_no_top20": int((ind["pop"][top[:20]] < 20000).sum())}
# distribuição de notas
R["notas"] = {"mediana": float(base.nota.median()), "p90": float(base.nota.quantile(.9)), "max": float(base.nota.max()), "min": float(base.nota.min()), "hist": np.histogram(base.nota, bins=10, range=(0, 100))[0].tolist()}
# frações de pares estáveis: quantos pares do top-20 mudam de ordem em >10% dos sorteios (uniforme)
t20 = list(top[:20]); inst = 0; npar = 0
for k, a in enumerate(t20):
    for b in t20[k + 1:]:
        p = ic.rank_reversal_pairs(mc_u, a, b); npar += 1; inst += int(0.1 < p < 0.9)
R["pares_top20"] = {"n": npar, "instaveis": inst}
# ranking completo em CSV
out = base.join(ind[["cod", "cfem_med", "cfem_pc", "cfem_pib", "lavra", "prelavra", "div_sub", "div_emp", "energia_mwh", "pop"]])
out = out.join(su[["p5", "p50", "p95", "prob_topk"]].add_prefix("mc_unif_")).join(sb[["p5", "p95"]].add_prefix("boot_"))
out["faixa_firmeza"] = P4.faixa
out = out.sort_values("posicao").rename(columns={"nota": "nota_0_100"})
out.to_csv("irmm_resultado.csv", index=False, float_format="%.4f", encoding="utf-8")
ind.reset_index(drop=True).to_csv("irmm_indicadores_brutos.csv", index=False, float_format="%.6g", encoding="utf-8")

# ============================================================ B) ÍNDICE POR SUBSTÂNCIA (IPES)
# AMB usa ids numéricos; CFEM usa o mesmo índice de dims.min. Substâncias com produção em Goiás em 2025 e CFEM em 2022–2025.
mname = mn.nome.to_dict()
ab2 = ab[["ano", "min", "rom_t"]].rename(columns={"rom_t": "br_rom"})
g = ag.merge(ab2, on=["ano", "min"], how="left")
g["share"] = g.rom_t / g.br_rom * 100
cfs = c.groupby("min").valor.sum() / NA
ce = c.groupby(["min", "emp"]).valor.sum().groupby(level=0).apply(inv_hhi)
rows = []
for m_, d_ in g.groupby("min"):
    d_ = d_.sort_values("ano")
    v25 = d_[d_.ano == 2025]
    if v25.empty or v25.rom_t.iloc[0] <= 0 or m_ not in cfs.index or v25.benef_rs.iloc[0] <= 0 or pd.isna(v25.share.iloc[0]):
        continue
    j = d_[(d_.ano >= 2015) & (d_.rom_t > 0)]
    if len(j) < 8:
        continue
    sl = stats.linregress(j.ano, np.log(j.rom_t)).slope
    cv = j.rom_t.std(ddof=1) / j.rom_t.mean()
    rows.append(dict(min=m_, nome=mname[m_], valor_mi=v25.benef_rs.iloc[0] / 1e6, cfem_mi=cfs[m_] / 1e6, share_br=v25.share.iloc[0], cresc=sl * 100, cv=cv, div_emp=ce.get(m_, 0.0)))
ip = pd.DataFrame(rows).set_index("min")
SPEC2 = {
    "Peso econômico": [dict(col="valor_mi", log=True), dict(col="cfem_mi", log=True)],
    "Posição nacional": [dict(col="share_br")],
    "Dinâmica": [dict(col="cresc")],
    "Robustez": [dict(col="cv", dir=-1), dict(col="div_emp")],
}
W2 = ic.weights_equal(SPEC2.keys())
b2, _ = ic.compute_index(ip, SPEC2, W2)
b2["nome"] = ip.nome
d2, _ = ic.build_dims(ip, SPEC2)
mc2, _ = ic.mc_weights(ip, SPEC2, W2, n=10000, conc=None, seed=SEED)
s2 = ic.rank_summary(mc2, b2.posicao, 5)
ws2 = {"equilibrado": W2, "entropia": ic.weights_entropy(d2), "critic": ic.weights_critic(d2)}
G2 = pd.DataFrame(ic.method_grid(ip, SPEC2, ws2))
R["ipes"] = {"n": int(len(ip)), "linhas": [{"nome": ip.nome[i], "posicao": int(b2.posicao[i]), "nota": float(b2.nota[i]), "p5": float(s2.p5[i]), "p50": float(s2.p50[i]), "p95": float(s2.p95[i]), "top5": float(s2.prob_topk[i]),
             "grade_min": int(G2.loc[i].min()), "grade_max": int(G2.loc[i].max()), "valor_mi": float(ip.valor_mi[i]), "share_br": float(ip.share_br[i]), "cresc": float(ip.cresc[i]), "cv": float(ip.cv[i]),
             **{k: float(v * 100 * W2[k]) for k, v in d2.loc[i].items()}} for i in b2.sort_values("posicao").index],
             "amplitude_mediana": float(s2.amplitude.median()), "grade_spearman_min": float(min(ic.spearman(G2[c_], b2.posicao) for c_ in G2.columns)),
             "grade_spearman_med": float(np.median([ic.spearman(G2[c_], b2.posicao) for c_ in G2.columns])), "grade_n": int(G2.shape[1])}
pd.DataFrame(R["ipes"]["linhas"]).to_csv("ipes_resultado.csv", index=False, float_format="%.4f", encoding="utf-8")
ip.to_csv("ipes_indicadores_brutos.csv", float_format="%.6g", encoding="utf-8")


# --- validade de face (critérios fixados ANTES de olhar o resultado; ver test_indices.py)
top5_cfem = list(ind.cfem_med.sort_values(ascending=False).head(5).index)
fv = {"top5_arrecadacao": [ind.nome[i] for i in top5_cfem],
      "no_top10_indice": int(sum(base_rank[i] <= 10 for i in top5_cfem)),
      "spearman_nota_cfem": R["viés"]["spearman_nota_cfem"],
      "criterio": "pelo menos 3 dos 5 maiores arrecadadores no top 10 e Spearman(nota, CFEM) >= 0,5"}
fv["aprovado"] = bool(fv["no_top10_indice"] >= 3 and fv["spearman_nota_cfem"] >= 0.5)
R["validade_face_irmm"] = fv
W2e = ic.weights_custom({"Peso econômico": .5, "Posição nacional": .2, "Dinâmica": .15, "Robustez": .15})
r2e, _ = ic.compute_index(ip, SPEC2, W2e)
top3_valor = list(ip.valor_mi.sort_values(ascending=False).head(3).index)
fv2 = {"top3_valor": [ip.nome[i] for i in top3_valor], "no_top5_equilibrado": int(sum(b2.posicao[i] <= 5 for i in top3_valor)),
       "no_top5_lente_economica": int(sum(r2e.posicao[i] <= 5 for i in top3_valor)),
       "criterio": "pelo menos 2 das 3 substâncias de maior valor no top 5 (pesos equilibrados)"}
fv2["aprovado"] = bool(fv2["no_top5_equilibrado"] >= 2)
R["validade_face_ipes"] = fv2
R["ipes"]["lente_economica"] = [{"nome": ip.nome[i], "posicao": int(r2e.posicao[i])} for i in r2e.sort_values("posicao").index]

# ============================================================ C) RECONCILIAÇÃO COM AS FONTES (testes de dados)
chk = {}
chk["cfem_total_painel"] = float(cf[cf.ano.between(*ANOS)].valor.sum())
chk["cfem_total_universo"] = float(tot.reindex(ind.index).sum())
chk["cfem_so_universo_vs_total"] = abs(chk["cfem_total_painel"] - chk["cfem_total_universo"]) / chk["cfem_total_painel"]
chk["n_mun_dims"] = int(len(mun)); chk["n_mun_cfem"] = int(tot.shape[0])
chk["cfem_negativa"] = int((cf.valor < 0).sum())
chk["pop_pib_ausentes"] = int(ind[["pop", "pib"]].isna().any(axis=1).sum())
chk["proc_total"] = int(len(pr)); chk["proc_soma_status"] = int(cnt.values.sum())
chk["hash_ranking"] = hashlib.sha256(out[["posicao"]].to_csv(index=False).encode()).hexdigest()[:16]
R["checagem"] = chk
json.dump(R, open("out4.json", "w"), ensure_ascii=False, default=float)
print("n mun", R["n_municipios"], "energia", R["n_com_energia"], "empates", ties)
print("top10", [r["nome"] for r in R["ranking"][:10]])
print("mc", R["mc_resumo"]); print("grade", R["grade_resumo"]); print("loo", R["loo"]); print("var", R["variantes"]); print("boot", {k: v for k, v in R["bootstrap"].items() if k != "linhas"})
print("viés", R["viés"], R["pares_top20"], "cand top10", R["n_candidatos_top10"])
print("lentes", {k: (v["top5"], round(v["spearman"], 3)) for k, v in R["lentes"].items()})
print("ipes", R["ipes"]["n"], [(r["nome"], r["posicao"], r["p5"], r["p95"]) for r in R["ipes"]["linhas"]], R["ipes"]["grade_spearman_min"], R["ipes"]["grade_spearman_med"])
print(chk)
