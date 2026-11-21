# -*- coding: utf-8 -*-
"""Análises do repositório de erros (gerar_repositorio_erros.py): leitura dos brutos e da planilha, contido × quantidade no AMB,
tonelagens repetidas, AMB × CFEM com a alíquota legal e bário × nióbio. Só lê; não muda nenhum arquivo."""
import glob
import os
import re

import numpy as np
import openpyxl
import pandas as pd

from caminhos import BASE, arquivo

MASSA_T = {"t": 1.0, "kg": 1e-3, "g": 1e-6, "ct": 2e-7, "mg": 1e-9}


def planilha():
    """A planilha consolidada de versão mais alta em documentacao/."""
    vs = [(int(m.group(1)), p) for p in glob.glob(os.path.join(BASE, "documentacao", "prototipo_bases_consolidadas_v*.xlsx"))
          if (m := re.search(r"_v(\d+)\.xlsx$", p))]
    return max(vs)[1]


# nomes de coluna antes da governança (planilha intermediária do pipeline) -> nomes da planilha final
_RENOMEIA = {"ano": "year", "mineral_nome": "mineral_name", "mineral_nome_padronizado": "mineral_name", "municipio_nome": "municipality_name",
             "producao_rom_t": "production_t_rom", "producao_beneficiada": "production_beneficiada", "unidade_beneficiada": "production_beneficiada_unit",
             "verificação": "verificacao", "decisão": "decisao"}


def aba(nome, caminho=None, linha_cabecalho=4):
    wb = openpyxl.load_workbook(caminho or planilha(), read_only=True)
    rows = list(wb[nome].iter_rows(min_row=linha_cabecalho, values_only=True))
    wb.close()
    return pd.DataFrame(rows[1:], columns=[_RENOMEIA.get(c, c) for c in rows[0]]).dropna(how="all")


def num(s):
    if s is None or (isinstance(s, float) and np.isnan(s)):
        return np.nan
    s = str(s).strip()
    if s in ("", "-"):
        return np.nan
    return float(s.replace(",", "."))


def _amb(nome, base, col):
    d = pd.read_csv(arquivo(f"dados/ANM/producao_amb_ral/{nome}"), encoding="cp1252", dtype=str, keep_default_na=False)
    c = list(d.columns)
    out = pd.DataFrame({"base": base, "arquivo": nome, "linha_csv": d.index + 2, "ano": d[c[0]].astype(int), "uf": d[c[1]],
                        "classe": d[c[2]], "substancia": d[c[3]], "qtd_txt": d[c[4]], "qtd": d[c[4]].map(num)})
    for k, i in col.items():
        out[k] = d[c[i]].map(num) if k not in ("unid", "unid_contido", "indicacao") else d[c[i]].str.strip()
    if "unid" not in col:
        out["unid"] = "t"
    return out


def load_amb():
    bruta = _amb("Producao_Bruta.csv", "bruta_rom", dict(contido=5, unid_contido=6, indicacao=7, valor_venda=9, valor_consumo=11, valor_transf=13))
    benef = _amb("Producao_Beneficiada.csv", "beneficiada", dict(unid=5, contido=6, unid_contido=7, indicacao=8, valor_venda=11,
                                                               valor_consumo=14, valor_transf=17))
    a = pd.concat([bruta, benef], ignore_index=True)
    a["contido_txt"] = None
    return a


def load_cfem():
    c = pd.read_csv(arquivo("dados/ANM/cfem/CFEM_Arrecadacao_2022_2026_GO.csv"), sep=";", encoding="cp1252", dtype=str, keep_default_na=False)
    c["valor"] = c["ValorRecolhido"].map(num)
    c["qtd"] = c["QuantidadeComercializada"].map(num)
    c["unid"] = c["UnidadeDeMedida"].str.strip()
    c["ano"] = c["Ano"].astype(int)
    return c


# ----------------------------------------------------------------------------------------------------------------- contido
def teor_df(go):
    """Uma linha por (mineral, base, ano) em GO com teor implícito (contido ÷ quantidade, em t) e os alertas C1…C8."""
    d = go.copy()
    d["qtd_t"] = d.qtd * d.unid.map(MASSA_T)
    d["contido_t"] = d.contido * d.unid_contido.map(MASSA_T)
    d["teor_pct"] = np.where((d.qtd_t > 0) & (d.contido_t > 0), d.contido_t / d.qtd_t * 100, np.nan)
    d = d.join(d.groupby(["substancia", "base"]).teor_pct.median().rename("teor_mediano_pct"), on=["substancia", "base"])
    d = d.sort_values(["substancia", "base", "ano"])
    d["qtd_ano_anterior"] = d.groupby(["substancia", "base"]).qtd_t.shift(1)
    d["ano_anterior"] = d.groupby(["substancia", "base"]).ano.shift(1)
    n_contido = d.groupby(["substancia", "base"]).contido_t.transform(lambda s: (s > 0).sum())
    alertas = []
    for r in d.itertuples():
        a = []
        if r.qtd_t > 0 and r.contido_t > r.qtd_t * 1.0000001:
            a.append("C1 contido maior que a quantidade")
        if r.unid_contido == "-" and (r.contido or 0) != 0:
            a.append("C2 contido diferente de zero com unidade '-'")
        if (r.contido or 0) > 0 and not r.indicacao:
            a.append("C3 contido sem indicação (não se sabe se é minério, óxido ou metal)")
        if r.teor_pct > 0 and r.teor_mediano_pct > 0 and not a[:1] == ["C1 contido maior que a quantidade"]:
            f = r.teor_pct / r.teor_mediano_pct
            if f > 3 or f < 1 / 3:
                a.append(f"C4 teor {r.teor_pct:.4g}% = {f:.2f}× a mediana do mineral ({r.teor_mediano_pct:.4g}%)")
        if r.qtd_t > 0 and not (r.contido_t > 0) and n_contido[r.Index] >= 3:
            a.append("C5 contido zerado num ano com produção (o mineral informa contido nos outros anos)")
        if r.qtd_t > 0 and r.qtd_ano_anterior > 0 and r.ano - r.ano_anterior == 1:
            f = r.qtd_t / r.qtd_ano_anterior
            if f > 5 or f < 0.2:
                a.append(f"C6 quebra de série: {f:.2f}× o ano anterior")
        if (r.qtd_t or 0) == 0 and r.qtd_ano_anterior and r.qtd_ano_anterior > 0:
            a.append("C7 produção zero logo após ano com produção")
        alertas.append("; ".join(a))
    d["alertas"] = alertas
    falt = []
    for (s, b), g in d.groupby(["substancia", "base"]):
        anos = set(g.ano)
        falt += [{"substancia": s, "base": b, "ano": y, "alertas": "C8 ano sem linha no AMB entre anos com linha"}
                 for y in range(min(anos), max(anos) + 1) if y not in anos]
    return pd.concat([d, pd.DataFrame(falt)], ignore_index=True).sort_values(["substancia", "base", "ano"])


def repetidas(a):
    """Mesma quantidade (texto original e unidade iguais, ≠ 0) em linhas diferentes da mesma UF, ano e base."""
    d = a[a.qtd > 0].copy()
    d["k"] = d.qtd_txt.str.strip() + "|" + d.unid
    d["n"] = d.groupby(["uf", "ano", "base", "k"]).substancia.transform("size")
    d = d[d.n > 1].copy()
    d["grupo"] = d.groupby(["uf", "ano", "base", "k"]).ngroup()
    d["minerais_do_grupo"] = d.groupby("grupo").substancia.transform(lambda s: " + ".join(sorted(set(s))))
    d["tipo"] = np.where(d.groupby("grupo").substancia.transform("nunique") > 1, "entre minerais diferentes",
                         "mesmo mineral em 2 linhas (categoria/teor)")
    return d.sort_values(["uf", "ano", "base", "grupo"])


# ------------------------------------------------------------------------------------------------------------- AMB × CFEM
ALIQ = {  # Lei 8.001/1990, Anexo, redação da Lei 13.540/2017 (conferida em 19/11/2026 no texto do Planalto)
    "Ouro": (1.5, "1,5% — ouro"),
    "Nióbio": (3.0, "3% — bauxita, manganês, nióbio e sal-gema"),
    "Alumínio (Bauxita)": (3.0, "3% — bauxita, manganês, nióbio e sal-gema"),
    "Manganês": (3.0, "3% — bauxita, manganês, nióbio e sal-gema"),
    "Ferro": (3.5, "3,5% — ferro"),
    "Areia": (1.0, "1% — uso imediato na construção civil"),
    "Rochas (Britadas) e Cascalho": (1.0, "1% — uso imediato na construção civil"),
    "Saibro": (1.0, "1% — uso imediato na construção civil"),
    "Rochas Ornamentais": (1.0, "1% — rochas ornamentais"),
    "Rochas Ornamentais - Outras": (1.0, "1% — rochas ornamentais"),
    "Água Mineral": (1.0, "1% — águas minerais e termais"),
    "Argilas": (None, "1% se uso imediato na construção civil, senão 2% — depende do uso"),
    "Calcário": (None, "1% se uso imediato na construção civil, senão 2% — depende do uso"),
}
DEMAIS = (2.0, "2% — diamante e demais substâncias minerais")
ANOS_CFEM = range(2022, 2026)


def amb_x_cfem(a, d09, dmin):
    go = a[(a.uf == "GO") & a.ano.isin(ANOS_CFEM)]
    p = go.pivot_table(index=["substancia", "ano"], columns="base", values=["qtd", "valor_venda", "valor_consumo", "valor_transf"], aggfunc="sum")
    p.columns = [f"{v}_{b}" for v, b in p.columns]
    p = p.reset_index().join(go[go.base == "beneficiada"].groupby(["substancia", "ano"]).unid.first().rename("unid_beneficiada"),
                             on=["substancia", "ano"])
    pai = dmin.set_index("mineral_name").mineral_grupo_pai.dropna()
    id2nome = dmin.set_index("mineral_id").mineral_name
    c = d09[(d09.uf == "GO") & d09.year.isin(ANOS_CFEM)][["mineral_name", "year", "cfem_recolhido_brl"]].copy()
    c["mineral_amb"] = c.mineral_name.map(lambda n: id2nome.get(pai.get(n), n) if n in pai.index else n)
    c = c.groupby(["mineral_amb", "year"]).agg(cfem_brl=("cfem_recolhido_brl", "sum"),
                                                subitens=("mineral_name", lambda s: ", ".join(sorted(set(s))))).reset_index()
    m = p.merge(c.rename(columns={"mineral_amb": "substancia", "year": "ano"}), on=["substancia", "ano"], how="outer")
    for col in [x for x in m.columns if x.startswith(("qtd_", "valor_")) or x == "cfem_brl"]:
        m[col] = pd.to_numeric(m[col], errors="coerce").fillna(0.0)
    m["vendas_brl"] = m.valor_venda_bruta_rom + m.valor_venda_beneficiada
    m["vendas_consumo_transf_brl"] = (m.vendas_brl + m.valor_consumo_bruta_rom + m.valor_consumo_beneficiada
                                      + m.valor_transf_bruta_rom + m.valor_transf_beneficiada)
    m["cfem_pct_vendas"] = np.where(m.vendas_brl > 0, m.cfem_brl / m.vendas_brl.where(m.vendas_brl > 0) * 100, np.nan)
    m["cfem_pct_vendas_consumo_transf"] = np.where(m.vendas_consumo_transf_brl > 0,
                                                   m.cfem_brl / m.vendas_consumo_transf_brl.where(m.vendas_consumo_transf_brl > 0) * 100, np.nan)
    m["aliquota_legal_pct"] = m.substancia.map(lambda s: ALIQ.get(s, DEMAIS)[0])
    m["aliquota_legal_texto"] = m.substancia.map(lambda s: ALIQ.get(s, DEMAIS)[1])
    clas = []
    for r in m.itertuples():
        prod = (r.qtd_bruta_rom or 0) > 0 or (r.qtd_beneficiada or 0) > 0
        if prod and r.cfem_brl == 0:
            clas.append("R1 produção no AMB sem CFEM no ano")
        elif not prod and r.cfem_brl > 0:
            clas.append("R2 CFEM sem produção no AMB no ano")
        elif not prod:
            clas.append("sem produção e sem CFEM")
        elif r.vendas_consumo_transf_brl == 0 and r.cfem_brl == 0:
            clas.append("R3 produção sem valor comercial no AMB e sem CFEM")
        elif r.vendas_consumo_transf_brl < r.cfem_brl:
            clas.append("R6 valor comercial do AMB menor que a própria CFEM (AMB sem valor ou incompleto)")
        else:
            al = r.aliquota_legal_pct if r.aliquota_legal_pct == r.aliquota_legal_pct and r.aliquota_legal_pct else 2.0
            lo = r.cfem_pct_vendas_consumo_transf
            hi = r.cfem_pct_vendas if r.cfem_pct_vendas == r.cfem_pct_vendas else lo
            if lo > al * 2:
                clas.append("R4 CFEM acima de 2× a alíquota mesmo sobre todo o valor do AMB")
            elif hi < al * 0.25:
                clas.append("R5 CFEM abaixo de 1/4 da alíquota mesmo só sobre as vendas")
            else:
                clas.append("compatível com a alíquota (dentro da faixa)")
    m["classificacao"] = clas
    return m.sort_values(["substancia", "ano"])


# ------------------------------------------------------------------------------------------------------- bário × nióbio
CFEM_BA_NB = (("BARITA", "cfem_barita"), ("NIÓBIO", "cfem_niobio"), ("MINÉRIO DE NIÓBIO", "cfem_minerio_niobio"))


def bario_niobio(a, cf):
    go = a[(a.uf == "GO") & a.substancia.isin(["Bário", "Nióbio"])]
    rows = []
    for y in range(int(go.ano.min()), int(go.ano.max()) + 1):
        r = {"ano": y}
        for s, k in (("Bário", "ba"), ("Nióbio", "nb")):
            for b, kb in (("bruta_rom", "rom"), ("beneficiada", "benef")):
                x = go[(go.substancia == s) & (go.base == b) & (go.ano == y)]
                r[f"{k}_{kb}_t"] = x.qtd.sum() if len(x) else np.nan
                r[f"{k}_{kb}_contido_t"] = x.contido.sum() if len(x) else np.nan
                r[f"{k}_{kb}_linha_csv"] = ", ".join(map(str, x.linha_csv)) if len(x) else "sem linha"
        r["rom_identico"] = bool(r["ba_rom_t"] > 0 and r["ba_rom_t"] == r["nb_rom_t"])
        r["ba_teor_rom_pct_baso4"] = r["ba_rom_contido_t"] / r["ba_rom_t"] * 100 if r["ba_rom_t"] else np.nan
        r["nb_teor_rom_pct_nb2o5"] = r["nb_rom_contido_t"] / r["nb_rom_t"] * 100 if r["nb_rom_t"] else np.nan
        r["nb_serie_beneficiada_t_nb2o5"] = r["nb_benef_contido_t"]  # decisão ERR_005 (v18): a série do nióbio beneficiado é o contido
        for sub, k in CFEM_BA_NB:
            x = cf[(cf["Substância"].str.strip() == sub) & (cf.ano == y)]
            r[k + "_brl"] = x.valor.sum() if y >= cf.ano.min() else np.nan
            r[k + "_t"] = x[x.unid == "t"].qtd.sum() if y >= cf.ano.min() else np.nan
        rows.append(r)
    x = cf[cf["Substância"].str.strip().isin([s for s, _ in CFEM_BA_NB])]
    proc = x.groupby(["Processo", "AnoDoProcesso", "Substância", "ano"]).agg(linhas=("valor", "size"), cfem_brl=("valor", "sum"),
                                                                           qtd_t=("qtd", "sum")).reset_index()
    proc["processo"] = proc.Processo + "/" + proc.AnoDoProcesso
    return pd.DataFrame(rows), proc[["processo", "Substância", "ano", "linhas", "qtd_t", "cfem_brl"]].rename(
        columns={"Substância": "substancia_cfem", "processo": "processo_anm"})
