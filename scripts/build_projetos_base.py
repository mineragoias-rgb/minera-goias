# -*- coding: utf-8 -*-
"""Base consolidada de projetos minerais de Goiás: gera o XLSX de três abas e o pacote JSON do portal.

    python scripts/build_projetos_base.py                  # usa a raiz do repositório onde está este script
    python scripts/build_projetos_base.py --repo <clone>

Lê a curadoria de `projetos/base_curada.json` e escreve:

- `Squad 1/entregas/projetos_minerais_goias.xlsx` — abas PROJETOS, NOTÍCIAS e METODOLOGIA;
- `data/projetos/projetos.json` — o mesmo conteúdo para a aba Base de dados do painel.

Um projeto é uma linha; uma fonte que sustenta vários projetos vira uma linha por projeto na aba NOTÍCIAS, ligada pelo ID. Campo sem
informação sai como `NA` — nunca estimativa, nunca número calculado a partir de outro projeto. O gerador recusa a curadoria que quebre as
regras: maturidade fora das sete categorias, projeto sem evidência, evidência órfã, ID repetido ou campo vazio em vez de `NA`.
"""
import argparse
import json
import sys
from datetime import date
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

sys.stdout.reconfigure(encoding="utf-8")
ap = argparse.ArgumentParser(description="Gera o XLSX e o JSON da base de projetos minerais de Goiás.")
ap.add_argument("--repo", default=str(Path(__file__).resolve().parents[1]), help="raiz do clone (padrão: a deste script)")
ap.add_argument("--xlsx", help="padrão: <repo>/Squad 1/entregas/projetos_minerais_goias.xlsx")
ap.add_argument("--json", dest="json_out", help="padrão: <repo>/data/projetos/projetos.json")
args = ap.parse_args()
REPO = Path(args.repo)
XLSX = Path(args.xlsx) if args.xlsx else REPO / "Squad 1" / "entregas" / "projetos_minerais_goias.xlsx"
JSON_OUT = Path(args.json_out) if args.json_out else REPO / "data" / "projetos" / "projetos.json"

VERSAO = "v1"
MATURIDADES = ["OPERAÇÃO", "EXPANSÃO", "CONSTRUÇÃO", "DEFINIDO", "PROVÁVEL", "POSSÍVEL", "SINAL"]
CONFIANCAS = {"ALTO", "MÉDIO", "BAIXO"}
RELEVANCIAS = {"ALTA", "MÉDIA", "BAIXA"}

COLS_PROJETOS = [
    ("ID", "id", 9), ("Projeto", "projeto", 40), ("Empresa", "empresa", 34), ("Empresa controladora", "controladora", 30),
    ("Parceiros / JV", "jv", 22), ("Mineral principal", "mineral", 20), ("Outros minerais", "outros", 16),
    ("Município", "municipio", 24), ("Estado", "estado", 8), ("Fase", "fase", 26), ("Maturidade", "maturidade", 13),
    ("Estágio detalhado", "estagio", 44), ("Status atual", "status", 40), ("Capacidade anunciada", "capacidade", 16),
    ("Unidade da capacidade", "cap_unidade", 34), ("Produção anual", "producao", 14), ("Unidade da produção", "prod_unidade", 34),
    ("CAPEX", "capex", 15), ("Moeda CAPEX", "moeda", 11), ("Ano do CAPEX", "ano_capex", 11),
    ("Previsão de entrada em operação", "entrada", 20), ("Ano previsto", "ano_entrada", 11),
    ("Data do anúncio", "anuncio", 13), ("Data da informação mais recente", "recente", 15),
    ("Grau de confiança", "confianca", 13), ("Evidência principal", "evidencia", 70), ("Fonte principal", "fonte", 40),
    ("Link principal", "link", 46), ("Outras evidências", "outras_ev", 26), ("Links adicionais", "links_add", 46),
    ("Observações", "obs", 70),
]
COLS_NOTICIAS = [
    ("ID da notícia", "id", 11), ("ID do projeto", "projeto_id", 11), ("Projeto", "projeto", 36), ("Empresa", "empresa", 30),
    ("Mineral", "mineral", 20), ("Município", "municipio", 22), ("Estado", "estado", 8), ("Data", "data", 10),
    ("Título", "titulo", 56), ("Veículo", "veiculo", 26), ("Tipo de fonte", "tipo", 22),
    ("Evidência extraída", "extrato", 70), ("Relevância", "relevancia", 11), ("Link", "link", 46),
    ("Data de acesso", "acesso", 13), ("Observações", "obs", 44),
]

AZUL, CINZA = "0F3D62", "EDF3F7"
TOM = {"OPERAÇÃO": "D6EADF", "EXPANSÃO": "DDEBF7", "CONSTRUÇÃO": "E2E0F3", "DEFINIDO": "FFF2CC",
       "PROVÁVEL": "FCE4D6", "POSSÍVEL": "F2F2F2", "SINAL": "FAFAFA"}
BORDA = Border(bottom=Side(style="thin", color="D5DEE5"))

base = json.loads((REPO / "projetos" / "base_curada.json").read_text(encoding="utf-8"))
projetos, evidencias = base["projetos"], base["evidencias"]

# --------------------------------------------------------------------------------------------------------- conferências de entrada
erros = []
vistos = set()
for p in projetos:
    onde = p.get("id", "(sem id)")
    if onde in vistos:
        erros.append(f"{onde}: ID repetido")
    vistos.add(onde)
    if p.get("maturidade") not in MATURIDADES:
        erros.append(f"{onde}: maturidade '{p.get('maturidade')}' fora das sete categorias")
    if p.get("confianca") not in CONFIANCAS:
        erros.append(f"{onde}: confiança '{p.get('confianca')}' fora do vocabulário")
    for chave, _, _ in [(c[1], 0, 0) for c in COLS_PROJETOS if c[1] not in ("estado", "outras_ev", "links_add")]:
        valor = p.get(chave)
        if valor is None or str(valor).strip() == "":
            erros.append(f"{onde}: campo '{chave}' vazio; use NA quando não houver informação")
    if not str(p.get("evidencia", "")).strip() or not str(p.get("link", "")).startswith("http"):
        erros.append(f"{onde}: sem evidência principal ou sem link")
ids = {p["id"] for p in projetos}
for e in evidencias:
    if e["projeto_id"] not in ids:
        erros.append(f"{e['id']}: evidência órfã, aponta para projeto inexistente")
    if e.get("relevancia") not in RELEVANCIAS:
        erros.append(f"{e['id']}: relevância '{e.get('relevancia')}' fora do vocabulário")
    if not str(e.get("link", "")).startswith("http"):
        erros.append(f"{e['id']}: sem link")
for pid in sorted(ids):
    if not any(e["projeto_id"] == pid for e in evidencias):
        erros.append(f"{pid}: nenhuma evidência ligada na aba NOTÍCIAS")
if erros:
    print("A curadoria não passou na conferência:")
    for erro in erros:
        print("  -", erro)
    sys.exit(1)

# --------------------------------------------------------------------------------- liga evidências ao projeto e ordena a base
por_projeto = {}
for e in evidencias:
    por_projeto.setdefault(e["projeto_id"], []).append(e)
for p in projetos:
    ligadas = por_projeto[p["id"]]
    p["estado"] = "GO"
    outras = [e for e in ligadas if e["link"] != p["link"]]
    p["outras_ev"] = "; ".join(e["id"] for e in outras) or "NA"
    p["links_add"] = " | ".join(dict.fromkeys(e["link"] for e in outras)) or "NA"
projetos.sort(key=lambda p: (MATURIDADES.index(p["maturidade"]), p["id"]))
ficha = {p["id"]: p for p in projetos}
evidencias.sort(key=lambda e: (MATURIDADES.index(ficha[e["projeto_id"]]["maturidade"]), e["projeto_id"], e["id"]))


def cabecalho(ws, colunas, titulo, subtitulo):
    """Cabeçalho fixo com nome da base, origem e data, como pedido para toda base do projeto."""
    largura = len(colunas)
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=largura)
    ws.cell(row=1, column=1, value=titulo).font = Font(bold=True, size=14, color="FFFFFF")
    ws.cell(row=1, column=1).fill = PatternFill("solid", fgColor=AZUL)
    ws.cell(row=1, column=1).alignment = Alignment(vertical="center", indent=1)
    ws.row_dimensions[1].height = 26
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=largura)
    ws.cell(row=2, column=2 - 1, value=subtitulo).font = Font(size=9, color="33516B")
    ws.cell(row=2, column=1).fill = PatternFill("solid", fgColor=CINZA)
    ws.cell(row=2, column=1).alignment = Alignment(vertical="center", indent=1, wrap_text=False)
    ws.row_dimensions[2].height = 18
    for i, (rotulo, _, largura_col) in enumerate(colunas, start=1):
        celula = ws.cell(row=3, column=i, value=rotulo)
        celula.font = Font(bold=True, size=9, color="FFFFFF")
        celula.fill = PatternFill("solid", fgColor=AZUL)
        celula.alignment = Alignment(vertical="center", wrap_text=True)
        ws.column_dimensions[get_column_letter(i)].width = largura_col
    ws.row_dimensions[3].height = 30
    ws.freeze_panes = "A4"
    ws.auto_filter.ref = f"A3:{get_column_letter(largura)}{3 + 1}"


livro = Workbook()
hoje = date.today().isoformat()

# ----------------------------------------------------------------------------------------------------------------- aba PROJETOS
ws = livro.active
ws.title = "PROJETOS"
cabecalho(ws, COLS_PROJETOS,
          "BASE CONSOLIDADA DE PROJETOS MINERAIS — GOIÁS",
          f"Origem: pesquisa em fontes públicas (RI, documentos regulatórios, órgãos públicos e imprensa) · "
          f"Última atualização: {base['pesquisa_em']} · Pacote {VERSAO} · {len(projetos)} projetos · "
          f"Campo sem informação = NA")
for linha, p in enumerate(projetos, start=4):
    for i, (_, chave, _) in enumerate(COLS_PROJETOS, start=1):
        celula = ws.cell(row=linha, column=i, value=p.get(chave, "NA"))
        celula.alignment = Alignment(vertical="top", wrap_text=chave in ("evidencia", "obs", "estagio", "status",
                                                                        "cap_unidade", "prod_unidade", "projeto"))
        celula.font = Font(size=9)
        celula.border = BORDA
        if chave == "maturidade":
            celula.fill = PatternFill("solid", fgColor=TOM[p["maturidade"]])
            celula.font = Font(size=9, bold=True)
        if chave in ("link", "links_add") and str(p.get(chave, "")).startswith("http"):
            celula.font = Font(size=9, color="0B6AA8", underline="single")
ws.auto_filter.ref = f"A3:{get_column_letter(len(COLS_PROJETOS))}{3 + len(projetos)}"

# ----------------------------------------------------------------------------------------------------------------- aba NOTÍCIAS
wn = livro.create_sheet("NOTÍCIAS")
cabecalho(wn, COLS_NOTICIAS,
          "EVIDÊNCIAS, NOTÍCIAS E DOCUMENTOS — PROJETOS MINERAIS DE GOIÁS",
          f"Origem: fontes públicas citadas em cada linha · Última atualização: {base['pesquisa_em']} · "
          f"{len(evidencias)} evidências ligadas a {len(ids)} projetos pelo ID do projeto")
for linha, e in enumerate(evidencias, start=4):
    p = ficha[e["projeto_id"]]
    valores = {**e, "projeto": p["projeto"], "empresa": p["empresa"], "mineral": p["mineral"],
               "municipio": p["municipio"], "estado": "GO", "acesso": base["pesquisa_em"]}
    for i, (_, chave, _) in enumerate(COLS_NOTICIAS, start=1):
        celula = wn.cell(row=linha, column=i, value=valores.get(chave, "NA"))
        celula.alignment = Alignment(vertical="top", wrap_text=chave in ("extrato", "titulo", "obs", "projeto"))
        celula.font = Font(size=9)
        celula.border = BORDA
        if chave == "link":
            celula.font = Font(size=9, color="0B6AA8", underline="single")
wn.auto_filter.ref = f"A3:{get_column_letter(len(COLS_NOTICIAS))}{3 + len(evidencias)}"

# -------------------------------------------------------------------------------------------------------------- aba METODOLOGIA
METODOLOGIA = [
    ("Objetivo", "Reunir, com rastreabilidade, os projetos minerais de Goiás em qualquer estágio — da operação ao indício de "
                 "investimento — para inteligência de mercado e acompanhamento do pipeline do estado."),
    ("Abrangência", "Estado de Goiás, todos os minerais e todos os portes de empresa. Entram operação, expansão, construção, "
                    "implantação, desenvolvimento, viabilidade, pré-viabilidade, pesquisa mineral, exploração, licenciamento, "
                    "projeto anunciado, projeto potencial, reativação, retomada e projeto suspenso ainda relevante."),
    ("Período da pesquisa", f"Coleta feita em {base['pesquisa_em']}. A coluna 'Data da informação mais recente' diz, por projeto, "
                            "a que momento o registro se refere."),
    ("Fontes", "Sites e relatórios de empresas, comunicados ao mercado, documentos regulatórios (SEC, NI 43-101), órgãos públicos "
               "(governo de Goiás, SIC, ANM, MME), associações setoriais (IBRAM, MINDE) e imprensa especializada e regional. "
               "Cada linha traz o endereço da fonte que sustenta a informação."),
    ("Critérios de inclusão", "Entra o projeto com pelo menos uma evidência pública localizável que sustente sua existência, a "
                              "empresa quando houver, o mineral e o município quando declarados. Projeto de confiança BAIXA "
                              "permanece quando relevante, sinalizado na coluna de confiança."),
    ("Critérios de exclusão", "Ficam de fora o processo minerário puramente cadastral sem projeto nomeado — esse universo já está "
                              "no atlas deste repositório, com 3.377 processos da aba 04 da base do Squad 1 — e a menção que não "
                              "identifique nem empresa, nem mineral, nem município."),
    ("Critérios de maturidade", "Sete categorias, nesta hierarquia: OPERAÇÃO > EXPANSÃO > CONSTRUÇÃO > DEFINIDO > PROVÁVEL > "
                                "POSSÍVEL > SINAL. OPERAÇÃO é o projeto que já produz comercialmente; EXPANSÃO é a operação com "
                                "projeto formal de aumento de capacidade; CONSTRUÇÃO é a implantação efetivamente iniciada; "
                                "DEFINIDO exige viabilidade concluída, decisão de investimento, financiamento ou licença de "
                                "instalação; PROVÁVEL tem evidência forte sem essa definição; POSSÍVEL é estágio inicial com "
                                "evidência razoável; SINAL é indício inicial. Maturidade mede o grau de comprovação econômica, "
                                "não a etapa administrativa: por isso FASE e MATURIDADE são colunas separadas."),
    ("Regras de deduplicação", "Um empreendimento é uma linha, por mais notícias que tenha. Projetos economicamente distintos ficam "
                               "separados mesmo sob a mesma empresa — Saúva está separado de Chapada por ter cava e decisão de "
                               "investimento próprias; a fábrica de argamassa de Edealina está separada da expansão de cimento. "
                               "Plantas em municípios diferentes ficam separadas mesmo quando o resultado é publicado em conjunto, "
                               "como Barro Alto e Codemin."),
    ("Regras de CAPEX", "Somente CAPEX publicamente divulgado, na moeda original, sem conversão e sem estimativa a partir de outro "
                        "projeto. Divergência entre fontes é registrada em Observações, com o valor escolhido e o motivo."),
    ("Regras de capacidade", "Somente capacidade explicitamente anunciada, na unidade original, declarada na coluna 'Unidade da "
                             "capacidade'. Linguagem de potencial não vira capacidade: 'poderia dobrar a produção' permanece como "
                             "texto em Observações, não como número."),
    ("Regras de previsão de entrada", "Registrada a previsão mais recente encontrada, na forma em que a fonte a publica (ano, "
                                      "semestre ou trimestre). Quando há previsão antiga e nova, fica a nova e a mudança é "
                                      "registrada em Observações."),
    ("Critérios de confiança", "ALTO: fonte primária, documento oficial, licença ou relatório empresarial recente. MÉDIO: imprensa "
                               "especializada confiável ou múltiplas fontes independentes consistentes. BAIXO: fonte secundária, "
                               "notícia antiga, diretório setorial ou evidência indireta."),
    ("Fontes conflitantes", "Prioridade: documento regulatório, empresa, órgão público, estudo técnico, imprensa especializada, "
                            "imprensa geral, outras fontes — e, dentro do mesmo nível, a informação mais recente. A divergência "
                            "relevante fica registrada em Observações em vez de desaparecer."),
    ("Significado de NA", "NA significa que a informação não foi encontrada em fonte pública durante esta pesquisa. Não significa "
                          "zero, não significa ausência do atributo e nunca foi substituído por estimativa."),
    ("Limitações da pesquisa", base["limitacao_da_coleta"] + " Em consequência: (1) a cobertura não é exaustiva — uma reportagem "
                               "de agosto de 2026 cita pelo menos 18 empresas estrangeiras com processos de terras raras no Brasil "
                               "sem nomeá-las, e esta base não as alcança; (2) os projetos de titânio e manganês vindos do "
                               "mapeamento estadual entram sem empresa e sem data, como SINAL, porque o documento não foi lido na "
                               "origem; (3) areia, brita, argila, rochas ornamentais, quartzito e água mineral estão sub-representados, "
                               "porque raramente geram projeto nomeado na imprensa, ainda que respondam por muitos títulos minerários "
                               "no estado; (4) nenhum processo de licenciamento ambiental foi consultado diretamente no sistema "
                               "estadual. O caminho para fechar essas lacunas é a consulta direta ao SIGMINE/ANM, ao sistema de "
                               "licenciamento da SEMAD e aos arquivos da SEC, da CVM e do SEDAR+."),
    ("Relação com as demais bases do repositório", "Esta base é de projetos nomeados, com empresa, CAPEX e cronograma. Ela não "
                                                   "substitui nem repete: o atlas traz o pipeline cadastral da ANM; data/producao "
                                                   "traz a produção declarada pelas empresas; data/empresas cruza produção com a "
                                                   "carga de energia da CCEE. A aba Base de dados do painel lista todas elas."),
]
wm = livro.create_sheet("METODOLOGIA")
cabecalho(wm, [("Item", "item", 34), ("Descrição", "texto", 150)],
          "METODOLOGIA — BASE CONSOLIDADA DE PROJETOS MINERAIS DE GOIÁS",
          f"Origem: critérios adotados nesta pesquisa · Última atualização: {base['pesquisa_em']} · Pacote {VERSAO}")
for linha, (item, texto) in enumerate(METODOLOGIA, start=4):
    a = wm.cell(row=linha, column=1, value=item)
    a.font = Font(bold=True, size=9)
    a.alignment = Alignment(vertical="top", wrap_text=True)
    a.border = BORDA
    b = wm.cell(row=linha, column=2, value=texto)
    b.font = Font(size=9)
    b.alignment = Alignment(vertical="top", wrap_text=True)
    b.border = BORDA
    wm.row_dimensions[linha].height = max(30, 12 * (len(texto) // 115 + 1))
wm.auto_filter.ref = None

XLSX.parent.mkdir(parents=True, exist_ok=True)
livro.save(XLSX)

# ----------------------------------------------------------------------------------------------------------------- pacote JSON
JSON_OUT.parent.mkdir(parents=True, exist_ok=True)
pacote = {
    "meta": {
        "built_on": hoje,
        "versao_base": VERSAO,
        "gerado_por": "scripts/build_projetos_base.py",
        "curadoria": "projetos/base_curada.json",
        "pesquisa_em": base["pesquisa_em"],
        "xlsx": "Squad 1/entregas/projetos_minerais_goias.xlsx",
        "limitacao_da_coleta": base["limitacao_da_coleta"],
        "maturidades": MATURIDADES,
        "metodologia": [{"item": i, "texto": t} for i, t in METODOLOGIA],
    },
    "projetos": projetos,
    "evidencias": evidencias,
}
with open(JSON_OUT, "w", encoding="utf-8", newline="\n") as f:
    json.dump(pacote, f, ensure_ascii=False, indent=1)
    f.write("\n")

# ----------------------------------------------------------------------------------------------------------------- conferências
conta = lambda campo: ", ".join(f"{k} {v}" for k, v in sorted(
    {x: sum(1 for p in projetos if p[campo] == x) for x in {p[campo] for p in projetos}}.items(),
    key=lambda kv: -kv[1]))
print(f"projetos: {len(projetos)} · evidências: {len(evidencias)} · municípios citados: "
      f"{len({m.strip() for p in projetos for m in p['municipio'].split(';') if m.strip() != 'NA'})}")
print(f"maturidade: " + ", ".join(f"{m} {sum(1 for p in projetos if p['maturidade'] == m)}" for m in MATURIDADES))
print(f"confiança: {conta('confianca')}")
print(f"minerais: {conta('mineral')}")
print(f"com CAPEX divulgado: {sum(1 for p in projetos if p['capex'] != 'NA')} · "
      f"com capacidade anunciada: {sum(1 for p in projetos if p['capacidade'] != 'NA')} · "
      f"com previsão de entrada: {sum(1 for p in projetos if p['entrada'] != 'NA')}")
print(f"SALVO: {XLSX} ({XLSX.stat().st_size / 1e3:.1f} kB) e {JSON_OUT} ({JSON_OUT.stat().st_size / 1e3:.1f} kB)")
