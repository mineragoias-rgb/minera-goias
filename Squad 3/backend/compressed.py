"""Data files of the Mapa Mineral and the atlas, gzipped when the browser accepts it (9.3 MB of JSON becomes 4.2 MB).

The VPS nginx only compresses text/html and is not updated by the deploy (deploy/README.md), so the API does it. Each file is
compressed once per process and kept in memory: every deploy is a new release directory and a restart (deploy/deploy.sh), so a
file never changes under a running API. Only files the routes already chose are cached, never a path taken from the request.
nginx passes the gzipped body through untouched, since it never compresses a response that already has Content-Encoding.
"""
import gzip
from functools import lru_cache
from fastapi.responses import FileResponse,Response

@lru_cache(maxsize=None)
def gzipped(path):
    return gzip.compress(path.read_bytes(),compresslevel=6,mtime=0)

def accepts_gzip(header):
    """Accept-Encoding with gzip or * at a q above zero; an explicit gzip entry wins over * (RFC 9110, 12.5.3)."""
    weights={}
    for item in header.lower().split(','):
        name,*params=[p.strip() for p in item.split(';')]
        q=1.0
        for p in params:
            if p.startswith('q='):
                try:
                    q=float(p[2:])
                except ValueError:
                    q=0.0
        weights.setdefault(name,q)
    return weights.get('gzip',weights.get('*',0.0))>0

def json_file(request,path):
    headers={'Vary':'Accept-Encoding'}
    if not accepts_gzip(request.headers.get('accept-encoding','')):
        return FileResponse(path,media_type='application/json',headers=headers)
    return Response(gzipped(path),media_type='application/json',headers={**headers,'Content-Encoding':'gzip'})
