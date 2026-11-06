# -*- coding: utf-8 -*-
"""Rateio da energia elétrica entre coprodutos, por valor (Squad 1 / Estudante 1 — Frente 1, auditoria).

    python "Squad 1/Bases consolidadas/base_consolidada_work/scripts/gerar_coprodutos.py"

Grava, na pasta do pacote do Squad 2 (documentacao/pacote_squad2/):
  - coprodutos_rateio_valor_2025.csv — uma linha por (operação, carga da CCEE, produto);
  - coprodutos_LEIA-ME.md — a regra, as fontes e o efeito sobre a intensidade usada no motor.
É chamado no fim de gerar_pacote_squad2.py, então é refeito sempre que o pacote é refeito.

Regra (hierarquia da ISO 14044 para alocação em sistemas multiproduto):
  1. separação física: carga da CCEE dedicada a um produto fica inteira nele;
  2. carga compartilhada: energia do produto i = energia da carga × valor_i / Σ valor;
  3. materialidade: coproduto com menos de 5% do valor da operação fica no produto principal;
  4. preço, nesta ordem: preço realizado publicado pela empresa; valor separado no AMB; preço médio de referência do ano;
  5. preços fixos do ano-base (2025): a intensidade não oscila com a cotação;
  6. conservação: a energia rateada soma exatamente a carga medida (conferido abaixo);
  7. o coproduto que recebe energia precisa de série de produção própria no motor, senão a energia dele some da previsão.

Só lê arquivos do repositório. Não altera a intensidade do Squad 2: a tabela é insumo para eles decidirem.
"""
import csv
import os
import sys
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8")
from caminhos import BASE, arquivo  # noqa: E402

PACOTE = os.path.join(BASE, "documentacao", "pacote_squad2")
INTERFACE = os.path.join(PACOTE, "interface_squad1_squad2.csv")
CCEE = next((p for p in (os.path.join(BASE, "..", "dados", "CCEE", "parcela_carga_consumo_2025_GO.csv"),
                          os.path.join(BASE, "dados", "CCEE", "parcela_carga_consumo_2025_GO.csv")) if os.path.exists(p)), None)
AMB_BENEF = arquivo("dados/ANM/producao_amb_ral/Producao_Beneficiada.csv")
ANO = "2025"
LIMIAR = 0.05
LB_POR_T = 2204.62262
ALUMINIO_MOTOR = os.path.join(BASE, "..", "..", "Squad 2", "intensidade_energetica", "coeficiente_estadual_para_modelo_v1.csv")

LUNDIN_PRECOS = ("Lundin Mining — Fourth Quarter and Full Year 2025 Results (19/02/2026): preço realizado de 2025, operações continuadas",
                 "https://lundinmining.com/news/lundin-mining-reports-fourth-quarter-and-full-year-2025-results")
LUNDIN_PRODUCAO = ("Lundin Mining — 2025 Production Results and 2026 Guidance (21/01/2026)",
                   "https://news.cision.com/lundin-mining-corporation/r/lundin-mining-announces-2025-production-results-and-2026-guidance,c4296017")
CMOC_NB = ("CMOC — resultado anual 2025 (via SMM, 27/03/2026)",
           "https://news.metal.com/newscontent/103830601/CMOC:-2025-Net-Profit-up-503-YoY,-Copper-Production-at-741,100-mt")

# Operações com mais de um produto e as cargas da CCEE de cada uma (sigla da parcela de carga, como vem no arquivo).
#   produto: (mineral_id, mineral, quantidade, unidade, preço, unidade do preço, fonte da quantidade, fonte do preço)
#   preço None = valor tirado do AMB (regra 4b), calculado abaixo
OPERACOES = [
    dict(operacao="Chapada (Alto Horizonte)", empresa="Mineração Maracá (Lundin Mining)", raiz="86902053",
         cargas={"MARACA MINERACAO": "compartilhada", "MARACÁ MINERAÇÃO - A": "compartilhada"},
         produtos=[("MIN_011", "Cobre", 43974.0, "t de Cu pago no concentrado", 4.91 * LB_POR_T, "US$/t (US$ 4,91/lb)", LUNDIN_PRODUCAO, LUNDIN_PRECOS),
                   ("MIN_023", "Ouro", 61331.0, "oz de Au no concentrado", 3662.0, "US$/oz", LUNDIN_PRODUCAO, LUNDIN_PRECOS)],
         nota="o ouro sai dentro do concentrado de cobre: a CFEM é paga só como cobre e o 'Ouro' do AMB de Goiás não o inclui "
              "(4,61 t em 2024 = Serra Grande + Mara Rosa); o valor do concentrado no AMB (R$ 3,26 bi) já contém o ouro"),
    dict(operacao="Complexo Catalão/Ouvidor (CMOC)", empresa="CMOC Brasil (NML e Copebrás)", raiz="26108898",
         cargas={"CMOC BRASIL - NIOBIO": "MIN_021", "CMOC NIOBIO - UC 218": "MIN_021", "NIOBIO MINA CATALAO": "MIN_021",
                 "COPEBRAS OUVIDOR": "MIN_049", "TAILINGS": "compartilhada"},
         produtos=[("MIN_021", "Nióbio", 10348.0, "t de produto de nióbio", None, "R$ (valor do AMB)", CMOC_NB, None),
                   ("MIN_049", "Fosfato", None, "t beneficiada (aba 12, rateio por CFEM)", None, "R$ (valor do AMB × participação na CFEM)", None, None)],
         nota="carga de rejeitos (TAILINGS) reprocessa o rejeito para nióbio e fosfato: é a única compartilhada; as demais têm produto pela sigla e pelo "
              "ramo da CCEE. O bário do AMB (ROM ~5,6 Mt/ano, sem produção beneficiada nem CFEM) é o mesmo minério contado de novo, não coproduto vendido"),
]
# Operações com coproduto abaixo do limiar de materialidade: a energia fica toda no produto principal (regra 3).
MATERIALIDADE = [
    dict(operacao="Complexo de Catalão (Mosaic)", empresa="Mosaic Fertilizantes", raiz="33931486", principal=("MIN_049", "Fosfato"),
         coprodutos=["MINÉRIO DE FERRO"], nota="magnetita (minério de ferro) recolhida à parte na CFEM"),
    dict(operacao="Barro Alto + Codemin (Anglo American)", empresa="Anglo American Níquel", raiz="42184226", principal=("MIN_022", "Níquel"),
         coprodutos=[], nota="o ferro da liga de ferroníquel não é pago e o cobalto é traço: a CFEM e o AMB registram só o níquel"),
    dict(operacao="Mineração Serra Grande (Crixás)", empresa="Mineração Serra Grande (Aura)", raiz="42445403", principal=("MIN_023", "Ouro"),
         coprodutos=["MINÉRIO DE PRATA", "PRATA"], nota="prata recolhida à parte na CFEM"),
]


def num_br(s):
    s = (s or "").strip()
    if not s or s == "-":
        return 0.0
    return float(s.replace(".", "").replace(",", ".")) if ("," in s and "." in s) else float(s.replace(",", "."))


# --- energia de 2025 por carga (CCEE) -------------------------------------------------------------------------------
if not CCEE:
    raise SystemExit("CCEE 2025 de Goiás não encontrada (Squad 1/dados/CCEE/parcela_carga_consumo_2025_GO.csv)")
energia, meses = defaultdict(float), defaultdict(set)
with open(CCEE, encoding="utf-8-sig") as f:
    for r in csv.DictReader(f, delimiter=";"):
        raiz = r["CNPJ_CARGA"][:8]
        energia[(raiz, r["SIGLA_PARCELA_CARGA"].strip())] += float(r["CONSUMO_TOTAL"] or 0)
        meses[raiz].add(r["MES_REFERENCIA"])
rotulo_meses = {raiz: f"{min(m)[:4]}-{min(m)[4:]} a {max(m)[:4]}-{max(m)[4:]} ({len(m)} meses)" for raiz, m in meses.items()}

# --- valor da produção de 2025 no AMB (venda + consumo na usina + transferência) -------------------------------------
valor_amb = defaultdict(float)
with open(AMB_BENEF, encoding="cp1252") as f:
    for r in csv.DictReader(f):
        if r["UF"] == "GO" and r["Ano base"] == ANO:
            valor_amb[r["Substância Mineral"]] += (num_br(r["Valor Venda (R$)"]) + num_br(r["Valor Consumo / Utilização na Usina (R$)"])
                                                   + num_br(r["Valor Transferência para Transformação / Utilização / Consumo (R$)"]))

# --- participação de cada empresa no mineral (aba 12, nível operação, beneficiada) ------------------------------------
part, prod_emp = defaultdict(float), defaultdict(float)
with open(INTERFACE, encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        if r["year"] == ANO and r["nivel_agregacao"] == "operacao" and r["production_basis"] == "beneficiada":
            part[(r["company_id"], r["mineral_id"])] += float(r["participacao_cfem_brl"] or 0)
            prod_emp[(r["company_id"], r["mineral_id"])] += float(r["production_t"] or 0)

# --- CFEM de 2025 por empresa e substância (para a materialidade) ----------------------------------------------------
cfem_sub = defaultdict(float)
with open(arquivo("dados/ANM/cfem/CFEM_Arrecadacao_2022_2026_GO.csv"), encoding="cp1252") as f:
    for r in csv.DictReader(f, delimiter=";"):
        if r["Ano"] == ANO:
            cfem_sub[(r["CPF_CNPJ"][:8], r["Substância"].strip().upper())] += num_br(r["ValorRecolhido"])

# --- intensidade que o motor usa hoje (para mostrar o efeito) ---------------------------------------------------------
motor = {}
if os.path.exists(ALUMINIO_MOTOR):
    with open(ALUMINIO_MOTOR, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            motor[r["mineral_id"]] = (float(r["energy_intensity_mwh_t"]), r["production_basis"])

CAMPOS = ["ano", "operacao", "empresa", "cnpj_raiz", "carga_ccee", "energia_carga_mwh", "periodo_energia", "tipo_carga", "regra", "mineral_id",
          "produto", "quantidade", "unidade_quantidade", "preco", "unidade_preco", "valor", "moeda_valor", "parcela_valor", "energia_rateada_mwh",
          "intensidade_rateada", "unidade_intensidade", "intensidade_motor_atual_mwh_t", "base_motor", "fonte_quantidade", "fonte_preco", "observacao"]
linhas = []
resumo = []

for op in OPERACOES:
    raiz = op["raiz"]
    cid = f"COM_CNPJ_{raiz}"
    # valores de cada produto da operação
    valores = {}
    prods = {}
    for mid, nome, q, uq, preco, up, fq, fp in op["produtos"]:
        if preco is not None:
            v, moeda = q * preco, "US$"
        elif mid == "MIN_021":
            v, moeda, fp = valor_amb["Nióbio"], "R$", ("AMB 2025 — valor da produção beneficiada de nióbio em Goiás (só a CMOC produz)",
                                                       "https://dadosabertos.anm.gov.br/AMB/Producao_Beneficiada.csv")
        else:
            s = part[(cid, mid)]
            v, moeda = valor_amb["Fosfato"] * s, "R$"
            q = prod_emp[(cid, mid)]
            fq = ("aba 12 (interface_squad1_squad2.csv): produção beneficiada estimada pela participação na CFEM", "documentacao/pacote_squad2/interface_squad1_squad2.csv")
            fp = (f"AMB 2025 — valor da produção beneficiada de fosfato em Goiás × participação da CMOC na CFEM de fosfato ({s:.1%})",
                  "https://dadosabertos.anm.gov.br/AMB/Producao_Beneficiada.csv")
        valores[mid] = (v, moeda)
        prods[mid] = (nome, q, uq, preco, up, fq, fp)
    moedas = {m for _, m in valores.values()}
    if len(moedas) != 1:
        raise SystemExit(f"{op['operacao']}: valores em moedas diferentes ({moedas}) — converter antes de ratear")
    total_v = sum(v for v, _ in valores.values())
    parcela = {mid: v / total_v for mid, (v, _) in valores.items()}

    soma_carga = soma_rateada = 0.0
    por_produto = defaultdict(float)
    for sigla, destino in op["cargas"].items():
        e = energia.get((raiz, sigla), 0.0)
        soma_carga += e
        alvo = parcela if destino == "compartilhada" else {destino: 1.0}
        for mid, p in alvo.items():
            nome, q, uq, preco, up, fq, fp = prods[mid]
            er = e * p
            soma_rateada += er
            por_produto[mid] += er
            linhas.append(dict(
                ano=ANO, operacao=op["operacao"], empresa=op["empresa"], cnpj_raiz=raiz, carga_ccee=sigla, energia_carga_mwh=round(e, 3),
                periodo_energia=rotulo_meses.get(raiz, ""), tipo_carga="compartilhada" if destino == "compartilhada" else "dedicada",
                regra="2 — rateio por valor" if destino == "compartilhada" else "1 — carga dedicada",
                mineral_id=mid, produto=nome, quantidade=round(q, 3) if q else "", unidade_quantidade=uq,
                preco=round(preco, 2) if preco else "", unidade_preco=up, valor=round(valores[mid][0], 2), moeda_valor=valores[mid][1],
                parcela_valor=round(parcela[mid], 6) if destino == "compartilhada" else 1.0, energia_rateada_mwh=round(er, 3),
                intensidade_rateada="", unidade_intensidade="", intensidade_motor_atual_mwh_t="", base_motor="",
                fonte_quantidade=f"{fq[0]} — {fq[1]}" if fq else "", fonte_preco=f"{fp[0]} — {fp[1]}" if fp else "", observacao=op["nota"]))
    if abs(soma_carga - soma_rateada) > 1e-6 * max(1.0, soma_carga):
        raise SystemExit(f"{op['operacao']}: energia rateada ({soma_rateada}) difere da carga medida ({soma_carga})")
    # intensidade rateada por produto, na última linha de cada produto
    for mid, er in por_produto.items():
        nome, q, uq, *_ = prods[mid]
        intens = er / q if q else None
        un = "MWh/" + uq.split(" ")[0] if q else ""
        for ln in reversed(linhas):
            if ln["operacao"] == op["operacao"] and ln["mineral_id"] == mid:
                ln["intensidade_rateada"] = round(intens, 6) if intens is not None else ""
                ln["unidade_intensidade"] = un + " (energia total do produto na operação)" if intens is not None else ""
                if mid in motor:
                    ln["intensidade_motor_atual_mwh_t"], ln["base_motor"] = round(motor[mid][0], 6), motor[mid][1]
                break
        resumo.append((op["operacao"], nome, er, intens, un, parcela.get(mid), motor.get(mid)))

for op in MATERIALIDADE:
    raiz = op["raiz"]
    tot = sum(v for (r, _), v in cfem_sub.items() if r == raiz)
    co = sum(cfem_sub.get((raiz, s), 0.0) for s in op["coprodutos"])
    share = co / tot if tot else 0.0
    if share >= LIMIAR:
        raise SystemExit(f"{op['operacao']}: coproduto com {share:.1%} da CFEM — acima do limiar de {LIMIAR:.0%}: levar para OPERACOES e ratear")
    e = sum(v for (r, _), v in energia.items() if r == raiz)
    mid, nome = op["principal"]
    linhas.append(dict(
        ano=ANO, operacao=op["operacao"], empresa=op["empresa"], cnpj_raiz=raiz, carga_ccee="todas as cargas do CNPJ", energia_carga_mwh=round(e, 3),
        periodo_energia=rotulo_meses.get(raiz, ""), tipo_carga="—", regra="3 — materialidade (coproduto < 5% do valor)", mineral_id=mid, produto=nome,
        quantidade="", unidade_quantidade="", preco="", unidade_preco="", valor=round(tot, 2), moeda_valor="R$ de CFEM (proxy do valor)",
        parcela_valor=round(1 - share, 6), energia_rateada_mwh=round(e, 3), intensidade_rateada="", unidade_intensidade="",
        intensidade_motor_atual_mwh_t=round(motor[mid][0], 6) if mid in motor else "", base_motor=motor[mid][1] if mid in motor else "",
        fonte_quantidade="", fonte_preco="CFEM 2025 de Goiás por substância — https://dadosabertos.anm.gov.br/CFEM/CFEM_Arrecadacao_2022_2026.csv",
        observacao=f"{op['nota']}: {share:.2%} da CFEM da empresa em 2025 — fica tudo no produto principal"))

with open(os.path.join(PACOTE, "coprodutos_rateio_valor_2025.csv"), "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=CAMPOS, delimiter=";", lineterminator="\r\n")
    w.writeheader()
    w.writerows(linhas)


def br(x, casas=0):
    return f"{x:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


tab = "\n".join(
    f"| {o} | {n} | {br(p * 100, 1) + '%' if p is not None else '—'} | {br(e)} | "
    + (f"{br(i, 2)} {u.replace('MWh/', 'MWh/')}" if i is not None else "—") + " | "
    + (f"{br(m[0], 2)} MWh/t ({m[1]})" if m else "fora do motor") + " |"
    for o, n, e, i, u, p, m in resumo)
leia = f"""# Coprodutos — rateio da energia por valor ({ANO})

Gerado por `base_consolidada_work/scripts/gerar_coprodutos.py` (chamado no fim de `gerar_pacote_squad2.py`). Tabela:
`coprodutos_rateio_valor_{ANO}.csv` (`;`, UTF-8), uma linha por operação × carga da CCEE × produto.

## Regra
1. **Separação física:** carga da CCEE dedicada a um produto fica inteira nele.
2. **Carga compartilhada:** energia do produto *i* = energia da carga × valor*ᵢ* / Σ valor.
3. **Materialidade:** coproduto com menos de {LIMIAR:.0%} do valor da operação fica no produto principal.
4. **Preço:** realizado pela empresa > valor separado no AMB > referência do ano (LME/LBMA × PTAX).
5. **Preços fixos de {ANO}** para a projeção: a intensidade não oscila com a cotação.
6. **Conservação:** a energia rateada soma exatamente a carga medida (o script para se não somar).
7. **O coproduto que recebe energia precisa de série de produção própria no motor**; senão a energia dele some da previsão.

## Resultado
| Operação | Produto | Parcela do valor (carga compartilhada) | Energia rateada (MWh) | Intensidade rateada | Intensidade no motor hoje |
|---|---|---|---|---|---|
{tab}

## Leitura para o Squad 2
- **Chapada:** hoje toda a energia vai para o cobre. Pelo valor, o ouro leva cerca de 1/3. Usar a intensidade rateada do cobre **sem** criar a linha
  do ouro de Chapada no motor tira essa energia da previsão. As duas formas coerentes: (a) cobre e ouro de Chapada como linhas separadas, cada um
  com a sua intensidade rateada; ou (b) manter "cobre equivalente" (toda a energia no cobre), como está, e registrar isso.
- **CMOC:** só a carga de rejeitos é compartilhada; o efeito no fosfato é pequeno. O nióbio está fora do motor: as cargas dele não entram na previsão.
- **Mosaic, Anglo e Serra Grande:** coproduto abaixo de {LIMIAR:.0%} do valor; nada muda.
- **Bário:** não é coproduto vendido; o ROM de bário do AMB é o mesmo minério do nióbio contado de novo — não somar com o ROM do nióbio.

Decidir entre (a) e (b) é do Squad 2: mexe na lista de minerais do motor. Esta tabela não altera nenhum parâmetro deles.
"""
open(os.path.join(PACOTE, "coprodutos_LEIA-ME.md"), "w", encoding="utf-8", newline="\n").write(leia)
print(f"SALVO: {PACOTE} (coprodutos_rateio_valor_{ANO}.csv: {len(linhas)} linhas; coprodutos_LEIA-ME.md)")
for o, n, e, i, u, p, m in resumo:
    print(f"  {o} — {n}: {br(e)} MWh" + (f", {br(i, 3)} {u}" if i is not None else "") + (f", parcela {p:.1%}" if p is not None else ""))
