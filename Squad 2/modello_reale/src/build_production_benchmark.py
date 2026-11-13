"""Benchmark de produção mineral para ampliar a análise além dos cinco minerais do modelo.

Não transforma minerais adicionais em demanda elétrica: compara somente produção
observada, em toneladas e em índice base 2025 = 100.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from common import MODEL_DIR, ROOT, SQUAD1_INTERFACE


OUTPUT_DIR = MODEL_DIR / "outputs" / "production_benchmark"
PUBLIC_OUTPUT = ROOT / "public" / "data" / "previsao" / "production_benchmark_v1.json"

MIN_YEARS_REQUIRED = 12
BASE_YEAR = 2025


def load_production() -> pd.DataFrame:
    """Carrega somente séries estaduais, observadas, válidas e beneficiadas."""
    data = pd.read_csv(SQUAD1_INTERFACE)

    production = data[
        (data["nivel_agregacao"] == "estado")
        & (data["valor_observado_estimado"] == "observado")
        & (data["status_validacao"] == "valido")
        & (data["production_basis"].str.lower() == "beneficiada")
    ].copy()

    production["year"] = pd.to_numeric(production["year"], errors="coerce")
    production["production_t"] = pd.to_numeric(
        production["production_t"], errors="coerce"
    )

    production = production.dropna(
        subset=["mineral_id", "mineral_name", "year", "production_t"]
    )

    production = production[production["production_t"] >= 0].copy()
    production["year"] = production["year"].astype(int)

    production = (
        production.groupby(
            ["mineral_id", "mineral_name", "year"],
            as_index=False,
        )["production_t"]
        .sum()
        .sort_values(["mineral_name", "year"])
    )

    return production


def select_complete_series(production: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Separa séries aptas ao benchmark das séries curtas ou incompletas."""
    summary = (
        production.groupby(["mineral_id", "mineral_name"], as_index=False)
        .agg(
            first_year=("year", "min"),
            last_year=("year", "max"),
            observed_years=("year", "nunique"),
            production_2025=("production_t", lambda values: 0.0),
        )
    )

    values_2025 = (
        production[production["year"] == BASE_YEAR]
        .groupby(["mineral_id", "mineral_name"], as_index=False)["production_t"]
        .sum()
        .rename(columns={"production_t": "production_2025"})
    )

    summary = summary.drop(columns=["production_2025"]).merge(
        values_2025,
        on=["mineral_id", "mineral_name"],
        how="left",
    )

    summary["production_2025"] = summary["production_2025"].fillna(0.0)

    complete = summary[
        (summary["observed_years"] >= MIN_YEARS_REQUIRED)
        & (summary["last_year"] == BASE_YEAR)
        & (summary["production_2025"] > 0)
    ].copy()

    incomplete = summary[
        ~summary.set_index(["mineral_id", "mineral_name"]).index.isin(
            complete.set_index(["mineral_id", "mineral_name"]).index
        )
    ].copy()

    complete = complete.sort_values("mineral_name")
    incomplete = incomplete.sort_values(
        ["observed_years", "mineral_name"],
        ascending=[False, True],
    )

    selected_ids = set(complete["mineral_id"])
    benchmark = production[production["mineral_id"].isin(selected_ids)].copy()

    benchmark = benchmark.merge(
        complete[
            [
                "mineral_id",
                "mineral_name",
                "first_year",
                "last_year",
                "observed_years",
                "production_2025",
            ]
        ],
        on=["mineral_id", "mineral_name"],
        how="inner",
    )

    benchmark["index_2025_100"] = (
        benchmark["production_t"] / benchmark["production_2025"] * 100
    )

    return benchmark, incomplete


def create_chart(benchmark: pd.DataFrame) -> None:
    """Gera gráfico das séries normalizadas para apresentação e verificação."""
    pivot = benchmark.pivot(
        index="year",
        columns="mineral_name",
        values="index_2025_100",
    ).sort_index()

    plt.figure(figsize=(14, 8))

    for mineral in pivot.columns:
        series = pivot[mineral].dropna()
        plt.plot(
            series.index,
            series.values,
            linewidth=1.8,
            alpha=0.9,
            label=mineral,
        )

    plt.axhline(
        100,
        color="#4b6273",
        linewidth=1,
        linestyle="--",
        alpha=0.8,
    )

    plt.title("Produção mineral observada — índice base 2025 = 100")
    plt.xlabel("Ano")
    plt.ylabel("Índice de produção")
    plt.grid(axis="y", alpha=0.22)
    plt.legend(
        title="Mineral",
        bbox_to_anchor=(1.02, 1),
        loc="upper left",
        fontsize=8,
    )
    plt.tight_layout()

    chart_path = OUTPUT_DIR / "production_benchmark_index_2025.png"
    plt.savefig(chart_path, dpi=180, bbox_inches="tight")
    plt.close()


def build_public_json(
    benchmark: pd.DataFrame,
    complete: pd.DataFrame,
    incomplete: pd.DataFrame,
) -> None:
    """Salva o formato que a plataforma web poderá ler diretamente."""
    records = (
        benchmark[
            [
                "mineral_id",
                "mineral_name",
                "year",
                "production_t",
                "index_2025_100",
            ]
        ]
        .sort_values(["mineral_name", "year"])
        .round({"production_t": 4, "index_2025_100": 2})
        .to_dict(orient="records")
    )

    minerals = (
        complete[
            [
                "mineral_id",
                "mineral_name",
                "first_year",
                "last_year",
                "observed_years",
                "production_2025",
            ]
        ]
        .sort_values("mineral_name")
        .round({"production_2025": 4})
        .to_dict(orient="records")
    )

    excluded = (
        incomplete[
            [
                "mineral_id",
                "mineral_name",
                "first_year",
                "last_year",
                "observed_years",
                "production_2025",
            ]
        ]
        .sort_values(["observed_years", "mineral_name"], ascending=[False, True])
        .round({"production_2025": 4})
        .to_dict(orient="records")
    )

    payload = {
        "title": "Benchmark de produção mineral",
        "source": "Squad 1 — interface Squad 1 / Squad 2",
        "production_basis": "beneficiada",
        "base_year": BASE_YEAR,
        "minimum_observed_years": MIN_YEARS_REQUIRED,
        "methodology": (
            "As séries são estaduais, observadas, válidas e em produção "
            "beneficiada. O índice 2025 = 100 permite comparar tendências "
            "entre minerais sem somar toneladas de substâncias diferentes. "
            "Este benchmark não converte os minerais adicionais em TWh."
        ),
        "minerals_in_benchmark": minerals,
        "minerals_not_in_benchmark": excluded,
        "series": records,
    }

    PUBLIC_OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    with PUBLIC_OUTPUT.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    production = load_production()
    benchmark, incomplete = select_complete_series(production)

    complete = (
        benchmark[
            [
                "mineral_id",
                "mineral_name",
                "first_year",
                "last_year",
                "observed_years",
                "production_2025",
            ]
        ]
        .drop_duplicates()
        .sort_values("mineral_name")
    )

    benchmark.to_csv(
        OUTPUT_DIR / "production_benchmark_series.csv",
        index=False,
        encoding="utf-8",
    )

    incomplete.to_csv(
        OUTPUT_DIR / "production_series_not_in_benchmark.csv",
        index=False,
        encoding="utf-8",
    )

    create_chart(benchmark)
    build_public_json(benchmark, complete, incomplete)

    print(
        "Benchmark concluído: "
        f"{len(complete)} minerais com pelo menos {MIN_YEARS_REQUIRED} anos "
        f"observados e produção disponível em {BASE_YEAR}."
    )
    print(f"Saída para o site: {PUBLIC_OUTPUT}")
    print(f"Saídas de análise: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
