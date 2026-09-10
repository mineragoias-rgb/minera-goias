import base64,json,struct,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class AtlasTests(unittest.TestCase):
 def test_municipality_transform_and_bounds(self):
  d=json.loads((ROOT/'data/atlas/atlas.json').read_text())
  self.assertEqual(len(d['municipalities']),246)
  self.assertEqual(len({m['code'] for m in d['municipalities']}),246)
  for m in d['municipalities']:
   for ring in m['rings']:
    self.assertEqual(ring[0],ring[-1])
    for lat,lon in ring:
     self.assertTrue(-19.51<lat<-12.38);self.assertTrue(-53.26<lon<-45.89)
  p=d['municipalities'][0]['rings'][0][0]
  self.assertAlmostEqual(p[0],-12.3954-632.5/1006.2*(19.4981-12.3954),places=5)
  self.assertEqual(len(d['dams']),23)
  self.assertAlmostEqual(sum(m['cfem_total'] for m in d['municipalities']),sum(r['valor'] for r in d['cfem_years']),places=2)
  self.assertEqual(len(d['cfem']['linhas']),8)
 def test_encoded_process_integrity_without_holder_data(self):
  p=json.loads((ROOT/'data/atlas/processes.json').read_text())
  def arr(key,fmt):
   b=base64.b64decode(p[key]);return struct.unpack('<'+fmt*(len(b)//struct.calcsize(fmt)),b)
  n=p['n'];self.assertEqual(n,17402)
  self.assertNotIn('nome',p);self.assertNotIn('dNome',p)
  self.assertEqual(len(p['processo'].split('\x01')),n)
  for key,fmt in [('g','B'),('fase','B'),('subs','H'),('area','f')]:self.assertEqual(len(arr(key,fmt)),n)
  xy,starts,owners=arr('xy','H'),arr('ringStart','I'),arr('ringPoly','H')
  self.assertEqual(starts[-1]*2,len(xy));self.assertEqual(len(starts),len(owners)+1)
  self.assertTrue(all(0<=i<n for i in owners))
  self.assertTrue(all(b-a>=3 for a,b in zip(starts,starts[1:])))
 def test_series_units_and_coverage(self):
  d=json.loads((ROOT/'data/atlas/atlas.json').read_text())
  self.assertEqual([r['Ano'] for r in d['cfem_years']],[2022,2023,2024,2025,2026])
  self.assertTrue(all('v' in r for r in d['cfem_comparable']))
  self.assertEqual(d['energy_months'][0]['rotulo'],'2024-04')
  self.assertEqual(d['energy_months'][-1]['rotulo'],'2026-06')
  self.assertNotIn('empresas_ee',d['energy'][0])
