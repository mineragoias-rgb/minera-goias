"""Authenticated snapshot for the energy price tab, rebuilt by scripts/build_precos_energia.py."""
from pathlib import Path
from fastapi import APIRouter,Depends
from fastapi.responses import FileResponse
from auth import reader
router=APIRouter(prefix='/api/precos')
DATA=Path(__file__).resolve().parents[2]/'data'/'precos'
@router.get('')
def precos(user=Depends(reader)):
    return FileResponse(DATA/'precos.json',media_type='application/json')
