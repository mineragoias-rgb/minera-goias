# -*- coding: utf-8 -*-
"""Pacote de dados dos indicadores municipais (aba Atlas · Território · Visão do mapa · Indicadores).

    python scripts/build_indicadores_municipais.py

Lê o banco de 20 indicadores por município (2025) de `Squad 2/indicadores_compostos/entregas/MINERA_Goias_Indicadores_2025.xlsx`
(aba Indicadores, valores já calculados) e grava `data/indicadores/indicadores_municipais.json`, que o painel lê atrás do login
(/api/indicadores). Cada indicador vem com família, unidade, fórmula, leitura e origem (nova ou antiga), em português e inglês.
Só a CFEM por ano (cfem_anual) é somada aqui, para o painel recalcular o crescimento; o resto do cálculo está em `Squad 2/indicadores_compostos/build_xlsx.py`.
"""
import json
import sys
from pathlib import Path

import openpyxl

sys.stdout.reconfigure(encoding="utf-8")
REPO = Path(__file__).resolve().parents[1]
XLSX = REPO / "Squad 2" / "indicadores_compostos" / "entregas" / "MINERA_Goias_Indicadores_2025.xlsx"
SAIDA = REPO / "data" / "indicadores" / "indicadores_municipais.json"

# id, família (pt, en), nome (pt, en), unidade, formato, fórmula (pt, en), leitura (pt, en), origem
IND = [
 ("R1", ("Receita", "Revenue"), ("CFEM 2025", "CFEM 2025"), "R$", "money0",
  ("Soma da CFEM recolhida de janeiro a dezembro de 2025.", "Sum of CFEM collected from January to December 2025."),
  ("Quanto maior, maior a arrecadação do município.", "The higher, the larger the municipality's collection."), "antiga"),
 ("R2", ("Receita", "Revenue"), ("Crescimento da CFEM", "CFEM growth"), "%", "pct",
  ("CFEM do ano final ÷ CFEM do ano base − 1. Os dois anos são escolhidos na tela. Sem valor quando a CFEM do ano base é zero. 2026 é parcial.", "CFEM of the end year ÷ CFEM of the base year − 1. Both years are chosen on screen. Blank when the base-year CFEM is zero. 2026 is partial."),
  ("Quanto maior, mais a arrecadação cresceu.", "The higher, the more collection grew."), "nova"),
 ("R3", ("Receita", "Revenue"), ("CFEM per capita", "CFEM per capita"), "R$/hab.", "money2",
  ("CFEM de 2025 ÷ população do município.", "CFEM 2025 ÷ municipal population."),
  ("Quanto maior, mais a mineração rende por habitante.", "The higher, the more mining yields per inhabitant."), "antiga"),
 ("R4", ("Receita", "Revenue"), ("CFEM/PIB (dependência da receita minerária)", "CFEM/GDP (dependence on mining revenue)"), "%", "pct2",
  ("CFEM de 2025 ÷ PIB municipal.", "CFEM 2025 ÷ municipal GDP."),
  ("Quanto maior, maior o peso da CFEM na economia local.", "The higher, the larger the weight of CFEM in the local economy."), "antiga"),
 ("R5", ("Receita", "Revenue"), ("Volatilidade da CFEM", "CFEM volatility"), "desvio-padrão", "dec3",
  ("Desvio-padrão de ln(1 + CFEM mensal) nos 12 meses de 2025.", "Standard deviation of ln(1 + monthly CFEM) over the 12 months of 2025."),
  ("Quanto maior, mais instável a receita mês a mês. Sem valor onde não há CFEM.", "The higher, the less stable the monthly revenue. Blank where there is no CFEM."), "nova"),
 ("R6", ("Receita", "Revenue"), ("Sharpe da CFEM", "CFEM Sharpe ratio"), "razão", "dec2",
  ("Média mensal ÷ desvio-padrão mensal da CFEM de 2025, sem taxa livre de risco.", "Monthly mean ÷ monthly standard deviation of CFEM in 2025, no risk-free rate."),
  ("Quanto maior, mais regular a receita em relação ao seu nível.", "The higher, the more regular the revenue relative to its level."), "nova"),
 ("P1", ("Processos por fase", "Processes by phase"), ("Processos de lavra", "Mining processes"), "nº", "int",
  ("Processos com lavra ativa ou autorizada (status 0 e 1).", "Processes with active or authorised mining (status 0 and 1)."),
  ("Quanto maior, mais títulos de lavra no município.", "The higher, the more mining titles in the municipality."), "antiga"),
 ("P2", ("Processos por fase", "Processes by phase"), ("Processos em pré-lavra", "Pre-mining processes"), "nº", "int",
  ("Processos em requerimento ou direito de lavra (status 3).", "Processes at mining request or right to mine (status 3)."),
  ("Quanto maior, mais projetos perto de virar lavra.", "The higher, the more projects close to becoming mines."), "antiga"),
 ("P3", ("Processos por fase", "Processes by phase"), ("Processos em pesquisa", "Exploration processes"), "nº", "int",
  ("Processos em pesquisa (status 4).", "Processes in exploration (status 4)."),
  ("Quanto maior, mais atividade exploratória.", "The higher, the more exploration activity."), "nova"),
 ("P4", ("Processos por fase", "Processes by phase"), ("Requerimentos", "Applications"), "nº", "int",
  ("Requerimentos de licenciamento ou de lavra garimpeira (status 5).", "Licensing or artisanal-mining applications (status 5)."),
  ("Quanto maior, mais pedidos em análise.", "The higher, the more applications under review."), "nova"),
 ("A1", ("Área por fase", "Area by phase"), ("Área em pesquisa", "Area under exploration"), "ha", "int",
  ("Soma da área dos processos únicos em pesquisa.", "Sum of the area of unique exploration processes."),
  ("Quanto maior, mais área requerida para pesquisa.", "The higher, the more area held for exploration."), "antiga"),
 ("A2", ("Área por fase", "Area by phase"), ("Área arrematada", "Area auctioned"), "ha", "int",
  ("Soma da área dos processos únicos conquistados ou arrematados nas rodadas de disponibilidade.", "Sum of the area of unique processes won or auctioned in availability rounds."),
  ("Quanto maior, mais área já arrematada.", "The higher, the more area already auctioned."), "nova"),
 ("A3", ("Área por fase", "Area by phase"), ("Área ofertada", "Area offered"), "ha", "int",
  ("Soma da área dos processos únicos livres ou aguardando leilão, exceto os já arrematados.", "Sum of the area of unique processes free or awaiting auction, excluding those already auctioned."),
  ("Quanto maior, mais área à espera de interessados.", "The higher, the more area waiting for bidders."), "nova"),
 ("A4", ("% da área do município", "% of municipal area"), ("% da área em pesquisa", "% of area under exploration"), "%", "pct",
  ("Área em pesquisa ÷ área territorial do município. Pode passar de 100% por sobreposição.", "Exploration area ÷ municipal territory. May exceed 100% because of overlaps."),
  ("Quanto maior, maior a fatia do território em pesquisa.", "The higher, the larger the share of territory under exploration."), "nova"),
 ("A5", ("% da área do município", "% of municipal area"), ("% da área arrematada", "% of area auctioned"), "%", "pct",
  ("Área arrematada ÷ área territorial do município.", "Auctioned area ÷ municipal territory."),
  ("Quanto maior, maior a fatia do território arrematada.", "The higher, the larger the share of territory auctioned."), "nova"),
 ("A6", ("% da área do município", "% of municipal area"), ("% da área ofertada", "% of area offered"), "%", "pct",
  ("Área ofertada ÷ área territorial do município.", "Offered area ÷ municipal territory."),
  ("Quanto maior, maior a fatia do território ofertada.", "The higher, the larger the share of territory offered."), "nova"),
 ("S1", ("Substâncias", "Substances"), ("Quantidade de substâncias", "Number of substances"), "nº", "int",
  ("Substâncias distintas nos processos do município.", "Distinct substances in the municipality's processes."),
  ("Quanto maior, mais variado o leque de substâncias.", "The higher, the wider the range of substances."), "nova"),
 ("S2", ("Substâncias", "Substances"), ("HHI por substância", "HHI by substance"), "0 a 1", "dec3",
  ("Σ (parcela²) da área dos processos por substância. Direto: valor alto é concentração alta.", "Σ (share²) of process area by substance. Direct: a high value means high concentration."),
  ("Quanto maior, mais a área se concentra em poucas substâncias. 1 = uma só.", "The higher, the more area is concentrated in few substances. 1 = a single one."), "nova"),
 ("T1", ("Titulares", "Holders"), ("Quantidade de titulares", "Number of holders"), "nº", "int",
  ("Titulares distintos nos processos do município.", "Distinct holders in the municipality's processes."),
  ("Quanto maior, mais agentes presentes no município.", "The higher, the more players in the municipality."), "nova"),
 ("T2", ("Titulares", "Holders"), ("HHI por titular", "HHI by holder"), "0 a 1", "dec3",
  ("Σ (parcela²) da área dos processos por titular. Direto: valor alto é concentração alta.", "Σ (share²) of process area by holder. Direct: a high value means high concentration."),
  ("Quanto maior, mais a área se concentra em poucos titulares. 1 = um só.", "The higher, the more area is concentrated in few holders. 1 = a single one."), "nova"),
]

# Combinações fixas: pesos de 0 a 100 sobre indicadores já normalizados de 0 a 1.
PRESETS = [
 ("arrecadacao", ("Arrecadação", "Collection"), {"R1": 0.5, "R3": 0.5}),
 ("dependencia", ("Dependência fiscal", "Fiscal dependence"), {"R4": 0.6, "R3": 0.4}),
 ("risco", ("Risco da receita", "Revenue risk"), {"R5": 0.4, "S2": 0.3, "T2": 0.3}),
 ("dinamica", ("Dinâmica e regularidade", "Dynamics and regularity"), {"R2": 0.5, "R6": 0.5}),
 ("atividade", ("Atividade minerária", "Mining activity"), {"P1": 0.25, "P2": 0.25, "P3": 0.25, "P4": 0.25}),
 ("territorio", ("Ocupação do território", "Territory occupation"), {"A4": 0.4, "A5": 0.3, "A6": 0.3}),
 ("diversidade", ("Diversidade de substâncias e titulares", "Substance and holder diversity"), {"S1": 0.5, "T1": 0.5}),
 ("concentracao", ("Concentração (HHI)", "Concentration (HHI)"), {"S2": 0.5, "T2": 0.5}),
]

RESSALVAS = (
 ["A população é a estimativa do IBGE para 1º de julho de 2025. O PIB é o do repositório (2023), não o de 2022 pedido, e não foi baixado do IBGE; CFEM/PIB mistura CFEM 2025 com PIB defasado.",
  "Processos e áreas são o estoque atual (fase = status atual) dos processos abertos até 2025. Não há histórico de fase.",
  "O % da área usa a área territorial do município e pode passar de 100% por sobreposição de processos.",
  "Volatilidade e Sharpe usam os 12 meses de 2025 e só existem onde há CFEM. A coluna de meses ativos ajuda a avaliar a confiança.",
  "As composições são exploratórias: o ranking depende dos pesos e da normalização escolhidos. Nenhum indicador ou composição foi validado por testes de índice."],
 ["Population is the IBGE estimate for 1 July 2025. GDP is the repository's (2023), not the 2022 figure requested, and was not downloaded from IBGE; CFEM/GDP mixes 2025 CFEM with lagged GDP.",
  "Processes and areas are the current stock (phase = current status) of processes opened up to 2025. There is no phase history.",
  "The % of area uses the municipal territory and may exceed 100% because of overlapping processes.",
  "Volatility and Sharpe use the 12 months of 2025 and exist only where there is CFEM. The active-months column helps judge confidence.",
  "Compositions are exploratory: the ranking depends on the weights and normalisation chosen. No indicator or composition has been validated by index tests."])

wb = openpyxl.load_workbook(XLSX, data_only=True)
ws = wb["Indicadores"]
cab = [c.value for c in ws[1]]
pos = {i[0]: next(j for j, h in enumerate(cab) if h and str(h).startswith(i[0] + " ")) for i in IND}
col_meses = next(j for j, h in enumerate(cab) if h and "meses" in str(h))
linhas = []
for r in ws.iter_rows(min_row=2, values_only=True):
    if r[0] is None:
        continue
    def v(j):
        x = r[j]
        return None if x is None or x == "" else round(float(x), 6)
    linhas.append([str(int(r[0])), *[v(pos[i[0]]) for i in IND], int(r[col_meses])])

# CFEM por município e ano (soma dos meses), para o painel recalcular o crescimento (R2) com o ano base e o ano final escolhidos.
pan = json.loads((REPO / "data" / "panorama" / "panorama.json").read_text(encoding="utf-8"))
cod_mun = [str(m[0]) for m in pan["dims"]["mun"]]
cc = pan["cfem"]["cols"]; ia, im, iv = cc.index("ano"), cc.index("mun"), cc.index("valor")
anos = sorted({r[ia] for r in pan["cfem"]["rows"]})
soma = {}
for r in pan["cfem"]["rows"]:
    soma[(cod_mun[r[im]], r[ia])] = soma.get((cod_mun[r[im]], r[ia]), 0.0) + r[iv]
cfem_anual = {"anos": anos, "rows": [[round(soma.get((l[0], a), 0.0), 2) for a in anos] for l in linhas]}

pacote = {
 "meta": {"versao": "indicadores-municipais-v1", "ano": 2025, "n_municipios": len(linhas), "fonte": "ANM (CFEM, Cadastro Mineiro, rodadas), IBGE via repositório; Squad 2/indicadores_compostos",
          "ressalvas": RESSALVAS[0], "ressalvas_en": RESSALVAS[1]},
 "cfem_anual": cfem_anual,
 "indicadores": [{"id": i[0], "familia": i[1][0], "familia_en": i[1][1], "nome": i[2][0], "nome_en": i[2][1], "unidade": i[3], "fmt": i[4],
                  "formula": i[5][0], "formula_en": i[5][1], "leitura": i[6][0], "leitura_en": i[6][1], "origem": i[7]} for i in IND],
 "presets": [{"id": p[0], "nome": p[1][0], "nome_en": p[1][1], "pesos": p[2]} for p in PRESETS],
 "cols": ["cod", *[i[0] for i in IND], "meses"],
 "rows": linhas,
}
SAIDA.parent.mkdir(parents=True, exist_ok=True)
SAIDA.write_text(json.dumps(pacote, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
print(f"{len(linhas)} municípios × {len(IND)} indicadores -> {SAIDA.relative_to(REPO)} ({SAIDA.stat().st_size/1024:.0f} KB)")
