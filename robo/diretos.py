# -*- coding: utf-8 -*-
"""Fontes de arquivo direto: IBGE (SIDRA e malhas) e SGB (RECMIN). O arquivo vai como a fonte publica, sem tratamento.

- SIDRA (população municipal, população de Goiás, PIB municipal): a consulta de `fontes.json` reproduz byte a byte o arquivo
  do repositório (conferido no GitHub em 24/10/2026, robo/explorar.py) e pede o último ano (`p/last`). A forma é a do arquivo
  atual: mesmo cabeçalho, mesmos níveis territoriais, mesma variável e unidade, todos os municípios de Goiás, ano que não volta.
  Quando o ano muda, o LEIA-ME de Dados brutos ganha o período e a consulta com o ano novo.
- RECMIN (WFS do SGB, caixa de Goiás): GeoJSON como o GeoServer devolve. O GeoServer põe a hora do pedido no arquivo
  (`timeStamp`): a comparação ignora esse campo. Download incompleto (menos feições que `numberMatched`) é barrado. O
  `.metadados.json` ao lado ganha a data, o tamanho, o sha256 e as contagens do download novo; o resto dele fica.
- Malhas do IBGE (municípios e limite de Goiás): só conferência. O nome do arquivo e o código dependem do ano da malha e o
  limite de Goiás recorta todas as camadas do P3M, então a troca é à mão. O robô avisa quando sai o ano seguinte e barra
  quando o IBGE republica o arquivo do mesmo ano.
"""
import collections
import datetime as dt
import json
import shutil
from pathlib import Path

import forma
from brutos import Registro
from comum import FalhaDownload, Resultado, baixar, digital_zip, existe, sha256


class Diretos:
    def __init__(self, raiz, hoje, cfg, gravar=True, espelho=None, pasta_tmp=None, aceitar=(), registro=None):
        self.raiz, self.hoje, self.cfg, self.gravar = Path(raiz), hoje, cfg, gravar
        self.espelho = espelho or {}
        self.aceitar = set(aceitar)
        self.tmp = Path(pasta_tmp)
        self.reg = registro or Registro(raiz, hoje, gravar)
        self.brutos = self.reg.brutos
        self.mudou = False

    def _baixar(self, url, nome, r):
        destino = self.tmp / nome
        try:
            baixar(self.espelho.get(url, url), destino, limite_mb=self.cfg.get("limite_download_mb", 200))
        except FalhaDownload as e:
            r.situacao, r.motivo = "falhou", f"{url}: {e}"
            return None
        r.baixado = str(destino)
        return destino

    def _existe(self, url):
        """No modo espelho (testes), só existe o que o espelho lista."""
        return (url in self.espelho) if self.espelho else existe(url)

    def rodar(self, grupos, so=None):
        resultados = []
        for f in self.cfg["fontes"]:
            if f["grupo"] not in grupos or (so and f["id"] not in so):
                continue
            resultados.append(getattr(self, f["tipo"])(f))
        return resultados

    def _gravar(self, novo, atual, f, r, logico=None):
        r.situacao = "atualizada"
        r.motivo = r.motivo or "conteúdo novo"
        if not self.gravar:
            return False
        shutil.copyfile(novo, atual)
        r.arquivos.append(atual.relative_to(self.raiz).as_posix())
        self.reg.arquivo(atual, logico or f.get("logico"), f.get("src"))
        self.mudou = True
        return True

    # ---------------------------------------------------------------------------------------------------------------- SIDRA
    def sidra(self, f):
        r = Resultado("IBGE", f["nome"])
        atual = self.brutos / f["arquivo"]
        novo = self._baixar(f["url"], Path(f["arquivo"]).name, r)
        if novo is None:
            return r
        dados, antes = novo.read_bytes(), atual.read_bytes()
        bloq, av, info = checar_sidra(dados, antes, fracao_minima=0.0 if f["id"] in self.aceitar else 0.99)
        r.avisos += av
        if bloq:
            r.situacao, r.motivo = "bloqueada", "; ".join(bloq)
            return r
        if dados == antes:
            r.situacao = "sem_mudanca"
            return r
        r.detalhes = info
        if self._gravar(novo, atual, f, r):
            self.reg.celula_da_fonte(f["src"], 3, periodo_sidra(json.loads(dados), f.get("periodo", "municipal")))
            self.reg.url_da_fonte(f["src"], f["url_registro"].format(ano=info["ano"]), "(consulta equivalente ao arquivo local)")
        return r

    # ---------------------------------------------------------------------------------------------------------------- RECMIN
    def geojson(self, f):
        r = Resultado("SGB", f["nome"])
        atual = self.brutos / f["arquivo"]
        novo = self._baixar(f["url"], Path(f["arquivo"]).name, r)
        if novo is None:
            return r
        dados, antes = novo.read_bytes(), atual.read_bytes()
        bloq, av = checar_geojson(dados, antes, fracao_minima=0.0 if f["id"] in self.aceitar else 0.9)
        r.avisos += av
        if bloq:
            r.situacao, r.motivo = "bloqueada", "; ".join(bloq)
            return r
        j, ja = json.loads(dados), json.loads(antes)
        if sem_hora(j) == sem_hora(ja):
            r.situacao = "sem_mudanca"
            return r
        if self._gravar(novo, atual, f, r):
            meta_path = atual.with_name(atual.name.replace(".geojson", ".metadados.json"))
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            meta.update(data_download_utc=dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), bytes=len(dados),
                        sha256=sha256(atual), feicoes=len(j["features"]), totalFeatures=j.get("totalFeatures"),
                        numberMatched=j.get("numberMatched"))
            # mesma escrita do arquivo de hoje: indentação 1, UTF-8 sem escapes, CRLF, sem quebra de linha no fim
            meta_path.write_bytes(json.dumps(meta, ensure_ascii=False, indent=1).replace("\n", "\r\n").encode("utf-8"))
            self.reg.arquivo(meta_path, f.get("logico_metadados"))
            r.arquivos.append(meta_path.relative_to(self.raiz).as_posix())
            self.reg.celula_da_fonte(f["src"], 3, periodo_recmin(j, meta["data_download_utc"]))
            r.detalhes = {"feicoes_antes": len(ja["features"]), "feicoes": len(j["features"])}
        return r

    # --------------------------------------------------------------------------------------------------------------- malhas
    def malha(self, f):
        r = Resultado("IBGE", f["nome"])
        atual = self.raiz / f["arquivo_raiz"]
        ano = f["ano"]
        seguinte = [a for a in range(ano + 1, ano + 4) if self._existe(f["url"].format(ano=a))]
        if seguinte:
            r.avisos.append(f"o IBGE já publicou a malha de {seguinte[-1]}; o repositório usa a de {ano}. A troca é à mão: {f['troca']}")
        novo = self._baixar(f["url"].format(ano=ano), atual.name, r)
        if novo is None:
            return r
        if novo.read_bytes() == atual.read_bytes() or digital_zip(novo) == digital_zip(atual):
            r.situacao = "sem_mudanca"
            return r
        r.situacao = "bloqueada"
        r.motivo = f"o IBGE republicou o arquivo de {ano} com outro conteúdo; conferir e trocar à mão ({f['troca']})"
        return r


# ---------------------------------------------------------------------------------------------------------------- checagens
def _linhas_sidra(dados):
    d = json.loads(dados)
    if not isinstance(d, list) or len(d) < 2 or not isinstance(d[0], dict):
        raise ValueError("a resposta não é a tabela do SIDRA (lista com cabeçalho e linhas)")
    return d[0], d[1:]


def _municipios_go(linhas):
    return {r["D1C"] for r in linhas if len(str(r.get("D1C", ""))) == 7 and str(r["D1C"]).startswith("52")}


def checar_sidra(novo, atual, fracao_minima=0.99):
    """(bloqueios, avisos, info) — a resposta nova tem a forma do arquivo atual?"""
    bloq, av = [], []
    try:
        cab_n, lin_n = _linhas_sidra(novo)
    except ValueError as e:
        return [f"não é JSON do SIDRA: {e}; começo: {novo[:200]!r}"], av, {}
    cab_a, lin_a = _linhas_sidra(atual)
    if cab_n != cab_a:
        return [f"o cabeçalho da tabela mudou: {cab_n}"], av, {}
    if any(set(r) != set(cab_a) for r in lin_n):
        bloq.append("linhas com campos diferentes do cabeçalho")
    for campo, nome in (("NN", "níveis territoriais"), ("D2C", "variável"), ("MN", "unidade de medida")):
        n, a = {r.get(campo) for r in lin_n}, {r.get(campo) for r in lin_a}
        if n != a:
            bloq.append(f"{nome} mudou: {sorted(a)} → {sorted(n)}")
    anos_n, anos_a = sorted({r.get("D3N") for r in lin_n}), sorted({r.get("D3N") for r in lin_a})
    if len(anos_n) != 1:
        bloq.append(f"mais de um ano na resposta: {anos_n}")
    elif anos_n[0] < anos_a[-1]:
        bloq.append(f"o ano voltou: {anos_a[-1]} → {anos_n[0]}")
    elif anos_n[0] != anos_a[-1]:
        av.append(f"ano {anos_a[-1]} → {anos_n[0]}")
    mun_n = sum(1 for r in lin_n if r.get("NN") == "Município")
    mun_a = sum(1 for r in lin_a if r.get("NN") == "Município")
    if mun_n < fracao_minima * mun_a:
        bloq.append(f"{mun_n} municípios contra {mun_a} no arquivo atual")
    go_n, go_a = _municipios_go(lin_n), _municipios_go(lin_a)
    if go_n != go_a:
        bloq.append(f"municípios de Goiás diferentes do arquivo atual: {len(go_a)} → {len(go_n)} (saíram {sorted(go_a - go_n)[:5]}, "
                    f"entraram {sorted(go_n - go_a)[:5]})")
    sem_valor = [r["D1C"] for r in lin_n if r.get("D1C") in go_n and not str(r.get("V", "")).replace(".", "", 1).isdigit()]
    if len(sem_valor) > 0.05 * max(len(go_n), 1):
        bloq.append(f"{len(sem_valor)} municípios de Goiás sem valor numérico (ex.: {sem_valor[:5]})")
    return bloq, av, {"ano": anos_n[0] if anos_n else None, "municipios": mun_n}


def periodo_sidra(d, tipo="municipal"):
    """O texto de 'Período coberto' do LEIA-ME e da aba 07 (o mesmo de periodo_json e periodo_json_uf da governança)."""
    linhas = d[1:]
    if tipo == "uf":
        return "; ".join(f"{r['D3N']} ({r['D1N']}: " + f"{int(r['V']):,}".replace(",", ".") + f" {r['MN'].lower()})" for r in linhas)
    anos = sorted({r["D3N"] for r in linhas})
    niveis = collections.Counter(r["NN"] for r in linhas)
    n_mun = niveis.pop("Município", 0)
    extra = "; " + ", ".join(f"mais {n} linha(s) de nível {k}" for k, n in niveis.items()) if niveis else ""
    return f"{', '.join(anos)} ({n_mun} municípios do Brasil no arquivo{extra})"


def sem_hora(j):
    return {k: v for k, v in j.items() if k != "timeStamp"}


def checar_geojson(novo, atual, fracao_minima=0.9, caixa=forma.RETANGULO_GOIAS, folga=1.0):
    """(bloqueios, avisos) — o GeoJSON novo tem a forma do atual? Todos os campos de hoje são exigidos (o pipeline lê vários)."""
    bloq, av = [], []
    if forma.parece_html(novo):
        return ["o servidor devolveu uma página HTML/XML em vez do GeoJSON: " + novo[:200].decode("utf-8", "replace")], av
    try:
        j = json.loads(novo)
    except ValueError as e:
        return [f"não é JSON: {e}; começo: {novo[:200]!r}"], av
    ja = json.loads(atual)
    if j.get("type") != "FeatureCollection" or not isinstance(j.get("features"), list):
        return ["não é uma FeatureCollection"], av
    n, na = len(j["features"]), len(ja["features"])
    if j.get("numberMatched") not in (None, n):
        bloq.append(f"download incompleto: {n} feições de {j['numberMatched']}")
    if n < fracao_minima * na:
        bloq.append(f"{n} feições contra {na} no arquivo atual (menos de {fracao_minima:.0%})")
    elif n != na:
        av.append(f"{n - na:+d} feições ({na} → {n})")
    if j.get("crs") != ja.get("crs"):
        bloq.append(f"sistema de coordenadas mudou: {ja.get('crs')} → {j.get('crs')}")
    tipos_n = {(ft.get("geometry") or {}).get("type") for ft in j["features"]}
    tipos_a = {(ft.get("geometry") or {}).get("type") for ft in ja["features"]}
    if not tipos_n <= tipos_a:
        bloq.append(f"geometria mudou: {sorted(map(str, tipos_a))} → {sorted(map(str, tipos_n))}")
    campos_a = set().union(*(ft.get("properties", {}) for ft in ja["features"])) if na else set()
    campos_n = set().union(*(ft.get("properties", {}) for ft in j["features"])) if n else set()
    if campos_a - campos_n:
        bloq.append(f"sumiram campos: {sorted(campos_a - campos_n)}")
    if campos_n - campos_a:
        av.append(f"campos novos: {sorted(campos_n - campos_a)}")
    x0, y0, x1, y1 = caixa
    fora = 0
    for ft in j["features"]:
        c = (ft.get("geometry") or {}).get("coordinates")
        if isinstance(c, list) and len(c) >= 2 and all(isinstance(v, (int, float)) for v in c[:2]):
            # o pedido usa EPSG:4326 com eixo lat,lon na caixa, mas o GeoJSON vem em lon,lat
            if not (x0 - folga <= c[0] <= x1 + folga and y0 - folga <= c[1] <= y1 + folga):
                fora += 1
    if fora > 0.01 * max(n, 1):
        bloq.append(f"{fora} feições fora da caixa de Goiás (coordenadas trocadas?)")
    return bloq, av


def periodo_recmin(j, data_download_utc):
    """O texto de 'Período coberto' (o mesmo de periodo_recmin da governança)."""
    dts = sorted(str(ft["properties"]["data_cadastro"])[:10] for ft in j["features"] if ft["properties"].get("data_cadastro"))
    ano_top, n_top = collections.Counter(x[:4] for x in dts).most_common(1)[0]
    return (f"cadastros no GeoSGB de {dts[0]} a {dts[-1]} ({100 * n_top / len(dts):.0f}% em {ano_top}, carga do banco); "
            f"baixado em {data_download_utc[:10]}")
