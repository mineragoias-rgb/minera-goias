# -*- coding: utf-8 -*-
"""Roda o pipeline inteiro, na ordem, e para na primeira falha.

    python base_consolidada_work/scripts/rodar_pipeline.py                     # tudo (~12 min)
    python base_consolidada_work/scripts/rodar_pipeline.py --de build_fato_08  # retoma a partir de uma etapa
    python base_consolidada_work/scripts/rodar_pipeline.py --lista             # só lista as etapas

Travas da atualização (ATUALIZACAO.md, na pasta do projeto): antes da 1ª etapa, o manifesto dos brutos (manifesto_brutos.py) trava
se um arquivo mudou de bytes sem nova data de acesso; no fim, gera documentacao/relatorio_diferencas.md (planilha anterior × nova)
e aplica travas.py à aba 14b: verificação de nível "bloqueia" com ALERTA termina com código 3 e a planilha não deve ser publicada.
Sem trava, grava o manifesto dos brutos que geraram a planilha.

Funciona a partir de qualquer pasta. Cada etapa roda num processo Python separado, como se o script fosse chamado à mão,
com PYTHONUTF8=1 (vários arquivos são lidos sem declarar encoding). O log completo de cada etapa fica em <TMP>/logs/.
Instruções: LEIA-ME.md nesta pasta.
"""
import argparse
import glob
import importlib.util
import os
import re
import shutil
import subprocess
import sys
import time

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, AQUI)
sys.dont_write_bytecode = True  # importar caminhos.py aqui não deve criar __pycache__ dentro do projeto
from caminhos import ARRANJO, BASE, BRUTOS, TMP  # noqa: E402

ETAPAS = [
    "build_base1_mineral_ano", "build_base2_municipio_ano", "build_base3_empresa_mineral_ano", "build_base4_mapas",
    "build_fato_08", "build_interface_12", "build_projetos_04", "build_ocorrencias_06", "build_mapas_04_06",
    "write_base1_into_workbook", "write_base2_into_workbook", "write_base3_into_workbook", "write_base4_into_workbook",
    "write_ocorrencias_06_into_workbook", "write_projetos_04_into_workbook", "write_interface_12_into_workbook",
    "write_fato_08_into_workbook", "write_repositorio_erros_into_workbook", "write_governanca_into_workbook",
]
PACOTES = ["pandas", "numpy", "openpyxl", "geopandas", "pyogrio", "shapely", "pyproj", "matplotlib"]
V0 = "prototipo_bases_consolidadas_v0.xlsx"
# cada entrada lista caminhos alternativos: no GitHub o modelo v0 fica em documentacao/modelo_demo/ (o importador do site ignora "demo")
# dados brutos: dados/ na cópia de trabalho ou Squad 1/Dados brutos/ no GitHub (ver caminhos.py)
ENTRADAS = [["dados", BRUTOS], [os.path.join("documentacao", "modelo_demo", V0), os.path.join("documentacao", V0)]]


def main():
    ap = argparse.ArgumentParser(description="Pipeline da planilha consolidada do MINERA Goiás (Squad 1).")
    ap.add_argument("--de", choices=ETAPAS, metavar="ETAPA", help="começa nesta etapa (as anteriores já precisam ter rodado)")
    ap.add_argument("--lista", action="store_true", help="lista as etapas e sai")
    args = ap.parse_args()
    if args.lista:
        for i, e in enumerate(ETAPAS, 1):
            print(f"{i:2d}. {e}")
        return 0
    if sys.version_info < (3, 11):
        print(f"Precisa de Python 3.11 ou mais novo (este é {sys.version.split()[0]}).")
        return 1
    faltam = [p for p in PACOTES if importlib.util.find_spec(p) is None]
    if faltam:
        print("Pacotes faltando: " + ", ".join(faltam) + ". Instale com: pip install -r base_consolidada_work/requirements.txt")
        return 1
    ausentes = [" ou ".join(alts) for alts in ENTRADAS if not any(os.path.exists(os.path.join(BASE, a)) for a in alts)]
    if ausentes:
        print(f"Entradas não encontradas em {BASE}: " + ", ".join(ausentes))
        return 1

    logs = os.path.join(TMP, "logs")
    os.makedirs(logs, exist_ok=True)
    env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8", PYTHONDONTWRITEBYTECODE="1", MINERA_TMP=TMP)  # sem __pycache__ na pasta
    inicio = ETAPAS.index(args.de) if args.de else 0
    print(f"projeto: {BASE}")
    print(f"dados brutos: {BRUTOS if ARRANJO == 'github' else os.path.join(BASE, 'dados')} (arranjo: {ARRANJO})")
    print(f"intermediários e logs: {TMP}")

    # trava 1: brutos que mudaram de bytes sem nova data de acesso (ERR_040)
    import manifesto_brutos
    travas_brutos, ln = manifesto_brutos.conferir()
    print(ln[0])
    if travas_brutos:
        print("\n".join(f"TRAVA: {t}" for t in travas_brutos))
        print("ATUALIZAÇÃO TRAVADA antes de rodar: corrija os brutos acima (passo a passo em ATUALIZACAO.md).")
        return 3
    # a planilha publicada, para o relatório de diferenças (ao retomar com --de, vale a cópia da execução que começou do zero)
    anterior = os.path.join(TMP, "planilha_anterior.xlsx")
    vs = [(int(m.group(1)), p) for p in glob.glob(os.path.join(BASE, "documentacao", "prototipo_bases_consolidadas_v*.xlsx"))
          if (m := re.search(r"_v(\d+)\.xlsx$", p))]
    if vs and (not args.de or not os.path.exists(anterior)):
        shutil.copyfile(max(vs)[1], anterior)
    t0 = time.time()
    for i in range(inicio, len(ETAPAS)):
        etapa, t = ETAPAS[i], time.time()
        log = os.path.join(logs, etapa + ".log")
        with open(log, "w", encoding="utf-8") as f:
            r = subprocess.run([sys.executable, os.path.join(AQUI, etapa + ".py")], stdout=f, stderr=subprocess.STDOUT, env=env)
        situacao = "ok" if r.returncode == 0 else "FALHOU"
        print(f"[{i + 1:2d}/{len(ETAPAS)}] {situacao:6s} {etapa} ({time.time() - t:.0f} s)", flush=True)
        if r.returncode:
            with open(log, encoding="utf-8", errors="replace") as f:
                print(f.read()[-4000:])
            print(f"Log completo: {log}")
            print(f'Depois de corrigir, retome com: python "{os.path.abspath(__file__)}" --de {etapa}')
            return r.returncode
    with open(os.path.join(logs, ETAPAS[-1] + ".log"), encoding="utf-8", errors="replace") as f:
        salvo = [linha.strip() for linha in f if linha.startswith("SALVO:")]
    print(f"concluído em {time.time() - t0:.0f} s" + (f" — {salvo[-1]}" if salvo else ""))
    return travar(salvo[-1][len("SALVO:"):].strip() if salvo else None, anterior if os.path.exists(anterior) else None)


def travar(nova, anterior):
    """Relatório de diferenças e trava 2 (aba 14b, travas.py). 0 = pode publicar; 3 = travou."""
    import manifesto_brutos
    import travas
    if not nova or not os.path.exists(nova):
        print("TRAVA: a planilha final não foi encontrada no log da governança")
        return 3
    if anterior:
        import relatorio_diferencas
        md, _ = relatorio_diferencas.relatorio(anterior, nova)
        saida = os.path.join(BASE, "documentacao", "relatorio_diferencas.md")
        with open(saida, "w", encoding="utf-8", newline="\n") as f:
            f.write(md)
        print(f"relatório de diferenças (planilha anterior × nova): {saida}")
    bloqueios, avisos, linhas = travas.conferir(nova, anterior)
    print(travas.texto(bloqueios, avisos, linhas))
    if bloqueios:
        return 3
    print(f"manifesto dos brutos: {manifesto_brutos.gravar()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
