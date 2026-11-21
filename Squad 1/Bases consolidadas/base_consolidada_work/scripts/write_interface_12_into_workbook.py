# -*- coding: utf-8 -*-
"""Aba 12 (v5 -> v5a_interface): entrega Squad 1 -> Squad 2 gerada por build_interface_12.py, no lugar da maquete.
A aba 08 entra depois (write_fato_08_into_workbook.py) e a governança valida as duas."""
import json
import sys

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo

sys.stdout.reconfigure(encoding="utf-8")
from caminhos import BASE, TMP  # caminhos relativos ao projeto — ver caminhos.py
SRC = f"{BASE}/documentacao/prototipo_bases_consolidadas_v5b_projetos.xlsx"  # v5 + 06/06b + 04/04b (write_ocorrencias_06, write_projetos_04)
OUT = f"{BASE}/documentacao/prototipo_bases_consolidadas_v5c_interface.xlsx"
ABA = "12_interface_squad1_squad2"
HDR = 4
NAVY, TEAL, LBLUE, WHITE = "17365D", "1F6D7A", "DCE6F1", "FFFFFF"

dados = json.load(open(f"{TMP}/_interface_12.json", encoding="utf-8"))
res = json.load(open(f"{TMP}/_interface_12_resumo.json", encoding="utf-8"))
COLS, LINHAS = dados["colunas"], dados["linhas"]
LARG = dict(mineral_id=10, mineral_name=24, company_id=21, operation_id=17, project_id=10, municipality_id=11, year=7, production_t=16,
            production_basis=12, latitude=11, longitude=11, source_id=34, nivel_agregacao=10, processo_anm=13, valor_observado_estimado=12,
            metodo_estimacao=50, erro_estimativa_intervalo=40, participacao_cfem_brl=12, cfem_brl_operacao=15, cfem_brl_mineral_ano=16,
            production_t_rateio_por_t=16, status_validacao=26, responsavel_validacao=30, periodo_referencia=9, tipo_fonte=9, source_url=50,
            data_acesso=22, fato_ids=28, observacao=70)
FMT = dict(year="0", production_t="#,##0.000", latitude="0.000000", longitude="0.000000", participacao_cfem_brl="0.000000",
           cfem_brl_operacao="#,##0.00", cfem_brl_mineral_ano="#,##0.00", production_t_rateio_por_t="#,##0.000")


def br(x, casas=0):
    return f"{x:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


wb = openpyxl.load_workbook(SRC)
pos = wb.sheetnames.index(ABA)
del wb[ABA]
ws = wb.create_sheet(ABA, pos)
ws.sheet_view.showGridLines = False
last = get_column_letter(len(COLS))
ws.merge_cells(f"A1:{last}1")
ws["A1"] = "Interface — Entrega Squad 1 → Squad 2: produção por mineral, ano e operação (v9, real)"
ws["A1"].font = Font(bold=True, color=WHITE, size=14)
ws["A1"].fill = PatternFill("solid", fgColor=NAVY)
ws.row_dimensions[1].height = 26
ws.merge_cells(f"A2:{last}2")
cob = "; ".join(f"{a}: {br(p, 1)}%" for a, p in sorted(res["cobertura_por_ano"].items()))
ws["A2"] = (
    f"{br(res['linhas'])} linhas com os campos do Contrato de Dados (fluxo Squad 1 → Squad 2) + production_basis + campos de governança. "
    f"NÍVEL ESTADO ({br(res['estado'])} linhas): produção OBSERVADA de Goiás no AMB por mineral, ano (2010–2025) e base (ROM ou beneficiada; no nióbio, conteudo_mineral = contido da beneficiada em t de Nb2O5), em t — igual à 08. "
    f"NÍVEL OPERAÇÃO ({br(res['operacao'])} linhas, {br(res['processos'])} processos): abertura ESTIMADA desse total em 2022–2025, rateada pela participação de cada "
    "processo na CFEM recolhida (R$) do mineral no ano; a soma das operações é igual ao total do estado — não somar os dois níveis. "
    f"Produção aberta por operação: {cob}. Da produção estimada, {br(res['pct_prod_com_operation_id'], 1)}% tem operation_id e {br(res['pct_prod_com_coordenadas'], 1)}% "
    "coordenadas (o resto é de processos sem poligonal no SIGMINE). A ANM não publica produção por operação: as linhas de operação são estimativa "
    "(valor_observado_estimado, metodo_estimacao, erro_estimativa_intervalo) e não devem ser usadas como produção observada nem como denominador observado de "
    "intensidade operação-específica. Conteúdo mineral (contido) fica na 08; project_id fica vazio até o Radar de Projetos.")
ws["A2"].font = Font(italic=True, color="404040", size=10)
ws["A2"].fill = PatternFill("solid", fgColor=LBLUE)
ws["A2"].alignment = Alignment(wrap_text=True, vertical="center")
ws.row_dimensions[2].height = 92

for i, c in enumerate(COLS, start=1):
    cell = ws.cell(row=HDR, column=i, value=c)
    cell.font = Font(bold=True, color=WHITE)
    cell.fill = PatternFill("solid", fgColor=TEAL)
    cell.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")
ws.row_dimensions[HDR].height = 30
fmt_col = {COLS.index(k): f for k, f in FMT.items()}
for r_i, linha in enumerate(LINHAS, start=HDR + 1):
    for c_i, v in enumerate(linha):
        if v is None or v == "":
            continue
        cell = ws.cell(row=r_i, column=c_i + 1, value=v)
        f = fmt_col.get(c_i)
        if f:
            cell.number_format = f
t = Table(displayName="InterfaceSquad1Squad2V9", ref=f"A{HDR}:{last}{HDR + len(LINHAS)}")
t.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True)
ws.add_table(t)
for i, c in enumerate(COLS, start=1):
    ws.column_dimensions[get_column_letter(i)].width = LARG.get(c, 16)
ws.freeze_panes = ws.cell(row=HDR + 1, column=3).coordinate

wb.save(OUT)
print(f"{ABA} escrita: {len(LINHAS)} linhas × {len(COLS)} colunas -> {OUT}")
