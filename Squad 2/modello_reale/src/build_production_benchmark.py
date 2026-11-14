"""Benchmark de produção mineral além dos cinco minerais do modelo elétrico.

O benchmark usa produção beneficiada observada. Ele não converte minerais
adicionais em TWh: compara a evolução produtiva de cada mineral a partir do
primeiro ano com produção positiva, definido como índice 100.
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
LATEST_YEAR_REQUIRED = 2025


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
        production["production_t"],
        errors="coerce",
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
    """Seleciona séries longas e encontra a primeira produção positiva."""
    summary = (
        production.groupby(["mineral_id", "mineral_name"], as_index=False)
        .agg(
            first_observed_year=("year", "min"),
            last_year=("year", "max"),
            observed_years=("year", "nunique"),
        )
    )

    eligible = summary[
        (summary["observed_years"] >= MIN_YEARS_REQUIRED)
        & (summary["last_year"] == LATEST_YEAR_REQUIRED)
    ].copy()

    excluded = summary[
        ~summary.set_index(["mineral_id", "mineral_name"]).index.isin(
            eligible.set_index(["mineral_id", "mineral_name"]).index
        )
    ].copy()

    selected_ids = set(eligible["mineral_id"])
    benchmark = production[production["mineral_id"].isin(selected_ids)].copy()

    first_positive = (
        benchmark[benchmark["production_t"] > 0]
        .sort_values("year")
        .groupby(["mineral_id", "mineral_name"], as_index=False)
        .first()[["mineral_id", "mineral_name", "year", "production_t"]]
        .rename(
            columns={
                "year": "index_base_year",
                "production_t": "index_base_production_t",
            }
        )
    )

    eligible = eligible.merge(
        first_positive,
        on=["mineral_id", "mineral_name"],
        how="left",
    )

    eligible = eligible.dropna(
        subset=["index_base_year", "index_base_production_t"]
    ).copy()

    eligible["index_base_year"] = eligible["index_base_year"].astype(int)

    benchmark = benchmark.merge(
        eligible[
            [
                "mineral_id",
                "mineral_name",
                "first_observed_year",
                "last_year",
                "observed_years",
                "index_base_year",
                "index_base_production_t",
            ]
        ],
        on=["mineral_id", "mineral_name"],
        how="inner",
    )

    benchmark["index_first_year_100"] = (
        benchmark["production_t"]
        / benchmark["index_base_production_t"]
        * 100
    )

    production_2025 = (
        benchmark[benchmark["year"] == LATEST_YEAR_REQUIRED]
        .groupby(["mineral_id", "mineral_name"], as_index=False)["production_t"]
        .sum()
        .rename(columns={"production_t": "production_latest_t"})
    )

    eligible = eligible.merge(
        production_2025,
        on=["mineral_id", "mineral_name"],
        how="left",
    )

    eligible["production_latest_t"] = eligible[
        "production_latest_t"
    ].fillna(0.0)

    eligible["change_from_base_pct"] = (
        eligible["production_latest_t"]
        / eligible["index_base_production_t"]
        - 1
    ) * 100

    return (
        benchmark.sort_values(["mineral_name", "year"]),
        eligible.sort_values("mineral_name"),
        excluded.sort_values(
            ["observed_years", "mineral_name"],
            ascending=[False, True],
        ),
    )


def create_overview_chart(benchmark: pd.DataFrame) -> None:
    """Gera uma visão geral com todos os minerais em escala logarítmica."""
    figure, axis = plt.subplots(figsize=(14, 8))

    for mineral, series in benchmark.groupby("mineral_name"):
        series = series.sort_values("year")
        series = series[series["index_first_year_100"] > 0]

        axis.plot(
            series["year"],
            series["index_first_year_100"],
            linewidth=1.8,
            marker="o",
            markersize=2.8,
            label=mineral,
        )

    axis.axhline(
        100,
        color="#4b6273",
        linewidth=1.1,
        linestyle="--",
        alpha=0.85,
    )

    axis.set_yscale("log")
    axis.set_title(
        "Benchmark de produção mineral — índice base no primeiro ano positivo = 100",
        fontsize=15,
        fontweight="bold",
    )
    axis.set_xlabel("Ano")
    axis.set_ylabel("Índice de produção — escala logarítmica")
    axis.grid(axis="y", which="both", alpha=0.22)

    axis.legend(
        title="Mineral",
        bbox_to_anchor=(1.02, 1),
        loc="upper left",
        fontsize=8,
    )

    figure.tight_layout()

    figure.savefig(
        OUTPUT_DIR / "production_benchmark_overview_log.png",
        dpi=180,
        bbox_inches="tight",
    )
    plt.close(figure)


def create_panels_chart(benchmark: pd.DataFrame) -> None:
    """Gera painéis individuais para leitura detalhada de cada série."""
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
            benchmark["mineral_name"] == mineral
        ].sort_values("year")

        axis.plot(
            series["year"],
            series["index_first_year_100"],
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
        "Produção mineral observada — índice base no primeiro ano positivo = 100",
        fontsize=16,
        fontweight="bold",
        y=1.01,
    )

    figure.text(
        0.5,
        0.995,
        "Cada painel tem escala própria; toneladas não são somadas entre minerais.",
        ha="center",
        fontsize=10,
    )

    figure.tight_layout()

    figure.savefig(
        OUTPUT_DIR / "production_benchmark_panels_first_year.png",
        dpi=180,
        bbox_inches="tight",
    )
    plt.close(figure)


def records_for_json(data: pd.DataFrame) -> list[dict]:
    """Converte NaN para null e mantém JSON válido para o site."""
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
    """Gera o arquivo lido diretamente pelo painel web."""
    series = benchmark[
        [
            "mineral_id",
            "mineral_name",
            "year",
            "production_t",
            "index_first_year_100",
        ]
    ].copy()

    minerals = selected[
        [
            "mineral_id",
            "mineral_name",
            "first_observed_year",
            "index_base_year",
            "index_base_production_t",
            "last_year",
            "observed_years",
            "production_latest_t",
            "change_from_base_pct",
        ]
    ].copy()

    not_included = excluded[
        [
            "mineral_id",
            "mineral_name",
            "first_observed_year",
            "last_year",
            "observed_years",
        ]
    ].copy()

    payload = {
        "title": "Benchmark de produção mineral",
        "source": "Squad 1 — interface Squad 1 / Squad 2",
        "production_basis": "beneficiada",
        "latest_year": LATEST_YEAR_REQUIRED,
        "minimum_observed_years": MIN_YEARS_REQUIRED,
        "index_definition": (
            "Para cada mineral, o primeiro ano com produção positiva recebe "
            "índice 100. Os demais anos mostram a produção relativa a essa base."
        ),
        "methodology": (
            "Inclui séries estaduais, observadas, válidas e de produção "
            "beneficiada com pelo menos 12 anos e dado em 2025. Toneladas não "
            "são somadas entre minerais. O índice permite comparar a trajetória "
            "de cada mineral desde o início de sua série. O benchmark não "
            "atribui demanda elétrica aos minerais adicionais."
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

    selected.to_csv(
        OUTPUT_DIR / "production_benchmark_summary.csv",
        index=False,
        encoding="utf-8",
    )

    excluded.to_csv(
        OUTPUT_DIR / "production_series_not_in_benchmark.csv",
        index=False,
        encoding="utf-8",
    )

    create_overview_chart(benchmark)
    create_panels_chart(benchmark)
    build_public_json(benchmark, selected, excluded)

    print(
        f"Benchmark concluído: {len(selected)} séries históricas, "
        f"cada uma indexada ao primeiro ano com produção positiva."
    )
    print(f"Saída para o site: {PUBLIC_OUTPUT}")
    print(f"Saídas de análise: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
