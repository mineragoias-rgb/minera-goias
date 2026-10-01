#!/usr/bin/env python3
"""News radar: collects headlines, stores them with provenance and reads direction
signals out of the wording. It never states a price series of its own - what it
produces is evidence about what the press is saying, dated and countable.

Successor to news/radar.py. Same architecture, four defects fixed - see
RELATORIO_REVISAO.md for the evidence behind each one:

  1. Commodity matching is whole-word now. 'Tesouro Direto tem alta' used to file
     a gold signal, because 'ouro' sits inside 'tesouro'.
  2. Browser user-agent. The old one was refused with 403 by mining.com, taking
     seven international sources down with it.
  3. gzip is decoded. G1 compresses intermittently, so the old fetcher failed on
     roughly two runs out of three and looked fine on the third.
  4. Source metadata is refreshed on every run, and 'tema' reaches the database,
     so editing feeds.json actually changes what the page can filter on.
"""
import argparse
import gzip
import hashlib
import json
import re
import sqlite3
import sys
import unicodedata
import urllib.error
import urllib.request
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

RADAR_VERSION = '0.2'
# No single agent gets the whole list. Measured on 19/09/2026:
#   mining.com                        browser 200, robot 403
#   mining-technology.com             browser 403, robot 200
#   power-technology.com              browser 403, robot 200
# So fetch() tries the browser agent and falls back to the robot one on refusal.
USER_AGENT = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
              '(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36')
FALLBACK_USER_AGENT = 'minera-goias-radar/0.2 (+https://github.com/mineragoias-rgb/minera-goias)'
REFUSAL_CODES = (401, 403, 406, 429)
MAX_FEED_BYTES = 8 * 1024 * 1024
# Currency, amount and - when the text gives one - the unit the amount is quoted in.
PRICE = re.compile(
    r'(?P<currency>R\$|US\$|USD|EUR|CNY|\$|€|¥)\s*'
    r'(?P<amount>\d{1,3}(?:[.\s]\d{3})*(?:,\d+)?|\d+(?:\.\d+)?)'
    r'\s*(?P<scale>mil|milh(?:ao|ão|oes|ões)|bilh(?:ao|ão|oes|ões)|thousand|million|billion)?'
    r'\s*(?P<unit>/\s*t\b|/\s*kg\b|/\s*mwh\b|/\s*ton\b|por\s+tonelada|por\s+quilo|per\s+tonne|per\s+ton|per\s+kg)?',
    re.IGNORECASE)
SCALES = {'mil': 1e3, 'thousand': 1e3, 'milhao': 1e6, 'milhão': 1e6, 'milhoes': 1e6, 'milhões': 1e6,
          'million': 1e6, 'bilhao': 1e9, 'bilhão': 1e9, 'bilhoes': 1e9, 'bilhões': 1e9, 'billion': 1e9}
SENTENCE = re.compile(r'(?<=[.!?;])\s+')


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def fold(text):
    """Lowercase without accents, so 'nióbio' and 'niobio' match the same term.

    Hyphens become spaces: the press writes both 'terras raras' and 'terras-raras',
    and without this the second one matched nothing at all.
    """
    stripped = unicodedata.normalize('NFKD', str(text or ''))
    plain = ''.join(c for c in stripped if not unicodedata.combining(c)).lower()
    return re.sub(r'[‐-―-]+', ' ', plain)


def schema(connection):
    connection.executescript('''
    CREATE TABLE IF NOT EXISTS news_runs(run_id TEXT PRIMARY KEY, started_at TEXT NOT NULL,
      finished_at TEXT, status TEXT NOT NULL, radar_version TEXT NOT NULL, summary_json TEXT);
    CREATE TABLE IF NOT EXISTS news_sources(source_id TEXT PRIMARY KEY, name TEXT NOT NULL,
      url TEXT NOT NULL, lang TEXT, last_status TEXT, last_seen TEXT, tipo TEXT, escopo TEXT,
      tema TEXT);
    CREATE TABLE IF NOT EXISTS news_items(item_id TEXT PRIMARY KEY, source_id TEXT NOT NULL,
      title TEXT NOT NULL, link TEXT NOT NULL, summary TEXT, published_at TEXT,
      first_seen TEXT NOT NULL, run_id TEXT NOT NULL, regional INTEGER NOT NULL DEFAULT 0,
      regiao_termo TEXT, setorial INTEGER NOT NULL DEFAULT 0);
    CREATE TABLE IF NOT EXISTS news_signals(item_id TEXT NOT NULL, commodity TEXT NOT NULL,
      direction TEXT NOT NULL, confidence REAL NOT NULL, evidence TEXT NOT NULL,
      price_currency TEXT, price_amount REAL, price_unit TEXT,
      PRIMARY KEY(item_id, commodity, evidence));
    CREATE TABLE IF NOT EXISTS news_trends(period TEXT NOT NULL, commodity TEXT NOT NULL,
      items INTEGER NOT NULL, up INTEGER NOT NULL, down INTEGER NOT NULL, price_points INTEGER NOT NULL,
      score REAL NOT NULL, verdict TEXT NOT NULL, computed_at TEXT NOT NULL,
      PRIMARY KEY(period, commodity));
    CREATE TABLE IF NOT EXISTS news_item_commodities(item_id TEXT NOT NULL,
      commodity TEXT NOT NULL, PRIMARY KEY(item_id, commodity));
    CREATE INDEX IF NOT EXISTS news_items_published ON news_items(published_at);
    CREATE INDEX IF NOT EXISTS news_item_commodities_commodity
      ON news_item_commodities(commodity);
    ''')
    # A database written by the older radar has news_sources without 'tema'.
    # CREATE TABLE IF NOT EXISTS leaves it alone, so add the column here.
    columns = {row[1] for row in connection.execute('PRAGMA table_info(news_sources)')}
    if 'tema' not in columns:
        connection.execute('ALTER TABLE news_sources ADD COLUMN tema TEXT')
    colunas_itens = {row[1] for row in connection.execute('PRAGMA table_info(news_items)')}
    if 'setorial' not in colunas_itens:
        connection.execute('ALTER TABLE news_items ADD COLUMN setorial INTEGER NOT NULL DEFAULT 0')
    connection.commit()


def read_once(url, agent, timeout):
    """Some feeds answer gzip even when it was not asked for - G1 does it on part of
    the requests only, which made the old fetcher fail on some runs and not others.
    Decide by the magic bytes, not by the header, because the header can be absent.
    """
    request = urllib.request.Request(url, headers={
        'User-Agent': agent,
        'Accept': 'application/rss+xml, application/atom+xml, application/xml, text/xml, */*',
        'Accept-Encoding': 'gzip',
    })
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload = response.read(MAX_FEED_BYTES)
    if payload[:2] == b'\x1f\x8b':
        payload = gzip.decompress(payload)
    return payload


def fetch(url, timeout=25):
    """Publishers disagree about which agent to trust, and they disagree in both
    directions - see the note on USER_AGENT. Try one, then the other.
    """
    try:
        return read_once(url, USER_AGENT, timeout)
    except urllib.error.HTTPError as error:
        if error.code not in REFUSAL_CODES:
            raise
        return read_once(url, FALLBACK_USER_AGENT, timeout)


def strip_tags(value):
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', value or '')).strip()


def parse_date(value):
    if not value:
        return None
    text = value.strip()
    try:
        return parsedate_to_datetime(text).astimezone(timezone.utc).isoformat()
    except (TypeError, ValueError):
        pass
    try:
        return datetime.fromisoformat(text.replace('Z', '+00:00')).astimezone(timezone.utc).isoformat()
    except ValueError:
        return None


def parse_feed(payload):
    """Read RSS <item> and Atom <entry> alike; anything without a link is dropped."""
    root = ET.fromstring(payload)
    entries = []
    for node in root.iter():
        tag = node.tag.rsplit('}', 1)[-1]
        if tag not in ('item', 'entry'):
            continue
        found = {}
        for child in node:
            name = child.tag.rsplit('}', 1)[-1]
            if name == 'link' and not (child.text or '').strip():
                found['link'] = child.attrib.get('href', '')
            else:
                found.setdefault(name, (child.text or '').strip())
        link = found.get('link', '')
        title = strip_tags(found.get('title'))
        if not link or not title:
            continue
        entries.append({
            'title': title,
            'link': link,
            'summary': strip_tags(found.get('description') or found.get('summary') or found.get('content')),
            'published_at': parse_date(found.get('pubDate') or found.get('published') or found.get('updated')),
        })
    return entries


def read_price(sentence):
    match = PRICE.search(sentence)
    if not match:
        return None
    raw = match.group('amount').replace(' ', '')
    # Brazilian and English notations both appear in the same feed set.
    if ',' in raw:
        raw = raw.replace('.', '').replace(',', '.')
    try:
        amount = float(raw)
    except ValueError:
        return None
    scale = SCALES.get(fold(match.group('scale')), 1) if match.group('scale') else 1
    unit = match.group('unit')
    return {'currency': match.group('currency').upper(), 'amount': amount * scale,
            'unit': re.sub(r'\s+', '', unit).lower() if unit else None}


def mentions(folded, term):
    """Whole-word match: short terms like 'mine' or 'mina' would otherwise hit inside
    'mineral' or 'terminar' and make unrelated stories look regional.
    """
    return re.search(rf'\b{re.escape(fold(term))}\b', folded) is not None


def region_hit(text, config):
    """Regional when the state is named, or when a Goias mining municipality appears
    next to a mining or energy term. A municipality alone is not enough: several of
    these names exist in other states too.
    """
    region = config.get('region') or {}
    folded = fold(text)
    for term in region.get('estado', []):
        if mentions(folded, term):
            return term
    if not any(mentions(folded, word) for word in region.get('contexto', [])):
        return None
    for town in region.get('municipios', []):
        if mentions(folded, town):
            return town
    return None


def setorial(item, config):
    """Is this a mining story, as opposed to any story that happens to name Goias?

    'regional' only asks whether the state is named, so it lets in football, crime and
    celebrity from a state-wide outlet like G1 Goias. Measured on the collection of
    19/09/2026: 487 stories named Goias, and only 175 of those were about the sector.

    A story counts as sector news when it names a mineral substance or a term from
    'contexto_mineracao'. Energy is deliberately excluded here - 'energia' and
    'eletrica' are everyday words, and letting them in pulled a storm warning and
    electrocuted cattle into the mining count.

    Only the headline is read, not the summary. A Google News summary carries scraped
    debris from the page, and a lottery story reached the mining count through a shop
    called 'casa loterica Aguia de Ouro'. Measured over the collection of 19/09/2026,
    dropping the summary cost two stories out of 176 - that one and a 'create an
    account to save locations' banner.
    """
    somente_titulo = {'title': item['title'], 'summary': ''}
    energeticas = set(config.get('substancias_energeticas') or ())
    if any(c not in energeticas for c in commodities_of(somente_titulo, config)):
        return True
    region = config.get('region') or {}
    termos = region.get('contexto_mineracao') or region.get('contexto') or []
    folded = fold(item['title'])
    return any(mentions(folded, termo) for termo in termos)


def direction_enabled(config):
    """Off unless feeds.json says otherwise. See the block below analyse()."""
    return bool(config.get('sinais_de_direcao', False))


def commodities_of(item, config):
    """Which substances the story mentions. This is a factual tag - the word is in the
    text or it is not - and it is what the page filters on. It is deliberately kept
    apart from the direction reading below, which is an interpretation and is off.

    Two Portuguese names carry another everyday meaning: 'ouro' as a medal and 'cobre'
    as the verb cobrir. When the headline is plainly about something else and carries
    no mining term, those two are dropped - 'Flávia Saraiva é ouro nas assimétricas'
    is not a gold story. Measured over September and August 2026 the rule caught that
    headline and its repeat, 2 of 524, and left every legitimate one standing.
    """
    folded = fold(f"{item['title']}. {item.get('summary') or ''}")
    achadas = sorted(name for name, terms in config['commodities'].items()
                     if any(mentions(folded, term) for term in terms))
    ambiguas = set(config.get('commodities_ambiguas') or ())
    if not ambiguas or not (set(achadas) & ambiguas):
        return achadas
    no_titulo = fold(item['title'])
    excecoes = config.get('commodities_excecoes') or ()
    if not any(mentions(no_titulo, termo) for termo in excecoes):
        return achadas
    region = config.get('region') or {}
    mineracao = region.get('contexto_mineracao') or region.get('contexto') or ()
    if any(mentions(no_titulo, termo) for termo in mineracao):
        return achadas
    return [nome for nome in achadas if nome not in ambiguas]


# ---------------------------------------------------------------------------
# Direction reading - DORMANT. Everything from here to trends() only runs when
# feeds.json sets "sinais_de_direcao": true, and it is false.
#
# It tries to read from the wording whether the press is pointing a price up or
# down. It was inherited from the older prototype, nobody asked for it, and it is
# measurably wrong on real headlines: "copper, silver prices plummet and gold
# slides" was filed as copper UP and gold UP, because 'rally' is in the up list
# and 'plummet' and 'slides' are in neither list.
#
# The code is kept, not deleted, so the decision can be revisited. If it is ever
# switched on, the lexicon needs work first - and note that stories already in the
# database are never re-read, so a lexicon change only affects new ones.
# ---------------------------------------------------------------------------


def analyse(item, config):
    """One signal per commodity per sentence that also carries a direction word."""
    text = f"{item['title']}. {item.get('summary') or ''}"
    signals = []
    for sentence in SENTENCE.split(text):
        folded = fold(sentence)
        if not folded.strip():
            continue
        # Whole word, same rule the regional mark already used. A plain substring
        # test files 'ouro' out of 'tesouro' and 'cobre' out of the verb cobrir,
        # and the economy feeds are full of both.
        hits = [name for name, terms in config['commodities'].items()
                if any(mentions(folded, term) for term in terms)]
        if not hits:
            continue
        up = sum(1 for word in config['direction']['up'] if re.search(rf'\b{re.escape(fold(word))}\b', folded))
        down = sum(1 for word in config['direction']['down'] if re.search(rf'\b{re.escape(fold(word))}\b', folded))
        if up == down:
            continue
        price = read_price(sentence)
        # A named price in the same sentence is stronger evidence than wording alone.
        confidence = min(1.0, 0.4 + 0.1 * abs(up - down) + (0.3 if price else 0.0))
        for commodity in hits:
            signals.append({
                'commodity': commodity,
                'direction': 'up' if up > down else 'down',
                'confidence': round(confidence, 3),
                'evidence': sentence.strip()[:300],
                'price': price,
            })
    return signals


def period_of(item):
    stamp = item.get('published_at') or item['first_seen']
    year, week, _ = datetime.fromisoformat(stamp).isocalendar()
    return f'{year}-W{week:02d}'


SOURCE_UPSERT = (
    'INSERT INTO news_sources VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(source_id) DO UPDATE SET '
    'name=excluded.name, lang=excluded.lang, last_status=excluded.last_status, '
    'last_seen=excluded.last_seen, tipo=excluded.tipo, escopo=excluded.escopo, tema=excluded.tema')


def remember_source(connection, source_id, source, status):
    """Write the source row and refresh it on every run. The older radar updated only
    status and timestamp, so an edit to tipo, escopo or tema in feeds.json never
    reached the database - and therefore never reached the filters on the page.
    'url' is left out of the update on purpose: source_id is its hash, so it cannot
    differ for an existing row.
    """
    connection.execute(SOURCE_UPSERT, (
        source_id, source['name'], source['url'], source.get('lang'), status, timestamp(),
        source.get('tipo'), source.get('escopo'), source.get('tema')))


def collect(connection, config, fetcher, run_id):
    report = {'sources': [], 'new_items': 0, 'commodities': 0, 'signals': 0, 'errors': 0,
              'regional': 0, 'setorial': 0, 'regional_setorial': 0}
    for source in config['sources']:
        source_id = hashlib.sha256(source['url'].encode()).hexdigest()[:32]
        entry = {'name': source['name'], 'tipo': source.get('tipo'), 'escopo': source.get('escopo'),
                 'tema': source.get('tema'), 'items': 0, 'new': 0}
        try:
            payload = fetcher(source['url'])
            entries = parse_feed(payload)
            entry['items'] = len(entries)
            remember_source(connection, source_id, source, 'ok')
            for found in entries:
                item_id = hashlib.sha256(found['link'].encode()).hexdigest()
                if connection.execute('SELECT 1 FROM news_items WHERE item_id=?', (item_id,)).fetchone():
                    continue
                item = {**found, 'first_seen': timestamp()}
                term = region_hit(f"{item['title']}. {item.get('summary') or ''}", config)
                do_setor = setorial(item, config)
                connection.execute('INSERT INTO news_items VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                                   (item_id, source_id, item['title'], item['link'], item['summary'],
                                    item['published_at'], item['first_seen'], run_id,
                                    1 if term else 0, term, 1 if do_setor else 0))
                report['regional'] += 1 if term else 0
                report['setorial'] += 1 if do_setor else 0
                report['regional_setorial'] += 1 if (term and do_setor) else 0
                for commodity in commodities_of(item, config):
                    connection.execute('INSERT OR IGNORE INTO news_item_commodities VALUES(?,?)',
                                       (item_id, commodity))
                    report['commodities'] += 1
                if direction_enabled(config):
                    for signal in analyse(item, config):
                        price = signal['price'] or {}
                        connection.execute(
                            'INSERT OR IGNORE INTO news_signals VALUES(?,?,?,?,?,?,?,?)',
                            (item_id, signal['commodity'], signal['direction'], signal['confidence'],
                             signal['evidence'], price.get('currency'), price.get('amount'),
                             price.get('unit')))
                        report['signals'] += 1
                entry['new'] += 1
                report['new_items'] += 1
        except (urllib.error.URLError, ET.ParseError, OSError, ValueError) as error:
            # One unreachable feed must not cost the whole run.
            entry['error'] = f'{type(error).__name__}: {error}'
            report['errors'] += 1
            remember_source(connection, source_id, source, entry['error'][:200])
        report['sources'].append(entry)
        connection.commit()
    return report


def trends(connection, config):
    """Weekly balance of up versus down wording, per commodity. Thin weeks stay undecided."""
    minimum = int(config.get('min_items_for_trend', 3))
    buckets = {}
    rows = connection.execute('''SELECT s.commodity, s.direction, s.price_amount, i.published_at, i.first_seen, i.item_id
        FROM news_signals s JOIN news_items i ON i.item_id=s.item_id''').fetchall()
    for commodity, direction, price_amount, published_at, first_seen, item_id in rows:
        key = (period_of({'published_at': published_at, 'first_seen': first_seen}), commodity)
        bucket = buckets.setdefault(key, {'up': 0, 'down': 0, 'items': set(), 'prices': 0})
        bucket[direction] += 1
        bucket['items'].add(item_id)
        bucket['prices'] += 1 if price_amount is not None else 0
    computed = timestamp()
    out = []
    for (period, commodity), bucket in sorted(buckets.items()):
        items = len(bucket['items'])
        total = bucket['up'] + bucket['down']
        score = round((bucket['up'] - bucket['down']) / total, 3) if total else 0.0
        if items < minimum:
            verdict = 'evidencia_insuficiente'
        elif score >= 0.34:
            verdict = 'pressao_de_alta'
        elif score <= -0.34:
            verdict = 'pressao_de_baixa'
        else:
            verdict = 'sem_direcao_clara'
        connection.execute('INSERT OR REPLACE INTO news_trends VALUES(?,?,?,?,?,?,?,?,?)',
                           (period, commodity, items, bucket['up'], bucket['down'], bucket['prices'],
                            score, verdict, computed))
        out.append({'period': period, 'commodity': commodity, 'items': items, 'up': bucket['up'],
                    'down': bucket['down'], 'price_points': bucket['prices'], 'score': score, 'verdict': verdict})
    connection.commit()
    return out


def run(database, config, fetcher=fetch):
    connection = sqlite3.connect(database, timeout=30)
    try:
        schema(connection)
        run_id = uuid.uuid4().hex
        started = timestamp()
        connection.execute('INSERT INTO news_runs VALUES(?,?,?,?,?,?)',
                           (run_id, started, None, 'running', RADAR_VERSION, None))
        connection.commit()
        report = collect(connection, config, fetcher, run_id)
        report['trends'] = trends(connection, config) if direction_enabled(config) else []
        report['run_id'] = run_id
        report['started_at'] = started
        report['radar_version'] = RADAR_VERSION
        status = 'partial' if report['errors'] else 'success'
        connection.execute('UPDATE news_runs SET finished_at=?,status=?,summary_json=? WHERE run_id=?',
                           (timestamp(), status, json.dumps(report, ensure_ascii=False), run_id))
        connection.commit()
        report['status'] = status
        return report
    finally:
        connection.close()


def export_payload(connection, limit=180, config_region=None):
    """Build exactly the packet /api/radar already serves under 'noticias'.

    This is how the collection reaches the site without anyone touching the VPS: the
    file is committed to the repository, the deploy carries the whole commit to the
    server every two minutes, and the API reads it - the same route data/atlas/
    processes.json already takes. A SQLite under /var/lib never leaves the machine
    it was written on, which is why the older module needed a manual install.

    Regional sector stories come first: they are the ones that bear on Goias. The
    default of 180 is measured, not guessed: it is where every Goias sector story of
    the 19/09/2026 collection fits and seven different substances still appear, so
    both filters on the page have something to work with. Sixty left the substance
    filter with a single option.
    """
    connection.row_factory = sqlite3.Row
    itens = connection.execute('''
        SELECT i.item_id, i.title, i.link, i.published_at, i.first_seen, i.regional,
               i.regiao_termo, i.setorial, s.name AS fonte, s.escopo, s.tema
        FROM news_items i LEFT JOIN news_sources s ON s.source_id = i.source_id
        ORDER BY (i.regional AND i.setorial) DESC, i.setorial DESC, i.regional DESC,
                 COALESCE(i.published_at, i.first_seen) DESC
        LIMIT ?''', (limit,)).fetchall()
    # Substances per story, so the page can filter by them without another round trip.
    por_item = {}
    for row in connection.execute('SELECT item_id, commodity FROM news_item_commodities'):
        por_item.setdefault(row['item_id'], []).append(row['commodity'])
    conta = lambda sql: connection.execute(sql).fetchone()[0]
    run = connection.execute("SELECT finished_at, status FROM news_runs "
                             "WHERE finished_at IS NOT NULL ORDER BY started_at DESC "
                             "LIMIT 1").fetchone()
    substancias = {}
    for row in connection.execute('SELECT commodity, COUNT(*) n FROM news_item_commodities '
                                  'GROUP BY 1 ORDER BY 2 DESC'):
        substancias[row['commodity']] = row['n']
    region = config_region or {}
    return {
        'disponivel': True,
        'gerado_por': f'radar-noticias {RADAR_VERSION}',
        # Nome acentuado de cada município, para a página não mostrar 'catalao'.
        'municipios': region.get('municipios_nome') or {},
        'atualizado_em': run['finished_at'] if run else None,
        'ultima_execucao': run['status'] if run else None,
        'itens': [{**{k: v for k, v in dict(row).items() if k != 'item_id'},
                   'substancias': sorted(por_item.get(row['item_id'], []))}
                  for row in itens],
        # Empty while sinais_de_direcao is false. The page renders an empty state.
        'tendencias': [],
        'total': conta('SELECT COUNT(*) FROM news_items'),
        'regionais': conta('SELECT COUNT(*) FROM news_items WHERE regional=1'),
        'setoriais': conta('SELECT COUNT(*) FROM news_items WHERE setorial=1'),
        'regionais_setoriais': conta('SELECT COUNT(*) FROM news_items '
                                     'WHERE regional=1 AND setorial=1'),
        'fontes_vivas': conta("SELECT COUNT(*) FROM news_sources WHERE last_status='ok'"),
        'fontes': conta('SELECT COUNT(*) FROM news_sources'),
        'substancias': substancias,
    }


ANTERIORES = 'anteriores'
MESES_ABERTOS = 12


def janela(hoje=None):
    """The oldest month that still gets a file of its own - a rolling window.

    Twelve months stay browsable one by one; everything older is folded into a single
    'anteriores' file. Without this the archive sprawled to 113 files, most under a
    kilobyte, because the feeds carry material going back decades. With it the folder
    never holds more than thirteen files, however long the radar runs.
    """
    hoje = hoje or datetime.now(timezone.utc)
    total = hoje.year * 12 + (hoje.month - 1) - (MESES_ABERTOS - 1)
    return f'{total // 12:04d}-{total % 12 + 1:02d}'


def revisar(item, config):
    """Re-apply the lexicon to a story already in the archive.

    A correction to the lexicon used to reach only stories collected afterwards, which
    left the archive holding two different criteria at once. The archive keeps every
    headline, so the marks can simply be recomputed from it on each export - and both
    marks read the headline only, so nothing is lost by not having the summary here.
    """
    ambiguas = set(config.get('commodities_ambiguas') or ())
    substancias = list(item.get('substancias') or ())
    if ambiguas and set(substancias) & ambiguas:
        titulo = fold(item.get('title') or '')
        region = config.get('region') or {}
        mineracao = region.get('contexto_mineracao') or region.get('contexto') or ()
        if (any(mentions(titulo, termo) for termo in config.get('commodities_excecoes') or ())
                and not any(mentions(titulo, termo) for termo in mineracao)):
            substancias = [nome for nome in substancias if nome not in ambiguas]
    revisto = {**item, 'substancias': substancias}
    revisto['setorial'] = 1 if setorial(revisto, config) else 0
    return revisto


def month_of(item, desde):
    """Which file a story belongs to, from its own date - never from the run date."""
    stamp = (item.get('published_at') or item.get('first_seen') or '')[:7]
    if not re.fullmatch(r'\d{4}-\d{2}', stamp):
        return ANTERIORES
    return stamp if stamp >= desde else ANTERIORES


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')


def read_month(path):
    """Whatever is already committed for this month, or nothing."""
    try:
        packet = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return []
    itens = packet.get('itens')
    return itens if isinstance(itens, list) else []


def export_archive(database, destination, recent=180, desde=None, config=None):
    """Write the monthly archive and the packet the page opens with.

    The committed files are the archive, not the SQLite. Each run merges what it
    collected into the month files that are already there, keyed by link, so nothing
    is dropped - which matters because an RSS feed is a rolling window: a story that
    leaves the feed cannot be collected again. The database is only a speed-up; if it
    is lost, the archive on disk survives and the next run adds to it.
    """
    destino = Path(destination)
    desde = desde or janela()
    connection = sqlite3.connect(f'file:{Path(database)}?mode=ro', uri=True, timeout=10)
    try:
        pacote = export_payload(connection, limit=10 ** 9,
                                config_region=(config or {}).get('region'))
    finally:
        connection.close()

    # Tudo é relido e reagrupado a cada execução: assim, quando a janela anda, o mês
    # que saiu dela se funde em 'anteriores' sozinho, sem migração manual.
    pasta = destino / 'meses'
    guardadas = {}
    for arquivo in sorted(pasta.glob('*.json')):
        for item in read_month(arquivo):
            guardadas[item['link']] = item
    antes = set(guardadas)
    # A matéria recoletada é atualizada; a que saiu do feed permanece onde está.
    for item in pacote['itens']:
        guardadas[item['link']] = item
    # O léxico de hoje vale para o acervo inteiro, não só para o que entrou agora.
    guardadas = {link: revisar(item, config or {}) for link, item in guardadas.items()}
    # Só notícia do setor é publicada. O coletor lê os feeds inteiros - um veículo
    # regional publica futebol e polícia junto com mineração - mas o que não é do
    # setor não chega ao site: não vira arquivo, não viaja até o navegador e não
    # aparece em contagem nenhuma. A separação é a mesma que o projeto já faz entre
    # a zona bruta e a zona tratada.
    antes_do_corte = len(guardadas)
    guardadas = {link: item for link, item in guardadas.items() if item.get('setorial')}
    descartadas = antes_do_corte - len(guardadas)
    novas_por_mes = {}
    for link, item in guardadas.items():
        if link not in antes:
            novas_por_mes[month_of(item, desde)] = novas_por_mes.get(month_of(item, desde), 0) + 1

    baldes = {}
    for item in guardadas.values():
        baldes.setdefault(month_of(item, desde), []).append(item)
    for obsoleto in pasta.glob('*.json'):
        if obsoleto.stem not in baldes:
            obsoleto.unlink()

    indice, todas = [], []
    # 'anteriores' fecha a lista: é material de arquivo dos feeds, não coleta nossa.
    for mes in sorted(baldes, key=lambda m: ('', m) if m == ANTERIORES else ('z', m), reverse=True):
        itens = sorted(baldes[mes],
                       key=lambda i: (i.get('published_at') or i.get('first_seen') or ''), reverse=True)
        write_json(pasta / f'{mes}.json', {'mes': mes, 'materias': len(itens), 'itens': itens})
        indice.append({'mes': mes, 'materias': len(itens), 'novas': novas_por_mes.get(mes, 0),
                       'regionais': sum(1 for i in itens if i.get('regional')),
                       'setoriais': sum(1 for i in itens if i.get('setorial')),
                       'regionais_setoriais': sum(1 for i in itens
                                                  if i.get('regional') and i.get('setorial'))})
        todas.extend(itens)

    # Os arquivos de mês ficam em ordem de data; a abertura, não. O painel é de
    # mineração, e por data pura ela encheria de concurso público e futebol do dia -
    # medido: das 180 mais recentes, 6 eram do setor. Setor e Goiás vêm primeiro.
    todas.sort(key=lambda i: (bool(i.get('regional')) and bool(i.get('setorial')),
                              bool(i.get('setorial')), bool(i.get('regional')),
                              i.get('published_at') or i.get('first_seen') or ''), reverse=True)
    # Os contadores descrevem o acervo publicado. 'descartadas' conta quantas esta
    # execução deixou de fora por não serem do setor - é rastro da execução, não do
    # acervo, porque o que foi descartado antes já não está mais aqui para contar.
    pacote.update(
        itens=todas[:recent], meses=indice,
        total=len(todas), descartadas=descartadas,
        # Contado no acervo, não no banco: o banco é cache e pode estar vazio.
        veiculos=len({i.get('fonte') for i in todas if i.get('fonte')}),
        regionais=sum(m['regionais'] for m in indice),
        setoriais=sum(m['setoriais'] for m in indice),
        regionais_setoriais=sum(m['regionais_setoriais'] for m in indice),
        substancias=dict(sorted(
            ((s, sum(1 for i in todas if s in (i.get('substancias') or [])))
             for s in {s for i in todas for s in (i.get('substancias') or [])}),
            key=lambda par: -par[1])))
    # Desde quando a coleta é nossa. Tudo antes disso o radar recolheu de uma vez,
    # do que os buscadores ainda guardavam - não é série temporal de notícia, e a
    # página precisa dizer isso em vez de deixar o gráfico ser lido como tendência.
    vistos = [(i.get('first_seen') or '')[:7] for i in todas if (i.get('first_seen') or '')[:7]]
    pacote['coleta_desde'] = min(vistos) if vistos else None
    pacote['janela'] = desde
    write_json(destino / 'latest.json', pacote)
    return pacote


def offline_fetcher(directory):
    """Reads .xml fixtures in order, so the radar can be exercised without network."""
    files = sorted(Path(directory).glob('*.xml'))
    if not files:
        raise ValueError(f'no .xml fixture in {directory}')
    state = {'i': 0}

    def fetcher(_url):
        payload = files[state['i'] % len(files)].read_bytes()
        state['i'] += 1
        return payload
    return fetcher


def check(config, fetcher=fetch):
    """Report which feeds actually answer, so dead ones can be pruned in one run."""
    results = []
    for source in config['sources']:
        entry = {'name': source['name'], 'tipo': source.get('tipo'), 'escopo': source.get('escopo'),
                 'tema': source.get('tema')}
        try:
            entries = parse_feed(fetcher(source['url']))
            entry.update(status='ok', items=len(entries))
        except (urllib.error.URLError, ET.ParseError, OSError, ValueError) as error:
            entry.update(status='falhou', items=0, error=f'{type(error).__name__}: {error}'[:120])
        results.append(entry)
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description='News radar for mining, energy and rare earths.')
    # Deliberately not the path the older radar uses, so the two never share a file
    # while both exist in the repository.
    parser.add_argument('--db', default='/var/lib/minera-goias-radar/radar.sqlite')
    parser.add_argument('--config', default=str(Path(__file__).with_name('feeds.json')))
    parser.add_argument('--report', help='write the run report as JSON to this path')
    parser.add_argument('--export-dir', metavar='DIR',
                        help='write the archive the site reads (public/data/noticias)')
    parser.add_argument('--export-limit', type=int, default=180,
                        help='how many stories the opening packet carries (default 180)')
    parser.add_argument('--offline-dir', help='read feeds from .xml fixtures instead of the network')
    parser.add_argument('--check', action='store_true',
                        help='only test whether each feed answers, without storing anything')
    parser.add_argument('--tema', action='append', metavar='TEMA',
                        help='restrict the run to these temas, e.g. --tema mineracao --tema geral')
    args = parser.parse_args(argv)

    config = json.loads(Path(args.config).read_text(encoding='utf-8'))
    if args.tema:
        wanted = set(args.tema)
        config = {**config, 'sources': [s for s in config['sources'] if s.get('tema') in wanted]}
        if not config['sources']:
            parser.error(f'no source has tema in {sorted(wanted)}')
    if args.check:
        fetcher = offline_fetcher(args.offline_dir) if args.offline_dir else fetch
        working = 0
        for entry in check(config, fetcher):
            mark = 'ok  ' if entry['status'] == 'ok' else 'FALHA'
            working += entry['status'] == 'ok'
            detail = f"{entry['items']:>3} itens" if entry['status'] == 'ok' else entry.get('error', '')
            print(f"  {mark} [{entry.get('tema') or '-':<9}|{entry.get('escopo') or '-':<13}] "
                  f"{entry['name']:<46} {detail}")
        print(f'{working}/{len(config["sources"])} fontes responderam')
        return 0 if working else 1
    Path(args.db).parent.mkdir(parents=True, exist_ok=True)
    fetcher = offline_fetcher(args.offline_dir) if args.offline_dir else fetch
    report = run(args.db, config, fetcher)
    if args.report:
        Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding='utf-8')
    campos = ['run_id', 'status', 'new_items', 'regional', 'setorial', 'regional_setorial',
              'commodities', 'errors']
    if direction_enabled(config):
        campos.insert(-1, 'signals')
    print(json.dumps({k: report[k] for k in campos}, ensure_ascii=False))
    if args.export_dir:
        pacote = export_archive(args.db, args.export_dir, args.export_limit, config=config)
        novas = sum(m['novas'] for m in pacote['meses'])
        print(f"  acervo em {args.export_dir}: {pacote['total']} materias em "
              f"{len(pacote['meses'])} meses, {novas} novas nesta coleta, "
              f"{pacote['regionais_setoriais']} de Goias e do setor")
    for trend in report['trends']:
        if trend['verdict'] in ('pressao_de_alta', 'pressao_de_baixa'):
            print(f"  {trend['period']}  {trend['commodity']:<18} {trend['verdict']:<18}"
                  f" score={trend['score']:+.2f}  materias={trend['items']}  precos={trend['price_points']}")
    return 0 if report['status'] == 'success' else 1


if __name__ == '__main__':
    sys.exit(main())
