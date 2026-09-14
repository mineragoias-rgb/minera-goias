"""Aba Visão geral, refeita no modelo do Panorama (public/overview.js).

Os testes fixam o que a aba mede: energia observada em MWh com o recorte por título minerário — o mesmo do Panorama e do
módulo de preços —, contagem nomeada como contagem, e preço sempre com o aviso de premissa.
"""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / 'public'
PANORAMA = json.loads((ROOT / 'data' / 'panorama' / 'panorama.json').read_text(encoding='utf-8'))
PRECOS = json.loads((ROOT / 'data' / 'precos' / 'precos.json').read_text(encoding='utf-8'))


class OverviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.markup = (PUBLIC / 'painel.html').read_text(encoding='utf-8')
        cls.code = (PUBLIC / 'overview.js').read_text(encoding='utf-8')
        cls.painel = (PUBLIC / 'painel.js').read_text(encoding='utf-8')

    def test_page_wires_the_overview(self):
        for script in ('pkg.js', 'overview.js', 'panorama-charts.js'):
            self.assertIn(f'src="/{script}"', self.markup)
        # Os gráficos e o carregador vêm antes de quem os usa.
        self.assertLess(self.markup.index('/pkg.js'), self.markup.index('/overview.js'))
        self.assertLess(self.markup.index('/panorama-charts.js'), self.markup.index('/overview.js'))
        for hook in ('id="ov-content"', 'id="ov-body"', 'id="ov-context"', 'id="ov-source"', 'id="ov-reset"', 'id="ov-export"'):
            self.assertIn(hook, self.markup)
        for card in ('tiles', 'mes', 'ramo', 'mun', 'emp', 'custo', 'cobertura'):
            self.assertIn(f'id="ov-c-{card}"', self.markup)
            self.assertIn(f"{{id:'{card}'", self.code)
        self.assertIn('window.showOverview', self.code)
        self.assertIn("if(name==='overview'&&window.showOverview)window.showOverview()", self.painel)

    def test_filters_change_every_number(self):
        # Sem botão de aplicar: cada filtro redesenha os quadros na hora.
        self.assertIn("FILTER_IDS.forEach(id=>el(id).onchange=render)", self.code)
        self.assertNotIn('filter-form', self.markup)
        self.assertNotIn('filter-form', self.painel)
        for control in ('id="ov-y0"', 'id="ov-y1"', 'id="ov-mes"', 'id="ov-mun"', 'id="ov-ramo"'):
            self.assertIn(control, self.markup)

    def test_the_old_record_counts_are_gone_from_the_headline(self):
        # A aba media contagem de linhas como se fosse volume; isso não volta.
        for velho in ('metric-records', 'metric-cities', 'metric-months', 'metric-files', 'months-chart', 'cities-chart',
                      'sectors-chart', 'id="year"', 'id="activity"'):
            self.assertNotIn(velho, self.markup, velho)
        self.assertNotIn('function bars(', self.painel)
        self.assertNotIn('function months(', self.painel)

    def test_packages_are_loaded_once(self):
        # Todas as abas pedem os pacotes pelo carregador compartilhado, nunca direto.
        self.assertIn("PKG.get('/panorama')", self.code)
        for arquivo in ('overview.js', 'panorama.js', 'atlas.js'):
            code = (PUBLIC / arquivo).read_text(encoding='utf-8')
            self.assertEqual(re.findall(r"(?<!PKG\.)\bapi\('/(?:panorama|precos|atlas)", code), [], arquivo)

    def test_the_mineral_cut_is_the_same_across_packages(self):
        """O recorte da aba (título minerário pela raiz do CNPJ) tem de dar o mesmo que o pacote de preços."""
        self.assertIn('const mineral=r=>P.dims.ce[r[3]][2]>=0', self.code)
        ce = PANORAMA['dims']['ce']
        por_ano = {}
        for mes, _mun, _ramo, emp, _acl, _cativo, total, _cap in PANORAMA['ccee']['rows']:
            if ce[emp][2] >= 0:
                por_ano[mes // 100] = por_ano.get(mes // 100, 0) + total
        for linha in PRECOS['observado']['por_ano']:
            self.assertAlmostEqual(por_ano[linha['ano']], linha['mwh_titular'], places=1)

    def test_price_in_the_overview_carries_the_assumption_warning(self):
        trecho = self.code.split("{id:'custo'")[1].split('{id:')[0]
        self.assertIn('aviso(box', trecho)
        self.assertIn("pn-warn", self.code)
        self.assertIn("t('pn.pr.premissa')", self.code)

    def test_the_note_states_the_cut_and_what_the_base_is_not(self):
        self.assertIn('class="notice" data-i18n="ov.note"', self.markup)
        # O texto exibido é o do dicionário, não o de reserva do HTML.
        dicionario = (PUBLIC / 'i18n.js').read_text(encoding='utf-8')
        nota = re.search(r"'ov\.note':\"([^\"]+)\"", dicionario)
        self.assertIsNotNone(nota)
        for termo in ('minerário', 'autodeclarado', 'mercado livre', 'premissa', 'nenhum ano'):
            self.assertIn(termo, nota.group(1).lower(), termo)


if __name__ == '__main__':
    unittest.main()
