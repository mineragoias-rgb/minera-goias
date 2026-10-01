"""Base de Intensidade Energética do Setor Mineral de Goiás — v1 (Squad 2 / Estudante 2 — Sarah Lattouf).

Uso (na raiz do repositório):
    python "Squad 2/intensidade_energetica/build_intensidade.py"

Só lê arquivos que já estão no repositório e só escreve dentro desta pasta:
  - energia 2025 por unidade consumidora (CCEE, 12 meses) e produção declarada pelas empresas:
    payload do "Squad 1/dados/Panorama Mineracao Goias.html" (chaves ee_cargas e coef);
  - CCEE bruta jun–dez/2025 ("Squad 1/dados/CCEE/parcela_carga_consumo_2025_GO.csv"), usada só como checagem;
  - produção da ANM por operação (Squad 1, aba 12): "Squad 1/Bases consolidadas/documentacao/pacote_squad2/interface_squad1_squad2.csv";
  - benchmarks do motor (Federico): "Squad 2/modello_reale/parameters/energy_intensity.csv".

Fórmula (EPE, Atlas da Eficiência Energética): consumo específico = consumo de energia / produção física,
com energia e produção da mesma entidade e do mesmo ano sempre que possível.
"""
import csv
import json
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
PANORAMA = ROOT / "Squad 1" / "dados" / "Panorama Mineracao Goias.html"
CCEE_2025 = ROOT / "Squad 1" / "dados" / "CCEE" / "parcela_carga_consumo_2025_GO.csv"
INTERFACE = ROOT / "Squad 1" / "Bases consolidadas" / "documentacao" / "pacote_squad2" / "interface_squad1_squad2.csv"
BENCH = ROOT / "Squad 2" / "modello_reale" / "parameters" / "energy_intensity.csv"

VERSAO = "v1"
DATA_ACESSO = "2026-09-21"
RESPONSAVEL = "Squad 2 / Estudante 2 — Sarah Lattouf"

SOURCES = {
    "SRC_CCEE_PARCELA_CARGA": ("https://dadosabertos.ccee.org.br/dataset/parcela_carga_consumo", "oficial"),
    "SRC_ANM_PROD_BENEF": ("https://dadosabertos.anm.gov.br/AMB/Producao_Beneficiada.csv", "oficial"),
    "SRC_ANM_CFEM": ("https://dadosabertos.anm.gov.br/CFEM/CFEM_Arrecadacao_2022_2026.csv", "oficial"),
    "SRC_FGV_EPGE_001": ("Squad 2/modello_reale/parameters/energy_intensity.csv", "setorial"),
}

ROTA_PAINEL = "texto do Panorama Mineração Goiás (Squad 1), seção de coeficientes energéticos"
SEM_ROTA = "rota não levantada nesta versão: sem fonte documental; ver ramo_atividade_ccee"

# Uma entrada por operação da tabela de coeficientes do painel (chave `pos`).
# cnpj: raiz do CNPJ (8 dígitos) — liga a carga da CCEE ao company_id do Squad 1 (COM_CNPJ_<raiz>) sem depender do nome.
# cargas: SIGLA_PARCELA_CARGA da CCEE atribuídas à operação.
# operation_id: processo principal da operação na aba 12 (maior participação na CFEM do mineral no município em 2025).
OPERACOES = {
    1: dict(mineral_id="MIN_022", cnpj="42184226", municipio="Barro Alto; Niquelândia",
            cargas=["ANGLO AMERICAN BARRO", "ANGLO AMERICAN (CODE"], operation_id="AGG_COM_CNPJ_42184226_NI",
            processos="960146/2003; 960795/1982", basis="conteudo_mineral", tecnologia="metalurgia_forno_eletrico_ferroniquel",
            rota="Metalurgia: forno elétrico reduzindo laterita a ferroníquel",
            tec_status=ROTA_PAINEL),
    2: dict(mineral_id="MIN_011", cnpj="86902053", municipio="Alto Horizonte",
            cargas=["MARACA MINERACAO", "MARACÁ MINERAÇÃO - A"], operation_id="OPE_808923_1974",
            processos="808923/1974; 860273/2003", basis="conteudo_mineral", tecnologia="flotacao_concentrado",
            rota="Concentra por flotação e embarca o concentrado (sem metalurgia local)",
            tec_status=ROTA_PAINEL),
    3: dict(mineral_id="MIN_021", cnpj="26108898", municipio="Catalão; Ouvidor",
            cargas=["CMOC BRASIL - NIOBIO", "CMOC NIOBIO - UC 218", "NIOBIO MINA CATALAO", "TAILINGS", "COPEBRAS OUVIDOR"],
            operation_id="OPE_803343_1973", processos="803343/1973; 801244/1968; 860402/2001; 804513/1968; 801560/1968",
            basis="produto", tecnologia="nao_levantada_v1",
            rota="",
            tec_status=SEM_ROTA),
    4: dict(mineral_id="MIN_049", cnpj="33931486", municipio="Catalão",
            cargas=["MOSAIC FERTILIZANTES"], operation_id="OPE_801562_1968",
            processos="801562/1968; 9291/1967", basis="capacidade", tecnologia="nao_levantada_v1",
            rota="",
            tec_status=SEM_ROTA),
    5: dict(mineral_id="MIN_023", cnpj="42445403", municipio="Crixás",
            cargas=["MSG MIN. SERRA GRAND"], operation_id="", processos="960658/1987", basis="conteudo_mineral",
            tecnologia="nao_levantada_v1",
            rota="",
            tec_status=SEM_ROTA),
    6: dict(mineral_id="MIN_023", cnpj="42799486", municipio="Mara Rosa",
            cargas=["Hochschild Amarillo"], operation_id="OPE_861241_1980",
            processos="861241/1980; 862000/1984; 860952/1980", basis="conteudo_mineral",
            tecnologia="nao_levantada_v1",
            rota="",
            tec_status=SEM_ROTA),
    7: dict(mineral_id="MIN_033", cnpj="15104599", municipio="Minaçu",
            cargas=["SAMA-MINACU-GO"], operation_id="OPE_850037_1975", processos="850037/1975", basis="produto",
            tecnologia="nao_levantada_v1",
            rota="",
            tec_status=SEM_ROTA),
    8: dict(mineral_id="MIN_020", cnpj="08842895", municipio="Minaçu",
            cargas=["Mineracao Serra Verd"], operation_id="OPE_861427_2010", processos="861427/2010; 861426/2010",
            basis="exportacao", tecnologia="nao_levantada_v1",
            rota="",
            tec_status=SEM_ROTA),
}

MINERAL_NAMES = {}


def payload():
    html = PANORAMA.read_text(encoding="utf-8")
    m = re.search(r'<script[^>]*id="payload"[^>]*>(.*?)</script>', html, re.S)
    if not m:
        raise ValueError("payload do Panorama não encontrado")
    return json.loads(m[1])


def energia_por_carga(d):
    """SIGLA_PARCELA_CARGA → (consumo 2025 em MWh, meses com registro, capacidade em MW), do painel do Squad 1."""
    return {c["SIGLA_PARCELA_CARGA"]: (c["consumo_mwh"], c["meses"], c["capacidade_mw"]) for c in d["ee_cargas"]}


def ccee_bruta_2025():
    """Soma jun–dez/2025 por (raiz CNPJ, sigla) direto do arquivo bruto da CCEE — só para checagem."""
    soma, meses = defaultdict(float), defaultdict(set)
    with open(CCEE_2025, encoding="utf-8-sig") as f:
        for r in csv.DictReader(f, delimiter=";"):
            k = (r["CNPJ_CARGA"][:8], r["SIGLA_PARCELA_CARGA"])
            soma[k] += float(r["CONSUMO_TOTAL"])
            meses[k].add(r["MES_REFERENCIA"])
    return soma, meses


def interface_rows():
    with open(INTERFACE, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        MINERAL_NAMES[r["mineral_id"]] = r["mineral_name"]
    return rows


def producao_anm(rows, cnpj, mineral_id, ano=2025, basis="beneficiada"):
    """Produção da aba 12 (nível operação, estimada por rateio da CFEM) do titular no mineral e ano, e a parcela do estado."""
    ops = [r for r in rows if r["nivel_agregacao"] == "operacao" and r["company_id"] == f"COM_CNPJ_{cnpj}"
           and r["mineral_id"] == mineral_id and r["year"] == str(ano) and r["production_basis"] == basis]
    estado = [r for r in rows if r["nivel_agregacao"] == "estado" and r["mineral_id"] == mineral_id
              and r["year"] == str(ano) and r["production_basis"] == basis]
    total_op = sum(float(r["production_t"]) for r in ops)
    total_estado = sum(float(r["production_t"]) for r in estado)
    alerta = any(r["status_validacao"] == "estimativa_com_alerta_09c" for r in ops)
    faixa = []
    for r in ops:
        if r["production_t_rateio_por_t"]:
            faixa.append(float(r["production_t_rateio_por_t"]))
    alt = sum(faixa) if len(faixa) == len(ops) and ops else None
    return total_op, total_estado, alerta, alt, sorted({r["processo_anm"] for r in ops})


def producao_t(qtd, un):
    """Converte a produção declarada para toneladas (contrato: production_t em t)."""
    if un.startswith("kg"):
        return qtd / 1000.0
    return qtd


def linha_base(**kw):
    campos = dict.fromkeys(CAMPOS, "")
    campos.update(kw)
    for k in ("production_t", "energy_mwh", "energy_intensity_mwh_t", "intensidade_valor", "producao_valor"):
        if isinstance(campos[k], float):
            campos[k] = round(campos[k], 6)
    return campos


CAMPOS = [
    "intensity_id", "mineral_id", "mineral_name", "company_id", "empresa", "operation_id", "processos_anm", "operacao",
    "municipio", "nivel", "tecnologia", "rota_tecnologica", "tecnologia_status", "ramo_atividade_ccee", "project_id",
    "produto", "production_basis", "producao_valor", "producao_unidade", "production_t", "ano_producao",
    "energy_mwh", "ano_energia", "cargas_ccee",
    "energy_intensity_mwh_t", "unidade", "intensidade_valor", "intensidade_unidade",
    "natureza_dado", "valor_observado_estimado", "natureza_energia", "natureza_producao", "compatibilidade_temporal", "confianca",
    "year", "periodo_referencia", "source_id", "source_url", "fonte_producao", "fonte_producao_url", "tipo_fonte",
    "data_acesso", "metodo_estimacao", "erro_estimativa_intervalo", "checagem_ccee_bruta",
    "status_validacao", "responsavel_validacao", "usar_no_motor", "observacao", "versao_base",
]


def build():
    d = payload()
    cargas = energia_por_carga(d)
    bruta, bruta_meses = ccee_bruta_2025()
    rows = interface_rows()
    coef = {c["pos"]: c for c in d["coef"]}
    base = []
    n = 0

    def nid():
        nonlocal n
        n += 1
        return f"INT_{n:03d}"

    def checagem(cnpj, siglas, energia_12m):
        jd = sum(bruta.get((cnpj, s), 0.0) for s in siglas)
        meses = set().union(*[bruta_meses.get((cnpj, s), set()) for s in siglas])
        if not meses:
            return "sem registro no arquivo bruto do repositório"
        anual = jd / len(meses) * 12
        return (f"jun–dez/2025 no arquivo bruto: {jd:,.0f} MWh em {len(meses)} meses; anualizado {anual:,.0f} MWh "
                f"({(anual / energia_12m - 1) * 100:+.1f}% contra os 12 meses do painel)")

    for pos, op in OPERACOES.items():
        c = coef[pos]
        mineral = MINERAL_NAMES[op["mineral_id"]]
        company = f"COM_CNPJ_{op['cnpj']}"
        siglas = op["cargas"]
        # CMOC: a energia do CNPJ inteiro inclui a planta de fosfato (Copebrás) — teto; a linha seguinte tira essa carga.
        energia = sum(cargas[s][0] for s in siglas)
        assert abs(energia - c["energia_mwh"]) < 1, (pos, energia, c["energia_mwh"])
        prod_t = producao_t(c["qtd"], c["un"])
        mesmo_ano = c["ano"] == 2025
        natureza = "calculado"
        if op["basis"] in ("capacidade", "exportacao"):
            natureza = "estimado"
        obs = c["detalhe"]
        if pos == 3:
            obs += "; teto: toda a energia do CNPJ (inclusive a carga Copebrás, de fosfato) atribuída ao nióbio"
        base.append(linha_base(
            intensity_id=nid(), mineral_id=op["mineral_id"], mineral_name=mineral, company_id=company, empresa=c["empresa"],
            operation_id=op["operation_id"], processos_anm=op["processos"], operacao=c["operacao"], municipio=op["municipio"],
            nivel="operacao_empresa", tecnologia=op["tecnologia"], rota_tecnologica=op["rota"], tecnologia_status=op["tec_status"],
            produto=c["produto"], production_basis=op["basis"], producao_valor=float(c["qtd"]), producao_unidade=c["un"],
            production_t=float(prod_t), ano_producao=c["ano"], energy_mwh=float(energia), ano_energia=2025,
            cargas_ccee="; ".join(siglas),
            energy_intensity_mwh_t=energia / prod_t, intensidade_valor=float(c["coef"]), intensidade_unidade=c["coef_un"],
            natureza_dado=natureza, natureza_energia="observado",
            natureza_producao={"capacidade": "capacidade_declarada", "exportacao": "exportacao_declarada"}.get(op["basis"], "declarado_empresa"),
            compatibilidade_temporal="mesmo_ano" if mesmo_ano else f"anos_diferentes (produção {c['ano']}, energia 2025)",
            confianca=c["conf"], year=2025, periodo_referencia="2025",
            source_id="SRC_CCEE_PARCELA_CARGA; SRC_EMPRESA_RELATORIO", source_url=SOURCES["SRC_CCEE_PARCELA_CARGA"][0],
            fonte_producao=c["fonte"], fonte_producao_url=c["url"], tipo_fonte="oficial; companhia" if "Report" in c["fonte"] or "Results" in c["fonte"] else "oficial; imprensa",
            data_acesso=DATA_ACESSO,
            metodo_estimacao="" if natureza == "calculado" else f"denominador = {op['basis']} declarada, não produção medida do ano",
            checagem_ccee_bruta=checagem(op["cnpj"], siglas, energia),
            status_validacao="calculado_conferido_com_painel", responsavel_validacao=RESPONSAVEL, observacao=obs, versao_base=VERSAO,
        ))

        # Detalhe por unidade consumidora (Anglo: duas plantas com produção publicada separadamente).
        if pos == 1:
            partes = [("ANGLO AMERICAN BARRO", "Barro Alto", 32400.0, "OPE_960146_2003", "960146/2003"),
                      ("ANGLO AMERICAN (CODE", "Codemin (Niquelândia)", 7300.0, "", "960795/1982")]
            for sigla, nome, qtd, ope, proc in partes:
                e = cargas[sigla][0]
                base.append(linha_base(
                    intensity_id=nid(), mineral_id=op["mineral_id"], mineral_name=mineral, company_id=company, empresa=c["empresa"],
                    operation_id=ope, processos_anm=proc, operacao=nome, municipio=nome.split("(")[-1].rstrip(")") if "(" in nome else nome,
                    nivel="unidade_consumidora", tecnologia=op["tecnologia"], rota_tecnologica=op["rota"], tecnologia_status=op["tec_status"],
                    produto=c["produto"], production_basis="conteudo_mineral", producao_valor=qtd, producao_unidade="t Ni",
                    production_t=qtd, ano_producao=2025, energy_mwh=float(e), ano_energia=2025, cargas_ccee=sigla,
                    energy_intensity_mwh_t=e / qtd, intensidade_valor=e / qtd, intensidade_unidade="MWh/t",
                    natureza_dado="calculado", natureza_energia="observado", natureza_producao="declarado_empresa",
                    compatibilidade_temporal="mesmo_ano", confianca="alta", year=2025, periodo_referencia="2025",
                    source_id="SRC_CCEE_PARCELA_CARGA; SRC_EMPRESA_RELATORIO", source_url=SOURCES["SRC_CCEE_PARCELA_CARGA"][0],
                    fonte_producao=c["fonte"], fonte_producao_url=c["url"], tipo_fonte="oficial; companhia", data_acesso=DATA_ACESSO,
                    checagem_ccee_bruta=checagem(op["cnpj"], [sigla], e),
                    status_validacao="calculado", responsavel_validacao=RESPONSAVEL,
                    observacao=("Codemin sem operation_id na aba 12 (processo sem poligonal no SIGMINE); " if not ope else "")
                    + "produção por planta do mesmo relatório da Anglo American", versao_base=VERSAO,
                ))

        # CMOC: só as cargas de nióbio (sem a Copebrás, de fosfato, e sem a de rejeitos).
        if pos == 3:
            nb = ["CMOC BRASIL - NIOBIO", "CMOC NIOBIO - UC 218", "NIOBIO MINA CATALAO"]
            e = sum(cargas[s][0] for s in nb)
            base.append(linha_base(
                intensity_id=nid(), mineral_id=op["mineral_id"], mineral_name=mineral, company_id=company, empresa=c["empresa"],
                operation_id=op["operation_id"], processos_anm=op["processos"], operacao=c["operacao"] + " — só cargas de nióbio",
                municipio=op["municipio"], nivel="unidade_consumidora", tecnologia=op["tecnologia"], rota_tecnologica=op["rota"],
                tecnologia_status=op["tec_status"], produto=c["produto"], production_basis="produto", producao_valor=float(c["qtd"]),
                producao_unidade=c["un"], production_t=float(c["qtd"]), ano_producao=2025, energy_mwh=float(e), ano_energia=2025,
                cargas_ccee="; ".join(nb), energy_intensity_mwh_t=e / c["qtd"], intensidade_valor=e / c["qtd"], intensidade_unidade="MWh/t",
                natureza_dado="calculado", natureza_energia="observado", natureza_producao="declarado_empresa",
                compatibilidade_temporal="mesmo_ano", confianca="média", year=2025, periodo_referencia="2025",
                source_id="SRC_CCEE_PARCELA_CARGA; SRC_EMPRESA_RELATORIO", source_url=SOURCES["SRC_CCEE_PARCELA_CARGA"][0],
                fonte_producao=c["fonte"], fonte_producao_url=c["url"], tipo_fonte="oficial; imprensa", data_acesso=DATA_ACESSO,
                checagem_ccee_bruta=checagem(op["cnpj"], nb, e), status_validacao="calculado", responsavel_validacao=RESPONSAVEL,
                observacao=("exclui COPEBRAS OUVIDOR (fosfato, %.0f MWh) e TAILINGS (rejeitos, %.0f MWh); "
                            "pareamento carga→produto pela sigla e pelo ramo da CCEE" % (cargas["COPEBRAS OUVIDOR"][0], cargas["TAILINGS"][0])),
                versao_base=VERSAO,
            ))

    # Base compatível com o motor: energia 2025 ÷ produção beneficiada da ANM 2025 do mesmo titular (aba 12 do Squad 1).
    anm_casos = [
        (1, "MIN_022", "42184226", ["ANGLO AMERICAN BARRO", "ANGLO AMERICAN (CODE"], "ferroníquel (produção beneficiada ANM)"),
        (2, "MIN_011", "86902053", ["MARACA MINERACAO", "MARACÁ MINERAÇÃO - A"], "concentrado de cobre (produção beneficiada ANM)"),
        (3, "MIN_021", "26108898", ["CMOC BRASIL - NIOBIO", "CMOC NIOBIO - UC 218", "NIOBIO MINA CATALAO"], "nióbio beneficiado (ANM)"),
        (3, "MIN_049", "26108898", ["COPEBRAS OUVIDOR"], "fosfato beneficiado (ANM) — Copebrás"),
        (4, "MIN_049", "33931486", ["MOSAIC FERTILIZANTES"], "fosfato beneficiado (ANM)"),
        (6, "MIN_023", "42799486", ["Hochschild Amarillo"], "ouro beneficiado (ANM)"),
        (7, "MIN_033", "15104599", ["SAMA-MINACU-GO"], "amianto beneficiado (ANM)"),
        (8, "MIN_020", "08842895", ["Mineracao Serra Verd"], "terras raras beneficiadas (ANM)"),
    ]
    for pos, mineral_id, cnpj, siglas, produto in anm_casos:
        c, op = coef[pos], OPERACOES[pos]
        e = sum(cargas[s][0] for s in siglas)
        prod, estado, alerta, alt, procs = producao_anm(rows, cnpj, mineral_id)
        if prod <= 0:
            continue
        faixa = ""
        if alt:
            lo, hi = sorted([e / prod, e / alt])
            faixa = f"entre {lo:.4f} e {hi:.4f} MWh/t (denominador rateado por R$ × por t da CFEM)"
        ouro = mineral_id == "MIN_023"
        operation_id = op["operation_id"] if mineral_id == op["mineral_id"] else "OPE_801244_1968"
        base.append(linha_base(
            intensity_id=nid(), mineral_id=mineral_id, mineral_name=MINERAL_NAMES[mineral_id], company_id=f"COM_CNPJ_{cnpj}",
            empresa=c["empresa"] if mineral_id == op["mineral_id"] else "CMOC Brasil (Copebrás)",
            operation_id=operation_id, processos_anm="; ".join(procs), operacao=c["operacao"], municipio=op["municipio"],
            nivel="titular_mineral_ano", tecnologia=op["tecnologia"] if mineral_id == op["mineral_id"] else "nao_levantada_v1",
            rota_tecnologica=op["rota"] if mineral_id == op["mineral_id"] else "",
            tecnologia_status=op["tec_status"] if mineral_id == op["mineral_id"] else SEM_ROTA,
            produto=produto, production_basis="beneficiada", producao_valor=prod, producao_unidade="t", production_t=prod,
            ano_producao=2025, energy_mwh=float(e), ano_energia=2025, cargas_ccee="; ".join(siglas),
            energy_intensity_mwh_t=e / prod,
            intensidade_valor=(e / (prod * 1000)) if ouro else e / prod, intensidade_unidade="MWh/kg" if ouro else "MWh/t",
            natureza_dado="estimado", natureza_energia="observado", natureza_producao="estimado (rateio CFEM do Squad 1)",
            compatibilidade_temporal="mesmo_ano", confianca="média" if prod / estado > 0.9 and not alerta else "baixa",
            year=2025, periodo_referencia="2025",
            source_id="SRC_CCEE_PARCELA_CARGA; SRC_ANM_PROD_BENEF; SRC_ANM_CFEM",
            source_url="; ".join(SOURCES[s][0] for s in ("SRC_CCEE_PARCELA_CARGA", "SRC_ANM_PROD_BENEF", "SRC_ANM_CFEM")),
            fonte_producao="Squad 1 — aba 12 (interface_squad1_squad2.csv, v17)", tipo_fonte="oficial", data_acesso=DATA_ACESSO,
            metodo_estimacao=("energia 2025 da CCEE ÷ soma da produção beneficiada 2025 que a aba 12 atribui ao titular "
                              "(rateio do total do AMB pela participação na CFEM em R$); o titular responde por "
                              f"{prod / estado:.1%} da produção beneficiada do mineral em Goiás"),
            erro_estimativa_intervalo=faixa, checagem_ccee_bruta=checagem(cnpj, siglas, e),
            status_validacao="estimativa_com_alerta_09c" if alerta else "estimativa",
            responsavel_validacao=RESPONSAVEL,
            observacao=("a produção da ANM é de produto beneficiado (concentrado, liga), não de metal contido; "
                        "base compatível com a série production_t usada pelo motor"
                        + ("; no nióbio a massa beneficiada da ANM (%.0f t) é da ordem de 300× as %.0f t de Nb declaradas pela "
                           "empresa: é massa processada, não Nb contido" % (prod, coef[3]["qtd"]) if mineral_id == "MIN_021" else "")),
            versao_base=VERSAO,
        ))

    # Benchmarks do motor atual (não são observação de operação).
    with open(BENCH, encoding="utf-8-sig") as f:
        for b in csv.DictReader(f):
            base.append(linha_base(
                intensity_id=nid(), mineral_id=b["mineral_id"], mineral_name=b["mineral_name"], operation_id=f"AGG_GO_{b['mineral_id']}",
                operacao="agregado de Goiás (parâmetro do motor)", nivel="benchmark_mineral", tecnologia="nao_especificada",
                production_basis=b["production_basis"], energy_intensity_mwh_t=float(b["energy_intensity_mwh_t"]),
                intensidade_valor=float(b["energy_intensity_mwh_t"]), intensidade_unidade="MWh/t", natureza_dado="benchmark",
                natureza_energia="benchmark", natureza_producao="benchmark", compatibilidade_temporal="não se aplica",
                confianca="não informada", year="", periodo_referencia="não informado", source_id=b["source_id"],
                source_url=SOURCES["SRC_FGV_EPGE_001"][0], tipo_fonte="setorial", data_acesso=DATA_ACESSO,
                status_validacao="benchmark_nao_validado", responsavel_validacao=RESPONSAVEL,
                observacao="copiado sem alteração de Squad 2/modello_reale/parameters/energy_intensity.csv (data_nature=benchmark_proxy)",
                versao_base=VERSAO,
            ))
    ramo = {c["SIGLA_PARCELA_CARGA"]: c["RAMO_ATIVIDADE"] for c in d["ee_cargas"]}
    for r in base:
        r["unidade"] = "MWh/t"
        r["valor_observado_estimado"] = r["natureza_dado"]  # nome do campo no padrão de rastreabilidade (Entrega 1, §3)
        r["project_id"] = ""  # nenhuma linha é projeto futuro; todas são operações em produção
        if r["cargas_ccee"]:
            r["ramo_atividade_ccee"] = "; ".join(sorted({ramo[s.strip()] for s in r["cargas_ccee"].split(";")}))
    return base


def marcar_uso_no_motor(base):
    """Decide, linha a linha, se a intensidade vai para o arquivo do motor — e registra o motivo."""
    agregados_com_detalhe = {r["operation_id"] for r in base if r["nivel"] == "unidade_consumidora"
                             and r["production_basis"] == "conteudo_mineral"}
    for r in base:
        if r["natureza_dado"] == "benchmark":
            r["usar_no_motor"] = "não — benchmark que já está no motor"
        elif r["production_basis"] not in ("beneficiada", "conteudo_mineral"):
            r["usar_no_motor"] = f"não — base '{r['production_basis']}' fora do vocabulário do motor (rom, beneficiada, conteudo_mineral)"
        elif r["compatibilidade_temporal"] != "mesmo_ano":
            r["usar_no_motor"] = "não — produção e energia de anos diferentes"
        elif r["nivel"] == "operacao_empresa" and r["mineral_id"] == "MIN_022" and agregados_com_detalhe:
            r["usar_no_motor"] = "não — as linhas por planta (unidade consumidora) somam a mesma energia"
        else:
            r["usar_no_motor"] = "sim"


def motor_rows(base):
    """Formato do contrato "Intensidade energética" do README do Squad 2 (MWh/t; production_basis em minúsculas)."""
    out = []
    for r in base:
        if r["usar_no_motor"] != "sim":
            continue
        out.append({
            "mineral_id": r["mineral_id"],
            "operation_id": r["operation_id"] or f"PROC_{r['processos_anm'].split(';')[0].replace('/', '_')}",
            "year": r["year"], "energy_intensity_mwh_t": r["energy_intensity_mwh_t"],
            "production_basis": r["production_basis"], "data_nature": r["natureza_dado"],
            "source_id": r["source_id"].replace(" ", ""), "intensity_id": r["intensity_id"],
        })
    return out


# Coeficiente estadual: uma linha por mineral do modelo, na mesma production_basis que o modelo usa.
# Linhas da base que entram em cada coeficiente (sem planta e agregado juntos, para não contar energia duas vezes).
ESTADUAL = {
    "MIN_011": dict(nivel="operacao_empresa", basis="conteudo_mineral",
                    nota="só a Maracá produz cobre em Goiás; produção de Cu contido declarada pela Lundin (43.974 t) "
                         "confere com a série da ANM que o modelo usa (43.983,55 t em 2025, v17 aba 08): diferença de 0,02%"),
    "MIN_005": None,  # sem produtor de bauxita na CCEE: fica o parâmetro atual do modelo
    "MIN_022": dict(nivel="titular_mineral_ano", basis="beneficiada",
                    nota="o valor atual do modelo (45,55) é MWh por t de Ni contido; aplicado à produção beneficiada "
                         "(ferroníquel) superestima a energia em cerca de 4 vezes"),
    "MIN_049": dict(nivel="titular_mineral_ano", basis="beneficiada",
                    nota="Mosaic (0,089) + Copebrás/CMOC (0,169), somando energia e produção"),
    "MIN_033": dict(nivel="titular_mineral_ano", basis="beneficiada",
                    nota="só a SAMA produz amianto em Goiás"),
}
CAMPOS_ESTADUAL = [
    "mineral_id", "mineral_name", "production_basis", "energy_intensity_mwh_t", "source_id", "data_nature",
    "aggregation_method", "year", "intensity_ids", "energy_mwh", "production_t", "coverage_share",
    "range_min_mwh_t", "range_max_mwh_t", "confianca", "valor_modelo_atual_mwh_t", "variacao_vs_modelo_pct",
    "observacao", "versao_base",
]


def coeficiente_estadual(base, rows):
    """Um coeficiente por mineral do modelo: Σ energia CCEE ÷ Σ produção das operações cobertas (média ponderada pela produção)."""
    with open(BENCH, encoding="utf-8-sig") as f:
        modelo = list(csv.DictReader(f))
    ccee_raizes = {cnpj for cnpj, _ in ccee_bruta_2025()[0]}
    out = []
    for m in modelo:
        regra = ESTADUAL[m["mineral_id"]]
        atual = float(m["energy_intensity_mwh_t"])
        linha = dict.fromkeys(CAMPOS_ESTADUAL, "")
        linha.update(mineral_id=m["mineral_id"], mineral_name=m["mineral_name"], production_basis=m["production_basis"],
                     year=2025, valor_modelo_atual_mwh_t=atual, versao_base=VERSAO)
        estado = [r for r in rows if r["nivel_agregacao"] == "estado" and r["mineral_id"] == m["mineral_id"]
                  and r["year"] == "2025" and r["production_basis"] == "beneficiada"]
        total_estado = sum(float(r["production_t"]) for r in estado)
        if regra is None:
            produtores = {r["company_id"][9:] for r in rows if r["mineral_id"] == m["mineral_id"] and r["year"] == "2025"
                          and r["company_id"].startswith("COM_CNPJ_")}
            bench = next(r for r in base if r["nivel"] == "benchmark_mineral" and r["mineral_id"] == m["mineral_id"])
            linha.update(energy_intensity_mwh_t=atual, source_id=m["source_id"], data_nature=m["data_nature"],
                         aggregation_method="sem dado próprio: mantido o parâmetro atual do modelo",
                         intensity_ids=bench["intensity_id"], coverage_share=0.0, confianca="não informada",
                         variacao_vs_modelo_pct=0.0,
                         observacao=f"nenhum dos {len(produtores)} titulares de bauxita com CNPJ na aba 12 aparece na CCEE "
                                    f"({len(produtores & ccee_raizes)} encontrados), provavelmente por comprarem energia "
                                    "no mercado cativo; sem energia observada não há coeficiente próprio")
            out.append(linha)
            continue
        usadas = [r for r in base if r["mineral_id"] == m["mineral_id"] and r["nivel"] == regra["nivel"]
                  and r["production_basis"] == regra["basis"]]
        assert regra["basis"] == m["production_basis"], m["mineral_id"]
        energia = sum(float(r["energy_mwh"]) for r in usadas)
        prod = sum(float(r["production_t"]) for r in usadas)
        coef = energia / prod
        # Faixa: o mesmo cálculo com o denominador alternativo do rateio da CFEM (R$ × por t) do Squad 1.
        faixa = [coef]
        if regra["nivel"] == "titular_mineral_ano":
            alts = [producao_anm(rows, r["company_id"][9:], m["mineral_id"])[3] for r in usadas]
            if all(alts):
                faixa.append(energia / sum(alts))
        cobertos = {r["company_id"] for r in usadas}
        cobertura = sum(float(r["production_t"]) for r in rows if r["nivel_agregacao"] == "operacao"
                        and r["mineral_id"] == m["mineral_id"] and r["year"] == "2025"
                        and r["production_basis"] == "beneficiada" and r["company_id"] in cobertos) / total_estado
        fontes = []
        for r in usadas:
            fontes += [s.strip() for s in r["source_id"].split(";") if s.strip() not in fontes]
        naturezas = {r["natureza_dado"] for r in usadas}
        linha.update(
            energy_intensity_mwh_t=round(coef, 6), source_id=";".join(fontes),
            data_nature="estimado" if "estimado" in naturezas else "calculado",
            aggregation_method=("Σ energia CCEE 2025 ÷ Σ produção 2025 das operações cobertas "
                                "(média das intensidades ponderada pela produção)" if len(usadas) > 1 else
                                "energia CCEE 2025 ÷ produção 2025 da única operação coberta"),
            intensity_ids=";".join(r["intensity_id"] for r in usadas), energy_mwh=round(energia, 3),
            production_t=round(prod, 3), coverage_share=round(cobertura, 4),
            range_min_mwh_t=round(min(faixa), 6), range_max_mwh_t=round(max(faixa), 6),
            confianca="alta" if naturezas == {"calculado"} else ("média" if cobertura > 0.9 else "baixa"),
            variacao_vs_modelo_pct=round((coef / atual - 1) * 100, 1),
            observacao=regra["nota"] + ("" if cobertura > 0.999 else
                                        f"; a produção não coberta ({1 - cobertura:.1%}) recebe a mesma intensidade"),
        )
        out.append(linha)
    return out


def write(path, rows, campos):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, campos, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def main():
    base = build()
    marcar_uso_no_motor(base)
    write(OUT / "base_intensidade_energetica_v1.csv", base, CAMPOS)
    motor = motor_rows(base)
    write(OUT / "energy_intensity_para_motor_v1.csv", motor,
          ["mineral_id", "operation_id", "year", "energy_intensity_mwh_t", "production_basis", "data_nature", "source_id", "intensity_id"])
    estadual = coeficiente_estadual(base, interface_rows())
    write(OUT / "coeficiente_estadual_para_modelo_v1.csv", estadual, CAMPOS_ESTADUAL)
    print(f"{len(base)} linhas na base; {len(motor)} no arquivo para o motor; {len(estadual)} coeficientes estaduais")
    for r in estadual:
        print(f"  {r['mineral_name']:<20} {r['production_basis']:<16} {r['energy_intensity_mwh_t']:>10} MWh/t "
              f"({r['data_nature']}; modelo atual {r['valor_modelo_atual_mwh_t']}; cobertura {r['coverage_share']})")
    for r in base:
        print(f"{r['intensity_id']} | {r['mineral_name']:<24} | {r['empresa'][:30]:<30} | {r['production_basis']:<16} | "
              f"{r['energy_intensity_mwh_t']:>12} MWh/t | {r['natureza_dado']:<9} | {r['confianca']}")


if __name__ == "__main__":
    main()
