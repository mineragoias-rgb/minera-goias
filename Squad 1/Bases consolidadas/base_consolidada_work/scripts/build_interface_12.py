# -*- coding: utf-8 -*-
"""Aba 12 -- entrega Squad 1 -> Squad 2 (Contrato de Dados: mineral_id, company_id, operation_id, project_id,
municipality_id, year, production_t, latitude, longitude, source_id + production_basis), em dois niveis:

  estado   -- producao OBSERVADA de Goias no AMB por mineral, ano (2010-2025) e base (ROM, beneficiada) = soma da 08;
  operacao -- abertura ESTIMADA desse total em 2022-2025, rateada pela participacao de cada processo na CFEM (R$)
              do mineral no ano. A soma das operacoes e igual ao total do estado (os niveis nao se somam).

Pente fino que definiu a regra (diagnóstico de 12/09/2026):
  - a ANM não publica produção por operação; a CFEM é a única medida por processo e cobre 99,6% das t de GO
    em 2022-2024 e 94,1% em 2025 (sem CFEM: areias industriais, feldspato, talco, bário 2025...);
  - rateio pela QUANTIDADE em t da CFEM foi descartado como regra principal: em 28 processo-mineral-anos a
    participação por t difere da por R$ em mais de 0,30, quase sempre por erro de quantidade já documentado
    (09b/09c: ouro 860677/2019 com 78% das t e 0,4% do R$; brita 860555/2014); a quantidade também some quando
    a CFEM vem em m3. Fica como alternativa de sensibilidade (production_t_rateio_por_t);
  - a CFEM dos subitens de Calcário (calcítico, dolomítico, industrial) não tem produção própria no AMB:
    entra em Calcário (R$ 4-4,1 mi/ano); nenhuma CFEM por processo é zero ou negativa;
  - 10,2% do R$ vem de processos sem poligonal no SIGMINE (fora da 03): entram sem operation_id e coordenadas.
O guia (Squad 2) proíbe intensidade operação-específica com numerador e denominador incompatíveis: a linha
estimada avisa que não é produção observada da operação.
"""
import glob
import json
import os
import sys
from collections import Counter, defaultdict

import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
from caminhos import BASE, TMP, arquivo, data_acesso  # caminhos relativos ao projeto — ver caminhos.py

FONTES = {  # url_recurso e arquivos iguais aos da 07 (a governança confere linha a linha)
    "SRC_ANM_PROD_BRUTA": ("https://dadosabertos.anm.gov.br/AMB/Producao_Bruta.csv", ["dados/ANM/producao_amb_ral/Producao_Bruta.csv"]),
    "SRC_ANM_PROD_BENEF": ("https://dadosabertos.anm.gov.br/AMB/Producao_Beneficiada.csv", ["dados/ANM/producao_amb_ral/Producao_Beneficiada.csv"]),
    "SRC_ANM_CFEM": ("https://dadosabertos.anm.gov.br/CFEM/CFEM_Arrecadacao_2022_2026.csv", ["dados/ANM/cfem/CFEM_Arrecadacao_2022_2026_GO.csv"]),
    "SRC_ANM_CADASTRO": ("https://dadosabertos.anm.gov.br/SCM/<arquivo>.csv — 13 arquivos (Alvara_de_Pesquisa, Cessoes_de_Direitos, Guia_de_Utilizacao_Autorizada, "
                         "Licenciamento, PLG, Portaria_de_Lavra, …)", ["dados/ANM/cadastro_mineiro/*.csv"]),
    "SRC_ANM_SIGMINE": ("https://dadosabertos.anm.gov.br/SIGMINE/PROCESSOS_MINERARIOS/GO.zip", ["dados/ANM/sigmine/GO.zip"]),
    "SRC_IBGE_MALHA_2025": ("https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/malhas_municipais/municipio_2025/UFs/GO/GO_Municipios_2025.zip",
                            ["dados/IBGE/GO_Municipios_2025.zip"]),
}
DATA = {sid: data_acesso(pads)
        for sid, (_, pads) in FONTES.items()}  # mesmo cálculo de data_arquivo_local da 07
RESPONSAVEL = "Squad 1 / Estudante 1 — checagens automáticas do pipeline (ver 14b)"
METODO = ("Rateio da produção observada do AMB de Goiás (mesmo mineral, ano e base) pela participação do processo na CFEM recolhida em R$ no mineral e ano: "
          "production_t = total do AMB × participacao_cfem_brl. A CFEM dos subitens de Calcário entra em Calcário. Premissa: a mesma relação R$/t entre as "
          "operações do mineral (preço, teor e mix de produto iguais); a quantidade em t da CFEM fica só como sensibilidade (production_t_rateio_por_t) porque "
          "carrega os erros documentados na 09b/09c. É estimativa: não usar como produção observada da operação nem como denominador observado de intensidade "
          "energética operação-específica.")
COLS = ["mineral_id", "mineral_name", "company_id", "operation_id", "project_id", "municipality_id", "year", "production_t", "production_basis",
        "latitude", "longitude", "source_id", "nivel_agregacao", "processo_anm", "valor_observado_estimado", "metodo_estimacao",
        "erro_estimativa_intervalo", "participacao_cfem_brl", "cfem_brl_operacao", "cfem_brl_mineral_ano", "production_t_rateio_por_t",
        "status_validacao", "responsavel_validacao", "periodo_referencia", "tipo_fonte", "source_url", "data_acesso", "fato_ids", "observacao"]
IX = {c: i for i, c in enumerate(COLS)}
BASE_DE = {"producao_rom": ("ROM", "SRC_ANM_PROD_BRUTA"), "producao_beneficiada": ("beneficiada", "SRC_ANM_PROD_BENEF")}


def br(x, casas=0):
    return f"{x:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def fontes(ids):
    return dict(source_id="; ".join(ids), source_url="; ".join(FONTES[i][0] for i in ids), data_acesso="; ".join(DATA[i] for i in ids))


md = json.load(open(f"{TMP}/_min_def.json", encoding="utf-8"))
_ordem = sorted(md.items(), key=lambda kv: (kv[1][1], kv[1][0]))
KEY2ID = {k: f"MIN_{i + 1:03d}" for i, (k, _) in enumerate(_ordem)}
NOME = {KEY2ID[k]: v[0] for k, v in md.items()}
PAI = {KEY2ID[k]: KEY2ID[v[2]] for k, v in md.items() if v[2]}  # subitem -> categoria do AMB (só a família Calcário hoje)
fato = json.load(open(f"{TMP}/_fato_08.json", encoding="utf-8"))
C = {c: i for i, c in enumerate(fato["colunas"])}
OPS = {o["processo_anm"]: o for o in json.load(open(f"{TMP}/_dim_operacoes.json", encoding="utf-8"))}
print(f"08: {len(fato['linhas'])} linhas; 03: {len(OPS)} processos; subitens com categoria-pai: {sorted(NOME[m] for m in PAI)}")

# ---------------------------------------------------------------------------
# 1) somas da 08: produção de GO (nível estado) e CFEM por processo (chave do rateio)
# ---------------------------------------------------------------------------
tot, fids, flags = defaultdict(float), defaultdict(list), defaultdict(set)
cf_rs, cf_t, tot_rs, tot_t = defaultdict(float), defaultdict(float), defaultdict(float), defaultdict(float)
cf_emp, cf_mun, cf_sub, cf_alerta = defaultdict(Counter), defaultdict(Counter), defaultdict(set), set()
pelo_cnpj = set()  # processos sem titular no Cadastro cuja empresa veio da raiz do CNPJ pagador no CFEM (notas da 08)
for r in fato["linhas"]:
    if r[C["uf"]] != "GO":
        continue
    met, vt = r[C["metrica"]], r[C["valor_tratado"]]
    if met in BASE_DE:
        if vt is None:
            continue
        k = (r[C["mineral_id"]], r[C["year"]], BASE_DE[met][0])
        tot[k] += vt
        fids[k].append(r[C["fato_id"]])
        if r[C["status_validacao"]] == "alerta_producao_repetida":
            flags[k].add(r[C["notas"]])
    elif r[C["source_id"]] == "SRC_ANM_CFEM" and r[C["mineral_id"]]:
        mid = r[C["mineral_id"]]
        cat = PAI.get(mid, mid)
        kp = (cat, r[C["year"]], r[C["processo_anm"]])
        if met == "cfem_recolhido" and vt is not None:
            cf_rs[kp] += vt
            tot_rs[kp[:2]] += vt
            cf_emp[kp][r[C["company_id"]]] += vt
            if "raiz do CNPJ pagador" in (r[C["notas"]] or ""):
                pelo_cnpj.add(r[C["processo_anm"]])
            if r[C["municipality_id"]]:
                cf_mun[kp][r[C["municipality_id"]]] += vt
            if mid != cat:
                cf_sub[kp].add(NOME[mid])
        elif met == "quantidade_comercializada_cfem":
            if vt is not None and r[C["unidade_padrao"]] == "t":
                cf_t[kp] += vt
                tot_t[kp[:2]] += vt
            if r[C["status_validacao"]] == "alerta_processo_09c":
                cf_alerta.add(kp)
procs_de = defaultdict(list)
for (cat, ano, proc), v in cf_rs.items():
    procs_de[(cat, ano)].append((proc, v))
negativos = [kp for kp, v in cf_rs.items() if v <= 0]
if negativos:
    raise SystemExit(f"CFEM por processo zero ou negativa ({len(negativos)}): a participação no rateio deixaria de ser uma fração -- revisar a regra")
ANO_CFEM_INI = min(a for _, a in tot_rs)

# ---------------------------------------------------------------------------
# 2) linhas: estado (observado) e, logo abaixo, a abertura por operação (estimada)
# ---------------------------------------------------------------------------
linhas, sem_abertura = [], []
cob = defaultdict(lambda: [0.0, 0.0])
t_est = t_ope = 0.0


def nova(**kw):
    row = [None] * len(COLS)
    for c, v in kw.items():
        row[IX[c]] = v
    linhas.append(row)


for k in sorted(tot, key=lambda kk: (NOME[kk[0]], kk[1], kk[2])):
    mid, ano, base = k
    P = tot[k]
    src_amb = BASE_DE["producao_rom" if base == "ROM" else "producao_beneficiada"][1]
    abre = P > 0 and tot_rs.get((mid, ano), 0.0) > 0 and ano <= 2025
    obs = []
    if P == 0:
        obs.append("produção zero declarada no AMB")
    if ano < ANO_CFEM_INI:
        obs.append(f"antes de {ANO_CFEM_INI} não há CFEM na base para abrir por operação")
    elif abre:
        obs.append("total observado; a abertura estimada por operação está nas linhas de nível operação logo abaixo — não somar os dois níveis")
    elif P > 0:
        obs.append("sem CFEM do mineral no ano em Goiás: produção sem abertura por operação")
        sem_abertura.append(f"{NOME[mid]} {ano} ({base})")
    obs += sorted(flags[k])
    if 2022 <= ano <= 2025:
        cob[ano][1] += P
        cob[ano][0] += P if abre else 0.0
    nova(mineral_id=mid, mineral_name=NOME[mid], year=ano, production_t=P, production_basis=base, nivel_agregacao="estado",
         valor_observado_estimado="observado", status_validacao="alerta_producao_repetida" if flags[k] else "valido",
         responsavel_validacao=RESPONSAVEL, periodo_referencia=str(ano), tipo_fonte="oficial", fato_ids="; ".join(fids[k]),
         observacao="; ".join(obs) or None, **fontes([src_amb]))
    if not abre:
        continue
    R, T = tot_rs[(mid, ano)], tot_t.get((mid, ano), 0.0)
    soma = 0.0
    for proc, v in sorted(procs_de[(mid, ano)], key=lambda x: -x[1]):
        kp = (mid, ano, proc)
        s = v / R
        est = P * s
        alt = (P * cf_t.get(kp, 0.0) / T) if T > 0 else None
        o = OPS.get(proc)
        comp = cf_emp[kp].most_common(1)[0][0] if cf_emp[kp] else None
        mun = o["municipality_id"] if (o and o["municipality_id"]) else (cf_mun[kp].most_common(1)[0][0] if cf_mun[kp] else None)
        ids = [src_amb, "SRC_ANM_CFEM"] + (["SRC_ANM_CADASTRO"] if comp and comp != "COM_NAO_IDENTIFICADO" and proc not in pelo_cnpj else []) \
            + (["SRC_ANM_SIGMINE", "SRC_IBGE_MALHA_2025"] if o else [])
        faixa = (f"entre {br(min(est, alt), 3)} e {br(max(est, alt), 3)} t (rateio por R$ × rateio pela quantidade em t da CFEM)" if alt is not None
                 else "sem alternativa: a CFEM do mineral no ano não tem quantidade em t")
        obs = []
        if cf_sub[kp]:
            obs.append("CFEM declarada como " + ", ".join(sorted(cf_sub[kp])) + f" (subitem de {NOME[mid]})")
        if not o:
            obs.append("processo sem poligonal no SIGMINE de GO: sem operation_id e coordenadas; município da CFEM")
        if comp == "COM_NAO_IDENTIFICADO":
            obs.append("titular não identificado nas bases de título")
        elif proc in pelo_cnpj:
            obs.append("processo sem titular nas bases de título: empresa pela raiz do CNPJ pagador no CFEM")
        if kp in cf_alerta:
            obs.append("processo na 09c (quantidade da CFEM implausível frente ao AMB): o rateio por R$ não usa a quantidade, mas a alternativa em t fica distorcida")
        if flags[k]:
            obs.append("o total do estado tem produção repetida entre linhas do AMB (ver linha de nível estado)")
        nova(mineral_id=mid, mineral_name=NOME[mid], company_id=comp, operation_id=o["operation_id"] if o else None, municipality_id=mun, year=ano,
             production_t=est, production_basis=base, latitude=o["latitude"] if o else None, longitude=o["longitude"] if o else None,
             nivel_agregacao="operacao", processo_anm=proc, valor_observado_estimado="estimado", metodo_estimacao=METODO, erro_estimativa_intervalo=faixa,
             participacao_cfem_brl=s, cfem_brl_operacao=v, cfem_brl_mineral_ano=R, production_t_rateio_por_t=alt,
             status_validacao="estimativa_com_alerta_09c" if kp in cf_alerta else "estimativa_conferida_no_total", responsavel_validacao=RESPONSAVEL,
             periodo_referencia=str(ano), tipo_fonte="oficial", fato_ids="; ".join(fids[k]), observacao="; ".join(obs) or None, **fontes(ids))
        soma += est
        t_est += est
        t_ope += est if o else 0.0
    if abs(soma - P) > 1e-6 * max(1.0, P):
        raise SystemExit(f"{NOME[mid]} {ano} {base}: operações somam {soma} e o estado tem {P}")

# ---------------------------------------------------------------------------
# 3) saída
# ---------------------------------------------------------------------------
ops_rows = [x for x in linhas if x[IX["nivel_agregacao"]] == "operacao"]
tem_prod = {(m, a) for (m, a, _), v in tot.items() if v > 0}
resumo = dict(
    linhas=len(linhas), estado=len(linhas) - len(ops_rows), operacao=len(ops_rows), processos=len({x[IX["processo_anm"]] for x in ops_rows}),
    cobertura_por_ano={str(a): 100 * v[0] / v[1] for a, v in sorted(cob.items()) if v[1]},
    pct_prod_com_operation_id=100 * t_ope / t_est if t_est else 0.0, pct_prod_com_coordenadas=100 * t_ope / t_est if t_est else 0.0,
    sem_abertura=sem_abertura,
    cfem_sem_producao_amb=sorted({f"{NOME[m]} {a}" for (m, a) in tot_rs if a <= 2025 and (m, a) not in tem_prod}),
    status=Counter(x[IX["status_validacao"]] for x in linhas))
with open(f"{TMP}/_interface_12.json", "w", encoding="utf-8") as f:
    json.dump(dict(colunas=COLS, linhas=linhas), f, ensure_ascii=False, separators=(",", ":"))
with open(f"{TMP}/_interface_12_resumo.json", "w", encoding="utf-8") as f:
    json.dump(resumo, f, ensure_ascii=False, indent=1)
print(json.dumps(resumo, ensure_ascii=False))
