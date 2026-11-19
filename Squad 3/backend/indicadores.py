"""Indicadores municipais (2025) da aba Atlas · Território · Visão do mapa · Indicadores, gerados por scripts/build_indicadores_municipais.py."""
from pathlib import Path
from fastapi import APIRouter,Depends
from fastapi.responses import FileResponse
from auth import reader
router=APIRouter(prefix='/api/indicadores')
DATA=Path(__file__).resolve().parents[2]/'data'/'indicadores'
@router.get('')
def indicadores(user=Depends(reader)):
    return FileResponse(DATA/'indicadores_municipais.json',media_type='application/json',headers={'Cache-Control':'private, max-age=3600'})
