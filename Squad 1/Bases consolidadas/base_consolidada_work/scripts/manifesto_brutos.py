# -*- coding: utf-8 -*-
"""Manifesto dos dados brutos: fonte, arquivo, data de acesso, tamanho e sha256 de cada arquivo que o pipeline pode ler.

    python manifesto_brutos.py            # confere os brutos de hoje com documentacao/manifesto_brutos.json (0 = ok, 3 = trava)
    python manifesto_brutos.py --gravar   # grava o manifesto (rodar_pipeline.py faz isso sozinho quando termina sem trava)

O manifesto registra os brutos que geraram a planilha atual. Na conferência, cada arquivo é classificado em novo, removido,
alterado (sha256 diferente) ou igual. TRAVA (ERR_040): arquivo alterado com a MESMA data de acesso registrada — os bytes mudaram
sem um download novo registrado (quebra de linha trocada pelo git, edição à mão, cópia errada). Quem baixa uma base nova registra
a data em "Dados brutos/datas_de_acesso.json" (o robô faz isso sozinho) e o sha256 no LEIA-ME da pasta. Na cópia de trabalho
(dados/), a data é a de modificação do arquivo e a trava não se aplica.
"""
import hashlib
import json
import os
import sys

sys.dont_write_bytecode = True
from caminhos import ARRANJO, ARQUIVO_DATAS, BASE, BRUTOS, DADOS_TRABALHO, arquivo, logico  # noqa: E402

MANIFESTO = os.path.join(BASE, "documentacao", "manifesto_brutos.json")
FORA = {"LEIA-ME.md", ARQUIVO_DATAS, ".gitattributes"}  # documentação da pasta, não dado


def _ler_json(caminho):
    with open(caminho, encoding="utf-8") as f:
        return json.load(f)


def sha256(caminho):
    h = hashlib.sha256()
    with open(caminho, "rb") as f:
        for bloco in iter(lambda: f.read(1 << 20), b""):
            h.update(bloco)
    return h.hexdigest()


def atual():
    """{caminho lógico: {fonte, arquivo, data_acesso, bytes, sha256}} dos brutos do arranjo em uso."""
    from datetime import datetime, timezone
    raiz = DADOS_TRABALHO if ARRANJO == "trabalho" else BRUTOS
    datas = {}
    if ARRANJO == "github" and os.path.exists(os.path.join(BRUTOS, ARQUIVO_DATAS)):
        datas = _ler_json(os.path.join(BRUTOS, ARQUIVO_DATAS))
    out = {}
    for d, _, ns in os.walk(raiz):
        for n in sorted(ns):
            if n in FORA:
                continue
            fis = os.path.join(d, n)
            lg = logico(fis)
            rel = os.path.relpath(fis, raiz).replace("\\", "/")
            data = (datas.get(lg, "") if ARRANJO == "github"
                    else datetime.fromtimestamp(os.path.getmtime(fis), tz=timezone.utc).strftime("%Y-%m-%d"))
            out[lg] = {"fonte": rel.split("/")[0], "arquivo": rel, "data_acesso": data, "bytes": os.path.getsize(fis), "sha256": sha256(fis)}
    return dict(sorted(out.items()))


def gravar(m=None):
    m = m or atual()
    with open(MANIFESTO, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"arranjo": ARRANJO, "arquivos": m}, f, ensure_ascii=False, indent=1)
    return MANIFESTO


def conferir(m=None):
    """(travas, linhas) — linhas = relatório Markdown do que mudou nos brutos desde o manifesto."""
    m = m or atual()
    if not os.path.exists(MANIFESTO):
        return [], ["Sem manifesto anterior (documentacao/manifesto_brutos.json): nada a comparar; ele será gravado no fim do pipeline."]
    ant = _ler_json(MANIFESTO)
    a = ant["arquivos"]
    mesmo_arranjo = ant.get("arranjo") == ARRANJO
    novos = sorted(set(m) - set(a))
    removidos = sorted(set(a) - set(m))
    alterados = sorted(k for k in set(m) & set(a) if m[k]["sha256"] != a[k]["sha256"])
    travas = []
    linhas = [f"Brutos ({ARRANJO}): {len(m)} arquivos; desde o manifesto: {len(novos)} novos, {len(removidos)} removidos, "
              f"{len(alterados)} alterados, {len(m) - len(novos) - len(alterados)} iguais."]
    if novos or removidos or alterados:
        linhas += ["", "| Arquivo | Fonte | Mudança | Data de acesso (antes → agora) | Tamanho (antes → agora) |", "|---|---|---|---|---|"]
    for k in novos:
        linhas.append(f"| {k} | {m[k]['fonte']} | novo | {m[k]['data_acesso']} | {m[k]['bytes']:,} |")
    for k in removidos:
        linhas.append(f"| {k} | {a[k]['fonte']} | removido | {a[k]['data_acesso']} | {a[k]['bytes']:,} |")
    for k in alterados:
        da, dn = a[k]["data_acesso"], m[k]["data_acesso"]
        linhas.append(f"| {k} | {m[k]['fonte']} | alterado | {da} → {dn} | {a[k]['bytes']:,} → {m[k]['bytes']:,} |")
        if ARRANJO == "github" and mesmo_arranjo and da and da == dn:
            travas.append(f"{k}: os bytes mudaram (sha256 {a[k]['sha256'][:12]}… → {m[k]['sha256'][:12]}…) com a mesma data de acesso "
                          f"({dn}) [ERR_040]. Se é um download novo, registre a data em Dados brutos/{ARQUIVO_DATAS} e o sha256 no "
                          "LEIA-ME da pasta; se não é, o arquivo foi alterado sem querer (git checkout -- <arquivo>).")
    for k in novos:
        if ARRANJO == "github" and not m[k]["data_acesso"] and k.startswith("dados/") and os.path.exists(arquivo(k)):
            linhas.append(f"aviso: {k} não tem data em Dados brutos/{ARQUIVO_DATAS}")
    return travas, linhas


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    if "--gravar" in sys.argv:
        print(f"SALVO: {gravar()}")
        sys.exit(0)
    t, ln = conferir()
    print("\n".join(ln + [""] + [f"TRAVA: {x}" for x in t]))
    sys.exit(3 if t else 0)
