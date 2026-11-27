"""Atlas Empresarial: identidade por CNPJ raiz, contagens sem dupla contagem, vínculos auditáveis e endpoint protegido.

    python -m unittest discover -s tests -p test_atlas_empresas.py -v
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import unicodedata
import unittest
from collections import Counter
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
PACOTE = json.loads((ROOT / 'data' / 'empresas' / 'atlas_empresas.json').read_text(encoding='utf-8'))
PANORAMA = json.loads((ROOT / 'data' / 'panorama' / 'panorama.json').read_text(encoding='utf-8'))
CURADORIA = json.loads((ROOT / 'data' / 'empresas' / 'curadoria_atlas.json').read_text(encoding='utf-8'))
COL = {c: i for i, c in enumerate(PACOTE['processos']['cols'])}
sem_acento = lambda t: ''.join(c for c in unicodedata.normalize('NFD', str(t)) if unicodedata.category(c) != 'Mn').upper()
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
            prov = json.loads((Path(tmp) / 'a_proveniencia.json').read_text(encoding='utf-8'))
        novo['meta'].pop('built_on'); atual = dict(PACOTE); atual['meta'] = dict(PACOTE['meta']); atual['meta'].pop('built_on')
        self.assertEqual(novo, atual, 'pacote desatualizado: rode python scripts/build_atlas_empresas.py')
        self.assertEqual(prov, json.loads((ROOT / 'data' / 'empresas' / 'atlas_empresas_proveniencia.json').read_text(encoding='utf-8')))


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
        self.assertEqual(r.json()['meta']['versao'], 'v2')
        self.assertNotIn('gerado_por', r.json()['meta'])   # rastreamento técnico fica fora do pacote servido
        self.assertEqual(r.headers.get('content-encoding'), 'gzip')

    def test_pacote_fora_da_pasta_publica(self):
        self.assertFalse(list((ROOT / 'public').rglob('atlas_empresas*.json')))
        self.assertFalse(list((ROOT / 'public').rglob('curadoria_atlas*.json')))


class InterfaceTests(unittest.TestCase):
    def test_painel_carrega_o_atlas_depois_da_aba_empresas(self):
        html = (ROOT / 'public' / 'painel.html').read_text(encoding='utf-8')
        self.assertLess(html.index('/empresas.js'), html.index('/empresas-atlas.js'))
        self.assertIn('id="empresas-content"', html, 'a análise de produção declarada e energia continua na aba')
        for id_ in ('ea-busca', 'ea-sel', 'ea-map', 'ea-modos', 'ea-lista', 'ea-resumo', 'ea-ficha', 'ea-kpis', 'ea-cmp', 'ea-cmp-busca',
                    'ea-escopo', 'ea-anal-nav', 'es-indisp', 'ep-indisp', 'ea-metodo', 'ea-exp-csv', 'ea-exp-json'):
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


class ConsolidacaoTests(unittest.TestCase):
    """Aba Empresas consolidada (26/11/2026): mapa único em três modos, análises recuperadas, sem duplicação nem retorno silencioso."""

    @classmethod
    def setUpClass(cls):
        cls.html = (ROOT / 'public' / 'painel.html').read_text(encoding='utf-8')
        cls.js = (ROOT / 'public' / 'empresas-atlas.js').read_text(encoding='utf-8')
        cls.analises = (ROOT / 'public' / 'empresas.js').read_text(encoding='utf-8')
        cls.base = json.loads((ROOT / 'data' / 'empresas' / 'empresas.json').read_text(encoding='utf-8'))
        i = cls.html.index('<section id="empresas-view"')
        cls.secao = cls.html[i:cls.html.index('</section>', cls.html.index('id="ea-metodo-corpo"'))]

    def area(self, nome):
        a = self.secao.index(f'id="ea-area-{nome}"')
        seguintes = [self.secao.index(f'id="ea-area-{x}"') for x in ('explorar', 'dossie', 'analises', 'comparar') if self.secao.index(f'id="ea-area-{x}"') > a]
        return self.secao[a:min(seguintes) if seguintes else self.secao.index('id="ea-metodo"')]

    # ----------------------------------------------------------- mapa: ponto por empresa e localização de projetos
    def test_ponto_da_empresa_segue_a_regra_do_mapa_de_empresas(self):
        lavra = {k for k, f in enumerate(PACOTE['dims']['fase']) if f['grupo'] == 'lavra_autorizada'}
        por_emp = {}
        for k, r in enumerate(ROWS):
            if r[COL['empresa']] >= 0 and r[COL['lat']] is not None:
                por_emp.setdefault(r[COL['empresa']], []).append(k)
        for e in PACOTE['empresas']:
            ks = por_emp.get(e['i'], [])
            if not ks:
                self.assertEqual(e['pt'], -1, e['nome'])
                continue
            self.assertIn(e['pt'], ks, e['nome'])   # o ponto é um processo da própria empresa
            chave = lambda k: (ROWS[k][COL['cfem_2022_2026']] or 0, ROWS[k][COL['fase']] in lavra, round(ROWS[k][COL['area_ha']] or 0, 1))
            self.assertEqual(chave(e['pt']), max(chave(k) for k in ks), e['nome'])
        self.assertEqual(PACOTE['meta']['cobertura']['empresas_com_ponto'], sum(1 for e in PACOTE['empresas'] if e['pt'] >= 0))
        self.assertIn('não a sede nem a mina', PACOTE['meta']['regras']['ponto_empresa'])

    def test_ponto_igual_ao_do_mapa_de_empresas_anterior(self):
        """Regressão contra data/empresas/mapa_empresas.json (legado de bb87b53): o mesmo processo de referência por empresa."""
        arq = ROOT / 'data' / 'empresas' / 'mapa_empresas.json'
        if not arq.exists():
            self.skipTest('sem o pacote legado do mapa de empresas')
        m = json.loads(arq.read_text(encoding='utf-8'))
        proc_antigo = {}
        for r in m['processos']['rows']:
            proc_antigo.setdefault((r[0], r[1], r[2]), r[8])
        iguais = total = 0
        for x in m['empresas']:
            if x['lat'] is None:
                continue
            total += 1
            e = POR_CNPJ[x['cnpj_raiz']]
            iguais += ROWS[e['pt']][COL['processo']] == proc_antigo.get((x['i'], x['lat'], x['lon']))
        self.assertEqual(total, sum(1 for e in PACOTE['empresas'] if e['pt'] >= 0))
        # um caso de dois títulos com o mesmo centroide antigo (média dos vértices) é aceito
        self.assertGreaterEqual(iguais, total - 2, f'{iguais} de {total}')
        self.assertAlmostEqual(sum(x['cfem_total'] for x in m['empresas']), PACOTE['meta']['cobertura']['cfem_pj_2022_2026'], delta=1.0)
        self.assertEqual(len(m['empresas']), PACOTE['meta']['cobertura']['empresas_indice'])

    def test_projeto_so_tem_a_localizacao_que_a_fonte_sustenta(self):
        mun_nome = {sem_acento(m[1]) for m in PACOTE['dims']['mun']}
        contagem = {'p': 0, 'm': 0, 'sem': 0}
        for p in PACOTE['projetos']:
            loc = p.get('loc')
            if loc and loc['t'] == 'p':
                citados = set(p.get('processos') or [])
                for k in loc['k']:
                    self.assertIn(ROWS[k][COL['processo']], citados, p['nome'])
                    self.assertIsNotNone(ROWS[k][COL['lat']])
                areas = [ROWS[k][COL['area_ha']] or 0 for k in loc['k']]
                self.assertEqual(areas, sorted(areas, reverse=True), p['nome'])   # o primeiro (desenhado) é o maior
            elif loc:
                self.assertEqual(loc['t'], 'm')
                self.assertTrue(loc['m'] and all(0 <= i < len(PACOTE['dims']['mun']) for i in loc['m']), p['nome'])
            else:
                # sem localização: nenhum processo citado com centroide e nenhum município de Goiás reconhecido
                self.assertFalse(any(ROWS[k][COL['lat']] is not None for k in range(len(ROWS)) if ROWS[k][COL['processo']] in set(p.get('processos') or [])), p['nome'])
                partes = re.split(r'\s*(?:[,/;]|\be\b)\s*', p.get('mun') or '')
                self.assertFalse(any(sem_acento(x.strip()) in mun_nome for x in partes if x.strip()), p['nome'])
            contagem[loc['t'] if loc else 'sem'] += 1
        self.assertEqual(contagem, {k: PACOTE['meta']['cobertura']['projetos_localizacao'].get(k, 0) for k in contagem})

    def test_mapa_unico_em_tres_modos(self):
        self.assertEqual(self.html.count('id="ea-map"'), 1)
        for modo in ('empresas', 'processos', 'projetos'):
            self.assertIn(f'data-modo="{modo}"', self.secao)
        for f in ('pintarEmpresas', 'pintarProcessos', 'pintarProjetos', 'definirModo'):
            self.assertIn(f'function {f}(', self.js)
        self.assertNotIn('empresas-mapa.js', self.html)
        self.assertNotIn('empresas-mapa.css', self.html)
        # nenhum símbolo é apresentado como localização exata de mina (aviso fixo na legenda do mapa)
        self.assertTrue("t('ea.leg.semMina')" in self.js or 'data-i18n="ea.leg.semMina"' in self.secao)

    # ----------------------------------------------------------- estrutura: quatro áreas, sem painéis duplicados
    def test_quatro_areas_com_navegacao_acessivel(self):
        for a in ('explorar', 'dossie', 'analises', 'comparar'):
            self.assertIn(f'id="ea-area-{a}"', self.secao)
            self.assertIn(f'id="ea-nav-{a}"', self.secao)
            self.assertIn(f'aria-controls="ea-area-{a}"', self.secao)
        self.assertIn('role="tablist"', self.secao)
        self.assertIn('id="ea-busca"', self.secao)   # busca fora das áreas: visível em todas

    def test_sem_painel_de_producao_e_energia_duplicado(self):
        """O painel de produção declarada e energia existe uma vez, dentro de Análises; o dossiê só resume e leva até ele."""
        ids = ['ep-metrics', 'ep-energia', 'ep-coef', 'ep-tabela', 'ep-serie', 'ep-cobertura', 'empresas-content',
               'es-metrics', 'es-barras', 'es-cobertura', 'es-energia', 'es-coef', 'es-tabela', 'es-publicado', 'es-ref', 'epn-body']
        analises, dossie, explorar = self.area('analises'), self.area('dossie'), self.area('explorar')
        for id_ in ids:
            self.assertEqual(self.html.count(f'id="{id_}"'), 1, id_)
            self.assertIn(f'id="{id_}"', analises, id_)
        for area in (dossie, explorar):
            self.assertNotRegex(area, r'id="(ep|es|epn)-', 'painel de análise fora da área Análises')
        self.assertNotIn('ea-divisor', self.html)
        # o resumo do dossiê não redesenha os gráficos da análise: lê as mesmas linhas e oferece "aprofundar"
        eco = self.js[self.js.index('function economia('):self.js.index('function projetos(')]
        for desenho in ("el('ep-", "el('es-", 'barrasEnergia', 'barrasCoeficiente', 'estTabela'):
            self.assertNotIn(desenho, eco)
        self.assertIn('data-anal=', eco)

    def test_analises_nao_voltam_silenciosamente_para_todas_as_empresas(self):
        """Empresa fora das 10 com produção declarada: aviso "Dados não disponíveis", nada do agregado no DOM (defeito de fc8c2ad)."""
        r = subprocess.run(['node', str(ROOT / 'tests' / 'js' / 'analises_escopo.js')], capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(r.returncode, 0, r.stderr)
        d = json.loads(r.stdout)
        fora = d['fora']
        self.assertTrue(fora['declarada']['indisp'])
        self.assertFalse(fora['declarada']['conteudo'])
        self.assertEqual(fora['declarada']['tabela'], '', 'a tabela de todas as empresas ficou na página')
        self.assertIn('ea.indisp.titulo', fora['declarada']['indispHtml'])
        self.assertIn('resumo 00057240', fora['declarada']['indispHtml'], 'o aviso mostra o que a base tem da empresa')
        self.assertEqual(fora['cnpjsEstimada'], ['00057240'], 'a estimativa mostrou outra empresa')
        self.assertFalse(fora['estimada']['buscaVisivel'])
        dentro = d['dentro']
        self.assertEqual(dentro['linhasDeclaradas'], dentro['linhasDeclaradasEsperadas'])
        self.assertEqual(dentro['cnpjsEstimada'], ['26108898'])
        sem = d['semDado']
        self.assertTrue(sem['declarada']['indisp'] and sem['estimada']['indisp'])
        self.assertEqual((sem['declarada']['tabela'], sem['estimada']['tabela']), ('', ''))
        self.assertEqual(d['devolta']['linhasDeclaradas'], d['totalDeclaradas'], 'pedir "todas as empresas" mostra as 10 de novo')
        # e a sincronização antiga (que limpava o filtro) não existe mais
        self.assertNotIn('empresasSelecionar', self.analises + self.js)
        self.assertNotIn("el('ep-emp').value=''", self.analises)

    # ----------------------------------------------------------- produção estimada recuperada
    def test_producao_estimada_preservada_sem_dado_pessoal(self):
        est = self.base['estimada']
        self.assertEqual(est['colunas'][:6], ['ano', 'mineral', 'base', 'empresa', 'cnpj_raiz', 'producao_t'])
        self.assertGreater(len(est['linhas']), 2000)
        c = {k: i for i, k in enumerate(est['colunas'])}
        cpf = re.compile(r'\d{3}\.?\d{3}\.?\d{3}-\d{2}')
        for r in est['linhas']:
            if not r[c['cnpj_raiz']]:
                self.assertEqual(r[c['empresa']], 'pessoa física (nome não publicado)')
            self.assertIsNone(cpf.search(r[c['empresa']]))
            self.assertIn(r[c['base']], ('ROM', 'beneficiada', 'conteudo_mineral'))
        self.assertIn('Anuário Mineral', est['metodo'])
        for f in ('estMetricas', 'estBarras', 'estCobertura', 'estEnergia', 'estCoef', 'estReferencias', 'estTabela', 'estPublicado', 'estExportar'):
            self.assertIn(f'function {f}(', self.analises)

    def test_cfem_da_estimativa_nao_dobra_com_todas_as_bases(self):
        """Correção documentada: ROM e beneficiada repetem a CFEM; soma-se uma base por empresa, mineral e ano."""
        est = self.base['estimada']
        c = {k: i for i, k in enumerate(est['colunas'])}
        ordem = ['beneficiada', 'conteudo_mineral', 'ROM']
        chave = lambda r: (r[c['ano']], r[c['mineral']], r[c['cnpj_raiz']] or r[c['empresa']])
        base = {}
        for r in est['linhas']:
            k = chave(r)
            if k not in base or ordem.index(r[c['base']]) < ordem.index(base[k]):
                base[k] = r[c['base']]
        unica = sum(r[c['cfem_brl']] or 0 for r in est['linhas'] if r[c['base']] == base[chave(r)] and not r[c['minerio_de_outro_mineral']])
        ingenua = sum(r[c['cfem_brl']] or 0 for r in est['linhas'] if not r[c['minerio_de_outro_mineral']])
        self.assertGreater(ingenua, 1.8 * unica)
        self.assertIn('function cfemUnica(', self.analises)
        self.assertIn('somaMapa(cfemUnica(proprias))', self.analises)
        self.assertIn('naBasePreferida(proprias)', self.analises)

    # ----------------------------------------------------------- arrecadação, títulos e consumo (panorama.js)
    def test_arrecadacao_titulos_e_consumo_filtram_pela_empresa_exata(self):
        pn = (ROOT / 'public' / 'panorama.js').read_text(encoding='utf-8')
        self.assertIn("P.dims.emp[i][2]===F.raiz", pn)
        self.assertIn("P.dims.ce[r[3]][0]===F.raiz", pn)
        self.assertIn("escopo:'empresasPanoramaEscopo'", pn)
        for aba in ('emp_arrec', 'emp_titulos', 'emp_consumo'):
            self.assertIn(f"['{aba}'", pn)
        # a chave de ligação existe: CNPJ raiz único por titular PJ nomeado e na carga CCEE
        raizes = [e[2] for e in PANORAMA['dims']['emp'] if e[3] == 'pj' and e[1]]
        self.assertEqual(len(raizes), len(set(raizes)))
        self.assertTrue(all(len(c[0]) == 8 for c in PANORAMA['dims']['ce']))
        self.assertIn('id="epn-tabs"', self.secao)

    def test_dossie_e_comparacao_leem_a_mesma_fonte_das_analises(self):
        self.assertIn('estimadaDe:', self.analises)
        self.assertIn('declaradaDe:', self.analises)
        self.assertIn('A.estimadaDe(', self.js)
        self.assertIn('A.declaradaDe(', self.js)
        cmp_ = self.js[self.js.index('function linhasComparacao('):self.js.index('function comparar(')]
        self.assertIn('(t)', cmp_)   # produção estimada sempre em t, por mineral e base
        self.assertNotIn('somar', cmp_)


class RefinamentoUxTests(unittest.TestCase):
    """Refinamento de UX (26/11/2026): Explorar em lateral + mapa, filtros recolhidos, cartão da seleção, ranking sob demanda,
    dossiê com cabeçalho de relatório, análises em três níveis e comparação em vagas — sem perder função."""

    @classmethod
    def setUpClass(cls):
        cls.html = (ROOT / 'public' / 'painel.html').read_text(encoding='utf-8')
        cls.js = (ROOT / 'public' / 'empresas-atlas.js').read_text(encoding='utf-8')
        cls.analises = (ROOT / 'public' / 'empresas.js').read_text(encoding='utf-8')
        cls.css = (ROOT / 'public' / 'empresas-atlas.css').read_text(encoding='utf-8')
        cls.panorama = (ROOT / 'public' / 'panorama.js').read_text(encoding='utf-8')
        i = cls.html.index('<section id="empresas-view"')
        cls.secao = cls.html[i:cls.html.index('<section id="radar-view"')]

    def bloco(self, id_):
        """HTML do elemento com esse id até o fechamento correspondente (contando as tags de mesmo nome)."""
        i = self.secao.index(f'id="{id_}"')
        ini = self.secao.rindex('<', 0, i)
        tag = re.match(r'<(\w+)', self.secao[ini:]).group(1)
        prof = 0
        for m in re.finditer(rf'<(/?){tag}\b', self.secao[ini:]):
            prof += 1 if m.group(1) == '' else -1
            if prof == 0:
                return self.secao[ini:ini + m.end()]
        raise AssertionError(f'{id_} sem fechamento')

    def test_explorar_tem_lateral_e_mapa_lado_a_lado(self):
        lateral = self.bloco('ea-lateral')
        for id_ in ('ea-busca-lat', 'ea-filtros-btn', 'ea-filtros', 'ea-lista', 'ea-metrica', 'ea-exp-csv', 'ea-exp-json', 'ea-ranking-btn'):
            self.assertIn(f'id="{id_}"', lateral)
        self.assertIn('.ea-explorar-corpo{display:grid;grid-template-columns:minmax(300px,27%) minmax(0,1fr)', self.css)
        self.assertEqual(self.secao.count('id="ea-busca"'), 1, 'uma busca só, que muda de lugar (lateral ou alto da aba)')
        self.assertIn('function posicionarBusca(', self.js)

    def test_filtros_recolhidos_e_removiveis(self):
        self.assertIn('id="ea-filtros" hidden', self.secao)
        self.assertIn('aria-controls="ea-filtros"', self.secao)
        self.assertIn('data-limpa=', self.js)   # etiqueta de filtro ativo que remove o filtro
        filtros = self.bloco('ea-filtros')
        for id_ in ('ea-mun', 'ea-min', 'ea-grupo', 'ea-dado', 'ea-ano-ini', 'ea-ano-fim'):
            self.assertIn(f'id="{id_}"', filtros)

    def test_ranking_integrado_a_lista_sem_lista_duplicada(self):
        self.assertEqual(self.secao.count('class="ea-lista"'), 1)
        self.assertNotIn('id="ea-top"', self.secao)
        opcoes = self.js[self.js.index("preencher(el('ea-metrica')"):][:200]
        for ordem in ('cfem', 'relevancia', 'processos', 'area', 'ccee', 'nome'):
            self.assertIn(f"'{ordem}'", opcoes)
        self.assertIn('function maisLista(', self.js)
        # ranking completo e Pareto: visualização própria, fechada até ser pedida
        self.assertIn('id="ea-ranking" aria-labelledby="ea-rk-titulo" hidden', self.secao)
        self.assertIn('function ranking(', self.js)
        self.assertIn('ea-p80', self.js)

    def test_cartao_da_selecao_sobre_o_mapa(self):
        painel = self.secao[self.secao.index('class="ea-map-panel"'):self.secao.index('id="ea-ranking"')]
        self.assertIn('id="ea-resumo"', painel)
        corpo = self.js[self.js.index('function resumoSel('):self.js.index('function resumoAlternativo(')]
        self.assertIn("mostrarArea('dossie')", corpo)
        self.assertIn('limparSelecao()', corpo)
        self.assertIn('dadosDisponiveis(e)', corpo)
        self.assertNotIn('ea-chip-sel', self.js)   # a etiqueta antiga sobre o mapa foi absorvida pelo cartão

    def test_dossie_com_cabecalho_de_relatorio(self):
        ficha = self.bloco('ea-ficha')
        for id_ in ('ea-ficha-titulo', 'ea-ficha-sub', 'ea-ficha-fatos', 'ea-kpis', 'ea-ficha-dados', 'ea-abas', 'ea-corpo'):
            self.assertIn(f'id="{id_}"', ficha)
        # <header> tem estilo global no painel (altura fixa e flex): a aba não usa esse elemento
        self.assertNotIn('<header', self.secao)

    def test_analises_em_tres_niveis(self):
        for pfx, conteudo in (('es', 'es-content'), ('ep', 'empresas-content')):
            bloco = self.bloco(conteudo)
            self.assertIn(f'id="{pfx}-sintese"', bloco)
            self.assertIn(f'id="{pfx}-metrics"', bloco)
            det = self.bloco(f'{pfx}-detalhe')
            for d in ('tabela', 'metodo'):
                self.assertIn(f'data-det="{d}"', det)
            # nota metodológica, fontes e tabela extensa ficam no detalhamento, fora da primeira dobra
            for id_ in (f'{pfx}-nota', f'{pfx}-fontes', f'{pfx}-tabela'):
                self.assertIn(f'id="{id_}"', det)
            # só a aba da tabela começa aberta
            self.assertEqual(det.count('data-det-painel=') - 1, det.count('role="tabpanel" hidden>'))
        self.assertIn('function estSintese(', self.analises)
        self.assertIn('function sinteseDeclarada(', self.analises)

    def test_comparacao_em_vagas_com_destaque_do_maior(self):
        self.assertIn('id="ea-cmp-slots"', self.secao)
        self.assertIn("' ea-max'", self.js)
        self.assertIn('id="ea-cmp-busca"', self.secao)

    def test_celular_e_tablet_reorganizam_em_gaveta(self):
        self.assertIn('@media(max-width:1000px)', self.css)
        self.assertIn('#empresas-view .ea-lateral{position:fixed', self.css)
        self.assertIn('id="ea-lista-btn"', self.secao)
        self.assertIn('function gaveta(', self.js)
        self.assertIn('visibility:hidden', self.css)   # gaveta fechada sai da ordem do Tab

    def test_panorama_da_aba_mexe_so_na_propria_barra_de_filtros(self):
        self.assertIn("el('pn-reset').closest('.pn-filters')", self.panorama)


NSX = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'


def ler_xlsx(caminho):
    """Lê um .xlsx sem biblioteca: {aba: [linha como dict]}, com o tipo de cada célula (str, float, bool) e o XML bruto de cada aba."""
    import zipfile
    import xml.etree.ElementTree as ET
    z = zipfile.ZipFile(caminho)
    rels = {r.get('Id'): r.get('Target') for r in ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))}
    abas, brutos = {}, {}
    for s in ET.fromstring(z.read('xl/workbook.xml')).find(NSX + 'sheets'):
        alvo = 'xl/' + rels[s.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')]
        brutos[s.get('name')] = z.read(alvo).decode('utf-8')
        linhas = []
        for row in ET.fromstring(z.read(alvo)).find(NSX + 'sheetData'):
            vals = {}
            for c in row:
                col, t = re.match(r'[A-Z]+', c.get('r')).group(0), c.get('t')
                if t == 'inlineStr':
                    vals[col] = (''.join(x.text or '' for x in c.iter(NSX + 't')), c.get('s'))
                elif t == 'b':
                    vals[col] = (c.find(NSX + 'v').text == '1', None)
                else:
                    vals[col] = (float(c.find(NSX + 'v').text), None)
            linhas.append(vals)
        cab = {k: v[0] for k, v in linhas[0].items()} if linhas else {}
        abas[s.get('name')] = [{cab[k]: r[k] for k in r} for r in linhas[1:]]
    return abas, brutos, z


class ExportacaoTests(unittest.TestCase):
    """Auditoria final (26/11/2026): exportações tipadas — CSV para o Excel brasileiro (cabeçalho na 1ª linha, decimal vírgula, fórmula
    neutralizada) e .xlsx (números como números, CNPJ como texto, nunca fórmula) — e a chave de comparabilidade da produção declarada.
    Os arquivos são gravados pelo módulo real (public/empresas-exportar.js) no Node e lidos aqui."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        r = subprocess.run(['node', str(ROOT / 'tests' / 'js' / 'exportacao.js'), cls.tmp.name], capture_output=True, text=True, encoding='utf-8')
        if r.returncode:
            raise AssertionError(r.stderr)
        cls.r = json.loads(r.stdout)
        cls.csv_bytes = (Path(cls.tmp.name) / 'teste.csv').read_bytes()
        cls.abas, cls.xml, cls.zip = ler_xlsx(Path(cls.tmp.name) / 'teste.xlsx')

    @classmethod
    def tearDownClass(cls):
        cls.zip.close()
        cls.tmp.cleanup()

    def linhas_csv(self):
        import csv
        import io
        return list(csv.DictReader(io.StringIO(self.csv_bytes.decode('utf-8-sig'), newline=''), delimiter=';'))

    def test_csv_tem_bom_e_o_cabecalho_na_primeira_linha(self):
        self.assertTrue(self.csv_bytes.startswith(b'\xef\xbb\xbf'))
        self.assertEqual(self.csv_bytes.decode('utf-8-sig').split('\r\n')[0], 'cnpj_raiz;empresa;valor;lat;n;ok;periodo')
        self.assertNotIn(b'\r\n#', self.csv_bytes)

    def test_csv_decimal_virgula_vazio_e_texto_com_quebra_de_linha(self):
        ls = self.linhas_csv()
        self.assertEqual(len(ls), 10)
        self.assertEqual((ls[0]['valor'], ls[0]['lat'], ls[0]['n']), ('12,345', '-16,1234', '7'))
        self.assertEqual(ls[0]['empresa'], 'Mineração “Ação” — São Luís; linha\nnova')
        self.assertEqual((ls[1]['valor'], ls[1]['lat'], ls[1]['n']), ('', '', ''), 'sem dado sai vazio, nunca zero')
        self.assertEqual(ls[2]['valor'], '1234567,891234')
        self.assertEqual(ls[2]['n'], '0', 'zero de verdade continua zero')
        self.assertEqual(ls[0]['cnpj_raiz'], '08842895')

    def test_csv_neutraliza_formula_e_nao_mexe_em_numero(self):
        for l in self.linhas_csv()[3:]:
            self.assertTrue(l['empresa'].startswith("'"), l['empresa'])
            self.assertTrue(l['periodo'].startswith("'"), l['periodo'])
            self.assertRegex(l['valor'], r'^-\d+,5$')
        self.assertEqual(self.r['celulas']['negativo'], '-16,1234')
        self.assertEqual(self.r['celulas']['formula'], '"\'=1+1"')

    def test_xlsx_numeros_como_numero_e_cnpj_como_texto(self):
        self.assertEqual(list(self.abas), ['Dados', 'Colunas', 'Metadados'])
        d = self.abas['Dados']
        self.assertEqual(d[0]['cnpj_raiz'], ('08842895', '2'))       # texto, com o formato @
        self.assertEqual(d[1]['cnpj_raiz'], ('00057240', '2'))
        self.assertEqual(d[0]['valor'][0], 12.345)
        self.assertEqual(d[0]['lat'][0], -16.1234)
        self.assertIs(d[0]['ok'][0], True)
        self.assertNotIn('valor', d[1], 'sem dado = célula vazia')
        self.assertEqual(d[0]['empresa'][0], 'Mineração “Ação” — São Luís; linha\nnova')

    def test_xlsx_nunca_tem_formula(self):
        d = self.abas['Dados']
        self.assertEqual([l['empresa'][0] for l in d[3:]], ['=1+1', '+SOMA(A1:A2)', '-2+3', '@cmd', '\t=1', '\r=1', '=HYPERLINK("http://exemplo.invalid","x")'])
        for nome, xml in self.xml.items():
            self.assertNotIn('<f>', xml, nome)
            self.assertNotIn('<f ', xml, nome)

    def test_xlsx_e_um_zip_valido_com_filtro_e_metadados(self):
        self.assertIsNone(self.zip.testzip())
        tipos = self.zip.read('[Content_Types].xml').decode('utf-8')
        self.assertEqual(tipos.count('worksheet+xml'), 3)
        self.assertIn('<autoFilter ref="A1:G11"/>', self.xml['Dados'])
        self.assertIn('state="frozen"', self.xml['Dados'])
        meta = {l['item'][0]: l['valor'][0] for l in self.abas['Metadados']}
        self.assertEqual(meta, {'gerado_em': '2026-11-26', 'filtro': '{"mineral":"Fosfato"}'})
        self.assertEqual(self.r['crc'], 0xCBF43926)

    def test_maior_da_linha_so_entre_valores_comparaveis(self):
        m = self.r['maiusculo']
        self.assertEqual(m['mesmosMeses'], 1)
        self.assertEqual(m['mesesDiferentes'], -1, 'CCEE com 8 e 9 meses não tem "maior"')
        self.assertEqual(m['umValor'], -1)
        self.assertEqual(m['empate'], -1)

    def test_producao_declarada_so_junta_registros_com_a_mesma_chave(self):
        tudo = self.r['todas']
        self.assertEqual(tudo['entrada'], tudo['nosGrupos'], 'nenhum registro é descartado')
        self.assertTrue(tudo['camposIguais'])
        chaves = lambda par: {g['chave']: g for g in self.r[par]}
        ma = chaves('maracaAmarillo')
        # Ouro 2025 em oz: Chapada consolidado global realizado × Mara Rosa guidance em Goiás — nunca na mesma linha
        self.assertEqual(ma['2025|Ouro|ouro em concentrado|metal_em_concentrado|oz|consolidado_global|realizado|empresa']['n'], [1, 0])
        self.assertEqual(ma['2025|Ouro|ouro|metal_em_concentrado|oz|operacao_goias|guidance|empresa']['n'], [0, 1])
        self.assertFalse([g for g in self.r['maracaAmarillo'] if g['empresas'] > 1])
        cm = chaves('cmocMosaic')
        # Fosfato 2023 em t: fertilizantes fosfatados (CMOC) × rocha fosfática (Mosaic)
        self.assertEqual(cm['2023|Fosfato|fertilizantes fosfatados|produto_acabado|t|consolidado_brasil|realizado|empresa']['n'], [1, 0])
        self.assertEqual(cm['2023|Fosfato|rocha fosfática|produto_acabado|t|consolidado_brasil|realizado|empresa']['n'], [0, 1])


class AuditoriaConsultoriaTests(unittest.TestCase):
    """Auditoria final: comparação sem conclusões erradas, exportação igual à tela, limite de três sem troca silenciosa, limites de tela
    com acesso ao resto e Voltar/Avançar pela URL. O comportamento é conferido no navegador (tests/e2e_atlas_empresas.py, seção 19)."""

    @classmethod
    def setUpClass(cls):
        cls.html = (ROOT / 'public' / 'painel.html').read_text(encoding='utf-8')
        cls.js = (ROOT / 'public' / 'empresas-atlas.js').read_text(encoding='utf-8')
        cls.css = (ROOT / 'public' / 'empresas-atlas.css').read_text(encoding='utf-8')
        cls.secao = cls.html[cls.html.index('<section id="empresas-view"'):cls.html.index('<section id="radar-view"')]

    def corpo(self, inicio, fim):
        return self.js[self.js.index(inicio):self.js.index(fim)]

    def test_comparacao_declarada_pela_chave_e_ccee_pela_cobertura(self):
        c = self.corpo('function linhasComparacao(', 'const rotuloGrupoCmp=')
        self.assertIn('gruposDeclarada(', c)
        self.assertNotIn("x.periodo+'|'+x.mineral+'|'+x.unidade", c, 'a chave antiga (período, mineral, unidade) juntava produtos diferentes')
        self.assertIn('meses:ms', c)
        self.assertIn('indiceMaior(', self.js)
        self.assertIn("t('ea.cmp.coberturaDif')", c)
        self.assertIn('fora', c)   # registros que não entram na tabela continuam acessíveis

    def test_quarta_empresa_nao_substitui_ninguem(self):
        self.assertNotIn('S.cmp.shift()', self.js)
        c = self.corpo('function alternarComparacao(', 'function aviso(')
        self.assertIn('S.cmp.length>=CMP_MAX', c)
        self.assertIn("aviso(t('ea.cmpCheia'", c)
        self.assertIn('return false', c)

    def test_exportacoes_tipadas_sem_linha_de_comentario(self):
        self.assertNotRegex(self.js, r"\[`# \$\{", 'CSV com "# ..." antes do cabeçalho')
        self.assertIn('X_.csv(tabela)', self.js)
        self.assertIn('X_.xlsx(', self.js)
        for id_ in ('ea-exp-xlsx', 'ea-cmp-xlsx', 'ea-ficha-xlsx'):
            self.assertIn(f'id="{id_}"', self.secao)
        self.assertLess(self.html.index('/empresas-exportar.js?v='), self.html.index('/empresas-atlas.js?v='))

    def test_recorte_exportado_conta_as_fases_do_recorte(self):
        c = self.corpo('function tabelaRecorte(', 'const COLS_PROJETOS=')
        self.assertIn("lavra_autorizada_no_recorte:fase(l.ps,'lavra_autorizada')", c)
        self.assertIn("lavra_autorizada_empresa_total:fase(tod,'lavra_autorizada')", c)
        self.assertNotIn('l.e.grupos', c, 'fase da empresa inteira numa linha filtrada')
        self.assertIn('ccee_mwh_agente_periodo:cc.meses?', c)   # quem não é agente da CCEE sai vazio, não zero

    def test_limites_de_tela_tem_acesso_ao_resto(self):
        self.assertIn('data-cmp-tudo', self.js)
        self.assertIn("t('ea.cmp.mostrando'", self.js)
        self.assertIn('data-news-mais', self.js)
        self.assertNotIn('diretas.slice(0,40)', self.js)
        self.assertIn('data-rk-mais', self.js)
        self.assertIn("t('ea.eventosConta'", self.js)

    def test_voltar_e_avancar_leem_a_url(self):
        c = self.js[self.js.index("addEventListener('popstate'"):][:300]
        # a URL manda; o state só complementa (escopo, análise, rolagem) e pode ser nulo na entrada inicial
        self.assertIn('aplicarHash(h,ev.state)', c)
        self.assertIn('esc=st&&(', self.js)
        self.assertIn('if(!semHistorico)gravarHash(false)', self.corpo('function mostrarArea(', 'const HASH='))

    def test_selecao_fora_do_recorte_e_dita_no_cartao(self):
        self.assertIn('recorteDoCartao(e)', self.corpo('function resumoSel(', 'function resumoAlternativo('))
        self.assertIn("t('ea.card.foraRecorte')", self.js)

    def test_producao_anualizada_nao_aparece_como_declarada(self):
        self.assertIn("t('ea.k.declaradaSubParcial'", self.js)

    def test_sem_nome_vai_para_o_fim_da_ordem_por_nome(self):
        self.assertIn('semNome(a.e)-semNome(b.e)', self.js)
        nomes = [e for e in PACOTE['empresas'] if re.match(r'^\(nome n', e['nome'], re.I)]
        self.assertTrue(nomes, 'o pacote tem CNPJ raiz sem razão social')


# Linguagem de bastidor que não pode chegar ao consultor: nome de equipe, caminho interno, nome de arquivo ou script, pipeline, repositório.
BASTIDOR = re.compile(r'Squad\s*\d|\bsquads?\b|scripts?/|(?<![\w/.])data/|\bpublic/|\.json\b|\.py\b|pipeline|reposit[óo]rio|repository|GitHub|'
                      r'Dados brutos|Bases consolidadas|Dados corrigidos|build_\w+|\bcoletor\b', re.I)
# fonte pública real cujo endereço contém "/data/" (SEC EDGAR)
FONTE_PUBLICA = re.compile(r'^https?://www\.sec\.gov/Archives/edgar/data/')


def textos(o):
    if isinstance(o, dict):
        for v in o.values():
            yield from textos(v)
    elif isinstance(o, list):
        for v in o:
            yield from textos(v)
    elif isinstance(o, str):
        yield o


class AjustesFinaisTests(unittest.TestCase):
    """Ajustes finais (26/11/2026): nome de empresa nas análises → dossiê sem perder a análise, linguagem pública sem bastidor (interface,
    pacotes e exportações), procedência técnica fora do pacote servido, histórico com "Mostrar mais", exportações das análises pelo
    exportador tipado e município do dossiê → mapa pelo código IBGE. O comportamento é conferido no navegador (e2e, seção 20)."""

    @classmethod
    def setUpClass(cls):
        cls.html = (ROOT / 'public' / 'painel.html').read_text(encoding='utf-8')
        cls.secao = cls.html[cls.html.index('<section id="empresas-view"'):cls.html.index('<section id="radar-view"')]
        cls.js = (ROOT / 'public' / 'empresas-atlas.js').read_text(encoding='utf-8')
        cls.analises = (ROOT / 'public' / 'empresas.js').read_text(encoding='utf-8')
        cls.panorama = (ROOT / 'public' / 'panorama.js').read_text(encoding='utf-8')
        cls.base = json.loads((ROOT / 'data' / 'empresas' / 'empresas.json').read_text(encoding='utf-8'))
        src = (ROOT / 'public' / 'i18n.js').read_text(encoding='utf-8')
        corpo = src.split('const DICT={', 1)[1]
        pt, en = corpo.split('\n},en:{', 1)
        item = re.compile(r"'([A-Za-z0-9._]+)':'((?:[^'\\]|\\.)*)'")
        cls.pt, cls.en = dict(item.findall(pt)), dict(item.findall(en.split('\n}};', 1)[0]))

    def test_textos_da_aba_sem_linguagem_de_bastidor(self):
        usadas = set()
        for codigo in (self.js, self.analises, self.panorama):
            usadas |= set(re.findall(r"(?<![A-Za-z0-9_])t\('([A-Za-z0-9._]+)'", codigo))
        usadas |= set(re.findall(r'data-i18n(?:-html)?="([^"]+)"', self.secao))
        achados = [(k, lg) for k in sorted(usadas) for lg, d in (('pt', self.pt), ('en', self.en)) if BASTIDOR.search(d.get(k, ''))]
        self.assertEqual(achados, [])
        visivel = re.sub(r'<[^>]+>', ' ', re.sub(r'<script.*?</script>', ' ', self.secao, flags=re.S))
        self.assertIsNone(BASTIDOR.search(visivel))

    def test_pacotes_servidos_sem_linguagem_de_bastidor(self):
        for nome, pacote in (('atlas_empresas.json', PACOTE), ('empresas.json', self.base)):
            ruins = [x[:90] for x in textos(pacote) if BASTIDOR.search(x) and not FONTE_PUBLICA.search(x)]
            self.assertEqual(ruins, [], nome)

    def test_procedencia_tecnica_fica_fora_do_pacote_servido(self):
        for chave in ('gerado_por', 'entradas', 'cfem_csv'):
            self.assertNotIn(chave, PACOTE['meta'])
        prov = json.loads((ROOT / 'data' / 'empresas' / 'atlas_empresas_proveniencia.json').read_text(encoding='utf-8'))
        self.assertEqual(prov['gerado_por'], 'scripts/build_atlas_empresas.py')
        self.assertIn('panorama', prov['entradas'])
        self.assertNotIn('gerado_por', self.base['meta'])
        self.assertFalse(list((ROOT / 'public').rglob('*proveniencia*')))

    def test_projeto_com_a_fonte_que_o_registro_documenta(self):
        mercado = {p['id']: p for p in json.loads((ROOT / 'public' / 'data' / 'mercado' / 'projetos_go_v1.json').read_text(encoding='utf-8'))['projetos']}
        radar_anm = 0
        for p in PACOTE['projetos']:
            self.assertNotIn('Squad', p['fonte_nome'] or '')
            if p['fonte'] == 'radar' and (p['link'] or '').startswith('https://dadosabertos.anm.gov.br/'):
                self.assertTrue(p['fonte_nome'].startswith('ANM · '), p['fonte_nome'])
                radar_anm += 1
            if p['fonte'] == 'mercado':
                m = mercado[p['id'][3:]]
                self.assertEqual((p['fonte_nome'], p['link']), (m['fonte'], m['link']))
        self.assertGreater(radar_anm, 900)
        # na tela, o texto do link diz o destino (ANM pelo nome, outro site pelo domínio), não quem fez o levantamento
        self.assertIn('function destinoLink(', self.js)
        self.assertIn("${escape(destinoLink(p.link))} ↗</a>", self.js)

    def test_base_de_producao_ja_tem_os_textos_publicos(self):
        """O --so-textos do gerador reaplica a camada de textos sem as entradas do Squad 1: sobre o pacote do repositório, nada muda."""
        with tempfile.TemporaryDirectory() as tmp:
            alvo = Path(tmp) / 'empresas.json'
            alvo.write_bytes((ROOT / 'data' / 'empresas' / 'empresas.json').read_bytes())
            subprocess.run([sys.executable, str(ROOT / 'scripts' / 'build_empresas_base.py'), '--so-textos', '--saida', str(alvo)],
                           check=True, capture_output=True)
            self.assertEqual(alvo.read_bytes(), (ROOT / 'data' / 'empresas' / 'empresas.json').read_bytes())

    def test_nome_nas_analises_abre_o_dossie_pela_chave(self):
        r = subprocess.run(['node', str(ROOT / 'tests' / 'js' / 'analises_ligacao.js')], capture_output=True, text=True, encoding='utf-8')
        self.assertEqual(r.returncode, 0, r.stderr)
        d = json.loads(r.stdout)
        modelo = d['modelo']['cnpj']
        barras = {x['cnpj']: x['rotulo'] for x in d['barras']}
        # mesmo nome, dois CNPJs: duas barras, dois atalhos, o CNPJ no rótulo
        self.assertIn(modelo, barras)
        self.assertIn('99999901', barras)
        self.assertNotEqual(barras[modelo], barras['99999901'])
        self.assertTrue(d['foraNaTabela'])
        self.assertNotIn('99999902', {x['cnpj'] for x in d['tabela'] + d['barras']}, 'CNPJ fora do índice não vira atalho')
        self.assertFalse(d['pfComAtalho'])
        self.assertTrue(d['coberturaSemAtalho'], 'linha do estado não vira atalho')
        self.assertEqual(d['filtrosAposTrocaTodas'], {'ano': '2023', 'base': '', 'min': 'Ouro'})
        self.assertEqual(sorted(d['declaradaTabela']), sorted(d['declaradaEsperada']))
        self.assertTrue(d['semLigacao'])

    def test_abrir_da_analise_nao_muda_a_analise_e_cria_uma_entrada(self):
        c = self.js[self.js.index('function abrirDaAnalise('):self.js.index('function voltarAnalise(')]
        self.assertIn("selecionar(e.i,{origem:'analise',semHistorico:true})", c)
        self.assertEqual(c.count("mostrarArea('dossie')"), 1)
        self.assertIn("S.escopo=escopo||(origem==='analise'?S.escopo:'empresa')", self.js)
        self.assertIn('aplicarHash(h,ev.state)', self.js)
        self.assertIn('titulares:true', self.panorama)

    def test_historico_e_exportacoes_das_analises(self):
        self.assertIn('data-ev-mais', self.js)
        self.assertNotIn('evs.length=Math.min(evs.length,25)', self.js)
        self.assertIn('window.EmpresasExportar.csv(tabela)', self.analises)
        self.assertNotIn('`# ${', self.analises)
        self.assertNotIn("const celula=", self.analises)

    def test_municipio_do_dossie_pelo_codigo_ibge(self):
        # a missão de cartografia substituiu o "enquadra sem filtrar" por recorte explícito (ver CartografiaTests): o vínculo continua
        # sendo o código IBGE, nunca o nome do município
        self.assertIn('data-mun-ibge', self.js)
        self.assertNotIn("m[1]===b.dataset.mun", self.js)
        self.assertIn('irMunicipioDoDossie(kDoIbge(a.dataset.munIbge))', self.js)


class CartografiaTests(unittest.TestCase):
    """Cartografia (26/11/2026): empresa × direito ANM × município × operação. Clique só na camada do modo, processo exato com escolha
    dos sobrepostos, cartão único (empresa, processo, município), seleção municipal pelo código IBGE com contorno e recorte, prévia do
    município no dossiê com os direitos da empresa. O comportamento é conferido no navegador (tests/e2e_cartografia_empresas.py)."""

    @classmethod
    def setUpClass(cls):
        cls.html = (ROOT / 'public' / 'painel.html').read_text(encoding='utf-8')
        cls.js = (ROOT / 'public' / 'empresas-atlas.js').read_text(encoding='utf-8')
        cls.css = (ROOT / 'public' / 'empresas-atlas.css').read_text(encoding='utf-8')
        src = (ROOT / 'public' / 'i18n.js').read_text(encoding='utf-8')
        pt, en = src.split('const DICT={', 1)[1].split('\n},en:{', 1)
        item = re.compile(r"'([A-Za-z0-9._]+)':'((?:[^'\\]|\\.)*)'")
        cls.pt, cls.en = dict(item.findall(pt)), dict(item.findall(en.split('\n}};', 1)[0]))
        r = subprocess.run(['node', str(ROOT / 'tests' / 'js' / 'cartografia.js')], capture_output=True, text=True, encoding='utf-8')
        if r.returncode:
            raise RuntimeError(r.stderr)
        cls.node = json.loads(r.stdout)

    def trecho(self, ini, fim):
        a = self.js.index(ini)
        return self.js[a:self.js.index(fim, a)]

    def test_so_a_camada_do_modo_responde_ao_clique(self):
        c = self.trecho('function acertar(', 'function munNoPixel(')
        self.assertIn('TIPO_DO_MODO[S.modo]', c)
        self.assertIn('.filter(h=>h.t===tp)', c)
        self.assertIn("if(S.modo!=='processos')return null;", c)   # polígonos só no modo Processos
        realce = self.trecho('function pintarProcessosDaEmpresa(', 'function pintarDestaque(')
        self.assertIn("if(S.modo==='processos')GRADE.pend.push(", realce)   # no modo Empresas, realce sem alvo
        self.assertIn('if(alvo)S.poliDesenhados.push(k)', self.js)
        op = self.trecho('function desenharOperacao(', 'function irParaProcesso(')
        self.assertIn('interactive:false', op)
        self.assertNotIn('bindTooltip', op)

    def test_processo_exato_sem_escolha_silenciosa_nem_corte(self):
        c = self.trecho('function clicarMapa(', 'function popupLista(')
        self.assertIn('if(h.ks.length===1){selecionarProcesso(h.ks[0]);return}', c)
        self.assertNotIn("selecionar(empresas[0],{origem:'mapa',processo", self.js)
        self.assertNotIn('.slice(0,12)', self.js)
        p = self.trecho('function popupLista(', 'function abrirProjeto(')
        self.assertIn('ea-pop-filtro', p)
        self.assertIn("ev.key!=='ArrowDown'&&ev.key!=='ArrowUp'", p)
        # o processo em foco não troca a empresa selecionada
        s = self.trecho('function selecionarProcesso(', 'function selecionarMunicipio(')
        self.assertNotIn('selecionar(', s.replace('function selecionarProcesso(', ''))

    def test_cartao_unico_com_tres_entidades(self):
        self.assertEqual(self.html.count('class="ea-card"'), 1)
        c = self.trecho('function resumoSel(', 'function cartaoEmpresa(')
        for f in ('cartaoProcesso(box)', 'cartaoMunicipio(box)', 'cartaoEmpresa(box)'):
            self.assertIn(f, c)
        self.assertIn('function focoAtual(', self.js)

    def test_cfem_do_processo_nunca_e_a_do_titular(self):
        c = self.trecho('function cartaoProcesso(', 'function cartaoMunicipio(')
        self.assertIn('D.cfem_processo_ano', c)
        self.assertNotIn('cfemPeriodo(', c)
        self.assertNotIn('e.cfem', c)

    def test_url_oficial_da_anm_so_com_numero_valido(self):
        u = self.node['urls']
        self.assertEqual(u['803343/1973'], 'https://sistemas.anm.gov.br/SCM/Extra/site/admin/dadosProcesso.aspx?numero=803343&ano=1973')
        self.assertTrue(u['860.337/2020'].endswith('numero=860337&ano=2020'))
        for ruim in ('abc', '', 'null', '12/2020', '860337/20201'):
            self.assertIsNone(u[ruim], ruim)

    def test_contorno_com_multipartes_e_buraco(self):
        m = self.node['mineiros']
        self.assertEqual(m['aneis'], 3)
        self.assertTrue(m['sul'], 'a parte separada ao sul é Mineiros')
        self.assertFalse(m['furo'], 'o enclave de Portelândia não é Mineiros')
        self.assertTrue(m['furoEmPortelandia'])
        self.assertEqual(self.node['semContorno'], [], 'todo município da aba tem contorno no pacote geográfico')

    def test_recorte_municipal_pelo_vinculo_ibge_nao_pelo_centroide(self):
        c = self.trecho('function procsFiltrados(', 'function cfemPeriodo(')
        self.assertIn('r[PC.municipios].includes(mun)', c)
        # dados reais: a CMOC tem 8 processos vinculados a Catalão e só 5 com o centroide dentro do contorno — os 8 entram no recorte
        cmoc = PACOTE['empresas'][[e['cnpj'] for e in PACOTE['empresas']].index('26108898')]['i']
        pc = {c_: i for i, c_ in enumerate(PACOTE['processos']['cols'])}
        k = [str(m[0]) for m in PACOTE['dims']['mun']].index('5205109')
        n = sum(1 for r in PACOTE['processos']['rows'] if r[pc['empresa']] == cmoc and k in r[pc['municipios']])
        self.assertEqual(n, self.node['cmocCatalao']['n'])
        self.assertLess(len(self.node['cmocCatalao']['dentro']), n)

    def test_previa_nao_muda_estado_e_nao_inventa_ponto(self):
        c = self.trecho('function htmlPrevia(', 'const previaAberta=')
        for proibido in ('anotarHistorico(', 'gravarHash(', 'redesenhar(', 'selecionar(', 'mostrarArea(', 'setView(', 'fitBounds(', "el('ea-mun').value="):
            self.assertNotIn(proibido, c, proibido)
        self.assertIn('if(!dentroPoligono(geo,q.x,q.y)){fora++;continue}', c)
        self.assertIn('PREVIA_MS=650', self.js)
        self.assertIn("ev.pointerType==='mouse'", self.js)   # toque navega direto, sem prévia
        self.assertNotIn('L.map(', c)
        self.assertIn('pointer-events:none', self.css[self.css.index('.ea-previa{'):])

    def test_esc_fecha_em_passos(self):
        c = self.trecho("document.addEventListener('keydown',ev=>{\n  if(ev.key!=='Escape')return;", '// Voltar/Avançar')
        ordem = [c.index(x) for x in ('fecharPrevia()', 'gaveta(false)', 'closePopup()', 'cam.open=false', "S.foco='fechado'", 'limparMunicipio()')]
        self.assertEqual(ordem, sorted(ordem))

    def test_painel_ferramenta_de_municipio_e_versao(self):
        # desde a auditoria crítica (27/11), a opção vem LIGADA: clicar no mapa seleciona o município sem configurar nada
        self.assertIn('<input type="checkbox" id="ea-sel-mun" checked>', self.html)
        self.assertIn('data-i18n="ea.selMun"', self.html)
        self.assertNotIn('?v=20261126e', self.html)
        self.assertNotIn('?v=20261126f', self.html)

    def test_exportacao_leva_o_codigo_ibge_e_avisa_a_area(self):
        self.assertIn("['filtro_municipio_ibge','id',9]", self.js)
        self.assertIn("['municipios_ibge','texto',16]", self.js)
        self.assertIn('não é a área dentro do município', self.pt['ea.col.area_ha_no_recorte'])
        self.assertIn('not the area inside the municipality', self.en['ea.col.area_ha_no_recorte'])

    def test_textos_da_cartografia_em_pt_e_en_com_os_mesmos_campos(self):
        chaves = [k for k in self.pt if k.startswith(('ea.card.', 'ea.previa.', 'ea.volta.', 'ea.nota.', 'ea.tip.mun', 'ea.selMun', 'ea.munLimpar'))]
        self.assertGreater(len(chaves), 40)
        for k in chaves:
            self.assertIn(k, self.en, k)
            self.assertEqual(sorted(re.findall(r'\{(\w+)\}', self.pt[k])), sorted(re.findall(r'\{(\w+)\}', self.en[k])), k)
        # o produto não chama título ANM de mina
        self.assertIn('não uma mina', self.pt['ea.previa.leg'])
        self.assertEqual(self.pt['ea.previa.titulo'], 'Direitos minerários da empresa neste município')


class AuditoriaCriticaTests(unittest.TestCase):
    """Auditoria crítica (27/11/2026): o significado do que a aba mostra, conferido contra um ORÁCULO que lê as fontes por outro caminho
    (tests/oraculo_empresas.py: panorama.json, processos_complemento.json e producao.json), não contra o próprio pacote nem a interface.
    Operação documentada × direitos vigentes × só disponibilidade × só CFEM; situação "Operação ativa" como indício; município por clique
    direto; município no endereço; integrador sem efeito parcial."""

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(ROOT / 'tests'))
        import oraculo_empresas
        cls.O = oraculo_empresas
        cls.js = (ROOT / 'public' / 'empresas-atlas.js').read_text(encoding='utf-8')
        cls.html = (ROOT / 'public' / 'painel.html').read_text(encoding='utf-8')
        src = (ROOT / 'public' / 'i18n.js').read_text(encoding='utf-8')
        pt, en = src.split('const DICT={', 1)[1].split('\n},en:{', 1)
        item = re.compile(r"'([A-Za-z0-9._]+)':'((?:[^'\\]|\\.)*)'")
        cls.pt, cls.en = dict(item.findall(pt)), dict(item.findall(en.split('\n}};', 1)[0]))
        r = subprocess.run(['node', str(ROOT / 'tests' / 'js' / 'municipios_origem.js')], capture_output=True, text=True, encoding='utf-8')
        if r.returncode:
            raise RuntimeError(r.stderr)
        cls.node = json.loads(r.stdout)
        cls.mun = {k: str(m[0]) for k, m in enumerate(PACOTE['dims']['mun'])}

    def test_pacote_bate_com_as_fontes_em_todas_as_empresas(self):
        for e in PACOTE['empresas']:
            o = self.O.empresa(e['cnpj'])
            self.assertEqual(e['n'], o['processos'], e['cnpj'])
            self.assertEqual({self.mun[k] for k in e['mun']}, o['todos'], e['cnpj'])

    def test_a_aba_classifica_os_municipios_como_as_fontes(self):
        """A função real da aba (munsPorOrigem, rodada no Node) dá, para TODAS as empresas, as mesmas origens que o oráculo."""
        self.assertEqual(len(self.node['empresas']), len(PACOTE['empresas']))
        for cnpj, o in self.node['empresas'].items():
            esp = self.O.empresa(cnpj)
            for k in ('op', 'vig', 'disp', 'cfem'):
                self.assertEqual(set(o[k]), esp[k], (cnpj, k))
            self.assertEqual(o['total'], len(esp['todos']), cnpj)

    def test_maraca_cmoc_nexa(self):
        casos = {'86902053': (173, 29, 26, {'Paraúna', 'São João da Paraúna', 'Matrinchã'}, {'Alto Horizonte', 'Nova Iguaçu de Goiás'}),
                 '26108898': (57, 11, 9, {'Santa Fé de Goiás', 'Três Ranchos'}, {'Catalão', 'Ouvidor'}),
                 '42416651': (201, 48, 47, {'Campos Verdes'}, set())}
        for cnpj, (n, todos, vig, so_disp, op) in casos.items():
            o = self.O.empresa(cnpj)
            self.assertEqual((o['processos'], len(o['todos']), len(o['vig'])), (n, todos, vig), cnpj)
            self.assertEqual({o['nome'](m) for m in o['disp']}, so_disp, cnpj)
            self.assertEqual({o['nome'](m) for m in o['op']}, op, cnpj)
        # Maracá: CFEM com origem só em Alto Horizonte
        self.assertEqual({self.O.empresa('86902053')['nome'](m) for m, v in self.O.indices()[2]['86902053'].items() if v}, {'Alto Horizonte'})

    def test_numeros_da_auditoria(self):
        pares = self.O.pares_so_disponibilidade()
        self.assertEqual((len(pares), len({c for c, _ in pares})), (145, 93))
        self.assertEqual(len(self.O.empresas_com_municipio_so_cfem()), 13)

    def test_situacao_operacao_ativa_vira_indicio(self):
        # nenhuma situação fica sem rótulo próprio, e nenhum texto da aba diz "operação ativa"
        self.assertTrue(all(s.startswith('ea.st.') for s in self.node['status']), self.node['status'])
        for k, v in list(self.pt.items()) + list(self.en.items()):
            if k.startswith('ea.'):
                self.assertNotRegex(v, r'(?i)opera[çc][ãa]o ativa|active operation', k)
        self.assertIn('indício de atividade, não confirmação', self.pt['ea.st.lavraCfem'])
        # o texto cru da fonte só é lido dentro de rotuloStatus e no teste /^Opera/ que conta os processos do bloco de indícios
        usos = [m.start() for m in re.finditer(r'D\.dims\.status\[', self.js)]
        self.assertLessEqual(len(usos), 4, 'D.dims.status lido fora de rotuloStatus')
        self.assertIn('rotuloStatus(r[PC.status])', self.js)

    def test_clique_direto_no_municipio_sem_camadas(self):
        self.assertIn('<input type="checkbox" id="ea-sel-mun" checked>', self.html)
        alvo = re.search(r'const alvoMunicipio=\(\)=>([^;]+);', self.js).group(1)
        self.assertNotIn('munSel()', alvo)
        self.assertIn("if(k!==munSel()){selecionarMunicipio(k,{origem:'mapa',enquadrar:false});return}\n   limparMunicipio();return}", self.js)

    def test_recorte_municipal_no_mapa(self):
        # ponto local (centroide dentro do contorno) e enquadramento pelo município
        f = self.js[self.js.index('function pontosDasEmpresas('):self.js.index('function posEmpresa(')]
        self.assertIn('dentroPoligono(geo,MP.x[j],MP.y[j])', f)
        d = self.js[self.js.index('async function desenharSelecao('):self.js.index('// Município da operação declarada')]
        self.assertIn("procsFiltrados(S.sel,{mun:local?String(km):'',min:'',grupo:''})", d)
        self.assertIn('caixasPoligonos()', self.js)

    def test_endereco_leva_o_municipio(self):
        m = re.search(r'const HASH=(/.+/);', self.js).group(1)
        self.assertIn('mun', m)
        r = subprocess.run(['node', '-e', f'const H={m};for(const h of ["#empresas/explorar/26108898/mun/5205109","#empresas/explorar/mun/5205109","#empresas/26108898"])console.log(JSON.stringify(h.match(H).slice(1)))'],
                           capture_output=True, text=True)
        self.assertEqual([json.loads(x) for x in r.stdout.split()], [['explorar', '26108898', '5205109'], ['explorar', None, '5205109'], [None, '26108898', None]])




class LinksSegurosTests(unittest.TestCase):
    """Os links vêm de coleta automática (notícias) e de bases de terceiros, e a tela os põe em <a href>: só http(s) entra."""

    def test_todo_link_do_pacote_e_http_ou_https(self):
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

    def test_todo_href_da_aba_passa_por_url_segura(self):
        js = (ROOT / 'public' / 'empresas-atlas.js').read_text(encoding='utf-8')
        self.assertIn("const urlSegura=u=>/^https?:\\/\\//i.test", js)
        self.assertFalse(re.findall(r'href="\$\{escape\((?!urlSegura\()', js), 'link sem urlSegura() em empresas-atlas.js')



if __name__ == '__main__':
    unittest.main()
