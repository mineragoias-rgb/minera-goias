"""Authenticated snapshots for the Empresas tab.

- /api/empresas: production × CCEE load × coefficient, rebuilt by scripts/build_empresas_base.py.
- /api/empresas/atlas: the Atlas Empresarial (company index keyed by CNPJ root, ANM claims, CFEM, CCEE, projects, news), rebuilt by
  scripts/build_atlas_empresas.py. Sent gzipped when the browser accepts it (compressed.py).

Both name companies and pair them with CCEE load, so they stay behind the reader dependency like the atlas and the panorama —
never under public/, which Nginx serves without a session.
"""
from pathlib import Path
from fastapi import APIRouter,Depends,Request
from fastapi.responses import FileResponse
from auth import reader
from compressed import json_file
router=APIRouter(prefix='/api/empresas')
DATA=Path(__file__).resolve().parents[2]/'data'/'empresas'
@router.get('')
def empresas(user=Depends(reader)):
    return FileResponse(DATA/'empresas.json',media_type='application/json')


@router.get('/mapa')
def mapa_empresas(user=Depends(reader)):
    """Onde cada empresa minera e o perfil dela (CFEM, CCEE, títulos, notícias): scripts/build_mapa_empresas.py."""
    return FileResponse(DATA/'mapa_empresas.json',media_type='application/json')


@router.get('/atlas')
def atlas_empresas(request:Request,user=Depends(reader)):
    return json_file(request,DATA/'atlas_empresas.json')
