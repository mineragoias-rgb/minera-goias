# -*- coding: utf-8 -*-
"""Pacote de preços e custo de energia da aba Preços do painel (data/precos/precos.json).

    python scripts/build_precos_energia.py                 # usa a raiz do repositório onde está este script
    python scripts/build_precos_energia.py --repo <clone>

Duas naturezas de dado, nunca misturadas no mesmo campo:

- **observado** — consumo das parcelas de carga da CCEE em Goiás (`Squad 1/dados/CCEE/parcela_carga_consumo_*_GO.csv`),
  com o recorte mineral feito pela raiz do CNPJ que aparece em `02_dim_empresas` da base consolidada do Squad 1 (mesmo
  vínculo do Panorama), e não pelo campo autodeclarado `RAMO_ATIVIDADE`, que fica como recorte alternativo mais largo;
- **premissa** — os parâmetros de preço e de crescimento da demanda em `Squad 2/precos/premissas/`. Nenhum preço
  observado existe no repositório: o módulo projeta a partir de premissa declarada e marcada como tal em todas as saídas.

O preço de um consumidor livre é a soma de três componentes (energia, uso de rede, encargos e perdas), em R$ reais do ano
base. O componente de energia reverte a um nível de longo prazo por cenário; os regulados seguem tendência real. O custo é
demanda × preço, com o cenário de preço e o de demanda cruzados — são hipóteses independentes.
"""
import argparse
import csv
import glob
import json
import math
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

import openpyxl

sys.stdout.reconfigure(encoding="utf-8")
ap = argparse.ArgumentParser(description="Gera data/precos/precos.json a partir das premissas do Squad 2 e da CCEE no repositório.")
ap.add_argument("--repo", default=str(Path(__file__).resolve().parents[1]), help="raiz do clone (padrão: a deste script)")
ap.add_argument("--saida", help="padrão: <repo>/data/precos/precos.json")
args = ap.parse_args()
REPO = Path(args.repo)
SAIDA = Path(args.saida) if args.saida else REPO / "data" / "precos" / "precos.json"
S1 = REPO / "Squad 1"
PREMISSAS = REPO / "Squad 2" / "precos" / "premissas"
CSV_SAIDAS = REPO / "Squad 2" / "precos" / "saidas"

CENARIOS = ["conservador", "referencia", "expansao"]
COMPONENTES = ["energia", "uso_de_rede", "encargos_e_perdas"]
ANO_INICIO, ANO_FIM = 2027, 2040
RAMOS_MINERAIS = ["EXTRAÇÃO DE MINERAIS METÁLICOS", "MINERAIS NÃO-METÁLICOS", "METALURGIA E PRODUTOS DE METAL"]
CPF = re.compile(r"(?<!\d)(\d{3})\.?(\d{3})\.?(\d{3})-?(\d{2})(?!\d)")


def mascarar_cpf(nome):
    """Mesma máscara da base consolidada e do Panorama: CPF dentro de um nome vira ***456789**."""
    return CPF.sub(lambda m: "***" + "".join(m.groups())[3:9] + "**", str(nome))


def norm(s):
    return unicodedata.normalize("NFD", str(s or "")).encode("ascii", "ignore").decode().upper().strip()


def num(s):
    s = str(s or "").strip()
    return float(s) if s else 0.0


def ler_csv(caminho, delimitador=","):
    with open(caminho, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f, delimiter=delimitador))


def opcional(valor):
    """Campo de premissa que pode vir vazio: ausência fica ausência, não zero."""
    s = str(valor or "").strip()
    return float(s) if s else None


# ------------------------------------------------------------------------------------------------------------- premissas
pre_preco = ler_csv(PREMISSAS / "premissas_preco_energia.csv")
pre_demanda = ler_csv(PREMISSAS / "premissas_demanda_energia.csv")
fontes = ler_csv(PREMISSAS / "fontes_preco_energia.csv")

PARAM = {}
for r in pre_preco:
    comp, cen = r["componente"], r["cenario"]
    assert comp in COMPONENTES, f"componente fora do contrato: {comp}"
    assert cen in CENARIOS, f"cenário fora do contrato: {cen}"
    assert r["data_nature"] != "observado", "nenhuma linha de premissa pode se declarar observada"
    PARAM[(comp, cen)] = {
        "ano_base": int(r["ano_base"]),
        "p0": float(r["preco_base_brl_mwh"]),
        "min": opcional(r["faixa_min_brl_mwh"]),
        "max": opcional(r["faixa_max_brl_mwh"]),
        "longo_prazo": opcional(r["nivel_longo_prazo_brl_mwh"]),
        "meia_vida": opcional(r["meia_vida_anos"]),
        "tendencia": float(r["tendencia_real_aa"]),
        "metodo": r["metodo"],
        "data_nature": r["data_nature"],
        "source_id": r["source_id"],
        "observacao": r["observacao"],
    }
faltando = [(c, s) for c in COMPONENTES for s in CENARIOS if (c, s) not in PARAM]
assert not faltando, f"premissa de preço incompleta: {faltando}"

CRESC = {}
for r in pre_demanda:
    assert r["cenario"] in CENARIOS, f"cenário fora do contrato: {r['cenario']}"
    assert r["data_nature"] != "observado", "nenhuma linha de premissa pode se declarar observada"
    CRESC[r["cenario"]] = {"taxa": float(r["crescimento_real_aa"]), "data_nature": r["data_nature"],
                           "source_id": r["source_id"], "observacao": r["observacao"]}
assert set(CRESC) == set(CENARIOS), "premissa de demanda incompleta"

ANO_BASE = {p["ano_base"] for p in PARAM.values()}
assert len(ANO_BASE) == 1, f"todos os componentes devem partir do mesmo ano base: {sorted(ANO_BASE)}"
ANO_BASE = ANO_BASE.pop()

# ------------------------------------------------------------------------------------------------------------- empresas com título
versoes = sorted((int(m.group(1)), p) for p in glob.glob(str(S1 / "Bases consolidadas" / "documentacao" / "prototipo_bases_consolidadas_v*.xlsx"))
                 if (m := re.search(r"_v(\d+)\.xlsx$", p)))
assert versoes, "planilha consolidada não encontrada em Squad 1/Bases consolidadas/documentacao/"
PLANILHA = Path(versoes[-1][1])
VERSAO = f"v{versoes[-1][0]}"
wb = openpyxl.load_workbook(PLANILHA, read_only=True)
it = wb["02_dim_empresas"].iter_rows(min_row=4, values_only=True)
cab = list(next(it))
col_id = cab.index("company_id")
RAIZES_MINERAIS = {str(r[col_id])[9:] for r in it if r and r[0] is not None and str(r[col_id]).startswith("COM_CNPJ_")}
print(f"planilha: {PLANILHA.name} — {len(RAIZES_MINERAIS)} raízes de CNPJ com título minerário")

# ------------------------------------------------------------------------------------------------------------- CCEE observada
arquivos = sorted(glob.glob(str(S1 / "dados" / "CCEE" / "parcela_carga_consumo_*_GO.csv")))
assert arquivos, "nenhum arquivo da CCEE em Squad 1/dados/CCEE/"
por_ano = defaultdict(lambda: {"titular": 0.0, "ramo": 0.0, "base": 0.0, "acl_titular": 0.0, "meses": set(),
                               "empresas": set(), "municipios": set()})
por_empresa = defaultdict(lambda: {"mwh": 0.0, "acl": 0.0, "cap_h": 0.0, "horas": 0.0, "nomes": Counter(),
                                   "ramos": Counter(), "municipios": Counter()})
HORAS = {2: 28 * 24, 4: 30 * 24, 6: 30 * 24, 9: 30 * 24, 11: 30 * 24}  # meses de 30 e 28 dias; o resto tem 31


def horas(mes_ref):
    m = mes_ref % 100
    return HORAS.get(m, 31 * 24)


for arq in arquivos:
    for r in ler_csv(arq, ";"):
        raiz = re.sub(r"\D", "", r["CNPJ_CARGA"]).zfill(14)[:8]
        mes = int(r["MES_REFERENCIA"])
        ano = mes // 100
        total, acl = num(r["CONSUMO_TOTAL"]), num(r["CONSUMO_ACL"])
        ramo = (r["RAMO_ATIVIDADE"] or "").strip()
        a = por_ano[ano]
        a["base"] += total
        a["meses"].add(mes)
        if raiz in RAIZES_MINERAIS:
            a["titular"] += total
            a["acl_titular"] += acl
            a["empresas"].add(raiz)
            a["municipios"].add(norm(r["CIDADE"]))
            e = por_empresa[raiz]
            e["mwh"] += total
            e["acl"] += acl
            e["cap_h"] += num(r["CAPACIDADE_CARGA"]) * horas(mes)
            e["horas"] += horas(mes)
            e["nomes"][(r["NOME_EMPRESARIAL"] or "").strip()] += 1
            e["ramos"][ramo or "—"] += total
            e["municipios"][(r["CIDADE"] or "").strip()] += total
        if ramo in RAMOS_MINERAIS:
            a["ramo"] += total

anos_ccee = sorted(por_ano)
OBS_ANOS = []
for ano in anos_ccee:
    a = por_ano[ano]
    meses = len(a["meses"])
    OBS_ANOS.append({
        "ano": ano, "meses": meses,
        "mwh_titular": round(a["titular"], 3),
        "mwh_ramo": round(a["ramo"], 3),
        "mwh_base": round(a["base"], 3),
        "acl_pct_titular": round(100 * a["acl_titular"] / a["titular"], 2) if a["titular"] else None,
        # Anualização = média mensal × 12. Só serve como referência porque nenhum ano da base está completo.
        "mwh_titular_anualizado": round(a["titular"] / meses * 12, 3) if meses else None,
        "mwh_ramo_anualizado": round(a["ramo"] / meses * 12, 3) if meses else None,
        "empresas": len(a["empresas"]), "municipios": len(a["municipios"]),
    })

# Baseline: o ano com mais meses cobertos; empatado, o mais recente.
ano_base_obs = max(OBS_ANOS, key=lambda r: (r["meses"], r["ano"]))
BASELINE_MWH = ano_base_obs["mwh_titular_anualizado"]
BASELINE_RAMO_MWH = ano_base_obs["mwh_ramo_anualizado"]
assert BASELINE_MWH and BASELINE_MWH > 0, "baseline observado vazio"

OBS_EMPRESAS = []
for raiz, e in sorted(por_empresa.items(), key=lambda kv: -kv[1]["mwh"]):
    nome = mascarar_cpf(e["nomes"].most_common(1)[0][0])
    # Só razão social de pessoa jurídica: nome com CPF mascarado não sai do pacote (mesma regra do Panorama).
    if "***" in nome:
        continue
    OBS_EMPRESAS.append({
        "raiz": raiz, "nome": nome,
        "mwh": round(e["mwh"], 3),
        "acl_pct": round(100 * e["acl"] / e["mwh"], 2) if e["mwh"] else None,
        "mw_media": round(e["cap_h"] / e["horas"], 3) if e["horas"] else None,
        "fator_carga": round(100 * e["mwh"] / e["cap_h"], 2) if e["cap_h"] else None,
        "ramo": e["ramos"].most_common(1)[0][0],
        "municipio": e["municipios"].most_common(1)[0][0],
    })

# ------------------------------------------------------------------------------------------------------------- preços projetados
def preco(componente, cenario, ano):
    """Preço real do componente no ano, em R$/MWh da moeda do ano base.

    reversao_a_media: P(t) = L(t) + (P0 − L) · e^(−λ·t), com λ = ln2 / meia_vida e L(t) = L · (1 + tendência)^t.
    tendencia_real:   P(t) = P0 · (1 + tendência)^t.
    """
    p = PARAM[(componente, cenario)]
    t = ano - p["ano_base"]
    if p["metodo"] == "reversao_a_media":
        assert p["longo_prazo"] is not None and p["meia_vida"], f"{componente}/{cenario}: reversão exige nível e meia-vida"
        lam = math.log(2) / p["meia_vida"]
        nivel = p["longo_prazo"] * (1 + p["tendencia"]) ** t
        return nivel + (p["p0"] - p["longo_prazo"]) * math.exp(-lam * t)
    assert p["metodo"] == "tendencia_real", f"método desconhecido: {p['metodo']}"
    return p["p0"] * (1 + p["tendencia"]) ** t


ANOS = list(range(ANO_INICIO, ANO_FIM + 1))
PRECOS = {}   # (ano, cenario) -> {componente: valor, 'total': soma}
linhas_precos = []
for cen in CENARIOS:
    for ano in ANOS:
        partes = {c: round(preco(c, cen, ano), 2) for c in COMPONENTES}
        total = round(sum(partes.values()), 2)
        PRECOS[(ano, cen)] = dict(partes, total=total)
        linhas_precos.append([ano, CENARIOS.index(cen), *[partes[c] for c in COMPONENTES], total])

# ------------------------------------------------------------------------------------------------------------- demanda e custo
def demanda(cenario, ano):
    """Demanda de referência: o baseline observado crescendo à taxa de premissa do cenário.

    É um cenário de referência, não previsão: a demanda real virá do motor econômico-energético do Squad 2
    (projecao_total_goias), que hoje só roda sobre dados sintéticos.
    """
    return BASELINE_MWH * (1 + CRESC[cenario]["taxa"]) ** (ano - ano_base_obs["ano"])


CUSTO, linhas_custo = {}, []
for cp in CENARIOS:           # cenário de preço
    for cd in CENARIOS:       # cenário de demanda
        for ano in ANOS:
            mwh = round(demanda(cd, ano), 3)
            brl = round(mwh * PRECOS[(ano, cp)]["total"], 2)
            CUSTO[(ano, cp, cd)] = (mwh, brl)
            linhas_custo.append([ano, CENARIOS.index(cp), CENARIOS.index(cd), mwh, brl])

# ------------------------------------------------------------------------------------------------------------- sensibilidade
def custo_total(precos_mult=1.0, demanda_mult=1.0, cenario="referencia", ano=ANO_FIM):
    return demanda(cenario, ano) * demanda_mult * PRECOS[(ano, cenario)]["total"] * precos_mult


BASE_2040 = custo_total()
SENS = []
for rotulo, kw in (("preco_mais_10", {"precos_mult": 1.10}), ("preco_menos_10", {"precos_mult": 0.90}),
                   ("demanda_mais_10", {"demanda_mult": 1.10}), ("demanda_menos_10", {"demanda_mult": 0.90}),
                   ("cenario_conservador", {"cenario": "conservador"}), ("cenario_expansao", {"cenario": "expansao"})):
    v = custo_total(**kw)
    SENS.append({"parametro": rotulo, "custo_brl": round(v, 2), "variacao_pct": round(100 * (v / BASE_2040 - 1), 2)})

# A faixa da premissa (mínimo e máximo de cada componente) aplicada ao ano base, como largura da incerteza declarada.
FAIXA = {"min": round(sum(PARAM[(c, "referencia")]["min"] for c in COMPONENTES), 2),
         "base": round(sum(PARAM[(c, "referencia")]["p0"] for c in COMPONENTES), 2),
         "max": round(sum(PARAM[(c, "referencia")]["max"] for c in COMPONENTES), 2)}

# ------------------------------------------------------------------------------------------------------------- saída
tab = lambda cols, rows: {"cols": cols, "rows": rows}
dados = {
    "meta": {
        "built_on": date.today().isoformat(),
        "versao_base": VERSAO,
        "planilha": f"Squad 1/Bases consolidadas/documentacao/{PLANILHA.name}",
        "ano_base": ANO_BASE,
        "horizonte": [ANO_INICIO, ANO_FIM],
        "cenarios": CENARIOS,
        "componentes": COMPONENTES,
        "moeda": f"R$ reais de {ANO_BASE}, sem ICMS",
        "aviso": "Os preços deste pacote são premissa ilustrativa do Squad 2, não série observada. Nenhum preço de energia "
                 "existe no repositório: PLD, tarifa e leilões ainda não foram coletados (ver Squad 2/precos/README.md).",
        "sources": {
            "ccee": "Squad 1/dados/CCEE/parcela_carga_consumo_*_GO.csv — CCEE, parcelas de carga em Goiás (observado)",
            "titularidade": "aba 02_dim_empresas — raiz do CNPJ com título minerário na base consolidada do Squad 1",
            "premissas": "Squad 2/precos/premissas/premissas_preco_energia.csv e premissas_demanda_energia.csv (premissa)",
        },
        "ccee_arquivos": [Path(a).name for a in arquivos],
        "recorte": "Carga cuja raiz de CNPJ tem título minerário na base do Squad 1; RAMO_ATIVIDADE fica como recorte "
                   "alternativo mais largo, porque é autodeclarado.",
        "baseline": {"ano": ano_base_obs["ano"], "meses": ano_base_obs["meses"], "mwh_ano": BASELINE_MWH,
                     "mwh_ano_ramo": BASELINE_RAMO_MWH, "empresas": ano_base_obs["empresas"],
                     "metodo": "média mensal do ano com mais meses cobertos × 12"},
        "faixa_premissa_ano_base": FAIXA,
        "demanda_motor": None,  # preenchido quando o motor do Squad 2 entregar projeção com dados reais
    },
    "observado": {
        "por_ano": OBS_ANOS,
        "por_empresa": OBS_EMPRESAS,
    },
    "premissas": {
        "preco": pre_preco,
        "demanda": pre_demanda,
        "fontes": fontes,
    },
    "precos": tab(["ano", "cenario", *COMPONENTES, "total"], linhas_precos),
    "custo": tab(["ano", "cenario_preco", "cenario_demanda", "mwh", "brl"], linhas_custo),
    "sensibilidade": SENS,
}
SAIDA.parent.mkdir(parents=True, exist_ok=True)
with open(SAIDA, "w", encoding="utf-8", newline="\n") as f:
    json.dump(dados, f, ensure_ascii=False, separators=(",", ":"))

CSV_SAIDAS.mkdir(parents=True, exist_ok=True)


def escrever_csv(nome, cabecalho, linhas):
    with open(CSV_SAIDAS / nome, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(cabecalho)
        w.writerows(linhas)


escrever_csv("precos_energia_projetados.csv",
             ["ano", "cenario", *COMPONENTES, "total_brl_mwh", "moeda", "data_nature", "source_id"],
             [[ano, cen, *[PRECOS[(ano, cen)][c] for c in COMPONENTES], PRECOS[(ano, cen)]["total"],
               f"BRL reais {ANO_BASE}", "premissa_ilustrativa", "SRC_PREMISSA_ILUSTRATIVA"]
              for cen in CENARIOS for ano in ANOS])
escrever_csv("custo_energia_projetado.csv",
             ["ano", "cenario_preco", "cenario_demanda", "demanda_mwh", "preco_brl_mwh", "custo_brl", "data_nature", "source_id"],
             [[ano, cp, cd, CUSTO[(ano, cp, cd)][0], PRECOS[(ano, cp)]["total"], CUSTO[(ano, cp, cd)][1],
               "premissa_ilustrativa", "SRC_PREMISSA_ILUSTRATIVA"]
              for cp in CENARIOS for cd in CENARIOS for ano in ANOS])
escrever_csv("consumo_observado_ccee.csv",
             ["ano", "meses_cobertos", "mwh_titular_minerario", "mwh_ramo_mineral", "mwh_total_base",
              "mwh_titular_anualizado", "empresas_com_titulo", "data_nature", "source_id"],
             [[r["ano"], r["meses"], r["mwh_titular"], r["mwh_ramo"], r["mwh_base"], r["mwh_titular_anualizado"],
               r["empresas"], "observado", "SRC_CCEE_PARCELA_CARGA"] for r in OBS_ANOS])

# ------------------------------------------------------------------------------------------------------------- conferências
for (ano, cen), p in PRECOS.items():
    assert all(p[c] > 0 for c in COMPONENTES), f"preço não positivo em {ano}/{cen}"
    assert abs(p["total"] - round(sum(p[c] for c in COMPONENTES), 2)) < 0.01, f"total não fecha em {ano}/{cen}"
assert len(linhas_precos) == len(ANOS) * len(CENARIOS), "cobertura de preço incompleta"
assert len(linhas_custo) == len(ANOS) * len(CENARIOS) ** 2, "cobertura de custo incompleta"
for ano, icp, icd, mwh, brl in linhas_custo:
    esperado = round(mwh * PRECOS[(ano, CENARIOS[icp])]["total"], 2)
    assert abs(brl - esperado) <= 0.02, f"custo não é demanda × preço em {ano}"
assert all(r["data_nature"] != "observado" for r in pre_preco + pre_demanda), "premissa declarada como observada"

print(f"CCEE: {len(arquivos)} arquivos, anos {anos_ccee[0]}–{anos_ccee[-1]}; "
      + "; ".join(f"{r['ano']} {r['meses']} meses, titular {r['mwh_titular'] / 1000:,.1f} GWh" for r in OBS_ANOS))
print(f"baseline: {BASELINE_MWH / 1000:,.1f} GWh/ano ({ano_base_obs['ano']}, {ano_base_obs['meses']} meses anualizados), "
      f"{ano_base_obs['empresas']} empresas com título; recorte por ramo {BASELINE_RAMO_MWH / 1000:,.1f} GWh/ano")
print(f"empresas nomeadas no pacote: {len(OBS_EMPRESAS)} (pessoa jurídica)")
for cen in CENARIOS:
    print(f"preço {cen}: {PRECOS[(ANO_INICIO, cen)]['total']:,.2f} R$/MWh em {ANO_INICIO} → "
          f"{PRECOS[(ANO_FIM, cen)]['total']:,.2f} em {ANO_FIM} (energia {PRECOS[(ANO_FIM, cen)]['energia']:,.2f})")
for cen in CENARIOS:
    c = next(r for r in linhas_custo if r[0] == ANO_FIM and r[1] == CENARIOS.index(cen) and r[2] == CENARIOS.index(cen))
    print(f"custo {cen} em {ANO_FIM}: R$ {c[4] / 1e6:,.1f} milhões com {c[3] / 1000:,.1f} GWh")
print(f"faixa da premissa no ano base: R$ {FAIXA['min']:,.2f} a {FAIXA['max']:,.2f} por MWh (base {FAIXA['base']:,.2f})")
print(f"SALVO: {SAIDA} ({SAIDA.stat().st_size / 1e3:.1f} kB) e {len(list(CSV_SAIDAS.glob('*.csv')))} CSV em {CSV_SAIDAS}")
