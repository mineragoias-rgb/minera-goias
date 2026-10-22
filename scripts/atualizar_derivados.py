# -*- coding: utf-8 -*-
"""Refaz, na ordem certa, tudo o que é derivado das bases do Squad 1 — inclusive o que o Squad 2 deriva delas.

    python scripts/atualizar_derivados.py               # roda tudo e deixa as saídas atualizadas na árvore
    python scripts/atualizar_derivados.py --verificar   # só diz o que está desatualizado; devolve 1 se algo estiver

Cadeia (cada etapa só roda depois das que ela usa):

    planilha consolidada (aba 12) ─► pacote_squad2 ─► intensidade do Squad 2 ─► parâmetros do Simulador
    bases brutas do Squad 1 + CCEE ─► Panorama ─┐
    curadoria de produção ──────────► Produção ─┴► Empresas
    levantamento do Lucas Maia ─────► carteira de projetos (Mercado)
    camadas do P3M (Squad 1/P3M) ───► inventário (classificação, metadados do site, registros, datas) ─► Mapa mineral (data/mapa)

Fica de fora, porque depende de arquivo que não está no repositório: o atlas (`build_atlas_base.py`, precisa do GeoPackage do
projeto) e o download da CCEE (`build_ccee_go.py`, o portal bloqueia acesso automatizado — os CSVs nacionais são baixados à mão).

Regras:
- Etapa que falha não deixa saída pela metade: os arquivos dela voltam ao que está versionado, e as etapas que dependem dela não rodam.
- Mudança que é só a data de geração (`built_on`, `data_versao`…) ou só a quebra de linha não conta: o arquivo volta ao versionado,
  para a automação não publicar commit vazio.
- Depois das etapas, rodam os testes das saídas. Se algum teste falhar, **todas** as saídas voltam ao versionado.

Saída: 0 = tudo certo (com ou sem mudança); 1 = alguma etapa falhou (as outras ficaram atualizadas e testadas);
2 = teste falhou (nada mudou na árvore); 3 = `--verificar` encontrou derivados desatualizados.
"""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PY = sys.executable
S1 = "Squad 1/Bases consolidadas"
INT = "Squad 2/intensidade_energetica"

# nome, comando (relativo à raiz), pasta onde roda, saídas (arquivos ou pastas), etapas de que depende, testes da saída
ETAPAS = [
    ("inventario_p3m", [PY, "scripts/build_inventario_p3m.py"], ".",
     ["Squad 1/P3M/inventario_p3m.csv"], [], ["tests/test_inventario_p3m.py"]),
    # o mapa lê do inventário a data, a pasta temática e a ficha de cada camada do P3M
    ("mapa", [PY, "scripts/build_mapa_base.py"], ".",
     ["data/mapa"], ["inventario_p3m"], ["tests/test_mapa.py"]),
    ("pacote_squad2", [PY, "base_consolidada_work/scripts/gerar_pacote_squad2.py"], S1,
     [f"{S1}/documentacao/pacote_squad2"], [], []),
    ("panorama", [PY, "scripts/build_panorama_base.py"], ".",
     ["data/panorama/panorama.json"], [], ["tests/test_panorama.py"]),
    ("producao", [PY, "scripts/build_producao_base.py"], ".",
     ["data/producao/producao.json", "data/producao/producao.csv"], [], ["tests/test_producao.py"]),
    ("empresas", [PY, "scripts/build_empresas_base.py"], ".",
     ["data/empresas/empresas.json"], ["panorama", "producao"], ["tests/test_empresas.py"]),
    ("intensidade_squad2", [PY, f"{INT}/build_intensidade.py"], ".",
     [f"{INT}/base_intensidade_energetica_v1.csv", f"{INT}/energy_intensity_para_motor_v1.csv",
      f"{INT}/coeficiente_estadual_para_modelo_v1.csv"], ["pacote_squad2"], [f"{INT}/test_intensidade.py"]),
    ("projetos_mercado", [PY, "scripts/build_projetos_go.py"], ".",
     ["public/data/mercado/projetos_go_v1.json"], [], ["tests/test_mercado.py"]),
    ("simulador", [PY, "scripts/build_simulador_base.py"], ".",
     ["public/data/simulador/parametros_v1.json"], ["pacote_squad2", "intensidade_squad2"], ["tests/test_simulador.py"]),
]
# Campos que só registram quando o arquivo foi gerado; mudança só neles não é mudança de dado.
DATAS_DE_GERACAO = {"built_on", "integrated_on", "data_versao"}
# O Simulador grava a data do dia como data de acesso de cada fonte do repositório: também é data de geração.
DATAS_POR_ARQUIVO = {"public/data/simulador/parametros_v1.json": {"data_acesso"}}


def git(*args, check=True):
    r = subprocess.run(["git", "-C", str(REPO), *args], capture_output=True)
    if check and r.returncode:
        raise RuntimeError(f"git {' '.join(args)}: {r.stderr.decode('utf-8', 'replace').strip()}")
    return r.stdout


def alterados(saidas):
    """Arquivos de saída que diferem do versionado (inclusive novos)."""
    out = git("status", "--porcelain", "-z", "--untracked-files=all", "--", *saidas).decode("utf-8")
    return [e[3:] for e in out.split("\0") if e]


def sem_datas(dado, extras=frozenset()):
    ignorar = DATAS_DE_GERACAO | set(extras)
    if isinstance(dado, dict):
        return {k: sem_datas(v, extras) for k, v in dado.items() if k not in ignorar}
    if isinstance(dado, list):
        return [sem_datas(v, extras) for v in dado]
    return dado


def mudou_de_verdade(caminho):
    """Falso quando a diferença é só data de geração ou quebra de linha."""
    novo = (REPO / caminho).read_bytes()
    r = subprocess.run(["git", "-C", str(REPO), "show", f"HEAD:{caminho}"], capture_output=True)
    if r.returncode:
        return True                      # arquivo novo
    velho = r.stdout
    if novo.replace(b"\r\n", b"\n") == velho.replace(b"\r\n", b"\n"):
        return False
    if caminho.endswith(".json"):
        try:
            extras = DATAS_POR_ARQUIVO.get(caminho, set())
            return sem_datas(json.loads(novo.decode("utf-8-sig")), extras) != sem_datas(json.loads(velho.decode("utf-8-sig")), extras)
        except ValueError:
            return True
    return True


def restaurar(saidas):
    for c in alterados(saidas):
        if subprocess.run(["git", "-C", str(REPO), "cat-file", "-e", f"HEAD:{c}"], capture_output=True).returncode == 0:
            git("checkout", "HEAD", "--", c)
        else:
            (REPO / c).unlink(missing_ok=True)


def rodar(cmd, cwd):
    env = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8", "PYTHONDONTWRITEBYTECODE": "1"}
    t0 = time.time()
    r = subprocess.run(cmd, cwd=REPO / cwd, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.returncode, (r.stdout + r.stderr).strip(), time.time() - t0


def teste(caminho):
    if caminho.startswith("tests/"):
        cmd = [PY, "-m", "unittest", "discover", "-s", "tests", "-p", Path(caminho).name]
    else:
        cmd = [PY, caminho]
    return rodar(cmd, ".")


def main():
    ap = argparse.ArgumentParser(description="Refaz os derivados das bases do Squad 1, na ordem de dependência.")
    ap.add_argument("--verificar", action="store_true", help="não altera nada; sai com 3 se algum derivado estiver desatualizado")
    ap.add_argument("--resumo", help="grava aqui um resumo em Markdown (o workflow usa no commit e na página da execução)")
    args = ap.parse_args()

    sujos = alterados([s for e in ETAPAS for s in e[3]])
    if sujos:
        sys.exit("há saídas com alteração não commitada; commite ou descarte antes:\n  " + "\n  ".join(sujos))

    estado, linhas = {}, []
    for nome, cmd, cwd, saidas, deps, _ in ETAPAS:
        falhou = [d for d in deps if estado.get(d) != "ok"]
        if falhou:
            estado[nome] = "pulada"
            linhas.append(f"- **{nome}**: pulada (depende de {', '.join(falhou)})")
            print(f"[{nome}] pulada: depende de {', '.join(falhou)}", flush=True)
            continue
        codigo, log, seg = rodar(cmd, cwd)
        if codigo:
            restaurar(saidas)
            estado[nome] = "falhou"
            ultima = log.splitlines()[-1] if log else f"código {codigo}"
            linhas.append(f"- **{nome}**: FALHOU — {ultima}")
            print(f"[{nome}] FALHOU ({seg:.0f}s): {ultima}", flush=True)
            continue
        for c in alterados(saidas):
            if not mudou_de_verdade(c):
                restaurar([c])
        mudaram = alterados(saidas)
        estado[nome] = "ok"
        linhas.append(f"- **{nome}**: " + (f"atualizou {', '.join(f'`{c}`' for c in mudaram)}" if mudaram else "sem mudança"))
        print(f"[{nome}] ok ({seg:.0f}s): " + (", ".join(mudaram) if mudaram else "sem mudança"), flush=True)

    todas = [s for e in ETAPAS for s in e[3]]
    mudaram = alterados(todas)
    codigo_final = 1 if "falhou" in estado.values() else 0

    if args.verificar:
        restaurar(todas)
        if mudaram:
            print("desatualizados:\n  " + "\n  ".join(mudaram))
            codigo_final = 3
    elif mudaram:
        testes = sorted({t for e in ETAPAS if estado.get(e[0]) == "ok" for t in e[5]})
        for t in testes:
            c, log, _ = teste(t)
            if c:
                restaurar(todas)
                print(f"[testes] {t} FALHOU — nada foi alterado na árvore\n{log[-3000:]}", flush=True)
                linhas.append(f"- **testes**: `{t}` falhou; todas as saídas voltaram ao versionado")
                codigo_final = 2
                break
        else:
            linhas.append(f"- **testes**: {', '.join(f'`{t}`' for t in testes)} passaram")
            print(f"[testes] ok: {', '.join(testes)}", flush=True)

    if args.resumo:
        Path(args.resumo).write_text("\n".join(linhas) + "\n", encoding="utf-8")
    sys.exit(codigo_final)


if __name__ == "__main__":
    main()
