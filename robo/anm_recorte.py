# -*- coding: utf-8 -*-
"""Recorte de Goiás nos arquivos nacionais da ANM, como está em `Squad 1/Dados brutos`.

- CFEM: ficam as linhas com UF = GO.
- Cadastro Mineiro (regras de `ANM - Cadastro Mineiro/recorte_goias.json`):
  `municipio_ou_processo` — fica a linha em que algum município do campo "Município(s)" é de Goiás ou cujo processo tem
  poligonal em Goiás no SIGMINE; `processo` — só pelo processo (arquivo sem município); `sem_filtro` — arquivo inteiro.
  Município de Goiás é decidido como no pipeline (`go_municipio_id`): token com sufixo de outra UF ("BARRO ALTO - BA") é
  rejeitado sem casar pelo nome, porque 24 municípios de outros estados são homônimos de municípios goianos.

As linhas que ficam são gravadas byte a byte como a ANM publica (o texto é lido em latin-1, que não perde byte nenhum, e
devolvido igual). Só a decisão de manter ou não a linha lê o conteúdo.
"""
import re
import struct
import unicodedata
import zipfile

from forma import campos, registros_brutos


def norm(s):
    """Igual a `norm` de build_base1_mineral_ano.py."""
    s = re.sub(r"\s+", " ", str(s)).strip().upper()
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c))


def canon_proc(p):
    """Igual a `canon_proc` de build_base1_mineral_ano.py: '<número sem zeros à esquerda>/<ano>'."""
    p = str(p).strip()
    dig = lambda x: re.sub(r"\D", "", str(x))  # noqa: E731
    if "/" in p:
        esq, dir_ = p.split("/", 1)
        return (dig(esq).lstrip("0") or "0") + "/" + dig(dir_)[:4]
    return dig(p).lstrip("0") or "0"


def split_multi(v):
    v = re.sub(r"\s+", " ", str(v)).strip()
    return [x.strip() for x in re.split(r"[,;]", v) if x.strip()]


def ler_dbf(dados, codificacao):
    """Registros de um .dbf como dicionários (texto), sem biblioteca externa."""
    n, tam_cab, tam_reg = struct.unpack("<IHH", dados[4:12])
    campos_dbf = []
    for k in range(32, tam_cab - 1, 32):
        d = dados[k:k + 32]
        if d[:1] == b"\r":
            break
        campos_dbf.append((d[:11].split(b"\0")[0].decode("latin-1"), d[16]))
    for i in range(n):
        reg = dados[tam_cab + i * tam_reg: tam_cab + (i + 1) * tam_reg]
        if reg[:1] == b"*":
            continue
        pos, linha = 1, {}
        for nome, tam in campos_dbf:
            linha[nome] = reg[pos:pos + tam].decode(codificacao, "replace").strip()
            pos += tam
        yield linha


def municipios_goias(malha_zip):
    """Nomes normalizados dos 246 municípios de Goiás, da malha do IBGE (campo NM_MUN)."""
    with zipfile.ZipFile(malha_zip) as z:
        dbf = z.read(next(n for n in z.namelist() if n.lower().endswith(".dbf")))
    return {norm(r["NM_MUN"]) for r in ler_dbf(dbf, "utf-8")}


def processos_sigmine(sigmine_zip):
    """Processos (canônicos) que têm poligonal no SIGMINE de Goiás."""
    with zipfile.ZipFile(sigmine_zip) as z:
        dbf = z.read(next(n for n in z.namelist() if n.lower().endswith(".dbf")))
    return {canon_proc(r["PROCESSO"]) for r in ler_dbf(dbf, "utf-8") if r.get("PROCESSO")}


def municipio_de_goias(token, municipios):
    t = str(token).strip()
    m = re.search(r"-\s*([A-Za-z]{2})\s*$", t)
    if m:
        if m.group(1).upper() != "GO":
            return False
        t = t[:m.start()].strip()
    return norm(t) in municipios


def _texto(dados):
    texto = dados.decode("latin-1")
    bom = texto.startswith("ï»¿")  # BOM UTF-8 visto em latin-1
    return (texto[3:], texto[:3]) if bom else (texto, "")


def _celula(v):
    """Valor de uma célula lido em cp1252 (a codificação da ANM), a partir do texto em latin-1."""
    return v.encode("latin-1").decode("cp1252", "replace")


def recortar_uf(dados, separador=";", coluna="UF", valor="GO"):
    """(bytes do recorte, contagens) — cabeçalho e linhas com `coluna` == `valor`, byte a byte."""
    texto, bom = _texto(dados)
    regs = list(registros_brutos(texto))
    cab = campos(regs[0], separador)
    if coluna not in cab:
        raise ValueError(f"o arquivo não tem a coluna '{coluna}' (separador '{separador}'); cabeçalho: {[c[:40] for c in cab[:15]]}")
    i = cab.index(coluna)
    ficam = [r for r in regs[1:] if r.strip() and (lambda c: len(c) > i and c[i].strip() == valor)(campos(r, separador))]
    saida = bom + regs[0] + "".join(ficam)
    return saida.encode("latin-1"), {"linhas_nacional": sum(1 for r in regs[1:] if r.strip()), "linhas_goias": len(ficam)}


def recortar_cadastro(dados, regra, municipios, processos, separador=","):
    """(bytes do recorte, contagens) de um arquivo do Cadastro Mineiro."""
    texto, bom = _texto(dados)
    regs = list(registros_brutos(texto))
    cab = [_celula(c) for c in campos(regs[0], separador)]
    imun = next((k for k, c in enumerate(cab) if "unicipio" in c.lower()), None)
    iproc = next((k for k, c in enumerate(cab) if c.strip() == "Processo"), None)
    if regra == "municipio_ou_processo" and imun is None:
        raise ValueError("arquivo sem coluna de município para a regra municipio_ou_processo")
    if regra in ("municipio_ou_processo", "processo") and iproc is None:
        raise ValueError(f"arquivo sem coluna 'Processo' para a regra {regra}")
    ficam, com_mun, procs, total = [], 0, set(), 0
    for r in regs[1:]:
        if not r.strip():
            continue
        total += 1
        if regra == "sem_filtro":
            ficam.append(r)
            continue
        c = campos(r, separador)
        por_mun = regra == "municipio_ou_processo" and imun < len(c) and any(
            municipio_de_goias(t, municipios) for t in split_multi(_celula(c[imun])))
        cp = canon_proc(c[iproc]) if iproc < len(c) else ""
        por_proc = cp in processos
        if por_mun or por_proc:
            ficam.append(r)
            com_mun += por_mun
            if por_proc:
                procs.add(cp)
    saida = bom + regs[0] + "".join(ficam)
    return saida.encode("latin-1"), {"linhas_nacional": total, "linhas_goias": len(ficam), "linhas_com_municipio_de_goias": com_mun,
                                     "processos_do_sigmine_go": len(procs)}
