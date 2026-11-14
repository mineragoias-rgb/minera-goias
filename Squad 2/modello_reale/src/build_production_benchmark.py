"""Benchmark de produção mineral para ampliar a análise além dos cinco minerais do modelo.

O benchmark compara apenas produção observada. Não transforma minerais adicionais
em TWh sem um coeficiente energético validado.
"""

from __future__ import annotations

import json
import math

import matplotlib.pyplot as plt
import pandas as pd

from common import MODEL_DIR, ROOT, SQUAD1_INTERFACE


OUTPUT_DIR = MODEL_DIR / "outputs" / "production_benchmark"
PUBLIC_OUTPUT = ROOT / "public" / "data" / "previsao" / "production_benchmark_v1.json"

MIN_YEARS_REQUIRED = 12
BASE_YEAR = 2025


def load_production() -> pd.DataFrame:
    """Lê produção estadual, observada, válida e beneficiada."""
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

    return (
        production.groupby(
            ["mineral_id", "mineral_name", "year"],
            as_index=False,
        )["production_t"]
        .sum()
        .sort_values(["mineral_name", "year"])
    )


def select_series(
    production: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Seleciona as séries históricas aptas e marca as normalizáveis."""
    summary = (
        production.groupby(["mineral_id", "mineral_name"], as_index=False)
        .agg(
            first_year=("year", "min"),
            last_year=("year", "max"),
            observed_years=("year", "nunique"),
        )
    )

    production_2025 = (
        production[production["year"] == BASE_YEAR]
        .groupby(["mineral_id", "mineral_name"], as_index=False)["production_t"]
        .sum()
        .rename(columns={"production_t": "production_2025"})
    )

    summary = summary.merge(
        production_2025,
        on=["mineral_id", "mineral_name"],
        how="left",
    )
    summary["production_2025"] = summary["production_2025"].fillna(0.0)

    selected = summary[
        (summary["observed_years"] >= MIN_YEARS_REQUIRED)
        & (summary["last_year"] == BASE_YEAR)
    ].copy()

    selected["can_normalize_2025"] = selected["production_2025"] > 0

    excluded = summary[
        ~summary.set_index(["mineral_id", "mineral_name"]).index.isin(
            selected.set_index(["mineral_id", "mineral_name"]).index
        )
    ].copy()

    benchmark = production.merge(
        selected[
            [
                "mineral_id",
                "mineral_name",
                "first_year",
                "last_year",
                "observed_years",
                "production_2025",
                "can_normalize_2025",
            ]
        ],
        on=["mineral_id", "mineral_name"],
        how="inner",
    )

    benchmark["index_2025_100"] = pd.NA

    mask = benchmark["can_normalize_2025"]
    benchmark.loc[mask, "index_2025_100"] = (
        benchmark.loc[mask, "production_t"]
        / benchmark.loc[mask, "production_2025"]
        * 100
    )

    return (
        benchmark.sort_values(["mineral_name", "year"]),
        selected.sort_values("mineral_name"),
        excluded.sort_values(
            ["observed_years", "mineral_name"],
            ascending=[False, True],
        ),
    )


def create_chart(benchmark: pd.DataFrame) -> None:
    """Cria painéis individuais: evita que séries pequenas escondam as demais."""
    minerals = benchmark["mineral_name"].drop_duplicates().tolist()

    columns = 3
    rows = math.ceil(len(minerals) / columns)

    figure, axes = plt.subplots(
        rows,
        columns,
        figsize=(15, rows * 3.1),
        squeeze=False,
    )

    for index, mineral in enumerate(minerals):
        axis = axes.flat[index]

        series = benchmark[
            (benchmark["mineral_name"] == mineral)
            & (benchmark["can_normalize_2025"])
        ].sort_values("year")

        if series.empty:
            axis.text(
                0.5,
                0.55,
                "Sem índice 2025\nprodução igual a zero",
                ha="center",
                va="center",
                fontsize=10,
            )
            axis.set_title(mineral, fontsize=11, fontweight="bold")
            axis.set_xticks([])
            axis.set_yticks([])
            continue

        axis.plot(
            series["year"],
            series["index_2025_100"],
            color="#0f6fb0",
            linewidth=2,
            marker="o",
            markersize=3,
        )
        axis.axhline(
            100,
            color="#6f8290",
            linewidth=1,
            linestyle="--",
        )
        axis.set_title(mineral, fontsize=11, fontweight="bold")
        axis.grid(axis="y", alpha=0.25)
        axis.tick_params(axis="both", labelsize=8)
        axis.set_xlabel("Ano", fontsize=8)
        axis.set_ylabel("Índice", fontsize=8)

    for index in range(len(minerals), rows * columns):
        axes.flat[index].axis("off")

    figure.suptitle(
        "Produção mineral observada — índice base 2025 = 100",
        fontsize=16,
        fontweight="bold",
        y=1.01,
    )
    figure.text(
        0.5,
        0.995,
        "Cada painel tem escala própria; o objetivo é comparar tendências, não toneladas entre minerais.",
        ha="center",
        fontsize=10,
    )

    figure.tight_layout()

    figure.savefig(
        OUTPUT_DIR / "production_benchmark_panels_2025.png",
        dpi=180,
        bbox_inches="tight",
    )
    plt.close(figure)


def records_for_json(data: pd.DataFrame) -> list[dict]:
    """Converte NaN em null, para JSON válido no site."""
    return json.loads(
        data.to_json(
            orient="records",
            force_ascii=False,
        )
    )


def build_public_json(
    benchmark: pd.DataFrame,
    selected: pd.DataFrame,
    excluded: pd.DataFrame,
) -> None:
    """Gera o arquivo que o site poderá buscar diretamente."""
    series = benchmark[
        [
            "mineral_id",
            "mineral_name",
            "year",
            "production_t",
            "index_2025_100",
            "can_normalize_2025",
        ]
    ].copy()

    minerals = selected[
        [
            "mineral_id",
            "mineral_name",
            "first_year",
            "last_year",
            "observed_years",
            "production_2025",
            "can_normalize_2025",
        ]
    ].copy()

    not_included = excluded[
        [
            "mineral_id",
            "mineral_name",
            "first_year",
            "last_year",
            "observed_years",
            "production_2025",
        ]
    ].copy()

    payload = {
        "title": "Benchmark de produção mineral",
        "source": "Squad 1 — interface Squad 1 / Squad 2",
        "production_basis": "beneficiada",
        "base_year": BASE_YEAR,
        "minimum_observed_years": MIN_YEARS_REQUIRED,
        "methodology": (
            "Inclui séries estaduais, observadas, válidas e de produção "
            "beneficiada com pelo menos 12 anos e dado em 2025. Toneladas "
            "não são somadas entre minerais. O índice base 2025 = 100 "
            "compara a evolução de cada mineral separadamente. Séries com "
            "produção igual a zero em 2025 continuam no benchmark em "
            "toneladas, mas não recebem índice normalizado."
        ),
        "minerals_in_benchmark": records_for_json(minerals),
        "minerals_not_in_benchmark": records_for_json(not_included),
        "series": records_for_json(series),
    }

    PUBLIC_OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    with PUBLIC_OUTPUT.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    production = load_production()
    benchmark, selected, excluded = select_series(production)

    benchmark.to_csv(
        OUTPUT_DIR / "production_benchmark_series.csv",
        index=False,
        encoding="utf-8",
    )

    excluded.to_csv(
        OUTPUT_DIR / "production_series_not_in_benchmark.csv",
        index=False,
        encoding="utf-8",
    )

    create_chart(benchmark)
    build_public_json(benchmark, selected, excluded)

    normalized = selected["can_normalize_2025"].sum()

    print(
        f"Benchmark concluído: {len(selected)} séries históricas; "
        f"{normalized} com índice base {BASE_YEAR} = 100."
    )
    print(f"Saída para o site: {PUBLIC_OUTPUT}")
    print(f"Saídas de análise: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
