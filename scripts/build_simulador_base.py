# -*- coding: utf-8 -*-
"""Pacote de parâmetros do Simulador (public/data/simulador/parametros_v1.json), gerado do modelo real do Squad 2.

    python scripts/build_simulador_base.py
    python scripts/build_simulador_base.py --repo <clone>

Executa os três scripts de `Squad 2/modello_reale/src` e lê os arquivos que eles produzem em
`Squad 2/modello_reale/outputs/`. As intensidades vêm de `load_parameters()` do próprio modelo — a mesma tabela que ele
usa no cálculo —, para o simulador nunca apontar para um arquivo que o Squad 2 deixou de usar. Nenhum número é recalculado aqui: o script extrai as primitivas do
modelo (ano-base, produção do último ano observado, crescimento histórico composto, intensidade
energética e as hipóteses de cenário) para que o navegador reproduza a mesma projeção sem depender de
artefatos do GitHub Actions, que não ficam versionados.

Antes de gravar, confere que a fórmula do simulador devolve exatamente a energia do modelo do Squad 2
em todos os minerais, anos e cenários. Requer pandas e openpyxl (Squad 2/modello_reale/requirements.txt).
"""
import argparse
import json
import subprocess
import sys
from collections import OrderedDict
from datetime import date
from pathlib import Path

import pandas as pd

CENARIOS = OrderedDict([
    ("conservador", ("Conservador", "#5B8DB8")),
    ("referencia", ("Referência", "#123B66")),
    ("expansao", ("Expansão", "#C6A15B")),
])
TOLERANCIA_MWH = 1e-6


def executar_modelo(src):
    for script in ("run_backtest.py", "run_future_scenarios.py", "run_intensity_sensitivity.py"):
        subprocess.run([sys.executable, script], cwd=src, check=True,
                       stdout=subprocess.DEVNULL, stderr=None)


def primitivas_por_mineral(projecao, intensidade, backtest):
    referencia = projecao[projecao["scenario"] == "referencia"]
    minerais = []
    for mineral_id, linhas in referencia.groupby("mineral_id", sort=False):
        linhas = linhas.sort_values("year")
        primeira = linhas.iloc[0]
        crescimento = float(primeira["historical_growth_rate"])
        ano_base = int(primeira["base_year"])
        # O modelo do Squad 2 publica a produção projetada, não a do ano-base; ela volta
        # dividindo a projeção pelo crescimento composto acumulado até aquele ano.
        expoente = int(primeira["year"]) - ano_base
        producao_base = float(primeira["projected_production_t"]) / (1 + crescimento) ** expoente

        par = intensidade[intensidade["mineral_id"] == mineral_id].iloc[0]
        erro = backtest[backtest["mineral_id"] == mineral_id]
        minerais.append(OrderedDict([
            ("mineral_id", mineral_id),
            ("mineral_name", str(primeira["mineral_name"])),
            ("production_basis", str(primeira["production_basis"])),
            ("ano_base", ano_base),
            ("producao_base_t", producao_base),
            ("crescimento_historico", crescimento),
            ("energy_intensity_mwh_t", float(par["energy_intensity_mwh_t"])),
            ("mape_backtest", float(erro.iloc[0]["mean_absolute_percentage_error"]) if len(erro) else None),
            ("anos_testados_backtest", int(erro.iloc[0]["tested_years"]) if len(erro) else None),
            ("valor_observado_estimado", "estimado"),
            ("data_nature", str(par["data_nature"])),
            ("source_id", str(par["source_id"])),
        ]))
    return sorted(minerais, key=lambda m: m["mineral_id"])


def conferir(minerais, cenarios, projecao):
    """A fórmula que o navegador vai rodar tem de devolver a energia do modelo do Squad 2."""
    indice = {m["mineral_id"]: m for m in minerais}
    maior = 0.0
    for _, linha in projecao.iterrows():
        m = indice[linha["mineral_id"]]
        c = cenarios[linha["scenario"]]
        n = int(linha["year"]) - m["ano_base"]
        producao = m["producao_base_t"] * (1 + m["crescimento_historico"] + c["growth_adjustment"]) ** n
        ie = m["energy_intensity_mwh_t"] * (1 - c["ganho_eficiencia_anual_padrao"]) ** n
        maior = max(maior, abs(producao * ie - float(linha["energy_demand_mwh"])))
    if maior > TOLERANCIA_MWH:
        raise SystemExit(f"A fórmula do simulador diverge do modelo do Squad 2 em até {maior:.6f} MWh.")
    return maior


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", default=Path(__file__).resolve().parents[1])
    parser.add_argument("--pular-execucao", action="store_true",
                        help="reaproveita os outputs já presentes em vez de rodar o modelo")
    args = parser.parse_args()

    raiz = Path(args.repo).resolve()
    modelo = raiz / "Squad 2" / "modello_reale"
    saida = raiz / "public" / "data" / "simulador" / "parametros_v1.json"

    if not args.pular_execucao:
        executar_modelo(modelo / "src")

    projecao = pd.read_csv(modelo / "outputs" / "future" / "future_projection_by_mineral.csv", encoding="utf-8-sig")
    backtest = pd.read_csv(modelo / "outputs" / "backtest" / "backtest_summary.csv", encoding="utf-8-sig")
    sys.path.insert(0, str(modelo / "src"))
    import common  # noqa: E402 — o carregador de parâmetros do modelo do Squad 2
    intensidade, _ = common.load_parameters()
    arquivo_intensidade = Path(common.FINAL_ENERGY_PARAMETERS).resolve().relative_to(raiz).as_posix()
    hipoteses = pd.read_csv(modelo / "parameters" / "scenarios.csv")
    contrato = json.loads((modelo / "outputs" / "sensitivity" / "intensity_sensitivity_contract.json").read_text(encoding="utf-8"))

    cenarios = OrderedDict()
    for _, linha in hipoteses.iterrows():
        rotulo, cor = CENARIOS[linha["scenario"]]
        cenarios[linha["scenario"]] = OrderedDict([
            ("scenario", linha["scenario"]),
            ("rotulo", rotulo),
            ("cor", cor),
            ("growth_adjustment", float(linha["growth_adjustment"])),
            ("ganho_eficiencia_anual_padrao", float(linha["annual_efficiency_improvement"])),
            ("valor_observado_estimado", "ilustrativo"),
            ("source_id", str(linha["source_id"])),
        ])

    minerais = primitivas_por_mineral(projecao, intensidade, backtest)
    maior_diferenca = conferir(minerais, cenarios, projecao)

    resumo = projecao.groupby(["year", "scenario"], as_index=False).agg(
        total=("energy_demand_mwh", "sum"))
    def total(ano, cenario):
        linha = resumo[(resumo.year == ano) & (resumo.scenario == cenario)]
        return round(float(linha.iloc[0]["total"]) / 1e6, 6)

    doc = OrderedDict([
        ("versao", "1.0.0"),
        ("data_versao", date.today().isoformat()),
        ("responsavel", "Squad 3 — Henrique Falci (simulador e rastreabilidade)"),
        ("modelo", "produção projetada × intensidade energética"),
        ("origem_modelo", OrderedDict([
            ("squad", "Squad 2 — Federico Castro"),
            ("diretorio", "Squad 2/modello_reale"),
            ("gerado_por", "scripts/build_simulador_base.py"),
            ("metodo_projecao", str(projecao.iloc[0]["projection_method"])),
        ])),
        ("horizonte", OrderedDict([("inicio", int(projecao["year"].min())), ("fim", int(projecao["year"].max()))])),
        ("equacoes", OrderedDict([
            ("producao", "producao_base_t × (1 + crescimento_historico + growth_adjustment)^(t − ano_base)"),
            ("intensidade", "energy_intensity_mwh_t × (1 + ajuste_pct/100) × (1 − g)^(t − ano_base)"),
            ("energia", "producao × intensidade"),
        ])),
        ("cobertura", OrderedDict([
            ("minerais", len(minerais)),
            ("nota", "Cinco minerais cujas séries de produção e parâmetros energéticos o Squad 2 conseguiu conciliar. "
                     "O nióbio ficou de fora: as unidades e o conceito de produção disponíveis não puderam ser "
                     "conciliados com segurança com o coeficiente energético."),
            ("toneladas_agregaveis", False),
            ("nota_toneladas", "As toneladas não são somadas entre minerais: o cobre usa conteúdo mineral e os demais "
                               "usam produção beneficiada. Só a energia, em MWh, é agregada."),
        ])),
        ("sensibilidade_intensidade", OrderedDict([
            ("minimo_pct", contrato["allowed_adjustment_pct"]["minimum"]),
            ("maximo_pct", contrato["allowed_adjustment_pct"]["maximum"]),
            ("passo_pct", contrato["allowed_adjustment_pct"]["step"]),
            ("formula", contrato["formula"]),
            ("contrato_versao", contrato["version"]),
            ("nota", "Faixa e fórmula definidas pelo contrato de sensibilidade do Squad 2, "
                     "intensity_sensitivity_contract.json."),
        ])),
        ("aviso", "As intensidades energéticas vêm da base do Squad 2: energia das cargas na CCEE em 2025 dividida pela "
                  "produção do mesmo ano, nas operações que a CCEE cobre; a bauxita, sem carga identificada, segue com "
                  "benchmark. São coeficientes por mineral, não medição de cada planta. As hipóteses de crescimento e "
                  "eficiência dos cenários são ilustrativas. Os resultados são cenários condicionais, não previsão oficial."),
        ("conferencia_modelo", OrderedDict([
            ("referencia_2027_twh", total(2027, "referencia")),
            ("referencia_2040_twh", total(2040, "referencia")),
            ("conservador_2040_twh", total(2040, "conservador")),
            ("expansao_2040_twh", total(2040, "expansao")),
            ("maior_diferenca_mwh", round(maior_diferenca, 9)),
            ("nota", "Diferença máxima entre a fórmula que o navegador executa e a energia publicada pelo modelo "
                     "do Squad 2, em todos os minerais, anos e cenários."),
        ])),
        ("cenarios", list(cenarios.values())),
        ("minerais", minerais),
        ("fontes", fontes(projecao, minerais, arquivo_intensidade)),
    ])

    saida.parent.mkdir(parents=True, exist_ok=True)
    with saida.open("w", encoding="utf-8") as fh:
        json.dump(doc, fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    print(f"{saida.relative_to(raiz)} — versão {doc['versao']}, {len(minerais)} minerais")
    print(f"referência: {doc['conferencia_modelo']['referencia_2027_twh']:.3f} TWh em 2027 → "
          f"{doc['conferencia_modelo']['referencia_2040_twh']:.3f} TWh em 2040")
    print(f"maior diferença para o modelo do Squad 2: {maior_diferenca:.2e} MWh")


def fontes(projecao, minerais, arquivo_intensidade):
    """Catálogo de fontes: as que os minerais citam (o `source_id` do Squad 2 pode juntar várias com `;`) e as fixas."""
    hoje = date.today().isoformat()
    usadas = {sid for m in minerais for sid in m["source_id"].split(";")}
    so_benchmark = sorted(m["mineral_name"] for m in minerais if m["source_id"] == "SRC_FGV_EPGE_001")
    catalogo = [
        OrderedDict([
            ("source_id", "SRC_S2_INTENSIDADE_V1"),
            ("source_name", "Squad 2 — base de intensidade energética v1 (coeficiente estadual por mineral)"),
            ("source_url", arquivo_intensidade),
            ("data_acesso", hoje),
            ("periodo_referencia", "2025"),
            ("tipo_fonte", "interna_projeto"),
            ("valor_observado_estimado", "estimado"),
            ("metodo_estimacao", "Consumo específico (EPE): energia das cargas na CCEE em 2025 ÷ produção física de 2025 da "
                                 "mesma entidade, somando as operações cobertas de cada mineral. Mineral sem carga na CCEE "
                                 "mantém o benchmark anterior. É a tabela que o modelo do Squad 2 carrega."),
            ("status_validacao", "pendente_validacao"),
            ("responsavel_validacao", "Squad 2 — intensidade energética"),
            ("notas", "Gerada por Squad 2/intensidade_energetica/build_intensidade.py, que o fluxo de derivados refaz quando "
                      "as bases mudam. Cada mineral cita as fontes primárias abaixo no campo source_id."),
        ]),
        OrderedDict([
            ("source_id", "SRC_CCEE_PARCELA_CARGA"),
            ("source_name", "CCEE — consumo das parcelas de carga em Goiás"),
            ("source_url", "https://dadosabertos.ccee.org.br/dataset/parcela_carga_consumo"),
            ("data_acesso", hoje),
            ("periodo_referencia", "2025 (doze meses)"),
            ("tipo_fonte", "oficial"),
            ("valor_observado_estimado", "observado"),
            ("metodo_estimacao", None),
            ("status_validacao", "conferido_squad1"),
            ("responsavel_validacao", "Squad 1 — bases públicas e diagnóstico mineral"),
            ("notas", "Carga ligada à empresa pela raiz do CNPJ. Não inclui autoprodução nem geração própria. Cópia filtrada "
                      "para Goiás em Squad 1/dados/CCEE."),
        ]),
        OrderedDict([
            ("source_id", "SRC_EMPRESA_RELATORIO"),
            ("source_name", "Relatórios das empresas — produção declarada da operação"),
            ("source_url", None),
            ("data_acesso", hoje),
            ("periodo_referencia", "2025"),
            ("tipo_fonte", "empresa"),
            ("valor_observado_estimado", "observado"),
            ("metodo_estimacao", None),
            ("status_validacao", "pendente_validacao"),
            ("responsavel_validacao", "Squad 2 — intensidade energética"),
            ("notas", "Usado quando a empresa publica a produção da própria operação em Goiás (ex.: cobre contido da Lundin "
                      "em Alto Horizonte). Fonte de cada número em Squad 2/intensidade_energetica/base_intensidade_energetica_v1.csv."),
        ]),
        OrderedDict([
            ("source_id", "SRC_ANM_PROD_BENEF"),
            ("source_name", "ANM — Anuário Mineral Brasileiro, produção beneficiada"),
            ("source_url", "https://dadosabertos.anm.gov.br/AMB/Producao_Beneficiada.csv"),
            ("data_acesso", hoje),
            ("periodo_referencia", "2025"),
            ("tipo_fonte", "oficial"),
            ("valor_observado_estimado", "observado"),
            ("metodo_estimacao", None),
            ("status_validacao", "validado_squad1"),
            ("responsavel_validacao", "Squad 1 — bases públicas e diagnóstico mineral"),
            ("notas", "Produção estadual por substância, lida da base consolidada do Squad 1."),
        ]),
        OrderedDict([
            ("source_id", "SRC_ANM_CFEM"),
            ("source_name", "ANM — arrecadação da CFEM por processo"),
            ("source_url", "https://dadosabertos.anm.gov.br/CFEM/CFEM_Arrecadacao_2022_2026.csv"),
            ("data_acesso", hoje),
            ("periodo_referencia", "2025"),
            ("tipo_fonte", "oficial"),
            ("valor_observado_estimado", "estimado"),
            ("metodo_estimacao", "A produção estadual da ANM é aberta por operação pela participação de cada processo na CFEM "
                                 "do mineral no município (aba 12 da base consolidada do Squad 1)."),
            ("status_validacao", "pendente_validacao"),
            ("responsavel_validacao", "Squad 1 — bases públicas e diagnóstico mineral"),
            ("notas", "Serve só para atribuir a produção a cada operação; não entra como valor monetário no simulador."),
        ]),
        OrderedDict([
            ("source_id", "SRC_FGV_EPGE_001"),
            ("source_name", "Apresentação FGV Energia-EPGE — intensidades energéticas de referência"),
            ("source_url", None),
            ("data_acesso", hoje),
            ("periodo_referencia", "não informado no material-base"),
            ("tipo_fonte", "institucional"),
            ("valor_observado_estimado", "estimado"),
            ("metodo_estimacao", "Benchmark ou proxy operacional por mineral, mantido pelo Squad 2 só onde não há energia "
                                 "observada na CCEE. Não é medição do consumo observado de cada operação."),
            ("status_validacao", "pendente_validacao"),
            ("responsavel_validacao", "Squad 2 — intensidade energética"),
            ("notas", "Hoje usado só para: " + (", ".join(so_benchmark) or "nenhum mineral") + ". Os demais minerais têm "
                      "coeficiente calculado com a CCEE (SRC_S2_INTENSIDADE_V1)."),
        ]),
        OrderedDict([
            ("source_id", "SRC_SQUAD1_PRODUCAO_001"),
            ("source_name", "Squad 1 — produção mineral histórica consolidada de Goiás"),
            ("source_url", "Squad 1/Bases consolidadas/documentacao/pacote_squad2/interface_squad1_squad2.csv"),
            ("data_acesso", hoje),
            ("periodo_referencia", "2010–2025 (2014–2025 para a bauxita)"),
            ("tipo_fonte", "oficial"),
            ("valor_observado_estimado", "observado"),
            ("metodo_estimacao", None),
            ("status_validacao", "validado_squad1"),
            ("responsavel_validacao", "Squad 1 — bases públicas e diagnóstico mineral"),
            ("notas", "Séries lidas pelo modelo do Squad 2 apenas nas linhas de nível estadual marcadas como "
                      "observadas. O cobre vem da aba 08_fato_producao_energia da planilha consolidada v17, "
                      "porque a métrica contido_beneficiada não está no arquivo de interface."),
        ]),
        OrderedDict([
            ("source_id", "SRC_S2_ASSUMPTION_001"),
            ("source_name", "Squad 2 — hipóteses de cenário do modelo real"),
            ("source_url", "Squad 2/modello_reale/parameters/scenarios.csv"),
            ("data_acesso", hoje),
            ("periodo_referencia", "2027–2040"),
            ("tipo_fonte", "interna_projeto"),
            ("valor_observado_estimado", "ilustrativo"),
            ("metodo_estimacao", "Ajuste em pontos percentuais sobre o crescimento histórico de cada mineral "
                                 "(−2, 0 e +2) e melhoria anual de eficiência energética (0,4%, 0,9% e 1,4%). "
                                 "O próprio Squad 2 identifica essas hipóteses como ilustrativas."),
            ("status_validacao", "nao_validado"),
            ("responsavel_validacao", "Squad 2 — modelo de projeção"),
            ("notas", "A projeção é de tendência histórica. O modelo ainda não inclui carteira física de projetos: "
                      "não há, nas bases atuais, capacidade, ano de entrada e grau de certeza estruturados."),
        ]),
    ]
    return [f for f in catalogo if f["source_id"] in usadas | {"SRC_S2_INTENSIDADE_V1", "SRC_SQUAD1_PRODUCAO_001", "SRC_S2_ASSUMPTION_001"}]


if __name__ == "__main__":
    main()
