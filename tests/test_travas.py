"""Travas da atualização da base consolidada (travas.py e manifesto_brutos.py, ao lado do pipeline do Squad 1)."""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "Squad 1" / "Bases consolidadas" / "base_consolidada_work" / "scripts"


def carregar(nome):
    spec = importlib.util.spec_from_file_location(nome, SCRIPTS / f"{nome}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@unittest.skipUnless(importlib.util.find_spec("openpyxl"), "precisa de openpyxl")
class TravasTests(unittest.TestCase):
    def setUp(self):
        self.travas = carregar("travas")
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def planilha(self, nome, linhas):
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "14b_validacoes_governanca"
        ws.append(["Validações de governança"])
        ws.append(["verificacao", "n", "resultado", "status"])
        for ln in linhas:
            ws.append(ln)
        caminho = self.dir / nome
        wb.save(caminho)
        return caminho

    def test_base_atual_passa_com_os_alertas_aceitos(self):
        p = self.planilha("v.xlsx", [["Integridade referencial (chaves)", 0, "0", "OK"],
                                     ["Arquivos de dados/ sem source_id no catálogo 07", 12, "x", "ALERTA"],
                                     ["Plausibilidade: CFEM comercializada", 30, "x", "ALERTA"],
                                     ["08: mesma tonelagem de produção em linhas diferentes", 170, "bário × nióbio 2023", "ALERTA"]])
        b, a, _ = self.travas.conferir(p)
        self.assertEqual(b, [])

    def test_bloqueia_trava_e_avisa_nao(self):
        p = self.planilha("v.xlsx", [["Integridade referencial (chaves)", 5, "5 órfãos", "ALERTA"],
                                     ["Repositório de erros (ERR_007): lacunas", 2, "NOVAS (2)", "ALERTA"]])
        b, a, _ = self.travas.conferir(p)
        self.assertEqual(len(b), 1)
        self.assertIn("Integridade referencial", b[0])
        self.assertEqual(len(a), 1)

    def test_acima_do_aceito_vale_o_nivel(self):
        p = self.planilha("v.xlsx", [["Arquivos de dados/ sem source_id no catálogo 07", 13, "x", "ALERTA"],  # bloqueia
                                     ["08: mesma tonelagem de produção", 171, "x", "ALERTA"]])              # avisa
        b, a, _ = self.travas.conferir(p)
        self.assertEqual(len(b), 1)
        self.assertIn("acima do aceito", b[0])
        self.assertEqual(len(a), 1)

    def test_verificacao_desconhecida_com_alerta_trava_e_sumida_trava(self):
        antes = self.planilha("a.xlsx", [["IDs fora do padrão", 0, "0", "OK"], ["Verificação inventada", 0, "0", "OK"]])
        depois = self.planilha("d.xlsx", [["Verificação inventada", 1, "x", "ALERTA"]])
        b, _, _ = self.travas.conferir(depois, antes)
        self.assertEqual(len(b), 2)
        self.assertTrue(any("sumiu" in x for x in b))

    def test_checagem_que_nao_rodou_trava_mesmo_com_ok(self):
        p = self.planilha("v.xlsx", [["Quantidade comercializada da CFEM: unidades", 89,
                                      "Na fonte: (checagem de unidades não executada: arquivo não encontrado)", "OK"]])
        b, _, _ = self.travas.conferir(p)
        self.assertEqual(len(b), 1)
        self.assertIn("não rodou", b[0])

    def test_todo_erro_do_repositorio_tem_nivel_ou_justificativa(self):
        tabela = self.travas.tabela_erros()
        self.assertEqual(tabela.count("| ERR_"), 45)
        self.assertNotIn("classifique em travas.py", tabela)
        self.assertIn("| ERR_005 | trava |", tabela)
        self.assertIn("| ERR_001 | só avisa |", tabela)

    def test_alertas_aceitos_registrados(self):
        ac = json.loads((SCRIPTS / "erros_conhecidos.json").read_text(encoding="utf-8"))["alertas_aceitos"]
        self.assertIn("bário × nióbio no ROM de 2023", ac["08: mesma tonelagem de produção"]["motivo"])
        for v in ac.values():
            self.assertTrue(v["motivo"])
            self.assertIsInstance(v["n_aceito"], int)


class ManifestoTests(unittest.TestCase):
    """manifesto_brutos.py num projeto de mentira (MINERA_BASE e MINERA_BRUTOS apontam para uma pasta temporária)."""

    def rodar(self, base, brutos, *args):
        env = dict(os.environ, MINERA_BASE=str(base), MINERA_BRUTOS=str(brutos), MINERA_TMP=str(base / "tmp"), PYTHONUTF8="1")
        return subprocess.run([sys.executable, str(SCRIPTS / "manifesto_brutos.py"), *args], env=env, capture_output=True, text=True)

    def test_bytes_mudaram_sem_data_nova_trava(self):
        with tempfile.TemporaryDirectory() as tmp:
            base, brutos = Path(tmp) / "Bases consolidadas", Path(tmp) / "Dados brutos"
            (base / "documentacao").mkdir(parents=True)
            amb = brutos / "ANM - Anuário Mineral Brasileiro (AMB)"
            amb.mkdir(parents=True)
            (amb / "Producao_Bruta.csv").write_text("a;b\n1;2\n", encoding="utf-8")
            datas = {"dados/ANM/producao_amb_ral/Producao_Bruta.csv": "2026-10-24"}
            (brutos / "datas_de_acesso.json").write_text(json.dumps(datas), encoding="utf-8")
            self.assertEqual(self.rodar(base, brutos, "--gravar").returncode, 0)
            self.assertEqual(self.rodar(base, brutos).returncode, 0)
            (amb / "Producao_Bruta.csv").write_text("a;b\r\n1;2\r\n", encoding="utf-8")  # quebra de linha trocada (ERR_040)
            r = self.rodar(base, brutos)
            self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
            self.assertIn("ERR_040", r.stdout)
            datas["dados/ANM/producao_amb_ral/Producao_Bruta.csv"] = "2026-11-21"  # download novo registrado
            (brutos / "datas_de_acesso.json").write_text(json.dumps(datas), encoding="utf-8")
            r = self.rodar(base, brutos)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("1 alterados", r.stdout)


if __name__ == "__main__":
    unittest.main()
