# -*- coding: utf-8 -*-
"""MINERA Goiás · Frente 8 — motor de indicadores compostos (protótipo, semana 2).

Funções puras (numpy/pandas/scipy). Nada aqui lê arquivo: os dados entram por DataFrame, para o motor ser testável.
Estrutura: indicadores brutos -> normalização (0–1) -> dimensões (média simples dos indicadores) -> índice (soma ponderada
das dimensões) -> nota 0–100 e posição. A posição nunca é apresentada sem o intervalo da análise de sensibilidade.
Nada aqui é validado: protótipo para revisão técnica.
"""
import numpy as np, pandas as pd
from scipy import stats

NORMS = ("minmax", "zcdf", "rank")
AGGS = ("aritmetica", "geometrica", "rank_soma")
EPS_GEO = 0.01  # piso da média geométrica: evita nota zero por um único indicador zerado


# ---------------------------------------------------------------- normalização
def normalize(x, method="minmax", higher_is_better=True, log=False, winsor=None):
    """Leva uma série para [0, 1]. log: log1p antes (para séries assimétricas). winsor=(p_baixo, p_alto) em percentis."""
    s = pd.Series(x, dtype=float)
    if s.isna().any():
        raise ValueError("indicador com valores ausentes: trate antes (política de ausentes documentada)")
    if log:
        if (s < 0).any():
            raise ValueError("log1p exige valores >= 0")
        s = np.log1p(s)
    if winsor:
        lo, hi = np.percentile(s, winsor[0]), np.percentile(s, winsor[1])
        s = s.clip(lo, hi)
    if method == "minmax":
        rng = s.max() - s.min()
        z = (s - s.min()) / rng if rng > 0 else s * 0 + 0.5
    elif method == "zcdf":  # z-score levado a [0,1] pela distribuição normal acumulada
        sd = s.std(ddof=0)
        z = pd.Series(stats.norm.cdf((s - s.mean()) / sd), index=s.index) if sd > 0 else s * 0 + 0.5
    elif method == "rank":  # percentil: (posição média - 1)/(n - 1)
        n = len(s)
        z = (s.rank(method="average") - 1) / (n - 1) if n > 1 else s * 0 + 0.5
    else:
        raise ValueError(f"normalização desconhecida: {method}")
    return z if higher_is_better else 1 - z


# ---------------------------------------------------------------- pesos
def weights_equal(names):
    return pd.Series(1.0 / len(names), index=list(names))


def weights_custom(d):
    w = pd.Series(d, dtype=float)
    if (w < 0).any() or w.sum() <= 0:
        raise ValueError("pesos devem ser >= 0 e somar > 0")
    return w / w.sum()


def weights_entropy(dim_df):
    """Peso por entropia: mais peso para a dimensão que mais diferencia as unidades (depende dos dados)."""
    p = dim_df.clip(lower=1e-12)
    p = p / p.sum()
    e = -(p * np.log(p)).sum() / np.log(len(dim_df))
    d = 1 - e
    return d / d.sum()


def weights_critic(dim_df):
    """CRITIC: desvio-padrão x conflito (1 - correlação). Reduz o peso de dimensões redundantes (dupla contagem)."""
    sd = dim_df.std(ddof=0)
    c = (1 - dim_df.corr().abs()).sum() - 0  # inclui 0 da diagonal
    info = sd * c
    return info / info.sum()


# ---------------------------------------------------------------- agregação
def aggregate(dim_df, w, how="aritmetica"):
    """Nota 0–100 a partir das dimensões (colunas) e dos pesos."""
    w = w.reindex(dim_df.columns)
    if abs(w.sum() - 1) > 1e-9:
        w = w / w.sum()
    if how == "aritmetica":
        s = (dim_df * w).sum(axis=1)
    elif how == "geometrica":
        g = EPS_GEO + (1 - EPS_GEO) * dim_df
        s = np.exp((np.log(g) * w).sum(axis=1))
    elif how == "rank_soma":  # ordinal: média ponderada dos percentis por dimensão
        r = dim_df.rank(method="average", pct=True)
        s = (r * w).sum(axis=1)
    else:
        raise ValueError(f"agregação desconhecida: {how}")
    return 100 * s


def rank_of(score):
    """Posição 1 = maior nota. Empates recebem a mesma posição (a menor), sem desempate arbitrário."""
    return score.rank(ascending=False, method="min").astype(int)


# ---------------------------------------------------------------- índice completo
def build_dims(ind_df, spec, norm="minmax"):
    """spec: {dimensão: [ {col, log, dir(+1/-1), winsor}, ... ]}. Devolve (dimensões 0–1, indicadores normalizados)."""
    nz, dims = {}, {}
    for d, items in spec.items():
        cols = []
        for it in items:
            z = normalize(ind_df[it["col"]], norm, it.get("dir", 1) > 0, it.get("log", False), it.get("winsor"))
            nz[it["col"]] = z
            cols.append(z)
        dims[d] = pd.concat(cols, axis=1).mean(axis=1)
    return pd.DataFrame(dims), pd.DataFrame(nz)


def compute_index(ind_df, spec, w, norm="minmax", how="aritmetica"):
    dims, nz = build_dims(ind_df, spec, norm)
    score = aggregate(dims, w, how)
    return pd.DataFrame({"nota": score, "posicao": rank_of(score)}).join(dims), nz


# ---------------------------------------------------------------- estabilidade de ranking
def spearman(a, b):
    return float(stats.spearmanr(a, b).correlation)


def kendall(a, b):
    return float(stats.kendalltau(a, b).correlation)


def topk_overlap(rank_a, rank_b, k):
    """Jaccard entre os conjuntos das k primeiras posições."""
    A, B = set(rank_a[rank_a <= k].index), set(rank_b[rank_b <= k].index)
    return len(A & B) / len(A | B) if A | B else 1.0


# ---------------------------------------------------------------- simulações
def mc_weights(ind_df, spec, base_w, n=10000, conc=None, seed=20261112, norm="minmax", how="aritmetica"):
    """Sorteia pesos (Dirichlet) e devolve a matriz de posições (n x unidades).
    conc=None: pesos uniformes no simplex (nada se assume). conc=k: Dirichlet(k * pesos-base), sorteio em torno do peso-base."""
    rng = np.random.default_rng(seed)
    dims, _ = build_dims(ind_df, spec, norm)
    names = list(dims.columns)
    alpha = np.ones(len(names)) if conc is None else np.maximum(conc * base_w.reindex(names).values, 1e-3)
    W = rng.dirichlet(alpha, size=n)
    D = dims.values
    if how == "aritmetica":
        S = W @ D.T
    else:
        G = np.log(EPS_GEO + (1 - EPS_GEO) * D)
        S = np.exp(W @ G.T)
    # posição "min": 1 + número de unidades com nota estritamente maior
    R = (S[:, :, None] > S[:, None, :]).sum(axis=1) + 1
    return pd.DataFrame(R, columns=dims.index), W


def method_grid(ind_df, spec, weight_sets, norms=NORMS, aggs=AGGS):
    """Todas as combinações normalização x agregação x conjunto de pesos. Devolve {nome: Series de posição}."""
    out = {}
    for nm in norms:
        for ag in aggs:
            for wn, w in weight_sets.items():
                res, _ = compute_index(ind_df, spec, w, nm, ag)
                out[f"{nm}|{ag}|{wn}"] = res["posicao"]
    return out


def leave_one_dim_out(ind_df, spec, base_w, norm="minmax", how="aritmetica"):
    out = {}
    for d in spec:
        sp = {k: v for k, v in spec.items() if k != d}
        w = base_w.drop(d)
        w = w / w.sum()
        res, _ = compute_index(ind_df, sp, w, norm, how)
        out[d] = res["posicao"]
    return out


def rank_summary(R, base_rank, k=10):
    """P5, mediana, P95 da posição simulada, probabilidade de estar no top-k e amplitude."""
    q = R.quantile([0.05, 0.5, 0.95]).T
    q.columns = ["p5", "p50", "p95"]
    q["amplitude"] = q.p95 - q.p5
    q["prob_topk"] = (R <= k).mean()
    q["base"] = base_rank
    return q


def rank_reversal_pairs(R, a, b):
    """Fração dos sorteios em que a unidade a fica à frente de b (1 = sempre; 0,5 = indefinido)."""
    return float((R[a] < R[b]).mean())
