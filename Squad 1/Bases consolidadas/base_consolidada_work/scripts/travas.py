# -*- coding: utf-8 -*-
"""Travas da atualização: decide, pela aba 14b da planilha gerada, se a base nova pode ser publicada.

    python travas.py PLANILHA.xlsx                    # 0 = pode seguir; 3 = travou (a mensagem diz o que fazer)
    python travas.py PLANILHA.xlsx --antes ANTERIOR.xlsx   # também trava se uma verificação sumiu da 14b
    python travas.py --tabela                         # imprime, em Markdown, o nível de cada erro do repositório (ATUALIZACAO.md)

Cada verificação da 14b tem um nível (lista CHECAGENS abaixo):
  • bloqueia — ALERTA trava a atualização: rodar_pipeline.py termina com código 3 e o robô do GitHub não publica;
  • avisa    — ALERTA aparece no relatório, mas não trava (sinalizações que o pipeline mantém de propósito, comparações informativas).
Os alertas que a base atual já tem e que o grupo aceitou ficam em erros_conhecidos.json → "alertas_aceitos", com o n aceito e o
motivo: ALERTA com n até o aceito passa como "aceito"; acima disso vale o nível da verificação. Verificação que não está na lista
CHECAGENS trava se der ALERTA (classifique-a aqui antes de publicar).

Usado por rodar_pipeline.py (fim do pipeline) e por robo/robo_bases.py --conferir-planilha (workflow do GitHub). Só lê a planilha.
"""
import json
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
CONHECIDOS = os.path.join(AQUI, "erros_conhecidos.json")
ABA = "14b_validacoes_governanca"

B, A = "bloqueia", "avisa"
# (início do nome da verificação na 14b, nível, erros do repositório que ela detecta, por que esse nível)
CHECAGENS = [
    ("Cabeçalhos renomeados", B, "ERR_042", "cabeçalho fora do contrato quebra quem lê a planilha (Squad 2, site)"),
    ("Nomes de coluna fora do padrão", B, "ERR_042", "estrutura da planilha"),
    ("Nomes de coluna duplicados", B, "ERR_042", "estrutura da planilha"),
    ("Campos do Contrato de Dados", B, "", "o Contrato de Dados fixa esses nomes"),
    ("Campos do fluxo Squad 1 → Squad 2", B, "", "campo do fluxo vazio = entrega ao Squad 2 quebrada"),
    ("Mesma coluna com tipo diferente", B, "", "estrutura da planilha"),
    ("Colunas sem descrição no dicionário", B, "ERR_035", "todo campo novo precisa estar no dicionário 14"),
    ("Valores em source_ids que não são ID", B, "", "rastreabilidade da fonte"),
    ("Fontes citadas em source_ids sem registro", B, "", "rastreabilidade da fonte"),
    ("Fontes catalogadas que nenhuma aba real cita", A, "", "informativa: fontes catalogadas para uso futuro"),
    ("Arquivos de dados/ sem source_id", B, "", "arquivo bruto novo precisa entrar no catálogo 07 antes de ser usado"),
    ("IDs fora do padrão", B, "", "IDs estáveis são a chave do projeto"),
    ("LGPD", B, "ERR_025", "CPF completo não pode ser publicado"),
    ("Integridade referencial", B, "ERR_020, ERR_021", "chave sem dimensão = número que não soma em lugar nenhum"),
    ("Colunas 100% vazias", A, "", "placeholders declarados no contrato"),
    ("Quantidade comercializada da CFEM", B, "ERR_011, ERR_012", "unidade misturada ou valor corrompido sem tratamento distorce as somas"),
    ("Plausibilidade: CFEM", A, "ERR_015", "sinalizado de propósito: a quantidade da CFEM é declaração do contribuinte"),
    ("Processos com quantidade na CFEM implausível", A, "ERR_006, ERR_015, ERR_016", "mantidos na soma e sinalizados na 09c, de propósito"),
    ("Rochas na CFEM", A, "ERR_018", "informativa: de onde veio a categoria das rochas"),
    ("IMB (Goiás em Dados) × AMB", A, "ERR_037", "checagem cruzada informativa"),
    ("08: cada célula numérica das fontes", B, "ERR_017", "célula da fonte perdida ou contada duas vezes"),
    ("08 → 09/10/11", B, "ERR_005, ERR_014", "as abas consolidadas têm de ser a soma da 08"),
    ("08: campos de governança por linha", B, "ERR_041", "fonte, URL e data de cada linha (Entrega §3)"),
    ("§3 da Entrega", B, "", "campos obrigatórios da Entrega Avaliativa"),
    ("08: mesma tonelagem de produção", A, "ERR_001, ERR_002",
     "co-produto ou mesma declaração em duas categorias: mantido e sinalizado (inclui bário × nióbio no ROM de 2023, sem correção)"),
    ("Repositório de erros (ERR_003/004)", B, "ERR_003, ERR_004", "contido incoerente novo no AMB de GO: conferir antes de publicar"),
    ("Repositório de erros (ERR_005)", B, "ERR_005", "quebra de série nova (o caso do nióbio em 2024): conferir o conceito antes de publicar"),
    ("Repositório de erros (ERR_007)", A, "ERR_007", "lacuna é fato da fonte (a ANM não publicou o mineral no ano)"),
    ("Repositório de erros (ERR_043–045)", A, "ERR_009, ERR_043, ERR_044, ERR_045",
     "comparação econômica: todo ano novo traz pares sem correspondência; conferir, mas não trava"),
    ("Repositório de erros (ERR_013)", B, "ERR_013", "CNPJ em notação científica não identifica a empresa (abas 02 e 11)"),
    ("Repositório de erros (ERR_024)", B, "ERR_024", "linha de Goiás descartada em silêncio pelo leitor do Cadastro Mineiro"),
    ("12: nível estado = produção de GO", B, "ERR_005", "entrega ao Squad 2 tem de fechar com a 08"),
    ("12: cobertura da abertura por operação", A, "", "informativa: quanto da produção foi aberta por operação"),
    ("12: governança por linha", B, "", "estimado com método e intervalo (Entrega §3)"),
    ("04: cada processo vivo", B, "ERR_030", "processo vivo fora de projeto ou em dois"),
    ("04: classificação refeita", B, "", "classificação dos projetos reproduzível"),
    ("04: governança por linha", B, "", "Entrega §3; nada inventado"),
    ("06: recorte refeito", B, "", "ocorrências de Goiás exatamente uma vez"),
    ("06: campos do RECMIN fora da aba", A, "ERR_032", "informativa: campos sem informação na fonte"),
    ("13: toda camada do catálogo", B, "", "mapa do site lê esses arquivos"),
    ("06: substâncias → mineral_ids", B, "ERR_033", "substância sem decisão ou mineral novo fora da 01"),
    ("06: governança por linha", B, "", "Entrega §3"),
]

# erros do repositório sem checagem que dê para automatizar na 14b, e por quê (os demais estão nas CHECAGENS acima)
SEM_CHECAGEM = {
    "ERR_008": "contido sem indicação é o padrão da fonte (C3 é só informativo na 15d); não há valor certo para comparar",
    "ERR_010": "a ANM republica dados preliminares: não é erro do dado novo; o relatório de diferenças mostra o que mudou",
    "ERR_019": "o último ano da CFEM é parcial por natureza; o pipeline marca periodo_referencia, não há o que travar",
    "ERR_022": "característica da fonte (dados abertos só com processos ativos)",
    "ERR_023": "característica da fonte (jurisdição regional da ANM); tratada pelo recorte por município",
    "ERR_026": "detectado comparando dois arranjos de dados (v16), à mão; não há assinatura num arquivo só",
    "ERR_027": "geometria (UF do SIGMINE) — auditada na 13b, sem assinatura simples para travar",
    "ERR_028": "geometria (autointerseção) — corrigida no pipeline e auditada na 13b",
    "ERR_029": "geometria × cadastro (desmembramentos) — auditada na 13b",
    "ERR_031": "geometria (simplificação) — auditada na 13b",
    "ERR_034": "regra de leitura do SIDRA (linha da UF), conferida na montagem da 05/07",
    "ERR_036": "geometria (centroide) — auditada na 13b",
    "ERR_038": "CCEE não entra na planilha consolidada",
    "ERR_039": "reprodutibilidade: se vê rodando duas vezes e comparando (relatório de diferenças vazio)",
}
# checado fora da 14b, pelo manifesto dos brutos (manifesto_brutos.py), antes de o pipeline rodar
MANIFESTO = {"ERR_040": (B, "arquivo bruto mudou de bytes sem nova data de acesso (download não registrado ou quebra de linha trocada)")}


def _ler_json(caminho):
    with open(caminho, encoding="utf-8") as f:
        return json.load(f)


def ler_14b(caminho):
    import openpyxl
    wb = openpyxl.load_workbook(caminho, read_only=True, data_only=True)
    linhas = list(wb[ABA].iter_rows(values_only=True))
    wb.close()
    cab = next(i for i, ln in enumerate(linhas) if ln and ln[0] == "verificacao")
    return {str(ln[0]): (ln[1], str(ln[2] or ""), str(ln[3] or "")) for ln in linhas[cab + 1:] if ln and ln[0]}


def nivel(nome):
    for prefixo, niv, erros, motivo in CHECAGENS:
        if nome.startswith(prefixo):
            return prefixo, niv, erros, motivo
    return None, B, "", "verificação sem nível definido em travas.py"


def aceitos():
    if not os.path.exists(CONHECIDOS):
        return {}
    return _ler_json(CONHECIDOS).get("alertas_aceitos", {})


def _int(n):
    try:
        return int(n)
    except (TypeError, ValueError):
        return None


def conferir(depois, antes=None):
    """(bloqueios, avisos, linhas) — bloqueios vazio = pode publicar. linhas = tabela Markdown de tudo que não está OK."""
    d = ler_14b(depois)
    a = ler_14b(antes) if antes else {}
    ac = aceitos()
    bloqueios, avisos = [], []
    linhas = ["| Verificação | Status | n | Nível | Decisão |", "|---|---|---|---|---|"]
    for nome, (n, resultado, status) in d.items():
        prefixo, niv, erros, motivo = nivel(nome)
        if "não executad" in resultado:  # a checagem caiu num erro e a governança seguiu: OK sem ter conferido não vale
            bloqueios.append(f"{nome[:110]}: a checagem não rodou ({resultado[:250]}). Corrija a causa e rode de novo.")
            linhas.append(f"| {nome[:90]} | {status} | {n} | {niv} | **TRAVA** (não executada) |")
            continue
        if status == "OK":
            if prefixo is None:
                avisos.append(f"{nome[:100]}: verificação nova sem nível em travas.py (está OK; classifique-a)")
            continue
        aceito = next((v for k, v in ac.items() if nome.startswith(k)), None)
        if aceito is not None and _int(n) is not None and _int(n) <= int(aceito["n_aceito"]):
            decisao = f"aceito (n ≤ {aceito['n_aceito']})"
        elif niv == B:
            extra = f" — acima do aceito ({aceito['n_aceito']})" if aceito else ""
            bloqueios.append(f"{nome[:110]} → {status}, n={n}{extra}. {resultado[:300]}"
                             + (f" [{erros}]" if erros else "") + f" Por que trava: {motivo}.")
            decisao = "**TRAVA**"
        else:
            avisos.append(f"{nome[:110]} → {status}, n={n}" + (f" (aceito até {aceito['n_aceito']})" if aceito else "")
                          + f". {resultado[:200]}")
            decisao = "aviso"
        linhas.append(f"| {nome[:90]} | {status} | {n} | {niv} | {decisao} |")
    for nome in a:
        if nome not in d:
            bloqueios.append(f"verificação sumiu da aba 14b: {nome[:110]}")
    return bloqueios, avisos, linhas


def texto(bloqueios, avisos, linhas):
    out = linhas[:] if len(linhas) > 2 else ["Todas as verificações da 14b estão OK."]
    out += [""] + [f"TRAVA: {b}" for b in bloqueios] + [f"aviso: {x}" for x in avisos]
    if bloqueios:
        out += ["", f"ATUALIZAÇÃO TRAVADA: {len(bloqueios)} trava(s) — verificação de nível 'bloqueia' com ALERTA acima do aceito, checagem que não rodou ou verificação que sumiu. A planilha foi gravada para "
                "inspeção, mas NÃO deve ser publicada. Para cada trava: abra a aba 14b, veja o resultado e a aba citada; se for erro "
                "do dado ou do pipeline, corrija e rode de novo; se for uma ocorrência nova legítima (conferida na fonte), registre-a "
                "(gerar_repositorio_erros.py --atualizar-conhecidos, ou o n aceito em erros_conhecidos.json → alertas_aceitos, com o "
                "motivo) e rode de novo. Passo a passo: Squad 1/Bases consolidadas/ATUALIZACAO.md."]
    else:
        out += ["", "travas: nenhuma verificação de nível 'bloqueia' com ALERTA — pode seguir"
                + (f" ({len(avisos)} aviso(s) para conferir)" if avisos else "")]
    return "\n".join(out)


def tabela_erros():
    """Nível de cada ERR_### do repositório (para o ATUALIZACAO.md)."""
    nivel_err = {}
    for prefixo, niv, erros, motivo in CHECAGENS:
        for e in filter(None, (x.strip() for x in erros.split(","))):
            nivel_err.setdefault(e, []).append((niv, prefixo, motivo))
    for e, (niv, motivo) in MANIFESTO.items():
        nivel_err.setdefault(e, []).append((niv, "manifesto dos brutos (manifesto_brutos.py)", motivo))
    out = ["| Erro | Nível | Onde é checado | Por quê |", "|---|---|---|---|"]
    for i in range(1, 46):
        e = f"ERR_{i:03d}"
        if e in nivel_err:
            vs = nivel_err[e]
            niv = B if any(v[0] == B for v in vs) else A
            out.append(f"| {e} | {'trava' if niv == B else 'só avisa'} | " + "; ".join(f"14b: {v[1]}…" if "manifesto" not in v[1] else v[1] for v in vs)
                       + " | " + "; ".join(dict.fromkeys(v[2] for v in vs)) + " |")
        else:
            out.append(f"| {e} | sem checagem automática | — | {SEM_CHECAGEM.get(e, '(sem justificativa: classifique em travas.py)')} |")
    return "\n".join(out)


def main(argv):
    import argparse
    ap = argparse.ArgumentParser(description="Travas da atualização da base consolidada (aba 14b).")
    ap.add_argument("planilha", nargs="?")
    ap.add_argument("--antes", help="planilha anterior: trava se uma verificação sumiu da 14b")
    ap.add_argument("--tabela", action="store_true", help="imprime o nível de cada erro do repositório e sai")
    args = ap.parse_args(argv)
    if args.tabela:
        print(tabela_erros())
        return 0
    if not args.planilha:
        ap.error("informe a planilha")
    b, a, ln = conferir(args.planilha, args.antes)
    print(texto(b, a, ln))
    return 3 if b else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main(sys.argv[1:]))
