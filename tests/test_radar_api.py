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
        self.assertLess(markup.index('src="/processes.js?v='), markup.index('src="/radar.js?v='))
        self.assertLess(markup.index('src="/processes.js?v='), markup.index('src="/atlas.js?v='))
        radar_js = (ROOT / 'public' / 'radar.js').read_text(encoding='utf-8')
        atlas_js = (ROOT / 'public' / 'atlas.js').read_text(encoding='utf-8')
        # One decoder for the 2.6 MB packet, fetched only once a phase is opened.
        for script in (radar_js, atlas_js):
            self.assertIn('window.loadProcesses()', script)
            self.assertNotIn("api('/atlas/processes')", script)
        self.assertIn('data-fase', radar_js)
        self.assertIn('window.atlasShowProcess', atlas_js)


class AbasTests(unittest.TestCase):
    """O Radar é três abas: cadastro, notícias e o cruzamento das duas."""

    @classmethod
    def setUpClass(cls):
        cls.markup = (ROOT / 'public' / 'painel.html').read_text(encoding='utf-8')
        cls.js = (ROOT / 'public' / 'radar.js').read_text(encoding='utf-8')

    def test_a_barra_de_abas_vem_antes_do_conteudo(self):
        self.assertIn('id="rd-tabs"', self.markup)
        self.assertLess(self.markup.index('id="rd-tabs"'), self.markup.index('id="radar-error"'))
        for aba in ('anm', 'noticias', 'cruzamento'):
            self.assertIn(f'data-rd="{aba}"', self.markup)
            self.assertIn(f'id="rd-aba-{aba}"', self.markup)
        # Reusa a barra do Panorama, que já está carregada: nenhum CSS novo para as abas.
        self.assertIn('class="pn-tabs page-nav" id="rd-tabs"', self.markup)

    def test_o_painel_da_aba_nao_usa_o_id_do_conteudo_interno(self):
        # #rd-noticias é o contêiner que newsBlock preenche; escondê-lo esconderia o
        # conteúdo em vez do painel.
        self.assertIn('id="rd-aba-noticias"', self.markup)
        self.assertIn("el('rd-aba-'+k).hidden=k!==aba", self.js)

    def test_o_explorador_de_fases_sobreviveu_a_mudanca(self):
        for ancora in ('id="rd-explorer"', 'id="rd-search"', 'id="rd-list"',
                       'id="rd-detail-body"', 'id="rd-detail-map"'):
            self.assertIn(ancora, self.markup)
        self.assertIn('data-fase', self.js)
        self.assertIn('window.loadProcesses()', self.js)

    def test_o_cruzamento_carrega_sob_demanda(self):
        # showRadar é idempotente e pinta tudo numa passada; o cruzamento busca o próprio
        # recorte só quando a aba abre, como o explorador faz com o pacote de processos.
        self.assertIn("api('/radar/cruzamento')", self.js)
        self.assertIn('if(CX){desenharCruzamento();return}', self.js)
        for ancora in ('id="rd-cx-div"', 'id="rd-cx-tabela"', 'id="rd-cx-escopos"',
                       'id="rd-cx-cartoes"', 'id="rd-cx-loading"'):
            self.assertIn(ancora, self.markup)

    def test_o_pnc_e_lido_em_tempo_de_execucao(self):
        # painel.html carrega radar.js antes de panorama-charts.js: capturar window.PNC no
        # topo da IIFE daria undefined para sempre.
        self.assertLess(self.markup.index('src="/radar.js?v='),
                        self.markup.index('src="/panorama-charts.js?v='))
        self.assertIn('const C=window.PNC;', self.js)

    def test_as_barras_do_cruzamento_mantem_a_linha_de_valor_zero(self):
        # Areia é 20,7% do cadastro e 0% das manchetes: a ausência é o achado, e o hbar do
        # Panorama descarta a linha de valor zero.
        self.assertIn('function bars(rows,color,fmt)', self.js)
        self.assertNotIn('C.hbar(', self.js)


class CruzamentoTests(unittest.TestCase):
    """Atenção, cadastro e caixa da mesma substância — e o que a aba não afirma."""

    def setUp(self):
        radar_api._anm_subs.update(mtime=None, value=None)
        radar_api._news_file.update(mtime=None, value=None)
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()
        radar_api._anm_subs.update(mtime=None, value=None)
        radar_api._news_file.update(mtime=None, value=None)

    def com_imprensa(self, por_escopo=None):
        """O cruzamento sobre um pacote de imprensa controlado.

        Os testes não podem depender do que o coletor publicou hoje: ele regenera
        public/data/noticias/ todo dia às 04:00 UTC, e o eixo da imprensa mudaria
        debaixo deles.
        """
        padrao = {
            'goias': {'materias': 600, 'com_substancia': 400, 'substancias': {
                'terras_raras': {'materias': 270, 'unicas': 151},
                'ouro': {'materias': 168, 'unicas': 13},
                'cobre': {'materias': 6, 'unicas': 6}}},
            'brasil': {'materias': 3000, 'com_substancia': 2000, 'substancias': {
                'terras_raras': {'materias': 1900, 'unicas': 1500},
                'ouro': {'materias': 280, 'unicas': 120}}},
            'tudo': {'materias': 5000, 'com_substancia': 4000, 'substancias': {
                'terras_raras': {'materias': 2000, 'unicas': 1700},
                'ouro': {'materias': 1000, 'unicas': 800},
                'cobre': {'materias': 500, 'unicas': 480}}},
        }
        caminho = Path(self.tmp.name) / 'latest.json'
        caminho.write_text(json.dumps({'itens': [], 'total': 5000, 'coleta_desde': '2026-09',
                                       'substancias_por_escopo': por_escopo or padrao}), encoding='utf-8')
        with patch.object(radar_api, 'NEWS_JSON', caminho):
            radar_api._news_file.update(mtime=None, value=None)
            return radar_api.cruzamento()

    def test_todo_nome_mapeado_existe_no_cadastro(self):
        """Um nome errado no mapa somaria zero em silêncio, e a aba leria como ausência."""
        pacote = json.loads((ROOT / 'data' / 'panorama' / 'panorama.json').read_text(encoding='utf-8'))
        nomes = {linha[1] for linha in pacote['dims']['min']}
        for chave, lista in radar_api.CRUZAMENTO_MIN.items():
            for nome in lista:
                self.assertIn(nome, nomes, f'{chave}: {nome}')

    def test_nenhum_nome_da_anm_serve_a_duas_substancias(self):
        visto = {}
        for chave, lista in radar_api.CRUZAMENTO_MIN.items():
            for nome in lista:
                self.assertNotIn(nome, visto, f'{nome} em {chave} e {visto.get(nome)}')
                visto[nome] = chave

    def test_a_tabela_cobre_quase_todo_o_cadastro_e_a_arrecadacao(self):
        # Sem isto, a aba compararia a imprensa com uma fatia do cadastro sem dizer qual.
        cobertura = self.com_imprensa()['cobertura']
        self.assertGreater(cobertura['cfem'], 0.95)
        self.assertGreater(cobertura['processos'], 0.9)

    def test_os_tres_eixos_somam_cem_no_mesmo_universo(self):
        linhas = self.com_imprensa()['dados']['tudo']['linhas']
        for campo in ('unicas_pct', 'processos_pct', 'cfem_pct'):
            soma = sum(linha[campo] for linha in linhas if linha[campo] is not None)
            self.assertAlmostEqual(soma, 100.0, places=0, msg=campo)

    def test_a_imprensa_vem_quebrada_por_escopo_do_pacote_publicado(self):
        dados = self.com_imprensa()['dados']
        self.assertEqual(set(dados), set(radar_api.ESCOPOS))
        # Goiás é um subconjunto: o cadastro e a CFEM são de Goiás, e o escopo errado
        # trocaria a população comparada.
        self.assertLessEqual(dados['goias']['materias'], dados['brasil']['materias'])
        self.assertLessEqual(dados['brasil']['materias'], dados['tudo']['materias'])

    def test_publicacoes_e_manchetes_sao_contadas_separadamente(self):
        # No recorte de Goiás o ouro tem ~13 manchetes e ~168 publicações: sem separar,
        # a sindicalização passaria por atenção.
        linhas = {l['chave']: l for l in self.com_imprensa()['dados']['goias']['linhas']}
        self.assertGreater(linhas['ouro']['materias'], linhas['ouro']['unicas'])

    def test_pacote_sem_a_quebra_degrada_em_vez_de_quebrar(self):
        # Entre o deploy do backend e o próximo run do coletor (04:00 UTC) há até 24 h.
        antigo = Path(self.tmp.name) / 'antigo.json'
        antigo.write_text(json.dumps({'itens': [], 'total': 9}), encoding='utf-8')
        with patch.object(radar_api, 'NEWS_JSON', antigo):
            radar_api._news_file.update(mtime=None, value=None)
            payload = radar_api.cruzamento()
        self.assertFalse(payload['imprensa_disponivel'])
        primeira = payload['dados']['goias']['linhas'][0]
        self.assertGreater(primeira['processos'], 0)
        # None, e não zero: zero afirmaria que ninguém escreveu sobre a substância.
        self.assertIsNone(primeira['materias'])
        self.assertIsNone(primeira['distancia'])

    def test_a_distancia_e_diferenca_e_nunca_razao(self):
        # Lítio tem R$ 0 de CFEM e urânio tem 0 processos e R$ 0.
        linhas = {l['chave']: l for l in self.com_imprensa()['dados']['tudo']['linhas']}
        self.assertEqual(linhas['uranio']['processos'], 0)
        self.assertEqual(linhas['litio']['cfem'], 0)
        for chave in ('uranio', 'litio'):
            self.assertIsInstance(linhas[chave]['distancia'], float)

    def test_a_nota_recusa_afirmar_antecipacao(self):
        nota = self.com_imprensa()['nota']
        self.assertIn('não mede antecipação', nota)
        self.assertIn('não é previsão', nota)

    def test_o_panorama_e_lido_uma_vez_por_versao_do_arquivo(self):
        radar_api.anm_por_substancia()
        with patch.object(Path, 'read_text', side_effect=AssertionError('releu o arquivo')):
            radar_api.anm_por_substancia()


if __name__ == '__main__':
    unittest.main()
