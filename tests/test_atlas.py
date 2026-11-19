"""Retrato do atlas gerado por scripts/build_atlas_base.py a partir da base consolidada do Squad 1 (v17)."""
import base64,importlib.util,json,struct,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tests'));sys.path.insert(0,str(ROOT/'robo'))
import anm_recorte  # noqa: E402
from test_panorama import cfem_bruta  # noqa: E402
SIGMINE=ROOT/'Squad 1/Dados brutos/ANM - SIGMINE/GO.zip'
PLANILHA=ROOT/'Squad 1/Bases consolidadas/documentacao/prototipo_bases_consolidadas_v17.xlsx'
ANOS=[2022,2023,2024,2025,2026]
def atlas():return json.loads((ROOT/'data/atlas/atlas.json').read_text(encoding='utf-8'))
def projetos_aba04():
 """Projetos da aba 04 da planilha (uma feição por projeto no atlas); sem openpyxl, os do próprio pacote."""
 if not importlib.util.find_spec('openpyxl'):return len(atlas()['projects']['rows'])
 import openpyxl
 wb=openpyxl.load_workbook(PLANILHA,read_only=True)
 return sum(1 for r in wb['04_dim_projetos'].iter_rows(values_only=True) if r and str(r[0]).startswith('PRJ_'))
class AtlasTests(unittest.TestCase):
 def test_municipalities_geometry_and_cfem(self):
  d=atlas();mun=d['municipalities']
  self.assertEqual(len(mun),246)
  self.assertEqual(len({m['code'] for m in mun}),246)
  self.assertTrue(all(len(m['code'])==7 and m['code'].startswith('52') for m in mun))
  for m in mun:
   self.assertTrue(m['rings'])
   for ring in m['rings']:
    self.assertEqual(ring[0],ring[-1]);self.assertGreaterEqual(len(ring),4)
    for lat,lon in ring:
     self.assertTrue(-19.51<lat<-12.38);self.assertTrue(-53.26<lon<-45.89)
  self.assertEqual(len(d['dams']),23)
  total=sum(m['cfem_total'] for m in mun)
  self.assertAlmostEqual(total,sum(r['valor'] for r in d['cfem_years']),places=2)
  # conciliado com o arquivo bruto da CFEM, como na base consolidada (aba 14b da planilha); o robô troca o arquivo quando há dado novo
  self.assertAlmostEqual(total,cfem_bruta()[0],places=2)
 def test_yearly_cfem_covers_every_municipality(self):
  d=atlas();por_nome={m['name']:m for m in d['municipalities']}
  self.assertEqual(d['cfem']['anos'],ANOS)
  self.assertEqual({x['Município'] for x in d['cfem']['linhas']},set(por_nome))
  for x in d['cfem']['linhas']:
   self.assertAlmostEqual(sum(x[str(a)] for a in ANOS),por_nome[x['Município']]['cfem_total'],places=2)
 def test_encoded_process_integrity_without_holder_data(self):
  p=json.loads((ROOT/'data/atlas/processes.json').read_text(encoding='utf-8'))
  def arr(key,fmt):
   b=base64.b64decode(p[key]);return struct.unpack('<'+fmt*(len(b)//struct.calcsize(fmt)),b)
  n=p['n'];self.assertEqual(n,len(anm_recorte.processos_sigmine(SIGMINE)))  # processos do SIGMINE em Goiás (aba 03)
  for key in ('nome','dNome','titular','razao_social','company_id'):self.assertNotIn(key,p)
  self.assertEqual(len(p['processo'].split('\x01')),n)
  for key,fmt in [('g','B'),('fase','B'),('subs','H'),('area','f')]:self.assertEqual(len(arr(key,fmt)),n)
  xy,starts,owners=arr('xy','H'),arr('ringStart','I'),arr('ringPoly','H')
  self.assertEqual(starts[-1]*2,len(xy));self.assertEqual(len(starts),len(owners)+1)
  self.assertEqual(set(owners),set(range(n)))  # todo processo tem ao menos um anel
  self.assertTrue(all(b-a>=3 for a,b in zip(starts,starts[1:])))
  self.assertLessEqual(len(p['grupos']),5)  # public/atlas.js tem cinco cores de fase
  self.assertTrue(all(g<len(p['grupos']) for g in arr('g','B')))
  self.assertEqual(sum(r['n'] for r in p['resumo']),n)
 def test_series_units_and_coverage(self):
  d=atlas()
  self.assertEqual([r['Ano'] for r in d['cfem_years']],ANOS)
  self.assertEqual([r['Ano'] for r in d['cfem_comparable']],ANOS)
  self.assertTrue(all(c['v']<=y['valor']+0.01 for c,y in zip(d['cfem_comparable'],d['cfem_years'])))
  self.assertEqual(d['energy_months'][0]['rotulo'],'2024-04')
  self.assertEqual(d['energy_months'][-1]['rotulo'],'2026-06')
  self.assertNotIn('empresas_ee',d['energy'][0])
  self.assertEqual(d['beneficiated'][0]['ano'],2010)
  subs=d['production']['subs']
  self.assertTrue(subs)
  self.assertEqual({s['sub'] for s in subs},set(d['production']['dados']))
  self.assertEqual(sorted(d['meta']['retained_from_artifact']['layers']),['coef','dams','energy','energy_months'])  # o que build_atlas_base.py carrega adiante
 def test_project_and_occurrence_points(self):
  d=atlas();codes={m['code'] for m in d['municipalities']}
  # uma feição por linha das abas 04 (camada CAM_06) e 06 (camada CAM_05) da base consolidada
  for key,n,prefix in (('projects',projetos_aba04(),'PRJ_'),('occurrences',1796,'OCC_')):
   rows=[dict(zip(d[key]['cols'],r)) for r in d[key]['rows']]
   self.assertEqual(len(rows),n);self.assertEqual(len({r['id'] for r in rows}),n)
   self.assertTrue(all(r['id'].startswith(prefix) and r['mun'] in codes for r in rows))
   self.assertTrue(all(-20<r['lat']<-12 and -54<r['lon']<-45 for r in rows))  # alguns projetos cruzam a divisa do estado
  proj=[dict(zip(d['projects']['cols'],r)) for r in d['projects']['rows']]
  self.assertEqual({r['classe'] for r in proj},{'provável','possível','sinal'})
  self.assertFalse(any('***' in str(r['titular'] or '') for r in proj))  # sem CPF mascarado de pessoa física no pacote
  occ=[dict(zip(d['occurrences']['cols'],r)) for r in d['occurrences']['rows']]
  self.assertEqual({r['importancia'] for r in occ},{'Depósito','Ocorrência','Indício','Indeterminado'})
 def test_charts_reconcile_with_the_base(self):
  d=atlas();c=d['charts']
  for key,chart in c.items():
   self.assertIn(chart['type'],('hbar','hstack','stack','group'),key)
   self.assertEqual(len(chart['values']),len(chart['groups']),key)
   self.assertTrue(all(len(v)==len(chart['labels']) for v in chart['values']),key)
  by_year={str(r['Ano']):r['valor']/1e6 for r in d['cfem_years']}
  years=c['cfem_substance_years'];self.assertEqual(years['labels'],[str(a) for a in ANOS])
  for j,y in enumerate(years['labels']):self.assertAlmostEqual(sum(v[j] for v in years['values']),by_year[y],places=4)
  self.assertAlmostEqual(sum(c['cfem_substances']['values'][0]),by_year['2025'],places=4)
  cover=c['operation_coverage']
  for j in range(len(cover['labels'])):self.assertAlmostEqual(sum(v[j] for v in cover['values']),100,places=3)
  self.assertEqual(sum(map(sum,c['projects_minerals']['values'])),len(d['projects']['rows']))
  self.assertGreaterEqual(sum(map(sum,c['occurrences_substances']['values'])),1796)  # com várias substâncias, conta em cada uma
  conc=c['cfem_concentration']['values']
  self.assertTrue(all(0<v<=100 for g in conc for v in g));self.assertTrue(all(a<=b for g in conc for a,b in zip(g,g[1:])))
