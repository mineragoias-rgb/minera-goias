"""The Portuguese and English dictionaries must stay in step with the pages."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / 'public'
KEY = re.compile(r"[{,]\s*'([A-Za-z0-9._]+)':")


def dictionaries():
    source = (PUBLIC / 'i18n.js').read_text(encoding='utf-8')
    body = source.split('const DICT={', 1)[1]
    portuguese, english = body.split("\n},en:{", 1)
    english = english.split("\n}};", 1)[0]
    return set(KEY.findall('{' + portuguese)), set(KEY.findall('{' + english))


def referenced():
    keys = set()
    for page in sorted(PUBLIC.glob('*.html')):
        markup = page.read_text(encoding='utf-8')
        keys.update(re.findall(r'data-i18n(?:-html)?="([^"]+)"', markup))
        for group in re.findall(r'data-i18n-attr="([^"]+)"', markup):
            keys.update(pair.split(':', 1)[1].strip() for pair in group.split(','))
    for script in ('painel.js', 'atlas.js', 'login.js', 'landing.js', 'processes.js', 'panorama.js',
                   'panorama-charts.js', 'panorama-cards1.js', 'panorama-cards2.js',
                   'panorama-cards3.js', 'panorama-analises.js', 'mercado.js', 'empresas.js'):
        code = (PUBLIC / script).read_text(encoding='utf-8')
        keys.update(re.findall(r"(?<![A-Za-z0-9_])t\('([A-Za-z0-9._]+)'", code))
    return keys


class TranslationTests(unittest.TestCase):
    def test_both_languages_define_the_same_keys(self):
        pt, en = dictionaries()
        self.assertGreater(len(pt), 200)
        self.assertEqual(pt - en, set(), 'sem tradução em inglês')
        self.assertEqual(en - pt, set(), 'sem texto em português')

    def test_every_key_used_by_the_pages_exists(self):
        pt, en = dictionaries()
        missing = referenced() - pt
        self.assertEqual(missing, set(), 'chaves usadas mas não traduzidas')
        self.assertEqual(referenced() - en, set())

    def test_pages_load_the_translation_layer_first(self):
        for page, follower in (('index.html', 'landing.js'), ('login.html', 'login.js'),
                               ('painel.html', 'painel.js')):
            markup = (PUBLIC / page).read_text(encoding='utf-8')
            self.assertLess(markup.index('/i18n.js'), markup.index(follower), page)

    def test_atlas_controls_are_present(self):
        markup = (PUBLIC / 'painel.html').read_text(encoding='utf-8')
        self.assertIn('<input type="range" id="atlas-year-from"', markup)
        self.assertIn('<input type="range" id="atlas-year-to"', markup)
        self.assertIn('id="atlas-mun"', markup)
        self.assertIn('id="atlas-minfilter"', markup)
        self.assertIn('id="mun-profile"', markup)
        # The municipal CFEM-by-year chart is gone: cfem_min_ano covers it, broken down by mineral.
        self.assertNotIn('id="mun-evo"', markup)
        code = (PUBLIC / 'atlas.js').read_text(encoding='utf-8')
        # Both ends resolve through the year table, and the span is always ordered.
        self.assertIn("const YEARS=['2022','2023','2024','2025','2026']", code)
        self.assertIn("if(a>b)[a,b]=[b,a]", code)
        # The mouse wheel zooms the map while the pointer is over it.
        self.assertIn("scrollWheelZoom:true", code)
        # Mineral layers keep the municipality selector, which also narrows projects and occurrences.
        self.assertNotIn("el('atlas-mun-wrap').hidden=byMineral", code)
        self.assertIn("String(x.mun)===selectedCode", code)
        self.assertNotIn("const year=el('atlas-year').value", code)
        # The scale under the sliders names every year the span can cover.
        self.assertIn("id=\"atlas-year-ticks\"", markup)
        self.assertIn("YEARS.map((y,i)=>", code)
        # A partial span is summed from the years it covers, never from the total.
        self.assertIn("present.reduce((sum,y)=>sum+source[y],0)", code)
        for hook in ('function selectMun(', 'function profile(', 'municipalitySubstances', 'municipalityDams',
                     'function pointRows(', 'function mineralOptions(', 'MINERAL_LAYERS'):
            self.assertIn(hook, code)
        # The state-wide series block left the atlas; the panorama covers it and honours the filters.
        for gone in ('function chartGeneric(', 'function series(', 'function chartBars('):
            self.assertNotIn(gone, code)

    def test_atlas_is_the_first_panel(self):
        markup = (PUBLIC / 'painel.html').read_text(encoding='utf-8')
        buttons = re.findall(r'data-view="(\w+)"', markup)
        self.assertEqual(buttons[0], 'atlas')
        self.assertIn('<button class="active" data-view="atlas"', markup)
        code = (PUBLIC / 'painel.js').read_text(encoding='utf-8')
        # The retired overview and source-catalogue screens no longer have a route.
        self.assertIn("view('atlas')", code)
        self.assertNotIn("'#visao'", code)
        self.assertNotIn("'#fontes'", code)


if __name__ == '__main__':
    unittest.main()
