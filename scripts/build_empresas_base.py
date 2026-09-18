# -*- coding: utf-8 -*-
"""Pacote da aba Empresas (data/empresas/empresas.json): produção declarada e carga de energia da CCEE, por empresa, mineral e ano.

    python scripts/build_empresas_base.py                  # usa a raiz do repositório onde está este script
    python scripts/build_empresas_base.py --repo <clone>

Junta duas bases que este repositório já versiona:

- `data/producao/producao.json` — o que cada empresa declarou ter produzido, com medida, escopo, período e fonte;
- `data/panorama/panorama.json` — as parcelas de carga da CCEE em Goiás, que já trazem o CNPJ raiz do agente e o vínculo com o titular
  minerário. A ligação entre as duas é o **CNPJ raiz**, não o nome: nove das dez empresas da base de produção têm carga própria declarada.

Acrescenta ao quadro as duas colunas pedidas — **energia gasta** e **coeficiente energético** — e, porque nenhuma das duas fontes cobre doze
meses de todos os anos, uma coluna de **anualização** para cada lado, sempre ao lado do número observado e nunca por cima dele:

- energia: soma dos meses observados ÷ meses observados × 12. A CCEE do repositório cobre ago/out–dez de 2024, jun–dez de 2025 e jan–jul de 2026;
- produção: quando não há número anual publicado, soma dos semestres ou trimestres publicados ÷ meses cobertos × 12. Semestre e trimestre que se
  sobrepõem nunca somam (um S1 já contém Q1 e Q2), e linha de planta isolada (`nivel='operacao'`) fica fora, para não duplicar a linha da empresa.

O coeficiente é `energia (kWh) ÷ produção`, na unidade em que a empresa publica — kWh/t ou kWh/oz. **Nada é convertido**: onça não vira quilo
para o coeficiente ficar bonito. E ele só sai quando a produção é do recorte de Goiás (`operacao_goias`), realizada, e no nível da empresa.

Quando a carga da empresa move mais de um mineral (Chapada faz cobre e ouro do mesmo minério; a CMOC move nióbio e fosfato em Catalão e
Ouvidor), a energia **não é rateada** e o coeficiente sai marcado `energia_exclusiva=false`: ele é a energia inteira da empresa por unidade
daquele mineral, e não a energia daquele circuito.
"""
import argparse
import json
import sys
from datetime import date
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ap = argparse.ArgumentParser(description="Gera data/empresas/empresas.json cruzando produção declarada e carga CCEE.")
ap.add_argument("--repo", default=str(Path(__file__).resolve().parents[1]), help="raiz do clone (padrão: a deste script)")
ap.add_argument("--saida", help="padrão: <repo>/data/empresas/empresas.json")
args = ap.parse_args()
REPO = Path(args.repo)
SAIDA = Path(args.saida) if args.saida else REPO / "data" / "empresas" / "empresas.json"

VERSAO = "v1"
# Medidas que descrevem o que saiu da operação. Embarque, venda, capacidade e meta ficam de fora de qualquer série de produção.
MEDIDAS_PRODUCAO = {"minerio_rom", "contido", "metal_em_concentrado", "produto_acabado"}
MESES_DO_PERIODO = {
    "ano": frozenset(range(1, 13)),
    "S1": frozenset(range(1, 7)), "S2": frozenset(range(7, 13)),
    "Q1": frozenset((1, 2, 3)), "Q2": frozenset((4, 5, 6)),
    "Q3": frozenset((7, 8, 9)), "Q4": frozenset((10, 11, 12)),
}


def sufixo(registro):
    """'2025-Q3' -> 'Q3'; '2025' -> 'ano'."""
    return registro["periodo"].split("-", 1)[1] if "-" in registro["periodo"] else "ano"


def ano_de(registro):
    return int(registro["periodo"][:4])


def cobre(registros):
    """Escolhe os períodos que mais cobrem o ano sem se sobrepor: um S1 já contém Q1 e Q2 e não soma com eles."""
    escolhidos, meses = [], set()
    for registro in sorted(registros, key=lambda r: -len(MESES_DO_PERIODO[sufixo(r)])):
        do_periodo = MESES_DO_PERIODO[sufixo(registro)]
        if do_periodo & meses:
            continue
        escolhidos.append(registro)
        meses |= do_periodo
    return escolhidos, meses


# ------------------------------------------------------------------------------------------------------- produção por empresa e ano
producao = json.loads((REPO / "data" / "producao" / "producao.json").read_text(encoding="utf-8"))
por_empresa, carga_declarada, ficha = {}, {}, {}
for registro in producao["registros"]:
    ficha.setdefault(registro["empresa"], {
        "empresa": registro["empresa"], "grupo": registro["grupo"], "cnpj_raiz": registro["cnpj_raiz"],
        "operacao": registro["operacao"], "municipios": registro["municipios"],
    })
    carga_declarada[registro["empresa"]] = registro["minerais_na_carga_ccee"]
    if (registro["escopo"] != "operacao_goias" or registro["tipo_valor"] != "realizado"
            or registro["medida"] not in MEDIDAS_PRODUCAO or registro["nivel"] != "empresa"):
        continue
    por_empresa.setdefault((registro["empresa"], registro["mineral"], ano_de(registro)), []).append(registro)

producoes = {}
for chave, registros in por_empresa.items():
    unidades = {r["unidade"] for r in registros}
    if len(unidades) > 1:
        # Duas unidades para o mesmo mineral e ano não se somam; fica a que tem mais linhas e a outra é declarada.
        principal = max(unidades, key=lambda u: sum(1 for r in registros if r["unidade"] == u))
        registros = [r for r in registros if r["unidade"] == principal]
    anuais = [r for r in registros if sufixo(r) == "ano"]
    if anuais:
        escolhido = max(anuais, key=lambda r: {"alta": 3, "media": 2, "baixa": 1}[r["confianca"]])
        producoes[chave] = {
            "valor": escolhido["valor"], "unidade": escolhido["unidade"], "produto": escolhido["produto"],
            "medida": escolhido["medida"], "origem": "declarada_anual", "meses_cobertos": 12,
            "periodos": [escolhido["periodo"]], "registros": [escolhido["id"]],
            "confianca": escolhido["confianca"], "unidades_descartadas": sorted(unidades - {escolhido["unidade"]}),
        }
        continue
    escolhidos, meses = cobre(registros)
    if not escolhidos:
        continue
    soma = sum(r["valor"] for r in escolhidos)
    producoes[chave] = {
        "valor": round(soma * 12 / len(meses), 3), "unidade": escolhidos[0]["unidade"],
        "produto": escolhidos[0]["produto"], "medida": escolhidos[0]["medida"],
        "origem": "anualizada_de_parciais", "meses_cobertos": len(meses),
        "periodos": sorted(r["periodo"] for r in escolhidos), "registros": sorted(r["id"] for r in escolhidos),
        "observado": round(soma, 3),
        "confianca": min((r["confianca"] for r in escolhidos), key=lambda c: {"alta": 3, "media": 2, "baixa": 1}[c]),
        "unidades_descartadas": sorted(unidades - {escolhidos[0]["unidade"]}),
    }

# ------------------------------------------------------------------------------------------------------ energia CCEE por empresa e ano
panorama = json.loads((REPO / "data" / "panorama" / "panorama.json").read_text(encoding="utf-8"))
coluna = {nome: i for i, nome in enumerate(panorama["ccee"]["cols"])}
municipios = panorama["dims"]["mun"]
ramos = panorama["dims"]["ramo"]
por_cnpj = {f["cnpj_raiz"]: nome for nome, f in ficha.items()}
indice_ccee = {i: por_cnpj[linha[0]] for i, linha in enumerate(panorama["dims"]["ce"]) if linha[0] in por_cnpj}
nome_ccee = {por_cnpj[linha[0]]: linha[1] for linha in panorama["dims"]["ce"] if linha[0] in por_cnpj}

energias = {}
for linha in panorama["ccee"]["rows"]:
    agente = linha[coluna["empresa"]]
    if agente not in indice_ccee:
        continue
    ano, mes = divmod(linha[coluna["mes"]], 100)
    bucket = energias.setdefault((indice_ccee[agente], ano), {
        "acl_mwh": 0.0, "cativo_mwh": 0.0, "total_mwh": 0.0, "meses": set(), "municipios": set(), "ramos": set(),
        "capacidade_mw": 0.0})
    bucket["acl_mwh"] += linha[coluna["acl_mwh"]]
    bucket["cativo_mwh"] += linha[coluna["cativo_mwh"]]
    bucket["total_mwh"] += linha[coluna["total_mwh"]]
    bucket["capacidade_mw"] = max(bucket["capacidade_mw"], linha[coluna["capacidade_mw"]])
    bucket["meses"].add(mes)
    bucket["ramos"].add(ramos[linha[coluna["ramo"]]])
    if linha[coluna["mun"]] >= 0:
        bucket["municipios"].add(municipios[linha[coluna["mun"]]][1])

# ------------------------------------------------------------------------------------------------------------------ o quadro
ESCALA_DE_QUALIDADE = ["observado_completo", "estimado_alto", "estimado_medio", "estimado_baixo"]


def qualidade(meses):
    return "observado_completo" if meses >= 12 else "estimado_alto" if meses >= 9 else \
           "estimado_medio" if meses >= 6 else "estimado_baixo"


def pior(*niveis):
    return max(niveis, key=ESCALA_DE_QUALIDADE.index)


linhas = []
chaves = {(empresa, ano) for (empresa, _, ano) in producoes} | set(energias)
for empresa, ano in sorted(chaves):
    energia = energias.get((empresa, ano))
    minerais_da_carga = carga_declarada.get(empresa, [])
    minerais = sorted({mineral for (e, mineral, a) in producoes if e == empresa and a == ano})
    for mineral in (minerais or [None]):
        producao_ano = producoes.get((empresa, mineral, ano)) if mineral else None
        linha = {
            **ficha[empresa],
            "nome_ccee": nome_ccee.get(empresa),
            "ano": ano,
            "mineral": mineral,
            "producao": producao_ano,
            "energia": None,
            "coeficiente": None,
        }
        if energia:
            meses = len(energia["meses"])
            linha["energia"] = {
                "mwh_observado": round(energia["total_mwh"], 3),
                "mwh_anualizado": round(energia["total_mwh"] * 12 / meses, 3),
                "acl_mwh_observado": round(energia["acl_mwh"], 3),
                "cativo_mwh_observado": round(energia["cativo_mwh"], 3),
                "capacidade_mw": round(energia["capacidade_mw"], 3),
                "meses_observados": meses,
                "meses": sorted(energia["meses"]),
                "origem": "observado_completo" if meses >= 12 else "anualizado_pro_rata",
                "qualidade": qualidade(meses),
                "municipios_ccee": sorted(energia["municipios"]),
                "ramos_ccee": sorted(energia["ramos"]),
            }
        if producao_ano and linha["energia"] and producao_ano["valor"] > 0:
            exclusiva = len(minerais_da_carga) == 1 and minerais_da_carga == [mineral]
            linha["coeficiente"] = {
                "valor": round(linha["energia"]["mwh_anualizado"] * 1000 / producao_ano["valor"], 3),
                "unidade": f'kWh/{producao_ano["unidade"]}',
                "energia_exclusiva": exclusiva,
                "minerais_na_carga": minerais_da_carga,
                # A linha vale o mais fraco dos dois lados: energia estimada de 4 meses não vira coeficiente confiável
                # só porque a produção do ano foi publicada.
                "qualidade": pior(linha["energia"]["qualidade"], qualidade(producao_ano["meses_cobertos"])),
            }
        elif linha["energia"] and not producao_ano:
            linha["sem_coeficiente"] = ("a empresa tem carga de energia no ano, mas nenhuma produção declarada no recorte de Goiás para "
                                        "esse ano")
        elif producao_ano and not linha["energia"]:
            linha["sem_coeficiente"] = "a empresa tem produção declarada, mas nenhuma carga própria identificada na base CCEE de Goiás"
        linhas.append(linha)

pacote = {
    "meta": {
        "built_on": date.today().isoformat(),
        "versao_base": VERSAO,
        "gerado_por": "scripts/build_empresas_base.py",
        "fontes": {
            "producao": "data/producao/producao.json — o que cada empresa declarou, com fonte e medida",
            "energia": "data/panorama/panorama.json, tabela ccee — parcelas de carga da CCEE em Goiás",
        },
        "chave_de_ligacao": "CNPJ raiz do agente da CCEE contra o CNPJ raiz do titular da base de produção. Nome não é chave.",
        "periodo_ccee": panorama["meta"]["periods"]["ccee"],
        "avisos": [
            "Energia e produção vêm de fontes diferentes, com cobertura diferente, e por isso a linha declara os meses observados de cada lado.",
            "Anualização é pro rata: soma observada ÷ meses observados × 12. É estimativa, não medição, e a qualidade da linha diz o quanto.",
            "Semestre e trimestre que se sobrepõem nunca somam; linha de planta isolada não entra no total da empresa.",
            "O coeficiente sai na unidade em que a empresa publica (kWh/t, kWh/oz). Nada é convertido entre unidades.",
            "Com mais de um mineral atrás da mesma carga, a energia NÃO é rateada: o coeficiente sai com energia_exclusiva=false e é a energia "
            "inteira da empresa por unidade daquele mineral.",
            "A carga da CCEE é do agente, não da planta: pode incluir uso administrativo e não inclui autoprodução nem geração própria.",
            "Nenhum número de produção foi conferido no documento de origem (ver data/producao/README.md): a linha herda essa limitação.",
        ],
    },
    "linhas": linhas,
}
SAIDA.parent.mkdir(parents=True, exist_ok=True)
with open(SAIDA, "w", encoding="utf-8", newline="\n") as arquivo:
    json.dump(pacote, arquivo, ensure_ascii=False, indent=1)
    arquivo.write("\n")

# ----------------------------------------------------------------------------------------------------------------- conferências
com_energia = [l for l in linhas if l["energia"]]
com_coef = [l for l in linhas if l["coeficiente"]]
print(f"linhas: {len(linhas)} · empresas {len({l['empresa'] for l in linhas})} · anos {sorted({l['ano'] for l in linhas})}")
print(f"com energia: {len(com_energia)} · com produção: {sum(1 for l in linhas if l['producao'])} · com coeficiente: {len(com_coef)}")
print(f"produção anualizada de parciais: {sum(1 for l in linhas if l['producao'] and l['producao']['origem'] == 'anualizada_de_parciais')}")
print(f"coeficiente com energia exclusiva: {sum(1 for l in com_coef if l['coeficiente']['energia_exclusiva'])} de {len(com_coef)}")
for linha in sorted(com_coef, key=lambda l: (l["empresa"], l["ano"], l["mineral"])):
    coef, prod, ener = linha["coeficiente"], linha["producao"], linha["energia"]
    marca = "" if coef["energia_exclusiva"] else "  [energia não exclusiva]"
    print(f"  {linha['grupo'].split(' (')[0][:26]:<28}{linha['ano']} {linha['mineral']:<22} "
          f"{prod['valor']:>12,.0f} {prod['unidade']:<3} ({prod['origem'][:9]}) · "
          f"{ener['mwh_anualizado']:>11,.0f} MWh/ano ({ener['meses_observados']}m) · "
          f"{coef['valor']:>11,.1f} {coef['unidade']}{marca}")
print(f"SALVO: {SAIDA} ({SAIDA.stat().st_size / 1e3:.1f} kB)")
