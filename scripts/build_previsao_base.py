# -*- coding: utf-8 -*-
"""Pacote da aba Previsão de demanda (public/data/previsao/previsao_v1.json), gerado do modelo real do Squad 2.

    python scripts/build_previsao_base.py
    python scripts/build_previsao_base.py --pular-execucao   # reaproveita Squad 2/modello_reale/outputs/

Executa o backtest, os cenários futuros, a sensibilidade e as faixas de incerteza de `Squad 2/modello_reale/src` e
junta, num único arquivo para o navegador:

- a previsão: energia por mineral, ano e cenário (2027–2040), com as faixas baixa/base/alta do Squad 2;
- os dados utilizados: a produção histórica que o modelo leu da base do Squad 1, os coeficientes de intensidade
  energética com a rastreabilidade da base do Squad 2 e o catálogo de fontes do simulador;
- a metodologia: hipóteses de cenário, regra de projeção de cada mineral e o backtest.

Nenhum número é recalculado aqui: tudo vem dos CSVs que o modelo grava. Antes de gravar, confere que a soma por
mineral bate com o total publicado pelo modelo. Requer pandas e openpyxl (Squad 2/modello_reale/requirements.txt).
"""
import argparse
import json
import subprocess
import sys
from collections import OrderedDict
from datetime import date
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
MODELO = RAIZ / "Squad 2" / "modello_reale"
SAIDA = RAIZ / "public" / "data" / "previsao" / "previsao_v1.json"
SCRIPTS = ("run_backtest.py", "run_future_scenarios.py", "run_intensity_sensitivity.py", "run_uncertainty_bands.py")
CENARIOS = ("conservador", "referencia", "expansao")
TOLERANCIA_MWH = 1e-3


def executar_modelo(src):
    for script in SCRIPTS:
        subprocess.run([sys.executable, script], cwd=src, check=True, stdout=subprocess.DEVNULL, stderr=None)


def ler(*partes):
    return pd.read_csv(MODELO.joinpath("outputs", *partes), encoding="utf-8-sig")


def num(v, casas=6):
    if v is None or pd.isna(v):
        return None
    return round(float(v), casas)


def texto(v):
    return None if v is None or pd.isna(v) else str(v)


def historico_por_mineral(common):
    historia = common.load_historical_production()
    saida = {}
    for mineral_id, linhas in historia.groupby("mineral_id"):
        linhas = linhas.sort_values("year")
        saida[mineral_id] = OrderedDict([
            ("fonte", ";".join(sorted(linhas["source_id"].astype(str).unique()))),
            ("status_validacao", ";".join(sorted(linhas["status_validacao"].astype(str).unique()))),
            ("serie", [OrderedDict([("ano", int(l.year)), ("producao_t", num(l.production_t, 2))])
                       for l in linhas.itertuples()]),
        ])
    return saida


def coeficientes(common):
    """A tabela que o modelo carrega, com as colunas de rastreabilidade que ele descarta no cálculo."""
    tabela = pd.read_csv(common.FINAL_ENERGY_PARAMETERS, encoding="utf-8-sig")
    saida = {}
    for l in tabela.itertuples():
        saida[l.mineral_id] = OrderedDict([
            ("mwh_t", num(l.energy_intensity_mwh_t)),
            ("natureza", texto(l.data_nature)),
            ("fontes", texto(l.source_id)),
            ("ano", int(l.year)),
            ("metodo_agregacao", texto(l.aggregation_method)),
            ("energia_ccee_mwh", num(l.energy_mwh, 3)),
            ("producao_coberta_t", num(l.production_t, 2)),
            ("cobertura", num(l.coverage_share, 4)),
            ("confianca", texto(l.confianca)),
            ("valor_anterior_mwh_t", num(l.valor_modelo_atual_mwh_t)),
            ("variacao_vs_anterior_pct", num(l.variacao_vs_modelo_pct, 1)),
            ("observacao", texto(l.observacao)),
        ])
    return saida, Path(common.FINAL_ENERGY_PARAMETERS).resolve().relative_to(RAIZ).as_posix()


def montar(projecao, faixas_min, faixas_tot, backtest_res, backtest_det, hipoteses, historico, coefs):
    projecao = projecao.merge(
        faixas_min[["mineral_id", "year", "scenario", "lower_energy_demand_mwh", "upper_energy_demand_mwh"]],
        on=["mineral_id", "year", "scenario"], how="left", validate="one_to_one")
    if projecao["lower_energy_demand_mwh"].isna().any():
        raise SystemExit("Faltam faixas de incerteza para alguma linha da projeção.")

    minerais = []
    for mineral_id, linhas in projecao.groupby("mineral_id", sort=False):
        primeira = linhas.iloc[0]
        res = backtest_res[backtest_res["mineral_id"] == mineral_id]
        det = backtest_det[backtest_det["mineral_id"] == mineral_id].sort_values("test_year")
        por_cenario = OrderedDict()
        for cenario in CENARIOS:
            g = linhas[linhas["scenario"] == cenario].sort_values("year")
            por_cenario[cenario] = OrderedDict([
                ("metodo", str(g.iloc[0]["projection_method"])),
                ("crescimento_aplicado", num(g.iloc[0]["applied_production_growth_rate"])),
                ("serie", [OrderedDict([
                    ("ano", int(l.year)),
                    ("producao_t", num(l.projected_production_t, 2)),
                    ("intensidade_mwh_t", num(l.energy_intensity_mwh_t, 10)),
                    ("energia_mwh", num(l.energy_demand_mwh, 3)),
                    ("baixa_mwh", num(l.lower_energy_demand_mwh, 3)),
                    ("alta_mwh", num(l.upper_energy_demand_mwh, 3)),
                ]) for l in g.itertuples()]),
            ])
        minerais.append(OrderedDict([
            ("mineral_id", mineral_id),
            ("nome", str(primeira["mineral_name"])),
            ("base_producao", str(primeira["production_basis"])),
            ("ano_base", int(primeira["base_year"])),
            ("crescimento_historico", num(primeira["historical_growth_rate"])),
            ("janela_tendencia", [int(primeira["trend_start_year"]), int(primeira["trend_end_year"])]),
            ("metodo_tendencia", str(primeira["trend_method"])),
            ("historico", historico[mineral_id]),
            ("coeficiente", coefs[mineral_id]),
            ("backtest", OrderedDict([
                ("regra_selecionada", str(res.iloc[0]["method"])),
                ("anos_testados", int(res.iloc[0]["tested_years"])),
                ("mape_selecionada", num(res.iloc[0]["mean_absolute_percentage_error"])),
                ("mape_tendencia", num(res.iloc[0]["trend_mean_absolute_percentage_error"])),
                ("mape_persistencia", num(res.iloc[0]["naive_mean_absolute_percentage_error"])),
                ("treino_ate", int(det.iloc[0]["train_through_year"])),
                ("detalhe", [OrderedDict([
                    ("ano", int(l.test_year)),
                    ("observado_t", num(l.actual_production_t, 2)),
                    ("tendencia_t", num(l.trend_forecast_production_t, 2)),
                    ("persistencia_t", num(l.naive_forecast_production_t, 2)),
                ]) for l in det.itertuples()]),
            ])),
            ("cenarios", por_cenario),
        ]))
    minerais.sort(key=lambda m: m["mineral_id"])

    total = []
    for l in faixas_tot.sort_values(["scenario", "year"]).itertuples():
        soma = projecao[(projecao.year == l.year) & (projecao.scenario == l.scenario)]["energy_demand_mwh"].sum()
        if abs(soma - l.base_energy_demand_mwh) > TOLERANCIA_MWH:
            raise SystemExit(f"Soma por mineral diverge do total do modelo em {l.year}/{l.scenario}.")
        total.append(OrderedDict([
            ("ano", int(l.year)), ("cenario", l.scenario),
            ("energia_mwh", num(l.base_energy_demand_mwh, 3)),
            ("baixa_mwh", num(l.lower_energy_demand_mwh, 3)),
            ("alta_mwh", num(l.upper_energy_demand_mwh, 3)),
        ]))

    cenarios = [OrderedDict([
        ("cenario", l.scenario),
        ("ajuste_crescimento", num(l.growth_adjustment)),
        ("ganho_eficiencia_anual", num(l.annual_efficiency_improvement)),
        ("natureza", str(l.data_nature)),
        ("fonte", str(l.source_id)),
    ]) for l in hipoteses.itertuples()]
    cenarios.sort(key=lambda c: CENARIOS.index(c["cenario"]))
    return minerais, total, cenarios


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pular-execucao", action="store_true",
                        help="reaproveita os outputs já presentes em vez de rodar o modelo")
    args = parser.parse_args()
    if not args.pular_execucao:
        executar_modelo(MODELO / "src")

    sys.path.insert(0, str(MODELO / "src"))
    sys.path.insert(0, str(RAIZ / "scripts"))
    import common  # noqa: E402 — carregadores do modelo do Squad 2
    from build_simulador_base import fontes  # noqa: E402 — mesmo catálogo de fontes do simulador

    projecao = ler("future", "future_projection_by_mineral.csv")
    coefs, arquivo_coef = coeficientes(common)
    minerais, total, cenarios = montar(
        projecao,
        ler("uncertainty", "uncertainty_by_mineral.csv"),
        ler("uncertainty", "uncertainty_total_goias.csv"),
        ler("backtest", "backtest_summary.csv"),
        ler("backtest", "backtest_detail.csv"),
        pd.read_csv(MODELO / "parameters" / "scenarios.csv"),
        historico_por_mineral(common),
        coefs,
    )
    # fontes() recebe o source_id de cada mineral, que pode juntar várias fontes com ";".
    catalogo = fontes(projecao, [{"source_id": m["coeficiente"]["fontes"], "mineral_name": m["nome"]}
                                          for m in minerais], arquivo_coef)

    doc = OrderedDict([
        ("versao", "1.0.0"),
        ("data_versao", date.today().isoformat()),
        ("gerado_por", "scripts/build_previsao_base.py"),
        ("modelo", OrderedDict([
            ("squad", "Squad 2"),
            ("diretorio", "Squad 2/modello_reale"),
            ("scripts", [f"Squad 2/modello_reale/src/{s}" for s in SCRIPTS]),
            ("coeficientes", arquivo_coef),
            ("hipoteses", "Squad 2/modello_reale/parameters/scenarios.csv"),
            ("producao_historica", [
                "Squad 1/Bases consolidadas/documentacao/pacote_squad2/interface_squad1_squad2.csv",
                "Squad 1/Bases consolidadas/documentacao/prototipo_bases_consolidadas_v17.xlsx (aba 08_fato_producao_energia)",
            ]),
        ])),
        ("horizonte", OrderedDict([("inicio", int(projecao.year.min())), ("fim", int(projecao.year.max()))])),
        ("ano_base", int(projecao.base_year.max())),
        ("faixa_intensidade_pct", 10),
        ("cenarios", cenarios),
        ("total", total),
        ("minerais", minerais),
        ("fontes", catalogo),
    ])
    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    with SAIDA.open("w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=1)
        fh.write("\n")

    ref = {(t["ano"], t["cenario"]): t for t in total}
    print(f"{SAIDA.relative_to(RAIZ)} — {len(minerais)} minerais, {len(total)} linhas de total")
    print(f"referência: {ref[(2027, 'referencia')]['energia_mwh'] / 1e6:.3f} TWh em 2027 → "
          f"{ref[(2040, 'referencia')]['energia_mwh'] / 1e6:.3f} TWh em 2040")


if __name__ == "__main__":
    main()
