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
_anm_subs = {'mtime': None, 'value': None}

PANORAMA = Path(__file__).resolve().parents[2] / 'data' / 'panorama' / 'panorama.json'

# A chave que o coletor de notícias usa, e o nome que a mesma substância tem no cadastro
# da ANM. Fica aqui, versionado ao lado do endpoint, porque é uma decisão editorial e não
# um dado: 'Monazita e Terras-Raras' é uma linha só do cadastro para o que a imprensa
# chama de terras raras, e 'Calcário' são quatro. Um teste afirma que todo nome à direita
# existe em dims.min, para que um nome errado não some em silêncio.
# Energia elétrica e gás natural não entram: não são substâncias minerais e não têm
# contraparte no cadastro nem na CFEM.
CRUZAMENTO_MIN = {
    'terras_raras': ['Monazita e Terras-Raras'],
    'ouro': ['Ouro'],
    'cobre': ['Cobre'],
    'litio': ['Lítio'],
    'niquel': ['Níquel'],
    'niobio': ['Nióbio'],
    'uranio': ['Urânio e outros Radioativos'],
    'fosfato': ['Fosfato'],
    'ferro': ['Ferro'],
    'areia': ['Areia', 'Areias Industriais'],
    'brita': ['Rochas (Britadas) e Cascalho'],
    'calcario': ['Calcário', 'Calcário Calcítico', 'Calcário Dolomítico', 'Calcário Industrial'],
    'argila': ['Argilas', 'Caulim'],
    'agua_mineral': ['Água Mineral'],
    'rochas_ornamentais': ['Rochas Ornamentais', 'Rochas Ornamentais - Outras'],
    'manganes': ['Manganês'],
    'gemas': ['Gemas', 'Geodos, Ágatas, Calcedônia, etc'],
    'amianto': ['Amianto'],
    'dolomito_magnesita': ['Dolomito e Magnesita'],
    'diamante': ['Diamante'],
    'titanio': ['Titânio'],
    'bauxita': ['Alumínio (Bauxita)'],
    'estanho': ['Estanho'],
    'vermiculita': ['Vermiculita e Perlita'],
    'zinco': ['Zinco'],
    'potassio': ['Potássio'],
    'grafita': ['Grafita'],
}
ESCOPOS = ('goias', 'brasil', 'tudo')

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


def anm_por_substancia():
    """Processos e CFEM de Goiás por substância, do pacote do Panorama, cacheado por mtime.

    Agregado aqui e não no cliente porque o arquivo tem 2,7 MB e o endpoint do Panorama
    o serve inteiro - não há como pedir duas colunas. Carregar e agregar custa ~120 ms
    uma vez por deploy; mandar o arquivo custaria 2,7 MB por leitor da aba.
    """
    mtime = PANORAMA.stat().st_mtime
    if _anm_subs['mtime'] == mtime:
        return _anm_subs['value']
    pacote = json.loads(PANORAMA.read_text(encoding='utf-8'))
    nomes = [linha[1] for linha in pacote['dims']['min']]
    de_quem = {nome: chave for chave, lista in CRUZAMENTO_MIN.items() for nome in lista}

    def chave_de(indice):
        # O índice -1 é "substância não informada" no pacote, e não pode cair em nome algum.
        return de_quem.get(nomes[indice]) if 0 <= indice < len(nomes) else None

    proc_cols = {c: i for i, c in enumerate(pacote['proc']['cols'])}
    cfem_cols = {c: i for i, c in enumerate(pacote['cfem']['cols'])}
    processos, cfem, anos = Counter(), Counter(), set()
    total_proc = len(pacote['proc']['rows'])
    total_cfem = 0.0
    for linha in pacote['proc']['rows']:
        chave = chave_de(linha[proc_cols['min']])
        if chave:
            processos[chave] += 1
    for linha in pacote['cfem']['rows']:
        valor = linha[cfem_cols['valor']] or 0
        total_cfem += valor
        anos.add(linha[cfem_cols['ano']])
        chave = chave_de(linha[cfem_cols['min']])
        if chave:
            cfem[chave] += valor
    value = {
        'processos': dict(processos), 'cfem': dict(cfem),
        'total_processos': total_proc, 'total_cfem': round(total_cfem, 2),
        'anos_cfem': [min(anos), max(anos)] if anos else None,
    }
    _anm_subs.update(mtime=mtime, value=value)
    return value


def _percentuais(linhas, campo):
    """Cada medida como fração do universo da própria tabela, para que as três somem 1.

    Os três eixos precisam do mesmo denominador, senão a comparação troca de população:
    o percentual da imprensa sairia de um universo e o do cadastro de outro. O quanto
    esse universo cobre o cadastro e a CFEM de Goiás vai em 'cobertura', declarado.
    """
    total = sum(linha[campo] or 0 for linha in linhas)
    for linha in linhas:
        linha[campo + '_pct'] = round((linha[campo] or 0) / total * 100, 2) if total else None
    return round(total, 2)


def cruzamento(limite_imprensa=None):
    """Atenção, cadastro e caixa da mesma substância, lado a lado.

    Não mede antecipação, e a nota diz isso: o cadastro da ANM não guarda a data em que
    um processo apareceu - só a da última movimentação - e não há histórico de retratos
    com que comparar. A coleta própria de imprensa começou em 09/2026.
    """
    anm = anm_por_substancia()
    pacote = news_from_repo() or {}
    por_escopo = pacote.get('substancias_por_escopo')
    dados = {}
    for escopo in ESCOPOS:
        imprensa = (por_escopo or {}).get(escopo) or {}
        subs = imprensa.get('substancias') or {}
        linhas = []
        for chave in CRUZAMENTO_MIN:
            visto = subs.get(chave) or {}
            linhas.append({
                'chave': chave, 'anm': CRUZAMENTO_MIN[chave],
                # None, e não zero, quando o pacote publicado é de uma versão do coletor
                # anterior à quebra por escopo: zero diria "ninguém escreveu sobre isso".
                'materias': visto.get('materias', 0) if por_escopo else None,
                'unicas': visto.get('unicas', 0) if por_escopo else None,
                'processos': anm['processos'].get(chave, 0),
                'cfem': round(anm['cfem'].get(chave, 0.0), 2),
            })
        soma_materias = _percentuais(linhas, 'materias') if por_escopo else None
        soma_unicas = _percentuais(linhas, 'unicas') if por_escopo else None
        _percentuais(linhas, 'processos')
        _percentuais(linhas, 'cfem')
        for linha in linhas:
            # A distância é diferença em pontos percentuais, nunca razão: lítio tem R$ 0
            # de CFEM e urânio tem 0 processos e R$ 0 - qualquer razão estoura.
            atencao = linha.get('unicas_pct')
            linha['distancia'] = (round(atencao - linha['cfem_pct'], 2)
                                  if atencao is not None and linha['cfem_pct'] is not None else None)
        linhas.sort(key=lambda linha: -(linha['processos'] or 0))
        dados[escopo] = {
            'materias': imprensa.get('materias') if por_escopo else None,
            'com_substancia': imprensa.get('com_substancia') if por_escopo else None,
            'tags': soma_materias, 'manchetes': soma_unicas,
            'linhas': linhas[:limite_imprensa] if limite_imprensa else linhas,
        }
    universo_proc = sum(anm['processos'].values())
    universo_cfem = sum(anm['cfem'].values())
    return {
        'escopos': list(ESCOPOS),
        'dados': dados,
        'cobertura': {
            'processos': round(universo_proc / anm['total_processos'], 4) if anm['total_processos'] else None,
            'cfem': round(universo_cfem / anm['total_cfem'], 4) if anm['total_cfem'] else None,
        },
        'totais': {'processos': anm['total_processos'], 'cfem': anm['total_cfem']},
        'imprensa_disponivel': por_escopo is not None,
        'periodos': {
            'cfem': anm['anos_cfem'],
            'imprensa_coleta_desde': pacote.get('coleta_desde'),
            'imprensa_janela': pacote.get('janela'),
            'imprensa_acervo': pacote.get('total'),
        },
        'nota': 'Três contagens da mesma substância, lado a lado: quantas matérias a imprensa '
                'publicou, quantos processos a ANM tem em Goiás e quanta CFEM Goiás arrecadou. '
                'É um retrato de um mesmo momento e não mede antecipação — o cadastro da ANM não '
                'guarda a data em que um processo apareceu, só a da última movimentação, e a coleta '
                'própria de imprensa começou em 09/2026. Distância alta não é previsão nem '
                'recomendação: diz que a atenção da imprensa e o dinheiro arrecadado estão em '
                'substâncias diferentes, e nada sobre qual das duas está certa.',
        'fonte': 'data/panorama/panorama.json · public/data/noticias/latest.json',
    }


@router.get('/cruzamento')
def radar_cruzamento(u=Depends(reader)):
    return cruzamento()


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
