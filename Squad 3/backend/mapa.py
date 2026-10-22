"""Authenticated data for the Mapa Mineral de Goiás, rebuilt by scripts/build_mapa_base.py into data/mapa/.

Like the atlas, it stays behind the reader dependency (titular names, company links) and never under public/. Only ids that the
catalogue publishes are served, so a request cannot reach any other file. Layers that already exist in the atlas are not copied:
the catalogue points them to /api/atlas and /api/atlas/processes. Files go out gzipped when the browser accepts it (compressed.py).
"""
import json
import re
from functools import lru_cache
from pathlib import Path
from fastapi import APIRouter,Depends,HTTPException,Request
from auth import reader
from compressed import json_file
router=APIRouter(prefix='/api/mapa')
DATA=Path(__file__).resolve().parents[2]/'data'/'mapa'
ID=re.compile(r'[a-z0-9_]{1,40}')

@lru_cache(maxsize=1)
def published():
    """Ids served from data/mapa. Read once: every deploy is a new release directory and a restart (deploy/deploy.sh)."""
    cat=json.loads((DATA/'catalogo.json').read_text(encoding='utf-8'))
    return {'camadas':{c['id'] for c in cat['camadas'] if c['dados']['formato']=='mapa-v1'},'tabelas':{t['id'] for t in cat['tabelas']}}

def serve(request,kind,ident):
    if not ID.fullmatch(ident) or ident not in published()[kind]:
        raise HTTPException(status_code=404,detail='Not found')
    return json_file(request,DATA/kind/f'{ident}.json')

@router.get('/catalogo')
def catalogo(request:Request,user=Depends(reader)):
    return json_file(request,DATA/'catalogo.json')

@router.get('/camadas/{camada}')
def camada(camada:str,request:Request,user=Depends(reader)):
    return serve(request,'camadas',camada)

@router.get('/tabelas/{tabela}')
def tabela(tabela:str,request:Request,user=Depends(reader)):
    return serve(request,'tabelas',tabela)
