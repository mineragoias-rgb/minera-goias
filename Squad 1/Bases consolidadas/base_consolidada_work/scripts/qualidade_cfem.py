# -*- coding: utf-8 -*-
"""Qualidade do CPF_CNPJ da CFEM, contada no arquivo em uso, para os textos da planilha (02b e catálogo de fontes).

Até a publicação de outubro de 2026, a ANM exportava o CNPJ da CFEM em notação científica ('9,69944E+11': 34.212 das 38.854
linhas de Goiás), o que impedia identificar a empresa. Na publicação de outubro de 2026 o CNPJ passou a vir completo. Os textos
saem destas contagens para valer com qualquer um dos dois arquivos.
"""
import re

CIENTIFICA = re.compile(r"[eE][+-]?\d+$")
COMPLETO = re.compile(r"^(\d{14}|\d{11})$")


def contar(docs):
    """Contagens do CPF_CNPJ: linhas, em notação científica, mascarados (CPF de pessoa física), completos (11 ou 14 dígitos)."""
    docs = [str(d).strip() for d in docs]
    return dict(linhas=len(docs), cientifica=sum(bool(CIENTIFICA.search(d)) for d in docs),
                mascarado=sum("*" in d for d in docs), completo=sum(bool(COMPLETO.match(d)) for d in docs))


def corrompido(q):
    return q["linhas"] > 0 and q["cientifica"] >= 0.5 * q["linhas"]


def n(v):
    return f"{v:,}".replace(",", ".")


def pct(parte, total, casas=0):
    return f"{100 * parte / total:.{casas}f}%".replace(".", ",") if total else "—"


def cobertura_ponte(p):
    """'93,1% das linhas e 90,1% do valor' a partir das contagens da ponte do processo (build_base3)."""
    if not p:
        return None
    return (pct(p["ponte_linhas"], p["ponte_linhas"] + p["ponte_sem_par"], 1) + " das linhas e "
            + pct(p["ponte_valor"], p["ponte_valor"] + p["ponte_valor_sem_par"], 1) + " do valor")


def achado_02b(q):
    """O achado (1) da aba 02b_crosswalk_empresas."""
    if corrompido(q):
        return (f"O campo CPF_CNPJ do CFEM está IRRECUPERAVELMENTE corrompido: {n(q['cientifica'])} das {n(q['linhas'])} linhas vieram "
                "em notação científica ('9,69944E+11') — o CNPJ virou float e perdeu precisão (sobram ~6 dígitos significativos de 14). "
                "Ele agrupa de forma estável, mas NÃO identifica a empresa, e o CFEM não tem coluna de nome.")
    return (f"O CPF_CNPJ do CFEM vem completo em {n(q['completo'])} das {n(q['linhas'])} linhas; {n(q['mascarado'])} são CPF de pessoa "
            f"física mascarado por LGPD e {n(q['cientifica'])} estão em notação científica. Até a publicação de outubro de 2026, a ANM "
            "exportava o CNPJ em notação científica ('9,69944E+11'), que não identifica a empresa. O CFEM continua sem coluna de nome.")


def limitacao_catalogo(q):
    """O trecho do CPF_CNPJ nas limitações da fonte SRC_ANM_CFEM (aba 07)."""
    if corrompido(q):
        return f"CPF_CNPJ IRRECUPERÁVEL: {pct(q['cientifica'], q['linhas'])} das linhas em notação científica ('9,69944E+11'); CPF de pessoa física mascarado por LGPD"
    return (f"CPF_CNPJ completo em {pct(q['completo'], q['linhas'])} das linhas (até out/2026 a ANM o exportava em notação científica); "
            f"CPF de pessoa física mascarado por LGPD ({pct(q['mascarado'], q['linhas'])})"
            + (f"; {pct(q['cientifica'], q['linhas'], 1)} ainda em notação científica" if q["cientifica"] else ""))


def aviso_titulares(q):
    """O aviso das colunas que contam titulares distintos pelo CPF_CNPJ."""
    if corrompido(q):
        return ("ATENÇÃO: contado pelo CPF_CNPJ da CFEM, que está corrompido (notação científica) — CNPJs diferentes podem colidir, "
                "então é um limite inferior aproximado. Recalcular pela ponte do número do processo (pendente).")
    return ("Contado pelo CPF_CNPJ da CFEM: cada CNPJ (matriz ou filial) conta como um titular, e o CPF de pessoa física vem "
            "mascarado por LGPD, então duas pessoas com a mesma parte visível contam como uma."
            + (f" {n(q['cientifica'])} linhas ainda em notação científica podem colidir." if q["cientifica"] else ""))
