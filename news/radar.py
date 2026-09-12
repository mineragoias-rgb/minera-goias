#!/usr/bin/env python3
"""Prototype news radar: collects headlines, stores them with provenance and reads
direction signals out of the wording. It never states a price series of its own -
what it produces is evidence about what the press is saying, dated and countable.
"""
import argparse
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

RADAR_VERSION = '0.1-prototype'
USER_AGENT = 'minera-goias-news-radar/0.1 (+https://github.com/mineragoias-rgb/minera-goias)'
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
    """Lowercase without accents, so 'nióbio' and 'niobio' match the same term."""
    stripped = unicodedata.normalize('NFKD', str(text or ''))
    return ''.join(c for c in stripped if not unicodedata.combining(c)).lower()


def schema(connection):
    connection.executescript('''
    CREATE TABLE IF NOT EXISTS news_runs(run_id TEXT PRIMARY KEY, started_at TEXT NOT NULL,
      finished_at TEXT, status TEXT NOT NULL, radar_version TEXT NOT NULL, summary_json TEXT);
    CREATE TABLE IF NOT EXISTS news_sources(source_id TEXT PRIMARY KEY, name TEXT NOT NULL,
      url TEXT NOT NULL, lang TEXT, last_status TEXT, last_seen TEXT);
    CREATE TABLE IF NOT EXISTS news_items(item_id TEXT PRIMARY KEY, source_id TEXT NOT NULL,
      title TEXT NOT NULL, link TEXT NOT NULL, summary TEXT, published_at TEXT,
      first_seen TEXT NOT NULL, run_id TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS news_signals(item_id TEXT NOT NULL, commodity TEXT NOT NULL,
      direction TEXT NOT NULL, confidence REAL NOT NULL, evidence TEXT NOT NULL,
      price_currency TEXT, price_amount REAL, price_unit TEXT,
      PRIMARY KEY(item_id, commodity, evidence));
    CREATE TABLE IF NOT EXISTS news_trends(period TEXT NOT NULL, commodity TEXT NOT NULL,
      items INTEGER NOT NULL, up INTEGER NOT NULL, down INTEGER NOT NULL, price_points INTEGER NOT NULL,
      score REAL NOT NULL, verdict TEXT NOT NULL, computed_at TEXT NOT NULL,
      PRIMARY KEY(period, commodity));
    CREATE INDEX IF NOT EXISTS news_items_published ON news_items(published_at);
    ''')
    connection.commit()


def fetch(url, timeout=25):
    request = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read(MAX_FEED_BYTES)


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


def analyse(item, config):
    """One signal per commodity per sentence that also carries a direction word."""
    text = f"{item['title']}. {item.get('summary') or ''}"
    signals = []
    for sentence in SENTENCE.split(text):
        folded = fold(sentence)
        if not folded.strip():
            continue
        hits = [name for name, terms in config['commodities'].items()
                if any(fold(term) in folded for term in terms)]
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


def collect(connection, config, fetcher, run_id):
    report = {'sources': [], 'new_items': 0, 'signals': 0, 'errors': 0}
    for source in config['sources']:
        source_id = hashlib.sha256(source['url'].encode()).hexdigest()[:32]
        entry = {'name': source['name'], 'items': 0, 'new': 0}
        try:
            payload = fetcher(source['url'])
            entries = parse_feed(payload)
            entry['items'] = len(entries)
            connection.execute(
                'INSERT INTO news_sources VALUES(?,?,?,?,?,?) ON CONFLICT(source_id) DO UPDATE '
                'SET last_status=excluded.last_status,last_seen=excluded.last_seen',
                (source_id, source['name'], source['url'], source.get('lang'), 'ok', timestamp()))
            for found in entries:
                item_id = hashlib.sha256(found['link'].encode()).hexdigest()
                if connection.execute('SELECT 1 FROM news_items WHERE item_id=?', (item_id,)).fetchone():
                    continue
                item = {**found, 'first_seen': timestamp()}
                connection.execute('INSERT INTO news_items VALUES(?,?,?,?,?,?,?,?)',
                                   (item_id, source_id, item['title'], item['link'], item['summary'],
                                    item['published_at'], item['first_seen'], run_id))
                for signal in analyse(item, config):
                    price = signal['price'] or {}
                    connection.execute(
                        'INSERT OR IGNORE INTO news_signals VALUES(?,?,?,?,?,?,?,?)',
                        (item_id, signal['commodity'], signal['direction'], signal['confidence'],
                         signal['evidence'], price.get('currency'), price.get('amount'), price.get('unit')))
                    report['signals'] += 1
                entry['new'] += 1
                report['new_items'] += 1
        except (urllib.error.URLError, ET.ParseError, OSError, ValueError) as error:
            # One unreachable feed must not cost the whole run.
            entry['error'] = f'{type(error).__name__}: {error}'
            report['errors'] += 1
            connection.execute(
                'INSERT INTO news_sources VALUES(?,?,?,?,?,?) ON CONFLICT(source_id) DO UPDATE '
                'SET last_status=excluded.last_status,last_seen=excluded.last_seen',
                (source_id, source['name'], source['url'], source.get('lang'), entry['error'][:200], timestamp()))
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
        report['trends'] = trends(connection, config)
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


def main(argv=None):
    parser = argparse.ArgumentParser(description='Prototype news radar for energy and rare earths.')
    parser.add_argument('--db', default='/var/lib/minera-goias-news/radar.sqlite')
    parser.add_argument('--config', default=str(Path(__file__).with_name('feeds.json')))
    parser.add_argument('--report', help='write the run report as JSON to this path')
    parser.add_argument('--offline-dir', help='read feeds from .xml fixtures instead of the network')
    args = parser.parse_args(argv)

    config = json.loads(Path(args.config).read_text(encoding='utf-8'))
    Path(args.db).parent.mkdir(parents=True, exist_ok=True)
    fetcher = offline_fetcher(args.offline_dir) if args.offline_dir else fetch
    report = run(args.db, config, fetcher)
    if args.report:
        Path(args.report).write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps({k: report[k] for k in ('run_id', 'status', 'new_items', 'signals', 'errors')},
                     ensure_ascii=False))
    for trend in report['trends']:
        if trend['verdict'] in ('pressao_de_alta', 'pressao_de_baixa'):
            print(f"  {trend['period']}  {trend['commodity']:<18} {trend['verdict']:<18}"
                  f" score={trend['score']:+.2f}  materias={trend['items']}  precos={trend['price_points']}")
    return 0 if report['status'] == 'success' else 1


if __name__ == '__main__':
    sys.exit(main())
