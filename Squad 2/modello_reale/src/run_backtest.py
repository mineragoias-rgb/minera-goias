from pathlib import Path

import pandas as pd

from common import load_historical_production


MODEL_DIR = Path(__file__).resolve().parents[1]
OUTPUT_DIR = MODEL_DIR / "outputs" / "backtest"

BAUXITE_MINERAL_ID = "MIN_005"
BAUXITE_RECENT_TREND_START_YEAR = 2018
MINIMUM_TREND_OBSERVATIONS = 4


def select_trend_history(mineral_id, history):
    """Select the historical window used to calculate the trend candidate."""
    if mineral_id == BAUXITE_MINERAL_ID:
        recent_history = history[
            history["year"] >= BAUXITE_RECENT_TREND_START_YEAR
        ].copy()

        if len(recent_history) >= MINIMUM_TREND_OBSERVATIONS:
            return recent_history, "recent_post_ramp_up_compound_growth_rate"

    return history.copy(), "full_historical_compound_growth_rate"


def calculate_annual_growth_rate(history):
    first = history.iloc[0]
    last = history.iloc[-1]
    years = int(last["year"]) - int(first["year"])

    if years <= 0 or first["production_t"] <= 0:
        raise ValueError("Série histórica inválida para calcular tendência.")

    return (last["production_t"] / first["production_t"]) ** (1 / years) - 1


def select_forecast(mineral_id, base_production, years_after_base, growth_rate):
    """Use the backtest-selected forecasting rule for each mineral."""
    if mineral_id == BAUXITE_MINERAL_ID:
        return base_production, "naive_last_observation_selected"

    return (
        base_production * (1 + growth_rate) ** years_after_base,
        "historical_compound_growth_rate_selected",
    )


def run_backtest():
    history = load_historical_production()
    results = []

    for mineral_id, mineral_history in history.groupby("mineral_id"):
        mineral_history = mineral_history.sort_values("year").reset_index(drop=True)

        # Os dois últimos anos disponíveis são ocultados ao modelo.
        test = mineral_history.tail(2)
        train = mineral_history.iloc[:-2]

        if len(train) < MINIMUM_TREND_OBSERVATIONS:
            raise ValueError(
                f"Série insuficiente para backtest: {mineral_id}"
            )

        trend_history, trend_method = select_trend_history(mineral_id, train)
        growth_rate = calculate_annual_growth_rate(trend_history)
        base = train.iloc[-1]
        trend_start_year = int(trend_history["year"].min())
        trend_end_year = int(trend_history["year"].max())

        for _, actual in test.iterrows():
            years_after_base = int(actual["year"]) - int(base["year"])
            trend_forecast = (
                base["production_t"]
                * (1 + growth_rate) ** years_after_base
            )
            naive_forecast = base["production_t"]
            selected_forecast, selected_method = select_forecast(
                mineral_id,
                base["production_t"],
                years_after_base,
                growth_rate,
            )

            absolute_error = abs(selected_forecast - actual["production_t"])
            absolute_percentage_error = (
                absolute_error / actual["production_t"]
            )
            trend_absolute_percentage_error = (
                abs(trend_forecast - actual["production_t"])
                / actual["production_t"]
            )
            naive_absolute_percentage_error = (
                abs(naive_forecast - actual["production_t"])
                / actual["production_t"]
            )

            results.append(
                {
                    "mineral_id": mineral_id,
                    "mineral_name": actual["mineral_name"],
                    "production_basis": actual["production_basis"],
                    "trend_start_year": trend_start_year,
                    "trend_end_year": trend_end_year,
                    "train_through_year": int(base["year"]),
                    "test_year": int(actual["year"]),
                    "actual_production_t": actual["production_t"],
                    "forecast_production_t": selected_forecast,
                    "trend_forecast_production_t": trend_forecast,
                    "naive_forecast_production_t": naive_forecast,
                    "annual_growth_rate_used": growth_rate,
                    "absolute_error_t": absolute_error,
                    "absolute_percentage_error": absolute_percentage_error,
                    "trend_absolute_percentage_error": (
                        trend_absolute_percentage_error
                    ),
                    "naive_absolute_percentage_error": (
                        naive_absolute_percentage_error
                    ),
                    "method": selected_method,
                    "trend_method": trend_method,
                }
            )

    detail = pd.DataFrame(results)

    if detail.empty or detail.isna().any().any():
        raise ValueError("Backtest gerou resultados ausentes.")

    summary = (
        detail.groupby(
            ["mineral_id", "mineral_name", "production_basis", "method"],
            as_index=False,
        )
        .agg(
            tested_years=("test_year", "count"),
            mean_absolute_percentage_error=(
                "absolute_percentage_error",
                "mean",
            ),
            trend_mean_absolute_percentage_error=(
                "trend_absolute_percentage_error",
                "mean",
            ),
            naive_mean_absolute_percentage_error=(
                "naive_absolute_percentage_error",
                "mean",
            ),
        )
    )

    summary["naive_minus_selected_mape_pct_points"] = (
        summary["naive_mean_absolute_percentage_error"]
        - summary["mean_absolute_percentage_error"]
    ) * 100

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    detail.to_csv(
        OUTPUT_DIR / "backtest_detail.csv",
        index=False,
        encoding="utf-8-sig",
    )

    summary.to_csv(
        OUTPUT_DIR / "backtest_summary.csv",
        index=False,
        encoding="utf-8-sig",
    )

    print(summary.to_string(index=False))


if __name__ == "__main__":
    run_backtest()
