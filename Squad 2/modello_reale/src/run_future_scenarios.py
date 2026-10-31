from pathlib import Path

import pandas as pd

from common import load_historical_production, load_parameters


MODEL_DIR = Path(__file__).resolve().parents[1]
OUTPUT_DIR = MODEL_DIR / "outputs" / "future"

FIRST_FORECAST_YEAR = 2027
LAST_FORECAST_YEAR = 2040

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


def select_growth_assumption(
    mineral_id,
    scenario,
    historical_growth_rate,
    growth_adjustment,
):
    """Return the production-growth assumption used in each scenario."""
    if mineral_id == BAUXITE_MINERAL_ID:
        if scenario == "conservador":
            return -0.02, "bauxite_decline_from_last_observation"

        if scenario == "referencia":
            return 0.0, "bauxite_naive_last_observation"

        if scenario == "expansao":
            return (
                historical_growth_rate,
                "bauxite_recent_post_ramp_up_growth",
            )

        raise ValueError(f"Cenário inválido para bauxita: {scenario}")

    return (
        historical_growth_rate + growth_adjustment,
        "historical_compound_growth_with_scenario_adjustment",
    )


def run_future_scenarios():
    history = load_historical_production()
    energy, scenarios = load_parameters()

    results = []

    for mineral_id, mineral_history in history.groupby("mineral_id"):
        mineral_history = mineral_history.sort_values("year").reset_index(drop=True)
        trend_history, trend_method = select_trend_history(
            mineral_id,
            mineral_history,
        )

        mineral = energy[energy["mineral_id"] == mineral_id].iloc[0]
        base = mineral_history.iloc[-1]
        historical_growth_rate = calculate_annual_growth_rate(trend_history)
        trend_start_year = int(trend_history["year"].min())
        trend_end_year = int(trend_history["year"].max())

        for _, scenario_row in scenarios.iterrows():
            scenario = scenario_row["scenario"]
            growth_rate, projection_method = select_growth_assumption(
                mineral_id,
                scenario,
                historical_growth_rate,
                scenario_row["growth_adjustment"],
            )

            for year in range(FIRST_FORECAST_YEAR, LAST_FORECAST_YEAR + 1):
                years_after_base = int(year) - int(base["year"])

                projected_production = (
                    base["production_t"]
                    * (1 + growth_rate) ** years_after_base
                )

                energy_intensity = (
                    mineral["energy_intensity_mwh_t"]
                    * (1 - scenario_row["annual_efficiency_improvement"])
                    ** years_after_base
                )

                results.append(
                    {
                        "mineral_id": mineral_id,
                        "mineral_name": mineral["mineral_name"],
                        "production_basis": mineral["production_basis"],
                        "base_year": int(base["year"]),
                        "trend_start_year": trend_start_year,
                        "trend_end_year": trend_end_year,
                        "year": year,
                        "scenario": scenario,
                        "projected_production_t": projected_production,
                        "historical_growth_rate": historical_growth_rate,
                        "growth_adjustment": scenario_row["growth_adjustment"],
                        "applied_production_growth_rate": growth_rate,
                        "energy_intensity_mwh_t": energy_intensity,
                        "annual_efficiency_improvement": (
                            scenario_row["annual_efficiency_improvement"]
                        ),
                        "energy_demand_mwh": (
                            projected_production * energy_intensity
                        ),
                        "projection_method": projection_method,
                        "trend_method": trend_method,
                        "data_nature": "illustrative_projection",
                    }
                )

    detail = pd.DataFrame(results)

    expected_rows = (
        history["mineral_id"].nunique()
        * scenarios["scenario"].nunique()
        * (LAST_FORECAST_YEAR - FIRST_FORECAST_YEAR + 1)
    )

    if len(detail) != expected_rows or detail.isna().any().any():
        raise ValueError("Cobertura incompleta ou valores ausentes.")

    if (
        detail[
            [
                "projected_production_t",
                "energy_intensity_mwh_t",
                "energy_demand_mwh",
            ]
        ]
        < 0
    ).any().any():
        raise ValueError("Foram encontrados valores negativos.")

    energy_summary = (
        detail.groupby(["year", "scenario"], as_index=False)
        .agg(total_energy_demand_mwh=("energy_demand_mwh", "sum"))
    )

    energy_summary["coverage_note"] = (
        "Energia total dos cinco minerais cobertos. "
        "As toneladas não são agregadas, pois Cobre usa conteúdo mineral "
        "e os demais usam produção beneficiada."
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    detail.to_csv(
        OUTPUT_DIR / "future_projection_by_mineral.csv",
        index=False,
        encoding="utf-8-sig",
    )

    energy_summary.to_csv(
        OUTPUT_DIR / "future_energy_summary.csv",
        index=False,
        encoding="utf-8-sig",
    )

    print(energy_summary.to_string(index=False))


if __name__ == "__main__":
    run_future_scenarios()
    
