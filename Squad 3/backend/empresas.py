"""Authenticated snapshot for the Empresas tab, rebuilt by scripts/build_empresas_base.py.

It names companies and pairs them with CCEE load, so it stays behind the reader dependency like the atlas and the panorama —
never under public/, which Nginx serves without a session.
"""
from pathlib import Path
from fastapi import APIRouter,Depends
from fastapi.responses import FileResponse
from auth import reader
router=APIRouter(prefix='/api/empresas')
DATA=Path(__file__).resolve().parents[2]/'data'/'empresas'
@router.get('')
def empresas(user=Depends(reader)):
    return FileResponse(DATA/'empresas.json',media_type='application/json')


@router.get('/mapa')
def mapa_empresas(user=Depends(reader)):
    """Onde cada empresa minera e o perfil dela (CFEM, CCEE, títulos, notícias): scripts/build_mapa_empresas.py."""
    return FileResponse(DATA/'mapa_empresas.json',media_type='application/json')
