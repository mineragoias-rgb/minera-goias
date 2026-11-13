from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from common import FINAL_ENERGY_PARAMETERS, MODEL_DIR


FUTURE_OUTPUT = (
    MODEL_DIR
    / "outputs"
    / "future"
    / "future_projection_by_mineral.csv"
)

OUTPUT_DIR = MODEL_DIR / "outputs" / "energy_comparison"


COLORS = {
    "Níquel": "#1976A3",
    "Alumínio (Bauxita)": "#D97A1B",
    "Cobre": "#B85450",
    "Fosfato": "#7157A6",
    "Amianto": "#5A9E6F",
}


def load_comparison_data():
    if not FUTURE_OUTPUT.exists():
        raise FileNotFoundError(
            "Não encontrei future_projection_by_mineral.csv. "
            "Execute run_future_scenarios.py antes deste script."
        )

    energy = pd.read_csv(FINAL_ENERGY_PARAMETERS)
    future = pd.read_csv(FUTURE_OUTPUT)

    reference_2040 = future[
        (future["scenario"] == "referencia")
        & (future["year"] == 2040)
    ].copy()

    required = [
        "mineral_id",
        "mineral_name",
        "production_basis",
        "energy_intensity_mwh_t",
        "data_nature",
        "coverage_share",
        "confianca",
    ]

    missing = set(required) - set(energy.columns)
    if missing:
        raise ValueError(
            "Colunas ausentes na base de intensidade: "
            + ", ".join(sorted(missing))
        )

    comparison = reference_2040.merge(
        energy[required],
        on=["mineral_id", "mineral_name", "production_basis"],
        how="left",
        suffixes=("_projection", "_base"),
    )

    if comparison["energy_intensity_mwh_t_base"].isna().any():
        missing_minerals = comparison.loc[
            comparison["energy_intensity_mwh_t_base"].isna(),
            "mineral_name",
        ].tolist()
        raise ValueError(
            "Minerais sem coeficiente energético na base final: "
            + ", ".join(missing_minerals)
        )

    comparison["energy_demand_twh_2040"] = (
        comparison["energy_demand_mwh"] / 1_000_000
    )

    total_twh = comparison["energy_demand_twh_2040"].sum()

    comparison["share_of_total_pct"] = (
        comparison["energy_demand_twh_2040"] / total_twh * 100
    )

    comparison = comparison.rename(
        columns={
            "energy_intensity_mwh_t_base": "energy_intensity_mwh_t",
            "data_nature": "intensity_data_nature",
            "coverage_share": "production_coverage_share",
            "confianca": "confidence",
        }
    )

    comparison = comparison[
        [
            "mineral_id",
            "mineral_name",
            "production_basis",
            "energy_intensity_mwh_t",
            "intensity_data_nature",
            "production_coverage_share",
            "confidence",
            "projected_production_t",
            "energy_demand_mwh",
            "energy_demand_twh_2040",
            "share_of_total_pct",
        ]
    ].sort_values("energy_demand_twh_2040", ascending=False)

    return comparison


def build_candidate_review():
    return pd.DataFrame(
        [
            {
                "mineral_name": "Nióbio",
                "production_history": "Produção beneficiada disponível de 2010 a 2025.",
                "energy_evidence": (
                    "Há evidência de energia CCEE, mas em base de produção "
                    "que ainda precisa ser conciliada com o modelo."
                ),
                "current_status": (
                    "Candidato à expansão após validação da base produtiva "
                    "e do coeficiente energético."
                ),
            },
            {
                "mineral_name": "Ouro",
                "production_history": "Produção beneficiada disponível de 2010 a 2025.",
                "energy_evidence": (
                    "Há evidência de energia em 2025, mas a unidade e o "
                    "denominador estimado exigem validação adicional."
                ),
                "current_status": (
                    "Não entra no total energético até validar unidade, "
                    "cobertura e compatibilidade do coeficiente."
                ),
            },
            {
                "mineral_name": "Monazita e Terras-Raras",
                "production_history": (
                    "Produção beneficiada disponível apenas de 2023 a 2025."
                ),
                "energy_evidence": (
                    "Há evidência de energia CCEE em 2025."
                ),
                "current_status": (
                    "Série histórica curta demais para backtest e projeção "
                    "robusta nesta versão."
                ),
            },
        ]
    )


def plot_energy_intensity(comparison):
    chart = comparison.sort_values(
        "energy_intensity_mwh_t",
        ascending=True,
    )

    colors = [
        COLORS.get(mineral, "#627D98")
        for mineral in chart["mineral_name"]
    ]

    fig, ax = plt.subplots(figsize=(10, 5.8))
    bars = ax.barh(
        chart["mineral_name"],
        chart["energy_intensity_mwh_t"],
        color=colors,
    )

    for bar, value in zip(bars, chart["energy_intensity_mwh_t"]):
        ax.text(
            bar.get_width(),
            bar.get_y() + bar.get_height() / 2,
            f" {value:,.3f} MWh/t",
            va="center",
            fontsize=10,
        )

    ax.set_title(
        "Intensidade energética por mineral",
        fontsize=16,
        fontweight="bold",
    )
    ax.set_xlabel("MWh por tonelada na base produtiva do modelo")
    ax.grid(axis="x", linestyle="--", alpha=0.35)
    ax.set_axisbelow(True)

    fig.text(
        0.01,
        0.01,
        (
            "Cobre usa conteúdo mineral; os demais usam produção beneficiada. "
            "A bauxita utiliza benchmark proxy, não consumo CCEE observado."
        ),
        fontsize=8.5,
        color="#4A5568",
    )

    fig.tight_layout(rect=[0, 0.06, 1, 1])
    fig.savefig(
        OUTPUT_DIR / "energy_intensity_by_mineral.png",
        dpi=180,
        bbox_inches="tight",
    )
    plt.close(fig)


def plot_energy_contribution(comparison):
    chart = comparison.sort_values(
        "energy_demand_twh_2040",
        ascending=True,
    )

    colors = [
        COLORS.get(mineral, "#627D98")
        for mineral in chart["mineral_name"]
    ]

    fig, ax = plt.subplots(figsize=(10, 5.8))
    bars = ax.barh(
        chart["mineral_name"],
        chart["energy_demand_twh_2040"],
        color=colors,
    )

    for bar, twh, share in zip(
        bars,
        chart["energy_demand_twh_2040"],
        chart["share_of_total_pct"],
    ):
        ax.text(
            bar.get_width(),
            bar.get_y() + bar.get_height() / 2,
            f" {twh:.2f} TWh ({share:.1f}%)",
            va="center",
            fontsize=10,
        )

    ax.set_title(
        "Contribuição para a demanda elétrica em 2040",
        fontsize=16,
        fontweight="bold",
    )
    ax.set_xlabel("Demanda elétrica no cenário de referência (TWh)")
    ax.grid(axis="x", linestyle="--", alpha=0.35)
    ax.set_axisbelow(True)

    fig.text(
        0.01,
        0.01,
        (
            "Cenário de referência. A soma representa somente os cinco "
            "minerais cobertos pelo modelo energético."
        ),
        fontsize=8.5,
        color="#4A5568",
    )

    fig.tight_layout(rect=[0, 0.06, 1, 1])
    fig.savefig(
        OUTPUT_DIR / "energy_demand_contribution_2040.png",
        dpi=180,
        bbox_inches="tight",
    )
    plt.close(fig)


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    comparison = load_comparison_data()
    candidates = build_candidate_review()

    comparison.to_csv(
        OUTPUT_DIR / "energy_comparison_2040.csv",
        index=False,
        encoding="utf-8-sig",
    )

    candidates.to_csv(
        OUTPUT_DIR / "candidate_minerals_review.csv",
        index=False,
        encoding="utf-8-sig",
    )

    plot_energy_intensity(comparison)
    plot_energy_contribution(comparison)

    total_twh = comparison["energy_demand_twh_2040"].sum()

    print("Análise de energia criada com sucesso.")
    print(f"Demanda total de referência em 2040: {total_twh:.2f} TWh")
    print(f"Outputs: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
