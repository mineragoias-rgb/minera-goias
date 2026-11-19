# -*- coding: utf-8 -*-
"""Recorte de uma camada do P3M pelo limite de Goiás — as regras do `Squad 1/P3M/Recortado pelo polígono de Goiás`.

- Pontos: ficam os que estão dentro ou na divisa de Goiás.
- Linhas e polígonos: o que está inteiro dentro fica como veio; o que cruza a divisa é cortado no limite (como o Recortar do
  QGIS). Atributos não mudam.
- Polígono inválido na origem é corrigido (`make_valid`) antes do recorte, mantendo só a parte poligonal.
- Fiapo de divisa: polígono cujo pedaço em Goiás tem menos de 1% da área original e menos de 10 km² sai (área medida em
  SIRGAS 2000 / Brazil Polyconic, EPSG:5880).
- Saída em shapefile com .cpg = UTF-8, no sistema de coordenadas da origem.

Conferido contra os recortados do repositório (feitos em 21/10/2026): das 155 camadas de um zip só, 154 saem com os mesmos bytes e
uma (Uso Sustentável) com a mesma geometria e as partes de um polígono em outra ordem; os fiapos são os mesmos do índice.
tests/test_robo.py refaz parte disso a cada execução.
"""
import io
import tempfile
import warnings
import zipfile
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import pyogrio
import shapely

CRS_AREA = "EPSG:5880"
FIAPO_FRACAO = 0.01
FIAPO_M2 = 10e6

POLIGONOS = ("Polygon", "MultiPolygon")
LINHAS = ("LineString", "MultiLineString")


def limite(caminho_zip):
    g = gpd.read_file(f"zip://{caminho_zip}")
    go = shapely.union_all(g.geometry.values)
    shapely.prepare(go)
    return go, g.crs


def ler_zip(caminho):
    """Todos os shapefiles do zip numa tabela só (em UTF-8, que é como o P3M grava)."""
    with zipfile.ZipFile(caminho) as z:
        shps = sorted(n for n in z.namelist() if n.lower().endswith(".shp"))
    partes = [gpd.read_file(f"zip://{caminho}!{s}", encoding="utf-8") for s in shps]
    gdf = pd.concat(partes, ignore_index=True) if len(partes) > 1 else partes[0]
    return gpd.GeoDataFrame(gdf, geometry="geometry", crs=partes[0].crs), Path(shps[0]).stem


def _parte(g, tipos):
    if g is None or g.is_empty:
        return None
    if g.geom_type in tipos:
        return g
    partes = [p for p in getattr(g, "geoms", []) if p.geom_type in tipos]
    return shapely.union_all(partes) if partes else None


def recortar(gdf, go, crs_area=CRS_AREA, fracao=FIAPO_FRACAO, m2=FIAPO_M2, crs_saida=None):
    """(recortado, fiapos removidos). Com `crs_saida`, a camada vai para esse sistema antes do recorte (o recorte do
    repositório grava tudo em SIRGAS 2000, o sistema do limite de Goiás; de WGS 84 para SIRGAS 2000 a transformação é nula)."""
    gdf = gdf.copy()
    if crs_saida is not None and gdf.crs is not None and gdf.crs != crs_saida:
        gdf = gdf.to_crs(crs_saida)
    geom = gdf.geometry
    tipos = geom.geom_type.dropna()
    tipo = tipos.iloc[0] if len(tipos) else None
    if tipo in ("Point", "MultiPoint"):
        return gdf[geom.intersects(go).values].reset_index(drop=True), 0
    if tipo in POLIGONOS:
        geom = gpd.GeoSeries([_parte(shapely.make_valid(g), POLIGONOS) if g is not None and not g.is_valid else g for g in geom],
                             crs=gdf.crs, index=gdf.index)
    original = geom.copy()
    dentro = geom.within(go).values
    cruza = ~dentro & geom.intersects(go).values
    novas = list(geom.values)
    for i in np.flatnonzero(cruza):
        c = novas[i].intersection(go)
        novas[i] = _parte(c, POLIGONOS if tipo in POLIGONOS else LINHAS)
    gdf = gdf.set_geometry(gpd.GeoSeries(novas, crs=gdf.crs, index=gdf.index))
    vazio = np.array([g is None or g.is_empty for g in novas])
    manter = (dentro | cruza) & ~vazio
    fiapos = 0
    if tipo in POLIGONOS:
        idx = np.flatnonzero(cruza & manter)
        if len(idx):
            a_orig = gpd.GeoSeries(original.values[idx], crs=gdf.crs).to_crs(crs_area).area.values
            a_go = gpd.GeoSeries(np.array(novas, dtype=object)[idx], crs=gdf.crs).to_crs(crs_area).area.values
            fiapo = (a_go < fracao * a_orig) & (a_go < m2)
            fiapos = int(fiapo.sum())
            manter[idx[fiapo]] = False
    return gdf[manter].reset_index(drop=True), fiapos


def gravar_zip(gdf, base, destino):
    """Shapefile em UTF-8 (.cpg) dentro de um zip, membros em ordem alfabética, como os recortados do repositório."""
    with tempfile.TemporaryDirectory() as tmp:
        shp = Path(tmp) / f"{base}.shp"
        with warnings.catch_warnings():  # datas viram texto no shapefile ("1997/11/27 00:00:00"), como no recorte do repositório
            warnings.simplefilter("ignore", RuntimeWarning)
            pyogrio.write_dataframe(gdf, shp, driver="ESRI Shapefile", encoding="UTF-8")
        with zipfile.ZipFile(destino, "w", zipfile.ZIP_DEFLATED) as z:
            for p in sorted(Path(tmp).iterdir()):
                z.write(p, p.name)


def recortar_zip(original, destino, go, crs_saida=None, **kw):
    """Recorta o zip `original` e grava `destino` (só quando sobra alguma feição). Devolve (registros na origem, em Goiás, fiapos)."""
    gdf, base = ler_zip(original)
    rec, fiapos = recortar(gdf, go, crs_saida=crs_saida, **kw)
    if len(rec):
        gravar_zip(rec, base, destino)
    return len(gdf), len(rec), fiapos


def conteudo(caminho):
    """Atributos e geometria de um zip, para comparar dois recortes."""
    gdf, _ = ler_zip(caminho)
    return gdf


def mesmo_conteudo(a, b, tolerancia=1e-9):
    """True quando dois zips têm as mesmas feições, na mesma ordem, com os mesmos atributos e geometria."""
    ga, gb = conteudo(a), conteudo(b)
    if len(ga) != len(gb) or list(ga.columns) != list(gb.columns):
        return False
    for c in ga.columns:
        if c == ga.geometry.name:
            continue
        if not (ga[c].astype(str).values == gb[c].astype(str).values).all():
            return False
    return bool(shapely.equals_exact(ga.geometry.values, gb.geometry.values, tolerance=tolerancia).all())


def zip_para_bytes(caminho):
    return io.BytesIO(Path(caminho).read_bytes())
