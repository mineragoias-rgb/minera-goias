# -*- coding: utf-8 -*-
"""Abas 15a–15f — repositório de erros dentro da planilha (v19, etapa 3 do plano do Eliel).

Roda depois de write_fato_08 e antes da governança: lê a planilha intermediária v5d_fato, executa gerar_repositorio_erros.py em modo
"pipeline" (mesmo código que gera Squad 1/Auditoria e qualidade/repositorio_erros.xlsx, só que sobre esta planilha e sem gravar os
arquivos à parte) e grava v5e_erros com as abas:
  15a_repositorio_erros      catálogo ERR_### (fonte, tipo, exemplo, número medido, impacto, regra adotada, checagem, aba, status)
  15b_bario_niobio           bário × nióbio em Goiás (AMB bruta/beneficiada/contido, série adotada e CFEM por substância)
  15c_bario_niobio_processos CFEM de bário e nióbio por processo
  15d_contido_vs_bruto       teor implícito e alertas C1…C8 de todos os minerais de Goiás
  15e_tonelagens_repetidas   mesma tonelagem em linhas diferentes do AMB (todas as UFs)
  15f_amb_x_cfem             CFEM ÷ valor do AMB por mineral e ano, comparada com a alíquota legal
As checagens dos erros (ocorrências fora de erros_conhecidos.json) vão para TMP/_erros_checagens.json e a governança as põe na 14b.
Só lê as fontes; nada é corrigido.
"""
import json
import os
import runpy
import sys

import numpy as np
import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo

sys.stdout.reconfigure(encoding="utf-8")
from caminhos import BASE, TMP

SRC = f"{BASE}/documentacao/prototipo_bases_consolidadas_v5d_fato.xlsx"
OUT = f"{BASE}/documentacao/prototipo_bases_consolidadas_v5e_erros.xlsx"
HDR = 4
NAVY, TEAL, LBLUE, WHITE = "17365D", "1F6D7A", "DCE6F1", "FFFFFF"

g = runpy.run_path(os.path.join(os.path.dirname(os.path.abspath(__file__)), "gerar_repositorio_erros.py"),
                   init_globals={"PLAN": SRC, "MODO": "pipeline"})
cat, bn, bnproc, t, r, x = (g[k] for k in ("cat", "bn", "bnproc", "t", "r", "x"))
ANOS = g["ANOS"]

# nomes de coluna únicos nesta planilha (a governança confere tipo e descrição de cada campo entre as abas)
cat = cat.rename(columns={"codigo": "codigo_erro", "fonte": "fonte_erro", "tipo": "tipo_erro", "descricao": "descricao_erro",
                          "exemplo": "exemplo_erro", "status": "status_erro"})
bnproc = bnproc.rename(columns={"linhas": "linhas_cfem", "qtd_t": "cfem_t"})
r = r.rename(columns={"base": "base_amb", "grupo": "grupo_repeticao", "tipo": "tipo_repeticao", "classe": "classe_substancia"})
t = t.rename(columns={"base": "base_amb", "codigos": "codigos_alerta", "severidade": "severidade_alerta", "alertas": "alertas_contido"})
x = x.rename(columns={"producao_bruta_t": "amb_producao_bruta_t", "producao_beneficiada": "amb_producao_beneficiada",
                      "unidade_beneficiada": "amb_unidade_beneficiada"})

nb23 = bn[bn.rom_identico]
nota_ba = ("Bário × Nióbio no ROM de " + ", ".join(str(int(a)) for a in nb23.ano) + ": a mesma tonelagem nos dois minerais. O alerta fica, SEM correção "
           "por inferência — não se sabe qual dos dois números está certo; a decisão é do grupo. " if len(nb23) else "")
ABAS = [
    ("15a_repositorio_erros", cat, "RepositorioErros", "Repositório de erros por base (catálogo ERR_###)",
     f"{len(cat)} erros das fontes do Squad 1 e do próprio pipeline. Cada número de numero_medido foi recalculado nesta execução (dos brutos e desta "
     "planilha), salvo os marcados 'registro do projeto' em onde_foi_conferido. status_erro: tratado (regra no pipeline), sinalizado (registrado, sem "
     "correção), pendente ou resolvido na fonte. As checagens automáticas desses erros estão na 14b (verificações 'Repositório de erros').",
     {"descricao_erro", "exemplo_erro", "numero_medido", "impacto", "regra_adotada"}),
    ("15b_bario_niobio", bn, "BarioNiobio", "Bário × Nióbio em Goiás (AMB e CFEM)",
     nota_ba + "Quantidades em t; contido em t de BaSO4 (bário) e Nb2O5 (nióbio). O ROM do bário é a rocha lavrada para nióbio e fosfato (status "
     "rom_minerio_associado na 08): separe os dois pelo contido e pela CFEM por substância. Série do nióbio beneficiado = contido em Nb2O5 (v18). "
     "linha_csv = linha no CSV do AMB.", set()),
    ("15c_bario_niobio_processos", bnproc, "BarioNiobioProcessos", "CFEM de bário e nióbio por processo",
     "Os mesmos processos pagam BARITA e NIÓBIO ou MINÉRIO DE NIÓBIO.", set()),
    ("15d_contido_vs_bruto", t, "ContidoVsBruto", "Contido × quantidade no AMB — Goiás",
     f"{len(t)} linhas mineral-base-ano. Alertas: C1 contido > quantidade; C2 contido ≠ 0 com unidade '-'; C3 sem indicação (informativo); C4 teor fora "
     "de 1/3–3× a mediana do mineral; C5 contido zerado; C6 quantidade > 5× ou < 1/5 do ano anterior; C7 zero depois de ano produtivo; C8 ano sem linha.",
     {"alertas_contido"}),
    ("15e_tonelagens_repetidas", r, "TonelagensRepetidas", "Mesma tonelagem em linhas diferentes do AMB (todas as UFs)",
     f"{r.grupo_repeticao.nunique()} grupos, {len(r)} linhas: quantidade com o mesmo texto e unidade, ≠ 0, na mesma UF, ano e base (co-produto, "
     "mineral separado por teor ou mesma declaração em duas categorias). Mantidas; status alerta_producao_repetida na 08.", set()),
    ("15f_amb_x_cfem", x, "AmbXCfem", f"AMB × CFEM por mineral — Goiás {ANOS[0]}–{ANOS[-1]}",
     "CFEM ÷ valor do AMB (só vendas; vendas + consumo + transferência) comparada com a alíquota da Lei 8.001/1990, Anexo, com a redação da Lei "
     "13.540/2017. R1 produção sem CFEM; R2 CFEM sem produção; R3 sem valor e sem CFEM; R4 CFEM > 2× a alíquota; R5 < 1/4; R6 valor do AMB menor que a CFEM.",
     set()),
]

wb = openpyxl.load_workbook(SRC)
for nome, df, tabela, titulo, nota, quebra in ABAS:
    assert len(nome) <= 31, nome
    if nome in wb.sheetnames:
        del wb[nome]
    ws = wb.create_sheet(nome)
    ws.sheet_view.showGridLines = False
    cols = list(df.columns)
    last = get_column_letter(len(cols))
    ws.merge_cells(f"A1:{last}1")
    ws["A1"] = titulo
    ws["A1"].font = Font(bold=True, color=WHITE, size=14)
    ws["A1"].fill = PatternFill("solid", fgColor=NAVY)
    ws.merge_cells(f"A2:{last}2")
    ws["A2"] = nota
    ws["A2"].font = Font(italic=True, color="404040", size=10)
    ws["A2"].fill = PatternFill("solid", fgColor=LBLUE)
    ws["A2"].alignment = Alignment(wrap_text=True, vertical="center")
    ws.row_dimensions[2].height = 60
    for j, c in enumerate(cols, 1):
        h = ws.cell(HDR, j, c)
        h.font = Font(bold=True, color=WHITE)
        h.fill = PatternFill("solid", fgColor=TEAL)
        h.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")
    for i, row in enumerate(df.replace({np.nan: None}).itertuples(index=False), HDR + 1):
        for j, v in enumerate(row, 1):
            v = v.item() if isinstance(v, np.generic) else v
            cell = ws.cell(i, j, None if v == "" else v)
            if cols[j - 1] in quebra:
                cell.alignment = Alignment(wrap_text=True, vertical="top")
    if len(df):
        tb = Table(displayName=tabela, ref=f"A{HDR}:{last}{HDR + len(df)}")
        tb.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True)
        ws.add_table(tb)
    for j, c in enumerate(cols, 1):
        w = 60 if c in quebra else min(max(10, max([len(str(c))] + [len(str(v)) for v in df[c].head(200) if v is not None]) + 2), 50)
        ws.column_dimensions[get_column_letter(j)].width = w
    ws.freeze_panes = ws.cell(row=HDR + 1, column=2).coordinate
    print(f"{nome}: {len(df)} linhas")
wb.save(OUT)
with open(f"{TMP}/_erros_checagens.json", "w", encoding="utf-8") as f:
    json.dump(g["CHECAGENS"], f, ensure_ascii=False, indent=1)
print(f"SALVO: {OUT}; {len(g['CHECAGENS'])} checagens para a 14b "
      f"({sum(not c['ok'] for c in g['CHECAGENS'])} com ocorrência nova)")
