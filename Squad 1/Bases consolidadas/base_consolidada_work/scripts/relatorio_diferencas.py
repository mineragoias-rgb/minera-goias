# -*- coding: utf-8 -*-
"""Relatório de diferenças entre duas versões da planilha consolidada (a publicada e a refeita com a base nova).

    python relatorio_diferencas.py ANTES.xlsx DEPOIS.xlsx [--saida relatorio.md] [--limiar 5]

rodar_pipeline.py gera o relatório sozinho no fim (antes = a planilha que estava em documentacao/ quando o pipeline começou)
e grava documentacao/relatorio_diferencas.md. Seções:
  1. brutos que mudaram desde o manifesto (manifesto_brutos.py): novos, removidos, alterados, com data e tamanho;
  2. linhas preenchidas por aba, abas novas e abas que sumiram;
  3. IDs que entraram e saíram de cada dimensão (01, 02, 03, 04, 05, 06);
  4. totais por substância e ano — aba 09 (mineral × UF × ano) e aba 12 (mineral × nível × base × ano, a entrega ao Squad 2): o que
     entrou, saiu ou mudou mais que o limiar (padrão 5%), por coluna numérica, e o total de Goiás por ano;
  5. aba 14b: verificações que mudaram de status e o resultado das travas (travas.py).
Só lê; nada é corrigido.
"""
import argparse
import datetime as dt
import os
import sys

sys.dont_write_bytecode = True
AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)

HDR = 4  # linha do cabeçalho nas abas de dados
DIMS = {"01_dim_minerais": "mineral_id", "02_dim_empresas": "company_id", "03_dim_operacoes": "operation_id",
        "04_dim_projetos": "project_id", "05_dim_municipios": "municipality_id", "06_dim_ocorrencias_geologicas": "occurrence_id"}
CHAVE_09 = ("mineral_name", "uf", "year")
NUM_09 = ["production_t_rom", "production_beneficiada", "contido_beneficiada_t", "valor_venda_beneficiada_brl",
          "cfem_qtd_comercializada_t", "cfem_recolhido_brl"]
CHAVE_12 = ("mineral_name", "nivel_agregacao", "production_basis", "year")
NUM_12 = ["production_t", "cfem_brl_operacao"]
TOTAIS = [("09_cons_mineral_ano", CHAVE_09, NUM_09, "Aba 09 — mineral × UF × ano"),
          ("12_interface_squad1_squad2", CHAVE_12, NUM_12, "Aba 12 — entrega ao Squad 2: mineral × nível (estado/operação) × base × ano")]
MAX_LINHAS = 300


def ler(caminho):
    """{aba: linhas preenchidas}, {aba: [linhas]} só das abas usadas nas seções 3 e 4."""
    import openpyxl
    wb = openpyxl.load_workbook(caminho, read_only=True, data_only=True)
    cont, guard = {}, {}
    for ws in wb.worksheets:
        n, rows = 0, []
        querer = ws.title in DIMS or ws.title in {t[0] for t in TOTAIS}
        for r in ws.iter_rows(values_only=True):
            if any(v is not None for v in r):
                n += 1
            if querer:
                rows.append(r)
        cont[ws.title] = n
        if querer:
            guard[ws.title] = rows
    wb.close()
    return cont, guard


def _tab(rows, chave):
    """Cabeçalho = a primeira linha que tem a coluna-chave (linha 4 nas abas de dados)."""
    i = next((i for i, r in enumerate(rows[:10]) if chave in r), HDR - 1)
    cab = list(rows[i])
    return cab, [dict(zip(cab, r)) for r in rows[i + 1:] if any(v is not None for v in r)]


def _fmt(v):
    return "—" if v is None else (f"{v:,.2f}" if isinstance(v, float) else f"{v:,}" if isinstance(v, int) else str(v))


def _somar(rows, chave, nums):
    """{chave: {coluna: soma}} — soma as colunas numéricas por chave."""
    out = {}
    for r in _tab(rows, chave[0])[1]:
        acc = out.setdefault(tuple(r.get(c) for c in chave), {c: None for c in nums})
        for c in nums:
            v = r.get(c)
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                acc[c] = (acc[c] or 0) + v
    return out


def _totais(rows_a, rows_d, chave, nums, limiar):
    """Linhas Markdown: chaves que entraram/saíram e valores que mudaram mais que o limiar."""
    a, d = _somar(rows_a, chave, nums), _somar(rows_d, chave, nums)
    ent, sai = sorted(set(d) - set(a), key=str), sorted(set(a) - set(d), key=str)
    mud = []
    for k in sorted(set(a) & set(d), key=str):
        for c in nums:
            x, y = a[k][c], d[k][c]
            if x == y:
                continue
            dif = (y or 0) - (x or 0)
            rel = abs(dif) / abs(x) * 100 if x else float("inf")
            if abs(dif) > 0.01 and rel > limiar:
                mud.append((k, c, x, y, rel))
    cab = " | ".join(chave)
    out = [f"{len(ent)} combinações ({', '.join(chave)}) entraram, {len(sai)} saíram e {len(mud)} valores mudaram mais que {limiar:g}%."]
    if ent or sai:
        out += ["", f"| {cab} | Entrou/saiu |", "|" + "---|" * (len(chave) + 1)]
        out += [f"| {' | '.join(map(str, k))} | entrou |" for k in ent[:MAX_LINHAS]]
        out += [f"| {' | '.join(map(str, k))} | saiu |" for k in sai[:MAX_LINHAS]]
    if mud:
        out += ["", f"| {cab} | Coluna | Antes | Depois | Variação |", "|" + "---|" * len(chave) + "---|---:|---:|---:|"]
        for k, c, x, y, rel in sorted(mud, key=lambda m: -m[4])[:MAX_LINHAS]:
            out.append(f"| {' | '.join(map(str, k))} | {c} | {_fmt(x)} | {_fmt(y)} | "
                       + ("novo" if rel == float("inf") else f"{rel:,.1f}%") + " |")
        if len(mud) > MAX_LINHAS:
            out.append(f"| … mais {len(mud) - MAX_LINHAS} |")
    return out


def relatorio(antes, depois, limiar=5.0, brutos=True):
    linhas = [f"# Relatório de diferenças da base consolidada", "",
              f"Gerado em {dt.date.today():%d/%m/%Y} por `relatorio_diferencas.py`.", "",
              f"- antes: `{os.path.basename(antes)}`", f"- depois: `{os.path.basename(depois)}`",
              f"- limiar para \"mudou\": {limiar:g}% (e diferença absoluta > 0,01)", ""]
    # 1. brutos
    if brutos:
        linhas += ["## 1. Dados brutos desde o manifesto", ""]
        try:
            import manifesto_brutos
            t, ln = manifesto_brutos.conferir()
            linhas += ln + [""] + [f"**TRAVA:** {x}" for x in t] + [""]
        except Exception as e:  # o relatório não pode cair por causa do manifesto
            linhas += [f"(manifesto não conferido: {e})", ""]
    ca, ga = ler(antes)
    cd, gd = ler(depois)
    # 2. linhas por aba
    linhas += ["## 2. Linhas preenchidas por aba", "", "| Aba | Antes | Depois | Diferença |", "|---|---:|---:|---:|"]
    for aba in list(cd) + [a for a in ca if a not in cd]:
        a, d = ca.get(aba), cd.get(aba)
        marca = " (nova)" if a is None else " (sumiu)" if d is None else ""
        linhas.append(f"| {aba}{marca} | {_fmt(a)} | {_fmt(d)} | {'' if a is None or d is None else f'{d - a:+,}'} |")
    # 3. IDs
    linhas += ["", "## 3. IDs que entraram e saíram das dimensões", "", "| Aba | Antes | Depois | Entraram | Saíram | Exemplos |",
               "|---|---:|---:|---:|---:|---|"]
    for aba, chave in DIMS.items():
        if aba not in ga or aba not in gd:
            continue
        ia = {r.get(chave) for r in _tab(ga[aba], chave)[1]} - {None}
        id_ = {r.get(chave) for r in _tab(gd[aba], chave)[1]} - {None}
        ent, sai = sorted(map(str, id_ - ia)), sorted(map(str, ia - id_))
        ex = "; ".join([f"+{x}" for x in ent[:4]] + [f"−{x}" for x in sai[:4]])
        linhas.append(f"| {aba} | {len(ia):,} | {len(id_):,} | {len(ent):,} | {len(sai):,} | {ex} |")
    # 4. totais por substância e ano: aba 09 (consolidada) e aba 12 (entrega ao Squad 2)
    for n_sec, (aba, chave, nums, titulo) in enumerate(TOTAIS):
        linhas += ["", f"## 4{'ab'[n_sec]}. {titulo}", ""]
        if aba in ga and aba in gd:
            linhas += _totais(ga[aba], gd[aba], chave, nums, limiar)
    if "09_cons_mineral_ano" in ga and "09_cons_mineral_ano" in gd:
        a9, d9 = (_somar(g["09_cons_mineral_ano"], CHAVE_09, NUM_09) for g in (ga, gd))
        # total por ano (GO)
        anos = sorted({k[2] for k in set(a9) | set(d9) if k[1] == "GO" and k[2] is not None})
        if anos:
            linhas += ["", "Totais de Goiás por ano (soma da aba 09):", "",
                       "| Ano | ROM antes (t) | ROM depois (t) | CFEM antes (R$) | CFEM depois (R$) |", "|---|---:|---:|---:|---:|"]
            for ano in anos:
                def s(m, c):
                    return sum((v[c] or 0) for k, v in m.items() if k[1] == "GO" and k[2] == ano)
                linhas.append(f"| {ano} | {s(a9, 'production_t_rom'):,.0f} | {s(d9, 'production_t_rom'):,.0f} | "
                              f"{s(a9, 'cfem_recolhido_brl'):,.2f} | {s(d9, 'cfem_recolhido_brl'):,.2f} |")
    # 5. 14b e travas
    import travas
    linhas += ["", "## 5. Aba 14b e travas", ""]
    a14, d14 = travas.ler_14b(antes), travas.ler_14b(depois)
    muda = [(n, a14.get(n, (None, "", "(nova)"))[2], v[2], v[0]) for n, v in d14.items() if a14.get(n, (None, "", "(nova)"))[2] != v[2]]
    muda += [(n, a14[n][2], "(sumiu)", "") for n in a14 if n not in d14]
    if muda:
        linhas += ["| Verificação | Antes | Depois | n |", "|---|---|---|---|"] + [f"| {n[:110]} | {x} | {y} | {k} |" for n, x, y, k in muda]
    else:
        linhas.append("Nenhuma verificação mudou de status.")
    b, av, ln = travas.conferir(depois, antes)
    linhas += ["", travas.texto(b, av, ln)]
    return "\n".join(linhas) + "\n", b


def main():
    ap = argparse.ArgumentParser(description="Relatório de diferenças entre duas versões da planilha consolidada.")
    ap.add_argument("antes")
    ap.add_argument("depois")
    ap.add_argument("--saida", help="grava o relatório aqui (padrão: só imprime)")
    ap.add_argument("--limiar", type=float, default=5.0, help="variação em %% para listar um valor da aba 09 como mudado")
    ap.add_argument("--sem-brutos", action="store_true", help="não confere o manifesto dos brutos")
    args = ap.parse_args()
    md, _ = relatorio(args.antes, args.depois, args.limiar, brutos=not args.sem_brutos)
    if args.saida:
        open(args.saida, "w", encoding="utf-8", newline="\n").write(md)
        print(f"SALVO: {args.saida}")
    else:
        print(md)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
