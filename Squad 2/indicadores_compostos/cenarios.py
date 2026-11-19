# -*- coding: utf-8 -*-
"""Frente 8 · motor de cenários: funções puras sobre tabelas (nenhuma lê arquivo).
Um cenário muda os DADOS de entrada (CFEM por substância/titular) e refaz os indicadores e o índice.
Cenários são testes de estresse ilustrativos, não previsões."""
import numpy as np, pandas as pd

def inv_hhi(g):
    s = g / g.sum()
    return 1 - float((s ** 2).sum())

def ind_from_cfem(cj, n_anos, base):
    """Refaz os indicadores de CFEM a partir de uma tabela (mun, min, emp, valor). `base` traz pop, pib, nome, lavra, prelavra."""
    cj = cj[cj.valor > 0]
    tot = cj.groupby("mun").valor.sum()
    d = base.drop(columns=[c for c in ["cfem_med", "cfem_pc", "cfem_pib", "div_sub", "div_emp"] if c in base.columns]).copy()
    d["cfem_med"] = (tot / n_anos).reindex(d.index).fillna(0)
    d["div_sub"] = cj.groupby(["mun", "min"]).valor.sum().groupby(level=0).apply(inv_hhi).reindex(d.index).fillna(0)
    d["div_emp"] = cj.groupby(["mun", "emp"]).valor.sum().groupby(level=0).apply(inv_hhi).reindex(d.index).fillna(0)
    d["cfem_pc"] = d.cfem_med / d["pop"]
    d["cfem_pib"] = d.cfem_med / d.pib * 100
    return d[d.cfem_med > 0]

def choque_preco(cj, mult):
    """CFEM é proporcional ao valor da produção (alíquota fixa): multiplica a CFEM da substância pelo fator. mult = {id_substancia: fator}."""
    out = cj.copy()
    out["valor"] = out.valor * out["min"].map(mult).fillna(1.0)
    return out

def remover_titular(cj, mun, emp):
    """Paralisação: zera a CFEM de um titular em um município."""
    return cj[~((cj.mun == mun) & (cj.emp == emp))].copy()

def efeito(base_rank, new_rank, nomes, k=10):
    """Compara posições: quem entra/sai do top k, maiores variações, Spearman nos municípios comuns."""
    from scipy import stats
    com = base_rank.index.intersection(new_rank.index)
    sp = float(stats.spearmanr(base_rank[com], new_rank[com])[0]) if len(com) > 2 else float("nan")
    tb, tn = set(base_rank[base_rank <= k].index), set(new_rank[new_rank <= k].index)
    d = (base_rank[com] - new_rank[com]).sort_values()   # positivo = subiu
    saiu = [nomes[i] for i in base_rank.index.difference(new_rank.index)]
    return {"spearman": sp, "top10_comum": len(tb & tn) / k, "entrou": [nomes[i] for i in tn - tb], "saiu": [nomes[i] for i in tb - tn],
            "maior_queda": [(nomes[i], int(d[i])) for i in d.index[:3] if d[i] < 0], "maior_alta": [(nomes[i], int(d[i])) for i in d.index[::-1][:3] if d[i] > 0],
            "saiu_universo": saiu}
