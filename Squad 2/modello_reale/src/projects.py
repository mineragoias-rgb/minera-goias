"""Camada de projetos do modelo real: liga a base de projetos do Squad 1 à projeção de produção.

A produção projetada passa a ser

    produção(m, t, s) = tendência(m, t, s) + Σ_p peso(maturidade_p, s) × incremento_p(t)

- tendência: a regra histórica de run_future_scenarios.py (operações existentes);
- incremento_p(t): produção adicional anual do projeto p entre o ano de entrada e o de saída, na mesma base de produção
  do mineral, quantificada em parameters/project_pipeline.csv a partir das fontes da curadoria;
- peso: probabilidade ilustrativa por maturidade e cenário, em parameters/project_maturity_weights.csv.

A maturidade de cada projeto é lida da curadoria do Squad 1 (Squad 1/Radar de Projetos/curadoria_web.json) a cada
execução, para que um projeto que avança ou recua mude o peso sem editar o modelo. Projetos em OPERAÇÃO já estão na
série histórica e têm peso zero. Um projeto da curadoria sem linha no pipeline aparece no inventário como não
quantificado, com o motivo.
"""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
MODEL_DIR = Path(__file__).resolve().parents[1]
CURADORIA = ROOT / "Squad 1" / "Radar de Projetos" / "curadoria_web.json"
PIPELINE = MODEL_DIR / "parameters" / "project_pipeline.csv"
WEIGHTS = MODEL_DIR / "parameters" / "project_maturity_weights.csv"

MATURIDADES = ["OPERAÇÃO", "EXPANSÃO", "CONSTRUÇÃO", "DEFINIDO", "PROVÁVEL", "POSSÍVEL", "SINAL"]
SCENARIOS = ["conservador", "referencia", "expansao"]
# Nome do mineral principal na curadoria → mineral do modelo.
MINERAL_DA_CURADORIA = {
    "Cobre": "MIN_011",
    "Bauxita": "MIN_005",
    "Níquel": "MIN_022",
    "Fosfato": "MIN_049",
    "Amianto": "MIN_033",
}


def load_curated_projects():
    dados = json.loads(CURADORIA.read_text(encoding="utf-8"))
    linhas = []
    for p in dados["projetos"]:
        if p.get("mineral") not in MINERAL_DA_CURADORIA:
            continue
        if p.get("maturidade") not in MATURIDADES:
            raise ValueError(f"Maturidade desconhecida na curadoria: {p.get('chave')} = {p.get('maturidade')}")
        linhas.append({
            "project_key": p["chave"],
            "project_name": p["projeto"],
            "company": p.get("empresa"),
            "municipality": p.get("municipio"),
            "mineral_id": MINERAL_DA_CURADORIA[p["mineral"]],
            "maturidade": p["maturidade"],
            "status": p.get("status"),
            "confianca": p.get("confianca"),
            "previsao": p.get("previsao"),
            "source": p.get("fonte"),
            "link": p.get("link"),
        })
    curated = pd.DataFrame(linhas)
    if curated["project_key"].duplicated().any():
        raise ValueError("Chave de projeto repetida na curadoria.")
    return curated


def load_weights():
    weights = pd.read_csv(WEIGHTS)
    if sorted(weights["maturidade"]) != sorted(MATURIDADES):
        raise ValueError("Os pesos devem cobrir exatamente as sete maturidades da curadoria.")
    for s in SCENARIOS:
        if not weights[s].between(0, 1).all():
            raise ValueError(f"Peso fora de 0–1 no cenário {s}.")
    if (weights.set_index("maturidade").loc["OPERAÇÃO", SCENARIOS] != 0).any():
        raise ValueError("OPERAÇÃO já está na série histórica: o peso tem de ser zero.")
    return weights


def load_pipeline(curated, energy):
    pipeline = pd.read_csv(PIPELINE)
    if pipeline["project_key"].duplicated().any():
        raise ValueError("Projeto repetido em project_pipeline.csv.")
    faltam = set(pipeline["project_key"]) - set(curated["project_key"])
    if faltam:
        raise ValueError(f"Projetos do pipeline ausentes da curadoria do Squad 1: {sorted(faltam)}")
    pipeline = pipeline.merge(curated[["project_key", "mineral_id", "maturidade"]], on="project_key",
                              suffixes=("", "_curadoria"))
    if (pipeline["mineral_id"] != pipeline["mineral_id_curadoria"]).any():
        raise ValueError("Mineral do pipeline difere do mineral principal na curadoria.")
    bases = energy.set_index("mineral_id")["production_basis"]
    if (pipeline["production_basis"] != pipeline["mineral_id"].map(bases)).any():
        raise ValueError("Base de produção do projeto difere da base que o modelo usa para o mineral.")
    if (pipeline["incremental_production_t_per_year"] <= 0).any() or (pipeline["end_year"] < pipeline["start_year"]).any():
        raise ValueError("Incremento não positivo ou período invertido no pipeline.")
    return pipeline.drop(columns=["mineral_id_curadoria"])


def build_project_layer(energy, first_year, last_year):
    """Devolve (incremento por mineral/cenário/ano, detalhe por projeto, inventário da curadoria)."""
    curated = load_curated_projects()
    weights = load_weights().set_index("maturidade")
    pipeline = load_pipeline(curated, energy)

    detalhe = []
    for p in pipeline.itertuples():
        for s in SCENARIOS:
            peso = float(weights.loc[p.maturidade, s])
            for ano in range(first_year, last_year + 1):
                ativo = p.start_year <= ano <= p.end_year
                detalhe.append({
                    "project_key": p.project_key,
                    "mineral_id": p.mineral_id,
                    "maturidade": p.maturidade,
                    "scenario": s,
                    "year": ano,
                    "weight": peso,
                    "incremental_production_t": p.incremental_production_t_per_year if ativo else 0.0,
                    "weighted_production_t": peso * p.incremental_production_t_per_year if ativo else 0.0,
                })
    detail = pd.DataFrame(detalhe, columns=["project_key", "mineral_id", "maturidade", "scenario", "year", "weight",
                                            "incremental_production_t", "weighted_production_t"])

    increment = (detail.groupby(["mineral_id", "scenario", "year"], as_index=False)
                 .agg(project_production_t=("weighted_production_t", "sum")))

    quantificados = set(pipeline["project_key"])
    inventory = curated.copy()
    inventory["in_model"] = inventory["project_key"].isin(quantificados)
    # quantificado: entra no modelo; em_operacao: já está na série histórica; sinal: fora da projeção;
    # sem_quantificacao: as fontes não trazem incremento de produção e ano de entrada.
    inventory["reason"] = inventory.apply(
        lambda r: "quantificado" if r["in_model"]
        else "em_operacao" if r["maturidade"] == "OPERAÇÃO"
        else "sinal" if r["maturidade"] == "SINAL"
        else "sem_quantificacao", axis=1)
    inventory = inventory.merge(
        pipeline[["project_key", "incremental_production_t_per_year", "start_year", "end_year", "quantity_nature",
                  "source_note"]], on="project_key", how="left")
    for s in SCENARIOS:
        inventory[f"weight_{s}"] = inventory["maturidade"].map(weights[s])
    return increment, detail, inventory


if __name__ == "__main__":
    from common import load_parameters
    energy, _ = load_parameters()
    inc, det, inv = build_project_layer(energy, 2027, 2040)
    print(inv[["project_key", "mineral_id", "maturidade", "reason"]].to_string(index=False))
    print(inc[inc.project_production_t > 0].to_string(index=False))
