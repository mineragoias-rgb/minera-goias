"""A aba de comércio exterior publica despacho aduaneiro. O risco não é o número errado — é o número certo lido como produção."""
import json
import re
import subprocess
import sys
import tempfile
import unicodedata
import unittest
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / 'public'
PACOTE = json.loads((ROOT / 'data' / 'comex' / 'comex.json').read_text(encoding='utf-8'))
CURADA = json.loads((ROOT / 'comex' / 'base_curada.json').read_text(encoding='utf-8'))
MERCADO = json.loads((PUBLIC / 'data' / 'mercado' / 'mercado_v1.json').read_text(encoding='utf-8'))
PRODUCAO = json.loads((ROOT / 'data' / 'producao' / 'producao.json').read_text(encoding='utf-8'))
PROJETOS = json.loads((ROOT / 'data' / 'projetos' / 'projetos.json').read_text(encoding='utf-8'))
POR_MINERAL = {m['mineral']: m for m in PACOTE['minerais']}


def dobra(texto):
    return ''.join(c for c in unicodedata.normalize('NFD', str(texto).lower())
                   if unicodedata.category(c) != 'Mn')


class PacoteTests(unittest.TestCase):
    def test_o_pacote_tem_as_quatro_leituras_e_nenhuma_esta_vazia(self):
        for secao in ('minerais', 'serie', 'anual', 'destinos', 'municipios'):
            self.assertTrue(PACOTE[secao], secao)

    def test_toda_ncm_curada_aparece_no_pacote_e_nenhuma_sobra(self):
        """Se a curadoria e a fonte descolarem, um mineral some da base sem ninguém perceber."""
        curadas = {n['codigo'] for m in CURADA['minerais'] for n in m['ncms']}
        publicadas = {n['codigo'] for m in PACOTE['minerais'] for n in m['ncms']}
        self.assertEqual(curadas, publicadas)
        for m in PACOTE['minerais']:
            for n in m['ncms']:
                self.assertNotEqual(n['descricao_oficial'], 'NA',
                                    f"NCM {n['codigo']} sem a descrição que a própria fonte dá")

    def test_cada_ncm_pertence_a_um_mineral_so(self):
        dono = {}
        for m in PACOTE['minerais']:
            for n in m['ncms']:
                self.assertNotIn(n['codigo'], dono,
                                 f"NCM {n['codigo']} em {m['mineral']} e em {dono.get(n['codigo'])}")
                dono[n['codigo']] = m['mineral']

    def test_o_recorte_critico_so_vale_enquanto_o_marco_estadual_nomear_o_mineral(self):
        """Chamar um mineral de crítico é uma afirmação; ela tem de continuar presa à aba Mercado, que é a fonte citada."""
        texto = dobra(json.dumps(MERCADO['operacoes'], ensure_ascii=False))
        criticos = [m for m in PACOTE['minerais'] if m['criticidade'] == 'marco_estadual']
        self.assertTrue(criticos)
        for m in criticos:
            self.assertTrue(m['termo_no_mercado'], f"{m['mineral']} é crítico sem dizer por qual termo")
            self.assertIn(dobra(m['termo_no_mercado']), texto, m['mineral'])

    def test_a_base_nao_atribui_classificacao_federal_que_nao_leu(self):
        self.assertEqual(PACOTE['meta']['criticidade']['classificacao_federal'], 'NA')
        self.assertIn('nao pode ser lido', dobra(PACOTE['meta']['criticidade']['por_que_na']))
        for m in PACOTE['minerais']:
            self.assertIn(m['criticidade'], CURADA['criticidade']['classes'])

    def test_mineral_do_vocabulario_do_projeto_existe_nas_outras_bases(self):
        vocabulario = {r['mineral'] for r in PRODUCAO['registros'] if r.get('mineral')}
        vocabulario |= {p['mineral'] for p in PROJETOS['projetos'] if p.get('mineral')}
        vocabulario |= {p['outros'] for p in PROJETOS['projetos'] if p.get('outros') not in (None, 'NA')}
        for m in PACOTE['minerais']:
            if m['no_vocabulario_do_projeto']:
                self.assertIn(m['mineral'], vocabulario, m['mineral'])
            else:
                self.assertNotIn(m['mineral'], vocabulario, m['mineral'])

    def test_a_soma_dos_meses_e_o_total_do_ano(self):
        mensal = defaultdict(int)
        for l in PACOTE['serie']:
            mensal[(l['mineral'], l['fluxo'], l['ano'])] += l['usd_fob']
        for l in PACOTE['anual']:
            self.assertEqual(mensal[(l['mineral'], l['fluxo'], l['ano'])], l['usd_fob'],
                             f"{l['mineral']} {l['fluxo']} {l['ano']}")

    def test_os_destinos_somam_a_exportacao_do_ano(self):
        """Pedir um período que cruza anos faz a API devolver só o acumulado até o mês final, calada.

        Conferido na coleta: NCM 26030010 em 2024 volta com US$ 378,6 mi num período 2019-01→2026-10 e com
        US$ 500,3 mi quando 2024 é pedido sozinho — a diferença é exatamente novembro e dezembro. Este teste é o
        que impede essa armadilha de voltar pela porta dos fundos numa recoleta futura.
        """
        exportado = {(l['mineral'], l['ano']): l['usd_fob'] for l in PACOTE['anual'] if l['fluxo'] == 'export'}
        destino = defaultdict(int)
        for d in PACOTE['destinos']:
            destino[(d['mineral'], d['ano'])] += d['usd_fob']
        for chave, soma in destino.items():
            self.assertEqual(soma, exportado.get(chave), f'{chave}: destinos não fecham com a exportação do ano')

    def test_a_participacao_do_destino_soma_um_em_cada_mineral_e_ano(self):
        parcelas = defaultdict(float)
        for d in PACOTE['destinos']:
            parcelas[(d['mineral'], d['ano'])] += d['participacao']
        for chave, total in parcelas.items():
            self.assertAlmostEqual(total, 1.0, places=4, msg=str(chave))

    def test_so_o_ano_que_a_fonte_ja_fechou_e_marcado_como_completo(self):
        ano, mes = PACOTE['meta']['publicado_ate']['ano'], PACOTE['meta']['publicado_ate']['mes']
        for l in PACOTE['anual']:
            esperado = l['ano'] < ano or (l['ano'] == ano and mes == 12)
            self.assertEqual(l['ano_completo'], esperado, f"{l['mineral']} {l['ano']}")
            self.assertLessEqual(l['meses_com_embarque'], l['meses_publicados'])
            if not l['ano_completo']:
                self.assertEqual(l['meses_publicados'], mes)

    def test_o_preco_implicito_so_existe_quando_ha_peso(self):
        for l in PACOTE['anual']:
            if l['kg']:
                self.assertAlmostEqual(l['usd_por_kg'], l['usd_fob'] / l['kg'], places=3)
            else:
                self.assertIsNone(l['usd_por_kg'])

    def test_nenhum_valor_e_negativo(self):
        for secao in ('serie', 'anual', 'destinos', 'municipios'):
            for l in PACOTE[secao]:
                self.assertGreaterEqual(l['usd_fob'], 0, f'{secao}: {l}')
                self.assertGreaterEqual(l['kg'], 0, f'{secao}: {l}')

    def test_fertilizante_nao_entra_como_minerio(self):
        """Goiás importa cloreto de potássio e fosfato de amônio em volume maior que todo o seu comércio mineral.

        Somar o capítulo 31 ao minério leria indústria química como mineração — e enterraria o nióbio num número de adubo.
        """
        for m in PACOTE['minerais']:
            for n in m['ncms']:
                self.assertIn(int(n['capitulo']), CURADA['regras']['capitulos_aceitos'], n['codigo'])
                self.assertNotEqual(n['capitulo'], '31')

    def test_o_que_a_curadoria_excluiu_continua_fora(self):
        """Platina, ródio, sucata e 'minérios de outros metais preciosos' não são lavra de Goiás."""
        codigos = {n['codigo'] for m in PACOTE['minerais'] for n in m['ncms']}
        for excluida in ('26169000', '71101910', '71102900', '71103100', '74040000', '28433010', '28433090'):
            self.assertNotIn(excluida, codigos, excluida)
        self.assertTrue(CURADA['regras']['o_que_fica_de_fora'])

    def test_a_granularidade_do_municipio_e_o_capitulo_e_a_base_diz_isso(self):
        capitulos = {m['capitulo'] for m in PACOTE['municipios']}
        self.assertTrue(capitulos)
        for m in PACOTE['municipios']:
            self.assertNotEqual(m['capitulo_nome'], 'NA', m['capitulo'])
            self.assertNotIn(' - GO', m['municipio'])
        aviso = ' '.join(PACOTE['meta']['avisos'])
        self.assertIn('capítulo', aviso)

    def test_o_pacote_avisa_que_despacho_nao_e_producao(self):
        texto = dobra(' '.join(PACOTE['meta']['o_que_a_base_nao_mede']))
        for assunto in ('producao', 'teor', 'consumo', 'mercado interno'):
            self.assertIn(assunto, texto, assunto)

    def test_o_gerador_e_reprodutivel(self):
        with tempfile.TemporaryDirectory() as tmp:
            saida = Path(tmp) / 'comex.json'
            resultado = subprocess.run(
                [sys.executable, str(ROOT / 'scripts' / 'build_comex_base.py'), '--saida', str(saida)],
                capture_output=True, text=True)
            self.assertEqual(resultado.returncode, 0, resultado.stderr)
            gerado = json.loads(saida.read_text(encoding='utf-8'))
            for secao in ('minerais', 'serie', 'anual', 'destinos', 'municipios'):
                self.assertEqual(gerado[secao], PACOTE[secao], secao)

    def test_o_csv_acompanha_a_serie(self):
        linhas = (ROOT / 'data' / 'comex' / 'comex.csv').read_text(encoding='utf-8-sig').strip().splitlines()
        self.assertEqual(len(linhas) - 1, len(PACOTE['serie']))
        self.assertTrue(linhas[0].startswith('mineral;criticidade;fluxo;ano;mes;'))


class ColetaTests(unittest.TestCase):
    def test_a_coleta_registra_ate_quando_a_fonte_publicou(self):
        coleta = PACOTE['meta']['coleta']
        self.assertEqual(coleta['publicado_ate'], PACOTE['meta']['publicado_ate'])
        self.assertTrue(coleta['baixado_em'])
        self.assertTrue(coleta['atualizacao_declarada_pela_api'])
        self.assertEqual(coleta['uf_comexstat'], 53)

    def test_o_coletor_pede_um_ano_por_vez_e_nunca_usa_bloco_economico(self):
        codigo = (ROOT / 'comex' / 'coleta.py').read_text(encoding='utf-8')
        self.assertIn('for ano in range(ANO_INICIAL, ano_fim + 1)', codigo)
        self.assertNotIn('economicBlock', codigo.split('"""', 2)[2],
                         'economicBlock repete o mesmo embarque em cada bloco e dobra a soma')

    def test_o_coletor_so_usa_a_biblioteca_padrao(self):
        """Ele roda por cron numa máquina enxuta, como o agente de produção: instalar dependência é o que o quebra."""
        codigo = (ROOT / 'comex' / 'coleta.py').read_text(encoding='utf-8')
        importados = set(re.findall(r'^(?:import|from)\s+([a-zA-Z_][\w.]*)', codigo, re.M))
        self.assertTrue(importados <= {'argparse', 'json', 'sys', 'time', 'urllib.error', 'urllib.request',
                                       'datetime', 'pathlib'}, importados)


class AbaTests(unittest.TestCase):
    """A aba cruza o Comex Stat com o vocabulário e as operações do projeto: fica atrás de sessão, como as outras."""

    def test_o_endpoint_exige_leitor_autenticado(self):
        codigo = (ROOT / 'Squad 3' / 'backend' / 'comex.py').read_text(encoding='utf-8')
        self.assertIn('Depends(reader)', codigo)
        self.assertIn("prefix='/api/comex'", codigo)
        principal = (ROOT / 'Squad 3' / 'backend' / 'main.py').read_text(encoding='utf-8')
        self.assertIn('app.include_router(comex_router)', principal)

    def test_o_pacote_nao_foi_para_a_pasta_publica(self):
        self.assertFalse((PUBLIC / 'data' / 'comex').exists())

    def test_a_aba_esta_na_barra_lateral_logo_abaixo_de_empresas(self):
        markup = (PUBLIC / 'painel.html').read_text(encoding='utf-8')
        botoes = re.findall(r'data-view="([a-z]+)"', markup)
        self.assertEqual(botoes[botoes.index('empresas') + 1], 'comex')
        self.assertIn('id="comex-view"', markup)
        self.assertIn('/comex.js', markup)

    def test_a_view_e_trocada_pelo_painel(self):
        codigo = (PUBLIC / 'painel.js').read_text(encoding='utf-8')
        self.assertIn("'comex'", codigo)
        self.assertIn('window.showComex', codigo)

    def test_todo_id_usado_pela_aba_existe_no_html(self):
        codigo = (PUBLIC / 'comex.js').read_text(encoding='utf-8')
        markup = (PUBLIC / 'painel.html').read_text(encoding='utf-8')
        for identificador in sorted(set(re.findall(r"el\('([a-z0-9-]+)'\)", codigo))):
            self.assertIn(f'id="{identificador}"', markup, identificador)

    def test_todo_texto_vindo_dos_dados_passa_por_escape(self):
        """Mineral, país, município e as notas da fonte entram em innerHTML; sem escape, viram injeção."""
        codigo = (PUBLIC / 'comex.js').read_text(encoding='utf-8')
        campos = ('l.mineral', 'i.rotulo', 'i.texto', 'i.nota', 'm.operacoes_em_goias', 'n.codigo',
                  'meta.criticidade', 'd.pais', 'm.municipio')
        cruas = [t.strip() for t in re.findall(r'\$\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}', codigo)
                 if any(c in t for c in campos) and 'escape(' not in t]
        self.assertEqual(cruas, [], f'texto de dado interpolado sem escape: {cruas}')

    def test_a_aba_mostra_na_tela_o_que_a_base_nao_mede(self):
        codigo = (PUBLIC / 'comex.js').read_text(encoding='utf-8')
        for trecho in ('o_que_a_base_nao_mede', 'avisos', 'recorte_do_projeto', 'por_que_na', 'o_que_fica_de_fora'):
            self.assertIn(trecho, codigo, trecho)

    def test_a_aba_marca_o_ano_que_ainda_nao_fechou(self):
        codigo = (PUBLIC / 'comex.js').read_text(encoding='utf-8')
        self.assertIn('ano_completo', codigo)
        self.assertIn('cx.anoParcial', codigo)

    def test_o_csv_exportado_cita_todo_campo(self):
        codigo = (PUBLIC / 'comex.js').read_text(encoding='utf-8')
        self.assertIn('replace(/"/g,\'""\')', codigo)
        self.assertIn("join(';')", codigo)

    def test_a_aba_tem_bloco_proprio_de_estilo(self):
        css = (PUBLIC / 'style.css').read_text(encoding='utf-8')
        self.assertIn('--- Comércio exterior ---', css)
        # A coluna de valor nasce com 44px no estilo global: "US$ 3,97 bi" não cabe e quebra a linha.
        self.assertIn('#cx-minerais .bar-row', css)


if __name__ == '__main__':
    unittest.main()
