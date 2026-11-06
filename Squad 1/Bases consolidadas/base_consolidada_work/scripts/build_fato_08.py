# -*- coding: utf-8 -*-
"""Aba 08 -- fato longo de producao e CFEM: UMA LINHA POR CELULA NUMERICA das fontes.

Fontes: ANM AMB Producao_Bruta e Producao_Beneficiada (todas as UFs, para a soma BR da 09) e CFEM de Goias.
Cada linha aponta a celula exata (source_file + source_linha + coluna_original), guarda o texto da celula
(valor_original, nunca sobrescrito) e o valor final na unidade padrao (valor_tratado), que e o que as abas
09, 10 e 11 somam. As chaves vem das Bases 1 e 3 (mesmo mineral_id, company_id, municipality_id, operation_id),
e o tratamento da quantidade da CFEM e o da Base 1, linha a linha (_cfem_linhas.json).

Pente fino desta base (achados que definem as decisoes abaixo):
  - arquivos: registros CSV = linhas fisicas nos 3 arquivos -> source_linha = indice + 2 e exato;
  - AMB: nenhuma celula numerica vazia; 'Quantidade Contido' com unidade '-' e zero = nao se aplica (nao e medida);
  - AMB beneficiada: a unidade (t, kg, ct) e unica por substancia -> a soma BR da 09 nao mistura unidades;
  - CFEM: 21.744 linhas repetem (ano, mes, processo, substancia, municipio, unidade, CPF_CNPJ) -- sao recolhimentos
    distintos, entao o grao e a linha do arquivo, sem agregar; 7 quantidades vazias.
Energia: nenhuma fonte do Squad 1 mede consumo; as linhas de energia entram com o Squad 2.
"""
import contextlib
import csv
import io
import json
import os
import re
import sys
from collections import Counter, defaultdict

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
from caminhos import BASE, TMP, arquivo, data_acesso  # caminhos relativos ao projeto — ver caminhos.py


# ---------------------------------------------------------------------------
# 0) chaves e pontes das Bases 1 e 3 (sem duplicar regras)
# ---------------------------------------------------------------------------
class _Mudo(io.StringIO):
    def reconfigure(self, **k):
        pass


B3 = {"__name__": "base3"}
with contextlib.redirect_stdout(_Mudo()):
    exec(open(f"{BASE}/base_consolidada_work/scripts/build_base3_empresa_mineral_ano.py", encoding="utf-8").read(), B3)
sys.stdout.reconfigure(encoding="utf-8")
read_csv, to_num, norm, MIN_DEF = B3["read_csv"], B3["to_num"], B3["norm"], B3["MIN_DEF"]
ANM_CATEGORY_TO_KEY = B3["_ns"]["ANM_CATEGORY_TO_KEY"]
proc2company, MUN_NOME, cfem, USO_PADRAO = B3["proc2company"], B3["MUN_NOME"], B3["cfem"], B3["USO_ROCHAS"]["padrao"]
proc2company_cfem = B3["proc2company_cfem"]  # processo sem titular no Cadastro: empresa pela raiz do CNPJ pagador (Base 3, 4b)
_ordem = sorted(MIN_DEF.items(), key=lambda kv: (kv[1][1], kv[1][0]))
KEY2ID = {k: f"MIN_{i + 1:03d}" for i, (k, _) in enumerate(_ordem)}
PARA_T = {"t": 1.0, "kg": 1e-3, "g": 1e-6, "ct": 2e-7}  # o mesmo da Base 1 (ct = quilate, 0,2 g)
FATOR_TXT = {"kg": "0,001", "g": "0,000001", "ct": "0,0000002"}
print("Chaves das Bases 1 e 3 carregadas.")

FONTES = {
    "SRC_ANM_PROD_BRUTA": dict(arquivo="dados/ANM/producao_amb_ral/Producao_Bruta.csv", url="https://dadosabertos.anm.gov.br/AMB/Producao_Bruta.csv"),
    "SRC_ANM_PROD_BENEF": dict(arquivo="dados/ANM/producao_amb_ral/Producao_Beneficiada.csv", url="https://dadosabertos.anm.gov.br/AMB/Producao_Beneficiada.csv"),
    "SRC_ANM_CFEM": dict(arquivo="dados/ANM/cfem/CFEM_Arrecadacao_2022_2026_GO.csv", url="https://dadosabertos.anm.gov.br/CFEM/CFEM_Arrecadacao_2022_2026.csv"),
}
for _f in FONTES.values():  # mesmo cálculo de data_arquivo_local da 07 (a governança confere)
    _f["data_acesso"] = data_acesso([_f['arquivo']])
TIPO_FONTE = "oficial"
RESPONSAVEL = "Squad 1 / Estudante 1 — checagens automáticas do pipeline (ver 14b)"

COLS = ["fato_id", "metrica", "year", "periodo_referencia", "uf", "mineral_id", "mineral_name", "company_id", "operation_id", "processo_anm", "project_id",
        "municipality_id", "valor_original", "unidade_original", "tratamento", "valor_tratado", "unidade_padrao", "production_basis",
        "valor_observado_estimado", "metodo_estimacao", "erro_estimativa_intervalo", "status_validacao", "responsavel_validacao",
        "source_id", "tipo_fonte", "source_url", "data_acesso", "source_file", "source_linha", "coluna_original", "mineral_nome_original", "notas"]
IX = {c: i for i, c in enumerate(COLS)}
linhas, fora = [], Counter()


def nova(sid, linha, coluna, metrica, ano, periodo, uf, k, bruto, un_orig, trat, vt, un_pad, basis, nome_orig,
         status="valido", company=None, operation=None, processo=None, municipio=None, notas=None):
    f = FONTES[sid]
    row = [None] * len(COLS)
    row[IX["metrica"]], row[IX["year"]], row[IX["periodo_referencia"]], row[IX["uf"]] = metrica, ano, periodo, uf
    row[IX["mineral_id"]], row[IX["mineral_name"]] = (KEY2ID[k], MIN_DEF[k][0]) if k else (None, None)
    row[IX["company_id"]], row[IX["operation_id"]], row[IX["municipality_id"]] = company, operation, municipio
    row[IX["processo_anm"]] = processo
    row[IX["valor_original"]], row[IX["unidade_original"]], row[IX["tratamento"]] = bruto, un_orig, trat
    row[IX["valor_tratado"]], row[IX["unidade_padrao"]], row[IX["production_basis"]] = vt, un_pad, basis
    row[IX["valor_observado_estimado"]], row[IX["status_validacao"]], row[IX["responsavel_validacao"]] = "observado", status, RESPONSAVEL
    row[IX["source_id"]], row[IX["tipo_fonte"]], row[IX["source_url"]], row[IX["data_acesso"]] = sid, TIPO_FONTE, f["url"], f["data_acesso"]
    row[IX["source_file"]], row[IX["source_linha"]], row[IX["coluna_original"]] = f["arquivo"], linha, coluna
    row[IX["mineral_nome_original"]], row[IX["notas"]] = nome_orig, ("; ".join(notas) if notas else None)
    linhas.append(row)


def num(s):
    """Leitor numérico da Base 1; ',00' (zero sem inteiro) vira 0 em vez de vazio."""
    v = to_num(s)
    if v is None and re.fullmatch(r"-?,0+", s):
        v = 0.0
    return v


def unidade_padrao(v, un):
    """(valor tratado, unidade padrão, tratamento) -- massa em t pelo contrato; sem densidade não há conversão."""
    u = un.lower()
    if un == "R$":
        return v, "BRL", None
    if u == "t":
        return v, "t", None
    if u in PARA_T:
        return (None if v is None else v * PARA_T[u]), "t", f"{u} → t (× {FATOR_TXT[u]})"
    if un in ("", "-"):
        return v, None, "unidade não informada na fonte"
    return v, un, f"{un}: sem conversão para t (sem densidade)"


def confere_linhas(sid, df, sep):
    raw = open(arquivo(FONTES[sid]['arquivo']), "rb").read().decode("cp1252", errors="replace")
    n = sum(1 for _ in csv.reader(io.StringIO(raw), delimiter=sep)) - 1
    if n != len(df):
        raise SystemExit(f"{sid}: {n} registros no arquivo x {len(df)} lidos -- source_linha deixaria de apontar a linha certa")


# ---------------------------------------------------------------------------
# 1) AMB -- produção bruta e beneficiada (todas as UFs)
# ---------------------------------------------------------------------------
PB_MET = [("Quantidade Produção - Minério ROM (t)", "t", "producao_rom", "ROM"),
          ("Quantidade Contido", "Unidade de Medida - Contido", "contido_rom", "conteudo_mineral"),
          ("Quantidade Venda (t)", "t", "venda_rom", "ROM"),
          ("Valor Venda (R$)", "R$", "valor_venda_rom", None),
          ("Quantidade Transformação / Consumo / Utilização (t)", "t", "consumo_mina_rom", "ROM"),
          ("Valor Transformação / Consumo / Utilização nesta mina (R$)", "R$", "valor_consumo_mina_rom", None),
          ("Quantidade Transferência para Transformação / Utilização / Consumo (t)", "t", "transferencia_rom", "ROM"),
          ("Valor Transferência para Transformação / Utilização / Consumo (R$)", "R$", "valor_transferencia_rom", None)]
PF_MET = [("Quantidade Produção", "Unidade de Medida - Produção", "producao_beneficiada", "beneficiada"),
          ("Quantidade Contido", "Unidade de Medida - Contido", "contido_beneficiada", "conteudo_mineral"),
          ("Quantidade Venda", "Unidade de Medida - Venda", "venda_beneficiada", "beneficiada"),
          ("Valor Venda (R$)", "R$", "valor_venda_beneficiada", None),
          ("Quantidade Consumo/Utilização na Usina", "Unidade de Medida - Consumo/Utilização na Usina", "consumo_usina_beneficiada", "beneficiada"),
          ("Valor Consumo / Utilização na Usina (R$)", "R$", "valor_consumo_usina_beneficiada", None),
          ("Quantidade Transferência para Transformação / Utilização / Consumo",
           "Unidade de Medida - Transferência para Transformação / Utilização / Consumo", "transferencia_beneficiada", "beneficiada"),
          ("Valor Transferência para Transformação / Utilização / Consumo (R$)", "R$", "valor_transferencia_beneficiada", None)]

anos_amb, IND = set(), {}  # IND: (fonte, linha) -> Indicação Contido, para as notas de produção repetida
for sid, METS in (("SRC_ANM_PROD_BRUTA", PB_MET), ("SRC_ANM_PROD_BENEF", PF_MET)):
    df = read_csv(arquivo(FONTES[sid]['arquivo']))
    confere_linhas(sid, df, ",")
    numericas = {c for c in df.columns if re.match(r"^(Quantidade|Valor)", c.strip())}
    faltam = {m[0] for m in METS} - set(df.columns)
    sobram = numericas - {m[0] for m in METS}
    if faltam or sobram:
        raise SystemExit(f"{sid}: colunas esperadas ausentes {faltam}; colunas numéricas sem métrica {sobram}")
    for idx, r in df.iterrows():
        k = ANM_CATEGORY_TO_KEY[r["Substância Mineral"]]
        ano, uf = int(r["Ano base"]), str(r["UF"]).strip()
        anos_amb.add(ano)
        ind = str(r.get("Indicação Contido", "")).strip()
        IND[(sid, idx + 2)] = ind
        for col, un_spec, met, basis in METS:
            bruto = str(r[col]).strip()
            if not bruto:
                fora["vazias"] += 1
                continue
            un = str(r[un_spec]).strip() if un_spec in df.columns else un_spec
            v = num(bruto)
            if col == "Quantidade Contido" and un == "-" and v == 0:
                fora["contido_nao_se_aplica"] += 1
                continue
            vt, upad, trat = unidade_padrao(v, un)
            notas = [f"contido expresso como {ind}"] if (col == "Quantidade Contido" and ind) else []
            if v is None:
                notas.append("valor não numérico na fonte")
            nova(sid, idx + 2, col, met, ano, str(ano), uf, k, bruto, un, trat, vt, upad, basis if un_spec != "R$" else None,
                 str(r["Substância Mineral"]).strip(), status="valido" if v is not None else "valor_nao_numerico", notas=notas)
    print(f"{sid}: {len(df)} linhas da fonte -> {sum(1 for x in linhas if x[IX['source_id']] == sid)} medidas")

# Produção repetida: o AMB repete a MESMA tonelagem em linhas diferentes da mesma UF e ano -- co-produtos de uma mina
# (Bário + Nióbio em GO 2023; Chumbo + Zinco; Ouro + Prata) ou o mesmo mineral separado por teor contido
# (Columbita-Tantalita Nb2O5 / Ta2O5 em AM). Cada linha está certa sozinha; somar entre elas conta a tonelagem duas vezes.
# Não há linha 100% duplicada na fonte. Regra do guia: registrar, não corrigir -> status + nota apontando as outras linhas.
grupos_rep = defaultdict(list)
for i, row in enumerate(linhas):
    if row[IX["metrica"]] in ("producao_rom", "producao_beneficiada") and (row[IX["valor_tratado"]] or 0) > 0:
        # a unidade entra na chave: "43" kg de prata e "43" t de titânio (GO 2025) é coincidência, não repetição
        grupos_rep[(row[IX["source_id"]], row[IX["uf"]], row[IX["year"]], row[IX["metrica"]], row[IX["valor_original"]], row[IX["unidade_original"]])].append(i)


def _rotulo(sid, j):
    ind = IND.get((sid, linhas[j][IX["source_linha"]]))
    return f"linha {linhas[j][IX['source_linha']]} ({linhas[j][IX['mineral_nome_original']]}" + (f", contido {ind})" if ind else ")")


rep = dict(linhas=0, dentro_do_mineral_t=0.0, entre_minerais_t=0.0, go=[])
for (sid, uf, ano, met, bruto, un_rep), idxs in grupos_rep.items():
    if len(idxs) < 2:
        continue
    extra = linhas[idxs[0]][IX["valor_tratado"]] * (len(idxs) - 1)
    rep["dentro_do_mineral_t" if len({linhas[i][IX["mineral_id"]] for i in idxs}) == 1 else "entre_minerais_t"] += extra
    if uf == "GO":
        rep["go"].append(f"{met} {ano}: {bruto} {un_rep} em " + " e ".join(_rotulo(sid, i) for i in idxs))
    for i in idxs:
        row = linhas[i]
        nota = "mesma tonelagem da " + ", ".join(_rotulo(sid, j) for j in idxs if j != i) + " na mesma UF e ano (co-produto, teor ou mesma declaração em duas categorias): não somar entre essas linhas"
        row[IX["notas"]] = (row[IX["notas"]] + "; " if row[IX["notas"]] else "") + nota
        row[IX["status_validacao"]] = "alerta_producao_repetida"
        rep["linhas"] += 1
print(f"Produção repetida no AMB: {rep['linhas']} linhas sinalizadas; tonelagem contada a mais numa soma: {rep['dentro_do_mineral_t']:,.0f} t dentro do "
      f"mesmo mineral (infla o total do mineral na 09) e {rep['entre_minerais_t']:,.0f} t entre minerais. GO: {rep['go']}")

# ---------------------------------------------------------------------------
# 2) CFEM (Goiás) -- quantidade comercializada e valor recolhido, linha a linha
# ---------------------------------------------------------------------------
confere_linhas("SRC_ANM_CFEM", cfem, ";")
LB1 = {l["idx"]: l for l in json.load(open(f"{TMP}/_cfem_linhas.json", encoding="utf-8"))}
ALERTAS = {(a["mineral_key"], a["year"], a["processo_anm"]) for a in json.load(open(f"{TMP}/_cfem_alertas_processo.json", encoding="utf-8"))}
OPS = {o["processo_anm"] for o in json.load(open(f"{TMP}/_dim_operacoes.json", encoding="utf-8"))}
desalinhadas = [i for i, l in LB1.items() if str(cfem.at[i, "Substância"]) != str(l["subst"])]
if desalinhadas:
    raise SystemExit(f"CFEM: {len(desalinhadas)} linhas da Base 1 não batem com o arquivo pela posição (ex.: {desalinhadas[:5]})")

for idx, r in cfem.iterrows():
    l = LB1.get(idx)
    k = l["k"] if l else None
    ano = int(r["_ano"]) if pd.notna(r["_ano"]) else None
    mes = str(r["Mês"]).strip()
    periodo = f"{ano}-{int(mes):02d}" if (ano and mes.isdigit()) else (str(ano) if ano else None)
    proc = r["_proc"]
    cid = proc2company.get(proc) or proc2company_cfem.get(proc) or "COM_NAO_IDENTIFICADO"
    ope = "OPE_" + proc.replace("/", "_") if proc in OPS else None
    cod = str(r["CodigoMunicipio"]).split(".")[0].strip()
    mun = cod if cod in MUN_NOME else None
    subst = str(r["Substância"]).strip()
    notas = []
    if l and l["regra"] == "uso_declarado":
        notas.append(f"rocha: categoria pelo uso '{l['uso']}' ({l['origem_uso']}) — 01c")
    elif l and l["regra"] == "uso_majoritario_da_rocha_em_GO":
        notas.append(f"rocha sem uso informativo no processo: uso mais comum da rocha em GO ('{USO_PADRAO.get(norm(subst), '')}') — 01c")
    elif l and l["regra"] == "sem_uso_informativo_mapeamento_por_tipo_de_rocha":
        notas.append("rocha sem uso informativo: categoria pelo tipo de rocha — 01c")
    if cid == "COM_NAO_IDENTIFICADO":
        notas.append("processo sem titular nas bases de título (COM_NAO_IDENTIFICADO)")
    elif proc not in proc2company:
        notas.append("processo sem titular nas bases de título: empresa pela raiz do CNPJ pagador no CFEM")
    if ope is None:
        notas.append("processo sem poligonal no SIGMINE de GO (fora da 03)")
    if mun is None:
        notas.append(f"CodigoMunicipio {cod} fora da malha de GO")
    if k is None:
        notas.append("substância sem mineral atribuído")
    comum = dict(company=cid, operation=ope, processo=proc, municipio=mun)  # processo: rastreia também quem não tem poligonal (fora da 03)
    uf = str(r["UF"]).strip()

    bruto = str(r["QuantidadeComercializada"]).strip()
    un = str(r["UnidadeDeMedida"]).strip()
    if not bruto:
        fora["vazias"] += 1
    else:
        u = un.lower()
        cient = bool(re.search(r"[eE][+-]?\d+$", bruto))
        v = None if cient else num(bruto)
        massa = u in PARA_T
        conv = None if v is None else (v * PARA_T[u] if massa else v)
        if l and not ((l["conv"] is None and conv in (None, 0.0)) or
                      (l["conv"] is not None and conv is not None and abs(l["conv"] - conv) <= 1e-9 * max(1.0, abs(conv)))):
            raise SystemExit(f"CFEM linha {idx + 2}: quantidade convertida diverge da Base 1 ({l['conv']} x {conv})")
        excl = bool(l and l["excluida"]) or cient
        if excl:
            trat = f"{(l or {}).get('motivo') or 'quantidade em notação científica (valor corrompido na exportação)'} — fora da soma de quantidade (09b)"
        elif v is None:
            trat = "valor não numérico na fonte"
        elif massa and u != "t":
            trat = f"{u} → t (× {FATOR_TXT[u]})"
        elif not massa:
            trat = f"{un}: sem conversão para t (sem densidade), fora da soma em t"
        else:
            trat = None
        status = ("quantidade_excluida_da_soma_09b" if excl else "valor_nao_numerico" if v is None
                  else "alerta_processo_09c" if (l and (k, ano, l["proc_canon"]) in ALERTAS) else "valido")
        nova("SRC_ANM_CFEM", idx + 2, "QuantidadeComercializada", "quantidade_comercializada_cfem", ano, periodo, uf, k, bruto, un, trat,
             None if excl else conv, "t" if massa else (un or None), None, subst, status=status, notas=notas, **comum)

    bruto = str(r["ValorRecolhido"]).strip()
    if not bruto:
        fora["vazias"] += 1
    else:
        v = num(bruto)
        nova("SRC_ANM_CFEM", idx + 2, "ValorRecolhido", "cfem_recolhido", ano, periodo, uf, k, bruto, "R$", None if v is not None else "valor não numérico na fonte",
             v, "BRL", None, subst, status="valido" if v is not None else "valor_nao_numerico", notas=notas, **comum)
print(f"SRC_ANM_CFEM: {len(cfem)} linhas da fonte -> {sum(1 for x in linhas if x[IX['source_id']] == 'SRC_ANM_CFEM')} medidas")

for i, row in enumerate(linhas, start=1):
    row[IX["fato_id"]] = f"FATO_{i:06d}"

# ---------------------------------------------------------------------------
# 3) conciliação (falha rápida): 09, 10 e 11 têm de sair da soma da 08
# ---------------------------------------------------------------------------
ID2KEY = {v: k for k, v in KEY2ID.items()}
M09 = {"producao_rom": "producao_rom_t", "producao_beneficiada": "producao_beneficiada_t", "valor_venda_beneficiada": "valor_venda_beneficiada_brl",
       "cfem_recolhido": "cfem_recolhido_brl", "quantidade_comercializada_cfem": "cfem_qtd_comercializada_t"}
i09, i10, i11 = defaultdict(float), defaultdict(float), defaultdict(float)
for row in linhas:
    vt, met, ano = row[IX["valor_tratado"]], row[IX["metrica"]], row[IX["year"]]
    if vt is None or ano is None:
        continue
    k = ID2KEY.get(row[IX["mineral_id"]])
    if met == "cfem_recolhido":
        if row[IX["municipality_id"]]:
            i10[(row[IX["municipality_id"]], ano)] += vt
        if k:
            i11[(row[IX["company_id"]], k, ano)] += vt
    campo = M09.get(met)
    if not campo or not k or (campo == "cfem_qtd_comercializada_t" and row[IX["unidade_padrao"]] != "t"):
        continue
    # a 09 só tem GO e BR (= soma de todas as UFs); as outras UFs ficam na 08 sem linha própria na 09
    for uf in ({row[IX["uf"]]} if row[IX["source_id"]] == "SRC_ANM_CFEM" else {row[IX["uf"]], "BR"}) & {"GO", "BR"}:
        i09[(uf, k, ano, campo)] += vt


def confere(esperado, rows, chave, campos):
    difs, vistos = [], set()
    for r in rows:
        if r.get("ano") is None:
            continue
        for campo, v in campos(r).items():
            kk = chave(r) + ((campo,) if campo else ())
            vistos.add(kk)
            if abs((v or 0.0) - esperado.get(kk, 0.0)) > 1e-6 * max(1.0, abs(v or 0.0)):
                difs.append((kk, v, esperado.get(kk)))
    return difs + [(kk, None, v) for kk, v in esperado.items() if kk not in vistos and abs(v) > 1e-9]


b1 = json.load(open(f"{TMP}/_base1_rows.json", encoding="utf-8"))
b2 = json.load(open(f"{TMP}/_base2_rows.json", encoding="utf-8"))
b3 = json.load(open(f"{TMP}/_base3_rows.json", encoding="utf-8"))
d09 = confere(i09, b1, lambda r: (r["uf"], r["mineral_id"], r["ano"]), lambda r: {
    "producao_rom_t": r["producao_rom_t"], "valor_venda_beneficiada_brl": r["valor_venda_beneficiada_brl"],
    "producao_beneficiada_t": (r["producao_beneficiada"] * PARA_T[r["unidade_beneficiada"].lower()]) if r["producao_beneficiada"] is not None else None,
    "cfem_recolhido_brl": r["cfem_recolhido_brl"], "cfem_qtd_comercializada_t": r["cfem_qtd_comercializada_t"]})
d10 = confere(i10, b2, lambda r: (str(r["municipality_id"]), r["ano"]), lambda r: {None: r["cfem_recolhido_brl"]})
d11 = confere(i11, b3, lambda r: (r["company_id"], r["mineral_id"], r["ano"]), lambda r: {None: r["cfem_recolhido_brl"]})
print(f"Conciliação 08 -> 09: {len(d09)} divergências; -> 10: {len(d10)}; -> 11: {len(d11)}")
for d in (d09 + d10 + d11)[:12]:
    print("   ", d)

# ---------------------------------------------------------------------------
# 4) saída
# ---------------------------------------------------------------------------
cf_periodos = sorted(x[IX["periodo_referencia"]] for x in linhas if x[IX["source_id"]] == "SRC_ANM_CFEM" and x[IX["periodo_referencia"]])
resumo = dict(
    linhas=len(linhas), linhas_por_fonte=Counter(x[IX["source_id"]] for x in linhas), linhas_por_metrica=Counter(x[IX["metrica"]] for x in linhas),
    status_validacao=Counter(x[IX["status_validacao"]] for x in linhas), celulas_fora=dict(vazias=fora["vazias"], contido_nao_se_aplica=fora["contido_nao_se_aplica"]),
    periodo_amb=f"{min(anos_amb)}–{max(anos_amb)}", periodo_cfem=f"{cf_periodos[0]} a {cf_periodos[-1]}",
    conciliacao=dict(d09=len(d09), d10=len(d10), d11=len(d11)), producao_repetida=rep)
with open(f"{TMP}/_fato_08.json", "w", encoding="utf-8") as f:
    json.dump(dict(colunas=COLS, linhas=linhas), f, ensure_ascii=False, separators=(",", ":"))
with open(f"{TMP}/_fato_08_resumo.json", "w", encoding="utf-8") as f:
    json.dump(resumo, f, ensure_ascii=False, indent=1)
print(json.dumps({k: v for k, v in resumo.items() if k != "linhas_por_metrica"}, ensure_ascii=False))
print("métricas:", dict(resumo["linhas_por_metrica"]))
if d09 or d10 or d11:
    raise SystemExit("A 08 não concilia com 09/10/11 -- não gravar a aba antes de explicar as divergências.")
