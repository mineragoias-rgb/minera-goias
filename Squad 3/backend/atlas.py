"""Authenticated, immutable artifact snapshots; separate from live MySQL ingestion.
Sent gzipped when the browser accepts it (compressed.py)."""
from pathlib import Path
from fastapi import APIRouter,Depends,Request
from auth import reader
from compressed import json_file
router=APIRouter(prefix='/api/atlas')
DATA=Path(__file__).resolve().parents[2]/'data'/'atlas'
@router.get('')
def atlas(request:Request,user=Depends(reader)):
    return json_file(request,DATA/'atlas.json')
@router.get('/processes')
def processes(request:Request,user=Depends(reader)):
    return json_file(request,DATA/'processes.json')
