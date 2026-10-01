"""The radar must never invent a forecast, and must say plainly when the collector is absent."""
import json
import os
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'Squad 3' / 'backend'))
import radar_api  # noqa: E402


def rounds_rows():
    """Two open areas, one already auctioned - shaped like ingest_current_rows."""
    records = [
        {'situacao': 'Aguardando Leilão', 'municipio': 'VILA PROPÍCIO',
         'regimedisponibilidade': 'Pesquisa', 'unidadefederacao': 'Goiás'},
        {'situacao': 'Livre', 'municipio': 'VILA PROPÍCIO',
         'regimedisponibilidade': 'Lavra', 'unidadefederacao': 'Goiás'},
        {'situacao': 'Arrematada', 'municipio': 'CATALÃO',
         'regimedisponibilidade': 'Pesquisa', 'unidadefederacao': 'Goiás'},
    ]
    return [{'values_json': json.dumps(r)} for r in records]


class RadarTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        conn = MagicMock()
        conn.cursor.return_value.__enter__.return_value.fetchall.return_value = rounds_rows()
        radar_api.connection_factory = lambda: conn
        self.conn = conn

    def tearDown(self):
        self.tmp.cleanup()
        radar_api.connection_factory = None

    def test_phases_are_split_into_cleared_pending_and_reopening(self):
        phases = radar_api.phase_counts()
        self.assertEqual(set(phases), {'confirmado', 'analise', 'abrindo'})
        cleared = {f['fase'] for f in phases['confirmado']['fases']}
        self.assertIn('CONCESSÃO DE LAVRA', cleared)
        self.assertIn('LICENCIAMENTO', cleared)
        reopening = {f['fase'] for f in phases['abrindo']['fases']}
        self.assertEqual(reopening, {'DISPONIBILIDADE', 'APTO PARA DISPONIBILIDADE'})
        # An application under analysis is never counted as cleared to extract.
        pending = {f['fase'] for f in phases['analise']['fases']}
        self.assertIn('REQUERIMENTO DE LAVRA', pending)
        self.assertNotIn('REQUERIMENTO DE LAVRA', cleared)
        self.assertEqual(sum(p['total'] for p in phases.values()),
                         sum(f['processos'] for p in phases.values() for f in p['fases']))

    def test_unregistered_phase_is_not_counted_as_a_bucket(self):
        phases = radar_api.phase_counts()
        every = {f['fase'] for p in phases.values() for f in p['fases']}
        self.assertNotIn('DADO NÃO CADASTRADO', every)
        self.assertNotIn('', every)

    def test_rounds_count_only_the_areas_still_open(self):
        rounds = radar_api.rounds()
        self.assertEqual(rounds['total'], 3)
        self.assertEqual(rounds['futuras'], 2)  # awaiting auction + no winner
        self.assertEqual(rounds['municipios'], 1)
        self.assertEqual(rounds['top_municipios'], [{'label': 'VILA PROPÍCIO', 'value': 2}])
        self.assertEqual(rounds['fonte'], radar_api.ROUNDS_PATH)

    def test_rounds_are_filtered_to_goias_in_sql(self):
        radar_api.rounds()
        sql, args = self.conn.cursor.return_value.__enter__.return_value.execute.call_args.args
        self.assertIn('unidadefederacao', sql)
        self.assertEqual(args[1], 'Goiás')

    def sem_arquivo_publicado(self):
        """Ignore the packet committed to the repository and read the local collector.

        The published file is the primary source now; these tests are about what
        happens when it is absent, so they point it at a path that does not exist.
        """
        return patch.object(radar_api, 'NEWS_JSON', Path(self.tmp.name) / 'ausente.json')

    def test_missing_collector_is_reported_not_hidden(self):
        with self.sem_arquivo_publicado(),              patch.object(radar_api, 'NEWS_DB', str(Path(self.tmp.name) / 'ausente.sqlite')):
            news = radar_api.news()
        self.assertFalse(news['disponivel'])
        self.assertEqual(news['motivo'], 'coletor_nao_instalado')
        self.assertEqual(news['itens'], [])

    def test_the_published_packet_is_preferred_over_the_local_collector(self):
        """The collector publishes a file; the deploy carries it to the server."""
        publicado = Path(self.tmp.name) / 'latest.json'
        publicado.write_text(json.dumps({
            'disponivel': True, 'atualizado_em': '2026-09-19T18:00:00+00:00',
            'itens': [{'title': 'Mina de terras raras em Goiás', 'link': 'https://exemplo/1',
                       'published_at': '2026-09-19', 'regional': 1, 'setorial': 1,
                       'fonte': 'Brasil Mineral', 'substancias': ['terras_raras']}],
            'total': 2562, 'regionais': 487, 'regionais_setoriais': 174,
        }, ensure_ascii=False), encoding='utf-8')
        with patch.object(radar_api, 'NEWS_JSON', publicado),              patch.object(radar_api, 'NEWS_DB', str(Path(self.tmp.name) / 'ausente.sqlite')):
            news = radar_api.news()
        self.assertTrue(news['disponivel'])
        self.assertEqual(news['total'], 2562)
        self.assertEqual(news['regionais_setoriais'], 174)
        self.assertEqual(news['itens'][0]['substancias'], ['terras_raras'])
        # A packet without the direction layer must still carry the key the page reads.
        self.assertEqual(news['tendencias'], [])

    def test_a_broken_published_packet_falls_back_instead_of_breaking(self):
        quebrado = Path(self.tmp.name) / 'quebrado.json'
        quebrado.write_text('{isto não é json', encoding='utf-8')
        with patch.object(radar_api, 'NEWS_JSON', quebrado),              patch.object(radar_api, 'NEWS_DB', str(Path(self.tmp.name) / 'ausente.sqlite')):
            news = radar_api.news()
        self.assertFalse(news['disponivel'])
        self.assertEqual(news['motivo'], 'coletor_nao_instalado')

    def test_news_is_served_when_the_collector_has_run(self):
        path = Path(self.tmp.name) / 'radar.sqlite'
        sys.path.insert(0, str(ROOT / 'news'))
        import radar as collector
        config = json.loads((ROOT / 'news' / 'feeds.json').read_text(encoding='utf-8'))
        fixture = (ROOT / 'tests' / 'fixtures' / 'news' / 'feed-pt.xml').read_bytes()
        collector.run(str(path), dict(config, sources=config['sources'][:1]), lambda _u: fixture)
        with self.sem_arquivo_publicado(), patch.object(radar_api, 'NEWS_DB', str(path)):
            news = radar_api.news()
        self.assertTrue(news['disponivel'])
        self.assertTrue(news['itens'])
        self.assertTrue(all(item['link'].startswith('http') for item in news['itens']))
        self.assertTrue(any(t['commodity'] == 'terras_raras' for t in news['tendencias']))

    def test_the_note_refuses_to_call_availability_a_project(self):
        with self.sem_arquivo_publicado(),              patch.object(radar_api, 'NEWS_DB', str(Path(self.tmp.name) / 'ausente.sqlite')):
            payload = radar_api.radar(u={'id': 1})
        self.assertIn('não de previsão', payload['nota'])
        self.assertIn('não um projeto anunciado', payload['nota'])

    def test_page_wires_the_claim_explorer(self):
        """Opening a phase lists the claims behind the count, decoded from the snapshot the atlas already serves."""
        markup = (ROOT / 'public' / 'painel.html').read_text(encoding='utf-8')
        for anchor in ('id="rd-explorer"', 'id="rd-search"', 'id="rd-list"', 'id="rd-detail-body"', 'id="rd-detail-map"'):
            self.assertIn(anchor, markup)
        self.assertLess(markup.index('src="/processes.js"'), markup.index('src="/radar.js"'))
        self.assertLess(markup.index('src="/processes.js"'), markup.index('src="/atlas.js"'))
        radar_js = (ROOT / 'public' / 'radar.js').read_text(encoding='utf-8')
        atlas_js = (ROOT / 'public' / 'atlas.js').read_text(encoding='utf-8')
        # One decoder for the 2.6 MB packet, fetched only once a phase is opened.
        for script in (radar_js, atlas_js):
            self.assertIn('window.loadProcesses()', script)
            self.assertNotIn("api('/atlas/processes')", script)
        self.assertIn('data-fase', radar_js)
        self.assertIn('window.atlasShowProcess', atlas_js)


if __name__ == '__main__':
    unittest.main()
