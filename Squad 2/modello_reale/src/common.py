from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[3]

SQUAD1_INTERFACE = (
    ROOT
    / "Squad 1"
    / "Bases consolidadas"
    / "documentacao"
    / "pacote_squad2"
    / "interface_squad1_squad2.csv"
)

SQUAD1_WORKBOOK = (
    ROOT
    / "Squad 1"
    / "Bases consolidadas"
    / "documentacao"
    / "prototipo_bases_consolidadas_v17.xlsx"
)

MODEL_DIR = Path(__file__).resolve().parents[1]

# Entrada final da intensidade energética da Squad 2.
# O arquivo antigo em parameters/energy_intensity.csv permanece como
# benchmark histórico e não é sobrescrito.
FINAL_ENERGY_PARAMETERS = (
    ROOT
    / "Squad 2"
    / "intensidade_energetica"
    / "coeficiente_estadual_para_modelo_v1.csv"
)

SCENARIO_PARAMETERS = MODEL_DIR / "parameters" / "scenarios.csv"

REQUIRED_ENERGY_COLUMNS = [
    "mineral_id",
    "mineral_name",
    "production_basis",
    "energy_intensity_mwh_t",
    "source_id",
    "data_nature",
]


def load_parameters():
    energy = pd.read_csv(FINAL_ENERGY_PARAMETERS)
    scenarios = pd.read_csv(SCENARIO_PARAMETERS)

    missing_energy_columns = set(REQUIRED_ENERGY_COLUMNS) - set(energy.columns)
    if missing_energy_columns:
        raise ValueError(
            "Colunas ausentes na tabela final de intensidade: "
            f"{missing_energy_columns}"
        )

    # O motor usa somente o contrato de seis colunas; as demais colunas
    # permanecem no arquivo de origem para rastreabilidade metodológica.
    energy = energy[REQUIRED_ENERGY_COLUMNS].copy()

    if energy.duplicated(["mineral_id", "production_basis"]).any():
        raise ValueError("Há parâmetros energéticos duplicados.")

    if len(energy) != 5:
        raise ValueError(
            "A tabela final deve conter exatamente um coeficiente "
            "para cada um dos cinco minerais do modelo."
        )

    if energy["energy_intensity_mwh_t"].isna().any():
        raise ValueError("Há intensidade energética ausente.")

    if (energy["energy_intensity_mwh_t"] <= 0).any():
        raise ValueError("Há intensidade energética não positiva.")

    if set(scenarios["scenario"]) != {
        "conservador",
        "referencia",
        "expansao",
    }:
        raise ValueError("Os três cenários obrigatórios não estão completos.")

    return energy, scenarios


def load_historical_production():
    energy, _ = load_parameters()

    # Quatro minerais disponíveis diretamente na interface Squad 1 → Squad 2.
    interface = pd.read_csv(SQUAD1_INTERFACE)
    direct = interface[
        (interface["nivel_agregacao"] == "estado")
        & (interface["valor_observado_estimado"] == "observado")
    ].copy()

    direct["production_basis"] = direct["production_basis"].str.lower()

    direct = direct.merge(
        energy[
            energy["mineral_name"].isin(
                ["Alumínio (Bauxita)", "Níquel", "Fosfato", "Amianto"]
            )
        ][["mineral_id", "mineral_name", "production_basis"]],
        on=["mineral_id", "mineral_name", "production_basis"],
        how="inner",
    )

    direct = direct[
        [
            "mineral_id",
            "mineral_name",
            "year",
            "production_t",
            "production_basis",
            "source_id",
            "status_validacao",
            "periodo_referencia",
        ]
    ]

    # O cobre usa conteúdo mineral: esta medida está na base completa
    # da Squad 1, não ainda no CSV de interface.
    full_data = pd.read_excel(
        SQUAD1_WORKBOOK,
        sheet_name="08_fato_producao_energia",
        header=3,
    )

    copper = full_data[
        (full_data["uf"] == "GO")
        & (full_data["mineral_name"] == "Cobre")
        & (full_data["metrica"] == "contido_beneficiada")
        & (full_data["production_basis"] == "conteudo_mineral")
        & (full_data["unidade_padrao"] == "t")
        & (full_data["status_validacao"] == "valido")
    ].copy()

    copper = copper.rename(columns={"valor_tratado": "production_t"})[
        [
            "mineral_id",
            "mineral_name",
            "year",
            "production_t",
            "production_basis",
            "source_id",
            "status_validacao",
            "periodo_referencia",
        ]
    ]

    history = pd.concat([direct, copper], ignore_index=True)
    history = history.sort_values(["mineral_id", "year"])

    if history.duplicated(
        ["mineral_id", "year", "production_basis"]
    ).any():
        raise ValueError("Há observações históricas duplicadas.")

    if history["production_t"].isna().any() or (history["production_t"] < 0).any():
        raise ValueError("Há produção ausente ou negativa.")

    return history


if __name__ == "__main__":
    history = load_historical_production()

    print(
        history.groupby(
            ["mineral_name", "production_basis"]
        ).agg(
            primeiro_ano=("year", "min"),
            ultimo_ano=("year", "max"),
            observacoes=("year", "size"),
        )
    )
