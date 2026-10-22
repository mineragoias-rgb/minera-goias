"""Mapa Mineral de Goiás (data/mapa/, gerado por scripts/build_mapa_base.py): o catálogo tem de bater com os arquivos, as chaves com
o grão de cada camada, os dados com a regra de pessoa física, e a API só entrega o que o catálogo publica a quem tem sessão."""
import base64
import csv
import importlib.util
import json
import os
import re
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
MAPA = ROOT / 'data' / 'mapa'
sys.path.insert(0, str(ROOT / 'scripts'))
import build_projetos_minerais_goias as radar  # noqa: E402  regra de titular e hierarquia de maturidade
from build_projetos_go import ler_xlsx, registros  # noqa: E402

CPF = re.compile(r'\d{3}\.\d{3}\.\d{3}-\d{2}')
PROCESSO = re.compile(r'\d{1,6}/\d{4}')
# nome de pessoa, documento e endereço; no SIAGAS, proprietário, perfurador e local do poço
CAMPOS_PESSOAIS = {'nm_pessoa', 'cpf_cnpj', 'endereco', 'fone', 'str_propri', 'str_perfur', 'str_local_'}
TIPOS = {'texto', 'categoria', 'numero', 'inteiro', 'ano', 'data', 'url', 'processo', 'municipio', 'municipios', 'municipios_nome', 'lista',
         'mineral', 'titular', 'posicao', 'booleano'}


def ler(caminho):
    return json.loads(Path(caminho).read_text(encoding='utf-8'))


def vertices(pacote):
    xy = base64.b64decode(pacote['xy'])
    return struct.unpack(f'<{len(xy) // 2}H', xy)


def partes(pacote):
    inicio = base64.b64decode(pacote['partStart'])
    dono = base64.b64decode(pacote['partFeat'])
    return struct.unpack(f'<{len(inicio) // 4}I', inicio), struct.unpack(f'<{len(dono) // 4}I', dono)


class CatalogoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cat = ler(MAPA / 'catalogo.json')
        cls.val = ler(MAPA / 'validacao.json')
        cls.camadas = {c['id']: c for c in cls.cat['camadas']}
        cls.proprias = [c for c in cls.cat['camadas'] if c['dados']['formato'] == 'mapa-v1']

    def test_cada_camada_declara_o_contrato(self):
        grupos = {g['id'] for g in self.cat['grupos']}
        self.assertEqual(len(self.camadas), len(self.cat['camadas']), 'id de camada repetido')
        for c in self.cat['camadas']:
            for k in ('id', 'nome', 'nome_en', 'grupo', 'geometria', 'dados', 'fonte', 'data_retrato', 'periodo_referencia', 'temporalidade', 'crs', 'chave',
                      'campos', 'filtros', 'legenda', 'visivel_padrao', 'carga', 'n_feicoes', 'bytes'):
                self.assertIn(k, c, f"{c['id']} sem {k}")
            self.assertIn(c['grupo'], grupos)
            self.assertIn(c['geometria'], ('ponto', 'linha', 'poligono'))
            self.assertIn(c['carga'], ('inicial', 'sob_demanda'))
            ids = [f['id'] for f in c['campos']]
            self.assertIn(c['chave'], ids, c['id'])
            for f in c['campos']:
                self.assertTrue(f.get('rotulo') and f.get('rotulo_en'), (c['id'], f['id']))
                self.assertIn(f['tipo'], TIPOS, (c['id'], f['id']))
                if f['tipo'] == 'numero':
                    self.assertTrue(f.get('unidade'), f"{c['id']}.{f['id']}: número sem unidade")
            for filtro in c['filtros']:
                self.assertIn(filtro, ids, c['id'])
            if c['legenda']['tipo'] == 'categorias':
                self.assertIn(c['legenda']['campo'], ids, c['id'])

    def test_arquivos_batem_com_o_catalogo(self):
        no_disco = {p.stem for p in (MAPA / 'camadas').glob('*.json')}
        self.assertEqual(no_disco, {c['id'] for c in self.proprias}, 'arquivo de camada órfão ou faltando')
        for c in self.proprias:
            caminho = ROOT / c['dados']['arquivo']
            self.assertEqual(c['dados']['endpoint'], f"/api/mapa/camadas/{c['id']}")
            self.assertEqual(caminho.stat().st_size, c['bytes'], c['id'])
        for c in self.cat['camadas']:
            if c['dados']['formato'] != 'mapa-v1':
                self.assertTrue((ROOT / c['dados']['arquivo']).exists(), c['id'])
                self.assertTrue(c['dados']['endpoint'].startswith('/api/atlas'), c['id'])
        tabelas = {t['id'] for t in self.cat['tabelas']}
        self.assertEqual({p.stem for p in (MAPA / 'tabelas').glob('*.json')}, tabelas)
        for t in self.cat['tabelas']:
            self.assertEqual((ROOT / t['arquivo']).stat().st_size, t['bytes'], t['id'])

    def test_geometria_e_atributos_de_cada_camada(self):
        for c in self.proprias:
            p = ler(ROOT / c['dados']['arquivo'])
            self.assertEqual(p['n'], c['n_feicoes'], c['id'])
            self.assertEqual(p['campos'], [f['id'] for f in c['campos']], c['id'])
            for campo, coluna in p['valores'].items():
                self.assertEqual(len(coluna), p['n'], (c['id'], campo))
                if campo in p['dic']:
                    for v in coluna:
                        for x in (v if isinstance(v, list) else [v]):
                            self.assertTrue(x is None or 0 <= x < len(p['dic'][campo]), (c['id'], campo))
            inicio, dono = partes(p)
            self.assertEqual(len(inicio), len(dono) + 1, c['id'])
            self.assertEqual(inicio[-1], len(vertices(p)) // 2, c['id'])
            self.assertEqual(set(dono), set(range(p['n'])), f"{c['id']}: feição sem geometria")
            b = p['bounds']
            # caixa de Goiás com folga para feições cortadas na divisa; x = longitude, y = latitude
            self.assertTrue(-53.5 <= b['lon0'] < b['lon1'] <= -45.6 and -19.8 <= b['lat0'] < b['lat1'] <= -12.2, (c['id'], b))
            minimo = {'ponto': 1, 'linha': 2, 'poligono': 3}[c['geometria']]
            self.assertTrue(all(inicio[k + 1] - inicio[k] >= minimo for k in range(len(dono))), c['id'])

    def test_chaves_unicas_no_grao_de_cada_camada(self):
        for c in self.proprias:
            p = ler(ROOT / c['dados']['arquivo'])
            chaves = p['valores'][c['chave']]
            self.assertNotIn(None, chaves, c['id'])
            self.assertEqual(len(chaves), len(set(map(str, chaves))), f"{c['id']}: chave {c['chave']} repetida")
        minas = ler(MAPA / 'camadas' / 'minas_ativas.json')
        # a fonte repete o processo uma vez por substância: o mapa tem um processo por feição e guarda quantos registros juntou
        self.assertEqual(sum(minas['valores']['n_registros_fonte']), self.val['camadas']['minas_ativas']['registros_fonte'])
        self.assertLess(minas['n'], self.val['camadas']['minas_ativas']['registros_fonte'])

    def test_contagens_batem_com_o_recorte(self):
        self.assertEqual(self.val['erros'], [])
        indice = {}
        with open(ROOT / 'Squad 1' / 'P3M' / 'Recortado pelo polígono de Goiás' / '_indice_recorte.csv', encoding='utf-8-sig') as f:
            for linha in f.read().splitlines()[1:]:
                partes_ = linha.split(';')
                indice[partes_[0]] = int(partes_[3])
        for cid, v in self.val['camadas'].items():
            if v['origem'] != 'p3m':
                continue
            for a in v['arquivos']:
                self.assertEqual(a['registros'], indice[a['arquivo']], (cid, a['arquivo']))
            self.assertEqual(v['sem_geometria'], 0, cid)
            self.assertFalse(v['chave']['duplicados'], cid)
            self.assertEqual(v.get('pontos_fora_de_goias', 0), 0, cid)

    def test_sem_dado_pessoal(self):
        for caminho in MAPA.rglob('*.json'):
            texto = caminho.read_text(encoding='utf-8')
            self.assertIsNone(CPF.search(texto), f'CPF em {caminho.name}')
        for c in self.cat['camadas']:
            self.assertFalse({f['id'] for f in c['campos']} & CAMPOS_PESSOAIS, c['id'])
            for f in c['campos']:
                fontes = f.get('fonte') or []
                self.assertFalse(set([fontes] if isinstance(fontes, str) else fontes) & CAMPOS_PESSOAIS, (c['id'], f['id']))
        for c in self.proprias:
            p = ler(ROOT / c['dados']['arquivo'])
            for nome in p['dic'].get('titular', []):
                self.assertTrue(nome == radar.TITULAR_INDIVIDUAL or radar.MARCA_EMPRESA.search(nome), (c['id'], nome))
        tit = ler(MAPA / 'tabelas' / 'processos_complemento.json')
        for nome in tit['dic']['titular']:
            self.assertTrue(nome == radar.TITULAR_INDIVIDUAL or radar.MARCA_EMPRESA.search(nome), nome)

    def test_sem_texto_com_codificacao_estragada(self):
        """Nome gravado em UTF-8 e lido como Latin-1 ('INÃ¡CIA') isolava um 'CIA' e fazia nome de pessoa passar por empresa."""
        estragado = re.compile('[ÃÂ][\x80-\xbf\u039c]')
        for caminho in MAPA.rglob('*.json'):
            achado = estragado.search(caminho.read_text(encoding='utf-8'))
            self.assertIsNone(achado, f'{caminho.name}: {achado and achado.group(0)!r}')

    def test_posicao_aproximada_rotulada(self):
        emp = ler(MAPA / 'camadas' / 'empreendimentos_sig.json')
        rotulos = [emp['dic']['posicionamento'][i] for i in emp['valores']['posicionamento']]
        self.assertTrue(all(r for r in rotulos))
        self.assertTrue(any(r.startswith('aproximada') for r in rotulos))


class InventarioTests(unittest.TestCase):
    """O inventário do P3M (Squad 1/P3M/inventario_p3m.csv) dá a data, a pasta temática e a ficha de cada camada do P3M."""
    @classmethod
    def setUpClass(cls):
        cls.cat = ler(MAPA / 'catalogo.json')
        with open(ROOT / 'Squad 1' / 'P3M' / 'inventario_p3m.csv', encoding='utf-8-sig', newline='') as f:
            cls.linhas = list(csv.DictReader(f, delimiter=';'))
        cls.por_zip = {Path(a).name: r for r in cls.linhas for col in ('arquivo_recortado', 'arquivo_original') for a in r[col].split(';') if a}

    def test_grupos_sao_as_pastas_tematicas(self):
        self.assertEqual([g['pasta'] for g in self.cat['grupos']], sorted({r['pasta_tematica'] for r in self.linhas}))
        # a ordem vem da pasta; o nome mostrado na aba não leva o número dela
        self.assertEqual([g['nome'] for g in self.cat['grupos'] if re.match(r'\d', g['nome'] + g['nome_en'])], [])

    def test_retrato_pasta_e_ficha_vem_do_inventario(self):
        pasta_do_grupo = {g['id']: g['pasta'] for g in self.cat['grupos']}
        for c in self.cat['camadas']:
            if c['dados']['formato'] != 'mapa-v1':
                self.assertNotIn('p3m', c, c['id'])
                continue
            linhas = [self.por_zip[z] for z in c['fonte_arquivos']]
            datas = sorted({r['data_download'] for r in linhas})
            self.assertEqual(c['data_retrato'], datas[0] if len(datas) == 1 else datas, c['id'])
            self.assertEqual({r['pasta_tematica'] for r in linhas}, {pasta_do_grupo[c['grupo']]}, c['id'])
            self.assertEqual([f['camada'] for f in c['p3m']], list(dict.fromkeys(r['camada'] for r in linhas)), c['id'])
            for f in c['p3m']:
                r = next(x for x in linhas if x['camada'] == f['camada'])
                self.assertEqual((f['orgao'], f['baixado_em'], f['atualizacao_sgb'] or '', f['fonte_atualizacao_sgb']),
                                 (r['orgao'], r['data_download'], r['data_atualizacao_sgb'], r['fonte_data_sgb']), c['id'])
                self.assertEqual(f['classificacao'], [x for x in (r['categoria_p3m'], r['tema_p3m'], r['subtema_p3m']) if x], c['id'])

    def test_resumo_e_link_do_inventario(self):
        inv = self.cat['p3m']['inventario']
        self.assertEqual(inv['camadas'], len(self.linhas))
        self.assertEqual(inv['no_mapa'], len({f['camada'] for c in self.cat['camadas'] for f in c.get('p3m', [])}))
        self.assertTrue(inv['url'].startswith('https://github.com/mineragoias-rgb/minera-goias/blob/main/'), inv['url'])
        self.assertTrue(inv['url'].endswith('/P3M/inventario_p3m.csv'), inv['url'])
        self.assertNotIn('sem dia registrado', self.cat['p3m']['nota_retrato'])


class TabelasTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.atlas = ler(ROOT / 'data' / 'atlas' / 'atlas.json')
        cls.processos = ler(ROOT / 'data' / 'atlas' / 'processes.json')
        cls.mun = ler(MAPA / 'tabelas' / 'municipios.json')
        cls.radar = ler(MAPA / 'tabelas' / 'radar_projetos.json')
        cls.planilha = registros(ler_xlsx(ROOT / 'Squad 1' / 'Radar de Projetos' / 'projetos_minerais_goias.xlsx')['PROJETOS'])

    def test_municipios_com_medidas_documentadas(self):
        codigos = [l['code'] for l in self.mun['linhas']]
        self.assertEqual(len(codigos), 246)
        self.assertEqual(set(codigos), {m['code'] for m in self.atlas['municipalities']})
        for nome, m in self.mun['medidas'].items():
            self.assertIn('unidade', m, nome)
            self.assertIn('aditiva_entre_municipios', m, nome)
        cfem = self.mun['medidas']['cfem_recolhida']
        self.assertEqual(cfem['periodos'], [str(a) for a in self.atlas['cfem']['anos']])
        self.assertIn(cfem['periodos'][-1], cfem['periodo_incompleto'], 'o último ano da CFEM é parcial e precisa dizer isso')
        self.assertIn(cfem['periodo_padrao'], cfem['periodos'])
        self.assertNotIn(cfem['periodo_padrao'], cfem['periodo_incompleto'], 'o período padrão tem de ser um ano completo')
        # CFEM: a tabela repete o Atlas, sem rateio
        por_nome = {l['Município']: l for l in self.atlas['cfem']['linhas']}
        for l in self.mun['linhas']:
            for a in cfem['periodos']:
                self.assertAlmostEqual(l['cfem_recolhida'][a], por_nome[l['name']][a], places=2)

    def test_radar_contado_uma_vez(self):
        """Total municipal nunca copiado para cada projeto: cada projeto conta só no município principal."""
        total = sum(sum(l['radar_projetos'].values()) for l in self.mun['linhas'])
        com_municipio = sum(1 for p in self.radar['linhas'] if p['municipio'])
        self.assertEqual(total, com_municipio)
        self.assertFalse(self.mun['medidas']['processos_que_tocam']['aditiva_entre_municipios'])

    def test_radar_ligado_por_processo_sem_coordenada_inventada(self):
        self.assertEqual([p['id'] for p in self.radar['linhas']], [p['ID'] for p in self.planilha])
        no_mapa = set(self.processos['processo'].split('\x01'))
        for p in self.radar['linhas']:
            self.assertIn(p['maturidade'], radar.HIERARQUIA)
            self.assertNotIn('lat', p)
            self.assertNotIn('lon', p)
            for k in p['processos']:
                self.assertRegex(k, PROCESSO)
            n = sum(1 for k in p['processos'] if k in no_mapa)
            self.assertEqual(p['processos_no_mapa'], n, p['id'])
            esperado = 'processos' if n else 'municipio' if p['municipios_codigos'] else 'nenhuma'
            self.assertEqual(p['ligacao'], esperado, p['id'])

    def test_complemento_alinhado_com_os_processos_do_atlas(self):
        comp = ler(MAPA / 'tabelas' / 'processos_complemento.json')
        self.assertEqual(comp['processos'], self.processos['processo'].split('\x01'))
        for campo in ('titular', 'municipios', 'mineral'):
            self.assertEqual(len(comp[campo]), self.processos['n'], campo)
        self.assertTrue(set(comp['dic']['municipios']) <= {m['code'] for m in self.atlas['municipalities']})

    def test_filtro_por_municipio_bate_com_o_atlas_e_o_perfil(self):
        """O filtro por município (complemento), o perfil do município (tabela) e a aba Atlas contam os mesmos processos."""
        comp = ler(MAPA / 'tabelas' / 'processos_complemento.json')
        conta = {}
        for lista in comp['municipios']:
            for j in lista or []:
                conta[comp['dic']['municipios'][j]] = conta.get(comp['dic']['municipios'][j], 0) + 1
        perfil = {l['code']: l['processos_que_tocam'] for l in self.mun['linhas']}
        for m in self.atlas['municipalities']:
            self.assertEqual(conta.get(m['code'], 0), m['processes'], m['name'])
            self.assertEqual(perfil[m['code']], m['processes'], m['name'])


class AbaTests(unittest.TestCase):
    """A aba do mapa no painel: navegação, rota, scripts e estilos com escopo próprio."""

    @classmethod
    def setUpClass(cls):
        publico = ROOT / 'public'
        cls.html = (publico / 'painel.html').read_text(encoding='utf-8')
        cls.js = (publico / 'mapa.js').read_text(encoding='utf-8')
        cls.css = (publico / 'mapa.css').read_text(encoding='utf-8')
        cls.painel = (publico / 'painel.js').read_text(encoding='utf-8')

    def test_navegacao_e_rota(self):
        botoes = re.findall(r'data-view="(\w+)"', self.html)
        self.assertEqual(botoes[:2], ['atlas', 'mapa'], 'o mapa fica logo abaixo de Atlas e panorama')
        self.assertIn("'mapa'", self.painel)
        self.assertIn("if(name==='mapa'&&window.showMapa)window.showMapa()", self.painel)
        self.assertIn('<section id="mapa-view" hidden>', self.html)
        ordem = [self.html.index(f'<script src="/{n}"') for n in ('i18n.js', 'painel.js', 'processes.js', 'mapa-dados.js', 'mapa-shp.js', 'mapa.js')]
        self.assertEqual(ordem, sorted(ordem))
        self.assertIn('<link rel="stylesheet" href="/mapa.css">', self.html)

    def test_elementos_usados_existem(self):
        ids = set(re.findall(r'\sid="([^"]+)"', self.html))
        usados = set(re.findall(r"el\('([a-z0-9-]+)'\)", self.js))
        self.assertEqual(usados - ids, set(), 'el() aponta para id que não existe no painel')

    def test_estilos_com_escopo(self):
        sem_comentario = re.sub(r'/\*.*?\*/', '', self.css, flags=re.S)
        regras = re.findall(r'([^{}]+)\{[^{}]*\}', re.sub(r'@(media|keyframes)[^{]*\{', '', sem_comentario))
        for regra in regras:
            for seletor in regra.split(','):
                seletor = seletor.strip()
                if not seletor or re.fullmatch(r'(from|to|\d+%)', seletor):
                    continue
                self.assertTrue(seletor.startswith(('#mapa-view', '#mapa-map')), seletor)

    def test_um_mapa_so_e_sem_dado_fora_do_contrato(self):
        self.assertEqual(self.js.count("L.map('mapa-map'"), 1)
        self.assertIn('if(!carregando)carregando=init()', self.js)
        # o painel lê só o que a API publica: nenhum caminho de arquivo nem endpoint fora de /api/mapa e /api/atlas
        self.assertIsNone(re.search(r"api\('/(?!mapa|atlas)", self.js))


@unittest.skipUnless(importlib.util.find_spec('fastapi') and importlib.util.find_spec('httpx'),
                     'a API precisa de fastapi e httpx (deploy/requirements-vps.txt)')
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
            c.execute('INSERT INTO users(username,name,password_hash,role,must_change) VALUES (?,?,?,?,?)',
                      ('reader', 'reader', auth.password_hash('long-test-password'), 'user', 0))
        self.client = TestClient(main.app, base_url='https://testserver')

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def test_sem_sessao_nada_sai(self):
        for url in ('/api/mapa/catalogo', '/api/mapa/camadas/minas_ativas', '/api/mapa/tabelas/municipios', '/api/atlas',
                    '/api/atlas/processes'):
            self.assertEqual(self.client.get(url).status_code, 401, url)
            self.assertEqual(self.client.get(url, headers={'Accept-Encoding': 'gzip'}).status_code, 401, url)

    def test_leitor_recebe_so_o_que_o_catalogo_publica(self):
        r = self.client.post('/api/auth/login', json={'username': 'reader', 'password': 'long-test-password'})
        self.assertEqual(r.status_code, 200)
        cat = self.client.get('/api/mapa/catalogo')
        self.assertEqual(cat.status_code, 200)
        self.assertEqual(cat.headers['cache-control'], 'no-store')
        for c in cat.json()['camadas']:
            if c['dados']['formato'] == 'mapa-v1':
                r = self.client.get(c['dados']['endpoint'])
                self.assertEqual(r.status_code, 200, c['id'])
                self.assertEqual(r.json()['n'], c['n_feicoes'])
        self.assertEqual(self.client.get('/api/mapa/tabelas/radar_projetos').status_code, 200)
        for proibido in ('processos', 'catalogo', 'validacao', 'NADA', '..%2Fcatalogo', 'minas_ativas.json'):
            self.assertEqual(self.client.get(f'/api/mapa/camadas/{proibido}').status_code, 404, proibido)
            self.assertEqual(self.client.get(f'/api/mapa/tabelas/{proibido}').status_code, 404, proibido)

    def test_dados_saem_em_gzip_so_para_quem_aceita(self):
        # o nginx da VPS só comprime HTML; a API manda os dados do mapa e do atlas já em gzip
        self.client.post('/api/auth/login', json={'username': 'reader', 'password': 'long-test-password'})
        atlas = ROOT / 'data' / 'atlas'
        arquivos = {'/api/mapa/catalogo': MAPA / 'catalogo.json',
                    '/api/mapa/camadas/litoestratigrafia': MAPA / 'camadas' / 'litoestratigrafia.json',
                    '/api/mapa/tabelas/radar_projetos': MAPA / 'tabelas' / 'radar_projetos.json',
                    '/api/atlas': atlas / 'atlas.json', '/api/atlas/processes': atlas / 'processes.json'}
        for url, arquivo in arquivos.items():
            bruto = arquivo.read_bytes()
            r = self.client.get(url, headers={'Accept-Encoding': 'gzip, deflate, br, zstd'})
            self.assertEqual(r.headers.get('content-encoding'), 'gzip', url)
            self.assertLess(int(r.headers['content-length']), len(bruto), url)
            self.assertEqual(r.content, bruto, url)  # o cliente descompacta, como o navegador
            self.assertEqual(r.headers['vary'], 'Accept-Encoding', url)
            self.assertEqual(r.headers['cache-control'], 'no-store', url)
            for pedido in ('identity', 'gzip;q=0', 'br'):
                r = self.client.get(url, headers={'Accept-Encoding': pedido})
                self.assertIsNone(r.headers.get('content-encoding'), (url, pedido))
                self.assertEqual(r.content, bruto, (url, pedido))

    def test_leitura_do_accept_encoding(self):
        from compressed import accepts_gzip
        for cabecalho, aceita in (('gzip, deflate, br', True), ('GZIP', True), ('br;q=1.0, gzip;q=0.5', True), ('*', True),
                                  ('deflate, *;q=0.1', True), ('', False), ('identity', False), ('br', False),
                                  ('gzip;q=0', False), ('gzip; q=0.0', False), ('*;q=0', False), ('gzip;q=0, *', False),
                                  ('gzip;q=x', False)):
            self.assertIs(accepts_gzip(cabecalho), aceita, cabecalho)


@unittest.skipUnless(all(importlib.util.find_spec(m) for m in ('shapefile', 'shapely', 'openpyxl')),
                     'o gerador precisa de pyshp, shapely e openpyxl')
class GeradorTests(unittest.TestCase):
    def test_dados_publicados_batem_com_o_gerador(self):
        import build_mapa_base as gerador
        cfg = ler(gerador.CATALOGO)
        catalogo, camadas, tabelas, validacao = gerador.montar(cfg)
        self.assertEqual(validacao['erros'], [])
        self.assertEqual(catalogo, ler(MAPA / 'catalogo.json'))
        for cid, pacote in camadas.items():
            self.assertEqual(pacote, ler(MAPA / 'camadas' / f'{cid}.json'), cid)
        for tid, tabela in tabelas.items():
            self.assertEqual(tabela, ler(MAPA / 'tabelas' / f'{tid}.json'), tid)


if __name__ == '__main__':
    unittest.main()
