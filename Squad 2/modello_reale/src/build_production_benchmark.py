"""Benchmark de produção mineral 2027–2040.

Inclui minerais sem coeficiente energético no escopo analítico por meio de
produção física: séries históricas, modelo selecionado por rolling backtest,
projeção de produção e faixa de incerteza. Não converte esses minerais em TWh.
"""

from __future__ import annotations

import json
import math

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from common import MODEL_DIR, ROOT, SQUAD1_INTERFACE


OUTPUT_DIR = MODEL_DIR / "outputs" / "production_benchmark"
PUBLIC_OUTPUT = ROOT / "public" / "data" / "previsao" / "production_benchmark_v1.json"

MIN_YEARS_REQUIRED = 12
LATEST_YEAR_REQUIRED = 2025
FORECAST_START = 2027
FORECAST_END = 2040
BACKTEST_YEARS = 3


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
    """Seleciona séries históricas longas para o benchmark."""
    summary = (
        production.groupby(["mineral_id", "mineral_name"], as_index=False)
        .agg(
            first_observed_year=("year", "min"),
            last_year=("year", "max"),
            observed_years=("year", "nunique"),
        )
    )

    selected = summary[
        (summary["observed_years"] >= MIN_YEARS_REQUIRED)
        & (summary["last_year"] == LATEST_YEAR_REQUIRED)
    ].copy()

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
                "first_observed_year",
                "last_year",
                "observed_years",
            ]
        ],
        on=["mineral_id", "mineral_name"],
        how="inner",
    )

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

    selected = selected.merge(
        first_positive,
        on=["mineral_id", "mineral_name"],
        how="inner",
    )

    benchmark = benchmark.merge(
        selected[
            [
                "mineral_id",
                "mineral_name",
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

    production_latest = (
        benchmark[benchmark["year"] == LATEST_YEAR_REQUIRED]
        .groupby(["mineral_id", "mineral_name"], as_index=False)["production_t"]
        .sum()
        .rename(columns={"production_t": "production_latest_t"})
    )

    selected = selected.merge(
        production_latest,
        on=["mineral_id", "mineral_name"],
        how="left",
    )

    selected["production_latest_t"] = selected[
        "production_latest_t"
    ].fillna(0.0)

    selected["change_from_base_pct"] = (
        selected["production_latest_t"]
        / selected["index_base_production_t"]
        - 1
    ) * 100

    return (
        benchmark.sort_values(["mineral_name", "year"]),
        selected.sort_values("mineral_name"),
        excluded.sort_values(
            ["observed_years", "mineral_name"],
            ascending=[False, True],
        ),
    )


def smape(actual: float, predicted: float) -> float:
    """Erro percentual simétrico: funciona também quando a produção é zero."""
    denominator = abs(actual) + abs(predicted)

    if denominator == 0:
        return 0.0

    return 200 * abs(actual - predicted) / denominator


def persistence_forecast(train_log: np.ndarray, horizon: int) -> float:
    """Mantém o último nível observado: apenas candidato de referência."""
    return float(train_log[-1])


def weighted_log_trend_forecast(train_log: np.ndarray, horizon: int) -> float:
    """Tendência logarítmica com maior peso para os anos recentes."""
    x = np.arange(len(train_log), dtype=float)
    weights = np.arange(1, len(train_log) + 1, dtype=float)

    slope, intercept = np.polyfit(
        x,
        train_log,
        1,
        w=weights,
    )

    return float(intercept + slope * (len(train_log) - 1 + horizon))


def holt_damped_forecast(
    train_log: np.ndarray,
    horizon: int,
    alpha: float,
    beta: float,
    phi: float,
) -> tuple[float, float]:
    """Holt com tendência amortecida, calculado sem dependência externa."""
    if len(train_log) < 2:
        return float(train_log[-1]), 0.0

    level = float(train_log[0])
    trend = float(train_log[1] - train_log[0])

    for value in train_log[1:]:
        previous_level = level
        level = alpha * float(value) + (1 - alpha) * (
            level + phi * trend
        )
        trend = beta * (level - previous_level) + (1 - beta) * phi * trend

    damped_sum = sum(phi**step for step in range(1, horizon + 1))

    return float(level + trend * damped_sum), trend


def fit_holt_parameters(train_log: np.ndarray) -> tuple[float, float, float]:
    """Escolhe parâmetros pelo menor erro de ajuste no período de treino."""
    candidates = []

    for alpha in (0.2, 0.4, 0.6, 0.8):
        for beta in (0.05, 0.15, 0.30, 0.50):
            for phi in (0.70, 0.80, 0.90, 0.95):
                if len(train_log) < 3:
                    candidates.append((float("inf"), alpha, beta, phi))
                    continue

                errors = []

                for end in range(2, len(train_log)):
                    predicted, _ = holt_damped_forecast(
                        train_log[:end],
                        1,
                        alpha,
                        beta,
                        phi,
                    )
                    errors.append((train_log[end] - predicted) ** 2)

                candidates.append(
                    (
                        float(np.mean(errors)),
                        alpha,
                        beta,
                        phi,
                    )
                )

    _, alpha, beta, phi = min(candidates, key=lambda item: item[0])

    return alpha, beta, phi


def forecast_candidate(
    method: str,
    train_production: np.ndarray,
    horizon: int,
) -> float:
    """Prevê em escala logarítmica e retorna toneladas não negativas."""
    train_log = np.log1p(np.maximum(train_production, 0))

    if method == "persistence":
        prediction_log = persistence_forecast(train_log, horizon)

    elif method == "weighted_log_trend":
        prediction_log = weighted_log_trend_forecast(train_log, horizon)

    elif method == "holt_damped":
        alpha, beta, phi = fit_holt_parameters(train_log)
        prediction_log, _ = holt_damped_forecast(
            train_log,
            horizon,
            alpha,
            beta,
            phi,
        )

    else:
        raise ValueError(f"Método desconhecido: {method}")

    return max(0.0, float(np.expm1(prediction_log)))


def evaluate_methods(production: np.ndarray) -> tuple[str, dict[str, float]]:
    """Compara candidatos em rolling backtest dos três últimos anos."""
    methods = [
        "persistence",
        "weighted_log_trend",
        "holt_damped",
    ]

    scores: dict[str, list[float]] = {method: [] for method in methods}

    first_test = max(8, len(production) - BACKTEST_YEARS)

    for split in range(first_test, len(production)):
        train = production[:split]
        actual = float(production[split])

        for method in methods:
            prediction = forecast_candidate(method, train, 1)
            scores[method].append(smape(actual, prediction))

    mean_scores = {
        method: float(np.mean(values))
        for method, values in scores.items()
        if values
    }

    selected = min(mean_scores, key=mean_scores.get)

    return selected, mean_scores


def forecast_series(
    benchmark: pd.DataFrame,
    selected: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Seleciona o melhor método e gera 2027–2040 com incerteza calibrada."""
    forecast_rows = []
    model_rows = []

    for mineral_id, historical in benchmark.groupby("mineral_id"):
        historical = historical.sort_values("year")
        production = historical["production_t"].to_numpy(dtype=float)

        method, scores = evaluate_methods(production)

        backtest_errors = []
        first_test = max(8, len(production) - BACKTEST_YEARS)

        for split in range(first_test, len(production)):
            prediction = forecast_candidate(
                method,
                production[:split],
                1,
            )
            actual = float(production[split])

            backtest_errors.append(
                abs(
                    math.log1p(actual)
                    - math.log1p(prediction)
                )
            )

        calibrated_error = float(np.median(backtest_errors))
        calibrated_error = max(0.12, min(calibrated_error, 1.25))

        mineral_name = historical["mineral_name"].iloc[0]
        last_observed_year = int(historical["year"].max())

        for year in range(last_observed_year + 1, FORECAST_END + 1):
            horizon = year - last_observed_year

            reference = forecast_candidate(
                method,
                production,
                horizon,
            )

            spread = min(
                1.75,
                calibrated_error * math.sqrt(horizon),
            )

            lower = max(
                0.0,
                float(np.expm1(math.log1p(reference) - spread)),
            )
            upper = max(
                reference,
                float(np.expm1(math.log1p(reference) + spread)),
            )

            if year >= FORECAST_START:
                forecast_rows.append(
                    {
                        "mineral_id": mineral_id,
                        "mineral_name": mineral_name,
                        "year": year,
                        "production_reference_t": reference,
                        "production_lower_t": lower,
                        "production_upper_t": upper,
                        "selected_method": method,
                    }
                )

        model_rows.append(
            {
                "mineral_id": mineral_id,
                "mineral_name": mineral_name,
                "selected_method": method,
                "backtest_smape_selected_pct": scores[method],
                "backtest_smape_persistence_pct": scores["persistence"],
                "backtest_smape_weighted_log_trend_pct": scores[
                    "weighted_log_trend"
                ],
                "backtest_smape_holt_damped_pct": scores["holt_damped"],
                "calibrated_log_error": calibrated_error,
            }
        )

    forecasts = pd.DataFrame(forecast_rows)
    models = pd.DataFrame(model_rows)

    selected = selected.merge(
        models,
        on=["mineral_id", "mineral_name"],
        how="left",
    )

    return forecasts, selected


def create_forecast_panels(
    benchmark: pd.DataFrame,
    forecasts: pd.DataFrame,
) -> None:
    """Painéis: eixo igual entre histórico e futuro de cada mineral."""
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

        historical = benchmark[
            benchmark["mineral_name"] == mineral
        ].sort_values("year")

        future = forecasts[
            forecasts["mineral_name"] == mineral
        ].sort_values("year")

        axis.plot(
            historical["year"],
            historical["production_t"],
            color="#14354e",
            linewidth=2.2,
            marker="o",
            markersize=3,
            label="Observado",
        )

        axis.fill_between(
            future["year"],
            future["production_lower_t"],
            future["production_upper_t"],
            color="#0f6fb0",
            alpha=0.15,
            label="Faixa de incerteza",
        )

        axis.plot(
            future["year"],
            future["production_reference_t"],
            color="#0f6fb0",
            linewidth=2.2,
            linestyle="--",
            marker="o",
            markersize=3,
            label="Referência",
        )

        axis.axvline(
            LATEST_YEAR_REQUIRED,
            color="#6f8290",
            linewidth=1,
            linestyle=":",
        )

        axis.set_title(mineral, fontsize=11, fontweight="bold")
        axis.grid(axis="y", alpha=0.25)
        axis.tick_params(axis="both", labelsize=8)
        axis.set_xlabel("Ano", fontsize=8)
        axis.set_ylabel("Produção (t)", fontsize=8)

    for index in range(len(minerals), rows * columns):
        axes.flat[index].axis("off")

    handles, labels = axes.flat[0].get_legend_handles_labels()

    figure.legend(
        handles,
        labels,
        loc="upper center",
        ncol=3,
        bbox_to_anchor=(0.5, 1.01),
        fontsize=10,
    )

    figure.suptitle(
        "Benchmark de produção mineral — histórico e projeção 2027–2040",
        fontsize=16,
        fontweight="bold",
        y=1.06,
    )

    figure.tight_layout()

    figure.savefig(
        OUTPUT_DIR / "production_benchmark_forecast_panels.png",
        dpi=180,
        bbox_inches="tight",
    )
    plt.close(figure)


def records_for_json(data: pd.DataFrame) -> list[dict]:
    """Converte DataFrame para JSON válido."""
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
    forecasts: pd.DataFrame,
) -> None:
    """Gera o arquivo consumido pelo painel web."""
    history = benchmark[
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
            "selected_method",
            "backtest_smape_selected_pct",
            "backtest_smape_persistence_pct",
            "backtest_smape_weighted_log_trend_pct",
            "backtest_smape_holt_damped_pct",
            "calibrated_log_error",
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
        "forecast_start": FORECAST_START,
        "forecast_end": FORECAST_END,
        "index_definition": (
            "Para cada mineral, o primeiro ano com produção positiva recebe "
            "índice 100. Os demais anos mostram a produção relativa a essa base."
        ),
        "forecast_methodology": (
            "Para cada mineral, três candidatos são comparados por rolling "
            "backtest: persistência, tendência logarítmica ponderada e Holt "
            "com tendência amortecida. A projeção de referência usa o menor "
            "sMAPE. A faixa baixa–alta é calibrada pelo erro histórico do "
            "método selecionado e não é um cenário econômico nem intervalo "
            "estatístico de confiança."
        ),
        "methodology": (
            "Inclui séries estaduais, observadas, válidas e de produção "
            "beneficiada com pelo menos 12 anos e dado em 2025. Toneladas não "
            "são somadas entre minerais. Minerais adicionais permanecem fora "
            "do total elétrico até que tenham coeficiente energético compatível."
        ),
        "minerals_in_benchmark": records_for_json(minerals),
        "minerals_not_in_benchmark": records_for_json(not_included),
        "series": records_for_json(history),
        "forecast": records_for_json(forecasts),
    }

    PUBLIC_OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    with PUBLIC_OUTPUT.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    production = load_production()
    benchmark, selected, excluded = select_series(production)

    forecasts, selected = forecast_series(benchmark, selected)

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

    forecasts.to_csv(
        OUTPUT_DIR / "production_benchmark_forecast_2027_2040.csv",
        index=False,
        encoding="utf-8",
    )

    excluded.to_csv(
        OUTPUT_DIR / "production_series_not_in_benchmark.csv",
        index=False,
        encoding="utf-8",
    )

    create_forecast_panels(benchmark, forecasts)

    build_public_json(
        benchmark,
        selected,
        excluded,
        forecasts,
    )

    print(
        f"Benchmark concluído: {len(selected)} minerais com previsão "
        f"de produção para {FORECAST_START}–{FORECAST_END}."
    )
    print(f"Saída para o site: {PUBLIC_OUTPUT}")
    print(f"Saídas de análise: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
