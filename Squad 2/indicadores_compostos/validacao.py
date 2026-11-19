# -*- coding: utf-8 -*-
"""Frente 8 · protocolo de validação técnica do IRMM. Critérios fixados ANTES de rodar (limiares abaixo).
Uso: python3 validacao.py [repo]  -> validacao_resultado.json"""
import sys, json
import numpy as np, pandas as pd
from scipy import stats
src = open(__file__.replace("validacao.py", "run_indices.py"), encoding="utf-8").read()
exec(compile(src.split('R["empates_base"] = ties')[0], "run_indices_setup", "exec"))  # só carrega dados, indicadores e índice-base
LIM = {"V3_spearman": .80, "V3_top10": .50, "V4_spearman": .50, "V5_pop": .50, "V6_spearman": .95, "V7_p95": .20, "V8_spearman": .85}
V = []
def add(i, nome, valor, crit, ok, nota=""): V.append({"id": i, "nome": nome, "valor": valor, "criterio": crit, "passou": bool(ok), "nota": nota})

# V3 estabilidade temporal: recalcula os indicadores de CFEM em 2022–23 e 2024–25 (processos e população não mudam)
def ind_janela(a, b):
    cj = cf[cf.ano.between(a, b)]; n = b - a + 1
    t = cj.groupby("mun").valor.sum()
    d = ind.drop(columns=["cfem_med", "cfem_pc", "cfem_pib", "div_sub", "div_emp"]).copy()
    d["cfem_med"] = (t / n).reindex(d.index).fillna(0)
    d["div_sub"] = cj.groupby(["mun", "min"]).valor.sum().groupby(level=0).apply(inv_hhi).reindex(d.index).fillna(0)
    d["div_emp"] = cj.groupby(["mun", "emp"]).valor.sum().groupby(level=0).apply(inv_hhi).reindex(d.index).fillna(0)
    d["cfem_pc"] = d.cfem_med / d["pop"]; d["cfem_pib"] = d.cfem_med / d.pib * 100
    return d[d.cfem_med > 0]
d1, d2 = ind_janela(2022, 2023), ind_janela(2024, 2025)
r1 = ic.compute_index(d1, SPEC, W0)[0].posicao; r2 = ic.compute_index(d2, SPEC, W0)[0].posicao
com = r1.index.intersection(r2.index)
sp = float(stats.spearmanr(r1[com], r2[com])[0])
t1 = set(r1.sort_values().head(10).index); t2 = set(r2.sort_values().head(10).index)
ov = len(t1 & t2) / 10
pv = float(stats.hypergeom.sf(len(t1 & t2) - 1, len(com), 10, 10))
add("V3", "Estabilidade temporal (2022–23 x 2024–25)", {"spearman": round(sp, 3), "top10_comum": ov, "n_comum": int(len(com)), "p_acaso_top10": pv},
    f"Spearman ≥ {LIM['V3_spearman']} e top 10 em comum ≥ {LIM['V3_top10']:.0%}", sp >= LIM["V3_spearman"] and ov >= LIM["V3_top10"], f"{len(t1&t2)} de 10 em comum; p de acaso = {pv:.1e}")

# V4 validade convergente com fonte independente (energia medida CCEE, fora do índice)
e = ind[ind.energia_mwh > 0]
rho, pe = stats.spearmanr(base.nota[e.index], e.energia_mwh)
add("V4", "Convergência com consumo medido de energia (CCEE, fora do índice)", {"spearman": round(float(rho), 3), "n": int(len(e)), "p": round(float(pe), 3)},
    f"Spearman ≥ {LIM['V4_spearman']} (n pequeno: indicativo)", rho >= LIM["V4_spearman"], f"n = {len(e)}; fonte independente, só 9 municípios")

# V5 discriminante: não é só tamanho
rp = float(stats.spearmanr(base.nota, ind["pop"])[0])
add("V5", "Não é proxy de população", {"spearman": round(rp, 3)}, f"|Spearman| ≤ {LIM['V5_pop']}", abs(rp) <= LIM["V5_pop"])

# V6 outlier: sem o maior arrecadador
out = ind.cfem_med.idxmax(); ind6 = ind.drop(out)
r6 = ic.compute_index(ind6, SPEC, W0)[0].posicao
sp6 = float(stats.spearmanr(r6, base.posicao[ind6.index])[0])
add("V6", "Robustez ao maior outlier (sem " + str(ind.nome[out]) + ")", {"spearman": round(sp6, 3)}, f"Spearman ≥ {LIM['V6_spearman']}", sp6 >= LIM["V6_spearman"])

# V7 modelo nulo: embaralhar cada indicador entre municípios
rng = np.random.default_rng(SEED + 7); nulls = []
for _ in range(500):
    sh = ind.copy()
    for c_ in ["cfem_med", "cfem_pc", "cfem_pib", "lavra", "prelavra", "div_sub", "div_emp"]: sh[c_] = rng.permutation(sh[c_].values)
    nulls.append(stats.spearmanr(ic.compute_index(sh, SPEC, W0)[0].posicao, base.posicao)[0])
p95 = float(np.percentile(np.abs(nulls), 95))
add("V7", "Modelo nulo (indicadores embaralhados, 500x)", {"abs_spearman_p95": round(p95, 3)}, f"P95 de |Spearman| < {LIM['V7_p95']}", p95 < LIM["V7_p95"], "o índice carrega estrutura que o acaso não reproduz")

# V8 remover um indicador por vez
loo = {}
for dname, lst in SPEC.items():
    for k, it in enumerate(lst):
        sp_ = {d: [x for j, x in enumerate(v) if not (d == dname and j == k)] for d, v in SPEC.items()}
        sp_ = {d: v for d, v in sp_.items() if v}
        loo[it["col"]] = float(stats.spearmanr(ic.compute_index(ind, sp_, ic.weights_equal(sp_.keys()))[0].posicao, base.posicao)[0])
mn_ = min(loo.values())
add("V8", "Remover um indicador por vez (7 casos)", {"spearman_min": round(mn_, 3), "pior": min(loo, key=loo.get), "todos": {k: round(v, 3) for k, v in loo.items()}},
    f"Spearman mínimo ≥ {LIM['V8_spearman']}", mn_ >= LIM["V8_spearman"])

# V1/V2 já medidos em test_indices (D07, D05); IPES: D06
T = json.load(open("testes_resultado.json")); tt = {t["id"]: t["passou"] for t in T}
V.insert(0, {"id": "V1", "nome": "Reprodutibilidade (mesma entrada, mesmo ranking; hash)", "valor": {"teste": "D07"}, "criterio": "D07 passa", "passou": tt["D07"], "nota": "reexecuta o pipeline do zero"})
V.insert(1, {"id": "V2", "nome": "Validade de face IRMM (critério fixado antes)", "valor": {"teste": "D05"}, "criterio": "D05 passa", "passou": tt["D05"], "nota": "3 dos 5 maiores arrecadadores no top 10"})
ok = all(v["passou"] for v in V)
res = {"limiares": LIM, "testes": V, "irmm_aprovado_tecnicamente": ok, "ipes_aprovado": bool(tt["D06"]),
       "veredito_irmm": "Aprovado na validação técnica interna" if ok else "Não validado: reprovou em pelo menos um critério",
       "pendente_externo": ["consulta estruturada de pesos (AHP)", "revisão técnica independente (frente 10)", "validação humana das bases"]}
json.dump(res, open("validacao_resultado.json", "w"), ensure_ascii=False, indent=1, default=float)
for v in V: print(v["id"], "OK " if v["passou"] else "FALHA", v["nome"], v["valor"])
print(res["veredito_irmm"])
