# -*- coding: utf-8 -*-
"""Pacote de dados da aba Panorama do painel (data/panorama/panorama.json), gerado das bases do Squad 1 que estão no repositório.

    python scripts/build_panorama_base.py                  # usa a raiz do repositório onde está este script
    python scripts/build_panorama_base.py --repo <clone>

Lê só arquivos versionados:
- a planilha consolidada mais recente em `Squad 1/Bases consolidadas/documentacao/` (abas 01, 01b, 02, 03, 05 e 08);
- `Squad 1/Dados brutos/ANM - Investimento em pesquisa mineral/InvestimentoPesquisaMineralUf.csv`;
- `Squad 1/dados/CCEE/parcela_carga_consumo_*_GO.csv` e `Squad 1/dados/ResultadoRodadaDisponibilidade (1).csv`.
A energia e a intensidade por município, a produção por substância no mapa e as barragens vêm do atlas (`data/atlas/atlas.json`), que o painel
já carrega. Os fatos saem em colunas com dicionários (`dims`), para o navegador filtrar por ano, mês, município, mineral, empresa, fase, rubrica e
ramo sem pedir nada ao servidor. Nomes de pessoa física não entram: titular só aparece com nome quando o company_id é COM_CNPJ_ e o nome não tem
CPF mascarado, e arrematante de rodada só aparece quando o documento é CNPJ.
"""
import argparse
import csv
import glob
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

import openpyxl

sys.stdout.reconfigure(encoding="utf-8")
ap = argparse.ArgumentParser(description="Gera data/panorama/panorama.json a partir das bases do Squad 1 no repositório.")
ap.add_argument("--repo", default=str(Path(__file__).resolve().parents[1]), help="raiz do clone (padrão: a deste script)")
ap.add_argument("--saida", help="padrão: <repo>/data/panorama/panorama.json")
args = ap.parse_args()
REPO = Path(args.repo)
SAIDA = Path(args.saida) if args.saida else REPO / "data" / "panorama" / "panorama.json"
S1 = REPO / "Squad 1"


def norm(s):
    return unicodedata.normalize("NFD", str(s or "")).encode("ascii", "ignore").decode().upper().strip()


def num_br(s):
    """Número em formato brasileiro ('1.527,45', ',00'); vazio ou '-' vale 0."""
    s = str(s or "").strip()
    if not s or s == "-":
        return 0.0
    return float(s.replace(".", "").replace(",", ".")) if "," in s else float(s)


def num(s):
    s = str(s or "").strip()
    return float(s) if s else 0.0


def codigo(x):
    return str(int(float(x))) if x not in (None, "") else ""


CPF = re.compile(r"(?<!\d)(\d{3})\.?(\d{3})\.?(\d{3})-?(\d{2})(?!\d)")


def mascarar_cpf(nome):
    """Mesma máscara da base consolidada: CPF dentro de um nome vira ***456789**."""
    return CPF.sub(lambda m: "***" + "".join(m.groups())[3:9] + "**", str(nome))


_CHAVE = object()  # valor padrão de Dim.idx: guardar a própria chave


class Dim:
    """Dicionário de valores: guarda cada chave uma vez e devolve a posição."""

    def __init__(self):
        self.items, self.pos = [], {}

    def idx(self, chave, valor=_CHAVE):
        if chave not in self.pos:
            self.pos[chave] = len(self.items)
            self.items.append(chave if valor is _CHAVE else valor)
        return self.pos[chave]


# ----------------------------------------------------------------------------------------------------------------- planilha
versoes = sorted((int(m.group(1)), p) for p in glob.glob(str(S1 / "Bases consolidadas" / "documentacao" / "prototipo_bases_consolidadas_v*.xlsx"))
                 if (m := re.search(r"_v(\d+)\.xlsx$", p)))
assert versoes, "planilha consolidada não encontrada em Squad 1/Bases consolidadas/documentacao/"
PLANILHA = Path(versoes[-1][1])
VERSAO = f"v{versoes[-1][0]}"
print(f"planilha: {PLANILHA.name}")
wb = openpyxl.load_workbook(PLANILHA, read_only=True)


def ler(aba, colunas):
    it = wb[aba].iter_rows(min_row=4, values_only=True)
    cab = list(next(it))
    pos = {c: cab.index(c) for c in colunas}
    for r in it:
        if r and r[0] is not None:
            yield {c: (r[i] if i < len(r) else None) for c, i in pos.items()}


MUN, mun_idx, mun_nome = [], {}, {}
for r in ler("05_dim_municipios", ["municipality_id", "municipality_name"]):
    c = codigo(r["municipality_id"])
    mun_idx[c] = len(MUN)
    mun_nome[norm(r["municipality_name"])] = len(MUN)
    MUN.append([c, r["municipality_name"]])
# População e PIB do último ano de cada município (aba 10): MUN vira [código, nome, população, PIB em R$].
for m in MUN:
    m += [None, None]
ANOS_POP, ANOS_PIB = Counter(), Counter()
for r in ler("10_cons_municipio_ano", ["municipality_id", "populacao", "populacao_ano", "pib_total_brl", "pib_ano"]):
    i = mun_idx.get(codigo(r["municipality_id"]))
    if i is None:
        continue
    if MUN[i][2] is None and r["populacao"] not in (None, ""):
        MUN[i][2] = int(float(r["populacao"]))
        ANOS_POP[r["populacao_ano"]] += 1
    if MUN[i][3] is None and r["pib_total_brl"] not in (None, ""):
        MUN[i][3] = round(float(r["pib_total_brl"]), 2)
        ANOS_PIB[r["pib_ano"]] += 1
ALIAS_MUN = {"AGUA LINDAS DE GOIAS": "AGUAS LINDAS DE GOIAS"}  # grafia da CCEE


def mun_de_nome(nome):
    k = norm(nome)
    return mun_nome.get(ALIAS_MUN.get(k, k), -1)


MIN, min_idx, min_nome = [], {}, {}
for r in ler("01_dim_minerais", ["mineral_id", "mineral_name", "classe_substancia"]):
    min_idx[r["mineral_id"]] = len(MIN)
    min_nome[norm(r["mineral_name"])] = len(MIN)
    MIN.append([r["mineral_id"], r["mineral_name"], r["classe_substancia"]])


def mineral(mid=None, nome=None):
    if mid in min_idx:
        return min_idx[mid]
    return min_nome.get(norm(nome), -1) if nome else -1


XW = {}
for r in ler("01b_crosswalk_pente_fino", ["valor_normalizado", "atribuido_a"]):
    m = re.match(r"(MIN_\d+)", str(r["atribuido_a"] or ""))
    if m:
        XW.setdefault(str(r["valor_normalizado"]), m.group(1))

EMPRESAS = {r["company_id"]: r for r in ler("02_dim_empresas", ["company_id", "razao_social", "cnpj_raiz", "tipo_pessoa"])}
EMP, emp_idx = [], {}


def empresa(cid):
    """[company_id, nome ou null, raiz do CNPJ ou null, tipo]: nome só para COM_CNPJ_ sem CPF mascarado."""
    if not cid:
        return -1
    if cid not in emp_idx:
        r = EMPRESAS.get(cid, {})
        nome = r.get("razao_social")
        pj = str(cid).startswith("COM_CNPJ_")
        mostrar = pj and nome and "***" not in str(nome) and mascarar_cpf(nome) == str(nome)
        tipo = "pj" if pj else ("ni" if cid == "COM_NAO_IDENTIFICADO" else "oculto")
        emp_idx[cid] = len(EMP)
        EMP.append([cid, nome if mostrar else None, str(r.get("cnpj_raiz") or "") if mostrar else None, tipo])
    return emp_idx[cid]


# ----------------------------------------------------------------------------------------------------------------- 08: CFEM e AMB
cfem = defaultdict(lambda: [0.0, 0])
go = defaultdict(lambda: [0.0] * 6)       # rom_t, rom_rs, benef_t, benef_rs, contido_rom_t, contido_benef_t
br = defaultdict(lambda: [0.0, 0.0])      # rom_t, benef_rs (soma de todas as UFs)
ufs = defaultdict(lambda: [0.0, 0.0])     # rom_t, benef_rs por UF
UF = Dim()
COL = {"producao_rom": 0, "valor_venda_rom": 1, "producao_beneficiada": 2, "valor_venda_beneficiada": 3, "contido_rom": 4, "contido_beneficiada": 5}
sem_mes = 0
for r in ler("08_fato_producao_energia", ["metrica", "year", "periodo_referencia", "uf", "mineral_id", "company_id", "municipality_id",
                                          "valor_tratado", "unidade_padrao", "status_validacao"]):
    met = r["metrica"]
    if met == "cfem_recolhido":
        m = re.search(r"(\d{4})-(\d{1,2})", str(r["periodo_referencia"] or ""))
        if not m:
            sem_mes += 1
            continue
        k = (int(m.group(1)), int(m.group(2)), mun_idx.get(codigo(r["municipality_id"]), -1), mineral(mid=r["mineral_id"]), empresa(r["company_id"]))
        cfem[k][0] += float(r["valor_tratado"] or 0)
        cfem[k][1] += 1
    elif met in COL:
        if met.startswith("contido") and r["unidade_padrao"] != "t":
            continue
        if met == "producao_rom" and r["status_validacao"] == "rom_minerio_associado":
            continue  # bário, cobalto e prata com a massa do minério de outro mineral: somar contaria o mesmo minério duas vezes
        v, ano, mi = float(r["valor_tratado"] or 0), int(float(r["year"])), mineral(mid=r["mineral_id"])
        if r["uf"] == "GO":
            go[(ano, mi)][COL[met]] += v
        if met in ("producao_rom", "valor_venda_beneficiada"):
            j = 0 if met == "producao_rom" else 1
            br[(ano, mi)][j] += v
            ufs[(ano, UF.idx(r["uf"]))][j] += v
assert not sem_mes, f"{sem_mes} linhas de CFEM sem mês em periodo_referencia"

# ----------------------------------------------------------------------------------------------------------------- 03: processos
FASE, USO, STATUS = Dim(), Dim(), Dim()
proc = []
for r in ler("03_dim_operacoes", ["processo_anm", "company_id", "mineral_principal", "municipality_id", "fase_atual", "status_operacional",
                                  "area_ha_declarada", "area_ha_calculada", "uso_declarado", "cfem_2022_2026_brl"]):
    m = re.search(r"/(\d{4})$", str(r["processo_anm"] or ""))
    area = r["area_ha_declarada"] if r["area_ha_declarada"] not in (None, "") else (r["area_ha_calculada"] or 0)
    proc.append([FASE.idx(r["fase_atual"] or "—"), mineral(nome=r["mineral_principal"]), mun_idx.get(codigo(r["municipality_id"]), -1),
                 empresa(r["company_id"]), round(float(area), 2), USO.idx(r["uso_declarado"] or "—"), STATUS.idx(r["status_operacional"] or "—"),
                 int(m.group(1)) if m else 0, round(float(r["cfem_2022_2026_brl"] or 0), 2), str(r["processo_anm"])])
min_do_processo = {p[9]: p[1] for p in proc}

# ----------------------------------------------------------------------------------------------------------------- investimento em pesquisa
RUBRICAS = [("ValorAnaliseFisica", "analise_fisica"), ("ValorAnaliseQuimica", "analise_quimica"), ("ValorEnsaioBeneficiamento", "ensaio_beneficiamento"),
            ("ValorGaleriaShaft", "galeria_shaft"), ("ValorGeologia", "geologia"), ("ValorInfraestrutura", "infraestrutura"), ("ValorOutro", "outro"),
            ("ValorProspeccaoGeofisica", "geofisica"), ("ValorProspeccaoGeoquimica", "geoquimica"), ("ValorSondagem", "sondagem"),
            ("ValorTopografiaCartografiaDesenho", "topografia"), ("ValorTrincheiraPoco", "trincheira_poco")]
SUBINV = Dim()
inv_go, inv_br = [], defaultdict(float)
ARQ_INV = S1 / "Dados brutos" / "ANM - Investimento em pesquisa mineral" / "InvestimentoPesquisaMineralUf.csv"
with open(ARQ_INV, encoding="cp1252", newline="") as f:
    for r in csv.DictReader(f, delimiter=";"):
        ano = int(r["Ano"])
        for j, (col, _) in enumerate(RUBRICAS):
            v = num_br(r[col])
            if not v:
                continue
            inv_br[(ano, j)] += v
            if r["UF"] == "GO":
                s = r["Substancia"]
                si = SUBINV.idx(s, [s, mineral(mid=XW.get(norm(s)))])
                inv_go.append([ano, si, j, round(v, 2)])

# ----------------------------------------------------------------------------------------------------------------- rodadas de disponibilidade
SIT, MOD, REG, VENC = Dim(), Dim(), Dim(), Dim()
rod = []
with open(S1 / "dados" / "ResultadoRodadaDisponibilidade (1).csv", encoding="utf-8-sig", newline="") as f:
    for r in csv.DictReader(f, delimiter=";"):
        if norm(r["UnidadeFederacao"]) != "GOIAS":
            continue
        nome, doc = r["NomeVencedor"].strip(), r["CpfCnpjVencedor"].strip()
        venc = -1
        if nome:
            # Nome só para CNPJ sem CPF no texto (empresário individual costuma trazer o CPF no nome).
            venc = VENC.idx(nome, nome) if "/" in doc and mascarar_cpf(nome) == nome else VENC.idx("__pessoa_fisica__", None)
        rod.append([int(r["Rodada"]), SIT.idx(r["Situacao"].strip()), MOD.idx(r["Modalidade"].strip()), REG.idx(r["RegimeDisponibilidade"].strip()),
                    mun_de_nome(r["Municipio"]), round(num_br(r["AreaPoligonal"]), 2), round(num_br(r["ValorLanceVencedorReais"]), 2), venc,
                    r["ProcessoMinerario"].strip(), min_do_processo.get(r["ProcessoMinerario"].strip(), -1)])

# ----------------------------------------------------------------------------------------------------------------- CCEE
RAMO = Dim()
# Cargas sem ramo de atividade são das distribuidoras (Equatorial Goiás, CHESP): o mercado cativo, não um setor.
DISTRIBUIDORA = "DISTRIBUIDORA (MERCADO CATIVO)"
nomes_distribuidora = Counter()
ccee = defaultdict(lambda: [0.0, 0.0, 0.0, 0.0])
nomes_ccee = defaultdict(Counter)
arquivos_ccee = sorted(glob.glob(str(S1 / "dados" / "CCEE" / "parcela_carga_consumo_*_GO.csv")))
for arq in arquivos_ccee:
    with open(arq, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f, delimiter=";"):
            raiz = re.sub(r"\D", "", r["CNPJ_CARGA"]).zfill(14)[:8]
            nomes_ccee[raiz][r["NOME_EMPRESARIAL"].strip()] += 1
            if not r["RAMO_ATIVIDADE"].strip():
                nomes_distribuidora[r["NOME_EMPRESARIAL"].strip()] += 1
            k = (int(r["MES_REFERENCIA"]), mun_de_nome(r["CIDADE"]), RAMO.idx(r["RAMO_ATIVIDADE"].strip() or DISTRIBUIDORA), raiz)
            a = ccee[k]
            a[0] += num(r["CONSUMO_ACL"])
            a[1] += num(r["CONSUMO_CATIVO_PARC_LIVRE"])
            a[2] += num(r["CONSUMO_TOTAL"])
            a[3] += num(r["CAPACIDADE_CARGA"])
CE, ce_idx = [], {}
for raiz in sorted(nomes_ccee):
    cid = "COM_CNPJ_" + raiz
    ce_idx[raiz] = len(CE)
    CE.append([raiz, mascarar_cpf(nomes_ccee[raiz].most_common(1)[0][0]), empresa(cid) if cid in EMPRESAS else -1])

# ----------------------------------------------------------------------------------------------------------------- saída
tab = lambda cols, rows: {"cols": cols, "rows": rows}
anos_cfem = sorted({k[0] for k in cfem})
dados = {
    "meta": {
        "built_on": date.today().isoformat(),
        "versao_base": VERSAO,
        "planilha": f"Squad 1/Bases consolidadas/documentacao/{PLANILHA.name}",
        "ccee_distribuidora": DISTRIBUIDORA,
        "sources": {
            "cfem": "aba 08 (cfem_recolhido) — ANM CFEM de Goiás",
            "amb": "aba 08 (produção bruta e beneficiada, todas as UFs) — ANM Anuário Mineral Brasileiro",
            "proc": "aba 03 — SIGMINE Goiás, com titular, CFEM e status da base consolidada",
            "inv": "Squad 1/Dados brutos/ANM - Investimento em pesquisa mineral/InvestimentoPesquisaMineralUf.csv",
            "rod": "Squad 1/dados/ResultadoRodadaDisponibilidade (1).csv — ANM, rodadas de disponibilidade de áreas",
            "ccee": "Squad 1/dados/CCEE/parcela_carga_consumo_*_GO.csv — CCEE, parcelas de carga em Goiás",
            "atlas": "data/atlas/atlas.json — energia e intensidade por município e barragens, do retrato recebido",
        },
        "periods": {
            "cfem": [anos_cfem[0], anos_cfem[-1]],
            "amb": [min(k[0] for k in go), max(k[0] for k in go)],
            "inv": [min(r[0] for r in inv_go), max(r[0] for r in inv_go)],
            "ccee": [min(k[0] for k in ccee), max(k[0] for k in ccee)],
            "pop": ANOS_POP.most_common(1)[0][0], "pib": ANOS_PIB.most_common(1)[0][0],
        },
        # Blocos do Panorama original que as bases do repositório não permitem refazer (explicados na própria aba).
        "not_reproduced": ["cfem_nacional", "repasse", "agua", "tah", "repem", "inativos", "coef_empresas"],
    },
    "dims": {"mun": MUN, "min": MIN, "emp": EMP, "fase": FASE.items, "uso": USO.items, "status": STATUS.items, "uf": UF.items,
             "subinv": SUBINV.items, "rubrica": [c for _, c in RUBRICAS], "sit": SIT.items, "mod": MOD.items, "reg": REG.items, "venc": VENC.items,
             "ramo": RAMO.items, "ce": CE},
    "cfem": tab(["ano", "mes", "mun", "min", "emp", "valor", "n"], [[*k, round(v[0], 2), v[1]] for k, v in sorted(cfem.items())]),
    "amb_go": tab(["ano", "min", "rom_t", "rom_rs", "benef_t", "benef_rs", "contido_rom_t", "contido_benef_t"],
                  [[*k, *[round(x, 3) for x in v]] for k, v in sorted(go.items())]),
    "amb_br": tab(["ano", "min", "rom_t", "benef_rs"], [[*k, *[round(x, 3) for x in v]] for k, v in sorted(br.items())]),
    "amb_uf": tab(["ano", "uf", "rom_t", "benef_rs"], [[*k, *[round(x, 3) for x in v]] for k, v in sorted(ufs.items())]),
    "proc": tab(["fase", "min", "mun", "emp", "area_ha", "uso", "status", "ano_processo", "cfem_2022_2026", "processo"], proc),
    "inv_go": tab(["ano", "sub", "rubrica", "valor"], sorted(inv_go)),
    "inv_br": tab(["ano", "rubrica", "valor"], [[*k, round(v, 2)] for k, v in sorted(inv_br.items())]),
    "rod": tab(["rodada", "situacao", "modalidade", "regime", "mun", "area_ha", "lance", "vencedor", "processo", "min"], rod),
    "ccee": tab(["mes", "mun", "ramo", "empresa", "acl_mwh", "cativo_mwh", "total_mwh", "capacidade_mw"],
                [[k[0], k[1], k[2], ce_idx[k[3]], *[round(x, 3) for x in v]] for k, v in sorted(ccee.items())]),
}
SAIDA.parent.mkdir(parents=True, exist_ok=True)
with open(SAIDA, "w", encoding="utf-8", newline="\n") as f:
    json.dump(dados, f, ensure_ascii=False, separators=(",", ":"))

# ----------------------------------------------------------------------------------------------------------------- conferências
soma = lambda it: sum(it)
print(f"CFEM: R$ {soma(v[0] for v in cfem.values()):,.2f} em {soma(v[1] for v in cfem.values())} linhas; por ano: "
      + "; ".join(f"{a} R$ {soma(v[0] for k, v in cfem.items() if k[0] == a):,.2f}" for a in anos_cfem))
print(f"AMB GO: valor da beneficiada 2010 R$ {soma(v[3] for k, v in go.items() if k[0] == 2010):,.2f}; "
      f"2025 R$ {soma(v[3] for k, v in go.items() if k[0] == 2025):,.2f}; ROM 2025 {soma(v[0] for k, v in go.items() if k[0] == 2025):,.0f} t; "
      f"participação no valor nacional 2025 {100 * soma(v[3] for k, v in go.items() if k[0] == 2025) / soma(v[1] for k, v in br.items() if k[0] == 2025):.2f}%")
print(f"processos: {len(proc)}; área declarada {soma(p[4] for p in proc):,.0f} ha; municípios com processo {len({p[2] for p in proc if p[2] >= 0})}")
print(f"investimento GO: 2003 R$ {soma(r[3] for r in inv_go if r[0] == 2003):,.2f}; 2025 R$ {soma(r[3] for r in inv_go if r[0] == 2025):,.2f}; "
      f"substâncias {len(SUBINV.items)} (sem mineral: {[s for s, m in SUBINV.items if m < 0]})")
print(f"rodadas GO: {len(rod)} áreas; {Counter(SIT.items[r[1]] for r in rod).most_common()}; lances R$ {soma(r[6] for r in rod):,.2f}; "
      f"sem município {sum(1 for r in rod if r[4] < 0)}")
print(f"CCEE: {len(arquivos_ccee)} arquivos, meses {min(k[0] for k in ccee)}–{max(k[0] for k in ccee)}, {len(ccee)} linhas agregadas; "
      f"consumo total 2025 {soma(v[2] for k, v in ccee.items() if 202501 <= k[0] <= 202512):,.0f} MWh; empresas {len(CE)} "
      f"(com título minerário na base: {sum(1 for c in CE if c[2] >= 0)}); sem município {sum(1 for k in ccee if k[1] < 0)}")
print(f"população e PIB: {sum(1 for m in MUN if m[2])} municípios; anos {dict(ANOS_POP)} / {dict(ANOS_PIB)}; Goiânia {[m for m in MUN if m[0] == '5208707']}; Alto Horizonte {[m for m in MUN if m[0] == '5200555']}")
print(f"CCEE sem ramo (distribuidoras): {dict(nomes_distribuidora)}")
print(f"dims: {len(MUN)} municípios, {len(MIN)} minerais, {len(EMP)} titulares ({sum(1 for e in EMP if e[1])} com nome)")
print(f"SALVO: {SAIDA} ({SAIDA.stat().st_size / 1e6:.2f} MB)")
