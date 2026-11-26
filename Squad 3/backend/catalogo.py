"""Authenticated catalogue of the data bases the system uses, rebuilt by scripts/build_catalogo_painel.py.

It names the sources and where each base lives in the repository, so it stays behind the reader dependency like the atlas, the panorama
and the Empresas tab — never under public/, which Nginx serves without a session.
"""
import json
import os
import tempfile
import zipfile
from pathlib import Path
from fastapi import APIRouter,Depends,HTTPException
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask
from auth import reader
router=APIRouter(prefix='/api/catalogo')
REPO=Path(__file__).resolve().parents[2]
DATA=REPO/'data'/'catalogo'
@router.get('')
def catalogo(user=Depends(reader)):
    return FileResponse(DATA/'catalogo.json',media_type='application/json')

# Download de uma base, para qualquer usuário logado. Só sai o que o catálogo lista para aquela base (nunca um caminho vindo do
# pedido); um arquivo vai como está, vários vão num .zip montado na hora.
@router.get('/baixar/{base_id}')
def baixar(base_id:str,user=Depends(reader)):
    bases=json.loads((DATA/'catalogo.json').read_text(encoding='utf-8'))['bases']
    base=next((b for b in bases if b['id']==base_id),None)
    if not base or not base.get('download'):
        raise HTTPException(404,'Base sem arquivo para baixar.')
    arquivos=[]
    for rel in base['download']['arquivos']:
        caminho=(REPO/rel).resolve()
        if not caminho.is_relative_to(REPO.resolve()) or not caminho.is_file():
            raise HTTPException(404,'Arquivo da base não encontrado.')
        arquivos.append((rel,caminho))
    if len(arquivos)==1:
        return FileResponse(arquivos[0][1],filename=arquivos[0][1].name)
    tmp=tempfile.NamedTemporaryFile(suffix='.zip',delete=False)
    tmp.close()
    # dentro do .zip, cada arquivo fica no caminho relativo à pasta comum a todos (subpastas preservadas, sem pastas internas acima)
    raiz=Path(os.path.commonpath([str(Path(r).parent) for r,_ in arquivos]))
    with zipfile.ZipFile(tmp.name,'w',zipfile.ZIP_DEFLATED) as z:
        for rel,caminho in arquivos:
            z.write(caminho,Path(rel).relative_to(raiz).as_posix())
    return FileResponse(tmp.name,filename=f'{base_id}.zip',media_type='application/zip',
                        background=BackgroundTask(lambda:Path(tmp.name).unlink(missing_ok=True)))
