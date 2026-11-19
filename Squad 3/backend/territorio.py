"""Aba Território e emissões: o relatório "Mineração e Cerrado em Goiás" do Squad 2 e a camada de risco ambiental dos projetos.

Os arquivos ficam em Squad 2/mineracao_cerrado/ e saem só por aqui, atrás da sessão (reader): trazem nome de projeto e de empresa
titular, e por isso não vão para public/, que o Nginx serve sem login. O relatório é uma página autocontida (scripts e estilos
embutidos, fontes do Google): vai para um iframe do painel com uma CSP que só libera isso, e o geojson sai como download.
"""
from pathlib import Path
from fastapi import APIRouter,Depends
from fastapi.responses import FileResponse
from auth import reader

router=APIRouter(prefix='/api/territorio')
PASTA=Path(__file__).resolve().parents[2]/'Squad 2'/'mineracao_cerrado'
RELATORIO=PASTA/'relatorio_mineracao_cerrado_GO.html'
RISCO=PASTA/'GO_radar_risco_ambiental.geojson'
CSP=("default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline' https://fonts.googleapis.com; "
     "font-src https://fonts.gstatic.com; img-src data:; frame-ancestors 'self'; base-uri 'none'; form-action 'none'")


@router.get('/relatorio')
def relatorio(user=Depends(reader)):
    return FileResponse(RELATORIO,media_type='text/html; charset=utf-8',
                        headers={'Content-Security-Policy':CSP,'X-Frame-Options':'SAMEORIGIN','Cache-Control':'private, max-age=3600'})


@router.get('/risco.geojson')
def risco(user=Depends(reader)):
    return FileResponse(RISCO,media_type='application/geo+json',filename='GO_radar_risco_ambiental.geojson',
                        headers={'Cache-Control':'private, max-age=3600'})
