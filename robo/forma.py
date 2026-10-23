# -*- coding: utf-8 -*-
"""Checagem de forma: o arquivo novo tem o mesmo formato do que o site usa hoje?

O padrão é o próprio arquivo que está no repositório (é dele que os geradores e o site dependem), mais o que o site exige
por escrito: os campos que `scripts/mapa_camadas.json` lê de cada camada do P3M. Cada checagem devolve `(bloqueios, avisos)`:
um bloqueio impede o arquivo novo de entrar; um aviso entra no relatório e não impede.

Lê CSV e shapefile só com a biblioteca padrão, para rodar em qualquer lugar (inclusive no CI do site, sem GDAL).
"""
import csv
import io
import re
import struct
import zipfile
from pathlib import Path

# ---------------------------------------------------------------------------------------------------------------------- CSV

INTEIRO = re.compile(r"^-?\d+$")
DECIMAL = re.compile(r"^-?(\d{1,3}(\.\d{3})+|\d+)?([.,]\d+)?([eE][-+]?\d+)?$")
DATA = re.compile(r"^(\d{2}/\d{2}/\d{4}|\d{4}-\d{2}-\d{2})([ T]\d{2}:\d{2}(:\d{2})?)?$")
FRACAO_TIPO_ATUAL = 0.98   # um tipo vale para a coluna quando cobre 98% dos valores preenchidos do arquivo atual
FRACAO_TIPO_NOVO = 0.95    # e o arquivo novo precisa manter pelo menos 95%


def parece_html(dados):
    """Portal fora do ar costuma responder 200 com uma página HTML ou um XML de erro do GeoServer."""
    inicio = dados[:2048].lstrip().lower()
    return inicio.startswith((b"<!doctype", b"<html", b"<?xml", b"<serviceexceptionreport", b"<ows:exceptionreport")) or b"<html" in inicio


def registros_brutos(texto):
    """Divide o texto em registros sem perder nenhum caractere: um registro termina na quebra de linha que fecha um número par
    de aspas. Devolve os pedaços exatamente como estavam (com a quebra de linha), para o recorte gravar as linhas da fonte
    sem reescrever nada."""
    # Só "\n" fecha linha. str.splitlines também quebraria em \x0b, \x0c, \x1c-\x1e e \x85 — e o \x85 é o "…" da ANM em cp1252,
    # que aparece dentro de campos nos arquivos nacionais (lido em latin-1, vira o caractere de "próxima linha").
    atual, aspas = [], 0
    for linha in re.findall(r"[^\n]*\n|[^\n]+$", texto):
        atual.append(linha)
        aspas += linha.count('"')
        if aspas % 2 == 0:
            yield "".join(atual)
            atual, aspas = [], 0
    if atual:
        yield "".join(atual)


def campos(registro, separador):
    """Campos de um registro. Um \r solto no meio da linha (fora de aspas) vira espaço só para esta leitura: o registro gravado
    continua com os bytes da fonte."""
    texto = registro.rstrip("\r\n").replace("\r", " ")
    try:
        return next(csv.reader([texto], delimiter=separador))
    except csv.Error:  # linha mal formada: o recorte decide pelo que der para ler, e a checagem de forma conta a linha torta
        return texto.split(separador)


def ler_csv(dados, codificacao, separador):
    """(cabeçalho, linhas como listas, registros brutos) de um CSV em bytes. Levanta ValueError se não decodifica."""
    texto = dados.decode(codificacao)  # estrito: byte inválido para a codificação declarada é problema de forma
    if texto.startswith("﻿"):
        texto = texto[1:]
    brutos = list(registros_brutos(texto))
    if not brutos:
        return [], [], []
    cab = campos(brutos[0], separador)
    linhas = [campos(r, separador) for r in brutos[1:] if r.strip()]
    return cab, linhas, brutos


def tipo_de(v):
    if INTEIRO.match(v):
        return "inteiro"
    if DATA.match(v):
        return "data"
    if DECIMAL.match(v) and any(c.isdigit() for c in v):
        return "decimal"
    return "texto"


def cabe(v, tipo):
    t = tipo_de(v)
    return t == tipo or (tipo == "decimal" and t == "inteiro")


def perfil_colunas(cab, linhas, limite=50000):
    """Para cada coluna: o tipo que vale para ela e a fração de valores preenchidos."""
    amostra = linhas[:limite]
    perfil = {}
    for i, nome in enumerate(cab):
        valores = [ln[i].strip() for ln in amostra if i < len(ln)]
        cheios = [v for v in valores if v]
        tipo = "texto"
        if cheios:
            for t in ("inteiro", "decimal", "data"):
                if sum(cabe(v, t) for v in cheios) >= FRACAO_TIPO_ATUAL * len(cheios):
                    tipo = t
                    break
        perfil[nome] = {"tipo": tipo, "preenchida": len(cheios) / len(valores) if valores else 0.0}
    return perfil


def checar_csv(novo, atual, codificacao, separador, fracao_minima=0.9, rotulo="arquivo"):
    """Compara o CSV novo (bytes) com o atual (bytes). Os dois já no mesmo recorte (Goiás com Goiás)."""
    bloqueios, avisos = [], []
    if not novo.strip():
        return ["arquivo vazio"], avisos
    if parece_html(novo):
        return ["o servidor devolveu uma página HTML/XML em vez do CSV: " + novo[:160].decode("utf-8", "replace").strip()], avisos
    try:
        cab_n, lin_n, _ = ler_csv(novo, codificacao, separador)
    except UnicodeDecodeError as e:
        return [f"não decodifica como {codificacao}: {e}"], avisos
    cab_a, lin_a, _ = ler_csv(atual, codificacao, separador)
    if len(cab_n) <= 1 and len(cab_a) > 1:
        return [f"cabeçalho com {len(cab_n)} coluna: o separador deixou de ser '{separador}'?"], avisos
    if cab_n != cab_a:
        saiu = [c for c in cab_a if c not in cab_n]
        entrou = [c for c in cab_n if c not in cab_a]
        msg = "colunas diferentes das do arquivo que o site usa"
        if saiu:
            msg += f"; saíram: {saiu}"
        if entrou:
            msg += f"; entraram: {entrou}"
        if not saiu and not entrou:
            msg += "; mesma lista em outra ordem"
        bloqueios.append(msg)
        return bloqueios, avisos
    tortas_n = sum(len(ln) != len(cab_n) for ln in lin_n)
    tortas_a = sum(len(ln) != len(cab_a) for ln in lin_a)
    if tortas_n > max(10, 2 * tortas_a):
        bloqueios.append(f"{tortas_n} linhas com número de campos diferente do cabeçalho (o atual tem {tortas_a})")
    if not lin_n:
        bloqueios.append("nenhuma linha de dados")
    elif len(lin_n) < fracao_minima * len(lin_a):
        bloqueios.append(f"{len(lin_n)} linhas contra {len(lin_a)} no arquivo atual (menos de {fracao_minima:.0%})")
    elif len(lin_n) != len(lin_a):
        avisos.append(f"{len(lin_n) - len(lin_a):+d} linhas ({len(lin_a)} → {len(lin_n)})")
    perfil = perfil_colunas(cab_a, lin_a)
    for i, nome in enumerate(cab_n):
        p = perfil[nome]
        valores = [ln[i].strip() for ln in lin_n[:50000] if i < len(ln)]
        cheios = [v for v in valores if v]
        if p["preenchida"] >= 0.9 and valores and len(cheios) < 0.5 * len(valores):
            bloqueios.append(f"coluna '{nome}' esvaziou: {len(cheios)}/{len(valores)} preenchidas (no atual, {p['preenchida']:.0%})")
            continue
        if p["tipo"] != "texto" and cheios:
            fora = [v for v in cheios if not cabe(v, p["tipo"])]
            if len(fora) > (1 - FRACAO_TIPO_NOVO) * len(cheios):
                bloqueios.append(f"coluna '{nome}' deixou de ser {p['tipo']}: {len(fora)} valores fora, ex.: {fora[:3]}")
    return bloqueios, avisos


# ---------------------------------------------------------------------------------------------------------------- shapefile

FAMILIA = {1: "ponto", 11: "ponto", 21: "ponto", 8: "multiponto", 18: "multiponto", 28: "multiponto",
           3: "linha", 13: "linha", 23: "linha", 5: "poligono", 15: "poligono", 25: "poligono"}
BRASIL = (-75.0, -35.0, -28.0, 6.0)          # lon0, lat0, lon1, lat1, com folga
RETANGULO_GOIAS = (-53.5, -19.8, -45.6, -12.1)


def ler_shapefile_zip(caminho_ou_bytes):
    """Lê do zip só o que define a forma: tipo de geometria, caixa, número de registros, campos, .prj e codificação."""
    origem = io.BytesIO(caminho_ou_bytes) if isinstance(caminho_ou_bytes, (bytes, bytearray)) else caminho_ou_bytes
    with zipfile.ZipFile(origem) as z:
        nomes = z.namelist()
        bases = sorted({n[:-4] for n in nomes if n.lower().endswith(".shp")})
        partes = []
        for b in bases:
            achar = lambda ext: next((n for n in nomes if n.lower() == (b + ext).lower()), None)  # noqa: E731
            faltam = [e for e in (".shx", ".dbf", ".prj") if not achar(e)]
            shp = z.read(achar(".shp"))
            if len(shp) < 100 or struct.unpack(">i", shp[:4])[0] != 9994:
                raise ValueError(f"{b}.shp não é um shapefile")
            tipo = struct.unpack("<i", shp[32:36])[0]
            caixa = struct.unpack("<4d", shp[36:68])
            n, campos_dbf = 0, []
            if achar(".dbf"):
                dbf = z.read(achar(".dbf"))
                n, tam_cab = struct.unpack("<IH", dbf[4:10])
                for k in range(32, tam_cab - 1, 32):
                    d = dbf[k:k + 32]
                    if d[:1] == b"\r":
                        break
                    campos_dbf.append((d[:11].split(b"\0")[0].decode("latin-1"), chr(d[11]), d[16], d[17]))
            prj = z.read(achar(".prj")).decode("latin-1") if achar(".prj") else ""
            cod = ""
            for e in (".cpg", ".cst"):
                if achar(e):
                    cod = z.read(achar(e)).decode("latin-1").strip()
            partes.append({"base": b, "tipo": tipo, "caixa": caixa, "n": n, "campos": campos_dbf, "prj": prj, "codificacao": cod,
                           "faltam": faltam})
    return partes


def crs_de(prj):
    """Identifica o sistema de coordenadas pelo .prj: 'SIRGAS 2000', 'WGS 84' ou o nome que vier."""
    t = re.sub(r"[\s_]+", " ", prj).upper()
    if "SIRGAS" in t and "2000" in t:
        return "SIRGAS 2000" + (" (projetado)" if t.startswith("PROJCS") else "")
    if "WGS" in t and "84" in t:
        return "WGS 84" + (" (projetado)" if t.startswith("PROJCS") else "")
    m = re.search(r'^(GEOGCS|PROJCS)\["([^"]+)"', t)
    return m.group(2) if m else (t[:40] or "sem .prj")


def intersecta(a, b):
    return not (a[2] < b[0] or a[0] > b[2] or a[3] < b[1] or a[1] > b[3])


def checar_shapefile(novo, atual, exigidos=(), fracao_minima=0.5, perto_de=RETANGULO_GOIAS, todos_exigidos=False):
    """Compara um zip de shapefile novo com o atual.

    `exigidos`: campos que o site lê (faltar um bloqueia). Com `todos_exigidos`, todo campo do arquivo atual é exigido
    (para bases que o pipeline lê inteiras, como o SIGMINE)."""
    bloqueios, avisos = [], []
    try:
        pn = ler_shapefile_zip(novo)
    except zipfile.BadZipFile:
        dados = novo if isinstance(novo, (bytes, bytearray)) else Path(novo).read_bytes()[:400]
        return ["não é um zip; o servidor devolveu: " + bytes(dados[:160]).decode("utf-8", "replace").strip()], avisos
    except (ValueError, struct.error, KeyError) as e:
        return [f"zip sem shapefile legível: {e}"], avisos
    pa = ler_shapefile_zip(atual)
    if not pn:
        return ["o zip não tem nenhum .shp"], avisos
    if len(pn) != len(pa):
        avisos.append(f"{len(pn)} shapefiles no zip (o atual tem {len(pa)})")
    for p in pn:
        if p["faltam"]:
            bloqueios.append(f"{p['base']}: faltam {', '.join(p['faltam'])}")
    fam_n = {FAMILIA.get(p["tipo"], str(p["tipo"])) for p in pn if p["n"]}
    fam_a = {FAMILIA.get(p["tipo"], str(p["tipo"])) for p in pa if p["n"]}
    if fam_a and fam_n and fam_n != fam_a:
        bloqueios.append(f"geometria mudou: {sorted(fam_a)} → {sorted(fam_n)}")
    crs_n, crs_a = {crs_de(p["prj"]) for p in pn}, {crs_de(p["prj"]) for p in pa}
    if crs_n != crs_a:
        bloqueios.append(f"sistema de coordenadas mudou: {sorted(crs_a)} → {sorted(crs_n)}")
    n_n, n_a = sum(p["n"] for p in pn), sum(p["n"] for p in pa)
    if n_n == 0:
        bloqueios.append("nenhum registro")
    elif n_n < fracao_minima * n_a:
        bloqueios.append(f"{n_n} registros contra {n_a} no arquivo atual (menos de {fracao_minima:.0%})")
    elif n_n != n_a:
        avisos.append(f"{n_n - n_a:+d} registros ({n_a} → {n_n})")
    if n_n and "projetado" not in " ".join(crs_n):
        for p in pn:
            if p["n"] and not intersecta(p["caixa"], BRASIL):
                bloqueios.append(f"caixa fora do Brasil {tuple(round(x, 2) for x in p['caixa'])}: coordenadas trocadas?")
            elif p["n"] and perto_de and not intersecta(p["caixa"], perto_de):
                bloqueios.append(f"nenhuma feição perto de Goiás; caixa {tuple(round(x, 2) for x in p['caixa'])}")
    cn = {c[0]: c for p in pn for c in p["campos"]}
    ca = {c[0]: c for p in pa for c in p["campos"]}
    exig = set(ca) if todos_exigidos else set(exigidos)
    for nome in sorted(set(ca) - set(cn)):
        (bloqueios if nome in exig else avisos).append(f"campo '{nome}' sumiu" + (" (o site usa)" if nome in exig else ""))
    faltam_site = sorted(set(exigidos) - set(cn) - set(ca))
    if faltam_site:
        bloqueios.append(f"campos que o site usa e não existem: {faltam_site}")
    novos = sorted(set(cn) - set(ca))
    if novos:
        avisos.append(f"campos novos: {novos}")
    for nome in sorted(set(cn) & set(ca)):
        tn, ta = cn[nome][1], ca[nome][1]
        if tn != ta and {tn, ta} != {"N", "F"}:
            (bloqueios if nome in exig else avisos).append(f"campo '{nome}' mudou de tipo: {ta} → {tn}")
    cod = {p["codificacao"].upper().replace("-", "") for p in pn}
    if cod - {"UTF8"}:
        avisos.append(f"codificação declarada: {sorted(cod)}")
    return bloqueios, avisos
