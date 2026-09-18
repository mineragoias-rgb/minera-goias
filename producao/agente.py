#!/usr/bin/env python3
"""Agente semanal da base de produção mineral.

Lê fontes públicas (RI, agências, imprensa setorial e buscas), procura no texto números de produção por empresa, confronta cada um com a base
curada em `base_curada.json` e guarda tudo com a frase que originou o número. Ele NÃO reescreve a base curada: produz candidatos
`nao_validado`, aponta divergências e propõe melhorias de metodologia para revisão humana — como manda o METODOLOGIA.md ("importar não é
validar", "quando a fonte não diz, o sistema não inventa").

O que ele devolve a cada execução:
  - candidatos    número + unidade + mineral + empresa + período, com a frase de evidência e o endereço da fonte;
  - confrontos    'confirma', 'diverge', 'unidade_divergente', 'novo' ou 'sem_periodo', contra a base curada;
  - propostas     lacunas da própria metodologia: frase que claramente traz produção e nenhum padrão capturou, unidade desconhecida,
                  termo de mineral fora do léxico. Cada proposta vem com assinatura, contagem, fontes distintas e exemplos;
  - decisoes      o que o agente promoveu sozinho (só com auto_promocao.ativa) e por quê.

Roda toda segunda-feira às 02:00 pelo `minera-goias-producao.timer`. Só biblioteca padrão.
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

AGENTE_VERSAO = '0.1'
USER_AGENT = 'minera-goias-producao/0.1 (+https://github.com/mineragoias-rgb/minera-goias)'
MAX_FEED_BYTES = 8 * 1024 * 1024
SENTENCE = re.compile(r'(?<=[.!?;])\s+')
NUM = r'(?P<valor>\d{1,3}(?:[.,\s]\d{3})+(?:[.,]\d+)?|\d+(?:[.,]\d+)?)'
PALAVRA = re.compile(r'[a-z][a-z-]*')
# Pistas de que a frase fala de produção. Sem uma delas, um número solto não vira nem candidato nem proposta.
PISTAS_PRODUCAO = ['producao', 'produziu', 'produzidas', 'produzidos', 'produziram', 'produced', 'production',
                   'output', 'extraiu', 'beneficiou', 'embarcou', 'exportou', 'shipped', 'capacidade', 'capacity']


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def fold(text):
    """Minúsculas sem acento: 'nióbio' e 'niobio' viram o mesmo termo."""
    stripped = unicodedata.normalize('NFKD', str(text or ''))
    return ''.join(c for c in stripped if not unicodedata.combining(c)).lower()


def schema(connection):
    connection.executescript('''
    CREATE TABLE IF NOT EXISTS prod_runs(run_id TEXT PRIMARY KEY, started_at TEXT NOT NULL, finished_at TEXT,
      status TEXT NOT NULL, agente_versao TEXT NOT NULL, metodologia_versao TEXT NOT NULL, summary_json TEXT);
    CREATE TABLE IF NOT EXISTS prod_fontes(source_id TEXT PRIMARY KEY, name TEXT NOT NULL, url TEXT NOT NULL,
      lang TEXT, tipo TEXT, empresa TEXT, last_status TEXT, last_seen TEXT);
    CREATE TABLE IF NOT EXISTS prod_itens(item_id TEXT PRIMARY KEY, source_id TEXT NOT NULL, title TEXT NOT NULL,
      link TEXT NOT NULL, summary TEXT, published_at TEXT, first_seen TEXT NOT NULL, run_id TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS prod_candidatos(candidato_id TEXT PRIMARY KEY, item_id TEXT NOT NULL,
      run_id TEXT NOT NULL, padrao_id TEXT NOT NULL, empresa TEXT, mineral TEXT NOT NULL, valor REAL NOT NULL,
      valor_bruto TEXT NOT NULL, notacao TEXT NOT NULL, unidade TEXT NOT NULL, medida TEXT NOT NULL,
      tipo_valor TEXT NOT NULL, periodo TEXT, periodo_tipo TEXT,
      evidencia TEXT NOT NULL, fonte_url TEXT NOT NULL, confronto TEXT NOT NULL, delta_relativo REAL,
      registro_base TEXT, medida_base TEXT, medida_confere INTEGER,
      status_validacao TEXT NOT NULL DEFAULT 'nao_validado', criado_em TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS prod_padroes(padrao_id TEXT PRIMARY KEY, descricao TEXT, ativo INTEGER NOT NULL,
      origem TEXT, capturas INTEGER NOT NULL DEFAULT 0, fontes_distintas INTEGER NOT NULL DEFAULT 0,
      execucoes_sem_uso INTEGER NOT NULL DEFAULT 0, ultima_captura TEXT);
    CREATE TABLE IF NOT EXISTS prod_propostas(proposta_id TEXT PRIMARY KEY, tipo TEXT NOT NULL,
      assinatura TEXT NOT NULL, sugestao TEXT NOT NULL, ocorrencias INTEGER NOT NULL DEFAULT 0,
      fontes_json TEXT NOT NULL, execucoes_json TEXT NOT NULL, exemplos_json TEXT NOT NULL,
      status TEXT NOT NULL DEFAULT 'proposta', criada_em TEXT NOT NULL, atualizada_em TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS prod_decisoes(decisao_id TEXT PRIMARY KEY, run_id TEXT NOT NULL, tipo TEXT NOT NULL,
      alvo TEXT NOT NULL, motivo TEXT NOT NULL, detalhe_json TEXT, decidido_em TEXT NOT NULL);
    CREATE INDEX IF NOT EXISTS prod_candidatos_conf ON prod_candidatos(confronto);
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
    """RSS <item> e Atom <entry>; item sem link ou sem título é descartado."""
    root = ET.fromstring(payload)
    entries = []
    for node in root.iter():
        if node.tag.rsplit('}', 1)[-1] not in ('item', 'entry'):
            continue
        found = {}
        for child in node:
            name = child.tag.rsplit('}', 1)[-1]
            if name == 'link' and not (child.text or '').strip():
                found['link'] = child.attrib.get('href', '')
            else:
                found.setdefault(name, (child.text or '').strip())
        link, title = found.get('link', ''), strip_tags(found.get('title'))
        if not link or not title:
            continue
        entries.append({
            'title': title, 'link': link,
            'summary': strip_tags(found.get('description') or found.get('summary') or found.get('content')),
            'published_at': parse_date(found.get('pubDate') or found.get('published') or found.get('updated')),
        })
    return entries


# ------------------------------------------------------------------------------------------------- leitura de números e unidades
def alternativa(termos):
    """Alternância de regex com os termos mais longos primeiro, para 'terras raras' vencer 'terra'."""
    return '(?:' + '|'.join(re.escape(t) for t in sorted({fold(t) for t in termos}, key=len, reverse=True)) + ')'


def parse_numero(bruto, lang):
    """Lê o número decidindo pela própria grafia sempre que ela for inequívoca, e só então pelo idioma da fonte.

    '43,974' em pt seria 43 e em en 43.974 — uma fonte com idioma declarado errado erraria por mil sem avisar. As regras abaixo fecham o
    caso na maior parte das vezes; o que sobra é devolvido como ambíguo, para o candidato carregar essa marca até a revisão.

    Devolve (valor, 'inequivoca'|'ambigua_pelo_idioma') ou (None, motivo).
    """
    texto = str(bruto).replace(' ', '')
    pontos, virgulas = texto.count('.'), texto.count(',')
    if pontos and virgulas:                       # os dois aparecem: o último é o decimal
        decimal = ',' if texto.rfind(',') > texto.rfind('.') else '.'
        milhar = '.' if decimal == ',' else ','
        texto, notacao = texto.replace(milhar, '').replace(decimal, '.'), 'inequivoca'
    elif pontos > 1 or virgulas > 1:              # repetido: só pode ser separador de milhar
        texto, notacao = texto.replace('.', '').replace(',', ''), 'inequivoca'
    elif pontos or virgulas:
        separador = '.' if pontos else ','
        casas = len(texto.split(separador)[1])
        if casas == 3:                            # '10.348': milhar em pt, decimal em en — só o idioma decide
            milhar = '.' if lang == 'pt' else ','
            texto = texto.replace(separador, '') if separador == milhar else texto.replace(separador, '.')
            notacao = 'ambigua_pelo_idioma'
        else:                                     # 1, 2 ou 4+ casas: decimal em qualquer notação
            texto, notacao = texto.replace(separador, '.'), 'inequivoca'
    else:
        notacao = 'inequivoca'
    try:
        return float(texto), notacao
    except ValueError:
        return None, 'ilegivel'


def primeiro_termo(frase, mapa):
    """Primeira chave do mapa (na ordem em que foi declarada) cujo termo aparece na frase."""
    for chave, termos in mapa.items():
        if chave == 'comment':
            continue
        if any(re.search(rf'\b{re.escape(fold(t))}\b', frase) for t in termos):
            return chave
    return None


def le_periodo(frase, config):
    for padrao in config['periodo']['padroes']:
        achado = re.search(padrao['regex'], frase)
        if not achado:
            continue
        grupos = {k: v for k, v in achado.groupdict().items() if v}
        ordinais = {'primeiro': '1', 'segundo': '2', 'terceiro': '3', 'quarto': '4'}
        if 'n' in grupos:
            grupos['n'] = ordinais.get(grupos['n'], grupos['n'])
        elif padrao['tipo'] != 'ano':
            continue
        try:
            return padrao['formato'].format(**grupos), padrao['tipo']
        except KeyError:
            continue
    return None, None


def compila(config):
    """Monta as expressões dos padrões substituindo os marcadores pelos léxicos configurados."""
    escalas = alternativa(config['numero']['escalas'])
    unidades = alternativa([u for u in config['unidades'] if u != 'comment'])
    minerais = alternativa([m for m in config['minerais'] if m != 'comment'])
    compilados = []
    for padrao in config['padroes']:
        if not padrao.get('ativo'):
            continue
        fonte = (padrao['regex'].replace('{NUM}', NUM)
                 .replace('{ESC}', f'(?P<escala>{escalas})')
                 .replace('{UNI}', rf'(?P<unidade>{unidades})\b')
                 .replace('{MIN}', f'(?P<mineral>{minerais})'))
        compilados.append({**padrao, 'compilado': re.compile(fonte)})
    return compilados


def extrai(texto, lang, config, padroes, empresa_da_fonte):
    """Um candidato por padrão que casar numa frase. Período nunca é deduzido da data da matéria."""
    unidades, minerais = config['unidades'], config['minerais']
    aliases = {k: v for k, v in config['aliases_empresa'].items() if k != 'comment'}
    achados, vistos = [], set()
    for frase in SENTENCE.split(fold(texto)):
        if not frase.strip():
            continue
        empresa = empresa_da_fonte
        for alias, nome in aliases.items():
            if re.search(rf'\b{re.escape(fold(alias))}\b', frase):
                empresa = nome
                break
        periodo, periodo_tipo = le_periodo(frase, config)
        for padrao in padroes:
            for achado in padrao['compilado'].finditer(frase):
                grupos = achado.groupdict()
                valor, notacao = parse_numero(grupos['valor'], lang)
                unidade = unidades.get(grupos.get('unidade') or '')
                mineral = minerais.get(grupos.get('mineral') or '')
                if valor is None or not unidade or not mineral:
                    continue
                escala = config['numero']['escalas'].get(grupos.get('escala') or '', 1)
                valor = valor * escala * unidade['fator']
                chave = (empresa, mineral, round(valor, 4), unidade['canonica'], periodo)
                if chave in vistos:
                    continue
                vistos.add(chave)
                achados.append({
                    'padrao_id': padrao['id'], 'empresa': empresa, 'mineral': mineral,
                    'valor': round(valor, 4), 'valor_bruto': grupos['valor'], 'notacao': notacao,
                    'unidade': unidade['canonica'],
                    'medida': primeiro_termo(frase, config['medida_por_termo']) or 'produto_acabado',
                    'tipo_valor': primeiro_termo(frase, config['tipo_valor_por_termo']) or 'realizado',
                    'periodo': periodo, 'periodo_tipo': periodo_tipo, 'evidencia': frase.strip()[:400],
                })
    return achados


# --------------------------------------------------------------------------------------- propostas de metodologia (auto-melhoria)
def proxima_palavra(trecho):
    """Primeira palavra ou número do trecho, ignorando um 'de' de ligação. Devolve '' quando não há nenhuma."""
    achado = re.match(r'\s*(?:de\s+)?([a-z0-9]+)', trecho)
    return achado.group(1) if achado else ''


def propoe(texto, config, achados):
    """Lacunas da metodologia: frase que fala de produção com número e que os padrões ativos não capturaram.

    Três tipos, porque são três buracos diferentes e o conserto de cada um é diferente:
      padrao   — unidade e mineral conhecidos, mas nenhuma expressão cobre a construção da frase;
      unidade  — o token depois do número não está no léxico de unidades;
      mineral  — a frase tem número e unidade, mas nenhum termo de mineral conhecido.
    """
    unidades = {u for u in config['unidades'] if u != 'comment'}
    minerais = {m for m in config['minerais'] if m != 'comment'}
    capturados = {a['evidencia'] for a in achados}
    propostas = []
    for frase in SENTENCE.split(fold(texto)):
        frase = frase.strip()
        if not frase or frase[:400] in capturados:
            continue
        if not any(re.search(rf'\b{re.escape(p)}\b', frase) for p in PISTAS_PRODUCAO):
            continue
        for achado in re.finditer(NUM, frase):
            depois = frase[achado.end():achado.end() + 60].strip()
            token = proxima_palavra(depois)
            if token in {fold(e) for e in config['numero']['escalas']}:   # '1,21 milhao de toneladas': pula a escala
                token = proxima_palavra(depois[depois.find(token) + len(token):])
            antes = PALAVRA.findall(frase[:achado.start()])[-4:]
            tem_mineral = any(re.search(rf'\b{re.escape(m)}\b', frase) for m in minerais)
            if token and token not in unidades:
                tipo, assinatura, sugestao = 'unidade', token, f"acrescentar '{token}' ao léxico de unidades"
            elif token in unidades and not tem_mineral:
                alvo = re.search(rf'\b{re.escape(token)}\b\s+(?:de|of)\s+([a-z][a-z\s-]{{2,30}})', frase)
                termo = (alvo.group(1).strip() if alvo else '').split(' e ')[0][:30]
                if not termo:
                    continue
                tipo, assinatura, sugestao = 'mineral', termo, f"mapear '{termo}' para uma substância da ANM"
            elif token in unidades and tem_mineral:
                tipo = 'padrao'
                assinatura = ' '.join(antes) + ' {NUM} {UNI}'
                sugestao = (re.escape(' '.join(antes)) + r'\s+{NUM}\s*{ESC}?\s*{UNI}') if antes else ''
                if not sugestao:
                    continue
            else:
                continue
            propostas.append({'tipo': tipo, 'assinatura': assinatura, 'sugestao': sugestao, 'exemplo': frase[:300]})
    return propostas


# ---------------------------------------------------------------------------------------------- confronto com a base curada
def indexa_curada(curada):
    """(empresa, mineral, período) -> registros publicados, para o candidato ser confrontado com o que já foi curado."""
    indice = {}
    for empresa in curada['empresas']:
        for i, r in enumerate(empresa['registros']):
            chave = (empresa['empresa_operadora'], r['mineral'], r['periodo'])
            indice.setdefault(chave, []).append({**r, 'ref': f"{empresa['empresa_operadora']}[{i}]"})
    return indice


def confronta(candidato, indice, tolerancia):
    """Nunca converte unidade: unidade diferente é um resultado do confronto, não um problema a resolver por fator.

    Devolve (veredito, delta_relativo, referência na base, medida da base, se a medida bate). Valor igual com medida diferente continua
    'confirma' — mas a medida da base viaja junto, porque produção, embarque e capacidade não são a mesma grandeza.
    """
    if not candidato['periodo']:
        return 'sem_periodo', None, None, None, None
    registros = indice.get((candidato['empresa'], candidato['mineral'], candidato['periodo']))
    if not registros:
        return 'novo', None, None, None, None
    mesma_unidade = [r for r in registros if r['unidade'] == candidato['unidade']]
    if not mesma_unidade:
        return 'unidade_divergente', None, registros[0]['ref'], registros[0]['medida'], 0
    alvo = min(mesma_unidade, key=lambda r: abs(r['valor'] - candidato['valor']))
    delta = abs(alvo['valor'] - candidato['valor']) / alvo['valor'] if alvo['valor'] else None
    veredito = 'confirma' if delta is not None and delta <= tolerancia else 'diverge'
    return veredito, delta, alvo['ref'], alvo['medida'], 1 if alvo['medida'] == candidato['medida'] else 0


# ----------------------------------------------------------------------------------------------------------------- execução
def registra_proposta(connection, proposta, source_id, run_id, agora):
    proposta_id = hashlib.sha256(f"{proposta['tipo']}|{proposta['assinatura']}".encode()).hexdigest()[:32]
    linha = connection.execute('SELECT ocorrencias, fontes_json, execucoes_json, exemplos_json, status '
                               'FROM prod_propostas WHERE proposta_id=?', (proposta_id,)).fetchone()
    if linha:
        ocorrencias, fontes, execucoes, exemplos, status = linha[0] + 1, json.loads(linha[1]), json.loads(linha[2]), json.loads(linha[3]), linha[4]
        fontes, execucoes = sorted(set(fontes) | {source_id}), sorted(set(execucoes) | {run_id})
        exemplos = (exemplos + [proposta['exemplo']])[-5:]
        connection.execute('UPDATE prod_propostas SET ocorrencias=?,fontes_json=?,execucoes_json=?,exemplos_json=?,'
                           'atualizada_em=? WHERE proposta_id=?',
                           (ocorrencias, json.dumps(fontes), json.dumps(execucoes),
                            json.dumps(exemplos, ensure_ascii=False), agora, proposta_id))
    else:
        ocorrencias, fontes, execucoes, status = 1, [source_id], [run_id], 'proposta'
        connection.execute('INSERT INTO prod_propostas VALUES(?,?,?,?,?,?,?,?,?,?,?)',
                           (proposta_id, proposta['tipo'], proposta['assinatura'], proposta['sugestao'], 1,
                            json.dumps(fontes), json.dumps(execucoes),
                            json.dumps([proposta['exemplo']], ensure_ascii=False), status, agora, agora))
    return proposta_id, ocorrencias, len(fontes), len(execucoes), status


def coleta(connection, config, curada, fetcher, run_id):
    padroes = compila(config)
    indice = indexa_curada(curada)
    tolerancia = float(config['confronto']['tolerancia_relativa'])
    agora = timestamp()
    relatorio = {'fontes': [], 'novos_itens': 0, 'candidatos': 0, 'propostas': 0, 'erros': 0,
                 'confrontos': {}, 'padroes_usados': {}}
    usados_por_fonte = {}
    for fonte in config['fontes']:
        source_id = hashlib.sha256(fonte['url'].encode()).hexdigest()[:32]
        entrada = {'name': fonte['name'], 'tipo': fonte.get('tipo'), 'itens': 0, 'novos': 0, 'candidatos': 0}
        try:
            entradas = parse_feed(fetcher(fonte['url']))
            entrada['itens'] = len(entradas)
            connection.execute(
                'INSERT INTO prod_fontes VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(source_id) DO UPDATE '
                'SET last_status=excluded.last_status,last_seen=excluded.last_seen',
                (source_id, fonte['name'], fonte['url'], fonte.get('lang'), fonte.get('tipo'),
                 fonte.get('empresa'), 'ok', agora))
            for achado in entradas:
                item_id = hashlib.sha256(achado['link'].encode()).hexdigest()
                if connection.execute('SELECT 1 FROM prod_itens WHERE item_id=?', (item_id,)).fetchone():
                    continue
                connection.execute('INSERT INTO prod_itens VALUES(?,?,?,?,?,?,?,?)',
                                   (item_id, source_id, achado['title'], achado['link'], achado['summary'],
                                    achado['published_at'], agora, run_id))
                entrada['novos'] += 1
                relatorio['novos_itens'] += 1
                texto = f"{achado['title']}. {achado.get('summary') or ''}"
                candidatos = extrai(texto, fonte.get('lang', 'pt'), config, padroes, fonte.get('empresa'))
                for candidato in candidatos:
                    veredito, delta, ref, medida_base, medida_ok = confronta(candidato, indice, tolerancia)
                    candidato_id = hashlib.sha256(
                        f"{item_id}|{candidato['padrao_id']}|{candidato['mineral']}|{candidato['valor']}"
                        f"|{candidato['unidade']}|{candidato['periodo']}".encode()).hexdigest()[:32]
                    connection.execute(
                        'INSERT OR IGNORE INTO prod_candidatos VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                        (candidato_id, item_id, run_id, candidato['padrao_id'], candidato['empresa'],
                         candidato['mineral'], candidato['valor'], candidato['valor_bruto'], candidato['notacao'],
                         candidato['unidade'], candidato['medida'],
                         candidato['tipo_valor'], candidato['periodo'], candidato['periodo_tipo'],
                         candidato['evidencia'], achado['link'], veredito, delta, ref, medida_base, medida_ok,
                         'nao_validado', agora))
                    relatorio['candidatos'] += 1
                    entrada['candidatos'] += 1
                    relatorio['confrontos'][veredito] = relatorio['confrontos'].get(veredito, 0) + 1
                    if candidato['notacao'] == 'ambigua_pelo_idioma':
                        relatorio['numeros_ambiguos'] = relatorio.get('numeros_ambiguos', 0) + 1
                    if medida_ok == 0 and veredito == 'confirma':
                        relatorio['confirma_medida_distinta'] = relatorio.get('confirma_medida_distinta', 0) + 1
                    relatorio['padroes_usados'][candidato['padrao_id']] = relatorio['padroes_usados'].get(candidato['padrao_id'], 0) + 1
                    usados_por_fonte.setdefault(candidato['padrao_id'], set()).add(source_id)
                for proposta in propoe(texto, config, candidatos):
                    registra_proposta(connection, proposta, source_id, run_id, agora)
                    relatorio['propostas'] += 1
        except (urllib.error.URLError, ET.ParseError, OSError, ValueError) as erro:
            # Uma fonte fora do ar não derruba a execução inteira.
            entrada['erro'] = f'{type(erro).__name__}: {erro}'
            relatorio['erros'] += 1
            connection.execute(
                'INSERT INTO prod_fontes VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(source_id) DO UPDATE '
                'SET last_status=excluded.last_status,last_seen=excluded.last_seen',
                (source_id, fonte['name'], fonte['url'], fonte.get('lang'), fonte.get('tipo'),
                 fonte.get('empresa'), entrada['erro'][:200], agora))
        relatorio['fontes'].append(entrada)
        connection.commit()

    for padrao in config['padroes']:
        usos = relatorio['padroes_usados'].get(padrao['id'], 0)
        connection.execute(
            'INSERT INTO prod_padroes VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(padrao_id) DO UPDATE SET '
            'descricao=excluded.descricao, ativo=excluded.ativo, capturas=prod_padroes.capturas+excluded.capturas, '
            'fontes_distintas=MAX(prod_padroes.fontes_distintas, excluded.fontes_distintas), '
            'execucoes_sem_uso=CASE WHEN excluded.capturas>0 THEN 0 ELSE prod_padroes.execucoes_sem_uso+1 END, '
            'ultima_captura=CASE WHEN excluded.capturas>0 THEN excluded.ultima_captura ELSE prod_padroes.ultima_captura END',
            (padrao['id'], padrao.get('descricao'), 1 if padrao.get('ativo') else 0, padrao.get('origem'), usos,
             len(usados_por_fonte.get(padrao['id'], ())), 0 if usos else 1, agora if usos else None))
    connection.commit()
    return relatorio


def decide(connection, config, run_id):
    """Promoções e aposentadorias. Com auto_promocao desligada, o agente só anota o que promoveria."""
    regra = config['auto_promocao']
    agora = timestamp()
    decisoes = []
    linhas = connection.execute(
        'SELECT proposta_id, tipo, assinatura, sugestao, ocorrencias, fontes_json, execucoes_json, status '
        'FROM prod_propostas WHERE status=?', ('proposta',)).fetchall()
    for proposta_id, tipo, assinatura, sugestao, ocorrencias, fontes, execucoes, _ in linhas:
        elegivel = (ocorrencias >= regra['min_ocorrencias']
                    and len(json.loads(fontes)) >= regra['min_fontes_distintas']
                    and len(json.loads(execucoes)) >= regra['min_execucoes'])
        if not elegivel:
            continue
        acao = 'promovida' if regra['ativa'] else 'elegivel_aguardando_revisao'
        connection.execute('UPDATE prod_propostas SET status=?, atualizada_em=? WHERE proposta_id=?',
                           (acao, agora, proposta_id))
        motivo = (f'{ocorrencias} ocorrências em {len(json.loads(fontes))} fontes e '
                  f'{len(json.loads(execucoes))} execuções distintas')
        decisoes.append({'tipo': f'proposta_{tipo}', 'alvo': assinatura, 'acao': acao, 'motivo': motivo,
                         'sugestao': sugestao})

    limite = config['aposentadoria_de_padrao']['min_execucoes_sem_uso']
    for padrao_id, sem_uso in connection.execute(
            'SELECT padrao_id, execucoes_sem_uso FROM prod_padroes WHERE ativo=1 AND execucoes_sem_uso>=?',
            (limite,)).fetchall():
        decisoes.append({'tipo': 'padrao_sem_uso', 'alvo': padrao_id, 'acao': 'propor_aposentadoria',
                         'motivo': f'{sem_uso} execuções seguidas sem capturar nada', 'sugestao': ''})

    for decisao in decisoes:
        connection.execute('INSERT INTO prod_decisoes VALUES(?,?,?,?,?,?,?)',
                           (uuid.uuid4().hex[:32], run_id, decisao['tipo'], decisao['alvo'],
                            decisao['motivo'], json.dumps(decisao, ensure_ascii=False), agora))
    connection.commit()
    return decisoes


def pendencias(connection, curada):
    """O que a base curada ainda não tem e o agente deveria procurar: registro com observação de pendência."""
    faltando = []
    for empresa in curada['empresas']:
        for r in empresa['registros']:
            if 'nao foi localizado' in fold(r.get('observacao', '')):
                faltando.append({'empresa': empresa['empresa_operadora'], 'mineral': r['mineral'],
                                 'periodo': r['periodo'], 'nota': r['observacao'][:160]})
    return faltando


def run(database, config, curada, fetcher=fetch):
    connection = sqlite3.connect(database, timeout=30)
    try:
        schema(connection)
        run_id = uuid.uuid4().hex
        started = timestamp()
        connection.execute('INSERT INTO prod_runs VALUES(?,?,?,?,?,?,?)',
                           (run_id, started, None, 'running', AGENTE_VERSAO, config['metodologia_versao'], None))
        connection.commit()
        relatorio = coleta(connection, config, curada, fetcher, run_id)
        relatorio['decisoes'] = decide(connection, config, run_id)
        relatorio['pendencias_da_base'] = pendencias(connection, curada)
        relatorio.update(run_id=run_id, started_at=started, agente_versao=AGENTE_VERSAO,
                         metodologia_versao=config['metodologia_versao'])
        status = 'partial' if relatorio['erros'] else 'success'
        relatorio['status'] = status
        connection.execute('UPDATE prod_runs SET finished_at=?,status=?,summary_json=? WHERE run_id=?',
                           (timestamp(), status, json.dumps(relatorio, ensure_ascii=False), run_id))
        connection.commit()
        return relatorio
    finally:
        connection.close()


def offline_fetcher(directory, config=None):
    """Lê fixtures .xml, escolhendo pelo idioma declarado da fonte quando o nome do arquivo o traz ('feed-pt.xml').

    Entregar um texto em inglês a uma fonte declarada em português faria o agente ler '43,974' como 43,974 — o teste passaria a medir o
    engano da bancada, não o do agente.
    """
    files = sorted(Path(directory).glob('*.xml'))
    if not files:
        raise ValueError(f'nenhuma fixture .xml em {directory}')
    por_idioma = {}
    for arquivo in files:
        for idioma in ('pt', 'en'):
            if f'-{idioma}' in arquivo.stem:
                por_idioma.setdefault(idioma, []).append(arquivo)
    idioma_da_url = {f['url']: f.get('lang') for f in (config or {}).get('fontes', [])}
    state = {}

    def fetcher(url):
        disponiveis = por_idioma.get(idioma_da_url.get(url)) or files
        i = state.get(id(disponiveis), 0)
        state[id(disponiveis)] = i + 1
        return disponiveis[i % len(disponiveis)].read_bytes()
    return fetcher


def check(config, fetcher=fetch):
    resultados = []
    for fonte in config['fontes']:
        entrada = {'name': fonte['name'], 'tipo': fonte.get('tipo')}
        try:
            entradas = parse_feed(fetcher(fonte['url']))
            entrada.update(status='ok', items=len(entradas))
        except (urllib.error.URLError, ET.ParseError, OSError, ValueError) as erro:
            entrada.update(status='falhou', items=0, error=f'{type(erro).__name__}: {erro}'[:120])
        resultados.append(entrada)
    return resultados


def main(argv=None):
    raiz = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description='Agente semanal da base de produção mineral por empresa.')
    parser.add_argument('--db', default='/var/lib/minera-goias-producao/producao.sqlite')
    parser.add_argument('--config', default=str(raiz / 'fontes.json'))
    parser.add_argument('--base', default=str(raiz / 'base_curada.json'))
    parser.add_argument('--report', help='grava o relatório da execução como JSON neste caminho')
    parser.add_argument('--offline-dir', help='lê fixtures .xml em vez da rede')
    parser.add_argument('--check', action='store_true', help='só testa se cada fonte responde, sem gravar nada')
    args = parser.parse_args(argv)

    config = json.loads(Path(args.config).read_text(encoding='utf-8'))
    curada = json.loads(Path(args.base).read_text(encoding='utf-8'))
    if args.check:
        fetcher = offline_fetcher(args.offline_dir, config) if args.offline_dir else fetch
        vivas = 0
        for entrada in check(config, fetcher):
            marca = 'ok   ' if entrada['status'] == 'ok' else 'FALHA'
            vivas += entrada['status'] == 'ok'
            detalhe = f"{entrada['items']:>3} itens" if entrada['status'] == 'ok' else entrada.get('error', '')
            print(f"  {marca} [{entrada.get('tipo') or '-':<7}] {entrada['name']:<44} {detalhe}")
        print(f'{vivas}/{len(config["fontes"])} fontes responderam')
        return 0 if vivas else 1

    Path(args.db).parent.mkdir(parents=True, exist_ok=True)
    fetcher = offline_fetcher(args.offline_dir, config) if args.offline_dir else fetch
    relatorio = run(args.db, config, curada, fetcher)
    if args.report:
        Path(args.report).write_text(json.dumps(relatorio, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps({k: relatorio.get(k) for k in ('run_id', 'status', 'novos_itens', 'candidatos', 'propostas',
                                                    'erros', 'numeros_ambiguos', 'confirma_medida_distinta')},
                     ensure_ascii=False))
    for veredito, quantos in sorted(relatorio['confrontos'].items()):
        print(f"  confronto {veredito:<20} {quantos}")
    for decisao in relatorio['decisoes']:
        print(f"  decisão   {decisao['acao']:<32} {decisao['tipo']}: {decisao['alvo'][:60]} ({decisao['motivo']})")
    for pendencia in relatorio['pendencias_da_base']:
        print(f"  pendência {pendencia['empresa'][:34]:<34} {pendencia['mineral']} {pendencia['periodo']}")
    return 0 if relatorio['status'] == 'success' else 1


if __name__ == '__main__':
    sys.exit(main())
