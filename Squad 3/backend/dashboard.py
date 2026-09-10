"""Read-only visual summaries from the current imported versions."""
import json
from collections import Counter
from fastapi import APIRouter, Depends, Query
from auth import reader

router=APIRouter(prefix='/api')
connection_factory=None

def query(sql,args=()):
    conn=connection_factory()
    try:
        with conn.cursor() as cur:
            cur.execute(sql,args)
            return cur.fetchall()
    finally:
        conn.close()

@router.get('/public/summary')
def summary():
    counts=query('''SELECT COUNT(DISTINCT f.file_id) files, COUNT(d.dataset_id) datasets,
    COALESCE(SUM(d.data_row_count),0) records FROM ingest_files f
    JOIN ingest_datasets d ON d.version_id=f.current_version WHERE f.active=1''')[0]
    run=query('SELECT finished_at FROM ingest_runs WHERE status=%s ORDER BY started_at DESC LIMIT 1',('success',))
    return {**counts,'updated_at':run[0]['finished_at'] if run else None}

@router.get('/dashboard')
def dashboard(year: int=Query(default=2025,ge=2024,le=2026), activity: str=Query(default='',max_length=150), u=Depends(reader)):
    path=f'Squad 1/dados/CCEE/parcela_carga_consumo_{year}_GO.csv'
    rows=query('''SELECT values_json FROM ingest_current_rows WHERE path=%s AND row_role='data' ''',(path,))
    values=[json.loads(r['values_json']) for r in rows]
    activities=sorted({str(r.get('ramo_atividade') or 'Não informado') for r in values})
    selected=[r for r in values if not activity or str(r.get('ramo_atividade') or 'Não informado')==activity]
    months=Counter(str(r.get('mes_referencia') or 'Não informado') for r in selected)
    cities=Counter(str(r.get('cidade') or 'Não informado') for r in selected)
    sectors=Counter(str(r.get('ramo_atividade') or 'Não informado') for r in selected)
    datasets=query('''SELECT f.path,f.status,d.sheet_name,d.data_row_count,d.warnings_json,v.imported_at
        FROM ingest_files f JOIN ingest_datasets d ON d.version_id=f.current_version
        JOIN ingest_versions v ON v.version_id=f.current_version WHERE f.active=1 ORDER BY f.path,d.sheet_name''')
    for d in datasets:
        d['warnings']=json.loads(d.pop('warnings_json') or '{}')
    return {'summary':summary(),'year':year,'activity':activity,'activities':activities,
        'records':len(selected),'cities':len(cities),'months':[{'label':k,'value':v} for k,v in sorted(months.items())],
        'municipalities':[{'label':k,'value':v} for k,v in cities.most_common(10)],
        'sectors':[{'label':k,'value':v} for k,v in sectors.most_common(8)],
        'source':path,'datasets':datasets,
        'note':'Contagem de registros de parcelas de carga da CCEE em Goiás, incluindo atividades não minerais. Não representa produção mineral nem consumo em MWh. Fontes importadas ainda em validação.'}
