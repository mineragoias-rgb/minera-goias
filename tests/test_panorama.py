"""Pacote da aba Panorama (data/panorama/panorama.json), gerado das bases do Squad 1 por scripts/build_panorama_base.py."""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data' / 'panorama' / 'panorama.json'


class PanoramaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = json.loads(DATA.read_text(encoding='utf-8'))

    def test_tables_are_rectangular_and_indexes_resolve(self):
        d, dims = self.d, self.d['dims']
        for key in ('cfem', 'amb_go', 'amb_br', 'amb_uf', 'proc', 'inv_go', 'inv_br', 'rod', 'ccee'):
            cols = d[key]['cols']
            self.assertTrue(d[key]['rows'], key)
            self.assertTrue(all(len(r) == len(cols) for r in d[key]['rows']), key)
        self.assertEqual(len(dims['mun']), 246)
        self.assertEqual(len(dims['rubrica']), 12)
        for r in d['cfem']['rows']:
            self.assertTrue(r[2] < len(dims['mun']) and r[3] < len(dims['min']) and r[4] < len(dims['emp']))
        for r in d['ccee']['rows']:
            self.assertTrue(r[2] < len(dims['ramo']) and r[3] < len(dims['ce']))

    def test_cfem_matches_the_consolidated_base(self):
        rows = self.d['cfem']['rows']
        self.assertAlmostEqual(sum(r[5] for r in rows), 867578398.91, places=1)
        self.assertEqual(sum(r[6] for r in rows), 38854)
        self.assertAlmostEqual(sum(r[5] for r in rows if r[0] == 2025), 229924046.03, places=1)
        self.assertTrue(all(1 <= r[1] <= 12 for r in rows))

    def test_production_research_claims_and_rounds(self):
        d = self.d
        self.assertAlmostEqual(sum(r[5] for r in d['amb_go']['rows'] if r[0] == 2010), 2823902658.66, places=0)
        self.assertAlmostEqual(sum(r[3] for r in d['inv_go']['rows'] if r[0] == 2003), 16175609.20, places=1)
        self.assertEqual(len(d['proc']['rows']), 16656)
        situacao = d['dims']['sit']
        self.assertEqual(len(d['rod']['rows']), 3632)
        self.assertEqual(sum(1 for r in d['rod']['rows'] if situacao[r[1]] == 'Arrematada'), 942)

    def test_ccee_distributors_are_their_own_group(self):
        # Loads without a sector are the distributors (captive market), kept apart from the free-market sectors.
        ramo = self.d['dims']['ramo']
        self.assertIn(self.d['meta']['ccee_distribuidora'], ramo)
        self.assertNotIn('—', ramo)

    def test_only_companies_are_named(self):
        for cid, nome, raiz, tipo in self.d['dims']['emp']:
            if nome is not None:
                self.assertTrue(cid.startswith('COM_CNPJ_'), cid)
                self.assertNotIn('***', nome)
                self.assertEqual(tipo, 'pj')
        self.assertIn(None, self.d['dims']['venc'])
        cpf = re.compile(r'(?<!\d)\d{3}\.?\d{3}\.?\d{3}-?\d{2}(?!\d)')
        dims = self.d['dims']
        for nome in [e[1] for e in dims['emp'] if e[1]] + [v for v in dims['venc'] if v] + [c[1] for c in dims['ce']]:
            self.assertIsNone(cpf.search(nome), nome)

    def test_page_wires_the_tab(self):
        markup = (ROOT / 'public' / 'painel.html').read_text(encoding='utf-8')
        views = re.findall(r'data-view="(\w+)"', markup)
        # Atlas swallowed the panorama; Mercado keeps the place it took next to it, com Empresas logo abaixo.
        self.assertEqual(views[:4], ['atlas', 'mercado', 'empresas', 'radar'])
        self.assertNotIn('panorama', views)
        self.assertLess(markup.index('id="atlas-view"'), markup.index('id="panorama-view"'))
        self.assertLess(markup.index('id="atlas-map"'), markup.index('id="panorama-view"'))
        self.assertLess(markup.index('id="panorama-view"'), markup.index('id="radar-view"'))
        for script in ('panorama-charts.js', 'panorama-cards1.js', 'panorama-cards2.js', 'panorama-cards3.js', 'panorama-analises.js', 'panorama.js'):
            self.assertIn(f'src="/{script}"', markup)
        self.assertLess(markup.index('/panorama-cards3.js'), markup.index('/panorama.js"'))
        self.assertLess(markup.index('/panorama-analises.js'), markup.index('/panorama.js"'))
        # The category tabs sit above the filters.
        self.assertIn('id="pn-tabs"', markup)
        self.assertLess(markup.index('id="pn-tabs"'), markup.index('class="pn-filters"'))
        self.assertNotIn('id="pn-nav"', markup)
        # One theme bar is the whole page's navigation: above the map, with the map view select demoted.
        self.assertLess(markup.index('id="pn-tabs"'), markup.index('id="atlas-map"'))
        self.assertIn('id="atlas-layer-wrap"', markup)
        # Each tab shows only the filters its cards read.
        panorama = (ROOT / 'public' / 'panorama.js').read_text(encoding='utf-8')
        # Picking a theme moves the map and the panels together.
        self.assertIn('window.atlasSetLayer', panorama)
        # The map selection is the page's geographic scope, and it travels both ways.
        atlas = (ROOT / 'public' / 'atlas.js').read_text(encoding='utf-8')
        self.assertIn('window.panoramaPickMun', panorama)
        self.assertIn('window.panoramaPickMun', atlas)
        self.assertIn('window.atlasSelectMun', atlas)
        # Coming from the panorama filter, the map reframes but the reader stays put.
        self.assertIn('selectMun(code,false)', atlas)
        self.assertIn('window.atlasSelectMun', panorama)
        # An unknown code must not fall through to -1, which means "every municipality".
        self.assertIn('if(i<0)return', panorama)
        # The state-wide series of the atlas are gone: the panorama covers them, with filters.
        self.assertNotIn('id="atlas-series"', markup)
        self.assertNotIn('id="mun-evo"', markup)
        self.assertNotIn("id:'mapa'", (ROOT / 'public' / 'panorama-cards1.js').read_text(encoding='utf-8'))
        self.assertIn('window.atlasSetLayer', atlas)
        self.assertIn("closest('div').hidden=!used.has(k)", panorama)
        self.assertNotIn('pn-off', panorama)
        self.assertIn("api('/panorama')", (ROOT / 'public' / 'panorama.js').read_text(encoding='utf-8'))
        # Every chart text uses the one FONT size set on the svg root, never a size of its own.
        charts = (ROOT / 'public' / 'panorama-charts.js').read_text(encoding='utf-8')
        self.assertIn('const FONT=12', charts)
        # Stacked columns print the column total on top.
        self.assertIn('const all=tot(i),txt=short(all)', charts)
        self.assertEqual(re.findall(r'font-size="\d', charts), [])


if __name__ == '__main__':
    unittest.main()
