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
# ------------------------------------------------------------------------------------------------ tratamentos no pipeline
# Tudo o que a base consolidada faz com os dados, além das cópias corrigidas acima: contado na planilha v18 e no pacote do
# Squad 2 a cada execução, para o registro não ficar desatualizado. Nada disso altera os arquivos brutos.
from collections import Counter
import openpyxl
DOC = os.path.join(SQ1, "Bases consolidadas", "documentacao")
wb = openpyxl.load_workbook(os.path.join(DOC, "prototipo_bases_consolidadas_v18.xlsx"), read_only=True)


def _aba(nome):
    it = wb[nome].iter_rows(min_row=4, values_only=True)
    cab = list(next(it))
    return cab, [r for r in it if r and r[0] is not None]


def fmtn(n):
    return format(n, ",").replace(",", ".")


cab8, f08 = _aba("08_fato_producao_energia")
i8 = {c: k for k, c in enumerate(cab8)}
trat, stat = Counter(), Counter()
cnpj = contido = 0
for r in f08:
    if r[i8["tratamento"]]:
        trat[(r[i8["source_id"]], r[i8["tratamento"]])] += 1
    stat[(r[i8["source_id"]], r[i8["status_validacao"]])] += 1
    n = r[i8["notas"]] or ""
    cnpj += "raiz do CNPJ pagador" in n
    contido += "contido expresso" in n
cab12, f12 = _aba("12_interface_squad1_squad2")
i12 = {c: k for k, c in enumerate(cab12)}
obs12 = Counter()
for r in f12:
    o = r[i12["observacao"]] or ""
    for chave in ("recolhimento atípico", "sem poligonal", "subitem de", "ROM sem abertura"):
        obs12[chave] += chave in o
op12 = sum(1 for r in f12 if r[i12["nivel_agregacao"]] == "operacao")
cw = {n: len(_aba(n)[1]) for n in ("01b_crosswalk_pente_fino", "02b_crosswalk_empresas", "05b_crosswalk_municipios", "06b_crosswalk_recmin")}
wb.close()
with open(os.path.join(DOC, "pacote_squad2", "coprodutos_rateio_valor_2025.csv"), encoding="utf-8-sig") as f:
    coprod = list(csv.DictReader(f, delimiter=";"))
FONTE = {"SRC_ANM_CFEM": "CFEM", "SRC_ANM_PROD_BRUTA": "AMB bruta", "SRC_ANM_PROD_BENEF": "AMB beneficiada"}
DESC = {"valido": "entra nas somas",
        "quantidade_excluida_da_soma_09b": "quantidade da CFEM corrompida ou implausível (R$ por unidade > 1.000x abaixo da mediana do mineral): fora da soma em t; o R$ fica (aba 09b)",
        "alerta_processo_09c": "processo com quantidade da CFEM implausível frente ao AMB: mantido e sinalizado (aba 09c)",
        "alerta_producao_repetida": "a mesma tonelagem aparece em outra linha da mesma UF e ano (coproduto, teor ou categoria): não somar entre essas linhas",
        "rom_minerio_associado": "ROM de subproduto (bário, cobalto, prata) que é a massa do minério de outro mineral, sem valor próprio: fora das somas de ROM entre minerais e da abertura por operação",
        "valor_nao_numerico": "valor não numérico na fonte"}
p("## Tratamentos feitos nas bases (pipeline da base consolidada)")
p()
p("Além das cópias corrigidas acima, o pipeline da base consolidada (`Squad 1/Bases consolidadas/base_consolidada_work/scripts/`, "
  "planilha `prototipo_bases_consolidadas_v18.xlsx`) trata os dados ao montar as abas. **Nenhum desses tratamentos altera os arquivos brutos**: "
  "o valor original fica na aba 08 (`valor_original`, `unidade_original`) e o tratamento fica registrado na própria linha (`tratamento`, "
  "`status_validacao`, `notas`). As contagens abaixo são lidas da planilha e do pacote do Squad 2 a cada execução deste script.")
p()
p("### Conversões de unidade (aba 08, coluna `tratamento`)")
p()
p("| Base | Tratamento | Linhas |")
p("|---|---|---:|")
for (src, t), n in sorted(trat.items(), key=lambda kv: (kv[0][0], -kv[1])):
    p(f"| {FONTE.get(src, src)} | {t} | {fmtn(n)} |")
p()
p("### Situação das linhas (aba 08, coluna `status_validacao`)")
p()
p("| Base | Status | Linhas | O que significa |")
p("|---|---|---:|---|")
for (src, st_), n in sorted(stat.items(), key=lambda kv: (kv[0][0], -kv[1])):
    p(f"| {FONTE.get(src, src)} | `{st_}` | {fmtn(n)} | {DESC.get(st_, '')} |")
p()
p("### Identificação e padronização")
p()
p("| Tratamento | Onde | Quantidade |")
p("|---|---|---:|")
p(f"| Grafias das substâncias das fontes ligadas às categorias da ANM | aba 01b | {fmtn(cw['01b_crosswalk_pente_fino'])} grafias |")
p(f"| Titulares e pagadores ligados a uma empresa pela raiz do CNPJ (CPF mascarado) | aba 02b | {fmtn(cw['02b_crosswalk_empresas'])} registros |")
p(f"| Empresa pela raiz do CNPJ pagador da CFEM quando o processo não tem titular no Cadastro | aba 08 (notas) | {fmtn(cnpj)} linhas |")
p(f"| Nomes de municípios das fontes ligados ao código do IBGE | aba 05b | {fmtn(cw['05b_crosswalk_municipios'])} grafias |")
p(f"| Ocorrências do RECMIN ligadas às categorias minerais | aba 06b | {fmtn(cw['06b_crosswalk_recmin'])} registros |")
p(f"| Contido com a indicação do que é medido (Cu, Ni, BaSO4…) | aba 08 (notas) | {fmtn(contido)} linhas |")
p("| Recortes de Goiás: CFEM (UF = GO) e Cadastro Mineiro (município de GO ou poligonal em GO) | `Dados brutos/LEIA-ME.md` | — |")
p()
p("### Divisão da produção por empresa e operação (aba 12 e pacote do Squad 2)")
p()
p("| Tratamento | Regra | Quantidade |")
p("|---|---|---:|")
p(f"| Total do estado (AMB) dividido por processo | parcela do processo na CFEM em R$ do mineral e ano; a CFEM em t fica só como sensibilidade "
  f"(`production_t_rateio_por_t`); margem de ±10% medida contra as empresas | {fmtn(op12)} linhas de operação |")
p(f"| Mês de recolhimento atípico trocado pela mediana do processo (só no rateio) | R$ > 3x e t > 10x a mediana dos outros meses, com R$/t abaixo "
  f"de metade do usual, em processos com 6 meses ou mais no ano | {fmtn(obs12['recolhimento atípico'])} linhas |")
p(f"| CFEM declarada como subitem somada ao mineral do AMB (ex.: minério de cobre → cobre) | crosswalk da 01b | {fmtn(obs12['subitem de'])} linhas |")
p(f"| Operação sem coordenadas (processo sem poligonal no SIGMINE de GO) | fica com o município da CFEM | {fmtn(obs12['sem poligonal'])} linhas |")
p(f"| ROM de minério associado sem abertura por operação | status `rom_minerio_associado` | {fmtn(obs12['ROM sem abertura'])} linhas de estado |")
p(f"| Coprodutos: energia da CCEE dividida por valor (ISO 14044) | carga dedicada fica com o produto; carga compartilhada por valor a preços de 2025; "
  f"coproduto abaixo de 5% fica no principal; energia conservada | {len(coprod)} linhas em `coprodutos_rateio_valor_2025.csv` |")
p("| Prévia de 2026 pela CFEM | jan–jun 2026 ÷ jan–jun 2025 por empresa; em t só se o R$/t fica estável (±30%), senão em R$ | `estimativa_2026_pela_cfem.csv` |")
p()
p("### Não feito de propósito")
p()
p("- Linhas repetidas da CFEM **não são removidas** (só com resposta da ANM).")
p("- m3, m2 e litro da CFEM **não são convertidos** para t: falta a densidade; ficam fora da soma em t.")
p("- Nenhum valor em R$ é alterado em nenhuma base.")
p()
p("## Registrado e não corrigido")
p()
p("| Caso | Por que não foi corrigido |")
p("|---|---|")
p("| Nióbio, Goiás, beneficiada 2024–2025 (3,3–3,6 Mt contra ~25 kt antes; fator ~10^2) | O fator não é de unidade: a CMOC parece ter passado a "
  "declarar outro produto (minério tratado). Está entre as perguntas para a ANM em auditoria_unidades_anm.md |")
p("| Bário, Goiás, ROM (5,6 Mt/ano, valor zero; em 2023 igual ao ROM do nióbio) | É o mesmo minério de Catalão contado de novo, não unidade: "
  "na base, status rom_minerio_associado (fora das somas de ROM e da abertura por operação) |")
p("| Ferro, Goiás, beneficiada 2024 (1,22 Mt por R$ 274 mil) | Fator não é potência de 10 |")
p("| Titânio, Goiás, contido 2022 e ROM 2023 | Sem valor em R$ para confirmar o fator |")
p("| Linhas repetidas da CFEM | Removidas só com resposta da ANM (alinhado com o Rodrigo) |")
p("| Unidades diferentes para a mesma substância na CFEM (t, kg, m3, m2, l) | Converter m3 ou m2 em t pede densidade; fica para o pipeline |")
with open(os.path.join(CORRIGIDOS, "REGISTRO_DE_ALTERACOES.md"), "w", encoding="utf-8", newline="\n") as f:
    f.write(md.getvalue())
print(f"AMB: {len(amb)} células · CFEM: {len(cfem)} quantidades esvaziadas · registro em {os.path.join(CORRIGIDOS, 'REGISTRO_DE_ALTERACOES.md')}")
