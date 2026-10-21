"""O orquestrador dos derivados e o workflow que o roda precisam continuar descrevendo a mesma cadeia."""
import importlib.util
import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("atualizar_derivados", ROOT / "scripts" / "atualizar_derivados.py")
derivados = importlib.util.module_from_spec(spec)
spec.loader.exec_module(derivados)
WORKFLOW = (ROOT / ".github" / "workflows" / "atualizar-derivados.yml").read_text(encoding="utf-8")


def versionado(caminho):
    return bool(subprocess.run(["git", "-C", str(ROOT), "ls-files", "--", caminho], capture_output=True, text=True).stdout.strip())


class CadeiaTests(unittest.TestCase):
    def test_cada_etapa_aponta_para_gerador_e_saidas_que_existem(self):
        for nome, cmd, cwd, saidas, deps, testes in derivados.ETAPAS:
            self.assertTrue((ROOT / cwd / cmd[1]).is_file(), f"{nome}: gerador {cmd[1]} não existe")
            for s in saidas:
                self.assertTrue(versionado(s), f"{nome}: saída {s} não está no repositório")
            for t in testes:
                self.assertTrue((ROOT / t).is_file(), f"{nome}: teste {t} não existe")

    def test_dependencias_vem_antes(self):
        vistas = set()
        for nome, _, _, _, deps, _ in derivados.ETAPAS:
            self.assertTrue(set(deps) <= vistas, f"{nome} depende de etapa que ainda não rodou: {set(deps) - vistas}")
            vistas.add(nome)

    def test_o_workflow_dispara_quando_um_gerador_muda(self):
        gatilhos = re.findall(r"^\s+- '([^']+)'", WORKFLOW, re.M)
        for nome, cmd, cwd, *_ in derivados.ETAPAS:
            gerador = (Path(cwd) / cmd[1]).as_posix()
            coberto = any(gerador == g or (g.endswith("/**") and gerador.startswith(g[:-2])) for g in gatilhos)
            self.assertTrue(coberto, f"{nome}: {gerador} não está nos gatilhos do workflow")
        self.assertIn("scripts/atualizar_derivados.py", gatilhos)

    def test_o_workflow_publica_todas_as_saidas(self):
        bloco = re.search(r"saidas=\((.*?)\)", WORKFLOW, re.S).group(1)
        publicadas = re.findall(r'"([^"]+)"|(\S+)', bloco)
        publicadas = [a or b for a, b in publicadas]
        for nome, _, _, saidas, *_ in derivados.ETAPAS:
            for s in saidas:
                self.assertTrue(any(s == p or s.startswith(p.rstrip("/") + "/") for p in publicadas),
                                f"{nome}: {s} não está na lista que o workflow publica")

    def test_mudanca_so_de_data_ou_quebra_de_linha_nao_conta(self):
        self.assertEqual(derivados.sem_datas({"meta": {"built_on": "2026-01-01", "x": 1}, "linhas": [{"data_versao": "a"}]}),
                         {"meta": {"x": 1}, "linhas": [{}]})


if __name__ == "__main__":
    unittest.main()
