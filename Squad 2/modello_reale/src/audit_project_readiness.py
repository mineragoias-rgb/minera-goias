"""Audita a curadoria do Radar de Projetos antes de alterar o pipeline energético.

O arquivo do Radar contém projetos em diferentes minerais e graus de maturidade.
Este script não transforma automaticamente capacidade anunciada em incremento de
produção nem adiciona TWh: ele apenas deixa explícito o que existe e o que ainda
falta para cada projeto poder entrar no modelo.

Critério para uma linha no ``project_pipeline.csv``:
1. o mineral tem coeficiente energético utilizável no modelo;
2. a quantidade é um incremento anual, na mesma base/unidade do modelo;
3. há ano de início (e, se temporário, ano de fim) documentado;
4. o projeto não é uma operação já incluída na série histórica.

Uso:
    python src/audit_project_readiness.py
"""
import json
from pathlib import Path

import pandas as pd

from common import load_parameters


ROOT = Path(__file__).resolve().parents[3]
MODEL_DIR = Path(__file__).resolve().parents[1]
CURADORIA = ROOT / "Squad 1" / "Radar de Projetos" / "curadoria_web.json"
PIPELINE = MODEL_DIR / "parameters" / "project_pipeline.csv"
OUTPUT_DIR = MODEL_DIR / "outputs" / "project_audit"

MINERAL_DA_CURADORIA = {
    "Cobre": "MIN_011",
    "Bauxita": "MIN_005",
    "Níquel": "MIN_022",
    "Fosfato": "MIN_049",
    "Amianto": "MIN_033",
}


def present(value):
    """Retorna True apenas para campos efetivamente preenchidos pela curadoria."""
    return value is not None and str(value).strip() not in {"", "—", "NA"}


def load_projects():
    data = json.loads(CURADORIA.read_text(encoding="utf-8"))
    rows = []

    for project in data["projetos"]:
        rows.append(
            {
                "project_key": project["chave"],
                "project_name": project["projeto"],
                "mineral_curadoria": project.get("mineral"),
                "maturity": project.get("maturidade"),
                "company": project.get("empresa"),
                "municipality": project.get("municipio"),
                "capacity_value": project.get("cap"),
                "capacity_unit": project.get("cap_un"),
                "reported_production": project.get("prod"),
                "reported_production_unit": project.get("prod_un"),
                "start_year_source": project.get("ano_prev"),
                "timing_source": project.get("previsao"),
                "confidence": project.get("confianca"),
                "source": project.get("fonte"),
                "evidence": project.get("evidencia"),
            }
        )

    return pd.DataFrame(rows)


def assess_project(row, active_mineral_ids, quantified_keys):
    """Classifica a prontidão; não infere números que não foram estruturados."""
    mineral_id = MINERAL_DA_CURADORIA.get(row.mineral_curadoria)
    has_quantity = present(row.capacity_value) or present(row.reported_production)
    has_start = present(row.start_year_source)

    if row.project_key in quantified_keys:
        return (
            mineral_id,
            "included",
            "Já tem incremento, período e base compatível no pipeline energético.",
        )

    if row.maturity == "OPERAÇÃO":
        return (
            mineral_id,
            "historical_operation",
            "Operação existente: a produção já pertence à série histórica; não somar de novo.",
        )

    if row.maturity == "SINAL":
        return (
            mineral_id,
            "early_signal",
            "Sinal/exploração: os pesos do modelo são zero e não há base para projeção quantitativa.",
        )

    if mineral_id is None or mineral_id not in active_mineral_ids:
        if has_quantity and has_start:
            return (
                mineral_id,
                "candidate_needs_energy_coefficient",
                "Há quantidade e data, mas falta coeficiente MWh/t compatível para entrar em TWh.",
            )

        return (
            mineral_id,
            "outside_energy_scope",
            "Mineral fora dos cinco coeficientes ativos; não pode ser convertido em TWh nesta versão.",
        )

    if not has_quantity and not has_start:
        return (
            mineral_id,
            "missing_quantity_and_start",
            "Faltam incremento anual quantificado e ano de início estruturado.",
        )

    if not has_quantity:
        return (
            mineral_id,
            "missing_quantity",
            "Há horizonte, mas não há incremento anual quantificado na curadoria.",
        )

    if not has_start:
        return (
            mineral_id,
            "missing_start",
            "Há capacidade/produção informada, mas não há ano de início do incremento.",
        )

    return (
        mineral_id,
        "needs_unit_and_increment_check",
        "Antes de incluir, confirmar que a quantidade é incremento líquido anual e usa a mesma base produtiva do modelo.",
    )


def make_markdown(audit):
    counts = audit["readiness"].value_counts().to_dict()

    lines = [
        "# Auditoria de prontidão da carteira de projetos",
        "",
        "Gerada automaticamente a partir de `Squad 1/Radar de Projetos/curadoria_web.json`.",
        "Ela não adiciona projetos ao forecast: apenas documenta o que pode ou não ser convertido em uma linha de `project_pipeline.csv`.",
        "",
        "## Resumo",
        "",
        f"- Projetos na curadoria: {len(audit)}",
        f"- Já incluídos no pipeline: {counts.get('included', 0)}",
        f"- Operações já presentes no histórico: {counts.get('historical_operation', 0)}",
        f"- Candidatos com quantidade e data, mas sem coeficiente energético: {counts.get('candidate_needs_energy_coefficient', 0)}",
        "",
        "## Regra de inclusão",
        "",
        "Um projeto só entra no total de TWh quando a fonte traz incremento anual, período de entrada e unidade/base compatível com um coeficiente energético do mineral. Capacidade total, produção corrente ou um simples anúncio não são tratados automaticamente como incremento.",
        "",
        "## Detalhe",
        "",
        "| Projeto | Mineral | Maturidade | Situação | Motivo |",
        "|---|---|---|---|---|",
    ]

    for row in audit.itertuples():
        lines.append(
            f"| {row.project_name} | {row.mineral_curadoria} | "
            f"{row.maturity} | {row.readiness} | {row.reason} |"
        )

    return "\n".join(lines) + "\n"


def run_audit():
    energy, _ = load_parameters()
    active_mineral_ids = set(energy["mineral_id"])

    pipeline = pd.read_csv(PIPELINE)
    quantified_keys = set(pipeline["project_key"])

    audit = load_projects()

    assessed = audit.apply(
        lambda row: assess_project(row, active_mineral_ids, quantified_keys),
        axis=1,
        result_type="expand",
    )
    assessed.columns = ["model_mineral_id", "readiness", "reason"]

    audit = pd.concat([audit, assessed], axis=1)

    audit["has_quantity"] = audit.apply(
        lambda row: present(row.capacity_value)
        or present(row.reported_production),
        axis=1,
    )

    audit["has_start_year"] = audit["start_year_source"].map(present)

    audit["in_energy_model"] = audit["model_mineral_id"].isin(
        active_mineral_ids
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    audit.to_csv(
        OUTPUT_DIR / "project_readiness.csv",
        index=False,
        encoding="utf-8-sig",
    )

    (OUTPUT_DIR / "README.md").write_text(
        make_markdown(audit),
        encoding="utf-8",
    )

    print(
        audit.groupby("readiness", dropna=False)
        .size()
        .sort_values(ascending=False)
        .to_string()
    )

    print(f"\nArquivos gerados em: {OUTPUT_DIR}")

    return audit


if __name__ == "__main__":
    run_audit()
