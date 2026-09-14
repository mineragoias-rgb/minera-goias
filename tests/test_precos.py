"""Pacote de preço e custo de energia (data/precos/precos.json), gerado por scripts/build_precos_energia.py.

Os testes fixam as decisões metodológicas do módulo: o consumo é observado, o preço é premissa declarada, o custo é
demanda × preço e nenhum nome de pessoa física sai no pacote.
"""
import csv
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'data' / 'precos' / 'precos.json'
PREMISSAS = ROOT / 'Squad 2' / 'precos' / 'premissas'
SAIDAS = ROOT / 'Squad 2' / 'precos' / 'saidas'
CENARIOS = ['conservador', 'referencia', 'expansao']
COMPONENTES = ['energia', 'uso_de_rede', 'encargos_e_perdas']


def ler(caminho):
    with open(caminho, encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


class PrecosTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = json.loads(DATA.read_text(encoding='utf-8'))

    def test_horizon_and_scenarios_are_complete(self):
        d = self.d
        self.assertEqual(d['meta']['horizonte'], [2027, 2040])
        self.assertEqual(d['meta']['cenarios'], CENARIOS)
        self.assertEqual(d['meta']['componentes'], COMPONENTES)
        anos = list(range(2027, 2041))
        self.assertEqual(sorted({r[0] for r in d['precos']['rows']}), anos)
        self.assertEqual(len(d['precos']['rows']), len(anos) * 3)
        # O custo cruza cenário de preço com cenário de demanda: as duas hipóteses são independentes.
        self.assertEqual(len(d['custo']['rows']), len(anos) * 9)
        self.assertEqual(sorted({(r[1], r[2]) for r in d['custo']['rows']}),
                         sorted((p, q) for p in range(3) for q in range(3)))

    def test_price_is_the_sum_of_its_components_and_never_negative(self):
        for ano, cen, energia, rede, encargos, total in self.d['precos']['rows']:
            self.assertTrue(min(energia, rede, encargos) > 0, (ano, cen))
            self.assertAlmostEqual(energia + rede + encargos, total, places=2)

    def test_cost_is_demand_times_price(self):
        preco = {(r[0], r[1]): r[5] for r in self.d['precos']['rows']}
        for ano, ip, _id, mwh, brl in self.d['custo']['rows']:
            self.assertAlmostEqual(mwh * preco[(ano, ip)], brl, delta=0.02)

    def test_every_price_is_declared_as_an_assumption(self):
        # Nenhum preço observado existe no repositório; o pacote não pode sugerir que exista.
        self.assertIn('premissa', self.d['meta']['aviso'].lower())
        for linha in self.d['premissas']['preco'] + self.d['premissas']['demanda']:
            self.assertEqual(linha['data_nature'], 'premissa_ilustrativa')
            self.assertEqual(linha['source_id'], 'SRC_PREMISSA_ILUSTRATIVA')
        fontes = {f['source_id']: f for f in self.d['premissas']['fontes']}
        self.assertEqual(fontes['SRC_PREMISSA_ILUSTRATIVA']['status'], 'em_uso_provisorio')
        # As séries oficiais de preço continuam por coletar: PLD, tarifa, leilões e PDE.
        for sid in ('SRC_CCEE_PLD', 'SRC_ANEEL_TARIFAS', 'SRC_ANEEL_LEILOES', 'SRC_EPE_PDE'):
            self.assertEqual(fontes[sid]['status'], 'a_coletar')
            self.assertEqual(fontes[sid]['data_nature'], 'observado')

    def test_observed_consumption_comes_from_the_ccee_files(self):
        d = self.d
        self.assertEqual(d['meta']['ccee_arquivos'],
                         ['parcela_carga_consumo_2024_GO.csv', 'parcela_carga_consumo_2025_GO.csv',
                          'parcela_carga_consumo_2026_GO.csv'])
        anos = d['observado']['por_ano']
        self.assertEqual([r['ano'] for r in anos], [2024, 2025, 2026])
        for r in anos:
            # Nenhum ano da base está completo: o recorte por título é parte da base e a anualização é média × 12.
            self.assertLess(r['meses'], 12)
            self.assertLessEqual(r['mwh_titular'], r['mwh_base'])
            self.assertAlmostEqual(r['mwh_titular'] / r['meses'] * 12, r['mwh_titular_anualizado'], places=1)
        base = d['meta']['baseline']
        escolhido = max(anos, key=lambda r: (r['meses'], r['ano']))
        self.assertEqual((base['ano'], base['meses']), (escolhido['ano'], escolhido['meses']))
        self.assertAlmostEqual(base['mwh_ano'], escolhido['mwh_titular_anualizado'], places=1)
        self.assertGreater(base['empresas'], 0)

    def test_no_individual_person_is_named(self):
        cpf = re.compile(r'(?<!\d)\d{3}\.?\d{3}\.?\d{3}-?\d{2}(?!\d)')
        for e in self.d['observado']['por_empresa']:
            self.assertNotIn('***', e['nome'])
            self.assertIsNone(cpf.search(e['nome']), e['nome'])

    def test_assumption_files_cover_the_contract(self):
        preco = ler(PREMISSAS / 'premissas_preco_energia.csv')
        self.assertEqual(sorted((r['componente'], r['cenario']) for r in preco),
                         sorted((c, s) for c in COMPONENTES for s in CENARIOS))
        for r in preco:
            self.assertIn(r['metodo'], ('reversao_a_media', 'tendencia_real'))
            if r['metodo'] == 'reversao_a_media':
                self.assertTrue(r['nivel_longo_prazo_brl_mwh'] and r['meia_vida_anos'])
            # Faixa declarada em volta do valor central, em vez de precisão falsa.
            self.assertLessEqual(float(r['faixa_min_brl_mwh']), float(r['preco_base_brl_mwh']))
            self.assertGreaterEqual(float(r['faixa_max_brl_mwh']), float(r['preco_base_brl_mwh']))
        self.assertEqual(sorted(r['cenario'] for r in ler(PREMISSAS / 'premissas_demanda_energia.csv')), sorted(CENARIOS))

    def test_csv_outputs_match_the_package(self):
        precos = ler(SAIDAS / 'precos_energia_projetados.csv')
        self.assertEqual(len(precos), 14 * 3)
        tabela = {(r[0], self.d['meta']['cenarios'][r[1]]): r[5] for r in self.d['precos']['rows']}
        for r in precos:
            self.assertAlmostEqual(float(r['total_brl_mwh']), tabela[(int(r['ano']), r['cenario'])], places=2)
            self.assertEqual(r['data_nature'], 'premissa_ilustrativa')
        observado = ler(SAIDAS / 'consumo_observado_ccee.csv')
        self.assertEqual([r['data_nature'] for r in observado], ['observado'] * len(observado))
        self.assertEqual(len(observado), len(self.d['observado']['por_ano']))

    def test_page_wires_the_price_tab(self):
        cards = (ROOT / 'public' / 'panorama-cards4.js').read_text(encoding='utf-8')
        controller = (ROOT / 'public' / 'panorama.js').read_text(encoding='utf-8')
        self.assertIn("api('/precos')", controller)
        self.assertIn("['precos',['precos']]", controller)
        self.assertIn("'precos'", controller.split('const SECTIONS=')[1].split(';')[0])
        # Todo quadro de preço ou custo projetado carrega o aviso de premissa.
        for card in ('pr_tiles', 'pr_curvas', 'pr_comp', 'pr_custo', 'pr_matriz', 'pr_sens', 'pr_emp', 'pr_premissas'):
            trecho = cards.split(f"id:'{card}'")[1].split('{id:')[0]
            self.assertIn('aviso(X,box', trecho, card)
        markup = (ROOT / 'public' / 'painel.html').read_text(encoding='utf-8')
        self.assertIn('src="/panorama-cards4.js"', markup)


if __name__ == '__main__':
    unittest.main()
