# -*- coding: utf-8 -*-
"""Testes do motor de cenários e dos índices extras. python3 test_extra.py (ou pytest)."""
import json, subprocess, sys, hashlib, os
import numpy as np, pandas as pd
import cenarios as cn, indices_compostos as ic
X = json.load(open("extra.json", encoding="utf-8"))
def _fx():
    rng = np.random.default_rng(1); n = 30
    base = pd.DataFrame({"nome": [f"m{i}" for i in range(n)], "pop": rng.integers(2000, 90000, n), "pib": rng.uniform(1e7, 9e8, n), "cod": range(n), "lavra": 0, "prelavra": 0}, index=range(n))
    rows = [(m, s, e, v) for m in range(n) for s in range(3) for e, v in [(m * 3 + s, rng.uniform(1e3, 5e5)), (m * 3 + s + 1, rng.uniform(1e3, 5e5))]]
    return base, pd.DataFrame(rows, columns=["mun", "min", "emp", "valor"])
SPEC = {"A": [dict(col="cfem_med", log=True), dict(col="cfem_pc", log=True)], "B": [dict(col="cfem_pib", log=True)], "C": [dict(col="div_sub"), dict(col="div_emp")]}
def t_identidade():
    b, c = _fx(); d0 = cn.ind_from_cfem(c, 4, b); d1 = cn.ind_from_cfem(cn.choque_preco(c, {0: 1.0, 1: 1.0}), 4, b)
    W = ic.weights_equal(SPEC.keys()); assert (ic.compute_index(d0, SPEC, W)[0].posicao == ic.compute_index(d1, SPEC, W)[0].posicao).all()
def t_conservacao_choque():
    b, c = _fx(); s0 = c.valor.sum(); share = c[c["min"] == 1].valor.sum() / s0
    assert abs(cn.choque_preco(c, {1: .7}).valor.sum() / s0 - (1 - .3 * share)) < 1e-9
def t_paralisacao_so_reduz():
    b, c = _fx(); e = c[c.mun == 5].emp.iloc[0]; c2 = cn.remover_titular(c, 5, e)
    assert c2.valor.sum() < c.valor.sum() and len(c2) == len(c) - (c[(c.mun == 5) & (c.emp == e)].shape[0])
    d0, d1 = cn.ind_from_cfem(c, 4, b), cn.ind_from_cfem(c2, 4, b); assert d1.cfem_med[5] < d0.cfem_med[5]
    assert (d1.cfem_med.drop(5) == d0.cfem_med.drop(5)).all()
def t_efeito_identico():
    s = pd.Series([1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12], index=range(12)); e = cn.efeito(s, s, {i: str(i) for i in range(12)})
    assert e["spearman"] == 1 and e["top10_comum"] == 1 and not e["entrou"] and not e["saiu"]
def t_universo_saida():
    b, c = _fx(); c2 = c[c.mun != 3]; d = cn.ind_from_cfem(c2, 4, b); assert 3 not in d.index
def t_choque_monotono_proprio():
    b, c = _fx(); d0 = cn.ind_from_cfem(c, 4, b); d1 = cn.ind_from_cfem(cn.choque_preco(c, {0: 1.5}), 4, b); assert (d1.cfem_med >= d0.cfem_med - 1e-9).all()
def t_choque_consistente_json():
    sh = {r["nome"]: r["pct"] for r in X["cfem_por_substancia"]}
    for e in X["cenarios_estresse"]:
        if e["cod"] == "E1": assert abs(e["d_cfem_pct"] - (-30 * sh["Cobre"] / 100)) < .01
        if e["cod"] == "E2": assert abs(e["d_cfem_pct"] - (-30 * sh["Níquel"] / 100)) < .01
def t_universo_ivfm():
    assert X["ivfm"]["n"] == len([1 for r in X["ivfm"]["linhas"]]) and X["ivfm"]["n"] >= 30
def t_notas_faixa():
    for k in ("ivfm", "ipmm"):
        for r in X[k]["linhas"]: assert 0 <= r["nota"] <= 100
def t_reproducao():
    h0 = hashlib.sha256(open("extra.json", "rb").read()).hexdigest(); subprocess.run([sys.executable, "run_extra.py"], check=True, capture_output=True)
    assert hashlib.sha256(open("extra.json", "rb").read()).hexdigest() == h0
TESTS = [("X01", "cenário neutro (fator 1) reproduz o ranking-base", t_identidade), ("X02", "choque de preço: variação da CFEM = parcela da substância x variação", t_conservacao_choque),
         ("X03", "paralisação só reduz a CFEM do município afetado e não mexe nos demais", t_paralisacao_so_reduz), ("X04", "comparação de dois rankings iguais: Spearman 1, nada entra nem sai", t_efeito_identico),
         ("X05", "município sem CFEM sai do universo", t_universo_saida), ("X06", "aumentar o preço nunca reduz a CFEM de nenhum município", t_choque_monotono_proprio),
         ("X07", "resultados dos cenários batem com a parcela de cada substância", t_choque_consistente_json), ("X08", "IVFM tem universo definido e notas em [0, 100]", t_universo_ivfm),
         ("X09", "IVFM e IPMM com notas entre 0 e 100", t_notas_faixa), ("X10", "rodar de novo produz exatamente o mesmo extra.json (semente fixa)", t_reproducao)]
def test_all():
    for i, n, f in TESTS: f()
if __name__ == "__main__":
    out = []
    for i, n, f in TESTS:
        try: f(); ok = True; err = ""
        except Exception as e: ok = False; err = repr(e)[:150]
        out.append({"id": i, "teste": n, "passou": ok, "erro": err}); print(i, "OK " if ok else "FALHA", n, err)
    json.dump(out, open("testes_extra_resultado.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
