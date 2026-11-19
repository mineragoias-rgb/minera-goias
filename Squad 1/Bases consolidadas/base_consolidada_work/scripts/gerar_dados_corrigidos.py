# -*- coding: utf-8 -*-
"""Bases corrigidas da ANM (Squad 1 / Estudante 1 — Frente 1).

    python "Squad 1/Bases consolidadas/base_consolidada_work/scripts/gerar_dados_corrigidos.py"

Lê os arquivos brutos (Squad 1/Dados brutos, que NÃO são alterados) e grava cópias corrigidas em Squad 1/Dados corrigidos,
no mesmo formato, nome e pasta da fonte — linha por linha igual ao bruto, exceto as células corrigidas. Cada célula alterada
vai para Squad 1/Dados corrigidos/REGISTRO_DE_ALTERACOES.md (e o mesmo em registro_alteracoes.csv), com o valor antes e
depois, a regra e a evidência. Rodar de novo depois de cada atualização dos brutos (o robô troca os arquivos todo mês).

Só entra correção com evidência forte e fator certo; o resto fica registrado como suspeita, sem alterar
(auditoria_unidades_anm.md). Regras:

  AMB-1  quantidade 1000x fora de escala (kg ou g declarado na unidade maior) em Goiás: o preço implícito da venda do ano
         (valor ÷ quantidade) fica a 10^±3 da mediana dos outros anos da mesma UF e substância (≥ 3 anos com venda
         ≥ R$ 100 mil) e o valor em R$ está na escala usual. As quantidades da linha (produção, venda, consumo,
         transferência) são divididas (ou multiplicadas) por 1000; valores em R$ e contido não mudam.
  CFEM-1 quantidade comercializada inválida em Goiás: o preço implícito da linha (R$ recolhido ÷ quantidade) fica a 1000x ou
         mais da mediana dos outros meses válidos do mesmo processo e unidade (≥ 3).
  CFEM-2 minerais do modelo: R$ recolhido ÷ t fora da faixa alíquota × valor por t de ROM … alíquota × valor por t de produto
         do AMB de Goiás no mesmo ano, com folga de 10x.
         Nas duas, a quantidade fica vazia e o valor recolhido não muda. Não se converte para outra unidade: o fator
         verdadeiro não é conhecido (ex.: Mara Rosa a partir de 2025).

Linhas repetidas da CFEM não são removidas (decisão com o Rodrigo: só com resposta da ANM).
"""
import csv
import hashlib
import io
import math
import os
import statistics
import sys
from collections import defaultdict

sys.stdout.reconfigure(encoding="utf-8")
AQUI = os.path.dirname(os.path.abspath(__file__))
SQ1 = os.path.abspath(os.path.join(AQUI, "..", "..", ".."))
BRUTOS = os.path.join(SQ1, "Dados brutos")
CORRIGIDOS = os.path.join(SQ1, "Dados corrigidos")
ARQ_AMB = [os.path.join("ANM - Anuário Mineral Brasileiro (AMB)", n) for n in ("Producao_Bruta.csv", "Producao_Beneficiada.csv")]
ARQ_CFEM = os.path.join("ANM - CFEM", "CFEM_Arrecadacao_2022_2026_GO.csv")
ENC = "cp1252"


def sha(caminho):
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


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


def fmt(x):
    """Número no estilo do arquivo da ANM (vírgula decimal, sem milhar)."""
    s = f"{x:.6f}".rstrip("0").rstrip(".")
    return s.replace(".", ",")


registro = []  # dicts com cada célula alterada
hash_antes = {a: sha(os.path.join(BRUTOS, a)) for a in ARQ_AMB + [ARQ_CFEM]}

# ------------------------------------------------------------------------------------------------ AMB-1
COLS_Q = {"Producao_Bruta.csv": ["Quantidade Produção - Minério ROM (t)", "Quantidade Venda (t)",
                                 "Quantidade Transformação / Consumo / Utilização (t)",
                                 "Quantidade Transferência para Transformação / Utilização / Consumo (t)"],
          "Producao_Beneficiada.csv": ["Quantidade Produção", "Quantidade Venda", "Quantidade Consumo/Utilização na Usina",
                                       "Quantidade Transferência para Transformação / Utilização / Consumo"]}
for arq in ARQ_AMB:
    nome = os.path.basename(arq)
    with open(os.path.join(BRUTOS, arq), encoding=ENC, newline="") as f:
        texto = f.read()
    linhas_txt = texto.split("\r\n")
    rows = list(csv.reader(io.StringIO(texto)))
    cab = rows[0]
    ix = {c: i for i, c in enumerate(cab)}
    col_qv = "Quantidade Venda (t)" if "Bruta" in nome else "Quantidade Venda"
    preco = defaultdict(dict)
    for i, r in enumerate(rows[1:], start=1):
        if len(r) != len(cab) or r[ix["UF"]] != "GO":
            continue
        q, v = num(r[ix[col_qv]]), num(r[ix["Valor Venda (R$)"]])
        if q > 0 and v >= 1e5:
            preco[r[ix["Substância Mineral"]]][int(r[ix["Ano base"]])] = (v / q, i)
    alterar = {}
    for sub, s in preco.items():
        for ano, (p, i) in s.items():
            outros = [pp for a, (pp, _) in s.items() if a != ano]
            if len(outros) < 3:
                continue
            ref = statistics.median(outros)
            lg = math.log10(p / ref)
            if abs(lg) >= 2.5 and round(lg) in (-3, 3):
                alterar[i] = (round(lg), p, ref)
    for i, (k, p, ref) in alterar.items():
        r = rows[i]
        fator = 10 ** k  # preço 1000x baixo -> quantidade 1000x alta -> multiplica a quantidade por 10^k
        for c in COLS_Q[nome]:
            antes = r[ix[c]]
            if num(antes) == 0:
                continue
            depois = fmt(num(antes) * fator)
            r[ix[c]] = depois
            registro.append(dict(regra="AMB-1", arquivo=arq.replace(os.sep, "/"), linha=i + 1, chave=f"{r[ix['Ano base']]} · {r[ix['UF']]} · {r[ix['Substância Mineral']]}",
                                 coluna=c, antes=antes, depois=depois,
                                 evidencia=f"preço da venda R$ {p:,.2f}/t contra mediana de R$ {ref:,.2f}/t nos outros anos (fator 10^{k}); valor em R$ mantido"))
        buf = io.StringIO()
        csv.writer(buf, quoting=csv.QUOTE_ALL, lineterminator="").writerow(r)
        linhas_txt[i] = buf.getvalue()
    destino = os.path.join(CORRIGIDOS, arq)
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    with open(destino, "w", encoding=ENC, newline="") as f:
        f.write("\r\n".join(linhas_txt))

# ------------------------------------------------------------------------------------------------ CFEM-1
with open(os.path.join(BRUTOS, ARQ_CFEM), encoding=ENC, newline="") as f:
    texto = f.read()
linhas_txt = texto.split("\r\n")
cab = linhas_txt[0].split(";")
ix = {c: i for i, c in enumerate(cab)}
campos = {}
por_proc = defaultdict(dict)
for i, l in enumerate(linhas_txt[1:], start=1):
    if not l:
        continue
    r = l.split(";")
    if len(r) != len(cab):
        continue
    q, v = num(r[ix["QuantidadeComercializada"]]), num(r[ix["ValorRecolhido"]])
    if q <= 0 or v <= 0:
        continue
    sub, u, ano = r[ix["Substância"]].strip(), r[ix["UnidadeDeMedida"]].strip(), r[ix["Ano"]]
    p = v / q
    campos[i] = (r, sub, u, ano, p)
    por_proc[(r[ix["Processo"]], r[ix["AnoDoProcesso"]], sub, u)][i] = p
# CFEM-2 primeiro, para os minerais do modelo: âncora no próprio AMB de Goiás (já com AMB-1). A CFEM é a alíquota sobre a
# receita, então R$ recolhido ÷ quantidade tem de ficar entre alíquota × (valor da beneficiada ÷ t de ROM) — quem declara
# minério — e alíquota × (valor da beneficiada ÷ t beneficiada) — quem declara produto —, com folga de 10x para cada lado.
# Fora disso, a quantidade está na escala errada. Pega o processo que declara errado o tempo todo (amianto da SAMA: ~1 t por
# mês pagando R$ 1 milhão) ou que trocou a unidade de vez (Mara Rosa a partir de 2025), que o próprio histórico não mostra.
# "OURO" é o metal: só vale o preço do produto. 2026 usa o AMB de 2025 (último ano publicado).
ANCORA = {  # substância da CFEM -> (mineral do AMB, alíquota, metal?)
    "OURO": ("Ouro", 0.015, True), "AMIANTO": ("Amianto", 0.02, False), "VERMICULITA": ("Vermiculita e Perlita", 0.02, False),
    "COBRE": ("Cobre", 0.02, False), "MINÉRIO DE COBRE": ("Cobre", 0.02, False), "NIÓBIO": ("Nióbio", 0.03, False),
    "FOSFATO": ("Fosfato", 0.02, False), "NÍQUEL": ("Níquel", 0.02, False), "MINÉRIO DE NÍQUEL": ("Níquel", 0.02, False),
    "BAUXITA": ("Alumínio (Bauxita)", 0.03, False), "MANGANÊS": ("Manganês", 0.03, False), "MINÉRIO DE MANGANÊS": ("Manganês", 0.03, False)}
PARA_T = {"t": 1.0, "kg": 1e-3, "g": 1e-6}
amb_go = defaultdict(lambda: [0.0, 0.0, 0.0])  # (mineral, ano) -> [valor beneficiada R$, t beneficiada, t ROM]
for arq in ARQ_AMB:
    with open(os.path.join(CORRIGIDOS, arq), encoding=ENC, newline="") as f:
        for l in csv.DictReader(f):
            if l["UF"] != "GO":
                continue
            k = (l["Substância Mineral"], int(l["Ano base"]))
            if "Bruta" in arq:
                amb_go[k][2] += num(l["Quantidade Produção - Minério ROM (t)"])
            else:
                amb_go[k][0] += sum(num(l[c]) for c in ("Valor Venda (R$)", "Valor Consumo / Utilização na Usina (R$)",
                                                        "Valor Transferência para Transformação / Utilização / Consumo (R$)"))
                amb_go[k][1] += num(l["Quantidade Produção"]) * PARA_T.get(l["Unidade de Medida - Produção"].strip(), 0.0)
invalidas = {}  # linha -> (regra, texto)
for i, (r, sub, u, ano, p) in campos.items():
    if sub not in ANCORA or u not in PARA_T:
        continue
    mineral, aliq, metal = ANCORA[sub]
    valor, t_benef, t_rom = amb_go.get((mineral, min(int(ano), 2025)), (0, 0, 0))
    if valor <= 0 or t_benef <= 0:
        continue
    alto = aliq * valor / t_benef * 10
    baixo = aliq * valor / (t_benef if metal or t_rom <= 0 else max(t_rom, t_benef)) / 10
    p_t = p / PARA_T[u]
    if not baixo <= p_t <= alto:
        invalidas[i] = ("CFEM-2", f"R$ {p_t:,.4g} recolhidos por t, fora da faixa de R$ {baixo:,.4g} a R$ {alto:,.4g}/t que o AMB de Goiás "
                                  f"dá para {mineral} em {min(int(ano), 2025)} (alíquota de {aliq:.1%} sobre o valor por t de ROM e de produto, folga de 10x)")
# CFEM-1: 1000x ou mais fora da mediana dos outros meses válidos do mesmo processo e unidade (>= 3): digitação, quantidade de
# preenchimento (0,01 t pagando R$ 1 milhão) ou unidade trocada num mês. 1000x e não 100x: o preço de areia, água e
# filito varia muito entre meses do mesmo processo (lote, produto, ajuste de recolhimento).
for i, (r, sub, u, ano, p) in campos.items():
    if i in invalidas:
        continue
    chave = (r[ix["Processo"]], r[ix["AnoDoProcesso"]], sub, u)
    outros = [pp for j, pp in por_proc[chave].items() if j != i and j not in invalidas]
    if len(outros) < 3:
        continue
    ref = statistics.median(outros)
    lg = math.log10(p / ref)
    if abs(lg) >= 3:
        invalidas[i] = ("CFEM-1", f"R$ {p:,.4g}/{u} contra mediana de R$ {ref:,.4g}/{u} nos outros meses do processo (fator {10 ** lg:,.3g})")
for i, (regra, texto) in sorted(invalidas.items()):
    r, sub, u, ano, p = campos[i]
    antes = r[ix["QuantidadeComercializada"]]
    r[ix["QuantidadeComercializada"]] = ""
    linhas_txt[i] = ";".join(r)
    registro.append(dict(regra=regra, arquivo=ARQ_CFEM.replace(os.sep, "/"), linha=i + 1,
                         chave=f"{r[ix['Ano']]}-{int(r[ix['Mês']]):02d} · processo {r[ix['Processo']]}/{r[ix['AnoDoProcesso']]} · {sub} · {r[ix['Município']].strip()}",
                         coluna="QuantidadeComercializada", antes=f"{antes} {u}", depois="(vazia)",
                         _rs=num(r[ix["ValorRecolhido"]]),
                         evidencia=f"R$ {num(r[ix['ValorRecolhido']]):,.2f} recolhidos; {texto}"))
destino = os.path.join(CORRIGIDOS, ARQ_CFEM)
os.makedirs(os.path.dirname(destino), exist_ok=True)
with open(destino, "w", encoding=ENC, newline="") as f:
    f.write("\r\n".join(linhas_txt))

# ------------------------------------------------------------------------------------------------ registro
for a in hash_antes:
    assert sha(os.path.join(BRUTOS, a)) == hash_antes[a], f"o bruto mudou durante a execução: {a}"
CAMPOS = ["regra", "arquivo", "linha", "chave", "coluna", "antes", "depois", "evidencia"]
with open(os.path.join(CORRIGIDOS, "registro_alteracoes.csv"), "w", encoding="utf-8-sig", newline="") as f:
    w = csv.DictWriter(f, fieldnames=CAMPOS, delimiter=";", lineterminator="\r\n", extrasaction="ignore")
    w.writeheader()
    w.writerows(registro)

md = io.StringIO()
p = lambda s="": md.write(s + "\n")
cfem = [x for x in registro if x["regra"].startswith("CFEM")]
amb = [x for x in registro if x["regra"] == "AMB-1"]
p("# Registro de alterações — bases corrigidas da ANM")
p()
p("Gerado por `Squad 1/Bases consolidadas/base_consolidada_work/scripts/gerar_dados_corrigidos.py` a partir dos brutos identificados pelo "
  "sha256 na tabela abaixo; a cadeia `scripts/atualizar_derivados.py` refaz tudo quando um bruto muda. "
  "**Não editar à mão**: rode o script de novo; este arquivo é refeito a cada execução.")
p()
p("- Os arquivos em `Squad 1/Dados brutos` ficam **exatamente como a ANM publica**. As cópias corrigidas ficam aqui, com o mesmo "
  "nome, pasta e formato; cada linha é igual à do bruto, exceto as células listadas abaixo.")
p("- Toda célula alterada está neste registro (e em `registro_alteracoes.csv`), com o valor antes e depois, a regra e a evidência. "
  "Linha = número da linha no arquivo, contando o cabeçalho.")
p("- Só entra correção com evidência forte e fator conhecido. Suspeitas sem fator certo ficam em "
  "`Squad 1/Auditoria e qualidade/auditoria_unidades_anm.md`, sem alterar o dado.")
p()
p("## Arquivos")
p()
p("| Arquivo | sha256 do bruto | sha256 do corrigido | Células alteradas |")
p("|---|---|---|---:|")
for a in hash_antes:
    p(f"| `{a.replace(os.sep, '/')}` | `{hash_antes[a][:16]}…` | `{sha(os.path.join(CORRIGIDOS, a))[:16]}…` | "
      f"{sum(1 for x in registro if x['arquivo'] == a.replace(os.sep, '/'))} |")
p()
p("## Regras")
p()
p("| Regra | O que corrige | Como |")
p("|---|---|---|")
p("| AMB-1 | Quantidade 1000x fora de escala no AMB de Goiás (kg ou g declarado na unidade maior) | O preço da venda do ano fica a 10^±3 da "
  "mediana dos outros anos (≥ 3 anos com venda ≥ R$ 100 mil) e o valor em R$ está na escala usual. As quantidades da linha são "
  "multiplicadas ou divididas por 1000; R$ e contido não mudam |")
p("| CFEM-1 | Quantidade comercializada inválida na CFEM de Goiás | O preço implícito da linha (R$ ÷ quantidade) fica a 1000x ou mais da "
  "mediana dos outros meses válidos do mesmo processo e unidade (≥ 3): digitação, quantidade de preenchimento ou unidade trocada num mês. "
  "A quantidade fica vazia — o fator verdadeiro não é conhecido — e o valor recolhido não muda |")
p("| CFEM-2 | Quantidade fora de escala nos minerais do modelo (ouro, amianto, vermiculita, cobre, nióbio, fosfato, níquel, bauxita, "
  "manganês) | A CFEM é a alíquota sobre a receita: R$ recolhido ÷ t tem de ficar entre alíquota × valor por t de ROM e alíquota × valor por t "
  "de produto, pelo AMB de Goiás do mesmo ano (2026 usa 2025), com folga de 10x. Fora disso, a quantidade fica vazia. Pega o processo que "
  "declara na escala errada o tempo todo ou que trocou a unidade de vez, que o próprio histórico não mostra |")
p()
p(f"## Alterações — AMB ({len(amb)} células)")
p()
p("| Linha | Ano · UF · Substância | Coluna | Antes | Depois | Evidência |")
p("|---:|---|---|---:|---:|---|")
for x in amb:
    p(f"| {x['linha']} | {x['chave']} | {x['coluna']} | {x['antes']} | {x['depois']} | {x['evidencia']} |")
p()
p(f"## Alterações — CFEM ({len(cfem)} células; R$ {sum(x['_rs'] for x in cfem):,.2f} recolhidos nessas linhas, que continuam somados)")
p()
por = defaultdict(list)
for x in cfem:
    por[x["chave"].split(" · ", 1)[1].rsplit(" · ", 1)[0]].append(x)
p("| Processo · Substância | Linhas | Meses |")
p("|---|---:|---|")
for k, xs in sorted(por.items(), key=lambda kv: -len(kv[1])):
    p(f"| {k} | {len(xs)} | {', '.join(sorted({x['chave'].split(' · ')[0] for x in xs}))} |")
p()
p("Todas as linhas:")
p()
p("| Linha | Mês · Processo · Substância · Município | Antes | Depois | Evidência |")
p("|---:|---|---:|---|---|")
for x in cfem:
    p(f"| {x['linha']} | {x['chave']} | {x['antes']} | {x['depois']} | {x['evidencia']} |")
p()
p("## Registrado e não corrigido")
p()
p("| Caso | Por que não foi corrigido |")
p("|---|---|")
p("| Nióbio, Goiás, beneficiada 2024–2025 (3,3–3,6 Mt contra ~25 kt antes; fator ~10^2) | O fator não é de unidade: a CMOC parece ter passado a "
  "declarar outro produto (minério tratado). Está entre as perguntas para a ANM em auditoria_unidades_anm.md |")
p("| Bário, Goiás, ROM (5,6 Mt/ano, valor zero; em 2023 igual ao ROM do nióbio) | É o mesmo minério de Catalão contado de novo, não unidade. "
  "Não somar com o ROM dos outros minerais |")
p("| Ferro, Goiás, beneficiada 2024 (1,22 Mt por R$ 274 mil) | Fator não é potência de 10 |")
p("| Titânio, Goiás, contido 2022 e ROM 2023 | Sem valor em R$ para confirmar o fator |")
p("| Linhas repetidas da CFEM | Removidas só com resposta da ANM (alinhado com o Rodrigo) |")
p("| Unidades diferentes para a mesma substância na CFEM (t, kg, m3, m2, l) | Converter m3 ou m2 em t pede densidade; fica para o pipeline |")
with open(os.path.join(CORRIGIDOS, "REGISTRO_DE_ALTERACOES.md"), "w", encoding="utf-8", newline="\n") as f:
    f.write(md.getvalue())
print(f"AMB: {len(amb)} células · CFEM: {len(cfem)} quantidades esvaziadas · registro em {os.path.join(CORRIGIDOS, 'REGISTRO_DE_ALTERACOES.md')}")
