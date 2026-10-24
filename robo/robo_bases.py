# -*- coding: utf-8 -*-
"""Robô de atualização das bases do P3M e da ANM.

    python robo/robo_bases.py                          # P3M (camadas do mapa), ANM, IBGE e SGB: baixa, confere, trata e grava
    python robo/robo_bases.py --fontes p3m --p3m-escopo todas
    python robo/robo_bases.py --so SIGMINE,CFEM        # só estas fontes (ids de fontes.json) ou camadas do P3M (código vw_…)
    python robo/robo_bases.py --sem-gravar             # baixa e confere, mas não grava nada
    python robo/robo_bases.py --guardar-barrados DIR   # copia para DIR o que a fonte publicou e foi barrado (para inspeção)
    python robo/robo_bases.py --aceitar-queda Alvara_de_Pesquisa.csv   # queda grande de linhas conferida e aceita por alguém
    python robo/robo_bases.py --checar                 # sem rede: os arquivos do repositório estão no formato que o site usa?
    python robo/robo_bases.py --conferir-planilha ANTES.xlsx DEPOIS.xlsx   # a base consolidada refeita ganhou alerta novo?
    python robo/robo_bases.py --comparar-xlsx A.xlsx B.xlsx                # mesmos valores? (o .xlsx muda de bytes a cada gravação)

O robô só mexe nos dados brutos (Squad 1/P3M, Squad 1/Dados brutos e as rodadas em Squad 1/dados). O que sai deles — base consolidada, atlas, mapa,
panorama… — é refeito depois pelo workflow `.github/workflows/robo-bases.yml`, que também roda os testes antes de publicar.
Detalhes em robo/LEIA-ME.md.

Saída: 0 = tudo certo (com ou sem mudança); 1 = alguma fonte foi bloqueada pela checagem de forma ou não baixou (o que
passou foi gravado); 3 = `--checar` ou `--conferir-planilha` acharam problema.
"""
import argparse
import datetime as dt
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.dont_write_bytecode = True

from comum import RAIZ, Resultado, gravar_json, pasta_temporaria, relatorio_md  # noqa: E402

CONFIG = Path(__file__).resolve().parent / "fontes.json"


def carregar_config():
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def rodar(args):
    cfg = carregar_config()
    raiz = Path(args.raiz).resolve()
    hoje = args.hoje or dt.date.today().isoformat()
    espelho = json.loads(Path(args.espelho).read_text(encoding="utf-8")) if args.espelho else {}
    so = set(filter(None, (args.so or "").split(",")))
    aceitar = {x.strip() for x in (args.aceitar_queda or "").split(",") if x.strip()}
    fontes = set(args.fontes.split(","))
    tmp = pasta_temporaria()
    resultados, gravados = [], []
    ids_anm = {f["id"] for f in cfg["anm"]["fontes"]}
    ids_diretos = {f["id"] for f in cfg["diretos"]["fontes"]}
    try:
        # ANM, IBGE e SGB gravam em Dados brutos: um registro só de datas_de_acesso.json e do LEIA-ME para os três
        grupos = fontes & {"ibge", "sgb"}
        registro = None
        if "anm" in fontes or grupos:
            from brutos import Registro
            registro = Registro(raiz, hoje, gravar=not args.sem_gravar)
        if "anm" in fontes:
            from anm import ANM
            anm = ANM(raiz, hoje, cfg["anm"], gravar=not args.sem_gravar, espelho=espelho, pasta_tmp=tmp, aceitar=aceitar,
                      registro=registro)
            so_anm = so & ids_anm
            if not so or so_anm:
                resultados += anm.rodar(so_anm or None)
            gravados += anm.salvar()
        so_diretos = so & ids_diretos
        if grupos and (not so or so_diretos):
            from diretos import Diretos
            diretos = Diretos(raiz, hoje, cfg["diretos"], gravar=not args.sem_gravar, espelho=espelho, pasta_tmp=tmp, aceitar=aceitar,
                              registro=registro)
            resultados += diretos.rodar(grupos, so_diretos or None)
        if registro:
            gravados += registro.salvar()
        so_p3m = so - ids_anm - ids_diretos
        if "p3m" in fontes and (not so or so_p3m):
            from p3m import P3M
            p3m = P3M(raiz, hoje, cfg["p3m"], gravar=not args.sem_gravar, espelho=espelho, pasta_tmp=tmp, aceitar=aceitar)
            alvos = p3m.alvos(args.p3m_escopo or cfg["p3m"]["escopo_padrao"], so_p3m or None)
            for i, linha in enumerate(alvos, 1):
                r = p3m.atualizar(linha)
                print(f"[P3M {i}/{len(alvos)}] {r.situacao:11s} {r.nome} {r.motivo}", flush=True)
                resultados.append(r)
            for r in p3m.conferir_chaves():
                print(f"[P3M chave] bloqueada  {r.nome} {r.motivo}", flush=True)
            p3m.gravar_pendentes()
            gravados += p3m.salvar()
            if p3m.mudou and not args.sem_inventario:
                resultados.append(refazer_inventario(raiz, args.catalogo_p3m))
        if args.guardar_barrados:
            guardar_barrados(resultados, Path(args.guardar_barrados))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    for r in resultados:
        if r.fonte != "P3M":
            print(f"[{r.fonte}] {r.situacao:11s} {r.nome} {r.motivo}" + (f" ({'; '.join(r.avisos)})" if r.avisos else ""))
            for linha in r.detalhes.get("diagnostico", []):  # formato da fonte convertida, sem nenhum valor
                print(f"[{r.fonte}]   {linha}")
    md = relatorio_md(resultados, hoje)
    print("\n" + md)
    resumo = {
        "data": hoje,
        "anm_mudou": any(r.fonte == "ANM" and r.situacao == "atualizada" for r in resultados),
        # a base consolidada lê ANM, IBGE (SIDRA) e SGB (RECMIN): qualquer uma que mudou refaz a planilha
        "base_mudou": any(r.fonte in ("ANM", "IBGE", "SGB") and r.situacao == "atualizada" for r in resultados),
        "p3m_mudou": any(r.fonte == "P3M" and r.situacao == "atualizada" for r in resultados),
        "problemas": [r.como_dict() for r in resultados if r.situacao in ("bloqueada", "falhou")],
        "gravados": sorted(set(gravados + [a for r in resultados for a in r.arquivos])),
        "resultados": [r.como_dict() for r in resultados],
    }
    if args.relatorio:
        Path(args.relatorio).write_text(md, encoding="utf-8")
    if args.json:
        gravar_json(args.json, resumo)
    return 1 if resumo["problemas"] else 0


def guardar_barrados(resultados, pasta, mb_arquivo=60, mb_total=400):
    """Copia para `pasta` o arquivo que cada fonte barrada publicou, com um LEIA-ME do motivo, para alguém conferir (o workflow
    sobe a pasta como artefato da execução). Arquivo grande demais vai só com o começo (cabeçalho e primeiras linhas)."""
    barrados = [r for r in resultados if r.situacao == "bloqueada" and r.baixado and Path(r.baixado).exists()]
    if not barrados:
        return
    pasta.mkdir(parents=True, exist_ok=True)
    linhas, total = [], 0
    for r in barrados:
        origem = Path(r.baixado)
        tam = origem.stat().st_size
        destino = pasta / f"{r.fonte}_{origem.name}"
        if tam <= mb_arquivo * 1e6 and total + tam <= mb_total * 1e6:
            shutil.copyfile(origem, destino)
            total += tam
            guardado = destino.name
        else:
            destino = destino.with_name(destino.name + ".inicio")
            with open(origem, "rb") as f:
                destino.write_bytes(f.read(2_000_000))
            guardado = f"{destino.name} (só os primeiros 2 MB de {tam / 1e6:.0f} MB)"
        linhas += [f"{r.fonte} — {r.nome}", f"  arquivo: {guardado}", f"  motivo: {r.motivo}", ""]
    (pasta / "LEIA-ME.txt").write_text("Arquivos que as fontes publicaram e o robô barrou nesta execução. O repositório continua com a "
                                       "versão anterior de cada um.\n\n" + "\n".join(linhas), encoding="utf-8")


def refazer_inventario(raiz, catalogo):
    """Refaz o inventário do P3M (registros, tamanhos, classificação) depois das camadas novas. Com `catalogo`, baixa antes o
    catálogo do site (traz a data de atualização de cada camada no SGB); se o catálogo novo quebrar o inventário, volta ao antigo."""
    r = Resultado("P3M", "inventário (scripts/build_inventario_p3m.py)")
    script = [sys.executable, str(raiz / "scripts" / "build_inventario_p3m.py"), "--mover"]
    if catalogo:
        p = subprocess.run(script + ["--atualizar-catalogo"], cwd=raiz, capture_output=True, text=True)
        if p.returncode == 0:
            r.situacao, r.motivo = "atualizada", "inventário refeito com o catálogo do site baixado hoje"
            return r
        subprocess.run(["git", "checkout", "--", "Squad 1/P3M/catalogo_p3m"], cwd=raiz)
        r.avisos.append("o catálogo novo do site não serviu e foi descartado: " + (p.stdout + p.stderr).strip()[-300:])
    p = subprocess.run(script, cwd=raiz, capture_output=True, text=True)
    if p.returncode:
        r.situacao, r.motivo = "bloqueada", "inventário não refez: " + (p.stdout + p.stderr).strip()[-400:]
    else:
        r.situacao, r.motivo = "atualizada", "inventário refeito"
    return r


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--fontes", default="anm,p3m,ibge,sgb", help="quais fontes, separadas por vírgula: anm, p3m, ibge, sgb (padrão: todas)")
    ap.add_argument("--p3m-escopo", choices=["mapa", "todas"], help="camadas do P3M: as que o mapa usa (padrão) ou todas")
    ap.add_argument("--so", help="só estas fontes (ids de robo/fontes.json) ou camadas do P3M (código vw_… ou nome do zip)")
    ap.add_argument("--sem-gravar", action="store_true", help="baixa e confere, sem gravar nada")
    ap.add_argument("--guardar-barrados", metavar="PASTA", help="copia para PASTA o que cada fonte barrada publicou, com o motivo")
    ap.add_argument("--aceitar-queda", metavar="LISTA",
                    help="fontes da ANM (id ou nome do arquivo) ou camadas do P3M (código vw_… ou nome do zip) em que uma queda grande "
                         "de linhas é legítima: passam sem a trava de 90%% (ANM) e 50%% (P3M). As outras checagens continuam")
    ap.add_argument("--catalogo-p3m", action="store_true", help="baixa de novo o catálogo do site P3M ao refazer o inventário")
    ap.add_argument("--sem-inventario", action="store_true", help="não refaz o inventário do P3M (os testes usam)")
    ap.add_argument("--hoje", help="data a registrar (AAAA-MM-DD); padrão: hoje")
    ap.add_argument("--raiz", default=str(RAIZ), help="raiz do repositório (os testes usam uma cópia)")
    ap.add_argument("--espelho", default=os.environ.get("ROBO_ESPELHO"),
                    help="JSON {url: arquivo local}: lê dali em vez de baixar (testes e reprocessamento; ou a variável ROBO_ESPELHO)")
    ap.add_argument("--relatorio", help="grava o relatório em Markdown aqui")
    ap.add_argument("--json", help="grava o resumo em JSON aqui (o workflow usa)")
    ap.add_argument("--checar", action="store_true", help="checagem de forma dos arquivos do repositório, sem rede")
    ap.add_argument("--conferir-planilha", nargs=2, metavar=("ANTES", "DEPOIS"), help="compara os alertas da aba 14b")
    ap.add_argument("--comparar-xlsx", nargs=2, metavar=("A", "B"), help="sai com 0 se as duas planilhas têm os mesmos valores")
    args = ap.parse_args()
    if args.checar:
        from checagem import checar_repositorio
        problemas = checar_repositorio(Path(args.raiz).resolve())
        print("\n".join(problemas) or "ok: os arquivos do P3M, da ANM, do IBGE e do SGB estão no formato que o site usa")
        sys.exit(3 if problemas else 0)
    if args.conferir_planilha:
        from checagem import conferir_planilha
        problemas, texto = conferir_planilha(*args.conferir_planilha)
        print(texto)
        sys.exit(3 if problemas else 0)
    if args.comparar_xlsx:
        from checagem import mesmo_conteudo_xlsx
        igual = mesmo_conteudo_xlsx(*args.comparar_xlsx)
        print("mesmo conteúdo" if igual else "conteúdo diferente")
        sys.exit(0 if igual else 1)
    sys.exit(rodar(args))


if __name__ == "__main__":
    main()
