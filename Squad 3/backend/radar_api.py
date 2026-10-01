"""Radar: what is already authorised, what is under analysis, and what is still to open.

Reads the cadastral snapshot for the phase picture and the availability rounds from
the imported sources. News comes from the prototype collector when it is installed;
when it is not, the endpoint says so instead of pretending the section is empty.
"""
import base64
import json
import os
import sqlite3
from collections import Counter
from pathlib import Path

from fastapi import APIRouter, Depends
from auth import reader

router = APIRouter(prefix='/api/radar')
DATA = Path(__file__).resolve().parents[2] / 'data' / 'atlas'
ROUNDS_PATH = 'Squad 1/dados/ResultadoRodadaDisponibilidade (1).csv'
NEWS_DB = os.getenv('NEWS_DB_PATH', '/var/lib/minera-goias-news/radar.sqlite')
# The collector publishes its result as files in the repository, so the deploy carries
# them here on its own. They sit under public/ because the browser fetches the monthly
# archives straight from /data/noticias/meses/ when someone asks for older news, and
# only public/ is served by Nginx. The SQLite below stays as a fallback for a
# collector installed on this machine.
NEWS_JSON = Path(__file__).resolve().parents[2] / 'public' / 'data' / 'noticias' / 'latest.json'

connection_factory = None
_phases = {'mtime': None, 'value': None}
_news_file = {'mtime': None, 'value': None}

# Which phases mean the holder may already extract, which are still being decided,
# and which are areas the ANM has put back on the table.
CONFIRMED = {'CONCESSÃO DE LAVRA', 'LAVRA GARIMPEIRA', 'LICENCIAMENTO', 'REGISTRO DE EXTRAÇÃO'}
OPENING = {'DISPONIBILIDADE', 'APTO PARA DISPONIBILIDADE'}
# Rounds still to be decided; 'Livre' is an area with no winner so far.
ROUND_FUTURE = {'Aguardando Leilão', 'Livre'}


def query(sql, args=()):
    conn = connection_factory()
    try:
        with conn.cursor() as cur:
            cur.execute(sql, args)
            return cur.fetchall()
    finally:
        conn.close()


def phase_counts():
    """Count the cadastral phases from the snapshot, cached until the file changes."""
    path = DATA / 'processes.json'
    mtime = path.stat().st_mtime
    if _phases['mtime'] == mtime:
        return _phases['value']
    packet = json.loads(path.read_text(encoding='utf-8'))
    codes = base64.b64decode(packet['fase'])
    names = packet['dFase']
    counts = Counter(names[c] if c < len(names) else '' for c in codes)
    buckets = {'confirmado': [], 'analise': [], 'abrindo': []}
    for name, total in counts.most_common():
        label = (name or '').strip()
        if not label or label == 'DADO NÃO CADASTRADO':
            continue
        key = 'confirmado' if label in CONFIRMED else 'abrindo' if label in OPENING else 'analise'
        buckets[key].append({'fase': label, 'processos': total})
    value = {k: {'total': sum(x['processos'] for x in v), 'fases': v} for k, v in buckets.items()}
    _phases.update(mtime=mtime, value=value)
    return value


def rounds():
    """Availability rounds for Goiás, filtered in SQL so the API reads 3.632 rows, not 31.841."""
    rows = query(
        "SELECT values_json FROM ingest_current_rows WHERE path=%s AND row_role='data' "
        "AND JSON_UNQUOTE(JSON_EXTRACT(values_json,'$.unidadefederacao'))=%s",
        (ROUNDS_PATH, 'Goiás'))
    records = [json.loads(r['values_json']) for r in rows]
    situations = Counter(str(r.get('situacao') or '—') for r in records)
    upcoming = [r for r in records if str(r.get('situacao')) in ROUND_FUTURE]
    by_municipality = Counter(str(r.get('municipio') or '—') for r in upcoming)
    regimes = Counter(str(r.get('regimedisponibilidade') or '—') for r in upcoming)
    return {
        'total': len(records),
        'situacoes': [{'label': k, 'value': v} for k, v in situations.most_common()],
        'futuras': len(upcoming),
        'municipios': len(by_municipality),
        'top_municipios': [{'label': k, 'value': v} for k, v in by_municipality.most_common(10)],
        'regimes': [{'label': k, 'value': v} for k, v in regimes.most_common()],
        'fonte': ROUNDS_PATH,
    }


def news_from_repo():
    """Read the packet the collector committed, cached until the file changes.

    Returns None when the file is absent or unreadable, so the caller falls back to a
    locally installed collector instead of reporting the section as broken.
    """
    try:
        # The path is part of the key: the module constant can be pointed elsewhere,
        # and two different files can share a modification time.
        key = (str(NEWS_JSON), NEWS_JSON.stat().st_mtime)
    except OSError:
        return None
    if _news_file['mtime'] == key:
        return _news_file['value']
    try:
        value = json.loads(NEWS_JSON.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None
    if not isinstance(value, dict) or not isinstance(value.get('itens'), list):
        return None
    value.setdefault('disponivel', True)
    value.setdefault('tendencias', [])
    _news_file.update(mtime=key, value=value)
    return value


def news(limit=12):
    """The collector is a separate service; report plainly when it is not installed."""
    packet = news_from_repo()
    if packet is not None:
        return {**packet, 'itens': packet['itens'][:limit]}
    path = Path(NEWS_DB)
    if not path.exists():
        return {'disponivel': False, 'motivo': 'coletor_nao_instalado', 'itens': [], 'tendencias': []}
    conn = sqlite3.connect(f'file:{path}?mode=ro', uri=True, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        # Regional stories first: they are the ones that bear on Goias.
        items = conn.execute('''SELECT i.title, i.link, i.published_at, i.first_seen, i.regional,
            i.regiao_termo, s.name AS fonte, s.escopo
            FROM news_items i LEFT JOIN news_sources s ON s.source_id=i.source_id
            ORDER BY i.regional DESC, COALESCE(i.published_at, i.first_seen) DESC LIMIT ?''',
            (limit,)).fetchall()
        regional_total = conn.execute('SELECT COUNT(*) FROM news_items WHERE regional=1').fetchone()[0]
        total = conn.execute('SELECT COUNT(*) FROM news_items').fetchone()[0]
        trends = conn.execute('''SELECT period, commodity, items, up, down, price_points, score, verdict
            FROM news_trends ORDER BY period DESC, commodity LIMIT 40''').fetchall()
        run = conn.execute("SELECT finished_at, status FROM news_runs WHERE finished_at IS NOT NULL "
                           "ORDER BY started_at DESC LIMIT 1").fetchone()
    except sqlite3.DatabaseError:
        return {'disponivel': False, 'motivo': 'banco_ilegivel', 'itens': [], 'tendencias': []}
    finally:
        conn.close()
    return {
        'disponivel': True,
        'atualizado_em': run['finished_at'] if run else None,
        'ultima_execucao': run['status'] if run else None,
        'itens': [dict(row) for row in items],
        'tendencias': [dict(row) for row in trends],
        'regionais': regional_total,
        'total': total,
    }


@router.get('')
def radar(u=Depends(reader)):
    return {
        'fases': phase_counts(),
        'rodadas': rounds(),
        # Enough stories for the panel to filter by substance and by region on the
        # client. Twelve only ever filled the list, leaving nothing to narrow.
        'noticias': news(180),
        'nota': 'Fases e rodadas vêm do cadastro e dos editais da ANM, não de previsão. '
                'Uma área em disponibilidade é uma área que pode ser requerida, não um projeto anunciado.',
    }
