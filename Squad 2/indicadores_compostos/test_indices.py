# -*- coding: utf-8 -*-
"""Frente 8 · testes do motor de indicadores compostos. Rodar: python3 test_indices.py (ou pytest test_indices.py).
Cada teste tem ID, o que verifica e por que importa. Critérios de validade de face foram fixados antes de olhar o resultado."""
import json, os, subprocess, sys, tempfile, hashlib
import numpy as np, pandas as pd
import indices_compostos as ic

HERE = os.path.dirname(os.path.abspath(__file__))
rng = np.random.default_rng(7)
N = 60
DF = pd.DataFrame({"a": rng.lognormal(3, 1.2, N), "b": rng.lognormal(1, .8, N), "c": rng.uniform(0, 1, N), "d": rng.integers(0, 30, N).astype(float)})
SPEC = {"X": [dict(col="a", log=True), dict(col="b", log=True)], "Y": [dict(col="c")], "Z": [dict(col="d", log=True)]}
W = ic.weights_equal(SPEC.keys())


def test_T01_normalizacao_em_0_1():
    for m in ic.NORMS:
        z = ic.normalize(DF.a, m, log=True)
        assert z.min() >= 0 and z.max() <= 1, m


def test_T02_invariancia_de_unidade():  # R$ -> R$ mil não pode mudar nota nem posição (minmax com log não é invariante; sem log sim)
    r1, _ = ic.compute_index(DF.assign(a=DF.a), {"X": [dict(col="a")], "Y": [dict(col="c")]}, ic.weights_equal(["X", "Y"]))
    r2, _ = ic.compute_index(DF.assign(a=DF.a / 1000), {"X": [dict(col="a")], "Y": [dict(col="c")]}, ic.weights_equal(["X", "Y"]))
    assert np.allclose(r1.nota, r2.nota) and (r1.posicao == r2.posicao).all()


def test_T03_inversao_de_sentido():
    z = ic.normalize(DF.c, "minmax", True)
    zi = ic.normalize(DF.c, "minmax", False)
    assert np.allclose(z + zi, 1)


def test_T04_monotonicidade():  # melhorar um indicador, mantendo os outros, não pode reduzir a nota
    for how in ("aritmetica", "geometrica"):
        base, _ = ic.compute_index(DF, SPEC, W, how=how)
        i = DF.c.idxmin()
        d2 = DF.copy()
        d2.loc[i, "c"] = DF.c.max()
        mod, _ = ic.compute_index(d2, SPEC, W, how=how)
        assert mod.nota[i] >= base.nota[i] - 1e-9, how


def test_T05_pesos_somam_1():
    dims, _ = ic.build_dims(DF, SPEC)
    for w in (ic.weights_equal(dims.columns), ic.weights_custom({"X": 2, "Y": 1, "Z": 1}), ic.weights_entropy(dims), ic.weights_critic(dims)):
        assert abs(w.sum() - 1) < 1e-9 and (w >= 0).all()


def test_T06_reprodutibilidade_da_simulacao():
    a, _ = ic.mc_weights(DF, SPEC, W, n=500, seed=1)
    b, _ = ic.mc_weights(DF, SPEC, W, n=500, seed=1)
    c, _ = ic.mc_weights(DF, SPEC, W, n=500, seed=2)
    assert a.equals(b) and not a.equals(c)


def test_T07_empates_sem_desempate_arbitrario():
    d = DF.copy()
    d.loc[1] = d.loc[0]
    r, _ = ic.compute_index(d, SPEC, W)
    assert r.posicao[0] == r.posicao[1]


def test_T08_ausentes_nao_passam_em_silencio():
    d = DF.copy()
    d.loc[3, "a"] = np.nan
    try:
        ic.compute_index(d, SPEC, W)
    except ValueError:
        return
    raise AssertionError("indicador ausente deveria barrar")


def test_T09_sem_reversao_por_dominancia():  # quem domina em todos os indicadores nunca fica atrás, com qualquer peso
    d = DF.copy()
    d.loc[0] = d.loc[1] * 1.0
    for c in ("a", "b", "c", "d"):
        d.loc[0, c] = d.loc[1, c] + 1
    R, _ = ic.mc_weights(d, SPEC, W, n=1000, seed=3)
    assert (R[0] <= R[1]).all()


def test_T10_geometrica_pune_zero_sem_zerar():
    d = DF.copy()
    d.loc[0, "c"] = 0
    r, _ = ic.compute_index(d, SPEC, W, how="geometrica")
    assert r.nota[0] > 0


def test_T11_mc_nota_na_faixa_e_posicoes_validas():
    R, Wm = ic.mc_weights(DF, SPEC, W, n=300, seed=5)
    assert R.values.min() >= 1 and R.values.max() <= len(DF) and np.allclose(Wm.sum(axis=1), 1)


def test_T12_correlacao_de_ranking_identidade():
    r, _ = ic.compute_index(DF, SPEC, W)
    assert abs(ic.spearman(r.posicao, r.posicao) - 1) < 1e-12 and ic.topk_overlap(r.posicao, r.posicao, 10) == 1


# ---------------- testes sobre os dados reais (leem out4.json gerado por run_indices.py)
def _R():
    return json.load(open(os.path.join(HERE, "out4.json"), encoding="utf-8"))


def test_D01_cfem_reconcilia_com_o_painel():
    c = _R()["checagem"]
    assert c["cfem_so_universo_vs_total"] < 1e-9


def test_D02_sem_cfem_negativa_nem_pop_pib_ausentes():
    c = _R()["checagem"]
    assert c["cfem_negativa"] == 0 and c["pop_pib_ausentes"] == 0


def test_D03_processos_somam_o_cadastro():
    c = _R()["checagem"]
    assert c["proc_total"] == c["proc_soma_status"]


def test_D04_sem_empates_no_ranking_base():
    assert _R()["empates_base"] == 0


def test_D05_validade_de_face_irmm():
    assert _R()["validade_face_irmm"]["aprovado"]


def test_D06_validade_de_face_ipes():  # critério fixado antes; este teste reprova de propósito se o índice não passar
    assert _R()["validade_face_ipes"]["aprovado"]


def test_D07_reproducao_integral():  # roda o pipeline completo em pasta temporária e compara o hash do ranking
    with tempfile.TemporaryDirectory() as t:
        env = dict(os.environ, PYTHONPATH=HERE)
        subprocess.run([sys.executable, os.path.join(HERE, "run_indices.py")] + sys.argv[1:2], cwd=t, env=env, check=True, capture_output=True)
        h = json.load(open(os.path.join(t, "out4.json"), encoding="utf-8"))["checagem"]["hash_ranking"]
    assert h == _R()["checagem"]["hash_ranking"]


DESCR = {
    "T01": ("Normalização", "toda normalização fica em [0, 1]"), "T02": ("Normalização", "mudar a unidade (R$ → R$ mil) não muda nota nem posição"),
    "T03": ("Normalização", "inverter o sentido do indicador devolve 1 − valor"), "T04": ("Agregação", "melhorar um indicador nunca reduz a nota (aritmética e geométrica)"),
    "T05": ("Pesos", "pesos (igual, especialista, entropia, CRITIC) somam 1 e não são negativos"), "T06": ("Simulação", "mesma semente, mesmo resultado; outra semente, outro resultado"),
    "T07": ("Ranking", "empates recebem a mesma posição, sem desempate arbitrário"), "T08": ("Dados", "indicador ausente barra o cálculo em vez de virar zero"),
    "T09": ("Ranking", "quem domina em todos os indicadores nunca fica atrás, com qualquer peso"), "T10": ("Agregação", "média geométrica penaliza o zero sem zerar a nota"),
    "T11": ("Simulação", "pesos sorteados somam 1 e as posições ficam entre 1 e n"), "T12": ("Ranking", "métricas de estabilidade dão 1 na comparação consigo mesmo"),
    "D01": ("Dados", "a soma da CFEM dos municípios do universo é igual à do painel"), "D02": ("Dados", "sem CFEM negativa e sem população ou PIB ausentes"),
    "D03": ("Dados", "os processos por status somam o cadastro (16.875)"), "D04": ("Ranking", "ranking-base sem empates"),
    "D05": ("Validade de face", "IRMM: ≥ 3 dos 5 maiores arrecadadores no top 10 e Spearman(nota, CFEM) ≥ 0,5"), "D06": ("Validade de face", "IPES: ≥ 2 das 3 substâncias de maior valor no top 5"),
    "D07": ("Reprodução", "rodar o pipeline do zero reproduz o mesmo ranking (hash)"),
}

if __name__ == "__main__":
    res = []
    for name, f in list(globals().items()):
        if name.startswith("test_"):
            tid = name.split("_")[1]
            try:
                f(); ok, msg = True, ""
            except AssertionError as e:
                ok, msg = False, str(e)[:120]
            except Exception as e:
                ok, msg = False, f"erro: {type(e).__name__}: {str(e)[:100]}"
            res.append({"id": tid, "grupo": DESCR[tid][0], "teste": DESCR[tid][1], "passou": ok, "obs": msg})
    res.sort(key=lambda r: r["id"][0] + r["id"][1:].zfill(3))
    json.dump(res, open(os.path.join(HERE, "testes_resultado.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for r in res:
        print(("OK   " if r["passou"] else "FALHA"), r["id"], r["teste"], r["obs"])
    print(f"{sum(r['passou'] for r in res)}/{len(res)} passaram")
