"""Indicadores municipais (Atlas · Território · Visão do mapa · Indicadores): pacote de dados, rota autenticada e ligação ao painel.

O pacote em data/indicadores sai de scripts/build_indicadores_municipais.py; o teste test_json_reproduz_o_xlsx confere cada valor com o xlsx do Squad 2."""
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
JSON = ROOT / 'data' / 'indicadores' / 'indicadores_municipais.json'
XLSX = ROOT / 'Squad 2' / 'indicadores_compostos' / 'entregas' / 'MINERA_Goias_Indicadores_2025.xlsx'
PUBLIC = ROOT / 'public'
IDS = ['R1', 'R2', 'R3', 'R4', 'R5', 'R6', 'P1', 'P2', 'P3', 'P4', 'A1', 'A2', 'A3', 'A4', 'A5', 'A6', 'S1', 'S2', 'S3', 'T1', 'T2', 'T3']


class PacoteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p = json.loads(JSON.read_text(encoding='utf-8'))
        cls.col = {c: [r[j] for r in cls.p['rows']] for j, c in enumerate(cls.p['cols'])}

    def test_vinte_e_dois_indicadores_para_todos_os_municipios(self):
        self.assertEqual([i['id'] for i in self.p['indicadores']], IDS)
        self.assertEqual(len(self.p['rows']), 246)
        self.assertEqual(self.p['cols'], ['cod', *IDS, 'meses'])
        for r in self.p['rows']:
            self.assertEqual(len(r), len(self.p['cols']))

    def test_cada_indicador_tem_texto_nos_dois_idiomas(self):
        for i in self.p['indicadores']:
            for campo in ('familia', 'nome', 'formula', 'leitura'):
                self.assertTrue(i[campo].strip() and i[campo + '_en'].strip(), (i['id'], campo))
            self.assertIn(i['origem'], ('nova', 'antiga'))
        self.assertEqual(len(self.p['meta']['ressalvas']), len(self.p['meta']['ressalvas_en']))

    def test_codigos_sao_os_do_atlas(self):
        atlas = json.loads((ROOT / 'data' / 'atlas' / 'atlas.json').read_text(encoding='utf-8'))
        self.assertEqual(set(self.col['cod']), {m['code'] for m in atlas['municipalities']})
        self.assertEqual(len(set(self.col['cod'])), 246)

    def test_hhi_direto_e_dentro_de_0_e_1(self):
        for c in ('S2', 'T2'):
            v = [x for x in self.col[c] if x is not None]
            self.assertGreater(len(v), 240)
            self.assertTrue(all(0 < x <= 1 for x in v), c)
        # vazio só onde não há processo
        for k, x in enumerate(self.col['S2']):
            self.assertEqual(x is None, self.col['T2'][k] is None)
            if x is None:
                self.assertEqual(self.col['S1'][k], 0)

    def test_hhi_por_receita_so_onde_ha_cfem(self):
        for c in ('S3', 'T3'):
            v = [x for x in self.col[c] if x is not None]
            self.assertGreater(len(v), 100)
            self.assertTrue(all(0 < x <= 1 for x in v), c)
        for k, r1 in enumerate(self.col['R1']):
            com_cfem = r1 is not None and r1 > 0
            self.assertEqual(self.col['S3'][k] is not None, com_cfem, k)
            self.assertEqual(self.col['T3'][k] is not None, com_cfem, k)

    def test_cfem_anual_reproduz_o_crescimento_padrao(self):
        ca = self.p['cfem_anual']
        self.assertEqual(ca['anos'], sorted(ca['anos']))
        self.assertEqual(len(ca['rows']), 246)
        ia, ib = ca['anos'].index(2024), ca['anos'].index(2025)
        for k, (a, r2) in enumerate(zip(ca['rows'], self.col['R2'])):
            esperado = a[ib] / a[ia] - 1 if a[ia] > 0 else None
            self.assertEqual(r2 is None, esperado is None, k)
            if esperado is not None:
                self.assertAlmostEqual(r2, esperado, places=4)
        # a CFEM de 2025 do pacote é a do R1
        for a, r1 in zip(ca['rows'], self.col['R1']):
            self.assertAlmostEqual(a[ib], r1 or 0, delta=0.05)

    def test_dominios_dos_indicadores(self):
        for c in ('R1', 'R3', 'R4', 'R5', 'P1', 'P2', 'P3', 'P4', 'A1', 'A2', 'A3', 'A4', 'A5', 'A6', 'S1', 'T1'):
            self.assertTrue(all(x is None or x >= 0 for x in self.col[c]), c)
        self.assertTrue(all(x >= -1 for x in self.col['R2'] if x is not None))
        for c in ('R1', 'R3', 'R4', 'P1', 'S1', 'T1'):
            self.assertEqual(sum(x is None for x in self.col[c]), 0, c)
        # volatilidade e Sharpe só onde há CFEM; crescimento só onde havia base em 2024
        for k, m in enumerate(self.col['meses']):
            if m == 0:
                self.assertIsNone(self.col['R5'][k]); self.assertIsNone(self.col['R6'][k])
        self.assertTrue(all(0 <= m <= 12 for m in self.col['meses']))

    def test_soma_da_cfem_bate_com_o_panorama(self):
        pan = json.loads((ROOT / 'data' / 'panorama' / 'panorama.json').read_text(encoding='utf-8'))
        cols = pan['cfem']['cols']
        i_ano, i_val = cols.index('ano'), cols.index('valor')
        total = sum(r[i_val] for r in pan['cfem']['rows'] if r[i_ano] == 2025)
        self.assertAlmostEqual(sum(self.col['R1']), total, delta=1)

    def test_combinacoes_fixas_usam_indicadores_existentes(self):
        self.assertGreaterEqual(len(self.p['presets']), 6)
        nomes = ' '.join(x['nome'] for x in self.p['presets']).lower()
        for tema in ('arrecadação', 'risco', 'dependência'):
            self.assertIn(tema, nomes)
        for pr in self.p['presets']:
            self.assertTrue(pr['pesos'] and set(pr['pesos']) <= set(IDS), pr['id'])
            self.assertTrue(all(w > 0 for w in pr['pesos'].values()))
            self.assertAlmostEqual(sum(pr['pesos'].values()), 1.0, places=6, msg=pr['id'])

    def test_json_reproduz_o_xlsx(self):
        try:
            import openpyxl
        except ImportError:
            self.skipTest('openpyxl não instalado')
        ws = openpyxl.load_workbook(XLSX, data_only=True)['Indicadores']
        cab = [c.value for c in ws[1]]
        pos = {i: next(j for j, h in enumerate(cab) if h and str(h).startswith(i + ' ')) for i in IDS}
        xl = {str(int(r[0])): r for r in ws.iter_rows(min_row=2, values_only=True) if r[0] is not None}
        self.assertEqual(set(xl), set(self.col['cod']))
        for k, cod in enumerate(self.col['cod']):
            for i in IDS:
                a, b = self.col[i][k], xl[cod][pos[i]]
                b = None if b in (None, '') else float(b)
                if a is None or b is None:
                    self.assertEqual(a, b, (cod, i))
                else:
                    self.assertAlmostEqual(a, b, delta=1e-5 + abs(b) * 1e-6, msg=(cod, i))


class ProtecaoETelaTests(unittest.TestCase):
    def test_dados_fora_de_public(self):
        self.assertFalse(list(PUBLIC.rglob('indicadores_municipais*')))

    def test_painel_liga_o_indicadores(self):
        html = (PUBLIC / 'painel.html').read_text(encoding='utf-8')
        for trecho in ('data-view="indicadores"', 'id="indicadores-view"', 'id="in-sel"', 'id="in-scale"', 'id="in-map"', 'id="in-explain"',
                       'id="in-rank-bars"', 'id="in-comp-rows"', 'id="in-preset"', '/indicadores.js?v='):
            self.assertIn(trecho, html)
        self.assertLess(html.index('/i18n.js'), html.index('/indicadores.js'))
        # seção própria: nada de indicadores dentro do Atlas
        for resto in ('atlas-ind', 'ind-section', 'value="indicators"'):
            self.assertNotIn(resto, html)
        ini = html.index('id="indicadores-view"'); fim = html.index('id="mercado-view"')
        self.assertLess(ini, fim)
        sec = html[ini:fim]
        # composição em expander acima do mapa, fechado e oculto até escolher a composição; explicação em expander no fim
        self.assertLess(sec.index('id="in-comp-box"'), sec.index('id="in-map"'))
        self.assertRegex(sec, r'<details[^>]*id="in-comp-box"[^>]*hidden')
        self.assertNotRegex(sec, r'<details[^>]*id="in-comp-box"[^>]*\bopen\b')
        self.assertLess(sec.index('id="in-map"'), sec.index('id="in-rank-bars"'))
        self.assertLess(sec.index('id="in-rank-bars"'), sec.index('id="in-explain"'))
        self.assertRegex(sec, r'<details[^>]*id="in-explain-box"')
        self.assertIn('id="in-comp-warn"', sec)
        self.assertNotIn('in-comp-use', html)

    def test_sem_coluna_origem_e_pesos_de_0_a_1(self):
        js = (PUBLIC / 'indicadores.js').read_text(encoding='utf-8')
        self.assertNotIn('in.col.origin', js)
        self.assertNotIn('in-origem', js)
        self.assertIn('type="number" class="in-num"', js)
        self.assertNotIn('type="range"', js)
        self.assertIn('in.sumUnder', js)
        self.assertIn("in-comp-warn", js)

    def test_indicadores_fora_do_atlas(self):
        for nome in ('atlas.js', 'panorama.js'):
            code = (PUBLIC / nome).read_text(encoding='utf-8')
            self.assertNotIn('indicators', code, nome)
            self.assertNotIn('AtInd', code, nome)
        self.assertIn("'indicadores'", (PUBLIC / 'painel.js').read_text(encoding='utf-8'))
        self.assertIn('showIndicadores', (PUBLIC / 'painel.js').read_text(encoding='utf-8'))
        i18n = (PUBLIC / 'i18n.js').read_text(encoding='utf-8')
        self.assertEqual(i18n.count("'nav.indicadores'"), 2)

    def test_secao_le_a_rota_e_desenha_o_proprio_mapa(self):
        js = (PUBLIC / 'indicadores.js').read_text(encoding='utf-8')
        self.assertIn("api('/indicadores')", js)
        self.assertIn("L.map('in-map'", js)
        self.assertIn('recalcularR2', js)
        html = (PUBLIC / 'painel.html').read_text(encoding='utf-8')
        self.assertIn('id="in-ano0"', html)
        self.assertIn('id="in-ano1"', html)
        self.assertIn('window.showIndicadores', js)

    def test_composicao_normaliza_e_pondera_sem_inverter(self):
        code = (PUBLIC / 'indicadores.js').read_text(encoding='utf-8')
        self.assertIn('function minmax', code)
        self.assertIn('function compor', code)
        self.assertNotRegex(code, r'1\s*-\s*(norm|x)\b', 'nenhum indicador é invertido')


try:
    from fastapi.testclient import TestClient
except ImportError:
    TestClient = None


@unittest.skipIf(TestClient is None, 'fastapi não instalado')
class RotaTests(unittest.TestCase):
    def setUp(self):
        sys.path.insert(0, str(ROOT / 'Squad 3' / 'backend'))
        import auth
        import main
        self.tmp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {'AUTH_DB_PATH': self.tmp.name + '/auth.sqlite', 'COOKIE_SECURE': '1'})
        self.env.start()
        with auth.database() as c:
            c.execute('INSERT INTO users(username,name,password_hash,role,must_change) VALUES (?,?,?,?,?)',
                      ('reader', 'reader', auth.password_hash('long-test-password'), 'user', 0))
        self.client = TestClient(main.app, base_url='https://testserver')

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def test_sem_sessao_nao_ve(self):
        self.assertEqual(self.client.get('/api/indicadores').status_code, 401)

    def test_com_sessao_ve_o_pacote(self):
        self.assertEqual(self.client.post('/api/auth/login', json={'username': 'reader', 'password': 'long-test-password'}).status_code, 200)
        r = self.client.get('/api/indicadores')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['meta']['n_municipios'], 246)
        self.assertEqual(len(r.json()['indicadores']), 22)


if __name__ == '__main__':
    unittest.main()
