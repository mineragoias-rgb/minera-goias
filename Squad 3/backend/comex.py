"""Authenticated foreign-trade base for the critical minerals of Goiás, rebuilt by scripts/build_comex_base.py.

Comex Stat is public data, but this package joins it to the project's own mineral vocabulary and to the operations named in
the other bases, so it stays behind the reader dependency like the atlas, the panorama, the Empresas tab and the catalogue —
never under public/, which Nginx serves without a session.
"""
from pathlib import Path
from fastapi import APIRouter,Depends
from fastapi.responses import FileResponse
from auth import reader
router=APIRouter(prefix='/api/comex')
DATA=Path(__file__).resolve().parents[2]/'data'/'comex'
@router.get('')
def comex(user=Depends(reader)):
    return FileResponse(DATA/'comex.json',media_type='application/json')
