# -*- coding: utf-8 -*-
"""Pacote da base de produção por empresa (data/producao/producao.json e .csv), gerado da curadoria em `producao/base_curada.json`.

    python scripts/build_producao_base.py                  # usa a raiz do repositório onde está este script
    python scripts/build_producao_base.py --repo <clone>

Cada linha da saída é UM número publicado por UMA fonte, com quatro campos obrigatórios — empresa, produção, mineral e unidade — e mais a
proveniência que este projeto exige: o que o número mede (`medida`), a que recorte ele se refere (`escopo`), se é realização, guidance,
capacidade ou meta (`tipo_valor`), o período, a fonte com endereço e a data da coleta.

O script NÃO converte unidade, NÃO soma entre unidades e NÃO soma trimestres para formar ano: períodos e medidas diferentes ficam como linhas
distintas.

**Só entra número declarado pela própria empresa** — no release de resultados, no relatório anual ou no que a imprensa e os agregadores de
mercado reproduzem dessas publicações. Estatística de agência (ANM, SGB) fica de fora por decisão de escopo: o Anuário Mineral mede o contido
no minério lavrado de um estado inteiro, e a empresa publica o produto que saiu da planta. São grandezas diferentes, e juntá-las na mesma
tabela faria parecer que uma corrige a outra. Por isso `agencia_oficial` não existe no vocabulário de `fonte_tipo`, e a curadoria que o declarar
é recusada.

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
MEDIDAS = {"minerio_rom", "contido", "metal_em_concentrado", "produto_acabado", "embarque", "venda", "capacidade", "meta"}
ESCOPOS = {"operacao_goias", "consolidado_brasil", "consolidado_global"}
TIPOS = {"realizado", "guidance", "capacidade", "meta"}
PERIODOS = {"ano", "semestre", "trimestre", "mes"}
# Sem "agencia_oficial": a base publica o que a empresa declara, não o que a agência apura (ver o cabeçalho).
FONTES = {"ri_empresa", "imprensa_setorial", "imprensa_geral", "agregador_mercado"}
CONFIANCAS = {"alta", "media", "baixa"}


def norm(s):
    return unicodedata.normalize("NFD", str(s or "")).encode("ascii", "ignore").decode().upper().strip()


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
            # Linha de uma planta isolada não pode ser somada com a linha da empresa: viraria dupla contagem.
            "nivel": "operacao" if r.get("operacao_detalhe") else "empresa",
            "municipios": empresa["municipios"],
            "uf": empresa["uf"],
            "minerais_na_carga_ccee": empresa["minerais_na_carga_ccee"],
            "rateio_ccee": empresa["rateio_ccee"],
            "notas_energia": empresa["notas_energia"],
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
        "escopo_da_base": ("Só números declarados pela própria empresa. Estatística de agência (ANM, SGB) não entra: o Anuário Mineral "
                           "mede o contido no minério lavrado de um estado inteiro e a empresa publica o produto que saiu da planta — "
                           "grandezas diferentes, que não se corrigem."),
        "avisos": [
            "Toda linha nasce nao_validado. Importar não é validar (METODOLOGIA.md §1).",
            "Nada é convertido entre unidades. Onça troy (oz), tonelada (t) e quilo (kg) convivem sem fator de conversão.",
            "Trimestres e semestres NÃO somam para formar o ano: a empresa pode revisar o número no fechamento.",
            "Escopo 'consolidado_brasil' e 'consolidado_global' NÃO são produção de Goiás e não podem ser agregados ao estado.",
            "'embarque', 'venda', 'capacidade' e 'meta' não são produção realizada e não entram em série de produção: "
            "embarque e venda podem sair de estoque e deixar produção em pátio.",
            "Estatística da ANM não entra nesta base e não deve ser somada nem comparada linha a linha com estes números.",
        ],
    },
    "registros": registros,
}
SAIDA.mkdir(parents=True, exist_ok=True)
with open(SAIDA / "producao.json", "w", encoding="utf-8", newline="\n") as f:
    json.dump(pacote, f, ensure_ascii=False, indent=1)
    f.write("\n")

COLUNAS = ["id", "empresa", "grupo", "operacao", "nivel", "municipios", "uf", "mineral", "produto", "valor", "valor_max",
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
print(f"fonte: {por('fonte_tipo')}")
print(f"SALVO: {SAIDA / 'producao.json'} ({(SAIDA / 'producao.json').stat().st_size / 1e3:.1f} kB) e {SAIDA / 'producao.csv'}")
