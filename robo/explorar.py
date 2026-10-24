# -*- coding: utf-8 -*-
"""Reconhecimento das fontes que o robô ainda não atualiza: só lê, não grava nada no repositório.

    python robo/explorar.py [--saida relatorio.md]

Roda no GitHub (workflow robo-explorar.yml), porque daqui os portais do governo não respondem. Para cada fonte, imprime o que
precisa ser registrado antes de automatizar: a URL do arquivo, a data e o tamanho que o servidor informa, se o download é
aceito e, nas APIs, o último período publicado. Nenhum dado de linha vai para o relatório, só nomes de arquivo, contagens e
cabeçalhos.
"""
import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from comum import AGENTE  # noqa: E402

NAVEGADOR = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
saida = []


def p(*partes):
    texto = " ".join(str(x) for x in partes)
    print(texto, flush=True)
    saida.append(texto)


def pedir(url, metodo="GET", limite=2_000_000, agente=AGENTE, intervalo=None, timeout=60):
    """(status, cabeçalhos, bytes até `limite`) — nunca levanta exceção."""
    cab = {"User-Agent": agente}
    if intervalo:
        cab["Range"] = f"bytes=0-{intervalo - 1}"
    try:
        req = urllib.request.Request(url, headers=cab, method=metodo)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, dict(r.headers), (r.read(limite) if metodo == "GET" else b"")
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers or {}), e.read(2000) if hasattr(e, "read") else b""
    except Exception as e:  # noqa: BLE001 — o relatório registra qualquer falha
        return None, {}, f"{type(e).__name__}: {e}".encode()


def resumo_http(status, cab):
    return (f"HTTP {status} · tipo {cab.get('Content-Type', '?')} · tamanho {cab.get('Content-Length', '?')} · "
            f"modificado {cab.get('Last-Modified', '?')}")


def links(html, base):
    """Links de uma página de índice que ficam abaixo de `base` (subpastas e arquivos)."""
    urls = (urllib.parse.urljoin(base, h) for h in re.findall(r'href=["\']([^"\'?#]+)', html, re.I))  # o IIS da ANM escreve HREF
    return [u for u in urls if u.startswith(base) and u != base]


# ------------------------------------------------------------------------------------------------------------------ ANM
def anm(raiz="https://dadosabertos.anm.gov.br/"):
    p("\n## ANM — índice de dadosabertos.anm.gov.br\n")
    st, cab, corpo = pedir(raiz)
    p(resumo_http(st, cab))
    if st != 200:
        p("corpo:", corpo[:300])
        return
    html = corpo.decode("utf-8", "replace")
    p("página inicial (texto):", re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()[:600])
    p("hrefs da página inicial:", re.findall(r'href=["\']([^"\']+)', html, re.I)[:40])
    pastas = sorted({u for u in links(html, raiz) if u.endswith("/")})
    # as pastas que o robô já usa: se a raiz não lista, o índice de cada uma pode listar
    pastas = sorted(set(pastas) | {raiz + d for d in ("AMB/", "CFEM/", "SCM/", "SIGMINE/", "DIPEM/", "SOPLE/", "SIGBM/")})
    p("pastas:", ", ".join(u[len(raiz):] for u in pastas))
    procurados = re.compile(r"invest|dipem|pesquisa|rodada|disponib|leil|sople|barrag|sigbm|agua", re.I)
    for pasta in pastas:
        st, _, corpo = pedir(pasta)
        if st != 200:
            p(f"- {pasta[len(raiz):]}: HTTP {st}")
            continue
        arquivos = sorted({u[len(pasta):] for u in links(corpo.decode("utf-8", "replace"), pasta) if u != pasta})
        # nas pastas novas (DIPEM, SOPLE, SIGBM) tudo interessa; nas que o robô já usa, só o que parece fonte nova
        marcados = arquivos if pasta.rstrip("/").rsplit("/", 1)[-1] in ("DIPEM", "SOPLE", "SIGBM") else \
            [a for a in arquivos if procurados.search(a)]
        p(f"- {pasta[len(raiz):]} ({len(arquivos)} itens): {', '.join(arquivos[:40])}{' …' if len(arquivos) > 40 else ''}")
        for a in marcados[:30]:
            if a.endswith("/"):
                st, _, corpo = pedir(pasta + a)
                sub = sorted({u[len(pasta + a):] for u in links(corpo.decode("utf-8", "replace"), pasta + a)})
                p(f"    pasta {pasta + a}: {', '.join(sub[:30])}")
                continue
            st, cab, corpo = pedir(pasta + a, intervalo=2048, limite=2048)
            primeira = corpo.split(b"\n", 1)[0][:300].decode("cp1252", "replace") if st in (200, 206) else ""
            p(f"    {pasta + a} · {resumo_http(st, cab)}" + (f" · 1ª linha: {primeira}" if a.lower().endswith((".csv", ".txt")) else ""))


# ------------------------------------------------------------------------------------------------------------------ CKAN
def ckan(portal, pacote, testar_download=False):
    url = f"{portal}/api/3/action/package_show?id={pacote}"
    p(f"\n## CKAN {portal} — {pacote}\n")
    st, cab, corpo = pedir(url)
    p(url, "·", resumo_http(st, cab))
    if st != 200:
        p("corpo:", corpo[:300])
        return []
    try:
        recursos = json.loads(corpo)["result"]["resources"]
    except (ValueError, KeyError) as e:
        p("resposta inesperada:", e, corpo[:200])
        return []
    for r in recursos:
        p(f"- {r.get('name')} · {r.get('format')} · modificado {r.get('last_modified') or r.get('metadata_modified')} · "
          f"tamanho {r.get('size')} · {r.get('url')}")
    if testar_download and recursos:
        alvo = sorted((r for r in recursos if (r.get("format") or "").upper() == "CSV"), key=lambda r: r.get("name") or "")[-1:]
        for r in alvo:
            for nome, agente in (("robô", AGENTE), ("navegador", NAVEGADOR)):
                st, cab, corpo = pedir(r["url"], agente=agente, intervalo=4096, limite=4096)
                p(f"  download de {r.get('name')} como {nome}: {resumo_http(st, cab)}")
                if st in (200, 206):
                    p("  primeira linha:", corpo.split(b"\n", 1)[0][:300].decode("utf-8", "replace"))
                else:
                    p("  corpo:", corpo[:200])
    return recursos


# ------------------------------------------------------------------------------------------------------------------ IBGE
def bloqueio_ccee():
    p("\n## CCEE — o bloqueio é do robô ou do lugar?\n")
    for url in ("https://dadosabertos.ccee.org.br/dataset/parcela_carga_consumo",
                "https://dadosabertos.ccee.org.br/api/3/action/package_show?id=parcela_carga_consumo"):
        for nome, agente in (("robô", AGENTE), ("navegador", NAVEGADOR)):
            st, cab, corpo = pedir(url, agente=agente)
            texto = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", corpo.decode("utf-8", "replace"))).strip()
            p(f"- {url} como {nome}: HTTP {st} · {texto[:300] if st != 200 else 'ok'}")


def dados_gov():
    p("\n## dados.gov.br — conjuntos da ANM\n")
    for url in ("https://dados.gov.br/api/publico/conjuntos-dados?isPrivado=false&pagina=1&nomeConjuntoDados=investimento",
                "https://dados.gov.br/dados/api/publico/conjuntos-dados?isPrivado=false&pagina=1&nomeConjuntoDados=investimento",
                "https://dados.gov.br/api/3/action/package_search?q=investimento%20pesquisa%20mineral"):
        st, cab, corpo = pedir(url)
        p(f"- {url}: {resumo_http(st, cab)} · {corpo[:300]!r}")


def sidra():
    p("\n## IBGE — SIDRA (último período)\n")
    for nome, url in (("população 6579/9324", "https://apisidra.ibge.gov.br/values/t/6579/n6/all/v/9324/p/last"),
                      ("PIB 5938/37", "https://apisidra.ibge.gov.br/values/t/5938/n6/all/v/37/p/last"),
                      ("população UF 6579/9324", "https://apisidra.ibge.gov.br/values/t/6579/n3/52/v/9324/p/last")):
        st, cab, corpo = pedir(url, limite=10_000_000)
        try:
            d = json.loads(corpo)
            anos = sorted({r.get("D3N") for r in d[1:]})
            p(f"- {nome}: HTTP {st} · {len(d) - 1} linhas · anos {anos} · níveis {sorted({r.get('NN') for r in d[1:]})}")
        except ValueError:
            p(f"- {nome}: HTTP {st} · resposta não é JSON: {corpo[:200]}")


def sidra_equivalente():
    """Qual consulta reproduz byte a byte os arquivos do repositório? Eles terminam com a linha da UF de Goiás, como na consulta
    de dois níveis (municípios e depois a UF)."""
    import hashlib
    p("\n## IBGE — SIDRA: consulta que reproduz o arquivo do repositório\n")
    pasta = Path(__file__).resolve().parents[1] / "Squad 1" / "Dados brutos" / "IBGE - População e PIB (SIDRA)"
    casos = (("populacao_municipal_goias_ultimo_ano.json", "https://apisidra.ibge.gov.br/values/t/6579/n6/all/n3/52/v/9324/p/{ano}"),
             ("pib_municipal_goias_ultimo_ano.json", "https://apisidra.ibge.gov.br/values/t/5938/n6/all/n3/52/v/37/p/{ano}"),
             ("populacao_goias_ultimo_ano.json", "https://apisidra.ibge.gov.br/values/t/6579/n3/52/v/9324/p/{ano}"))
    for nome, modelo in casos:
        arq = pasta / nome
        if not arq.exists():
            p(f"- {nome}: não está no checkout")
            continue
        atual = arq.read_bytes()
        ano = json.loads(atual)[1]["D3N"]
        for url in (modelo.format(ano=ano), modelo.format(ano="last")):
            st, _, corpo = pedir(url, limite=10_000_000)
            igual = hashlib.sha256(corpo).hexdigest() == hashlib.sha256(atual).hexdigest()
            try:
                anos = sorted({r.get("D3N") for r in json.loads(corpo)[1:]})
            except ValueError:
                anos = "?"
            p(f"- {nome} ← {url}: HTTP {st} · {len(corpo)} bytes (repositório: {len(atual)}) · anos {anos} · "
              f"{'IGUAL byte a byte' if igual else 'diferente'}")


def malhas():
    p("\n## IBGE — malhas no geoftp\n")
    base = "https://geoftp.ibge.gov.br/organizacao_do_territorio/malhas_territoriais/malhas_municipais"
    for ano in (2024, 2025, 2026, 2027):
        for arq in (f"GO_Municipios_{ano}.zip", f"GO_UF_{ano}.zip"):
            url = f"{base}/municipio_{ano}/UFs/GO/{arq}"
            st, cab, _ = pedir(url, "HEAD")
            p(f"- {url} · {resumo_http(st, cab)}")


# ------------------------------------------------------------------------------------------------------------------ SGB
def recmin():
    p("\n## SGB — RECMIN (WFS, só a contagem)\n")
    url = ("https://geoservicos.sgb.gov.br/geoserver/ows?service=WFS&version=2.0.0&request=GetFeature"
           "&typeNames=geosgb:ocorrencias_recursos_minerais&resultType=hits&bbox=-19.7,-53.4,-12.2,-45.8,urn:ogc:def:crs:EPSG::4326")
    st, cab, corpo = pedir(url)
    m = re.search(rb'numberMatched="(\d+)"', corpo)
    p(f"- HTTP {st} · numberMatched {m.group(1).decode() if m else '?'}")


def sigbm():
    p("\n## ANM — SIGBM Público\n")
    for url in ("https://app.anm.gov.br/SIGBM/Publico", "https://app.anm.gov.br/SIGBM/Publico/ClassificacaoNacionalDaBarragem"):
        st, cab, corpo = pedir(url)
        exporta = sorted(set(re.findall(rb'href="([^"]*(?:xls|xlsx|csv|Exportar|Download)[^"]*)"', corpo, re.I)))[:10]
        p(f"- {url} · {resumo_http(st, cab)} · links de exportação: {[e.decode('utf-8', 'replace') for e in exporta]}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--saida", help="grava o relatório em Markdown aqui")
    args = ap.parse_args()
    p("# Reconhecimento das fontes ainda fora do robô")
    anm()
    sigbm()
    ckan("https://dadosabertos.ccee.org.br", "parcela_carga_consumo", testar_download=True)
    bloqueio_ccee()
    dados_gov()
    ckan("https://dadosabertos.aneel.gov.br", "siga-sistema-de-informacoes-de-geracao-da-aneel")
    ckan("https://dados.ons.org.br", "linha-transmissao")
    ckan("https://dados.ons.org.br", "subestacao")
    sidra()
    sidra_equivalente()
    malhas()
    recmin()
    if args.saida:
        Path(args.saida).write_text("\n".join(saida) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
