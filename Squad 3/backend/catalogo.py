"""Authenticated catalogue of the data bases the system uses, rebuilt by scripts/build_catalogo_bases.py.

It names the sources and where each base lives in the repository, so it stays behind the reader dependency like the atlas, the panorama
and the Empresas tab — never under public/, which Nginx serves without a session.
"""
from pathlib import Path
from fastapi import APIRouter,Depends
from fastapi.responses import FileResponse
from auth import reader
router=APIRouter(prefix='/api/catalogo')
DATA=Path(__file__).resolve().parents[2]/'data'/'catalogo'
@router.get('')
def catalogo(user=Depends(reader)):
    return FileResponse(DATA/'catalogo.json',media_type='application/json')
