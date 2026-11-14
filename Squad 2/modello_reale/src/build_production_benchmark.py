"""Previsões de produção mineral para o benchmark fora do modelo elétrico.

Os minerais adicionais permanecem fora do total em TWh até existir um
coeficiente energético compatível. Este arquivo prevê somente toneladas.
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
LAST_OBSERVED_YEAR = 2025
FORECAST_START = 2027
FORECAST_END = 2040
MAX_ACCEPTABLE_SMAPE = 35.0
MIN_IMPROVEMENT_VS_PERSISTENCE = 0.15


def records(frame: pd.DataFrame) -> list[dict]:
    return json.loads(frame.to_json(orient="records", force_ascii=False))


def smape(actual: np.ndarray, forecast: np.ndarray) -> float:
    denominator = np.abs(actual) + np.abs(forecast)
    valid = denominator > 0
    if not valid.any():
        return 0.0
    return float(
        np.mean(
            200.0
            * np.abs(forecast[valid] - actual[valid])
            / denominator[valid]
        )
    )


def read_production() -> pd.DataFrame:
    raw = pd.read_csv(SQUAD1_INTERFACE)

    frame = raw[
        (raw["nivel_agregacao"] == "estado")
        & (raw["valor_observado_estimado"] == "observado")
        & (raw["status_validacao"] == "valido")
        & (raw["production_basis"].fillna("").str.lower() == "beneficiada")
    ].copy()

    frame["year"] = pd.to_numeric(frame["year"], errors="coerce")
    frame["production_t"] = pd.to_numeric(
        frame["production_t"], errors="coerce"
    )

    frame = frame.dropna(
        subset=["mineral_id", "mineral_name", "year", "production_t"]
    )
    frame = frame[frame["production_t"] >= 0].copy()
    frame["year"] = frame["year"].astype(int)

    return (
        frame.groupby(
            ["mineral_id", "mineral_name", "year"],
            as_index=False,
        )["production_t"]
        .sum()
        .sort_values(["mineral_name", "year"])
    )


def fit_persistence(values: np.ndarray, horizon: int) -> np.ndarray:
    return np.repeat(float(values[-1]), horizon)


def fit_weighted_log_trend(
    values: np.ndarray,
    horizon: int,
) -> np.ndarray:
    log_values = np.log1p(values)
    x = np.arange(len(log_values), dtype=float)
    weights = np.linspace(0.35, 1.0, len(log_values))

    slope, intercept = np.polyfit(
        x,
        log_values,
        1,
        w=weights,
    )

    future_x = np.arange(
        len(log_values),
        len(log_values) + horizon,
        dtype=float,
    )

    return np.maximum(
        0.0,
        np.expm1(intercept + slope * future_x),
    )


def fit_holt_damped(values: np.ndarray, horizon: int) -> np.ndarray:
    """Holt simples em log, com tendência amortecida."""

    y = np.log1p(values)

    level = float(y[0])
    trend = float(y[1] - y[0]) if len(y) > 1 else 0.0

    alpha = 0.55
    beta = 0.20
    phi = 0.72

    for value in y[1:]:
        previous_level = level
        level = alpha * value + (1.0 - alpha) * (
            level + phi * trend
        )
        trend = beta * (level - previous_level) + (
            1.0 - beta
        ) * phi * trend

    steps = np.arange(1, horizon + 1, dtype=float)
    damped_steps = phi * (
        1.0 - np.power(phi, steps)
    ) / (1.0 - phi)

    return np.maximum(
        0.0,
        np.expm1(level + damped_steps * trend),
    )


METHODS = {
    "persistence": fit_persistence,
    "weighted_log_trend": fit_weighted_log_trend,
    "holt_damped": fit_holt_damped,
}


def backtest(values: np.ndarray) -> dict[str, float]:
    """Deixa os últimos três anos fora e mede o erro de cada método."""

    test_size = min(3, max(2, len(values) // 4))

    train = values[:-test_size]
    actual = values[-test_size:]

    return {
        name: smape(actual, function(train, test_size))
        for name, function in METHODS.items()
    }


def select_method(scores: dict[str, float]) -> str:
    """Tendência só entra se superar persistência de forma clara."""

    persistence_score = scores["persistence"]

    eligible = {
        name: score
        for name, score in scores.items()
        if score <= MAX_ACCEPTABLE_SMAPE
        and (
            name == "persistence"
            or score
            <= persistence_score
            * (1.0 - MIN_IMPROVEMENT_VS_PERSISTENCE)
        )
    }

    if not eligible:
        return "persistence"

    return min(eligible, key=eligible.get)


def build() -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
]:
    production = read_production()

    counts = (
        production.groupby(
            ["mineral_id", "mineral_name"],
            as_index=False,
        )
        .agg(
            first_observed_year=("year", "min"),
            last_year=("year", "max"),
            observed_years=("year", "nunique"),
        )
    )

    eligible = counts[
        (counts["observed_years"] >= MIN_YEARS_REQUIRED)
        & (counts["last_year"] == LAST_OBSERVED_YEAR)
    ].copy()

    included = production.merge(
        eligible[["mineral_id", "mineral_name"]],
        on=["mineral_id", "mineral_name"],
    )

    excluded = counts.merge(
        eligible[["mineral_id", "mineral_name"]],
        on=["mineral_id", "mineral_name"],
        how="left",
        indicator=True,
    )

    excluded = excluded[
        excluded["_merge"] == "left_only"
    ].drop(columns="_merge")

    summaries = []
    forecasts = []

    for (
        mineral_id,
        mineral_name,
    ), group in included.groupby(
        ["mineral_id", "mineral_name"],
        sort=True,
    ):
        group = group.sort_values("year")
        values = group["production_t"].to_numpy(dtype=float)

        first_positive = group[group["production_t"] > 0].iloc[0]
        base = float(first_positive["production_t"])

        scores = backtest(values)
        latest = float(values[-1])

        forecast_eligible = latest > 0

        method = (
            select_method(scores)
            if forecast_eligible
            else "not_forecastable_zero_2025"
        )

        log_error = (
            max(
                0.12,
                min(
                    0.60,
                    scores.get(
                        method,
                        scores["persistence"],
                    )
                    / 100.0,
                ),
            )
            if forecast_eligible
            else None
        )

        summaries.append(
            {
                "mineral_id": mineral_id,
                "mineral_name": mineral_name,
                "first_observed_year": int(
                    group["year"].min()
                ),
                "index_base_year": int(
                    first_positive["year"]
                ),
                "index_base_production_t": base,
                "last_year": int(group["year"].max()),
                "observed_years": int(
                    group["year"].nunique()
                ),
                "production_latest_t": latest,
                "change_from_base_pct": (
                    latest / base - 1.0
                )
                * 100.0,
                "forecast_eligible": forecast_eligible,
                "selected_method": method,
                "backtest_smape_selected_pct": scores.get(
                    method
                ),
                "backtest_smape_persistence_pct": scores[
                    "persistence"
                ],
                "backtest_smape_weighted_log_trend_pct": scores[
                    "weighted_log_trend"
                ],
                "backtest_smape_holt_damped_pct": scores[
                    "holt_damped"
                ],
                "calibrated_log_error": log_error,
            }
        )

        if not forecast_eligible:
            continue

        reference = METHODS[method](
            values,
            FORECAST_END - FORECAST_START + 1,
        )

        for step, (year, point) in enumerate(
            zip(
                range(FORECAST_START, FORECAST_END + 1),
                reference,
            ),
            start=1,
        ):
            spread = min(
                1.0,
                log_error * math.sqrt(step),
            )

            forecasts.append(
                {
                    "mineral_id": mineral_id,
                    "mineral_name": mineral_name,
                    "year": year,
                    "production_reference_t": float(point),
                    "production_lower_t": float(
                        point * math.exp(-spread)
                    ),
                    "production_upper_t": float(
                        point * math.exp(spread)
                    ),
                    "selected_method": method,
                }
            )

    series = included.copy()

    series["index_first_year_100"] = series.groupby(
        "mineral_id"
    )["production_t"].transform(
        lambda values: values
        / values[values.gt(0)].iloc[0]
        * 100.0
    )

    return (
        series,
        pd.DataFrame(summaries),
        pd.DataFrame(forecasts),
        excluded,
    )


def chart(
    series: pd.DataFrame,
    forecasts: pd.DataFrame,
) -> None:
    minerals = sorted(series["mineral_name"].unique())

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

        observed = series[
            series["mineral_name"] == mineral
        ].sort_values("year")

        projected = forecasts[
            forecasts["mineral_name"] == mineral
        ].sort_values("year")

        axis.plot(
            observed["year"],
            observed["production_t"],
            color="#123a5a",
            marker="o",
            markersize=2.5,
            linewidth=1.8,
            label="Observada",
        )

        if not projected.empty:
            axis.plot(
                projected["year"],
                projected["production_reference_t"],
                "--",
                color="#168a7a",
                linewidth=1.8,
                label="Projeção",
            )

            axis.fill_between(
                projected["year"],
                projected["production_lower_t"],
                projected["production_upper_t"],
                color="#168a7a",
                alpha=0.16,
            )

        axis.set_title(
            mineral,
            fontsize=10,
            fontweight="bold",
        )
        axis.grid(axis="y", alpha=0.22)
        axis.tick_params(labelsize=7)

    for index in range(len(minerals), rows * columns):
        axes.flat[index].axis("off")

    figure.suptitle(
        "Produção observada e projeção prudente por mineral",
        fontsize=15,
        fontweight="bold",
    )

    figure.tight_layout()

    figure.savefig(
        OUTPUT_DIR / "production_benchmark_forecast_panels.png",
        dpi=180,
        bbox_inches="tight",
    )

    plt.close(figure)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    PUBLIC_OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    series, summary, forecasts, excluded = build()

    summary = summary.sort_values("mineral_name")
    series = series.sort_values(["mineral_name", "year"])
    forecasts = forecasts.sort_values(
        ["mineral_name", "year"]
    )

    series.to_csv(
        OUTPUT_DIR / "production_benchmark_series.csv",
        index=False,
    )

    summary.to_csv(
        OUTPUT_DIR / "production_benchmark_summary.csv",
        index=False,
    )

    forecasts.to_csv(
        OUTPUT_DIR
        / "production_benchmark_forecast_2027_2040.csv",
        index=False,
    )

    excluded.to_csv(
        OUTPUT_DIR / "production_series_not_in_benchmark.csv",
        index=False,
    )

    chart(series, forecasts)

    payload = {
        "title": "Mineral production benchmark",
        "source": (
            "Squad 1 consolidated observed state production"
        ),
        "production_basis": "beneficiada",
        "latest_year": LAST_OBSERVED_YEAR,
        "minimum_observed_years": MIN_YEARS_REQUIRED,
        "forecast_start": FORECAST_START,
        "forecast_end": FORECAST_END,
        "index_definition": (
            "First positive observed production year = 100."
        ),
        "methodology": (
            "Observed state-level beneficiated production with "
            "at least 12 years and a 2025 observation. Tonnes "
            "are not aggregated between minerals."
        ),
        "forecast_methodology": (
            "Three candidates are compared by rolling backtest: "
            "persistence, weighted logarithmic trend and damped "
            "Holt. A trend is used only when it improves "
            "persistence by at least 15% and its sMAPE is at "
            "most 35%. Otherwise the reference is persistence. "
            "Ranges are error-calibrated scenario bands, not "
            "confidence intervals."
        ),
        "minerals_in_benchmark": records(summary),
        "minerals_not_in_benchmark": records(
            excluded.sort_values("mineral_name")
        ),
        "series": records(series),
        "forecast": records(forecasts),
    }

    PUBLIC_OUTPUT.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(f"Created {PUBLIC_OUTPUT}")


if __name__ == "__main__":
    main()
