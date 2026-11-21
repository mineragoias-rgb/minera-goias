# -*- coding: utf-8 -*-
"""Base de produção mineral de Goiás por empresa (Squad 1 / Estudante 1 — Frente 1).

    python "Squad 1/Bases consolidadas/base_consolidada_work/scripts/gerar_base_producao.py"

Versão legível da aba 12 da base consolidada: uma linha por ano × mineral × base (ROM ou beneficiada) × empresa, com a
produção dividida pela CFEM, a parcela da empresa no total do estado, os municípios e os processos — e, ao lado, o número
que a própria empresa publica (relatórios, RIs, 10-K, HKEX), quando existe, com a diferença quando os dois medem a mesma coisa.

Entradas (nada é recalculado aqui):
  - documentacao/pacote_squad2/interface_squad1_squad2.csv — aba 12: total do estado (AMB) e divisão por processo (CFEM em R$);
  - documentacao/prototipo_bases_consolidadas_v19.xlsx — nomes das empresas (aba 02) e dos municípios (aba 05);
  - Squad 1/Auditoria e qualidade/producao_empresas_ri_2025_2026.csv — produção publicada pelas empresas.

Saídas (documentacao/base_producao/):
  - base_producao_empresa_ano.csv — empresa × mineral × ano × base;
  - base_producao_estado_ano.csv — total do estado por mineral × ano × base, com a parte dividida por empresa e a confirmada;
  - LEIA-ME.md.
Pessoa física não tem nome nem CPF publicados: aparece como "pessoa física (nome não publicado)".
"""
import csv
import os
import sys
from collections import defaultdict

import openpyxl

sys.stdout.reconfigure(encoding="utf-8")
AQUI = os.path.dirname(os.path.abspath(__file__))
BASE = os.path.abspath(os.path.join(AQUI, "..", ".."))
DOC = os.path.join(BASE, "documentacao")
RI = os.path.join(BASE, "..", "Auditoria e qualidade", "producao_empresas_ri_2025_2026.csv")
SAIDA = os.path.join(DOC, "base_producao")
OZ_T = 31.1034768e-6  # t por onça troy

# Número publicado que mede a mesma coisa que a linha da aba 12 (mesmo produto, mesma base). O resto entra só como informação.
# (prefixo da empresa na tabela de RIs, mineral na tabela de RIs, medida) -> (company_id, mineral da aba 12, base, fator para t, comparável?)
PUBLICADOS = {
    ("Mosaic Fertilizantes", "Fosfato", "concentrado de rocha fosfática (~34,7% P2O5)"): ("COM_CNPJ_33931486", "Fosfato", "beneficiada", 1.0, True),
    ("AngloGold Ashanti", "Ouro", "ouro produzido"): ("COM_CNPJ_42445403", "Ouro", "beneficiada", OZ_T, True),
    ("Hochschild Mining", "Ouro", "ouro produzido"): ("COM_CNPJ_42799486", "Ouro", "beneficiada", OZ_T, True),
    ("Eternit (SAMA)", "Amianto", "fibra de crisotila vendida"): ("COM_CNPJ_15104599", "Amianto", "beneficiada", 1.0, True),
    ("Eternit (SAMA)", "Amianto", "fibra de crisotila exportada"): ("COM_CNPJ_15104599", "Amianto", "beneficiada", 1.0, True),
    ("Lundin Mining", "Cobre", "cobre produzido (base 100%)"): ("COM_CNPJ_86902053", "Cobre", "beneficiada", 1.0, False),
    ("Lundin Mining", "Cobre", "metal no concentrado"): ("COM_CNPJ_86902053", "Cobre", "beneficiada", 1.0, False),
    ("Anglo American", "Níquel", "níquel no ferroníquel (Brasil)"): ("COM_CNPJ_42184226", "Níquel", "beneficiada", 1.0, False),
    ("CMOC (NML", "Nióbio", "nióbio (t de metal convertido)"): ("COM_CNPJ_26108898", "Nióbio", "beneficiada", 1.0, False),
    ("CMOC (NML", "Nióbio", "nióbio contido em liga"): ("COM_CNPJ_26108898", "Nióbio", "beneficiada", 1.0, False),
}
POR_QUE_NAO = {"Cobre": "a empresa publica o cobre metálico; o AMB, o concentrado (compare com o cobre contido do AMB)",
               "Níquel": "a empresa publica o níquel contido; o AMB, o ferroníquel (compare com o níquel contido do AMB)",
               "Nióbio": "a empresa publica o nióbio metálico; a beneficiada do AMB mudou de escala em 2024"}


def ler_aba(wb, nome):
    it = wb[nome].iter_rows(min_row=4, values_only=True)
    cab = list(next(it))
    return [dict(zip(cab, r)) for r in it if r and r[0] is not None]


wb = openpyxl.load_workbook(os.path.join(DOC, "prototipo_bases_consolidadas_v19.xlsx"), read_only=True)
EMP = {}
for r in ler_aba(wb, "02_dim_empresas"):
    pf = str(r.get("tipo_pessoa") or "").upper() == "PF"
    EMP[r["company_id"]] = ("pessoa física (nome não publicado)" if pf else (r.get("razao_social") or ""), "" if pf else str(r.get("cnpj_raiz") or ""))
MUN = {str(r["municipality_id"]): r.get("municipality_name") or r.get("nome_municipio") or "" for r in ler_aba(wb, "05_dim_municipios")}
wb.close()

with open(os.path.join(DOC, "pacote_squad2", "interface_squad1_squad2.csv"), encoding="utf-8-sig") as f:
    linhas = list(csv.DictReader(f))
num = lambda v: float(v) if v not in (None, "") else 0.0

estado, status_estado = {}, {}
emp = defaultdict(lambda: dict(t=0.0, procs=set(), muns=set(), com_coord=0.0, cfem=0.0))
for r in linhas:
    k = (r["year"], r["mineral_name"], r["production_basis"])
    if r["nivel_agregacao"] == "estado":
        estado[k] = num(r["production_t"])
        status_estado[k] = r["status_validacao"]
        continue
    # linhas de minério associado parcial (ex.: minério da Chapada no ROM de ouro, já no ROM de cobre): à parte, fora da divisão
    e = emp[k + (r["company_id"] or "COM_NAO_IDENTIFICADO", r["status_validacao"] == "rom_minerio_associado")]
    t = num(r["production_t"])
    e["t"] += t
    e["procs"].add(r["processo_anm"])
    if r["municipality_id"]:
        e["muns"].add(MUN.get(str(r["municipality_id"]).split(".")[0], str(r["municipality_id"])))
    e["com_coord"] += t if r["latitude"] else 0.0
    e["cfem"] += num(r["cfem_brl_operacao"])

pub = defaultdict(list)
with open(RI, encoding="utf-8-sig") as f:
    for r in csv.DictReader(f, delimiter=";"):
        if not (r["periodo"].isdigit() and r["tipo_valor"].startswith("realizado") and r["valor"].replace(".", "", 1).isdigit()):
            continue  # só o ano fechado realizado; trimestres, metas e guidance ficam de fora
        for (pref, mineral, medida), (cid, m12, base, fator, comp) in PUBLICADOS.items():
            if r["empresa"].startswith(pref) and r["mineral"] == mineral and r["medida"] == medida:
                pub[(r["periodo"], m12, base, cid)].append(dict(valor=float(r["valor"]), unidade=r["unidade"], medida=medida, t=float(r["valor"]) * fator,
                                                                comparavel=comp, fonte=r["fonte"], url=r["url"], conferido=r["conferido_no_original"]))

os.makedirs(SAIDA, exist_ok=True)
CAMPOS = ["ano", "mineral", "base", "empresa", "cnpj_raiz", "company_id", "producao_t", "parcela_do_estado", "producao_estado_t", "processos",
          "municipios", "parcela_com_coordenadas", "cfem_brl", "metodo", "publicado_valor", "publicado_unidade", "publicado_medida",
          "publicado_em_t", "diferenca_base_vs_publicado", "publicado_comparavel", "publicado_fonte", "publicado_url", "publicado_conferido_no_original"]
saida, conf = [], defaultdict(float)
for (ano, mineral, base, cid, assoc), e in sorted(emp.items(), key=lambda kv: (kv[0][0], kv[0][1], kv[0][2], kv[0][4], -kv[1]["t"])):
    tot = estado.get((ano, mineral, base), 0.0)
    nome, raiz = EMP.get(cid, ("não identificada", ""))
    linha = dict(ano=ano, mineral=mineral, base=base, empresa=nome, cnpj_raiz=raiz, company_id=cid, producao_t=round(e["t"], 3),
                 parcela_do_estado=round(e["t"] / tot, 6) if tot else "", producao_estado_t=round(tot, 3), processos=len(e["procs"]),
                 municipios="; ".join(sorted(m for m in e["muns"] if m)), parcela_com_coordenadas=round(e["com_coord"] / e["t"], 4) if e["t"] else "",
                 cfem_brl=round(e["cfem"], 2), metodo="total do estado (AMB) × parcela da empresa na CFEM em R$ do mineral e ano; margem ±10%"
                 if e["t"] < tot * 0.999 else "única produtora do mineral: produção = total do estado (AMB)")
    if assoc:
        linha["metodo"] = ("minério de outro mineral declarado de novo neste ROM (rom_minerio_associado): já está no ROM do mineral que a empresa paga "
                           "na CFEM; não somar — rateado pela CFEM desse mineral")
    for p in ([] if assoc else pub.get((ano, mineral, base, cid), [])[:1]):
        linha.update(publicado_valor=p["valor"], publicado_unidade=p["unidade"], publicado_medida=p["medida"], publicado_em_t=round(p["t"], 3),
                     publicado_comparavel="sim" if p["comparavel"] else "não: " + POR_QUE_NAO.get(mineral, ""),
                     diferenca_base_vs_publicado=round(e["t"] / p["t"] - 1, 4) if p["comparavel"] and p["t"] else "",
                     publicado_fonte=p["fonte"], publicado_url=p["url"], publicado_conferido_no_original=p["conferido"])
        conf[(ano, mineral, base)] += e["t"]
    saida.append(linha)
with open(os.path.join(SAIDA, "base_producao_empresa_ano.csv"), "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=CAMPOS, delimiter=";", lineterminator="\r\n")
    w.writeheader()
    w.writerows(saida)

CAMPOS_E = ["ano", "mineral", "base", "producao_estado_t", "minerio_de_outro_mineral_t", "dividida_por_empresa_t", "parcela_dividida", "empresas",
            "com_numero_publicado_t", "parcela_com_numero_publicado", "situacao"]
est = []
for (ano, mineral, base), tot in sorted(estado.items()):
    if tot <= 0:
        continue
    div = sum(e["t"] for k, e in emp.items() if k[:3] == (ano, mineral, base) and not k[4])
    outro = sum(e["t"] for k, e in emp.items() if k[:3] == (ano, mineral, base) and k[4])
    n = sum(1 for k in emp if k[:3] == (ano, mineral, base) and not k[4])
    st = status_estado.get((ano, mineral, base), "")
    sit = ("minério de outro mineral declarado de novo (rom_minerio_associado): não somar" if st == "rom_minerio_associado" else
           "antes de 2022: sem CFEM na base para dividir" if int(ano) < 2022 else "sem CFEM do mineral no ano: sem divisão" if not div else
           "2026: sem AMB publicado" if int(ano) > 2025 else
           "dividida pela CFEM; a parte que é minério de outro mineral (já no ROM dele) fica à parte" if outro else "dividida pela CFEM")
    est.append(dict(ano=ano, mineral=mineral, base=base, producao_estado_t=round(tot, 3), minerio_de_outro_mineral_t=round(outro, 3),
                    dividida_por_empresa_t=round(div, 3), parcela_dividida=round(div / (tot - outro), 6), empresas=n, com_numero_publicado_t=round(conf[(ano, mineral, base)], 3),
                    parcela_com_numero_publicado=round(conf[(ano, mineral, base)] / tot, 6), situacao=sit))
with open(os.path.join(SAIDA, "base_producao_estado_ano.csv"), "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=CAMPOS_E, delimiter=";", lineterminator="\r\n")
    w.writeheader()
    w.writerows(est)

def br(x):
    """Número no padrão brasileiro; abaixo de 100 com duas casas (ouro em t)."""
    s = f"{x:,.0f}" if abs(x) >= 100 else f"{x:,.2f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


# Resumo para o LEIA-ME: anos com CFEM, ROM e beneficiada, sem o minério associado
res = []
for ano in sorted({e["ano"] for e in est}):
    if not "2022" <= ano <= "2025":
        continue
    for base in ("ROM", "beneficiada"):
        xs = [e for e in est if e["ano"] == ano and e["base"] == base and not e["situacao"].startswith("minério de outro")]
        tot = sum(e["producao_estado_t"] - e["minerio_de_outro_mineral_t"] for e in xs)
        div = sum(e["dividida_por_empresa_t"] for e in xs)
        res.append(f"| {ano} | {base} | {tot / 1e6:,.1f} Mt | {div / tot:.1%} | {sum(e['empresas'] for e in xs)} |".replace(",", "X").replace(".", ",").replace("X", "."))
dif = [l for l in saida if l.get("diferenca_base_vs_publicado", "") != ""]
with open(os.path.join(SAIDA, "LEIA-ME.md"), "w", encoding="utf-8", newline="\n") as f:
    f.write("# Base de produção mineral de Goiás por empresa\n\n"
            "Gerada por `base_consolidada_work/scripts/gerar_base_producao.py` a partir da aba 12 da base consolidada (pacote do Squad 2), "
            "dos nomes das abas 02 e 05 e da produção publicada pelas empresas (`Squad 1/Auditoria e qualidade/producao_empresas_ri_2025_2026.csv`). "
            "Não editar à mão: a cadeia `scripts/atualizar_derivados.py` refaz os arquivos quando a base muda.\n\n"
            "## Como a produção é dividida\n\n"
            "- **Total do estado:** Anuário Mineral Brasileiro (ANM), por mineral e ano, em ROM e beneficiada. É o controle: a soma das empresas fecha nele.\n"
            "- **Parcela de cada empresa (2022 em diante):** a parcela dos processos dela na CFEM paga em R$ naquele mineral e ano. A CFEM em t não é usada "
            "(unidades trocadas e quantidades implausíveis — ver `Squad 1/Dados corrigidos/REGISTRO_DE_ALTERACOES.md`). Meses de pagamento atípico entram pela "
            "mediana do processo. Margem de ±10%, medida contra o que as empresas publicam.\n"
            "- **Minério associado** (bário, cobalto, prata declarados com a massa do minério de outro mineral) não é dividido nem somado. "
            "No ouro, o ROM do AMB inclui o minério de cobre-ouro da Chapada, já no ROM de cobre: essa parte (igual ao ROM de cobre do ano) fica numa "
            "linha à parte da Maracá, marcada como minério de outro mineral, e só o restante é dividido pela CFEM de ouro "
            "(coluna `minerio_de_outro_mineral_t` no arquivo do estado).\n"
            "- **Pessoa física:** sem nome nem CPF.\n\n"
            "## Arquivos\n\n"
            "| Arquivo | Uma linha por | Colunas principais |\n|---|---|---|\n"
            "| `base_producao_empresa_ano.csv` | ano × mineral × base × empresa | produção dividida (t), parcela do estado, processos, municípios, CFEM, número publicado pela empresa e diferença |\n"
            "| `base_producao_estado_ano.csv` | ano × mineral × base | total do estado, parte dividida por empresa, parte com número publicado, situação |\n\n"
            "## Cobertura (2022–2025, sem o minério associado)\n\n"
            "| Ano | Base | Total do estado (sem minério de outro mineral) | Dividido por empresa | Linhas de empresa |\n|---|---|---:|---:|---:|\n" + "\n".join(res) + "\n\n"
            "## Divisão × número publicado (mesma medida)\n\n"
            "| Ano | Mineral | Empresa | Base de produção | Publicado | Diferença |\n|---|---|---|---:|---:|---:|\n"
            + "\n".join(f"| {l['ano']} | {l['mineral']} | {l['empresa']} | {br(l['producao_t'])} t | {br(l['publicado_em_t'])} t | "
                        f"{l['diferenca_base_vs_publicado']:+.0%} |" for l in dif)
            + "\n\nDiferenças acima de ±10% indicam onde a CFEM não representa bem a produção (ex.: Mosaic 2024–25 no fosfato; Serra Grande 2022 no ouro, "
              "em que o AMB tem ouro de outra origem). Nenhum número publicado substitui a divisão: ficam lado a lado.\n")
print(f"SALVO: {SAIDA} — {len(saida)} linhas de empresa, {len(est)} linhas de estado, {len(dif)} comparações com número publicado")
for l in dif:
    print(f"  {l['ano']} {l['mineral']:8s} {l['empresa'][:32]:32s} base {l['producao_t']:>12,.0f} t  publicado {l['publicado_em_t']:>12,.0f} t  {l['diferenca_base_vs_publicado']:+.1%}")
