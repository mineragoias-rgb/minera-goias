# -*- coding: utf-8 -*-
"""Conversão de um CSV da ANM publicado em outro formato para o formato do arquivo que o repositório guarda.

Em outubro de 2026 a ANM passou a publicar a CFEM separada por vírgula e com aspas em todos os campos. O repositório, o
pipeline do Squad 1 e o Radar leem o formato antigo: ponto e vírgula, sem aspas, cp1252, CRLF. A conversão muda só o formato:

- separador, aspas, codificação e quebra de linha passam a ser os do arquivo atual;
- coluna numérica: o separador decimal volta a ser o do arquivo atual (ponto vira vírgula; separador de milhar sai);
- coluna de data: a data volta ao padrão do arquivo atual (ex.: '2026-08-31 14:05:00' vira '31/08/2026 14:05');
- o resto do valor fica como a ANM publicou. O que a ANM corrigiu (ex.: CNPJ completo no lugar da notação científica) entra
  corrigido, porque continua cabendo no formato antigo.

Barra o arquivo (ValueError) quando a conversão não é segura: cabeçalho diferente do atual, coluna com dois estilos de número,
valor com o separador antigo, aspas ou quebra de linha (o formato antigo não tem como representar), caractere fora da
codificação antiga. A checagem de forma (forma.checar_csv) confere o resultado contra o arquivo atual, como em qualquer fonte.
"""
import collections
import csv
import datetime as dt
import io
import re

import forma

SEPARADORES = (",", ";", "\t", "|")
FORMATOS_DATA = {"99/99/9999 99:99": "%d/%m/%Y %H:%M", "99/99/9999 99:99:99": "%d/%m/%Y %H:%M:%S", "99/99/9999": "%d/%m/%Y",
                 "9999-99-99": "%Y-%m-%d", "9999-99-99 99:99:99": "%Y-%m-%d %H:%M:%S", "9999-99-99 99:99": "%Y-%m-%d %H:%M"}
# datas que dá para ler sem ambiguidade (ISO, ou dia/mês/ano com segundos, no mesmo padrão dia/mês do formato antigo)
LEITURA_DATA = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%d %H:%M",
                "%Y-%m-%d", "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M")


def forma_do_valor(v):
    """'41474,14' -> '99999,99'; 'ANÁPOLIS' -> 'aaaaaaaa'. Serve ao diagnóstico sem expor dado."""
    return re.sub(r"[^\W\d_]", "a", re.sub(r"\d", "9", v))


def decodificar(dados, codificacao):
    if dados.startswith(b"\xef\xbb\xbf"):
        return dados[3:].decode("utf-8"), "utf-8"
    try:
        return dados.decode("utf-8"), "utf-8"  # texto com acento em cp1252 quase nunca é UTF-8 válido
    except UnicodeDecodeError:
        return dados.decode(codificacao), codificacao


def separador_do(cab_linha, cab_atual):
    """O separador com que a primeira linha vira exatamente o cabeçalho atual; None se nenhum serve."""
    for s in SEPARADORES:
        try:
            if [c.strip() for c in next(csv.reader([cab_linha], delimiter=s))] == cab_atual:
                return s
        except (csv.Error, StopIteration):
            continue
    return None


AMBIGUO = "?"


def _separadores_numero(valores):
    """(decimal, milhar) de uma coluna numérica. Nos valores com os dois sinais, o decimal é o último. AMBIGUO quando a coluna
    não decide: valores só com ponto ao lado de valores só com vírgula, ou o último sinal variando."""
    so_ponto = [v for v in valores if "." in v and "," not in v]
    so_virgula = [v for v in valores if "," in v and "." not in v]
    os_dois = [v for v in valores if "," in v and "." in v]
    if os_dois:
        ultimos = {"," if v.rfind(",") > v.rfind(".") else "." for v in os_dois}
        if len(ultimos) > 1:
            return AMBIGUO, AMBIGUO
        dec = ultimos.pop()
        return dec, "." if dec == "," else ","
    if so_ponto and so_virgula:
        return AMBIGUO, AMBIGUO
    if so_ponto:  # vários pontos num valor só é milhar ('1.234.567'); um ponto só é decimal
        return (None, ".") if all(v.count(".") > 1 for v in so_ponto) else (".", None)
    return ("," if so_virgula else None), None


def _numero(v, dec, milhar, dec_antigo):
    if not v:
        return v
    if milhar:
        v = v.replace(milhar, "")
    if dec and dec != dec_antigo:
        v = v.replace(dec, dec_antigo)
    return v


def _data(v, formato_antigo):
    for f in LEITURA_DATA:
        try:
            return dt.datetime.strptime(v, f).strftime(formato_antigo)
        except ValueError:
            continue
    return None


def converter(dados, atual, codificacao, separador, coluna=None, valor=None):
    """Converte `dados` (o arquivo nacional, em qualquer dialeto) para o formato de `atual` (bytes do arquivo do repositório),
    ficando só com as linhas em que `coluna` == `valor` quando pedido.

    Devolve None quando `dados` já está no formato antigo (o recorte byte a byte de anm_recorte serve), ou
    (bytes, contagens, notas, diagnostico)."""
    cab_a, lin_a, brutos_a = forma.ler_csv(atual, codificacao, separador)
    texto, cod_nova = decodificar(dados, codificacao)
    cab_linha = texto.split("\n", 1)[0].rstrip("\r")
    sep = separador_do(cab_linha, cab_a)
    if sep is None:
        raise ValueError(f"o cabeçalho não bate com o do arquivo atual em nenhum separador; cabeçalho: {cab_linha[:300]}")
    if sep == separador and '"' not in cab_linha and cod_nova == codificacao:
        return None
    leitor = csv.reader(io.StringIO(texto, newline=""), delimiter=sep, quotechar='"')
    next(leitor)
    i_filtro = cab_a.index(coluna) if coluna else None
    linhas, total, tortas = [], 0, 0
    for row in leitor:
        if not row or (len(row) == 1 and not row[0].strip()):
            continue
        total += 1
        if len(row) != len(cab_a):
            tortas += 1
        if i_filtro is not None and not (len(row) > i_filtro and row[i_filtro].strip() == valor):
            continue
        linhas.append(row)

    notas = [f"a fonte veio em outro formato (separador '{sep}', {'com' if chr(34) in cab_linha else 'sem'} aspas, {cod_nova}) "
             f"e foi convertida para o do repositório (separador '{separador}', sem aspas, {codificacao})"]
    perfil = forma.perfil_colunas(cab_a, lin_a)
    for i, nome in enumerate(cab_a):
        antigos = [ln[i].strip() for ln in lin_a if i < len(ln) and ln[i].strip()]
        novos = [ln[i] for ln in linhas if i < len(ln)]
        tipo = perfil[nome]["tipo"]
        if tipo in ("inteiro", "decimal"):
            dec_antigo, _ = _separadores_numero(antigos)
            dec, milhar = _separadores_numero([v.strip() for v in novos if v.strip()])
            if dec == AMBIGUO:
                raise ValueError(f"a coluna '{nome}' mistura dois estilos de número; não dá para converter com segurança")
            if dec_antigo in (",", ".") and ((dec and dec != dec_antigo) or milhar):
                mudou = 0
                for ln in linhas:
                    if i < len(ln):
                        novo = _numero(ln[i], dec, milhar, dec_antigo)
                        mudou += novo != ln[i]
                        ln[i] = novo
                if mudou:
                    notas.append(f"{nome}: separador decimal '{dec or '-'}' → '{dec_antigo}'" + (f", milhar '{milhar}' retirado" if milhar else "")
                                 + f" ({mudou} valores)")
        elif tipo == "data":
            formas_antigas = collections.Counter(forma_do_valor(v) for v in antigos)
            principal = formas_antigas.most_common(1)[0][0] if formas_antigas else None
            formato = FORMATOS_DATA.get(principal)
            if formato:
                mudou = 0
                for ln in linhas:
                    if i < len(ln) and ln[i].strip() and forma_do_valor(ln[i].strip()) not in formas_antigas:
                        novo = _data(ln[i].strip(), formato)
                        if novo is not None:
                            ln[i] = novo
                            mudou += 1
                if mudou:
                    notas.append(f"{nome}: data no padrão do arquivo atual ({mudou} valores)")

    ruins = collections.Counter(cab_a[i] if i < len(cab_a) else f"coluna {i + 1}"
                                for ln in linhas for i, v in enumerate(ln) if separador in v or '"' in v or "\n" in v or "\r" in v)
    if ruins:
        raise ValueError("valores com o separador antigo, aspas ou quebra de linha, que o formato antigo não representa: "
                         + ", ".join(f"{c} ({n})" for c, n in ruins.most_common()))
    fim = "\r\n" if brutos_a and brutos_a[0].endswith("\r\n") else "\n"
    bom = b"\xef\xbb\xbf" if atual.startswith(b"\xef\xbb\xbf") else b""
    saida = brutos_a[0] + "".join(separador.join(ln) + fim for ln in linhas)
    try:
        convertido = bom + saida.encode(codificacao)
    except UnicodeEncodeError as e:
        raise ValueError(f"caractere que {codificacao} não representa: {e.object[e.start:e.end]!r}") from None
    return convertido, {"linhas_nacional": total, "linhas_goias": len(linhas), "linhas_tortas": tortas}, notas, \
        diagnostico(cab_a, lin_a, linhas, brutos_a, saida, fim)


def diagnostico(cab, lin_a, lin_n, brutos_a, saida, fim):
    """Para o log: as formas mais comuns de cada coluna (dígito vira 9, letra vira a), antes e depois, e quanto do arquivo atual
    reaparece igual no convertido. Nenhum valor vai para o log."""
    linhas_novas = set(saida.split(fim)[1:])
    iguais = sum(1 for b in brutos_a[1:] if b.rstrip("\r\n") in linhas_novas)
    texto = [f"linhas do arquivo atual que reaparecem iguais no convertido: {iguais} de {len(brutos_a) - 1}"]
    for i, nome in enumerate(cab):
        va = collections.Counter(forma_do_valor(ln[i]) for ln in lin_a if i < len(ln))
        vn = collections.Counter(forma_do_valor(ln[i]) for ln in lin_n if i < len(ln))
        antigos = {ln[i] for ln in lin_a if i < len(ln)}
        novos = {ln[i] for ln in lin_n if i < len(ln)}
        comuns = len(antigos & novos) / len(antigos) if antigos else 0
        texto.append(f"  {nome}: atual {fmt(va)} | convertido {fmt(vn)} | valores do atual que reaparecem: {comuns:.0%}")
    return texto


def fmt(contagem):
    total = sum(contagem.values()) or 1
    return ", ".join(f"'{k}' {n / total:.0%}" for k, n in contagem.most_common(3))
