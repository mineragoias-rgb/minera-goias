"""Create concise, presentation-ready summaries from model outputs."""

from pathlib import Path

import pandas as pd


MODEL_DIR = Path(__file__).resolve().parents[1]
BACKTEST_SUMMARY = MODEL_DIR / "outputs" / "backtest" / "backtest_summary.csv"
UNCERTAINTY_TOTAL = (
    MODEL_DIR / "outputs" / "uncertainty" / "uncertainty_total_goias.csv"
)
UNCERTAINTY_BY_MINERAL = (
    MODEL_DIR / "outputs" / "uncertainty" / "uncertainty_by_mineral.csv"
)
OUTPUT_DIR = MODEL_DIR / "outputs" / "presentation"

PRESENTATION_YEARS = [2035, 2040]
REFERENCE_SCENARIO = "referencia"
BAUXITE_ID = "MIN_005"


def load_inputs():
    required_files = [
        BACKTEST_SUMMARY,
        UNCERTAINTY_TOTAL,
        UNCERTAINTY_BY_MINERAL,
    ]

    missing_files = [str(path) for path in required_files if not path.exists()]

    if missing_files:
        raise FileNotFoundError(
            "Execute primeiro backtest, cenários e faixas de incerteza: "
            + ", ".join(missing_files)
        )

    backtest = pd.read_csv(BACKTEST_SUMMARY)
    total = pd.read_csv(UNCERTAINTY_TOTAL)
    by_mineral = pd.read_csv(UNCERTAINTY_BY_MINERAL)

    if backtest.empty or total.empty or by_mineral.empty:
        raise ValueError("Um dos outputs de entrada está vazio.")

    return backtest, total, by_mineral


def to_twh(frame, columns):
    result = frame.copy()

    for column in columns:
        result[column.replace("_mwh", "_twh")] = result[column] / 1_000_000

    return result.drop(columns=columns)


def build_scenario_summary(total):
    summary = total[total["year"].isin(PRESENTATION_YEARS)].copy()

    summary = to_twh(
        summary,
        [
            "lower_energy_demand_mwh",
            "base_energy_demand_mwh",
            "upper_energy_demand_mwh",
        ],
    )

    return summary.sort_values(["year", "scenario"]).reset_index(drop=True)


def build_reference_breakdown(by_mineral):
    detail = by_mineral[
        (by_mineral["scenario"] == REFERENCE_SCENARIO)
        & (by_mineral["year"] == 2040)
    ].copy()

    if detail.empty:
        raise ValueError("Não há dados do cenário de referência para 2040.")

    total_base = detail["base_energy_demand_mwh"].sum()
    total_width = (
        detail["upper_energy_demand_mwh"].sum()
        - detail["lower_energy_demand_mwh"].sum()
    )

    detail["base_energy_share_pct"] = (
        detail["base_energy_demand_mwh"] / total_base * 100
    )
    detail["uncertainty_width_mwh"] = (
        detail["upper_energy_demand_mwh"]
        - detail["lower_energy_demand_mwh"]
    )
    detail["uncertainty_width_share_pct"] = (
        detail["uncertainty_width_mwh"] / total_width * 100
    )

    detail = to_twh(
        detail,
        [
            "lower_energy_demand_mwh",
            "base_energy_demand_mwh",
            "upper_energy_demand_mwh",
            "uncertainty_width_mwh",
        ],
    )

    columns = [
        "mineral_id",
        "mineral_name",
        "production_error_pct",
        "lower_energy_demand_twh",
        "base_energy_demand_twh",
        "upper_energy_demand_twh",
        "base_energy_share_pct",
        "uncertainty_width_twh",
        "uncertainty_width_share_pct",
    ]

    return detail[columns].sort_values(
        "base_energy_demand_twh",
        ascending=False,
    ).reset_index(drop=True)


def build_bauxite_diagnostic(by_mineral):
    rows = []

    for year in PRESENTATION_YEARS:
        detail = by_mineral[
            (by_mineral["scenario"] == REFERENCE_SCENARIO)
            & (by_mineral["year"] == year)
        ].copy()

        for scope, selected in [
            ("all_five_minerals", detail),
            (
                "excluding_bauxite",
                detail[detail["mineral_id"] != BAUXITE_ID],
            ),
        ]:
            rows.append(
                {
                    "year": year,
                    "scenario": REFERENCE_SCENARIO,
                    "scope": scope,
                    "included_minerals": int(
                        selected["mineral_id"].nunique()
                    ),
                    "lower_energy_demand_twh": (
                        selected["lower_energy_demand_mwh"].sum() / 1_000_000
                    ),
                    "base_energy_demand_twh": (
                        selected["base_energy_demand_mwh"].sum() / 1_000_000
                    ),
                    "upper_energy_demand_twh": (
                        selected["upper_energy_demand_mwh"].sum() / 1_000_000
                    ),
                    "purpose": (
                        "scope_diagnostic_not_replacement_for_total_projection"
                    ),
                }
            )

    return pd.DataFrame(rows)


def build_backtest_summary(backtest):
    result = backtest.copy()
    result["mape_pct"] = result["mean_absolute_percentage_error"] * 100

    return result.drop(
        columns=["mean_absolute_percentage_error"]
    ).sort_values("mape_pct").reset_index(drop=True)


def main():
    backtest, total, by_mineral = load_inputs()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    build_scenario_summary(total).to_csv(
        OUTPUT_DIR / "scenario_summary_2035_2040.csv",
        index=False,
        encoding="utf-8-sig",
    )

    build_reference_breakdown(by_mineral).to_csv(
        OUTPUT_DIR / "reference_breakdown_2040.csv",
        index=False,
        encoding="utf-8-sig",
    )

    build_bauxite_diagnostic(by_mineral).to_csv(
        OUTPUT_DIR / "bauxite_scope_diagnostic.csv",
        index=False,
        encoding="utf-8-sig",
    )

    build_backtest_summary(backtest).to_csv(
        OUTPUT_DIR / "backtest_quality_summary.csv",
        index=False,
        encoding="utf-8-sig",
    )

    print("Presentation summaries created in:", OUTPUT_DIR)


if __name__ == "__main__":
    main()
