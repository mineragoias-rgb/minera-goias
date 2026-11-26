"""Atlas Empresarial: identidade por CNPJ raiz, contagens sem dupla contagem, vínculos auditáveis e endpoint protegido.

    python -m unittest discover -s tests -p test_atlas_empresas.py -v
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
PACOTE = json.loads((ROOT / 'data' / 'empresas' / 'atlas_empresas.json').read_text(encoding='utf-8'))
PANORAMA = json.loads((ROOT / 'data' / 'panorama' / 'panorama.json').read_text(encoding='utf-8'))
CURADORIA = json.loads((ROOT / 'data' / 'empresas' / 'curadoria_atlas.json').read_text(encoding='utf-8'))
COL = {c: i for i, c in enumerate(PACOTE['processos']['cols'])}
ROWS = PACOTE['processos']['rows']
EMP = {e['i']: e for e in PACOTE['empresas']}
POR_CNPJ = {e['cnpj']: e for e in PACOTE['empresas']}


class IdentidadeTests(unittest.TestCase):
    def test_uma_empresa_por_cnpj_raiz_e_todas_pessoa_juridica(self):
        cnpjs = [e['cnpj'] for e in PACOTE['empresas']]
        self.assertEqual(len(cnpjs), len(set(cnpjs)), 'CNPJ raiz repetido no índice')
        dims = PANORAMA['dims']['emp']
        for e in PACOTE['empresas']:
            self.assertRegex(e['cnpj'], r'^\d{8}$')
            self.assertEqual(dims[e['i']][3], 'pj', e['nome'])
            self.assertEqual(dims[e['i']][2], e['cnpj'])
            self.assertEqual(e['id'], 'COM_CNPJ_' + e['cnpj'])

    def test_pessoa_fisica_nao_e_nomeada(self):
        ocultos = {i for i, d in enumerate(PANORAMA['dims']['emp']) if d[3] != 'pj'}
        self.assertFalse(ocultos & set(EMP), 'pessoa física entrou no índice')
        for r in ROWS:
            self.assertTrue(r[COL['empresa']] >= 0 or r[COL['empresa']] in (-1, -2))
        texto = json.dumps(PACOTE, ensure_ascii=False)
        self.assertNotRegex(texto, r'\d{3}\.\d{3}\.\d{3}-\d{2}', 'CPF no pacote')

    def test_as_dez_empresas_da_base_de_producao_estao_enriquecidas(self):
        producao = json.loads((ROOT / 'data' / 'producao' / 'producao.json').read_text(encoding='utf-8'))
        cnpjs = {r['cnpj_raiz'] for r in producao['registros']}
        self.assertEqual(len(cnpjs), 10)
        for c in cnpjs:
            self.assertIn(c, POR_CNPJ)
            self.assertEqual(POR_CNPJ[c]['enr'], 1)
            self.assertIn(str(POR_CNPJ[c]['i']), PACOTE['detalhes'])


class ContagemTests(unittest.TestCase):
    def test_cada_processo_aparece_uma_vez_e_bate_com_o_panorama(self):
        ids = [r[COL['processo']] for r in ROWS]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(ids), len(PANORAMA['proc']['rows']))

    def test_processos_por_empresa_somam_os_processos_pj_sem_dupla_contagem(self):
        por = Counter(r[COL['empresa']] for r in ROWS if r[COL['empresa']] >= 0)
        for i, n in por.items():
            self.assertEqual(EMP[i]['n'], n, EMP[i]['nome'])
            self.assertEqual(sum(EMP[i]['grupos'].values()), n)
        self.assertEqual(sum(por.values()), PACOTE['meta']['cobertura']['processos_pj'])

    def test_cfem_por_empresa_bate_com_a_cfem_do_panorama(self):
        cols = {c: i for i, c in enumerate(PANORAMA['cfem']['cols'])}
        esperado = Counter()
        for r in PANORAMA['cfem']['rows']:
            if r[cols['emp']] in EMP:
                esperado[(r[cols['emp']], str(r[cols['ano']]))] += r[cols['valor']]
        for (i, ano), v in esperado.items():
            self.assertAlmostEqual(EMP[i]['cfem'].get(ano, 0), v, delta=0.05 * 3, msg=f'{EMP[i]["nome"]} {ano}')

    def test_carga_ccee_bate_com_o_pacote_de_empresas_onde_os_dois_existem(self):
        empresas = json.loads((ROOT / 'data' / 'empresas' / 'empresas.json').read_text(encoding='utf-8'))
        conferidas = 0
        for l in empresas['linhas']:
            e = l['energia']
            if not e:
                continue
            c = POR_CNPJ[l['cnpj_raiz']]['ccee'][str(l['ano'])]
            self.assertAlmostEqual(c['obs'], e['mwh_empresa_observado'], places=1)
            self.assertEqual(c['meses'], e['meses_observados'])
            conferidas += 1
        self.assertGreater(conferidas, 10)

    def test_cfem_por_processo_e_ano_nao_passa_do_total_do_processo(self):
        cpa = PACOTE['cfem_processo_ano']
        self.assertTrue(cpa, 'CSV corrigido da CFEM ausente: CFEM por processo-ano não foi gerada')
        perto = 0
        for r in ROWS:
            anos = cpa.get(r[COL['processo']])
            if not anos or not r[COL['cfem_2022_2026']]:
                continue
            soma = sum(anos.values())
            if abs(soma - r[COL['cfem_2022_2026']]) <= max(1.0, 0.01 * r[COL['cfem_2022_2026']]):
                perto += 1
        # As duas pontas vêm da mesma ANM por caminhos diferentes (aba 03 do Squad 1 × CSV corrigido): a maioria tem de bater.
        com_os_dois = sum(1 for r in ROWS if cpa.get(r[COL['processo']]) and r[COL['cfem_2022_2026']])
        self.assertGreater(perto / com_os_dois, 0.9, f'{perto}/{com_os_dois}')


class FaseTests(unittest.TestCase):
    def test_grupo_juridico_da_fase_segue_o_radar(self):
        grupos = {f['nome']: f['grupo'] for f in PACOTE['dims']['fase']}
        for f in ('CONCESSÃO DE LAVRA', 'LAVRA GARIMPEIRA', 'LICENCIAMENTO', 'REGISTRO DE EXTRAÇÃO'):
            self.assertEqual(grupos[f], 'lavra_autorizada')
        self.assertEqual(grupos['AUTORIZAÇÃO DE PESQUISA'], 'pesquisa')
        self.assertEqual(grupos['REQUERIMENTO DE LAVRA'], 'requerimento_lavra')
        self.assertEqual(grupos['DISPONIBILIDADE'], 'disponibilidade')

    def test_titulo_nao_e_chamado_de_mina_ativa(self):
        js = (ROOT / 'public' / 'empresas-atlas.js').read_text(encoding='utf-8')
        i18n = (ROOT / 'public' / 'i18n.js').read_text(encoding='utf-8')
        self.assertIn('não comprova operação', i18n)
        bloco = i18n.split('/* atlas-empresas:pt */')[1].split('/* fim atlas-empresas */')[0]
        # 'Minas ativas' só aparece como nome da camada do SGB, entre aspas, nunca como rótulo de título ANM
        for linha in bloco.splitlines():
            if re.search(r'mina[s]? ativa', linha, re.I):
                self.assertIn('"Minas ativas"', linha.replace('“', '"').replace('”', '"'), linha)
        self.assertIn('lavra_autorizada', js)

    def test_centroide_dentro_de_goias(self):
        for r in ROWS:
            self.assertIsNotNone(r[COL['lat']], r[COL['processo']])
            self.assertTrue(-19.6 < r[COL['lat']] < -12.3 and -53.4 < r[COL['lon']] < -45.8, r[COL['processo']])


class VinculoTests(unittest.TestCase):
    def test_todo_projeto_vinculado_diz_metodo_e_confianca(self):
        for p in PACOTE['projetos']:
            self.assertIn(p['metodo'], ('processo_anm', 'curadoria_cnpj', 'sem_vinculo_verificado'))
            if p['e']:
                self.assertIn(p['conf'], ('alta', 'media'), p['id'])
                for i in p['e']:
                    self.assertIn(i, EMP)
            else:
                self.assertEqual(p['metodo'], 'sem_vinculo_verificado')

    def test_projeto_do_radar_so_se_liga_por_processo_do_proprio_titular(self):
        por_id = {r[COL['processo']]: r[COL['empresa']] for r in ROWS}
        for p in PACOTE['projetos']:
            if p['metodo'] != 'processo_anm':
                continue
            titulares = {por_id[x] for x in p['processos'] if x in por_id and por_id[x] >= 0}
            self.assertTrue(set(p['e']) <= titulares, p['id'])

    def test_curadoria_de_projetos_aponta_para_cnpj_existente(self):
        for nome, v in CURADORIA['projetos_cnpj'].items():
            if nome.startswith('_'):
                continue
            self.assertIn(v['cnpj_raiz'], POR_CNPJ, nome)

    def test_toda_noticia_tem_titulo_data_veiculo_link_metodo_e_confianca(self):
        self.assertTrue(PACOTE['noticias'])
        for n in PACOTE['noticias']:
            self.assertRegex(n['d'], r'^\d{4}-\d{2}-\d{2}$')
            self.assertTrue(n['t'] and n['u'].startswith('http') and n['v'])
            self.assertIn(n['metodo'], ('alias_entidade', 'alias_grupo'))
            self.assertIn(n['conf'], ('alta', 'media'))
            self.assertIn(n['tipo'], ('empresa', 'indireta'))

    def test_todo_link_do_pacote_e_http_ou_https(self):
        # Os links vêm de coleta automática (notícias) e de bases de terceiros; a tela os põe em <a href>. Só http(s) entra.
        achados = []

        def andar(x, chave=''):
            if isinstance(x, dict):
                for k, v in x.items():
                    andar(v, k)
            elif isinstance(x, list):
                for v in x:
                    andar(v, chave)
            elif isinstance(x, str) and re.match(r'^\s*[A-Za-z][A-Za-z0-9+.-]*:', x) and not re.match(r'^\d', x):
                if chave in ('u', 'url', 'link', 'fonte_url', 'fonte') or '//' in x or x.strip().lower().startswith(('javascript:', 'data:', 'vbscript:')):
                    achados.append(x)
        andar(PACOTE)
        andar(CURADORIA)
        self.assertTrue(achados)
        ruins = [u for u in achados if not re.match(r'^https?://', u)]
        self.assertFalse(ruins, ruins[:5])
        js = (ROOT / 'public' / 'empresas-atlas.js').read_text(encoding='utf-8')
        self.assertFalse(re.findall(r'href="\$\{escape\((?!urlSegura\()', js), 'link sem urlSegura() em empresas-atlas.js')

    def test_mosaic_nao_recebe_noticia_de_minas_gerais_sem_goias(self):
        mosaic = POR_CNPJ['33931486']['i']
        for n in PACOTE['noticias']:
            if n['e'] != mosaic:
                continue
            titulo = n['t'].lower()
            self.assertTrue(n['go'] or 'catalão' in titulo or 'catalao' in titulo, n['t'])
        titulos = [n['t'] for n in PACOTE['noticias'] if n['e'] == mosaic]
        self.assertFalse(any('Saskatchewan' in t or 'Rainbow' in t for t in titulos))

    def test_ex_funcionarios_da_serra_verde_nao_viram_evento_da_empresa(self):
        sv = POR_CNPJ['08842895']['i']
        for n in PACOTE['noticias']:
            if n['e'] == sv and re.search(r'ex-gerente|ex-funcion|próximo de mina', n['t'], re.I):
                self.assertEqual(n['tipo'], 'indireta', n['t'])

    def test_nome_de_grupo_exige_contexto_de_goias(self):
        for n in PACOTE['noticias']:
            if n['metodo'] != 'alias_grupo':
                continue
            regra = CURADORIA['noticias']['empresas'][EMP[n['e']]['cnpj']]
            titulo = re.sub(r'\s[-–]\s[^-–]{2,60}$', '', n['t'])
            norm = lambda s: __import__('unicodedata').normalize('NFKD', s).encode('ascii', 'ignore').decode().lower()
            ctx = [norm(c) for c in regra['contexto'] + CURADORIA['noticias']['contexto_go_geral']]
            self.assertTrue(any(c in norm(titulo) for c in ctx), n['t'])

    def test_aliases_ambiguos_conhecidos_nao_sao_usados(self):
        for cnpj, r in CURADORIA['noticias']['empresas'].items():
            self.assertNotIn('Lundin', r['grupo'], 'casaria Lundin Gold')
            self.assertNotIn('USAR', r['grupo'], "casaria o verbo 'usar'")


class CriticosTests(unittest.TestCase):
    def test_federal_e_estadual_separados_com_norma_e_link(self):
        c = PACOTE['criticos']
        self.assertIn('Resolução nº 2', c['federal']['norma'])
        self.assertIn('23.597', c['estadual']['norma'])
        for esfera in ('federal', 'estadual'):
            self.assertTrue(c[esfera]['link'].startswith('https://'))
            self.assertTrue(c[esfera]['categorias'])
        ids = lambda e: {cat['id'] for cat in c[e]['categorias']}
        self.assertFalse(ids('federal') & ids('estadual'))

    def test_niobio_e_estrategico_federal_e_critico_estadual(self):
        nb = [i for i, m in enumerate(PACOTE['dims']['min']) if m[0] == 'Nióbio'][0]
        em = lambda e: any(nb in it['min'] for cat in PACOTE['criticos'][e]['categorias'] for it in cat['itens'])
        self.assertTrue(em('federal') and em('estadual'))
        au = [i for i, m in enumerate(PACOTE['dims']['min']) if m[0] == 'Ouro'][0]
        self.assertFalse(any(au in it['min'] for cat in PACOTE['criticos']['estadual']['categorias'] for it in cat['itens']),
                         'ouro não está no art. 3º da Lei 23.597/2025')


class MetaTests(unittest.TestCase):
    def test_regras_de_top_n_e_puxadores_declaradas(self):
        r = PACOTE['meta']['regras']
        self.assertIn('80%', r['puxadores'])
        self.assertIn('universo', r['top_n'])

    def test_o_gerador_e_idempotente(self):
        with tempfile.TemporaryDirectory() as tmp:
            saida = Path(tmp) / 'a.json'
            subprocess.run([sys.executable, str(ROOT / 'scripts' / 'build_atlas_empresas.py'), '--saida', str(saida)],
                           check=True, capture_output=True)
            novo = json.loads(saida.read_text(encoding='utf-8'))
        novo['meta'].pop('built_on'); atual = dict(PACOTE); atual['meta'] = dict(PACOTE['meta']); atual['meta'].pop('built_on')
        self.assertEqual(novo, atual, 'pacote desatualizado: rode python scripts/build_atlas_empresas.py')


class ApiTests(unittest.TestCase):
    def setUp(self):
        sys.path.insert(0, str(ROOT / 'Squad 3' / 'backend'))
        import auth
        import main
        from fastapi.testclient import TestClient
        self.tmp = tempfile.TemporaryDirectory()
        self.env = patch.dict(os.environ, {'AUTH_DB_PATH': self.tmp.name + '/auth.sqlite', 'COOKIE_SECURE': '1'})
        self.env.start()
        with auth.database() as c:
            c.execute('INSERT INTO users(username,name,password_hash,role,must_change) VALUES (?,?,?,?,0)',
                      ('leitor', 'leitor', auth.password_hash('long-test-password'), 'user'))
            c.execute('INSERT INTO users(username,name,password_hash,role,must_change) VALUES (?,?,?,?,1)',
                      ('novo', 'novo', auth.password_hash('long-test-password'), 'user'))
        self.client = TestClient(main.app, base_url='https://testserver')

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def test_endpoint_exige_sessao_e_senha_trocada(self):
        self.assertEqual(self.client.get('/api/empresas/atlas').status_code, 401)
        self.client.post('/api/auth/login', json={'username': 'novo', 'password': 'long-test-password'})
        self.assertEqual(self.client.get('/api/empresas/atlas').status_code, 403)

    def test_leitor_recebe_o_pacote_comprimido(self):
        self.assertEqual(self.client.post('/api/auth/login', json={'username': 'leitor', 'password': 'long-test-password'}).status_code, 200)
        r = self.client.get('/api/empresas/atlas', headers={'Accept-Encoding': 'gzip'})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()['meta']['gerado_por'], 'scripts/build_atlas_empresas.py')
        self.assertEqual(r.headers.get('content-encoding'), 'gzip')

    def test_pacote_fora_da_pasta_publica(self):
        self.assertFalse(list((ROOT / 'public').rglob('atlas_empresas*.json')))
        self.assertFalse(list((ROOT / 'public').rglob('curadoria_atlas*.json')))


class InterfaceTests(unittest.TestCase):
    def test_painel_carrega_o_atlas_depois_da_aba_empresas(self):
        html = (ROOT / 'public' / 'painel.html').read_text(encoding='utf-8')
        self.assertLess(html.index('/empresas.js'), html.index('/empresas-atlas.js'))
        self.assertIn('id="empresas-content"', html, 'o painel de produção e energia continua na aba')
        for id_ in ('ea-busca', 'ea-map', 'ea-lista', 'ea-ficha', 'ea-cmp', 'ea-metodo', 'ea-exp-csv', 'ea-exp-json'):
            self.assertIn(f'id="{id_}"', html)

    def test_estilos_novos_ficam_na_aba_empresas(self):
        css = (ROOT / 'public' / 'empresas-atlas.css').read_text(encoding='utf-8')
        regras = re.findall(r'(^|})\s*([^{}@]+){', re.sub(r'/\*.*?\*/', '', css, flags=re.S))
        for _, seletor in regras:
            for s in seletor.split(','):
                s = s.strip()
                if not s or s.startswith(('from', 'to', '0%', '100%')):
                    continue
                self.assertTrue(s.startswith(('#empresas-view', '#ea-', '.leaflet-popup .ea-pop')), s)

    def test_sintaxe_do_javascript(self):
        subprocess.run(['node', '--check', str(ROOT / 'public' / 'empresas-atlas.js')], check=True)
        subprocess.run(['node', '--check', str(ROOT / 'public' / 'empresas.js')], check=True)


if __name__ == '__main__':
    unittest.main()
