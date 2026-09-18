# -*- coding: utf-8 -*-
"""Pacote da base de produção por empresa (data/producao/producao.json e .csv), gerado da curadoria em `producao/base_curada.json`.

    python scripts/build_producao_base.py                  # usa a raiz do repositório onde está este script
    python scripts/build_producao_base.py --repo <clone>

Cada linha da saída é UM número publicado por UMA fonte, com quatro campos obrigatórios — empresa, produção, mineral e unidade — e mais a
proveniência que este projeto exige: o que o número mede (`medida`), a que recorte ele se refere (`escopo`), se é realização, guidance,
capacidade ou meta (`tipo_valor`), o período, a fonte com endereço e a data da coleta.

O script NÃO converte unidade, NÃO soma entre unidades e NÃO soma trimestres para formar ano: períodos e medidas diferentes ficam como linhas
distintas. Ele junta, como referência de reconciliação, a produção de Goiás por substância do Anuário Mineral Brasileiro que já está versionada
em `Squad 1/Dados brutos/ANM - Anuário Mineral Brasileiro (AMB)/Producao_Bruta.csv` — números do estado, não da empresa, e por isso guardados
numa seção separada.

O vocabulário de mineral é conferido contra `data/panorama/panorama.json` (dims/min), para a base falar a mesma língua do atlas e do panorama.
"""
import argparse
import csv
import json
import sys
import unicodedata
from datetime import date
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ap = argparse.ArgumentParser(description="Gera data/producao/producao.json e producao.csv a partir de producao/base_curada.json.")
ap.add_argument("--repo", default=str(Path(__file__).resolve().parents[1]), help="raiz do clone (padrão: a deste script)")
ap.add_argument("--saida", help="padrão: <repo>/data/producao")
args = ap.parse_args()
REPO = Path(args.repo)
SAIDA = Path(args.saida) if args.saida else REPO / "data" / "producao"

VERSAO = "v1"
UNIDADES = {"t", "kg", "g", "oz", "m3", "l", "ct", "m2"}
MEDIDAS = {"minerio_rom", "contido", "metal_em_concentrado", "produto_acabado", "embarque", "capacidade", "meta"}
ESCOPOS = {"operacao_goias", "consolidado_brasil", "consolidado_global"}
TIPOS = {"realizado", "guidance", "capacidade", "meta"}
PERIODOS = {"ano", "semestre", "trimestre", "mes"}
FONTES = {"ri_empresa", "agencia_oficial", "imprensa_setorial", "imprensa_geral", "agregador_mercado"}
CONFIANCAS = {"alta", "media", "baixa"}
# Substâncias do AMB que interessam à reconciliação com as empresas desta base.
AMB_SUBSTANCIAS = ["Alumínio (Bauxita)", "Amianto", "Cobre", "Fosfato", "Monazita e Terras-Raras", "Nióbio", "Níquel",
                   "Ouro", "Vermiculita e Perlita"]


def norm(s):
    return unicodedata.normalize("NFD", str(s or "")).encode("ascii", "ignore").decode().upper().strip()


def num_amb(s):
    """Número do AMB ('9249167,900000', ',000000000000000'); vazio vale 0."""
    s = str(s or "").strip()
    return float(s.replace(".", "").replace(",", ".")) if s else 0.0


# --------------------------------------------------------------------------------------------------------- vocabulário de mineral
panorama = json.loads((REPO / "data" / "panorama" / "panorama.json").read_text(encoding="utf-8"))
MINERAIS = {norm(m[1]): m[1] for m in panorama["dims"]["min"]}

# ----------------------------------------------------------------------------------------------------------------- curadoria
curada = json.loads((REPO / "producao" / "base_curada.json").read_text(encoding="utf-8"))
erros, registros = [], []
for empresa in curada["empresas"]:
    for i, r in enumerate(empresa["registros"]):
        onde = f"{empresa['empresa_operadora']}[{i}]"
        if r["unidade"] not in UNIDADES:
            erros.append(f"{onde}: unidade '{r['unidade']}' fora do vocabulário")
        if r["medida"] not in MEDIDAS:
            erros.append(f"{onde}: medida '{r['medida']}' fora do vocabulário")
        if r["escopo"] not in ESCOPOS:
            erros.append(f"{onde}: escopo '{r['escopo']}' fora do vocabulário")
        if r["tipo_valor"] not in TIPOS:
            erros.append(f"{onde}: tipo_valor '{r['tipo_valor']}' fora do vocabulário")
        if r["periodo_tipo"] not in PERIODOS:
            erros.append(f"{onde}: periodo_tipo '{r['periodo_tipo']}' fora do vocabulário")
        if r["fonte_tipo"] not in FONTES:
            erros.append(f"{onde}: fonte_tipo '{r['fonte_tipo']}' fora do vocabulário")
        if r["confianca"] not in CONFIANCAS:
            erros.append(f"{onde}: confianca '{r['confianca']}' fora do vocabulário")
        if norm(r["mineral"]) not in MINERAIS:
            erros.append(f"{onde}: mineral '{r['mineral']}' não existe no dicionário da ANM usado pelo panorama")
        if not str(r.get("fonte_url", "")).startswith("http"):
            erros.append(f"{onde}: sem endereço de fonte")
        if not isinstance(r["valor"], (int, float)) or r["valor"] <= 0:
            erros.append(f"{onde}: valor inválido")
        if "valor_max" in r and r["valor_max"] < r["valor"]:
            erros.append(f"{onde}: valor_max menor que valor")
        if r["tipo_valor"] == "guidance" and "valor_max" not in r:
            erros.append(f"{onde}: guidance sem faixa (valor_max)")

        registros.append({
            "id": f"PRD_{len(registros) + 1:04d}",
            "empresa": empresa["empresa_operadora"],
            "grupo": empresa["grupo"],
            "cnpj_raiz": empresa["cnpj_raiz"],
            "operacao": r.get("operacao_detalhe") or empresa["operacao"],
            "municipios": empresa["municipios"],
            "uf": empresa["uf"],
            "mineral": MINERAIS[norm(r["mineral"])] if norm(r["mineral"]) in MINERAIS else r["mineral"],
            "produto": r["produto"],
            "valor": r["valor"],
            "valor_max": r.get("valor_max"),
            "unidade": r["unidade"],
            "medida": r["medida"],
            "periodo_tipo": r["periodo_tipo"],
            "periodo": r["periodo"],
            "escopo": r["escopo"],
            "tipo_valor": r["tipo_valor"],
            "fonte_nome": r["fonte_nome"],
            "fonte_url": r["fonte_url"],
            "fonte_tipo": r["fonte_tipo"],
            "confianca": r["confianca"],
            "coleta_metodo": "busca_web",
            "coleta_data": curada["atualizado_em"],
            "status_validacao": "nao_validado",
            "responsavel_validacao": None,
            "observacao": r.get("observacao", ""),
        })

if erros:
    print("A curadoria não passou na conferência:")
    for e in erros:
        print("  -", e)
    sys.exit(1)

# ------------------------------------------------------------------------------------- referência do estado (AMB), para reconciliar
amb_path = REPO / "Squad 1" / "Dados brutos" / "ANM - Anuário Mineral Brasileiro (AMB)" / "Producao_Bruta.csv"
referencia, anos_amb = [], set()
with open(amb_path, encoding="latin-1", newline="") as f:
    for linha in csv.DictReader(f):
        if linha["UF"] != "GO" or linha["Substância Mineral"] not in AMB_SUBSTANCIAS:
            continue
        ano = int(linha["Ano base"])
        anos_amb.add(ano)
        if ano < 2022:
            continue
        referencia.append({
            "ano": ano,
            "mineral": linha["Substância Mineral"],
            "rom_t": round(num_amb(linha["Quantidade Produção - Minério ROM (t)"]), 2),
            "contido": round(num_amb(linha["Quantidade Contido"]), 3),
            "contido_unidade": (linha["Unidade de Medida - Contido"] or "").strip(),
            "contido_indicacao": (linha["Indicação Contido"] or "").strip(),
        })
referencia.sort(key=lambda r: (r["ano"], r["mineral"]))

# ----------------------------------------------------------------------------------------------------------------- saída
pacote = {
    "meta": {
        "built_on": date.today().isoformat(),
        "versao_base": VERSAO,
        "gerado_por": "scripts/build_producao_base.py",
        "curadoria": "producao/base_curada.json",
        "atualizado_em": curada["atualizado_em"],
        "vocabulario": curada["vocabulario"],
        "limitacao_da_coleta": curada["limitacao_da_coleta_v1"],
        "fonte_referencia_uf": "Anuário Mineral Brasileiro (ANM), aba de produção bruta, versionado no repositório",
        "avisos": [
            "Toda linha nasce nao_validado. Importar não é validar (METODOLOGIA.md §1).",
            "Nada é convertido entre unidades. Onça troy (oz), tonelada (t) e quilo (kg) convivem sem fator de conversão.",
            "Trimestres e semestres NÃO somam para formar o ano: a empresa pode revisar o número no fechamento.",
            "Escopo 'consolidado_brasil' e 'consolidado_global' NÃO são produção de Goiás e não podem ser agregados ao estado.",
            "'embarque', 'capacidade' e 'meta' não são produção realizada e não entram em série de produção.",
            "A referência do AMB é do estado por substância, não da empresa: ela serve para conferir ordem de grandeza, não para atribuir produção a titular.",
        ],
    },
    "registros": registros,
    "referencia_amb_go": referencia,
}
SAIDA.mkdir(parents=True, exist_ok=True)
with open(SAIDA / "producao.json", "w", encoding="utf-8", newline="\n") as f:
    json.dump(pacote, f, ensure_ascii=False, indent=1)
    f.write("\n")

COLUNAS = ["id", "empresa", "grupo", "operacao", "municipios", "uf", "mineral", "produto", "valor", "valor_max",
           "unidade", "medida", "periodo_tipo", "periodo", "escopo", "tipo_valor", "confianca", "fonte_nome",
           "fonte_url", "fonte_tipo", "coleta_metodo", "coleta_data", "status_validacao", "observacao"]
with open(SAIDA / "producao.csv", "w", encoding="utf-8", newline="") as f:
    escritor = csv.writer(f, delimiter=";")
    escritor.writerow(COLUNAS)
    for r in registros:
        escritor.writerow(["; ".join(r[c]) if c == "municipios" else ("" if r[c] is None else r[c]) for c in COLUNAS])

# ----------------------------------------------------------------------------------------------------------------- conferências
por = lambda campo: ", ".join(f"{k} {v}" for k, v in sorted(
    {x: sum(1 for r in registros if r[campo] == x) for x in {r[campo] for r in registros}}.items()))
print(f"registros: {len(registros)} de {len(curada['empresas'])} empresas, {len({r['mineral'] for r in registros})} minerais")
print(f"unidades: {por('unidade')}")
print(f"medida: {por('medida')}")
print(f"escopo: {por('escopo')}")
print(f"tipo_valor: {por('tipo_valor')}")
print(f"confiança: {por('confianca')}")
print(f"realizados em Goiás por ano: " + "; ".join(
    f"{p} {sum(1 for r in registros if r['periodo'] == p and r['tipo_valor'] == 'realizado' and r['escopo'] == 'operacao_goias')}"
    for p in sorted({r['periodo'] for r in registros if r['periodo_tipo'] == 'ano'})))
print(f"referência AMB GO: {len(referencia)} linhas, anos {min(anos_amb)}–{max(anos_amb)} na fonte, {min(r['ano'] for r in referencia)}–{max(r['ano'] for r in referencia)} no pacote")
for r in [x for x in referencia if x["ano"] == max(y["ano"] for y in referencia)]:
    print(f"  AMB {r['ano']} {r['mineral']}: ROM {r['rom_t']:,.0f} t; contido {r['contido']:,.2f} {r['contido_unidade']} {r['contido_indicacao']}")
print(f"SALVO: {SAIDA / 'producao.json'} ({(SAIDA / 'producao.json').stat().st_size / 1e3:.1f} kB) e {SAIDA / 'producao.csv'}")
