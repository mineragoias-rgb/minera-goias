"""A aba Empresas cruza duas fontes com cobertura diferente: o que é medido e o que é estimado não podem se confundir."""
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / 'public'
PACOTE = json.loads((ROOT / 'data' / 'empresas' / 'empresas.json').read_text(encoding='utf-8'))
PRODUCAO = json.loads((ROOT / 'data' / 'producao' / 'producao.json').read_text(encoding='utf-8'))
PANORAMA = json.loads((ROOT / 'data' / 'panorama' / 'panorama.json').read_text(encoding='utf-8'))
MESES = {'S1': set(range(1, 7)), 'S2': set(range(7, 13)), 'Q1': {1, 2, 3}, 'Q2': {4, 5, 6},
         'Q3': {7, 8, 9}, 'Q4': {10, 11, 12}}


class PacoteTests(unittest.TestCase):
    def test_toda_linha_diz_de_onde_veio_cada_lado(self):
        self.assertTrue(PACOTE['linhas'])
        for linha in PACOTE['linhas']:
            with self.subTest(empresa=linha['empresa'], ano=linha['ano'], mineral=linha['mineral']):
                self.assertTrue(linha['cnpj_raiz'])
                if linha['energia']:
                    self.assertGreater(linha['energia']['meses_observados'], 0)
                    self.assertIn(linha['energia']['origem'], ('observado_completo', 'anualizado_pro_rata'))
                if linha['producao']:
                    self.assertIn(linha['producao']['origem'], ('declarada_anual', 'anualizada_de_parciais'))
                    self.assertTrue(linha['producao']['registros'], 'produção sem os ids que a originaram')
                if not linha['energia'] or not linha['producao']:
                    self.assertIsNone(linha['coeficiente'])

    def test_anualizacao_da_energia_e_pro_rata_dos_meses_observados(self):
        for linha in PACOTE['linhas']:
            energia = linha['energia']
            if not energia:
                continue
            esperado = energia['mwh_observado'] * 12 / energia['meses_observados']
            self.assertAlmostEqual(energia['mwh_anualizado'], esperado, places=2)
            if energia['meses_observados'] == 12:
                self.assertEqual(energia['origem'], 'observado_completo')

    def test_energia_bate_com_a_tabela_ccee_do_panorama(self):
        coluna = {nome: i for i, nome in enumerate(PANORAMA['ccee']['cols'])}
        cnpjs = {linha['cnpj_raiz'] for linha in PACOTE['linhas']}
        agentes = {i: ce[0] for i, ce in enumerate(PANORAMA['dims']['ce']) if ce[0] in cnpjs}
        soma = {}
        for linha in PANORAMA['ccee']['rows']:
            agente = linha[coluna['empresa']]
            if agente in agentes:
                chave = (agentes[agente], linha[coluna['mes']] // 100)
                soma[chave] = soma.get(chave, 0.0) + linha[coluna['total_mwh']]
        conferidas = 0
        for linha in PACOTE['linhas']:
            if not linha['energia']:
                continue
            esperado = soma.get((linha['cnpj_raiz'], linha['ano']))
            self.assertIsNotNone(esperado, f"{linha['empresa']} {linha['ano']} não existe na CCEE")
            self.assertAlmostEqual(linha['energia']['mwh_observado'], esperado, places=2)
            conferidas += 1
        self.assertGreater(conferidas, 0)

    def test_producao_declarada_bate_com_a_base_de_producao(self):
        por_id = {r['id']: r for r in PRODUCAO['registros']}
        for linha in PACOTE['linhas']:
            producao = linha['producao']
            if not producao or producao['origem'] != 'declarada_anual':
                continue
            origem = por_id[producao['registros'][0]]
            self.assertEqual(producao['valor'], origem['valor'])
            self.assertEqual(producao['unidade'], origem['unidade'])
            self.assertEqual(origem['periodo'], str(linha['ano']))

    def test_periodos_parciais_nao_se_sobrepoem_ao_serem_anualizados(self):
        """Um S1 já contém Q1 e Q2: somar os três daria um ano e meio dentro de um ano."""
        anualizadas = 0
        for linha in PACOTE['linhas']:
            producao = linha['producao']
            if not producao or producao['origem'] != 'anualizada_de_parciais':
                continue
            anualizadas += 1
            cobertos = set()
            for periodo in producao['periodos']:
                meses = MESES[periodo.split('-', 1)[1]]
                self.assertFalse(meses & cobertos, f'{linha["empresa"]} {periodo} se sobrepõe a outro período')
                cobertos |= meses
            self.assertEqual(len(cobertos), producao['meses_cobertos'])
            self.assertLess(producao['meses_cobertos'], 12)
        self.assertGreater(anualizadas, 0, 'a base precisa exercitar a anualização')

    def test_producao_anualizada_e_a_soma_levada_a_doze_meses(self):
        for linha in PACOTE['linhas']:
            producao = linha['producao']
            if not producao or producao['origem'] != 'anualizada_de_parciais':
                continue
            esperado = producao['observado'] * 12 / producao['meses_cobertos']
            self.assertAlmostEqual(producao['valor'], esperado, places=2)

    def test_so_entra_producao_realizada_do_recorte_de_goias(self):
        """Embarque, venda, capacidade, meta e consolidado do Brasil não podem virar numerador de coeficiente."""
        por_id = {r['id']: r for r in PRODUCAO['registros']}
        for linha in PACOTE['linhas']:
            if not linha['producao']:
                continue
            for identificador in linha['producao']['registros']:
                origem = por_id[identificador]
                self.assertEqual(origem['escopo'], 'operacao_goias')
                self.assertEqual(origem['tipo_valor'], 'realizado')
                self.assertEqual(origem['nivel'], 'empresa')
                self.assertIn(origem['medida'],
                              {'minerio_rom', 'contido', 'metal_em_concentrado', 'produto_acabado'})

    def test_coeficiente_e_energia_sobre_producao_na_unidade_publicada(self):
        conferidos = 0
        for linha in PACOTE['linhas']:
            coeficiente = linha['coeficiente']
            if not coeficiente:
                continue
            esperado = linha['energia']['mwh_anualizado'] * 1000 / linha['producao']['valor']
            self.assertAlmostEqual(coeficiente['valor'], esperado, places=2)
            self.assertEqual(coeficiente['unidade'], 'kWh/' + linha['producao']['unidade'])
            conferidos += 1
        self.assertGreater(conferidos, 0)

    def test_carga_com_mais_de_um_mineral_nunca_sai_como_exclusiva(self):
        for linha in PACOTE['linhas']:
            coeficiente = linha['coeficiente']
            if not coeficiente:
                continue
            if len(coeficiente['minerais_na_carga']) > 1:
                self.assertFalse(coeficiente['energia_exclusiva'],
                                 f"{linha['empresa']}: energia de vários minerais não pode virar coeficiente exclusivo")
            else:
                self.assertEqual(coeficiente['energia_exclusiva'],
                                 coeficiente['minerais_na_carga'] == [linha['mineral']])

    def test_qualidade_do_coeficiente_e_a_do_lado_mais_fraco(self):
        escala = ['observado_completo', 'estimado_alto', 'estimado_medio', 'estimado_baixo']
        for linha in PACOTE['linhas']:
            coeficiente = linha['coeficiente']
            if not coeficiente:
                continue
            self.assertEqual(escala.index(coeficiente['qualidade']),
                             max(escala.index(linha['energia']['qualidade']),
                                 escala.index(self.qualidade(linha['producao']['meses_cobertos']))))

    @staticmethod
    def qualidade(meses):
        return ('observado_completo' if meses >= 12 else 'estimado_alto' if meses >= 9
                else 'estimado_medio' if meses >= 6 else 'estimado_baixo')

    def test_o_pacote_avisa_o_que_nao_mede(self):
        avisos = ' '.join(PACOTE['meta']['avisos'])
        for termo in ('Anualização', 'rateada', 'convertido'):
            self.assertIn(termo, avisos)

    def test_o_gerador_e_reprodutivel(self):
        with tempfile.TemporaryDirectory() as tmp:
            saida = Path(tmp) / 'empresas.json'
            resultado = subprocess.run(
                [sys.executable, str(ROOT / 'scripts' / 'build_empresas_base.py'), '--saida', str(saida)],
                capture_output=True, text=True)
            self.assertEqual(resultado.returncode, 0, resultado.stderr)
            gerado = json.loads(saida.read_text(encoding='utf-8'))
            self.assertEqual(gerado['linhas'], PACOTE['linhas'],
                             'o pacote versionado não bate com o que o gerador produz agora')


class AbaTests(unittest.TestCase):
    """A aba fica atrás de sessão, como o atlas e o panorama: ela nomeia empresas ao lado da carga de energia."""

    def test_o_endpoint_exige_leitor_autenticado(self):
        codigo = (ROOT / 'Squad 3' / 'backend' / 'empresas.py').read_text(encoding='utf-8')
        self.assertIn('Depends(reader)', codigo)
        self.assertIn("prefix='/api/empresas'", codigo)

    def test_o_pacote_nao_foi_para_a_pasta_publica(self):
        # public/ é servida pelo Nginx sem sessão; a carga por empresa não pode cair ali.
        self.assertFalse((PUBLIC / 'data' / 'empresas').exists())

    def test_a_aba_esta_na_barra_lateral_logo_abaixo_de_mercado(self):
        markup = (PUBLIC / 'painel.html').read_text(encoding='utf-8')
        botoes = re.findall(r'data-view="([a-z]+)"', markup)
        self.assertIn('empresas', botoes)
        self.assertEqual(botoes[botoes.index('mercado') + 1], 'empresas')
        self.assertIn('id="empresas-view"', markup)
        self.assertIn('/empresas.js', markup)

    def test_a_view_e_trocada_pelo_painel(self):
        codigo = (PUBLIC / 'painel.js').read_text(encoding='utf-8')
        self.assertIn("'empresas'", codigo)
        self.assertIn('window.showEmpresas', codigo)

    def test_todo_id_usado_pela_aba_existe_no_html(self):
        codigo = (PUBLIC / 'empresas.js').read_text(encoding='utf-8')
        markup = (PUBLIC / 'painel.html').read_text(encoding='utf-8')
        for identificador in sorted(set(re.findall(r"el\('([a-z0-9-]+)'\)", codigo))):
            self.assertIn(f'id="{identificador}"', markup, identificador)

    def test_todo_texto_vindo_dos_dados_passa_por_escape(self):
        """Nome de empresa, mineral e município entram em innerHTML; sem escape, viram injeção."""
        codigo = (PUBLIC / 'empresas.js').read_text(encoding='utf-8')
        campos_de_texto = ('l.empresa', 'l.mineral', 'l.grupo', 'l.municipios', 'p.produto', 'p.unidade',
                           'p.periodos', 'c.unidade', 'c.minerais_na_carga', 'e.municipios_ccee', 'nomeCurto(')
        cruas = []
        for trecho in re.findall(r'\$\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}', codigo):
            if any(campo in trecho for campo in campos_de_texto) and 'escape(' not in trecho:
                cruas.append(trecho.strip())
        self.assertEqual(cruas, [], f'texto de dado interpolado sem escape: {cruas}')

    def test_o_csv_exportado_cita_todo_campo(self):
        # Nome de empresa tem vírgula e ponto e vírgula; sem aspas, a planilha desloca as colunas.
        codigo = (PUBLIC / 'empresas.js').read_text(encoding='utf-8')
        self.assertIn('replace(/"/g,\'""\')', codigo)
        self.assertIn("join(';')", codigo)


if __name__ == '__main__':
    unittest.main()
