"""A base de produção e o agente têm de ficar honestos: nada convertido, nada somado entre unidades, nada validado sozinho."""
import csv
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'producao'))
import agente  # noqa: E402

FIXTURES = ROOT / 'tests' / 'fixtures' / 'producao'
CONFIG = json.loads((ROOT / 'producao' / 'fontes.json').read_text(encoding='utf-8'))
CURADA = json.loads((ROOT / 'producao' / 'base_curada.json').read_text(encoding='utf-8'))
PACOTE = json.loads((ROOT / 'data' / 'producao' / 'producao.json').read_text(encoding='utf-8'))


class BaseCuradaTests(unittest.TestCase):
    """O que está publicado tem de trazer de onde veio e o que mede."""

    def test_todo_registro_declara_fonte_medida_escopo_e_periodo(self):
        for registro in PACOTE['registros']:
            with self.subTest(registro=registro['id']):
                self.assertTrue(registro['fonte_url'].startswith('http'), 'registro sem endereço de fonte')
                self.assertIn(registro['medida'], PACOTE['meta']['vocabulario']['medida'])
                self.assertIn(registro['escopo'], PACOTE['meta']['vocabulario']['escopo'])
                self.assertIn(registro['tipo_valor'], PACOTE['meta']['vocabulario']['tipo_valor'])
                self.assertTrue(registro['periodo'], 'registro sem período')
                self.assertGreater(registro['valor'], 0)

    def test_nenhum_registro_nasce_validado(self):
        # METODOLOGIA.md §1: importar não é validar. A validação é ato humano, registrado à parte.
        self.assertTrue(all(r['status_validacao'] == 'nao_validado' for r in PACOTE['registros']))
        self.assertTrue(all(r['responsavel_validacao'] is None for r in PACOTE['registros']))

    def test_mineral_de_todo_registro_existe_no_dicionario_da_anm(self):
        panorama = json.loads((ROOT / 'data' / 'panorama' / 'panorama.json').read_text(encoding='utf-8'))
        nomes = {m[1] for m in panorama['dims']['min']}
        for registro in PACOTE['registros']:
            self.assertIn(registro['mineral'], nomes, f"{registro['id']} usa mineral fora do dicionário da ANM")

    def test_guidance_e_capacidade_nao_se_passam_por_realizacao(self):
        for registro in PACOTE['registros']:
            if registro['tipo_valor'] == 'guidance':
                self.assertIsNotNone(registro['valor_max'], f"{registro['id']}: guidance sem faixa")
            if registro['medida'] in ('capacidade', 'meta'):
                self.assertNotEqual(registro['tipo_valor'], 'realizado',
                                    f"{registro['id']}: {registro['medida']} não pode valer como produção realizada")

    def test_embarque_e_realizacao_mas_nunca_producao(self):
        """Um embarque que aconteceu é 'realizado' — quem diz que ele não é produção é a 'medida', e isso tem de estar escrito."""
        embarques = [r for r in PACOTE['registros'] if r['medida'] == 'embarque']
        self.assertTrue(embarques, 'a base tem números de embarque e eles precisam continuar marcados como tal')
        for registro in embarques:
            self.assertTrue(registro['observacao'].strip(),
                            f"{registro['id']}: embarque sem observação dizendo que não é produção de mina")
        self.assertTrue(any('embarque' in aviso for aviso in PACOTE['meta']['avisos']),
                        'o pacote precisa avisar que embarque não entra em série de produção')

    def test_escopo_fora_de_goias_esta_marcado_e_e_minoria_identificavel(self):
        fora = [r for r in PACOTE['registros'] if r['escopo'] != 'operacao_goias']
        self.assertTrue(fora, 'a base deve conter e marcar os números consolidados, para não serem confundidos com Goiás')
        for registro in fora:
            self.assertIn('escopo', registro)
            self.assertNotEqual(registro['escopo'], 'operacao_goias')

    def test_a_base_so_traz_valor_declarado_pela_empresa(self):
        """O Anuário mede contido no minério lavrado e a empresa publica produto de planta: uma não corrige a outra e não convivem aqui."""
        self.assertNotIn('referencia_amb_go', PACOTE, 'estatística de agência não entra no pacote')
        self.assertNotIn('agencia_oficial', PACOTE['meta']['vocabulario']['fonte_tipo'])
        for registro in PACOTE['registros']:
            self.assertIn(registro['fonte_tipo'], PACOTE['meta']['vocabulario']['fonte_tipo'],
                          f"{registro['id']}: fonte fora do vocabulário")
            self.assertNotEqual(registro['fonte_tipo'], 'agencia_oficial')

    def test_o_gerador_recusa_registro_apurado_por_agencia(self):
        with tempfile.TemporaryDirectory() as tmp:
            quebrada = json.loads(json.dumps(CURADA))
            quebrada['empresas'][0]['registros'][0]['fonte_tipo'] = 'agencia_oficial'
            repo = self.repo_falso(Path(tmp), quebrada)
            resultado = subprocess.run(
                [sys.executable, str(ROOT / 'scripts' / 'build_producao_base.py'), '--repo', str(repo),
                 '--saida', str(Path(tmp) / 'saida')], capture_output=True, text=True)
            self.assertEqual(resultado.returncode, 1)
            self.assertIn('agencia_oficial', resultado.stdout)

    def test_csv_publicado_tem_as_mesmas_linhas_do_json(self):
        with open(ROOT / 'data' / 'producao' / 'producao.csv', encoding='utf-8', newline='') as arquivo:
            linhas = list(csv.DictReader(arquivo, delimiter=';'))
        self.assertEqual(len(linhas), len(PACOTE['registros']))
        self.assertEqual([linha['id'] for linha in linhas], [r['id'] for r in PACOTE['registros']])

    @staticmethod
    def repo_falso(tmp, curadoria):
        """Clone mínimo para rodar o gerador contra uma curadoria propositalmente quebrada."""
        repo = tmp / 'repo'
        (repo / 'producao').mkdir(parents=True)
        (repo / 'producao' / 'base_curada.json').write_text(json.dumps(curadoria), encoding='utf-8')
        (repo / 'data' / 'panorama').mkdir(parents=True)
        (repo / 'data' / 'panorama' / 'panorama.json').write_bytes(
            (ROOT / 'data' / 'panorama' / 'panorama.json').read_bytes())
        return repo

    def test_o_gerador_recusa_curadoria_com_unidade_fora_do_vocabulario(self):
        with tempfile.TemporaryDirectory() as tmp:
            quebrada = json.loads(json.dumps(CURADA))
            quebrada['empresas'][0]['registros'][0]['unidade'] = 'arrobas'
            repo = self.repo_falso(Path(tmp), quebrada)
            resultado = subprocess.run(
                [sys.executable, str(ROOT / 'scripts' / 'build_producao_base.py'), '--repo', str(repo),
                 '--saida', str(Path(tmp) / 'saida')], capture_output=True, text=True)
            self.assertEqual(resultado.returncode, 1)
            self.assertIn('arrobas', resultado.stdout)


class LeituraDeNumeroTests(unittest.TestCase):
    """Um erro de notação vale mil vezes o número. A grafia decide sempre que puder."""

    def test_grafia_inequivoca_nao_depende_do_idioma_declarado(self):
        for bruto, esperado in [('1.234.567', 1234567.0), ('1,234,567', 1234567.0), ('4.2', 4.2), ('39,7', 39.7)]:
            for idioma in ('pt', 'en'):
                valor, notacao = agente.parse_numero(bruto, idioma)
                with self.subTest(bruto=bruto, idioma=idioma):
                    self.assertEqual(notacao, 'inequivoca')
                    if bruto in ('1.234.567', '1,234,567'):
                        self.assertEqual(valor, esperado)

    def test_tres_casas_e_ambiguo_e_o_idioma_resolve(self):
        self.assertEqual(agente.parse_numero('10.348', 'pt'), (10348.0, 'ambigua_pelo_idioma'))
        self.assertEqual(agente.parse_numero('43,974', 'en'), (43974.0, 'ambigua_pelo_idioma'))
        self.assertEqual(agente.parse_numero('10,348', 'pt'), (10.348, 'ambigua_pelo_idioma'))

    def test_texto_ilegivel_nao_vira_numero(self):
        self.assertEqual(agente.parse_numero('1.2.3,4,5', 'pt')[0], None)


class ConfrontoTests(unittest.TestCase):
    """Unidade diferente é resultado do confronto, nunca motivo para aplicar um fator."""

    def setUp(self):
        self.indice = agente.indexa_curada(CURADA)
        self.tolerancia = CONFIG['confronto']['tolerancia_relativa']

    def candidato(self, **campos):
        base = {'empresa': 'ANGLO AMERICAN NIQUEL BRASIL LTDA', 'mineral': 'Níquel', 'valor': 39700.0,
                'unidade': 't', 'periodo': '2025', 'medida': 'produto_acabado'}
        return {**base, **campos}

    def test_valor_igual_confirma(self):
        self.assertEqual(agente.confronta(self.candidato(), self.indice, self.tolerancia)[0], 'confirma')

    def test_diferenca_acima_da_tolerancia_diverge(self):
        veredito, delta, _, _, _ = agente.confronta(self.candidato(valor=41000.0), self.indice, self.tolerancia)
        self.assertEqual(veredito, 'diverge')
        self.assertGreater(delta, self.tolerancia)

    def test_arredondamento_de_publicacao_cabe_na_tolerancia(self):
        # 39,7 kt publicado contra 39.700 t curados não pode virar divergência.
        self.assertEqual(agente.confronta(self.candidato(valor=39650.0), self.indice, self.tolerancia)[0], 'confirma')

    def test_unidade_diferente_nao_e_convertida(self):
        veredito, delta, _, _, medida_ok = agente.confronta(
            self.candidato(empresa='AMARILLO MINERACAO DO BRASIL LTDA', mineral='Ouro', periodo='2025-Q4',
                           valor=0.2, unidade='kg'), self.indice, self.tolerancia)
        self.assertEqual(veredito, 'unidade_divergente')
        self.assertIsNone(delta)

    def test_sem_periodo_no_texto_nao_ha_confronto(self):
        self.assertEqual(agente.confronta(self.candidato(periodo=None), self.indice, self.tolerancia)[0], 'sem_periodo')

    def test_medida_diferente_viaja_junto_com_a_confirmacao(self):
        veredito, _, _, medida_base, medida_ok = agente.confronta(
            self.candidato(empresa='SERRA VERDE PESQUISA E MINERACAO LTDA', mineral='Monazita e Terras-Raras',
                           periodo='2025', valor=678.0, medida='produto_acabado'), self.indice, self.tolerancia)
        self.assertEqual(veredito, 'confirma')
        self.assertEqual(medida_base, 'embarque')
        self.assertEqual(medida_ok, 0, 'embarque confirmado como produção tem de sair marcado')


class AgenteTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = str(Path(self.tmp.name) / 'producao.sqlite')
        fontes = [f for f in CONFIG['fontes'] if f.get('lang') == 'pt'][:1] + \
                 [f for f in CONFIG['fontes'] if f.get('lang') == 'en'][:1]
        self.config = dict(CONFIG, fontes=fontes)
        self.fetcher = agente.offline_fetcher(FIXTURES, self.config)

    def tearDown(self):
        self.tmp.cleanup()

    def consulta(self, sql, args=()):
        conexao = sqlite3.connect(self.db)
        try:
            return conexao.execute(sql, args).fetchall()
        finally:
            conexao.close()

    def test_extrai_numero_mineral_unidade_e_periodo_da_frase(self):
        relatorio = agente.run(self.db, self.config, CURADA, self.fetcher)
        self.assertEqual(relatorio['status'], 'success')
        linhas = self.consulta('SELECT mineral, valor, unidade, periodo FROM prod_candidatos '
                               "WHERE mineral='Nióbio' AND periodo='2025-S1'")
        self.assertIn(('Nióbio', 5231.0, 't', '2025-S1'), linhas)

    def test_semestre_nao_e_lido_como_ano(self):
        agente.run(self.db, self.config, CURADA, self.fetcher)
        periodos = {linha[0] for linha in self.consulta('SELECT periodo FROM prod_candidatos')}
        self.assertIn('2025-S1', periodos)

    def test_todo_candidato_guarda_a_frase_e_o_endereco_que_o_originaram(self):
        agente.run(self.db, self.config, CURADA, self.fetcher)
        for evidencia, url in self.consulta('SELECT evidencia, fonte_url FROM prod_candidatos'):
            self.assertTrue(evidencia.strip())
            self.assertTrue(url.startswith('http'))

    def test_candidato_nasce_nao_validado(self):
        agente.run(self.db, self.config, CURADA, self.fetcher)
        estados = {linha[0] for linha in self.consulta('SELECT status_validacao FROM prod_candidatos')}
        self.assertEqual(estados, {'nao_validado'})

    def test_reexecutar_nao_duplica_materia(self):
        agente.run(self.db, self.config, CURADA, self.fetcher)
        primeiro = self.consulta('SELECT COUNT(*) FROM prod_itens')[0][0]
        agente.run(self.db, self.config, CURADA, agente.offline_fetcher(FIXTURES, self.config))
        self.assertEqual(self.consulta('SELECT COUNT(*) FROM prod_itens')[0][0], primeiro)

    def test_numero_sem_periodo_no_texto_nao_ganha_o_ano_da_materia(self):
        agente.run(self.db, self.config, CURADA, self.fetcher)
        linhas = self.consulta("SELECT periodo, confronto FROM prod_candidatos WHERE confronto='sem_periodo'")
        self.assertTrue(linhas)
        self.assertTrue(all(linha[0] is None for linha in linhas))

    def test_unidade_desconhecida_vira_proposta_e_nao_candidato(self):
        agente.run(self.db, self.config, CURADA, self.fetcher)
        propostas = self.consulta("SELECT assinatura FROM prod_propostas WHERE tipo='unidade'")
        self.assertIn(('sacas',), propostas)
        self.assertEqual(self.consulta("SELECT COUNT(*) FROM prod_candidatos WHERE unidade='sacas'")[0][0], 0)

    def test_com_auto_promocao_desligada_nada_e_promovido(self):
        config = json.loads(json.dumps(self.config))
        config['auto_promocao'].update(ativa=False, min_ocorrencias=1, min_fontes_distintas=1, min_execucoes=1)
        agente.run(self.db, config, CURADA, self.fetcher)
        estados = {linha[0] for linha in self.consulta('SELECT status FROM prod_propostas')}
        self.assertNotIn('promovida', estados)
        self.assertIn('elegivel_aguardando_revisao', estados)

    def test_com_auto_promocao_ligada_a_decisao_fica_registrada_com_o_motivo(self):
        config = json.loads(json.dumps(self.config))
        config['auto_promocao'].update(ativa=True, min_ocorrencias=1, min_fontes_distintas=1, min_execucoes=1)
        agente.run(self.db, config, CURADA, self.fetcher)
        decisoes = self.consulta("SELECT tipo, alvo, motivo FROM prod_decisoes")
        self.assertTrue(decisoes)
        self.assertTrue(all(linha[2].strip() for linha in decisoes), 'promoção sem motivo registrado')

    def test_uma_fonte_fora_do_ar_nao_derruba_a_execucao(self):
        def fetcher_ruim(url):
            if 'google' in url:
                raise OSError('fonte fora do ar')
            return self.fetcher(url)
        relatorio = agente.run(self.db, self.config, CURADA, fetcher_ruim)
        self.assertEqual(relatorio['status'], 'partial')
        self.assertGreaterEqual(relatorio['erros'], 1)

    def test_a_base_curada_nao_e_reescrita_pelo_agente(self):
        antes = (ROOT / 'producao' / 'base_curada.json').read_bytes()
        agente.run(self.db, self.config, CURADA, self.fetcher)
        self.assertEqual((ROOT / 'producao' / 'base_curada.json').read_bytes(), antes)


if __name__ == '__main__':
    unittest.main()
