"""Extract only selected data, never execute source HTML. Usage: python scripts/extract_atlas.py input.html"""
import base64,hashlib,json,re,sys
from pathlib import Path

def extract(source,target):
    raw=Path(source).read_bytes()
    match=re.search(r'<script[^>]*id="payload"[^>]*>(.*?)</script>',raw.decode('utf-8'),re.S)
    if not match:raise ValueError('Missing JSON payload')
    d=json.loads(match[1]);g=d['mapa'];municipalities=[]
    for m in g['mun']:
        # Source uses only SVG absolute M + coordinate pairs + Z, linear lon/lat projection.
        if re.sub(r'[MmZz\d.,\s\-+]','',m['d']):raise ValueError('Unsupported SVG path')
        rings=[]
        for segment in re.findall(r'M([^Z]+)Z',m['d']):
            nums=[float(x) for x in re.findall(r'[-+]?\d+(?:\.\d+)?',segment)]
            if len(nums)%2:raise ValueError('Unpaired coordinates')
            ring=[[round(g['lat1']-y/g['h']*(g['lat1']-g['lat0']),6),
                   round(g['lon0']+x/g['w']*(g['lon1']-g['lon0']),6)] for x,y in zip(nums[::2],nums[1::2])]
            if len(ring)<4:raise ValueError('Invalid ring')
            if ring[0]!=ring[-1]:ring.append(ring[0])
            rings.append(ring)
        if not rings:raise ValueError('Missing municipality geometry')
        municipalities.append({'code':m['cod'],'name':m['nome'],'rings':rings,'processes':m['proc'],'cfem_total':m['cfem']})
    p=d['proc']
    # Holders and owner dictionary deliberately omitted: visualization needs only process metadata.
    proc={k:p[k] for k in ['n','xy','ringStart','ringPoly','g','fase','subs','area','processo','dFase','dSubs','grupos','resumo']}
    proc['bounds']={k:g[k] for k in ['lon0','lon1','lat0','lat1']}
    packet={'meta':{'artifact':'eliel.html','sha256':hashlib.sha256(raw).hexdigest(),
      'integrated_on':'2026-09-10','status':'snapshot_unvalidated',
      'note':'Retrato do artefato recebido; não é uma consulta em tempo real à ANM, SIGBM ou CCEE. Geometrias simplificadas/quantizadas preservadas do arquivo. Não usar como limite cadastral.',
      'sources':['ANM / CFEM','Anuário Mineral Brasileiro','Cadastro mineiro','SIGBM','CCEE'],
      'periods':{'cfem':'2022–2026; 2026 até julho','production':'2025','energy':'abril/2024–junho/2026','dams':'Data da extração não informada no artefato','processes':'Data da extração não informada no artefato'}},
      'municipalities':municipalities,'cfem':d['cfem_mun_ano'],'production':d['mapa_prod'],
      'energy':[{k:v for k,v in c.items() if k!='empresas_ee'} for c in d['mapa_coef']],
      'dams':d['barragens'],'cfem_years':d['cfem_ano'],'cfem_comparable':d['cfem_jan_jul'],
      'energy_months':d['ee_mensal'],'beneficiated':d['prod_benef'],'investment':d['invest_ano']}
    target=Path(target);target.mkdir(parents=True,exist_ok=True)
    for name,obj in [('atlas.json',packet),('processes.json',proc)]:
        (target/name).write_text(json.dumps(obj,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    print('Extracted',len(municipalities),'municipalities,',p['n'],'process polygons,',len(d['barragens']),'dams')
if __name__=='__main__':extract(sys.argv[1],Path(__file__).resolve().parents[1]/'data/atlas')
