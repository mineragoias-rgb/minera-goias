"""A base de projetos e o catálogo de bases: nada inventado, cada projeto com evidência, cada base com origem e data."""
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / 'public'
CURADA = json.loads((ROOT / 'projetos' / 'base_curada.json').read_text(encoding='utf-8'))
PACOTE = json.loads((ROOT / 'data' / 'projetos' / 'projetos.json').read_text(encoding='utf-8'))
CATALOGO = json.loads((ROOT / 'data' / 'catalogo' / 'catalogo.json').read_text(encoding='utf-8'))
XLSX = ROOT / 'Squad 1' / 'entregas' / 'projetos_minerais_goias.xlsx'
MATURIDADES = ['OPERAÇÃO', 'EXPANSÃO', 'CONSTRUÇÃO', 'DEFINIDO', 'PROVÁVEL', 'POSSÍVEL', 'SINAL']


class ProjetosTests(unittest.TestCase):
    def test_maturidade_usa_exatamente_as_sete_categorias(self):
        for projeto in PACOTE['projetos']:
            self.assertIn(projeto['maturidade'], MATURIDADES, projeto['id'])

    def test_cada_projeto_tem_ao_menos_uma_evidencia_ligada_pelo_id(self):
        ligadas = {e['projeto_id'] for e in PACOTE['evidencias']}
        for projeto in PACOTE['projetos']:
            self.assertIn(projeto['id'], ligadas, f"{projeto['id']} sem evidência na aba NOTÍCIAS")

    def test_nenhuma_evidencia_e_orfa(self):
        ids = {p['id'] for p in PACOTE['projetos']}
        for evidencia in PACOTE['evidencias']:
            self.assertIn(evidencia['projeto_id'], ids, evidencia['id'])

    def test_ids_sao_unicos_e_seguem_o_padrao(self):
        ids = [p['id'] for p in PACOTE['projetos']]
        self.assertEqual(len(ids), len(set(ids)), 'ID de projeto repetido')
        for identificador in ids:
            self.assertRegex(identificador, r'^GO-\d{3}$')
        evidencias = [e['id'] for e in PACOTE['evidencias']]
        self.assertEqual(len(evidencias), len(set(evidencias)), 'ID de evidência repetido')

    def test_informacao_ausente_e_NA_e_nunca_vazio(self):
        """NA é declaração de que não foi encontrado. Célula vazia esconde a diferença entre ausente e zero."""
        for projeto in PACOTE['projetos']:
            for chave, valor in projeto.items():
                if isinstance(valor, str):
                    self.assertTrue(valor.strip(), f"{projeto['id']}: campo '{chave}' vazio; deveria ser NA")

    def test_capex_declarado_vem_com_moeda_e_ano(self):
        for projeto in PACOTE['projetos']:
            if projeto['capex'] != 'NA':
                self.assertNotEqual(projeto['moeda'], 'NA', f"{projeto['id']}: CAPEX sem moeda")
                self.assertNotEqual(projeto['ano_capex'], 'NA', f"{projeto['id']}: CAPEX sem ano")

    def test_capacidade_anunciada_vem_com_unidade(self):
        for projeto in PACOTE['projetos']:
            if projeto['capacidade'] != 'NA':
                self.assertNotEqual(projeto['cap_unidade'], 'NA', f"{projeto['id']}: capacidade sem unidade")

    def test_todo_projeto_tem_evidencia_principal_e_link(self):
        for projeto in PACOTE['projetos']:
            self.assertTrue(projeto['evidencia'].strip(), projeto['id'])
            self.assertTrue(projeto['link'].startswith('http'), projeto['id'])

    def test_todo_link_de_evidencia_e_http(self):
        for evidencia in PACOTE['evidencias']:
            self.assertTrue(evidencia['link'].startswith('http'), evidencia['id'])

    def test_projetos_de_confianca_baixa_estao_marcados_e_nao_escondidos(self):
        baixos = [p for p in PACOTE['projetos'] if p['confianca'] == 'BAIXO']
        self.assertTrue(baixos, 'a base mantém projetos de confiança baixa, e eles precisam ficar marcados')
        for projeto in baixos:
            self.assertNotEqual(projeto['obs'], 'NA',
                                f"{projeto['id']}: confiança BAIXA sem observação explicando por quê")

    def test_a_base_declara_a_limitacao_da_coleta(self):
        limitacao = PACOTE['meta']['limitacao_da_coleta']
        self.assertIn('não foi', limitacao.lower().replace('nenhum documento foi aberto', 'não foi'))
        self.assertTrue(any(i['item'] == 'Limitações da pesquisa' for i in PACOTE['meta']['metodologia']))

    def test_o_gerador_recusa_maturidade_fora_do_vocabulario(self):
        with tempfile.TemporaryDirectory() as tmp:
            quebrada = json.loads(json.dumps(CURADA))
            quebrada['projetos'][0]['maturidade'] = 'TALVEZ'
            repo = Path(tmp) / 'repo'
            (repo / 'projetos').mkdir(parents=True)
            (repo / 'projetos' / 'base_curada.json').write_text(json.dumps(quebrada), encoding='utf-8')
            resultado = subprocess.run(
                [sys.executable, str(ROOT / 'scripts' / 'build_projetos_base.py'), '--repo', str(repo),
                 '--xlsx', str(Path(tmp) / 'x.xlsx'), '--json', str(Path(tmp) / 'x.json')],
                capture_output=True, text=True)
            self.assertEqual(resultado.returncode, 1)
            self.assertIn('TALVEZ', resultado.stdout)

    def test_o_gerador_recusa_projeto_sem_evidencia(self):
        with tempfile.TemporaryDirectory() as tmp:
            quebrada = json.loads(json.dumps(CURADA))
            alvo = quebrada['projetos'][0]['id']
            quebrada['evidencias'] = [e for e in quebrada['evidencias'] if e['projeto_id'] != alvo]
            repo = Path(tmp) / 'repo'
            (repo / 'projetos').mkdir(parents=True)
            (repo / 'projetos' / 'base_curada.json').write_text(json.dumps(quebrada), encoding='utf-8')
            resultado = subprocess.run(
                [sys.executable, str(ROOT / 'scripts' / 'build_projetos_base.py'), '--repo', str(repo),
                 '--xlsx', str(Path(tmp) / 'x.xlsx'), '--json', str(Path(tmp) / 'x.json')],
                capture_output=True, text=True)
            self.assertEqual(resultado.returncode, 1)
            self.assertIn('nenhuma evidência', resultado.stdout)


class XlsxTests(unittest.TestCase):
    def setUp(self):
        from openpyxl import load_workbook
        self.wb = load_workbook(XLSX)

    def test_tem_as_tres_abas_pedidas(self):
        self.assertEqual(self.wb.sheetnames, ['PROJETOS', 'NOTÍCIAS', 'METODOLOGIA'])

    def test_cada_aba_abre_com_nome_origem_e_ultima_atualizacao(self):
        for nome in self.wb.sheetnames:
            ws = self.wb[nome]
            with self.subTest(aba=nome):
                self.assertTrue(str(ws.cell(1, 1).value or '').strip(), 'linha 1 sem o nome da base')
                subtitulo = str(ws.cell(2, 1).value or '')
                self.assertIn('Origem:', subtitulo)
                self.assertIn('Última atualização:', subtitulo)
                self.assertEqual(ws.freeze_panes, 'A4', 'cabeçalho precisa ficar fixo')

    def test_as_colunas_sao_as_31_e_as_16_pedidas(self):
        projetos = self.wb['PROJETOS']
        self.assertEqual(projetos.max_column, 31)
        self.assertEqual(projetos.cell(3, 1).value, 'ID')
        self.assertEqual(projetos.cell(3, 11).value, 'Maturidade')
        self.assertEqual(projetos.cell(3, 31).value, 'Observações')
        noticias = self.wb['NOTÍCIAS']
        self.assertEqual(noticias.max_column, 16)
        self.assertEqual(noticias.cell(3, 2).value, 'ID do projeto')

    def test_as_linhas_do_xlsx_batem_com_o_pacote(self):
        self.assertEqual(self.wb['PROJETOS'].max_row, 3 + len(PACOTE['projetos']))
        self.assertEqual(self.wb['NOTÍCIAS'].max_row, 3 + len(PACOTE['evidencias']))

    def test_a_metodologia_cobre_os_itens_pedidos(self):
        itens = {str(self.wb['METODOLOGIA'].cell(linha, 1).value)
                 for linha in range(4, self.wb['METODOLOGIA'].max_row + 1)}
        for esperado in ('Objetivo', 'Abrangência', 'Fontes', 'Critérios de inclusão', 'Critérios de exclusão',
                         'Critérios de maturidade', 'Regras de deduplicação', 'Regras de CAPEX',
                         'Regras de capacidade', 'Regras de previsão de entrada', 'Critérios de confiança',
                         'Significado de NA', 'Limitações da pesquisa'):
            self.assertIn(esperado, itens, esperado)


class CatalogoTests(unittest.TestCase):
    def test_toda_base_declara_nome_origem_e_data(self):
        """São os três campos do cabeçalho: sem um deles o catálogo não responde ao que existe para responder."""
        self.assertTrue(CATALOGO['bases'])
        for base in CATALOGO['bases']:
            with self.subTest(base=base.get('id')):
                self.assertTrue(base['nome'].strip())
                self.assertTrue(base['origem'].strip())
                self.assertTrue(base['atualizado_em'])
                self.assertNotEqual(base['atualizado_em'], 'NA', 'base sem data de atualização')
                self.assertRegex(base['atualizado_em'], r'^\d{4}-\d{2}(-\d{2})?$')

    def test_natureza_e_familia_estao_no_vocabulario(self):
        for base in CATALOGO['bases']:
            self.assertIn(base['natureza'], {'bruta', 'derivada', 'curada', 'coletada'}, base['id'])
            self.assertTrue(base['familia'].strip())

    def test_o_catalogo_cobre_as_bases_que_o_painel_serve(self):
        ids = {b['id'] for b in CATALOGO['bases']}
        for esperado in ('ccee', 'cfem', 'amb', 'atlas', 'panorama', 'producao', 'empresas', 'projetos'):
            self.assertIn(esperado, ids, f'base {esperado} fora do catálogo')

    def test_os_readmes_citados_existem(self):
        for base in CATALOGO['bases']:
            if base.get('readme'):
                self.assertTrue((ROOT / base['readme']).is_file(), base['readme'])

    def test_o_catalogo_bate_com_os_pacotes_que_descreve(self):
        por_id = {b['id']: b for b in CATALOGO['bases']}
        self.assertIn(str(len(PACOTE['projetos'])), por_id['projetos']['volume'])
        producao = json.loads((ROOT / 'data' / 'producao' / 'producao.json').read_text(encoding='utf-8'))
        self.assertIn(str(len(producao['registros'])), por_id['producao']['volume'])


class AbaTests(unittest.TestCase):
    def test_a_aba_esta_na_barra_lateral_e_a_view_e_trocada(self):
        markup = (PUBLIC / 'painel.html').read_text(encoding='utf-8')
        botoes = re.findall(r'data-view="([a-z]+)"', markup)
        self.assertIn('bases', botoes)
        self.assertEqual(botoes[botoes.index('radar') + 1], 'bases')
        self.assertIn('id="bases-view"', markup)
        self.assertIn('/bases.js', markup)
        codigo = (PUBLIC / 'painel.js').read_text(encoding='utf-8')
        self.assertIn("'bases'", codigo)
        self.assertIn('window.showBases', codigo)

    def test_o_endpoint_exige_leitor_autenticado(self):
        codigo = (ROOT / 'Squad 3' / 'backend' / 'catalogo.py').read_text(encoding='utf-8')
        self.assertIn('Depends(reader)', codigo)
        self.assertIn("prefix='/api/catalogo'", codigo)
        self.assertFalse((PUBLIC / 'data' / 'catalogo').exists(), 'o catálogo não vai para a pasta pública')

    def test_todo_id_usado_pela_aba_existe_no_html(self):
        codigo = (PUBLIC / 'bases.js').read_text(encoding='utf-8')
        markup = (PUBLIC / 'painel.html').read_text(encoding='utf-8')
        for identificador in sorted(set(re.findall(r"el\('([a-z0-9-]+)'\)", codigo))):
            self.assertIn(f'id="{identificador}"', markup, identificador)

    def test_o_cabecalho_do_cartao_desfaz_a_altura_global_de_header(self):
        """style.css tem `header{height:94px}` para a barra do site. O cabeçalho do cartão é um <header> e herdava
        essa altura, com o conteúdo transbordando sobre o corpo quando o nome quebrava em três linhas."""
        css = (PUBLIC / 'style.css').read_text(encoding='utf-8')
        regra = [linha for linha in css.splitlines() if linha.startswith('.bd-head{')]
        self.assertTrue(regra, 'regra .bd-head não encontrada')
        self.assertIn('height:auto', regra[0])

    def test_todo_texto_vindo_do_catalogo_passa_por_escape(self):
        codigo = (PUBLIC / 'bases.js').read_text(encoding='utf-8')
        campos = ('b.nome', 'b.origem', 'b.familia', 'b.onde', 'b.mede', 'b.atualizado_em', 'b.readme',
                  'rotuloNatureza(', 'tomNatureza(')
        cruas = [trecho.strip() for trecho in re.findall(r'\$\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}', codigo)
                 if any(c in trecho for c in campos) and 'escape(' not in trecho]
        self.assertEqual(cruas, [], f'texto do catálogo interpolado sem escape: {cruas}')


if __name__ == '__main__':
    unittest.main()
