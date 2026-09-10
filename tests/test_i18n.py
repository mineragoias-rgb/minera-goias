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
    for script in ('painel.js', 'atlas.js', 'login.js', 'landing.js'):
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
        missing = {k for k in referenced() if not k.startswith('at.s.')} - pt
        self.assertEqual(missing, set(), 'chaves usadas mas não traduzidas')
        self.assertEqual({k for k in referenced() if not k.startswith('at.s.')} - en, set())

    def test_series_keys_are_complete_in_both_languages(self):
        pt, en = dictionaries()
        for series in ('cfem_years', 'cfem_comparable', 'energy_months', 'beneficiated', 'investment'):
            for part in ('title', 'note', 'unit'):
                key = f'at.s.{series}.{part}'
                self.assertIn(key, pt)
                self.assertIn(key, en)

    def test_pages_load_the_translation_layer_first(self):
        for page, follower in (('index.html', 'landing.js'), ('login.html', 'login.js'),
                               ('painel.html', 'painel.js')):
            markup = (PUBLIC / page).read_text(encoding='utf-8')
            self.assertLess(markup.index('/i18n.js'), markup.index(follower), page)

    def test_atlas_is_the_first_panel(self):
        markup = (PUBLIC / 'painel.html').read_text(encoding='utf-8')
        buttons = re.findall(r'data-view="(\w+)"', markup)
        self.assertEqual(buttons[0], 'atlas')
        self.assertIn('<button class="active" data-view="atlas"', markup)
        self.assertIn("location.hash==='#visao'?'overview':'atlas'",
                      (PUBLIC / 'painel.js').read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
