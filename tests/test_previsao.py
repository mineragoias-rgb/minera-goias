"""Aba Previsão de demanda (public/previsao.js) e o pacote que ela lê (public/data/previsao/previsao_v1.json).

O pacote é gerado por scripts/build_previsao_base.py a partir dos outputs do modelo real do Squad 2. Estes testes não
rodam o modelo: conferem a coerência interna do pacote, que ele bate com o Simulador (gerado do mesmo modelo) e com a
tabela de intensidade que o modelo usa, e que a página expõe a aba.
"""
import csv
import json
import math
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / 'public'
PACOTE = PUBLIC / 'data' / 'previsao' / 'previsao_v1.json'
SIMULADOR = PUBLIC / 'data' / 'simulador' / 'parametros_v1.json'
CENARIOS = ['conservador', 'referencia', 'expansao']


class PacoteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = json.loads(PACOTE.read_text(encoding='utf-8'))
        cls.anos = list(range(cls.d['horizonte']['inicio'], cls.d['horizonte']['fim'] + 1))

    def test_cabecalho_e_origem(self):
        self.assertRegex(self.d['versao'], r'^\d+\.\d+\.\d+$')
        self.assertRegex(self.d['data_versao'], r'^\d{4}-\d{2}-\d{2}$')
        self.assertEqual(self.d['horizonte'], {'inicio': 2027, 'fim': 2040})
        self.assertTrue((ROOT / self.d['gerado_por']).is_file())
        for arquivo in [self.d['modelo']['diretorio'], self.d['modelo']['coeficientes'], self.d['modelo']['hipoteses'],
                        *self.d['modelo']['scripts']]:
            self.assertTrue((ROOT / arquivo).exists(), arquivo)
        self.assertEqual([c['cenario'] for c in self.d['cenarios']], CENARIOS)

    def test_cada_mineral_tem_serie_completa_e_faixa_ordenada(self):
        self.assertEqual(len(self.d['minerais']), 5)
        for m in self.d['minerais']:
            self.assertGreaterEqual(len(m['historico']['serie']), 10, m['nome'])
            self.assertEqual(m['historico']['serie'][-1]['ano'], m['ano_base'])
            for c in CENARIOS:
                serie = m['cenarios'][c]['serie']
                self.assertEqual([p['ano'] for p in serie], self.anos, (m['nome'], c))
                for p in serie:
                    self.assertGreater(p['producao_t'], 0)
                    self.assertTrue(math.isclose(p['producao_t'] * p['intensidade_mwh_t'], p['energia_mwh'], rel_tol=1e-6),
                                    (m['nome'], c, p['ano']))
                    self.assertLessEqual(p['baixa_mwh'], p['energia_mwh'])
                    self.assertLessEqual(p['energia_mwh'], p['alta_mwh'])

    def test_total_e_a_soma_dos_minerais(self):
        self.assertEqual(len(self.d['total']), len(self.anos) * 3)
        for linha in self.d['total']:
            soma = sum(next(p for p in m['cenarios'][linha['cenario']]['serie'] if p['ano'] == linha['ano'])['energia_mwh']
                       for m in self.d['minerais'])
            self.assertAlmostEqual(soma, linha['energia_mwh'], delta=0.01)
            self.assertLess(linha['baixa_mwh'], linha['energia_mwh'])
            self.assertLess(linha['energia_mwh'], linha['alta_mwh'])

    def test_cenarios_ficam_na_ordem_esperada(self):
        tot = {(l['ano'], l['cenario']): l['energia_mwh'] for l in self.d['total']}
        fim = self.d['horizonte']['fim']
        self.assertLess(tot[(fim, 'conservador')], tot[(fim, 'referencia')])
        self.assertLess(tot[(fim, 'referencia')], tot[(fim, 'expansao')])

    def test_bate_com_o_simulador_gerado_do_mesmo_modelo(self):
        sim = json.loads(SIMULADOR.read_text(encoding='utf-8'))['conferencia_modelo']
        tot = {(l['ano'], l['cenario']): l['energia_mwh'] / 1e6 for l in self.d['total']}
        self.assertAlmostEqual(tot[(2027, 'referencia')], sim['referencia_2027_twh'], places=4)
        self.assertAlmostEqual(tot[(2040, 'referencia')], sim['referencia_2040_twh'], places=4)
        self.assertAlmostEqual(tot[(2040, 'conservador')], sim['conservador_2040_twh'], places=4)
        self.assertAlmostEqual(tot[(2040, 'expansao')], sim['expansao_2040_twh'], places=4)

    def test_coeficientes_sao_os_da_tabela_que_o_modelo_usa(self):
        with (ROOT / self.d['modelo']['coeficientes']).open(encoding='utf-8-sig') as fh:
            tabela = {l['mineral_id']: float(l['energy_intensity_mwh_t']) for l in csv.DictReader(fh)}
        self.assertEqual({m['mineral_id'] for m in self.d['minerais']}, set(tabela))
        for m in self.d['minerais']:
            self.assertAlmostEqual(m['coeficiente']['mwh_t'], tabela[m['mineral_id']], places=6)

    def test_backtest_registra_as_duas_regras(self):
        for m in self.d['minerais']:
            b = m['backtest']
            self.assertEqual(len(b['detalhe']), b['anos_testados'])
            self.assertIn(b['mape_selecionada'], (b['mape_tendencia'], b['mape_persistencia']))

    def test_toda_fonte_citada_esta_no_catalogo(self):
        catalogo = {f['source_id'] for f in self.d['fontes']}
        for m in self.d['minerais']:
            for sid in m['coeficiente']['fontes'].split(';'):
                self.assertIn(sid, catalogo, m['nome'])
            self.assertIn(m['historico']['fonte'], catalogo | {'SRC_ANM_PROD_BENEF'})
        for c in self.d['cenarios']:
            self.assertIn(c['fonte'], catalogo)


class PaginaTests(unittest.TestCase):
    def test_painel_expoe_a_aba(self):
        markup = (PUBLIC / 'painel.html').read_text(encoding='utf-8')
        self.assertIn('data-view="previsao"', markup)
        self.assertIn('id="previsao-view"', markup)
        for sub in ('pv-previsao', 'pv-dados', 'pv-metodo'):
            self.assertIn(f'id="{sub}"', markup)
        self.assertIn('/previsao.js', markup)
        self.assertIn('/previsao.css', markup)
        nav = (PUBLIC / 'painel.js').read_text(encoding='utf-8')
        self.assertIn("'previsao'", nav)
        self.assertIn('showPrevisao', nav)

    def test_rotulos_cobrem_os_valores_do_pacote(self):
        """Mineral, base, natureza e método aparecem traduzidos; uma chave faltando mostraria o código na tela."""
        d = json.loads(PACOTE.read_text(encoding='utf-8'))
        i18n = (PUBLIC / 'i18n.js').read_text(encoding='utf-8')
        chaves = set()
        for m in d['minerais']:
            chaves |= {f"pv.min.{m['mineral_id']}", f"pv.base.{m['base_producao']}", f"pv.nat.{m['coeficiente']['natureza']}",
                       f"pv.met.{m['backtest']['regra_selecionada']}"}
            chaves |= {f"pv.met.{m['cenarios'][c]['metodo']}" for c in CENARIOS}
        chaves |= {f"pv.nat.{c['natureza']}" for c in d['cenarios']}
        chaves |= {f"pv.nat.{f['valor_observado_estimado']}" for f in d['fontes']}
        for chave in sorted(chaves):
            self.assertEqual(i18n.count(f"'{chave}':"), 2, chave)


if __name__ == '__main__':
    unittest.main()
