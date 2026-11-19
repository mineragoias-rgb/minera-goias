"""Generate transparent uncertainty bands for the real model outputs.

The bands combine two already documented sources of uncertainty:
1. the production MAPE observed in the historical backtest, by mineral; and
2. the +/- 10% range used in the energy-intensity sensitivity analysis.

They are scenario ranges, not statistical confidence intervals.
"""

from pathlib import Path

import pandas as pd


MODEL_DIR = Path(__file__).resolve().parents[1]
BACKTEST_SUMMARY = MODEL_DIR / "outputs" / "backtest" / "backtest_summary.csv"
FUTURE_DETAIL = (
    MODEL_DIR / "outputs" / "future" / "future_projection_by_mineral.csv"
)
OUTPUT_DIR = MODEL_DIR / "outputs" / "uncertainty"

INTENSITY_RANGE_PCT = 10.0


def load_inputs():
    if not BACKTEST_SUMMARY.exists() or not FUTURE_DETAIL.exists():
        raise FileNotFoundError(
            "Execute primeiro run_backtest.py e run_future_scenarios.py."
        )

    backtest = pd.read_csv(BACKTEST_SUMMARY)
    future = pd.read_csv(FUTURE_DETAIL)

    required_backtest = {
        "mineral_id",
        "mean_absolute_percentage_error",
    }
    required_future = {
        "mineral_id",
        "mineral_name",
        "production_basis",
        "year",
        "scenario",
        "energy_demand_mwh",
    }

    missing_backtest = required_backtest - set(backtest.columns)
    missing_future = required_future - set(future.columns)

    if missing_backtest or missing_future:
        raise ValueError(
            "Colunas ausentes nos outputs anteriores: "
            f"backtest={missing_backtest}, future={missing_future}"
        )

    if backtest["mineral_id"].duplicated().any():
        raise ValueError("O resumo do backtest possui minerais duplicados.")

    if (
        future["energy_demand_mwh"].isna().any()
        or (future["energy_demand_mwh"] < 0).any()
    ):
        raise ValueError("O output futuro possui demanda de energia inválida.")

    return backtest, future


def build_uncertainty_bands(backtest, future):
    error_by_mineral = backtest[
        ["mineral_id", "mean_absolute_percentage_error"]
    ].copy()

    detail = future.merge(error_by_mineral, on="mineral_id", how="left")

    if detail["mean_absolute_percentage_error"].isna().any():
        missing = detail.loc[
            detail["mean_absolute_percentage_error"].isna(),
            "mineral_id",
        ].unique()
        raise ValueError(f"Sem MAPE de backtest para: {', '.join(missing)}")

    intensity_range = INTENSITY_RANGE_PCT / 100

    detail["production_error_pct"] = (
        detail["mean_absolute_percentage_error"] * 100
    )
    detail["intensity_range_pct"] = INTENSITY_RANGE_PCT

    detail["lower_energy_demand_mwh"] = (
        detail["energy_demand_mwh"]
        * (1 - detail["mean_absolute_percentage_error"])
        * (1 - intensity_range)
    )
    detail["base_energy_demand_mwh"] = detail["energy_demand_mwh"]
    detail["upper_energy_demand_mwh"] = (
        detail["energy_demand_mwh"]
        * (1 + detail["mean_absolute_percentage_error"])
        * (1 + intensity_range)
    )

    detail["lower_energy_demand_mwh"] = (
        detail["lower_energy_demand_mwh"].clip(lower=0)
    )

    detail["uncertainty_method"] = (
        "production_backtest_mape_combined_with_plus_minus_10pct_intensity_range"
    )
    detail["interval_interpretation"] = (
        "scenario_range_not_statistical_confidence_interval"
    )

    columns = [
        "mineral_id",
        "mineral_name",
        "production_basis",
        "year",
        "scenario",
        "production_error_pct",
        "intensity_range_pct",
        "lower_energy_demand_mwh",
        "base_energy_demand_mwh",
        "upper_energy_demand_mwh",
        "uncertainty_method",
        "interval_interpretation",
    ]

    detail = detail[columns]

    if (
        detail["lower_energy_demand_mwh"]
        > detail["base_energy_demand_mwh"]
    ).any() or (
        detail["base_energy_demand_mwh"]
        > detail["upper_energy_demand_mwh"]
    ).any():
        raise ValueError("As faixas de incerteza não são monotônicas.")

    total = (
        detail.groupby(["year", "scenario"], as_index=False)
        .agg(
            lower_energy_demand_mwh=(
                "lower_energy_demand_mwh",
                "sum",
            ),
            base_energy_demand_mwh=(
                "base_energy_demand_mwh",
                "sum",
            ),
            upper_energy_demand_mwh=(
                "upper_energy_demand_mwh",
                "sum",
            ),
        )
    )

    total["intensity_range_pct"] = INTENSITY_RANGE_PCT
    total["uncertainty_method"] = (
        "sum_of_mineral_ranges_using_backtest_mape_and_plus_minus_10pct_intensity"
    )
    total["interval_interpretation"] = (
        "scenario_range_not_statistical_confidence_interval"
    )

    return detail, total


def main():
    backtest, future = load_inputs()
    by_mineral, total = build_uncertainty_bands(backtest, future)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    by_mineral.to_csv(
        OUTPUT_DIR / "uncertainty_by_mineral.csv",
        index=False,
        encoding="utf-8-sig",
    )

    total.to_csv(
        OUTPUT_DIR / "uncertainty_total_goias.csv",
        index=False,
        encoding="utf-8-sig",
    )

    print(total.to_string(index=False))


if __name__ == "__main__":
    main()
