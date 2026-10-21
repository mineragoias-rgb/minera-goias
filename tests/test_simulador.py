"""Parâmetros do simulador (public/data/simulador/) e rastreabilidade da página do Simulador.

O pacote v1 é gerado por scripts/build_simulador_base.py a partir do modelo real do Squad 2
(Squad 2/modello_reale). O v0 fica no repositório como registro da primeira versão.
"""
import ast
import csv
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DADOS = ROOT / 'public' / 'data' / 'simulador'
V0 = DADOS / 'parametros_v0.json'
V1 = DADOS / 'parametros_v1.json'
PUBLIC = ROOT / 'public'
MODELO_S2 = ROOT / 'Squad 2' / 'modello_reale'

GOVERNANCA = (
    'source_id', 'source_name', 'source_url', 'data_acesso', 'periodo_referencia',
    'tipo_fonte', 'valor_observado_estimado', 'metodo_estimacao',
    'status_validacao', 'responsavel_validacao',
)
NATUREZAS = {'observado', 'estimado', 'ilustrativo'}


def tabela_de_intensidade_do_modelo():
    """O arquivo que o modelo do Squad 2 carrega (FINAL_ENERGY_PARAMETERS em src/common.py), lido sem executar o modelo."""
    arvore = ast.parse((MODELO_S2 / 'src' / 'common.py').read_text(encoding='utf-8'))
    for no in ast.walk(arvore):
        if isinstance(no, ast.Assign) and any(getattr(a, 'id', '') == 'FINAL_ENERGY_PARAMETERS' for a in no.targets):
            def partes(n):  # ROOT / 'a' / 'b' é BinOp aninhado à esquerda: lê da esquerda para a direita
                if isinstance(n, ast.BinOp):
                    return partes(n.left) + partes(n.right)
                return [n.value] if isinstance(n, ast.Constant) and isinstance(n.value, str) else []
            return ROOT.joinpath(*partes(no.value))
    raise AssertionError('FINAL_ENERGY_PARAMETERS não encontrado em Squad 2/modello_reale/src/common.py')


class ParametrosV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = json.loads(V1.read_text(encoding='utf-8'))

    def test_versao_horizonte_e_origem_declarados(self):
        self.assertRegex(self.d['versao'], r'^\d+\.\d+\.\d+$')
        self.assertRegex(self.d['data_versao'], r'^\d{4}-\d{2}-\d{2}$')
        self.assertEqual(self.d['horizonte'], {'inicio': 2027, 'fim': 2040})
        origem = self.d['origem_modelo']
        self.assertEqual(origem['diretorio'], 'Squad 2/modello_reale')
        self.assertEqual(origem['gerado_por'], 'scripts/build_simulador_base.py')
        self.assertTrue((ROOT / origem['gerado_por']).is_file())
        self.assertTrue((ROOT / origem['diretorio']).is_dir())

    def test_minerais_batem_com_os_parametros_do_squad_2(self):
        # Contrato de integração: o pacote não pode divergir do modelo que o gerou — nem da tabela que ele usa hoje.
        with tabela_de_intensidade_do_modelo().open(encoding='utf-8-sig') as fh:
            catalogo = {l['mineral_id']: l for l in csv.DictReader(fh)}
        self.assertEqual({m['mineral_id'] for m in self.d['minerais']}, set(catalogo))
        for m in self.d['minerais']:
            fonte = catalogo[m['mineral_id']]
            self.assertEqual(m['mineral_name'], fonte['mineral_name'], m['mineral_id'])
            self.assertEqual(m['production_basis'], fonte['production_basis'], m['mineral_id'])
            self.assertAlmostEqual(m['energy_intensity_mwh_t'],
                                   float(fonte['energy_intensity_mwh_t']), places=9, msg=m['mineral_id'])
            self.assertEqual(m['source_id'], fonte['source_id'], m['mineral_id'])

    def test_cenarios_batem_com_as_hipoteses_do_squad_2(self):
        with (MODELO_S2 / 'parameters' / 'scenarios.csv').open(encoding='utf-8-sig') as fh:
            hipoteses = {l['scenario']: l for l in csv.DictReader(fh)}
        cen = {c['scenario']: c for c in self.d['cenarios']}
        self.assertEqual(set(cen), {'conservador', 'referencia', 'expansao'})
        for nome, c in cen.items():
            self.assertAlmostEqual(c['growth_adjustment'],
                                   float(hipoteses[nome]['growth_adjustment']), places=9, msg=nome)
            self.assertAlmostEqual(c['ganho_eficiencia_anual_padrao'],
                                   float(hipoteses[nome]['annual_efficiency_improvement']), places=9, msg=nome)
            self.assertEqual(c['valor_observado_estimado'], 'ilustrativo')
        self.assertEqual(cen['conservador']['cor'], '#5B8DB8')
        self.assertEqual(cen['referencia']['cor'], '#123B66')
        self.assertEqual(cen['expansao']['cor'], '#C6A15B')
        self.assertLess(cen['conservador']['growth_adjustment'], cen['referencia']['growth_adjustment'])
        self.assertLess(cen['referencia']['growth_adjustment'], cen['expansao']['growth_adjustment'])

    def test_primitivas_de_cada_mineral_sao_utilizaveis(self):
        self.assertEqual(len(self.d['minerais']), self.d['cobertura']['minerais'])
        for m in self.d['minerais']:
            for campo in ('mineral_id', 'mineral_name', 'production_basis', 'ano_base',
                          'producao_base_t', 'crescimento_historico', 'energy_intensity_mwh_t',
                          'valor_observado_estimado', 'source_id'):
                self.assertIn(campo, m, m.get('mineral_id'))
            self.assertGreater(m['producao_base_t'], 0)
            self.assertGreater(m['energy_intensity_mwh_t'], 0)
            self.assertLess(m['ano_base'], self.d['horizonte']['inicio'])
            self.assertGreater(m['crescimento_historico'], -1)
            self.assertIn(m['valor_observado_estimado'], NATUREZAS)
            self.assertIn(m['production_basis'], {'beneficiada', 'conteudo_mineral'})

    def test_a_formula_do_navegador_reproduz_o_modelo_do_squad_2(self):
        # O build grava a maior diferença encontrada ao comparar a fórmula da página
        # com a energia publicada pelo modelo, em todos os minerais, anos e cenários.
        conf = self.d['conferencia_modelo']
        self.assertLess(conf['maior_diferenca_mwh'], 1e-6)
        cen = {c['scenario']: c for c in self.d['cenarios']}
        for chave, scenario, ano in (('referencia_2027_twh', 'referencia', 2027),
                                     ('referencia_2040_twh', 'referencia', 2040),
                                     ('conservador_2040_twh', 'conservador', 2040),
                                     ('expansao_2040_twh', 'expansao', 2040)):
            c = cen[scenario]
            total = 0.0
            for m in self.d['minerais']:
                n = ano - m['ano_base']
                producao = m['producao_base_t'] * (1 + m['crescimento_historico'] + c['growth_adjustment']) ** n
                ie = m['energy_intensity_mwh_t'] * (1 - c['ganho_eficiencia_anual_padrao']) ** n
                total += producao * ie
            self.assertAlmostEqual(self.d['conferencia_modelo'][chave], total / 1e6, places=5, msg=chave)
        self.assertLess(conf['referencia_2027_twh'], conf['referencia_2040_twh'])
        self.assertLess(conf['conservador_2040_twh'], conf['referencia_2040_twh'])
        self.assertLess(conf['referencia_2040_twh'], conf['expansao_2040_twh'])

    def test_faixa_de_sensibilidade_vem_do_contrato_do_squad_2(self):
        s = self.d['sensibilidade_intensidade']
        self.assertEqual((s['minimo_pct'], s['maximo_pct'], s['passo_pct']), (-10, 10, 1))
        self.assertIn('adjustment_pct', s['formula'])

    def test_limites_da_cobertura_ficam_explicitos(self):
        cobertura = self.d['cobertura']
        self.assertFalse(cobertura['toneladas_agregaveis'])
        self.assertIn('nióbio', cobertura['nota'].lower())
        self.assertTrue(cobertura['nota_toneladas'])
        self.assertNotIn('MIN_003', {m['mineral_id'] for m in self.d['minerais']})

    def test_toda_medida_aponta_para_uma_fonte_completa(self):
        fontes = {f['source_id']: f for f in self.d['fontes']}
        for f in self.d['fontes']:
            for campo in GOVERNANCA:
                self.assertIn(campo, f, f['source_id'])
            self.assertIn(f['valor_observado_estimado'], NATUREZAS)
            self.assertRegex(f['data_acesso'], r'^\d{4}-\d{2}-\d{2}$')
            if f['valor_observado_estimado'] != 'observado':
                self.assertTrue(f['metodo_estimacao'], f['source_id'])
                self.assertNotEqual(f['status_validacao'], 'validado')
        # O Squad 2 pode citar várias fontes num mesmo source_id, separadas por ';'.
        referencias = {sid for m in self.d['minerais'] for sid in m['source_id'].split(';')}
        referencias |= {c['source_id'] for c in self.d['cenarios']}
        for sid in referencias:
            self.assertIn(sid, fontes, sid)
        self.assertIn('SRC_SQUAD1_PRODUCAO_001', fontes)

    def test_fontes_do_repositorio_apontam_para_arquivos_que_existem(self):
        for f in self.d['fontes']:
            url = f['source_url']
            if url and not url.startswith('http'):
                self.assertTrue((ROOT / url).exists(), url)


class ParametrosV0Tests(unittest.TestCase):
    """A primeira versão fica no repositório como registro; o simulador não a carrega mais."""

    @classmethod
    def setUpClass(cls):
        cls.d = json.loads(V0.read_text(encoding='utf-8'))

    def test_marcado_como_substituido(self):
        self.assertEqual(self.d['situacao'], 'substituido')
        self.assertEqual(self.d['substituido_por'], 'parametros_v1.json')
        self.assertTrue((DADOS / self.d['substituido_por']).is_file())
        self.assertTrue(self.d['nota_substituicao'])

    def test_rastreabilidade_preservada(self):
        for f in self.d['fontes']:
            for campo in GOVERNANCA:
                self.assertIn(campo, f, f['source_id'])
        self.assertEqual(len(self.d['operacoes']), 7)
        self.assertTrue(self.d['conferencia_baseline']['nota'])


class PaginaTests(unittest.TestCase):
    def test_pagina_carrega_motor_e_a_versao_atual_dos_parametros(self):
        html = (PUBLIC / 'simulador.html').read_text(encoding='utf-8')
        for arquivo in ('/simulador-engine.js', '/simulador.js', '/simulador.css'):
            self.assertIn(arquivo, html)
        js = (PUBLIC / 'simulador.js').read_text(encoding='utf-8')
        self.assertIn('/data/simulador/parametros_v1.json', js)
        self.assertNotIn('parametros_v0.json', js)

    def test_calculo_fica_fora_da_interface(self):
        engine = (PUBLIC / 'simulador-engine.js').read_text(encoding='utf-8')
        self.assertNotIn('document.', engine)
        self.assertNotIn('getElementById', engine)

    def test_simulador_nao_consulta_fonte_externa(self):
        for nome in ('simulador.js', 'simulador-engine.js', 'simulador.html'):
            texto = (PUBLIC / nome).read_text(encoding='utf-8')
            self.assertNotIn('http://', texto, nome)
            self.assertNotIn('https://', texto, nome)

    def test_a_tela_tem_os_tres_controles(self):
        html = (PUBLIC / 'simulador.html').read_text(encoding='utf-8')
        self.assertIn('id="cenarios"', html)
        self.assertIn('id="ganho"', html)
        self.assertIn('id="sensibilidade"', html)


# Padrões genéricos, para que nenhum segredo precise ser escrito neste arquivo.
PROIBIDOS = (
    ('endereço de e-mail', re.compile(r'[\w.+-]+@[\w-]+\.[\w]{2,}')),
    ('credencial declarada', re.compile(r'(senha|password|passwd|secret|token|api[_-]?key)\s*[:=]\s*\S', re.I)),
    ('chave privada', re.compile(r'BEGIN [A-Z ]*PRIVATE KEY')),
    ('token de provedor', re.compile(r'\b(AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{20,})\b')),
)


class SegredosTests(unittest.TestCase):
    def test_nenhum_segredo_ou_dado_pessoal_nos_arquivos(self):
        alvos = [V0, V1, ROOT / 'tests' / 'simulador.test.js', ROOT / 'tests' / 'test_simulador.py',
                 ROOT / 'scripts' / 'build_simulador_base.py']
        alvos += [PUBLIC / n for n in
                  ('simulador.html', 'simulador.css', 'simulador.js', 'simulador-engine.js')]
        alvos.append(ROOT / 'Squad 3' / 'documentacao' / 'simulador' / 'README.md')
        for caminho in alvos:
            texto = caminho.read_text(encoding='utf-8')
            for rotulo, padrao in PROIBIDOS:
                achado = padrao.search(texto)
                self.assertIsNone(achado, f'{caminho.name}: {rotulo} — {achado.group(0) if achado else ""}')


if __name__ == '__main__':
    unittest.main()
