"""Aba Território e emissões: relatório do Squad 2 só atrás da sessão, nunca em public/, e ligado ao painel."""
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
PASTA = ROOT / 'Squad 2' / 'mineracao_cerrado'


class ArquivosTests(unittest.TestCase):
    def test_relatorio_e_camada_fora_de_public(self):
        self.assertTrue((PASTA / 'relatorio_mineracao_cerrado_GO.html').is_file())
        self.assertTrue((PASTA / 'GO_radar_risco_ambiental.geojson').is_file())
        self.assertFalse(list((ROOT / 'public').rglob('*mineracao_cerrado*')))
        self.assertFalse(list((ROOT / 'public').rglob('*risco_ambiental*')))

    def test_relatorio_nao_carrega_script_de_fora(self):
        html = (PASTA / 'relatorio_mineracao_cerrado_GO.html').read_text(encoding='utf-8')
        self.assertNotRegex(html, r'<script[^>]+src=')
        for url in re.findall(r'(?:href|src)="(https?://[^"]+)"', html):
            self.assertTrue(url.startswith('https://fonts.googleapis.com'), url)

    def test_camada_sem_nome_de_pessoa_fisica(self):
        g = json.loads((PASTA / 'GO_radar_risco_ambiental.geojson').read_text(encoding='utf-8'))
        cpf = re.compile(r'\d{3}\.?\d{3}\.?\d{3}-?\d{2}')
        for f in g['features']:
            self.assertNotRegex(json.dumps(f['properties'], ensure_ascii=False), cpf, f['properties'].get('id'))

    def test_aba_no_painel(self):
        markup = (ROOT / 'public' / 'painel.html').read_text(encoding='utf-8')
        self.assertIn('data-view="territorio"', markup)
        self.assertIn('id="territorio-view"', markup)
        self.assertIn('id="te-frame"', markup)
        self.assertNotRegex(markup, r'id="te-frame"[^>]*\ssrc=')  # o iframe só carrega quando a aba abre
        code = (ROOT / 'public' / 'painel.js').read_text(encoding='utf-8')
        self.assertIn("'territorio'", code)
        self.assertIn('/api/territorio/relatorio', code)


try:
    from fastapi.testclient import TestClient
except ImportError:  # o CI instala; numa máquina sem fastapi, só os testes de arquivo rodam
    TestClient = None


@unittest.skipIf(TestClient is None, 'fastapi não instalado')
class RotaTests(unittest.TestCase):
    def setUp(self):
        sys.path.insert(0, str(ROOT / 'Squad 3' / 'backend'))
        import auth
        import main
        self.auth = auth
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
        self.assertEqual(self.client.get('/api/territorio/relatorio').status_code, 401)
        self.assertEqual(self.client.get('/api/territorio/risco.geojson').status_code, 401)

    def test_com_sessao_ve_com_csp(self):
        r = self.client.post('/api/auth/login', json={'username': 'reader', 'password': 'long-test-password'})
        self.assertEqual(r.status_code, 200)
        r = self.client.get('/api/territorio/relatorio')
        self.assertEqual(r.status_code, 200)
        self.assertIn('Mineração e Cerrado em Goiás', r.text)
        self.assertIn("frame-ancestors 'self'", r.headers['content-security-policy'])
        self.assertEqual(r.headers['x-frame-options'], 'SAMEORIGIN')
        g = self.client.get('/api/territorio/risco.geojson')
        self.assertEqual(g.status_code, 200)
        self.assertEqual(len(g.json()['features']), 1046)


if __name__ == '__main__':
    unittest.main()
