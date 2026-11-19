# -*- coding: utf-8 -*-
"""Auditoria de unidades de medida nas bases da ANM (Squad 1 / Estudante 1 — Frente 1).

    python "Squad 1/Bases consolidadas/base_consolidada_work/scripts/auditoria_unidades_anm.py"

Lê os arquivos brutos como vieram da ANM (Squad 1/Dados brutos) e procura sinais de unidade trocada:

AMB (Produção Bruta e Beneficiada, todas as UFs, 2010 em diante)
  U1  unidade declarada diferente para a mesma substância (entre UFs ou entre anos);
  U2  série UF × substância × medida com ano fora da mediana dos outros anos por um fator perto de uma potência de 10
      (10, 100, 1000…) E com o valor em R$ na escala usual — o preço implícito muda pelo mesmo 10^k. Quantidade e valor
      que mudam juntos são produção real e não entram. Contido (sem valor) só com fator de 1000 ou mais;
  U4  preço implícito da UF fora da mediana das outras UFs no mesmo ano por 10^3 ou mais;
  U5  incoerências internas: venda ≫ produção, contido > produção na mesma unidade, beneficiada ≫ ROM.
CFEM (Goiás, 2022 em diante)
  C1  o mesmo processo e substância declarado em mais de uma unidade;
  C2  mês com preço implícito (R$ recolhido ÷ quantidade) fora da mediana do próprio processo por 10^2 ou mais;
  C3  a mesma substância declarada em unidades diferentes por processos diferentes (m3 × t, g × kg…).

Nada é corrigido: a saída é a lista de suspeitas, com o fator e a leitura provável, para revisão e para a pergunta à ANM.
CPF de pessoa física não sai no arquivo (só o processo).

Saídas: Squad 1/Auditoria e qualidade/auditoria_unidades_anm.csv e auditoria_unidades_anm.md
"""
import csv
import math
import os
import statistics
import sys
from collections import defaultdict, Counter

sys.stdout.reconfigure(encoding="utf-8")
AQUI = os.path.dirname(os.path.abspath(__file__))
SQ1 = os.path.abspath(os.path.join(AQUI, "..", "..", ".."))
BRUTOS = os.path.join(SQ1, "Dados brutos")
AMB = os.path.join(BRUTOS, "ANM - Anuário Mineral Brasileiro (AMB)")
CFEM = os.path.join(BRUTOS, "ANM - CFEM", "CFEM_Arrecadacao_2022_2026_GO.csv")
SAIDA = os.path.join(SQ1, "Auditoria e qualidade", "auditoria_unidades_anm.csv")
RESUMO = os.path.join(SQ1, "Auditoria e qualidade", "auditoria_unidades_anm.md")

MIN_OUTROS = 3          # anos (ou meses, ou UFs) de comparação com valor positivo
LIMIAR = 10 ** 0.85     # ~7x: abaixo disso não é suspeita de unidade
TOL = 0.15              # |log10(fator) - k| <= TOL conta como potência de 10 (10^k ± ~40%)
VALOR_MIN_RS = 1e5      # série/mês muito pequeno não entra (ruído de arredondamento)


def num(v):
    v = (v or "").strip()
    if not v or v == "-":
        return 0.0
    if "," in v:
        v = v.replace(".", "").replace(",", ".")
    try:
        return float(v)
    except ValueError:
        return 0.0


def ler(caminho, sep):
    with open(caminho, encoding="cp1252", newline="") as f:
        return list(csv.DictReader(f, delimiter=sep))


def mediana_outros(serie, chave):
    outros = [v for k, v in serie.items() if k != chave and v > 0]
    return statistics.median(outros) if len(outros) >= MIN_OUTROS else None


def classifica(fator):
    """('potência de 10', k) | ('salto', None) | None"""
    lg = math.log10(fator)
    if abs(lg) < math.log10(LIMIAR):
        return None
    k = round(lg)
    if k != 0 and abs(lg - k) <= TOL:
        return "potência de 10", k
    return "salto", None


def leitura(k, unidade):
    if k is None:
        return "salto grande sem fator redondo: mudança de produto, parada/retomada ou erro de digitação"
    if abs(k) == 3:
        return f"fator 10^{k}: típico de troca kg↔t ou g↔kg (unidade declarada: {unidade or '—'})"
    if abs(k) == 6:
        return f"fator 10^{k}: típico de troca g↔t ou mil t↔t (unidade declarada: {unidade or '—'})"
    return f"fator 10^{k}: vírgula decimal deslocada ou unidade trocada (unidade declarada: {unidade or '—'})"


achados = []


def achado(**k):
    base = dict(base="", verificacao="", uf="", substancia="", medida="", periodo="", processo="", valor=None, unidade="",
                referencia=None, fator=None, potencia_10="", tipo="", leitura="", relevancia_rs=None)
    base.update(k)
    for c in ("valor", "referencia", "fator", "relevancia_rs"):
        if isinstance(base[c], float):
            base[c] = round(base[c], 6 if c == "fator" else 2)
    achados.append(base)


# ---------------------------------------------------------------- AMB
MEDIDAS = {
    # produção compara com o valor total (venda + consumo + transferência): onde quase tudo é transferido para a usina da
    # própria empresa (nióbio), a venda é zero e não serve de controle
    "Producao_Bruta.csv": [("ROM", "Quantidade Produção - Minério ROM (t)", None,
                            ("Valor Venda (R$)", "Valor Transformação / Consumo / Utilização nesta mina (R$)",
                             "Valor Transferência para Transformação / Utilização / Consumo (R$)")),
                           ("venda", "Quantidade Venda (t)", None, "Valor Venda (R$)"),
                           ("contido", "Quantidade Contido", "Unidade de Medida - Contido", None)],
    "Producao_Beneficiada.csv": [("produção", "Quantidade Produção", "Unidade de Medida - Produção",
                                  ("Valor Venda (R$)", "Valor Consumo / Utilização na Usina (R$)",
                                   "Valor Transferência para Transformação / Utilização / Consumo (R$)")),
                                 ("venda", "Quantidade Venda", "Unidade de Medida - Venda", "Valor Venda (R$)"),
                                 ("contido", "Quantidade Contido", "Unidade de Medida - Contido", None)],
}
amb = {}
for arq, medidas in MEDIDAS.items():
    linhas = ler(os.path.join(AMB, arq), ",")
    amb[arq] = linhas
    nome = "AMB bruta" if "Bruta" in arq else "AMB beneficiada"
    # U1: unidades por substância
    for med, col_q, col_u, _ in medidas:
        if not col_u:
            continue
        unid = defaultdict(Counter)
        for l in linhas:
            if num(l[col_q]) > 0:
                unid[l["Substância Mineral"]][l[col_u].strip()] += 1
        for sub, c in unid.items():
            if len(c) > 1:
                maior = c.most_common(1)[0][0]
                for u, n in c.items():
                    if u == maior:
                        continue
                    exemplos = sorted({(l["Ano base"], l["UF"]) for l in linhas if l["Substância Mineral"] == sub
                                       and l[col_u].strip() == u and num(l[col_q]) > 0})
                    achado(base=nome, verificacao="U1 unidade diferente na mesma substância", substancia=sub, medida=med,
                           periodo="; ".join(f"{a}/{uf}" for a, uf in exemplos[:12]) + (" …" if len(exemplos) > 12 else ""),
                           unidade=f"{u} (em {n} linhas; o usual é {maior}, {c[maior]} linhas)", tipo="unidade",
                           leitura="conferir se a quantidade foi convertida ou só o rótulo mudou")
    # U2: séries por UF × substância × medida
    for med, col_q, col_u, col_v in medidas:
        serie = defaultdict(dict)
        unid = {}
        valor = defaultdict(dict)
        for l in linhas:
            k = (l["UF"], l["Substância Mineral"])
            serie[k][int(l["Ano base"])] = serie[k].get(int(l["Ano base"]), 0) + num(l[col_q])
            unid[k] = l[col_u].strip() if col_u else "t"
            if col_v:
                valor[k][int(l["Ano base"])] = valor[k].get(int(l["Ano base"]), 0) + sum(num(l[c]) for c in ((col_v,) if isinstance(col_v, str) else col_v))
        for (uf, sub), s in serie.items():
            for ano, v in s.items():
                if v <= 0:
                    continue
                ref = mediana_outros(s, ano)
                if not ref:
                    continue
                c = classifica(v / ref)
                if not c or c[0] != "potência de 10":
                    continue
                if col_v:
                    # assinatura de unidade trocada: a quantidade pula 10^k e o valor em R$ não acompanha (o preço implícito
                    # cai ou sobe pelo mesmo 10^k). Se o valor acompanha, é mudança real de produção e não entra.
                    vs = valor[(uf, sub)]
                    vr = mediana_outros(vs, ano)
                    va = vs.get(ano, 0)
                    if not vr or va <= 0:
                        if abs(c[1]) < 3:
                            continue
                        conf = "sem valor no ano para conferir"
                    else:
                        cp = classifica((v / ref) / (va / vr))
                        if not cp or cp[0] != "potência de 10" or cp[1] != c[1]:
                            continue
                        conf = f"valor em R$ ficou na escala usual (fator do valor {va / vr:.2g}): o preço implícito muda 10^{c[1]}"
                elif abs(c[1]) < 3:
                    continue  # contido não tem valor para conferir: só fatores de 1000 ou mais
                else:
                    conf = "contido sem valor para conferir"
                rel = max(valor[(uf, sub)].get(ano, 0), 0) if col_v else None
                achado(base=nome, verificacao="U2 quantidade fora de escala", uf=uf, substancia=sub, medida=med,
                       periodo=str(ano), valor=v, unidade=unid[(uf, sub)], referencia=ref, fator=v / ref,
                       potencia_10=f"10^{c[1]}", tipo=c[0], leitura=leitura(c[1], unid[(uf, sub)]) + "; " + conf,
                       relevancia_rs=rel)
    # U3/U4: preço implícito da venda
    med, col_q, col_u, col_v = medidas[1]
    preco = defaultdict(dict)
    vend = defaultdict(dict)
    unid = {}
    for l in linhas:
        q, v = num(l[col_q]), num(l[col_v])
        if q > 0 and v >= VALOR_MIN_RS:
            k = (l["UF"], l["Substância Mineral"])
            preco[k][int(l["Ano base"])] = v / q
            vend[k][int(l["Ano base"])] = v
            unid[k] = l[col_u].strip() if col_u else "t"
    # U3: preço da venda 100x ou mais fora do próprio histórico — preço de minério não varia assim de um ano para outro;
    # pega o caso em que a quantidade oscila e a mediana da quantidade não mostra o fator certo (talco GO 2025: kg como t)
    for (uf, sub), s in preco.items():
        for ano, p in s.items():
            ref = mediana_outros(s, ano)
            if not ref:
                continue
            c = classifica(p / ref)
            if c and abs(math.log10(p / ref)) >= 2:  # 100x ou mais; o histórico de preço oscila, então o fator nem sempre é redondo
                k = round(math.log10(p / ref))
                achado(base=nome, verificacao="U3 preço implícito fora do histórico da UF", uf=uf, substancia=sub, medida="R$/" + unid[(uf, sub)],
                       periodo=str(ano), valor=p, unidade="R$/" + unid[(uf, sub)], referencia=ref, fator=p / ref,
                       potencia_10=f"10^{k}" if c[0] == "potência de 10" else f"~10^{k}", tipo=c[0],
                       leitura=leitura(k, unid[(uf, sub)]) + f"; o preço muda ~10^{k} sem razão de mercado: a quantidade vendida está na escala errada",
                       relevancia_rs=vend[(uf, sub)][ano])
    por_ano = defaultdict(dict)
    for (uf, sub), s in preco.items():
        for ano, p in s.items():
            por_ano[(sub, ano, unid[(uf, sub)])][uf] = p
    for (sub, ano, u), s in por_ano.items():
        for uf, p in s.items():
            ref = mediana_outros(s, uf)
            if not ref:
                continue
            c = classifica(p / ref)
            if c and c[0] == "potência de 10" and abs(c[1]) >= 3:
                achado(base=nome, verificacao="U4 preço implícito fora das outras UFs", uf=uf, substancia=sub, medida="R$/" + u,
                       periodo=str(ano), valor=p, unidade="R$/" + u, referencia=ref, fator=p / ref, potencia_10=f"10^{c[1]}",
                       tipo=c[0], leitura=leitura(c[1], u) + " (comparado com a mediana das outras UFs)", relevancia_rs=vend[(uf, sub)][ano])

# U5: incoerências internas
for arq, linhas in amb.items():
    nome = "AMB bruta" if "Bruta" in arq else "AMB beneficiada"
    for l in linhas:
        if "Bruta" in arq:
            prod, venda, u_prod, u_venda = num(l["Quantidade Produção - Minério ROM (t)"]), num(l["Quantidade Venda (t)"]), "t", "t"
        else:
            prod, venda = num(l["Quantidade Produção"]), num(l["Quantidade Venda"])
            u_prod, u_venda = l["Unidade de Medida - Produção"].strip(), l["Unidade de Medida - Venda"].strip()
        cont, u_cont = num(l["Quantidade Contido"]), l["Unidade de Medida - Contido"].strip()
        val = num(l["Valor Venda (R$)"])
        if prod > 0 and venda > 5 * prod and u_prod == u_venda and val >= VALOR_MIN_RS:
            f = venda / prod
            c = classifica(f)
            achado(base=nome, verificacao="U5 venda maior que a produção", uf=l["UF"], substancia=l["Substância Mineral"], medida="venda ÷ produção",
                   periodo=l["Ano base"], valor=venda, unidade=u_venda, referencia=prod, fator=f,
                   potencia_10=f"10^{c[1]}" if c and c[1] else "", tipo=c[0] if c else "incoerência",
                   leitura="venda acima de 5x a produção do ano: estoque não explica; unidade ou digitação", relevancia_rs=val)
        if prod > 0 and cont > 1.001 * prod and u_cont == u_prod:
            f = cont / prod
            c = classifica(f)
            achado(base=nome, verificacao="U5 contido maior que a produção", uf=l["UF"], substancia=l["Substância Mineral"], medida="contido ÷ produção",
                   periodo=l["Ano base"], valor=cont, unidade=u_cont, referencia=prod, fator=f,
                   potencia_10=f"10^{c[1]}" if c and c[1] else "", tipo=c[0] if c else "incoerência",
                   leitura="o metal contido não pode passar do minério que o contém", relevancia_rs=val)
rom = {(l["Ano base"], l["UF"], l["Substância Mineral"]): num(l["Quantidade Produção - Minério ROM (t)"]) for l in amb["Producao_Bruta.csv"]}
for l in amb["Producao_Beneficiada.csv"]:
    k = (l["Ano base"], l["UF"], l["Substância Mineral"])
    b = num(l["Quantidade Produção"])
    if l["Unidade de Medida - Produção"].strip() == "t" and rom.get(k, 0) > 0 and b > 2 * rom[k] and b > 1000:
        f = b / rom[k]
        c = classifica(f)
        achado(base="AMB beneficiada × bruta", verificacao="U5 beneficiada maior que o ROM", uf=l["UF"], substancia=l["Substância Mineral"],
               medida="beneficiada ÷ ROM", periodo=l["Ano base"], valor=b, unidade="t", referencia=rom[k], fator=f,
               potencia_10=f"10^{c[1]}" if c and c[1] else "", tipo=c[0] if c else "incoerência",
               leitura="usina beneficiando mais do que a mina lavrou: compra de minério de outra UF, estoque, ou unidade",
               relevancia_rs=num(l["Valor Venda (R$)"]))

# ---------------------------------------------------------------- CFEM
cf = ler(CFEM, ";")
unid_proc = defaultdict(Counter)
mes = defaultdict(lambda: defaultdict(lambda: [0.0, 0.0]))
unid_sub = defaultdict(Counter)
for l in cf:
    k = (l["Processo"], l["AnoDoProcesso"], l["Substância"].strip())
    u = l["UnidadeDeMedida"].strip()
    q, v = num(l["QuantidadeComercializada"]), num(l["ValorRecolhido"])
    unid_proc[k][u] += 1
    unid_sub[l["Substância"].strip()][u] += 1
    m = mes[k][(int(l["Ano"]), int(l["Mês"]), u)]
    m[0] += q
    m[1] += v
for k, c in unid_proc.items():
    if len(c) > 1:
        rs = sum(v[1] for v in mes[k].values())
        achado(base="CFEM GO", verificacao="C1 processo com mais de uma unidade", substancia=k[2], processo=f"{k[0]}/{k[1]}",
               unidade="; ".join(f"{u} ({n} linhas)" for u, n in c.most_common()), tipo="unidade",
               leitura="a quantidade muda de unidade no mesmo processo: somar meses mistura unidades", relevancia_rs=rs)
for k, meses in mes.items():
    for u in {mm[2] for mm in meses}:
        precos = {(a, m): v / q for (a, m, uu), (q, v) in meses.items() if uu == u and q > 0 and v > 0}
        for am, p in precos.items():
            ref = mediana_outros(precos, am)
            if not ref:
                continue
            c = classifica(p / ref)
            q, v = meses[(am[0], am[1], u)]
            if c and c[0] == "potência de 10" and abs(c[1]) >= 2 and v >= 1000:
                achado(base="CFEM GO", verificacao="C2 mês com preço implícito fora do processo", substancia=k[2], processo=f"{k[0]}/{k[1]}",
                       medida="R$ recolhido ÷ quantidade", periodo=f"{am[0]}-{am[1]:02d}", valor=q, unidade=u,
                       referencia=v / ref, fator=ref / p, potencia_10=f"10^{-c[1]}", tipo=c[0],
                       leitura="quantidade do mês fora de escala em relação ao valor pago (valor = quantidade esperada pelo preço usual na coluna referencia); "
                               + leitura(-c[1], u).split(":", 1)[1].strip(), relevancia_rs=v)
for sub, c in unid_sub.items():
    if len(c) > 1:
        achado(base="CFEM GO", verificacao="C3 substância em unidades diferentes", substancia=sub,
               unidade="; ".join(f"{u} ({n} linhas)" for u, n in c.most_common()), tipo="unidade",
               leitura="somar a quantidade da substância entre processos mistura unidades; converter antes (m3→t pede densidade)")

CAMPOS = ["base", "verificacao", "uf", "substancia", "medida", "periodo", "processo", "valor", "unidade", "referencia", "fator",
          "potencia_10", "tipo", "leitura", "relevancia_rs"]
achados.sort(key=lambda a: (a["base"], a["verificacao"], -(a["relevancia_rs"] or 0)))
with open(SAIDA, "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=CAMPOS, delimiter=";", lineterminator="\r\n")
    w.writeheader()
    for a in achados:
        w.writerow({k: ("" if a[k] is None else a[k]) for k in CAMPOS})
cont = Counter((a["base"], a["verificacao"], a["tipo"]) for a in achados)
print(f"SALVO: {SAIDA} — {len(achados)} suspeitas")
for (b, v, t), n in sorted(cont.items()):
    print(f"  {b:24s} {v:48s} {t:16s} {n:5d}")
