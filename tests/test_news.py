"""The radar must stay honest: no duplicates, no verdict without evidence, no invented prices."""
import json
import sqlite3
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'news'))
import radar  # noqa: E402

FIXTURES = ROOT / 'tests' / 'fixtures' / 'news'
CONFIG = json.loads((ROOT / 'news' / 'feeds.json').read_text(encoding='utf-8'))


def two_feeds():
    payloads = [(FIXTURES / 'feed-pt.xml').read_bytes(), (FIXTURES / 'feed-en.xml').read_bytes()]
    state = {'i': 0}

    def fetcher(_url):
        payload = payloads[state['i'] % len(payloads)]
        state['i'] += 1
        return payload
    return fetcher


class RadarTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = str(Path(self.tmp.name) / 'radar.sqlite')
        self.config = dict(CONFIG, sources=CONFIG['sources'][:2])

    def tearDown(self):
        self.tmp.cleanup()

    def query(self, sql, args=()):
        conn = sqlite3.connect(self.db)
        try:
            return conn.execute(sql, args).fetchall()
        finally:
            conn.close()

    def test_collects_and_does_not_duplicate_on_a_second_run(self):
        first = radar.run(self.db, self.config, two_feeds())
        self.assertEqual(first['status'], 'success')
        self.assertEqual(first['new_items'], 8)
        second = radar.run(self.db, self.config, two_feeds())
        self.assertEqual(second['new_items'], 0)
        self.assertEqual(self.query('SELECT COUNT(*) FROM news_items')[0][0], 8)

    def test_prices_are_read_with_currency_unit_and_scale(self):
        radar.run(self.db, self.config, two_feeds())
        prices = {(c, u): a for c, a, u in self.query(
            'SELECT price_currency, price_amount, price_unit FROM news_signals WHERE price_amount IS NOT NULL')}
        self.assertEqual(prices[('US$', '/kg')], 92.0)
        self.assertEqual(prices[('R$', '/mwh')], 61.0)
        # "USD 9 thousand per tonne" must become 9000, not 9.
        self.assertEqual(prices[('USD', 'pertonne')], 9000.0)

    def test_direction_follows_the_wording(self):
        radar.run(self.db, self.config, two_feeds())
        rows = dict(self.query('''SELECT commodity, direction FROM news_signals
            WHERE commodity IN ('terras_raras','litio') GROUP BY commodity'''))
        self.assertEqual(rows['terras_raras'], 'up')
        self.assertEqual(rows['litio'], 'down')

    def test_a_thin_week_gets_no_verdict(self):
        report = radar.run(self.db, self.config, two_feeds())
        verdicts = {t['commodity']: t['verdict'] for t in report['trends']}
        self.assertEqual(verdicts['terras_raras'], 'pressao_de_alta')
        # Only one or two stories: not enough to call a direction, whatever the score.
        self.assertEqual(verdicts['litio'], 'evidencia_insuficiente')
        self.assertEqual(verdicts['energia_eletrica'], 'evidencia_insuficiente')

    def test_a_story_without_a_direction_word_yields_no_signal(self):
        radar.run(self.db, self.config, two_feeds())
        quiet = self.query('''SELECT COUNT(*) FROM news_signals s JOIN news_items i ON i.item_id=s.item_id
            WHERE i.link LIKE '%/pt/5' ''')[0][0]
        self.assertEqual(quiet, 0)

    def test_one_broken_feed_does_not_lose_the_others(self):
        good = (FIXTURES / 'feed-pt.xml').read_bytes()
        state = {'i': 0}

        def flaky(_url):
            state['i'] += 1
            if state['i'] == 1:
                raise urllib.error.URLError('connection refused')
            return good
        report = radar.run(self.db, self.config, flaky)
        self.assertEqual(report['status'], 'partial')
        self.assertEqual(report['errors'], 1)
        self.assertEqual(self.query('SELECT COUNT(*) FROM news_items')[0][0], 5)

    def test_run_history_is_recorded(self):
        radar.run(self.db, self.config, two_feeds())
        runs = self.query('SELECT status, radar_version, summary_json FROM news_runs')
        self.assertEqual(len(runs), 1)
        self.assertEqual(runs[0][0], 'success')
        self.assertEqual(runs[0][1], radar.RADAR_VERSION)
        self.assertIn('trends', json.loads(runs[0][2]))

    def test_atom_and_rss_are_both_understood(self):
        entries = radar.parse_feed((FIXTURES / 'feed-en.xml').read_bytes())
        self.assertEqual(len(entries), 3)
        self.assertTrue(all(e['link'].startswith('https://') for e in entries))
        self.assertTrue(all(e['published_at'] for e in entries))


if __name__ == '__main__':
    unittest.main()
