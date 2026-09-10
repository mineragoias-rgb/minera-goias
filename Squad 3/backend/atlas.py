"""Authenticated, immutable artifact snapshots; separate from live MySQL ingestion."""
from pathlib import Path
from fastapi import APIRouter,Depends
from fastapi.responses import FileResponse
from auth import reader
router=APIRouter(prefix='/api/atlas')
DATA=Path(__file__).resolve().parents[2]/'data'/'atlas'
@router.get('')
def atlas(user=Depends(reader)):
    return FileResponse(DATA/'atlas.json',media_type='application/json')
@router.get('/processes')
def processes(user=Depends(reader)):
    return FileResponse(DATA/'processes.json',media_type='application/json')
