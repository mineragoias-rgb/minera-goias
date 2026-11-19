"""O acervo de notícias só guarda o que é do setor, era notícia quando chegou e diz se é do Brasil.

Cada caso abaixo veio de uma matéria real do acervo de 06/10/2026.
"""
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'Squad 3' / 'radar-noticias'))
import radar  # noqa: E402

CONFIG = json.loads((ROOT / 'Squad 3' / 'radar-noticias' / 'feeds.json').read_text(encoding='utf-8'))
GOOGLE = 'https://news.google.com/rss/articles/CBMi{}?oc=5'


def item(title, link=None, **extra):
    base = {'title': title, 'link': link or GOOGLE.format(abs(hash(title))), 'summary': '',
            'published_at': '2026-10-01T10:00:00+00:00', 'first_seen': '2026-10-02T04:00:00+00:00'}
    return {**base, **extra}


class TituloLimpoTests(unittest.TestCase):
    def test_tira_o_veiculo_que_o_google_cola_no_titulo(self):
        t = radar.titulo_limpo('Vale reabre mina em Minas Gerais - Mineração Brasil', GOOGLE.format(1))
        self.assertEqual(t, 'Vale reabre mina em Minas Gerais')

    def test_tira_o_nome_do_orgao_das_paginas_da_anm(self):
        t = radar.titulo_limpo('Ouvidoria — Agência Nacional de Mineração - www.gov.br', GOOGLE.format(2))
        self.assertEqual(t, 'Ouvidoria')

    def test_titulo_de_feed_direto_fica_inteiro(self):
        titulo = 'Copper - the metal of the future'
        self.assertEqual(radar.titulo_limpo(titulo, 'https://www.mining.com/x/'), titulo)


class SetorialTests(unittest.TestCase):
    def test_pagina_institucional_da_anm_nao_e_do_setor(self):
        for pagina in ('Ouvidoria', 'Emissão de Boletos', 'Biblioteca'):
            with self.subTest(pagina):
                self.assertFalse(radar.setorial(
                    item(f'{pagina} — Agência Nacional de Mineração - www.gov.br'), CONFIG))

    def test_noticia_da_anm_e_do_setor_mesmo_sem_palavra_chave(self):
        self.assertTrue(radar.setorial(item(
            'Nova resolução reforça segurança de barragens no país — Agência Nacional de Mineração - www.gov.br'),
            CONFIG))

    def test_nome_do_veiculo_nao_basta(self):
        self.assertFalse(radar.setorial(item('Governo anuncia pacote de obras - Mineração Brasil'), CONFIG))

    def test_titulo_com_termo_continua_do_setor(self):
        self.assertTrue(radar.setorial(item('Vale reabre mina em Minas Gerais - G1'), CONFIG))

    def test_expressoes_fora_do_setor(self):
        for titulo in ('Ouro Minas completa 30 anos e se reinventa como resort urbano em BH',
                       'Barcelona vende Yerry Mina ao Everton, afirma jornal catalão',
                       "How Tether's bitcoin mining plans in Uruguay unraveled",
                       'Geração Z cobre tudo de strass — e marcas entram na onda'):
            with self.subTest(titulo):
                self.assertFalse(radar.setorial(item(titulo, 'https://exemplo.com/a'), CONFIG))

    def test_rare_earths_no_plural(self):
        self.assertTrue(radar.setorial(
            item('Brazil rare earths project secures offtake', 'https://exemplo.com/b'), CONFIG))


class IdadeTests(unittest.TestCase):
    def test_materia_de_anos_atras_nao_entra(self):
        velha = item('Mineração Serra Verde oferece 135 vagas', published_at='2022-01-04T10:00:00+00:00',
                     first_seen='2026-09-19T19:48:00+00:00')
        self.assertFalse(radar.recente_o_bastante(velha, CONFIG))

    def test_data_de_1970_e_data_ausente(self):
        self.assertFalse(radar.recente_o_bastante(item('x', published_at='1970-01-01T00:00:00+00:00'), CONFIG))

    def test_conta_a_partir_da_coleta_e_nao_de_hoje(self):
        # Publicada há mais de um ano de hoje, mas era notícia quando chegou: fica.
        antiga_mas_coletada_na_hora = item('x', published_at='2024-03-01T10:00:00+00:00',
                                           first_seen='2024-03-02T04:00:00+00:00')
        self.assertTrue(radar.recente_o_bastante(antiga_mas_coletada_na_hora, CONFIG))

    def test_sem_data_de_publicacao_fica(self):
        self.assertTrue(radar.recente_o_bastante(item('x', published_at=None), CONFIG))


class BrasilTests(unittest.TestCase):
    def test_fonte_brasileira_e_do_brasil(self):
        self.assertTrue(radar.sobre_brasil(item('Preço do cobre sobe', fonte='Brasil Mineral',
                                                escopo='setorial'), CONFIG))

    def test_estrangeira_sem_brasil_e_internacional(self):
        self.assertFalse(radar.sobre_brasil(item('Glencore coal mine cleared to 2045', 'https://x.com/a',
                                                 fonte='Mining.com', escopo='internacional'), CONFIG))

    def test_estrangeira_que_cita_o_brasil(self):
        for titulo in ('Brazil court shuts Sigma Lithium mine', 'Vale buys Ligga iron ore stake for $190M'):
            with self.subTest(titulo):
                self.assertTrue(radar.sobre_brasil(item(titulo, 'https://x.com/b', fonte='Mining.com',
                                                        escopo='internacional'), CONFIG))

    def test_busca_estrangeira_com_foco_no_brasil(self):
        self.assertTrue(radar.sobre_brasil(item('Lynas buys into the clay belt - Reuters',
                                                fonte='Busca · rare earth Brazil', escopo='internacional'),
                                           CONFIG))

    def test_o_nome_do_veiculo_nao_faz_a_materia_ser_do_brasil(self):
        self.assertFalse(radar.sobre_brasil(item('Glencore coal mine cleared - Brasil Mineral', fonte='Mining.com',
                                                 escopo='internacional'), CONFIG))


class AcervoTests(unittest.TestCase):
    """A limpeza vale para o que já está publicado, e a recoleta não apaga o histórico."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.db, self.destino = base / 'radar.sqlite', base / 'noticias'
        connection = sqlite3.connect(self.db)
        radar.schema(connection)
        radar.remember_source(connection, 'src', {'name': 'Mining.com', 'url': 'https://www.mining.com/feed/',
                                                  'escopo': 'internacional', 'tema': 'mineracao'}, 'ok')
        # A boa voltou no feed hoje: o banco a vê como nova.
        connection.execute('INSERT INTO news_items VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                           ('id-boa', 'src', 'Brazil court shuts Sigma Lithium mine', 'https://x.com/boa', '',
                            '2026-09-20T10:00:00+00:00', '2026-10-06T04:00:00+00:00', 'run', 0, None, 1))
        connection.commit()
        connection.close()
        publicadas = [
            {'title': 'Brazil court shuts Sigma Lithium mine', 'link': 'https://x.com/boa',
             'published_at': '2026-09-20T10:00:00+00:00', 'first_seen': '2026-09-21T04:00:00+00:00',
             'regional': 0, 'regiao_termo': None, 'setorial': 1, 'fonte': 'Mining.com',
             'escopo': 'internacional', 'tema': 'mineracao', 'substancias': ['litio']},
            {'title': 'Ouvidoria — Agência Nacional de Mineração - www.gov.br', 'link': GOOGLE.format(9),
             'published_at': '2026-09-01T10:00:00+00:00', 'first_seen': '2026-09-19T19:00:00+00:00',
             'regional': 0, 'regiao_termo': None, 'setorial': 1, 'fonte': 'Busca · ANM (site oficial)',
             'escopo': 'setorial', 'tema': 'mineracao', 'substancias': []},
            {'title': 'Mineração Serra Verde oferece 135 vagas em Goiás', 'link': 'https://x.com/velha',
             'published_at': '2022-01-04T10:00:00+00:00', 'first_seen': '2026-09-19T19:00:00+00:00',
             'regional': 1, 'regiao_termo': 'goias', 'setorial': 1, 'fonte': 'Brasil Mineral',
             'escopo': 'setorial', 'tema': 'mineracao', 'substancias': []},
        ]
        radar.write_json(self.destino / 'meses' / '2026-09.json',
                         {'mes': '2026-09', 'materias': len(publicadas), 'itens': publicadas})

    def tearDown(self):
        self.tmp.cleanup()

    def exporta(self):
        return radar.export_archive(self.db, self.destino, desde='2025-11', config=CONFIG)

    def test_tira_pagina_e_materia_velha_do_que_ja_estava_publicado(self):
        pacote = self.exporta()
        links = [i['link'] for i in pacote['itens']]
        self.assertEqual(links, ['https://x.com/boa'])
        self.assertEqual(pacote['descartadas_antigas'], 1)

    def test_recoleta_preserva_a_primeira_vez_que_a_materia_foi_vista(self):
        boa = self.exporta()['itens'][0]
        self.assertEqual(boa['first_seen'], '2026-09-21T04:00:00+00:00')

    def test_marca_brasil_e_conta(self):
        pacote = self.exporta()
        self.assertEqual(pacote['itens'][0]['brasil'], 1)
        self.assertEqual(pacote['brasileiras'], 1)

    def test_exportar_duas_vezes_da_o_mesmo_acervo(self):
        primeiro = self.exporta()
        segundo = self.exporta()
        self.assertEqual([i['link'] for i in primeiro['itens']], [i['link'] for i in segundo['itens']])
        self.assertEqual(primeiro['total'], segundo['total'])


if __name__ == '__main__':
    unittest.main()
