"""Generate transparent, presentation-ready figures from validated model outputs."""

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter
import pandas as pd


MODEL_DIR = Path(__file__).resolve().parents[1]
FUTURE_SUMMARY = MODEL_DIR / "outputs" / "future" / "future_energy_summary.csv"
UNCERTAINTY_TOTAL = MODEL_DIR / "outputs" / "uncertainty" / "uncertainty_total_goias.csv"
UNCERTAINTY_BY_MINERAL = (
    MODEL_DIR / "outputs" / "uncertainty" / "uncertainty_by_mineral.csv"
)
BACKTEST_SUMMARY = MODEL_DIR / "outputs" / "backtest" / "backtest_summary.csv"
OUTPUT_DIR = MODEL_DIR / "outputs" / "presentation" / "charts"

REFERENCE_SCENARIO = "referencia"
SCENARIO_LABELS = {
    "conservador": "Conservador",
    "referencia": "Referência",
    "expansao": "Expansão",
}
SCENARIO_COLORS = {
    "conservador": "#4C78A8",
    "referencia": "#F58518",
    "expansao": "#54A24B",
}


def load_inputs():
    required_files = [
        FUTURE_SUMMARY,
        UNCERTAINTY_TOTAL,
        UNCERTAINTY_BY_MINERAL,
        BACKTEST_SUMMARY,
    ]
    missing_files = [str(path) for path in required_files if not path.exists()]

    if missing_files:
        raise FileNotFoundError(
            "Execute primeiro backtest, cenários e faixas de incerteza: "
            + ", ".join(missing_files)
        )

    return (
        pd.read_csv(FUTURE_SUMMARY),
        pd.read_csv(UNCERTAINTY_TOTAL),
        pd.read_csv(UNCERTAINTY_BY_MINERAL),
        pd.read_csv(BACKTEST_SUMMARY),
    )


def configure_chart_style():
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 10,
            "axes.titlesize": 14,
            "axes.titleweight": "bold",
            "axes.labelsize": 11,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.alpha": 0.22,
            "grid.linestyle": "--",
            "figure.dpi": 160,
            "savefig.dpi": 220,
        }
    )


def save_figure(figure, file_name):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    figure.tight_layout()
    figure.savefig(OUTPUT_DIR / file_name, bbox_inches="tight")
    plt.close(figure)


def plot_scenarios_with_ranges(uncertainty_total):
    data = uncertainty_total.copy().sort_values(["scenario", "year"])
    figure, axis = plt.subplots(figsize=(10, 5.8))

    for scenario in ["conservador", "referencia", "expansao"]:
        series = data[data["scenario"] == scenario].sort_values("year")

        if series.empty:
            raise ValueError(f"Cenário ausente no output: {scenario}")

        years = series["year"]
        lower = series["lower_energy_demand_mwh"] / 1_000_000
        base = series["base_energy_demand_mwh"] / 1_000_000
        upper = series["upper_energy_demand_mwh"] / 1_000_000
        color = SCENARIO_COLORS[scenario]

        axis.fill_between(years, lower, upper, color=color, alpha=0.11)
        axis.plot(
            years,
            base,
            color=color,
            linewidth=2.5,
            label=SCENARIO_LABELS[scenario],
        )

    axis.set_title("Demanda elétrica projetada por cenário")
    axis.set_xlabel("Ano")
    axis.set_ylabel("Demanda elétrica (TWh)")
    axis.set_xticks(sorted(data["year"].unique()))
    axis.legend(title="Cenário", ncols=3, frameon=False, loc="upper left")
    axis.text(
        0.01,
        -0.19,
        "Áreas sombreadas: faixas de cenário baseadas no erro do backtest por mineral e em ±10% de intensidade energética; não são intervalos de confiança estatísticos.",
        transform=axis.transAxes,
        fontsize=8.5,
        color="#4a4a4a",
        wrap=True,
    )

    save_figure(figure, "scenario_paths_with_uncertainty.png")


def plot_reference_breakdown_2040(uncertainty_by_mineral):
    data = uncertainty_by_mineral[
        (uncertainty_by_mineral["scenario"] == REFERENCE_SCENARIO)
        & (uncertainty_by_mineral["year"] == 2040)
    ].copy()

    if data.empty:
        raise ValueError("Não há dados do cenário de referência para 2040.")

    data = data.sort_values("base_energy_demand_mwh", ascending=True)
    base = data["base_energy_demand_mwh"] / 1_000_000
    lower = data["lower_energy_demand_mwh"] / 1_000_000
    upper = data["upper_energy_demand_mwh"] / 1_000_000
    errors = [base - lower, upper - base]

    colors = [
        "#E45756" if mineral_id == "MIN_005" else "#4C78A8"
        for mineral_id in data["mineral_id"]
    ]

    figure, axis = plt.subplots(figsize=(9.5, 5.6))
    bars = axis.barh(
        data["mineral_name"],
        base,
        xerr=errors,
        capsize=4,
        color=colors,
        alpha=0.9,
        error_kw={"ecolor": "#303030", "elinewidth": 1.2},
    )

    for bar, value in zip(bars, base):
        axis.text(
            value + 0.15,
            bar.get_y() + bar.get_height() / 2,
            f"{value:.2f}",
            va="center",
            fontsize=9,
        )

    axis.set_title("Composição da demanda elétrica em 2040 — cenário de referência")
    axis.set_xlabel("Demanda elétrica (TWh)")
    axis.text(
        0.01,
        -0.16,
        "Barras: projeção central. Linhas: faixa de cenário por mineral. A bauxita é destacada porque concentra a maior parcela da demanda e da incerteza.",
        transform=axis.transAxes,
        fontsize=8.5,
        color="#4a4a4a",
        wrap=True,
    )

    save_figure(figure, "reference_2040_mineral_breakdown.png")


def plot_backtest_quality(backtest_summary):
    data = backtest_summary.copy()
    data["mape_pct"] = data["mean_absolute_percentage_error"] * 100
    data = data.sort_values("mape_pct", ascending=True)

    colors = [
        "#E45756" if mineral_id == "MIN_005" else "#72B7B2"
        for mineral_id in data["mineral_id"]
    ]

    figure, axis = plt.subplots(figsize=(8.8, 5.3))
    bars = axis.barh(data["mineral_name"], data["mape_pct"], color=colors)

    for bar, value in zip(bars, data["mape_pct"]):
        axis.text(
            value + 0.7,
            bar.get_y() + bar.get_height() / 2,
            f"{value:.1f}%",
            va="center",
            fontsize=9,
        )

    axis.set_title("Validação retrospectiva: erro médio absoluto percentual")
    axis.set_xlabel("MAPE")
    axis.xaxis.set_major_formatter(PercentFormatter(xmax=100))
    axis.text(
        0.01,
        -0.16,
        "A bauxita concentra o maior erro histórico; por isso seu resultado é tratado com uma faixa de cenário mais ampla, e não como uma previsão pontual precisa.",
        transform=axis.transAxes,
        fontsize=8.5,
        color="#4a4a4a",
        wrap=True,
    )

    save_figure(figure, "backtest_quality_by_mineral.png")


def main():
    _, uncertainty_total, uncertainty_by_mineral, backtest_summary = load_inputs()
    configure_chart_style()

    plot_scenarios_with_ranges(uncertainty_total)
    plot_reference_breakdown_2040(uncertainty_by_mineral)
    plot_backtest_quality(backtest_summary)

    print("Presentation charts created in:", OUTPUT_DIR)


if __name__ == "__main__":
    main()
