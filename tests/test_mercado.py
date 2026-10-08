"""The Mercado tab reads a curated public-source file, so its shape has to hold."""
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / 'public'
DATA = PUBLIC / 'data' / 'mercado' / 'mercado_v1.json'
PROJETOS = PUBLIC / 'data' / 'mercado' / 'projetos_go_v1.json'
PLANILHA = ROOT / 'Squad 1' / 'Dados brutos' / 'Aluno Lucas Maia' / 'projetos_minerais_goias.xlsx'
GERADOR = ROOT / 'scripts' / 'build_projetos_go.py'

PROSE = {
    'operacoes': ('mineral', 'local', 'situacao', 'nota'),
    'transacoes': ('ativo', 'rotulo'),
    'referencias': ('mineral', 'onde', 'receita', 'resultado', 'nota'),
    'regulacao': ('nome', 'descricao'),
    'noticias': ('titulo', 'resumo'),
    'indicadores': ('valor', 'rotulo', 'detalhe'),
}


class MercadoDataTests(unittest.TestCase):
    def setUp(self):
        self.packet = json.loads(DATA.read_text(encoding='utf-8'))

    def test_every_section_has_content(self):
        for section in (*PROSE, 'oportunidades', 'riscos', 'fontes'):
            self.assertTrue(self.packet[section], section)

    def test_prose_fields_carry_both_languages(self):
        for section, fields in PROSE.items():
            for row in self.packet[section]:
                for field in fields:
                    value = row[field]
                    self.assertEqual(set(value), {'pt', 'en'}, f'{section}.{field}')
                    self.assertTrue(value['pt'].strip() and value['en'].strip(), f'{section}.{field}')
        for section in ('oportunidades', 'riscos'):
            for row in self.packet[section]:
                self.assertEqual(set(row), {'pt', 'en'}, section)
        self.assertEqual(set(self.packet['nota']), {'pt', 'en'})

    def test_links_are_https(self):
        links = [row['link'] for row in self.packet['noticias']] + [row['link'] for row in self.packet['fontes']]
        for link in links:
            self.assertTrue(link.startswith('https://'), link)

    def test_news_dates_are_year_month(self):
        for row in self.packet['noticias']:
            self.assertRegex(row['data'], r'^\d{4}-\d{2}$')

    def test_deal_bars_have_a_comparable_number(self):
        # The bar widths come from this field, so it has to be a number in one currency.
        for row in self.packet['transacoes']:
            self.assertIsInstance(row['valor_usd_milhoes'], (int, float))
            self.assertGreater(row['valor_usd_milhoes'], 0)

    def test_metric_tones_match_the_stylesheet(self):
        for row in self.packet['indicadores']:
            self.assertIn(row['tom'], {'a', 'b', 'c', 'd'})


class MercadoPanelTests(unittest.TestCase):
    def setUp(self):
        self.markup = (PUBLIC / 'painel.html').read_text(encoding='utf-8')
        self.code = (PUBLIC / 'mercado.js').read_text(encoding='utf-8')

    def test_the_panel_is_wired_to_the_sidebar_and_the_renderer(self):
        self.assertIn('<button data-view="mercado">', self.markup)
        self.assertIn('id="mercado-view"', self.markup)
        self.assertIn('/mercado.js', self.markup)
        painel = (PUBLIC / 'painel.js').read_text(encoding='utf-8')
        self.assertIn("'radar','mercado'", painel)
        self.assertIn("window.showMercado", painel)
        # Atlas stays the first tab; Mercado must not take its place.
        self.assertEqual(re.findall(r'data-view="(\w+)"', self.markup)[0], 'atlas')

    def test_every_container_the_renderer_fills_exists_in_the_page(self):
        for target in re.findall(r"el\('([\w-]+)'\)", self.code):
            self.assertIn(f'id="{target}"', self.markup, target)

    def test_external_links_open_safely(self):
        for anchor in re.findall(r'<a href="\$\{escape\(r\.link\)\}"[^>]*>', self.code):
            self.assertIn('rel="noopener noreferrer"', anchor)
        self.assertEqual(self.code.count('target="_blank"'), self.code.count('rel="noopener noreferrer"'))


class CarteiraProjetosTests(unittest.TestCase):
    """The project pipeline is the Squad 1 survey published as-is: the generator may only copy, never reinterpret."""

    def setUp(self):
        self.pacote = json.loads(PROJETOS.read_text(encoding='utf-8'))

    def test_o_pacote_e_o_que_o_gerador_produz_da_planilha_versionada(self):
        self.assertEqual(self.pacote['meta']['sha256_origem'], hashlib.sha256(PLANILHA.read_bytes()).hexdigest(),
                         'a planilha mudou: rode python scripts/build_projetos_go.py')
        with tempfile.TemporaryDirectory() as tmp:
            saida = Path(tmp) / 'projetos.json'
            r = subprocess.run([sys.executable, str(GERADOR), '--saida', str(saida)], capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(json.loads(saida.read_text(encoding='utf-8')), self.pacote)

    def test_o_gerador_recusa_planilha_fora_do_vocabulario(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            destino = repo / PLANILHA.relative_to(ROOT)
            destino.parent.mkdir(parents=True)
            with zipfile.ZipFile(PLANILHA) as origem, zipfile.ZipFile(destino, 'w') as copia:
                for item in origem.infolist():
                    dados = origem.read(item)
                    if item.filename == 'xl/worksheets/sheet1.xml':
                        dados = dados.replace(b'GO-015', b'GO-014', 1)
                    copia.writestr(item, dados)
            r = subprocess.run([sys.executable, str(GERADOR), '--repo', str(repo), '--saida', str(repo / 'x.json')],
                               capture_output=True, text=True)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn('ID repetido', r.stderr)

    def test_todo_projeto_esta_na_hierarquia_e_em_goias(self):
        hierarquia = self.pacote['meta']['hierarquia']
        self.assertEqual(hierarquia, ['OPERAÇÃO', 'EXPANSÃO', 'CONSTRUÇÃO', 'DEFINIDO', 'PROVÁVEL', 'POSSÍVEL', 'SINAL'])
        ids = [p['id'] for p in self.pacote['projetos']]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertGreater(len(ids), 0)
        for projeto in self.pacote['projetos']:
            self.assertRegex(projeto['id'], r'^GO-\d{3}$')
            self.assertIn(projeto['maturidade'], hierarquia)
            self.assertIn(projeto['confianca'], self.pacote['meta']['confianca'])

    def test_na_vira_ausencia_e_nao_texto(self):
        texto = json.dumps(self.pacote, ensure_ascii=False)
        self.assertNotIn('"NA"', texto)

    def test_capex_traz_moeda_e_ano(self):
        # Valores de anos diferentes não se somam; sem o ano, a tela não teria como dizer de quando é cada um.
        for projeto in self.pacote['projetos']:
            if projeto['capex']:
                self.assertIsInstance(projeto['capex']['valor'], (int, float))
                self.assertTrue(projeto['capex']['moeda'])
                self.assertIsInstance(projeto['capex']['ano'], int)

    def test_toda_noticia_aponta_para_um_projeto(self):
        ids = {p['id'] for p in self.pacote['projetos']}
        self.assertTrue(self.pacote['noticias'])
        for noticia in self.pacote['noticias']:
            self.assertIn(noticia['projeto_id'], ids)

    def test_links_sao_https(self):
        links = [p['link'] for p in self.pacote['projetos'] if p['link']]
        links += [l for p in self.pacote['projetos'] for l in p['links_adicionais']]
        links += [n['link'] for n in self.pacote['noticias'] if n['link']]
        for link in links:
            self.assertTrue(link.startswith('https://'), link)

    def test_todo_texto_vindo_da_planilha_passa_por_escape(self):
        """Nome de projeto, empresa e evidência entram em innerHTML; sem escape, viram injeção."""
        codigo = (PUBLIC / 'mercado.js').read_text(encoding='utf-8')
        inicio = codigo.index('const PROJETOS=')
        trecho_carteira = codigo[inicio:codigo.index('window.showMercado')]
        cruas = [t.strip() for t in re.findall(r'\$\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}', trecho_carteira)
                 if re.search(r'\b[pnm]\.[a-z_]+', t) and 'escape(' not in t and 'tomMaturidade' not in t
                 and not re.fullmatch(r'\w+', t.strip())]
        self.assertEqual(cruas, [], f'texto de dado interpolado sem escape: {cruas}')

    def test_a_carteira_fica_na_aba_mercado(self):
        markup = (PUBLIC / 'painel.html').read_text(encoding='utf-8')
        secao = markup[markup.index('id="mercado-view"'):markup.index('id="empresas-view"')]
        self.assertIn('id="mk-projetos"', secao)
        self.assertIn('loadProjetos()', (PUBLIC / 'mercado.js').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
