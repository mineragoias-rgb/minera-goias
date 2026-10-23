# -*- coding: utf-8 -*-
"""Base 3 -- Empresa x Mineral x Ano (Goias).

Pente fino da chave 'empresa'. Tres achados que definem a arquitetura desta base:

1. Ate a publicacao de out/2026, o campo CPF_CNPJ do CFEM vinha IRRECUPERAVELMENTE corrompido: 34.212
   das 38.854 linhas em notacao cientifica ('9,69944E+11'), ou seja, o CNPJ foi convertido para float em
   algum passo da exportacao e perdeu precisao (sobram ~6 digitos significativos de 14). Depois disso a
   ANM passou a publicar o CNPJ completo; os textos da planilha saem das contagens do arquivo em uso
   (qualidade_cfem.py).
   O valor AGRUPA de forma estavel (mesmo CNPJ -> mesma string), mas NAO IDENTIFICA a empresa,
   e colisoes entre CNPJs distintos sao possiveis. Alem disso o CFEM nao tem coluna de nome.
   => O CFEM NAO pode ser a fonte de identidade da empresa.

2. A ponte correta e o NUMERO DO PROCESSO: CFEM(processo) -> Cadastro Mineiro(processo->titular+CNPJ).
   Exige canonizar o formato ('860582' + ano 1995  <->  '860582/1995'  <->  '002393/1935').

3. A identidade da empresa vem da RAIZ DO CNPJ (8 primeiros digitos), nao do CNPJ completo:
   o sufixo /0001-19 e o estabelecimento (matriz/filial). Anglo American aparece como
   42.184.226/0019-69 (filial 19) -- agrupar pela raiz e o que faz 'a empresa' ser uma so.
   Titulares pessoa fisica tem CPF mascarado por LGPD ('***370285**'), entao so podem ser
   identificados por nome.
"""
import glob, json, re, struct, sys, unicodedata, zipfile
from collections import Counter, defaultdict
import pandas as pd

sys.stdout.reconfigure(encoding="utf-8")
from caminhos import BASE, TMP, arquivo  # caminhos relativos ao projeto — ver caminhos.py
import qualidade_cfem


def norm(s):
    s = re.sub(r"\s+", " ", str(s)).strip().upper()
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c))


SUFIXOS = [
    (r"\bS[/.]?\s?A\b\.?", "SA"), (r"\bSOCIEDADE ANONIMA\b", "SA"),
    (r"\bLIMITADA\b", "LTDA"), (r"\bLTDA\b\.?", "LTDA"),
    (r"\bEIRELI\b\.?", "EIRELI"), (r"\bME\b\.?", "ME"), (r"\bEPP\b\.?", "EPP"),
]


def norm_razao(s):
    """Normaliza razao social: maiusculo, sem acento, formas societarias padronizadas."""
    t = norm(s)
    t = re.sub(r"[^\w\s/&.-]", " ", t)
    for pat, rep in SUFIXOS:
        t = re.sub(pat, rep, t)
    t = re.sub(r"[.\-/]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def read_csv(path, sep=",", encoding="cp1252"):
    return pd.read_csv(path, sep=sep, encoding=encoding, encoding_errors="replace",
                        dtype=str, keep_default_na=False, engine="python", on_bad_lines="skip")


def split_multi(v):
    return [x.strip() for x in re.split(r"[,;]", re.sub(r"\s+", " ", str(v)).strip()) if x.strip()]


def read_dbf_bytes(data, encoding="utf-8"):
    n = struct.unpack("<I", data[4:8])[0]
    hl = struct.unpack("<H", data[8:10])[0]
    rl = struct.unpack("<H", data[10:12])[0]
    fields, pos = [], 32
    while data[pos] != 0x0D:
        d = data[pos:pos + 32]
        fields.append((d[:11].split(b"\x00", 1)[0].decode("ascii", "replace"), d[16]))
        pos += 32
    rows, pos = [], hl
    for _ in range(n):
        raw = data[pos:pos + rl]
        pos += rl
        if not raw or raw[0:1] == b"*":
            continue
        rp, row = 1, {}
        for nm, ln in fields:
            row[nm] = raw[rp:rp + ln].decode(encoding, "replace").strip()
            rp += ln
        rows.append(row)
    return rows


def to_num(s):
    s = str(s).strip()
    if not s or s in {"-", ",00"}:
        return None
    s = s.replace(".", "").replace(",", ".") if "," in s else s
    try:
        return float(s)
    except ValueError:
        return None


def canon_processo(proc, ano=""):
    """Formato canonico do processo minerario: '<numero sem zeros a esquerda>/<ano>'."""
    p = str(proc).strip()
    if "/" in p:
        left, right = p.split("/", 1)
        num = re.sub(r"\D", "", left).lstrip("0") or "0"
        yr = re.sub(r"\D", "", right)[:4]
    else:
        num = re.sub(r"\D", "", p).lstrip("0") or "0"
        yr = re.sub(r"\D", "", str(ano))[:4]
    return f"{num}/{yr}" if yr else num


# ---------------------------------------------------------------------------
# malha GO + filtro de municipio corrigido (mesma regra das Bases 1 e 2)
# ---------------------------------------------------------------------------
with zipfile.ZipFile(arquivo("dados/IBGE/GO_Municipios_2025.zip")) as z:
    _dbf = z.read([n for n in z.namelist() if n.lower().endswith(".dbf")][0])
    _mun = read_dbf_bytes(_dbf, "utf-8")
GO_MUN_BY_NORM = {norm(r["NM_MUN"]): r["CD_MUN"] for r in _mun}
MUN_NOME = {r["CD_MUN"]: r["NM_MUN"] for r in _mun}


def go_municipio_id(token):
    t = str(token).strip()
    m = re.search(r"-\s*([A-Za-z]{2})\s*$", t)
    if m:
        if m.group(1).upper() != "GO":
            return None
        t = t[:m.start()].strip()
    return GO_MUN_BY_NORM.get(norm(t))


# dimensao canonica de minerais da Base 1 (sem duplicar definicoes)
_b1 = open(f"{BASE}/base_consolidada_work/scripts/build_base1_mineral_ano.py", encoding="utf-8").read()
_ns = {}
exec(_b1.split("# 2) Carregar as fontes")[0], _ns)
RAW2KEY, MIN_DEF = _ns["RAW2KEY"], _ns["MIN_DEF"]
mineral_key_com_uso, eh_rocha = _ns["mineral_key_com_uso"], _ns["eh_rocha"]
# uso das rochas por processo e uso majoritário em GO, calculados pela Base 1 (que roda antes)
USO_ROCHAS = json.load(open(f"{TMP}/_uso_rochas.json", encoding="utf-8"))


def mineral_key(raw, uso=None):
    return mineral_key_com_uso(raw, uso, USO_ROCHAS["padrao"])[0]


def mineral_key_cfem(raw, proc_canon):
    """Rochas na CFEM: o uso vem do processo (a CFEM não tem campo de uso)."""
    uso = None
    if eh_rocha(raw):
        uso = USO_ROCHAS["proc_subst"].get(f"{proc_canon}|{norm(raw)}") or USO_ROCHAS["proc"].get(proc_canon)
    return mineral_key(raw, uso)


# ---------------------------------------------------------------------------
# 1) Cadastro Mineiro -- fonte da IDENTIDADE (titular + CNPJ) e do vinculo processo->empresa
# ---------------------------------------------------------------------------
registros = []  # dict por linha de titulo em GO
for path in sorted(glob.glob(arquivo("dados/ANM/cadastro_mineiro/*.csv"))):
    df = read_csv(path)
    muncol = next((c for c in df.columns if "unicipio" in c.lower()), None)
    titcol = next((c for c in df.columns if c.strip() == "Titular"), None)
    doccol = next((c for c in df.columns if "CPF/CNPJ" in c), None)
    proccol = next((c for c in df.columns if c.strip() == "Processo"), None)
    subcol = next((c for c in df.columns if "ubst" in c), None)
    fasecol = next((c for c in df.columns if "Fase" in c), None)
    usocol = next((c for c in df.columns if "Uso" in c), None)
    if not titcol:
        continue
    for _, r in df.iterrows():
        mids = [m for m in (go_municipio_id(t) for t in split_multi(r.get(muncol, ""))) if m]
        if not mids:
            continue
        registros.append(dict(
            processo=canon_processo(r.get(proccol, "")), titular=str(r.get(titcol, "")).strip(),
            doc=str(r.get(doccol, "")), municipios=mids, fase=str(r.get(fasecol, "")).strip(),
            substancias=split_multi(r.get(subcol, "")), usos=split_multi(r.get(usocol, "")) if usocol else [],
            arquivo=__import__("pathlib").Path(path).stem,
        ))
print(f"Cadastro Mineiro (GO): {len(registros)} linhas de título.")

# ---------------------------------------------------------------------------
# 2) Resolucao de identidade -- company_id pela raiz do CNPJ; nome como fallback
# ---------------------------------------------------------------------------
raiz2nomes = defaultdict(Counter)
nome2raizes = defaultdict(set)
for reg in registros:
    dd = re.sub(r"\D", "", reg["doc"])
    if len(dd) == 14:
        raiz = dd[:8]
        raiz2nomes[raiz][norm_razao(reg["titular"])] += 1
        nome2raizes[norm_razao(reg["titular"])].add(raiz)

# nome -> raiz, apenas quando o nome aponta para UMA unica raiz (senao e ambiguo)
nome_para_raiz = {n: list(rs)[0] for n, rs in nome2raizes.items() if len(rs) == 1}
nomes_ambiguos = {n: sorted(rs) for n, rs in nome2raizes.items() if len(rs) > 1}

crosswalk = []
EMP = {}  # company_id -> dict


def id_por_nome(nr):
    """ID deterministico a partir do nome normalizado.

    NAO usar hash() do Python: ele e randomizado por processo (PYTHONHASHSEED), o que faria o
    company_id MUDAR a cada execucao -- violando a regra de IDs estaveis do Contrato de Dados.
    """
    import hashlib
    return "COM_NOME_" + hashlib.sha1(nr.encode("utf-8")).hexdigest()[:8].upper()


_CPF = re.compile(r"(?<![\d/])\d{3}\.?\d{3}\.?\d{3}-?\d{2}(?![\d/])")


def mascarar_cpf(s):
    """LGPD: CPF (11 dígitos, com ou sem pontuação) dentro de um nome vira '***456789**', o padrão de máscara da ANM.

    Empresário individual costuma trazer o CPF no nome ('FULANO DE TAL 12345678901'). Só a EXIBIÇÃO é mascarada:
    company_id_de() continua recebendo o nome e o documento originais, então nenhum ID muda.
    """
    if not isinstance(s, str):
        return s
    return _CPF.sub(lambda m: "***" + m.group(0)[3:-2] + "**", s)


def company_id_de(titular, doc):
    """Retorna (company_id, tipo_pessoa, identificacao)."""
    dd = re.sub(r"\D", "", str(doc))
    nr = norm_razao(titular)
    if len(dd) == 14:
        return f"COM_CNPJ_{dd[:8]}", "PJ", "raiz_cnpj"
    if nr in nome_para_raiz:  # sem CNPJ nesta linha, mas o nome casa com uma raiz conhecida
        return f"COM_CNPJ_{nome_para_raiz[nr]}", "PJ", "nome_casado_com_raiz_cnpj"
    if len(dd) == 11:
        return f"COM_CPF_{dd}", "PF", "cpf"
    if dd and len(dd) == 6:  # CPF mascarado por LGPD ('***370285**')
        return id_por_nome(nr), "PF", "nome (CPF mascarado por LGPD)"
    return id_por_nome(nr), "indeterminado", "nome (sem documento)"


for reg in registros:
    cid, tipo, ident = company_id_de(reg["titular"], reg["doc"])
    reg["company_id"], reg["tipo_pessoa"], reg["identificacao"] = cid, tipo, ident
    e = EMP.setdefault(cid, dict(company_id=cid, tipo_pessoa=tipo, identificacao=ident,
                                 cnpj_raiz=cid.replace("COM_CNPJ_", "") if cid.startswith("COM_CNPJ_") else "",
                                 nomes=Counter(), docs=set(), processos=set(), municipios=set(),
                                 minerais=Counter(), fases=Counter()))
    e["nomes"][mascarar_cpf(reg["titular"].strip())] += 1  # só exibição; o ID acima já saiu do nome original
    if reg["doc"].strip():
        e["docs"].add(reg["doc"].strip())
    e["processos"].add(reg["processo"])
    e["municipios"].update(reg["municipios"])
    e["fases"][reg["fase"]] += 1
    _usos = reg["usos"] if len(reg["usos"]) == len(reg["substancias"]) else [""] * len(reg["substancias"])
    for s, u in zip(reg["substancias"], _usos):
        k = mineral_key(s, u)
        if k:
            e["minerais"][k] += 1

print(f"Empresas/titulares resolvidos: {len(EMP)}")
print(f"   por raiz de CNPJ: {sum(1 for e in EMP.values() if e['identificacao'] == 'raiz_cnpj')}")
print(f"   por nome casado com raiz: {sum(1 for e in EMP.values() if e['identificacao'].startswith('nome_casado'))}")
print(f"   pessoa fisica (CPF mascarado): {sum(1 for e in EMP.values() if 'mascarado' in e['identificacao'])}")
print(f"   sem documento (so nome): {sum(1 for e in EMP.values() if 'sem documento' in e['identificacao'])}")

# auditoria: raizes com mais de uma grafia + nomes com mais de uma raiz
for raiz, nomes in raiz2nomes.items():
    if len(nomes) > 1:
        crosswalk.append(dict(fonte="Cadastro_Mineiro(GO)", valor_original=" | ".join(sorted(nomes)),
                               chave_normalizada=f"raiz {raiz}", contagem=sum(nomes.values()),
                               atribuido=f"COM_CNPJ_{raiz}",
                               tipo_correspondencia="mesma_raiz_cnpj_varias_grafias (fundidas)"))
for nome, raizes in nomes_ambiguos.items():
    crosswalk.append(dict(fonte="Cadastro_Mineiro(GO)", valor_original=nome, chave_normalizada=nome,
                           contagem=0, atribuido="; ".join(f"COM_CNPJ_{r}" for r in raizes),
                           tipo_correspondencia="AMBIGUO: mesmo nome, raizes de CNPJ diferentes (NAO fundidas)"))

# ---------------------------------------------------------------------------
# 3) SIGMINE -- so tem NOME; casar por nome normalizado quando nao for ambiguo
# ---------------------------------------------------------------------------
with zipfile.ZipFile(arquivo("dados/ANM/sigmine/GO.zip")) as z:
    sig = read_dbf_bytes(z.read("GO.dbf"), "utf-8")
sig_por_empresa = defaultdict(set)
sig_sem_match = Counter()
for r in sig:
    nm = r.get("NOME", "").strip()
    if not nm:
        continue
    nr = norm_razao(nm)
    if nr in nome_para_raiz:
        sig_por_empresa[f"COM_CNPJ_{nome_para_raiz[nr]}"].add(canon_processo(r.get("PROCESSO", "")))
    elif nr in nomes_ambiguos:
        sig_sem_match[f"[ambiguo] {nm}"] += 1
    else:
        sig_sem_match[nm] += 1
print(f"\nSIGMINE: {len(sig)} processos; casados a uma empresa do Cadastro por nome: "
      f"{sum(len(v) for v in sig_por_empresa.values())}; sem par: {sum(sig_sem_match.values())} "
      f"({len(sig_sem_match)} nomes distintos)")
for nm, c in sig_sem_match.most_common(40):
    crosswalk.append(dict(fonte="SIGMINE(GO)", valor_original=nm, chave_normalizada=norm_razao(nm),
                           contagem=c, atribuido="SEM_PAR_NO_CADASTRO",
                           tipo_correspondencia="nome do SIGMINE sem titular equivalente no Cadastro Mineiro"))

# ---------------------------------------------------------------------------
# 4) CFEM -> empresa pela PONTE DO PROCESSO (o CNPJ do CFEM vinha corrompido ate out/2026, e o CFEM nao tem nome)
# ---------------------------------------------------------------------------
proc2company = {}
for reg in registros:
    proc2company.setdefault(reg["processo"], reg["company_id"])

cfem = read_csv(arquivo("dados/ANM/cfem/CFEM_Arrecadacao_2022_2026_GO.csv"), sep=";")
cfem["_proc"] = [canon_processo(p, a) for p, a in zip(cfem["Processo"], cfem["AnoDoProcesso"])]
cfem["_ano"] = pd.to_numeric(cfem["Ano"], errors="coerce")

cfem_agg = defaultdict(float)   # (company_id, mineral_key, ano) -> R$
cfem_mun = defaultdict(set)
casou = naocasou = 0
valor_casou = valor_naocasou = 0.0
procs_sem_par = Counter()
for _, r in cfem.iterrows():
    v = to_num(r["ValorRecolhido"]) or 0.0
    cid = proc2company.get(r["_proc"])
    if cid is None:
        # O processo nao existe nem no Cadastro Mineiro nem no SIGMINE (serie 96xxxx / regimes
        # nao cobertos pelos 13 arquivos de titulo). NAO descartar: o valor vai para um titular
        # explicito 'nao identificado', para que a soma da coluna continue batendo com o CFEM total.
        naocasou += 1
        valor_naocasou += v
        procs_sem_par[r["_proc"]] += 1
        cid = "COM_NAO_IDENTIFICADO"
    else:
        casou += 1
        valor_casou += v
    mk = mineral_key_cfem(r["Substância"], r["_proc"])
    ano = int(r["_ano"]) if pd.notna(r["_ano"]) else None
    if mk and ano:
        cfem_agg[(cid, mk, ano)] += v
        cod = str(r["CodigoMunicipio"]).split(".")[0]
        if cod in MUN_NOME:
            cfem_mun[(cid, mk, ano)].add(cod)

print(f"\nPonte CFEM -> empresa (via processo): {casou} linhas casadas, {naocasou} sem par "
      f"({100*casou/(casou+naocasou):.1f}% das linhas; {100*valor_casou/(valor_casou+valor_naocasou):.1f}% do valor em R$)")
print(f"   processos do CFEM sem titular no Cadastro Mineiro: {len(procs_sem_par)}")
# qualidade do CPF_CNPJ e cobertura da ponte: os textos da 02b e do catálogo (aba 07) saem daqui
qualidade = dict(qualidade_cfem.contar(cfem["CPF_CNPJ"]), ponte_linhas=casou, ponte_sem_par=naocasou,
                 ponte_valor=valor_casou, ponte_valor_sem_par=valor_naocasou)
with open(f"{TMP}/_cfem_qualidade.json", "w", encoding="utf-8") as f:
    json.dump(qualidade, f, ensure_ascii=False)
print("   CPF_CNPJ do CFEM:", {k: qualidade[k] for k in ("linhas", "cientifica", "mascarado", "completo")})
for p, c in procs_sem_par.most_common(30):
    crosswalk.append(dict(fonte="CFEM(GO)", valor_original=f"processo {p}", chave_normalizada=p, contagem=c,
                           atribuido="SEM_PAR_NO_CADASTRO",
                           tipo_correspondencia="processo do CFEM sem titular correspondente no Cadastro Mineiro"))

# ---------------------------------------------------------------------------
# 5) Montagem final -- Base 3 (empresa x mineral x ano)
# ---------------------------------------------------------------------------
# titular explicito para o CFEM que nao casou com nenhuma fonte de titulo
EMP["COM_NAO_IDENTIFICADO"] = dict(
    company_id="COM_NAO_IDENTIFICADO", tipo_pessoa="indeterminado",
    identificacao="processo do CFEM ausente do Cadastro Mineiro e do SIGMINE",
    cnpj_raiz="", nomes=Counter({"(titular não identificado — processo fora das bases de título)": 1}),
    docs=set(), processos=set(procs_sem_par), municipios=set(), minerais=Counter(), fases=Counter())

base3 = []
for cid, e in EMP.items():
    nome_principal = e["nomes"].most_common(1)[0][0]
    alternativos = [n for n, _ in e["nomes"].most_common()[1:]]
    cnpjs = sorted(e["docs"])
    anos_mins = {(mk, ano) for (c, mk, ano) in cfem_agg if c == cid}
    minerais_titulo = set(e["minerais"])
    combos = anos_mins | {(mk, None) for mk in minerais_titulo if mk not in {m for m, _ in anos_mins}}
    for mk, ano in sorted(combos, key=lambda x: (MIN_DEF[x[0]][0], (x[1] is None, x[1]))):
        v = cfem_agg.get((cid, mk, ano))
        muns = cfem_mun.get((cid, mk, ano), set()) or e["municipios"]
        base3.append(dict(
            company_id=cid, razao_social=nome_principal, cnpj_raiz=e["cnpj_raiz"],
            cnpj_completo_exemplo=cnpjs[0] if cnpjs else "", tipo_pessoa=e["tipo_pessoa"],
            identificacao=e["identificacao"], nomes_alternativos="; ".join(alternativos[:3]),
            mineral_id=mk, mineral_nome=MIN_DEF[mk][0], ano=ano,
            cfem_recolhido_brl=v,
            qtd_processos_titulo=e["minerais"].get(mk, 0),
            qtd_processos_total_empresa=len(e["processos"]),
            qtd_processos_sigmine=len(sig_por_empresa.get(cid, [])),
            municipios_atuacao="; ".join(sorted(MUN_NOME[m] for m in muns)[:6]),  # ordenar ANTES de cortar: set não tem ordem estável entre execuções
            qtd_municipios_mineral_ano=len(muns),  # total por trás da lista cortada em 6
            qtd_municipios=len(e["municipios"]),
            fase_predominante=e["fases"].most_common(1)[0][0] if e["fases"] else "",
            producao_t=None, consumo_energia_mwh=None, intensidade_mwh_t=None,
            source_ids="SRC_ANM_CADASTRO" + ("; SRC_ANM_CFEM" if v is not None else "") + ("; SRC_ANM_SIGMINE" if cid in sig_por_empresa else ""),
            observacao="",
        ))

print(f"\nBase 3 (empresa x mineral x ano): {len(base3)} linhas para {len(EMP)} empresas/titulares.")
with open(f"{TMP}/_base3_rows.json", "w", encoding="utf-8") as f:
    json.dump(base3, f, ensure_ascii=False)
# LGPD: a auditoria mostra os nomes como vieram das fontes — mascarar o CPF que vier dentro deles (IDs e contagens não mudam)
crosswalk = [{k: mascarar_cpf(v) for k, v in row.items()} for row in crosswalk]
with open(f"{TMP}/_crosswalk_emp.json", "w", encoding="utf-8") as f:
    json.dump(crosswalk, f, ensure_ascii=False)
emp_dim = [dict(company_id=e["company_id"], razao_social=e["nomes"].most_common(1)[0][0],
                cnpj_raiz=e["cnpj_raiz"], cnpj_completo_exemplo=sorted(e["docs"])[0] if e["docs"] else "",
                tipo_pessoa=e["tipo_pessoa"], identificacao=e["identificacao"],
                nomes_alternativos="; ".join(n for n, _ in e["nomes"].most_common()[1:][:3]),
                qtd_processos=len(e["processos"]), qtd_municipios=len(e["municipios"]),
                principais_minerais="; ".join(MIN_DEF[k][0] for k, _ in e["minerais"].most_common(4)),
                fase_predominante=e["fases"].most_common(1)[0][0] if e["fases"] else "")
           for e in EMP.values()]
emp_dim.sort(key=lambda x: -x["qtd_processos"])
with open(f"{TMP}/_emp_dim.json", "w", encoding="utf-8") as f:
    json.dump(emp_dim, f, ensure_ascii=False)
print("crosswalk empresa:", len(crosswalk), "linhas | dimensão:", len(emp_dim), "empresas")
