"""Inventário das camadas do P3M (Squad 1/P3M/inventario_p3m.csv) e organização por pasta temática."""
import csv
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P3M = ROOT / "Squad 1" / "P3M"
sys.path.insert(0, str(ROOT / "scripts"))
import build_inventario_p3m as inv  # noqa: E402

LINHAS = list(csv.DictReader(open(P3M / "inventario_p3m.csv", encoding="utf-8-sig", newline=""), delimiter=";"))


class InventarioTests(unittest.TestCase):
    def test_inventario_em_dia_e_cada_zip_na_pasta_tematica(self):
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / "build_inventario_p3m.py"), "--verificar"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_uma_linha_por_camada_e_todo_zip_no_inventario(self):
        camadas = [l["camada"] for l in LINHAS]
        self.assertEqual(len(camadas), len(set(camadas)))
        citados = {a for l in LINHAS for col in ("arquivo_original", "arquivo_recortado") for a in l[col].split(";") if a}
        no_disco = {z.relative_to(P3M).as_posix() for z in P3M.rglob("*.zip")}
        self.assertEqual(citados, no_disco)

    def test_pastas_sao_as_oito_tematicas(self):
        self.assertEqual({l["pasta_tematica"] for l in LINHAS}, set(inv.PASTAS.values()))
        for lado in (inv.ORIGINAL, inv.RECORTADO):
            for z in lado.rglob("*.zip"):
                self.assertIn(z.parent.name, inv.PASTAS.values(), z)
                self.assertEqual(z.parent.parent, lado, z)

    def test_o_que_nao_se_recalcula_esta_registrado(self):
        for l in LINHAS:
            self.assertRegex(l["data_download"], r"^\d{4}-\d{2}-\d{2}$", l["camada"])
            self.assertTrue(l["extensao_original"], l["camada"])
            self.assertTrue(l["url_download"] or l["camada"] == "GO_UF_2024", l["camada"])
            self.assertTrue(l["orgao"], l["camada"])

    def test_recorte_bate_com_o_indice_do_recorte(self):
        with open(inv.INDICE_RECORTE, encoding="utf-8-sig", newline="") as f:
            indice = {r["arquivo"]: int(r["registros_em_goias"]) for r in csv.DictReader(f, delimiter=";")}
        for l in LINHAS:
            for a in filter(None, l["arquivo_recortado"].split(";")):
                self.assertEqual(int(l["registros_goias"]), indice[Path(a).name], l["camada"])

    def test_resumo_sem_html(self):
        for l in LINHAS:
            self.assertNotRegex(l["resumo"], r"<[a-zA-Z/]|&[a-z]+;", l["camada"])

    def test_classificacao_do_squad_1_preservada(self):
        # O que o Squad 1 já tinha organizado à mão continua nas pastas dele.
        esperado = {"vw_cprm_go_aflor": "1- Geologia", "vw_cprm_cartas_anomalia": "1- Geologia", "vw_cprm_geocron": "1- Geologia",
                    "vw_cprm_go_lito": "1- Geologia", "vw_cprm_go_petrografia": "1- Geologia", "vw_cprm_lev_aerogf_1": "2- Geofísica",
                    "vw_cprm_go_geoquim": "3- Geoquímica", "vw_cprm_au_dist_br": "4- Recursos minerais",
                    "vw_cprm_ocorr_min": "4- Recursos minerais", "vw_cprm_go_pot_min": "4- Recursos minerais",
                    "vw_cprm_go_rec_min": "4- Recursos minerais"}
        por_camada = {l["camada"]: l["pasta_tematica"] for l in LINHAS}
        for camada, pasta in esperado.items():
            self.assertEqual(por_camada[camada], pasta, camada)


if __name__ == "__main__":
    unittest.main()
