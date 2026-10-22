# -*- coding: utf-8 -*-
"""Gera os dados do Mapa Mineral de Goiás (data/mapa/) a partir do catálogo scripts/mapa_camadas.json.

Entradas (todas no repositório):
  Squad 1/P3M/Recortado pelo polígono de Goiás/<pasta temática>/*.zip   camadas do P3M já cortadas pelo limite de Goiás (SIRGAS 2000)
  Squad 1/P3M/Original/6- Cartografia/GO_UF_2024.zip                     limite estadual do IBGE usado no recorte (marca as feições na divisa)
  Squad 1/P3M/inventario_p3m.csv                                         data de download de cada zip (retrato de cada camada)
  data/atlas/atlas.json e processes.json               municípios, CFEM, projetos (aba 04), ocorrências e processos já publicados
  Squad 1/Radar de Projetos/ e Squad 1/Dados brutos/   Radar de Projetos e titulares PJ (scripts/build_projetos_minerais_goias.py)
  Squad 1/Bases consolidadas/documentacao/prototipo_bases_consolidadas_v17.xlsx   crosswalk de substâncias (aba 01b)

Saídas (data/mapa/):
  catalogo.json      grupos, camadas e tabelas: origem, campos com rótulo/tipo/unidade, datas, legenda, carga, tamanho e contagens
  camadas/<id>.json  geometria quantizada (convenção de data/atlas/processes.json) e atributos em colunas
  tabelas/<id>.json  municipios, radar_projetos e processos_complemento (titular, municípios e mineral de cada processo do Atlas)
  validacao.json     contagens, chaves, junções, extensão, recorte e tamanhos

As camadas com origem 'atlas' no catálogo não são copiadas: o mapa lê /api/atlas e /api/atlas/processes.
A saída não tem data de geração: rodar de novo com as mesmas entradas grava os mesmos bytes.

Uso (precisa de pyshp, shapely >= 2 e openpyxl):
    python scripts/build_mapa_base.py            # gera data/mapa/
    python scripts/build_mapa_base.py --checar   # só valida e mostra o resumo, sem gravar
"""
import argparse
import base64
import collections
import csv
import io
import json
import re
import sys
import zipfile
from array import array
from pathlib import Path

import shapefile  # pyshp
import shapely
from shapely.geometry import shape as geometria_de

RAIZ = Path(__file__).resolve().parents[1]
CATALOGO = RAIZ / 'scripts' / 'mapa_camadas.json'
SAIDA = RAIZ / 'data' / 'mapa'
ATLAS = RAIZ / 'data' / 'atlas' / 'atlas.json'
PROCESSOS_ATLAS = RAIZ / 'data' / 'atlas' / 'processes.json'
PLANILHA = RAIZ / 'Squad 1' / 'Bases consolidadas' / 'documentacao' / 'prototipo_bases_consolidadas_v17.xlsx'
GRUPOS_ATLAS = ['Lavra / extração autorizada', 'Pesquisa autorizada', 'Requerimento em análise', 'Disponibilidade', 'Outros']

# Caixa de Goiás com folga: o que cair fora dela indica CRS errado ou latitude e longitude trocadas.
CAIXA_GO = (-53.5, -19.8, -45.6, -12.2)
FOLGA_DIVISA = 1e-5          # graus (~1 m): feição a essa distância do limite estadual "encosta na divisa"
FOLGA_PONTO = 0.01           # graus (~1 km): ponto mais longe que isso do polígono de Goiás é erro
CPF = re.compile(r'\d{3}\.\d{3}\.\d{3}-\d{2}')
UNIDADE_CRS = 'EPSG:4674 — SIRGAS 2000, longitude e latitude em graus'
MESES = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']

sys.path.insert(0, str(RAIZ / 'scripts'))
import build_projetos_minerais_goias as radar  # noqa: E402  regra de titular PJ, contexto de municípios e o próprio Radar


def sem_acento(s):
    return radar.sem_acento(s)


def b64(valores, tipo):
    return base64.b64encode(array(tipo, valores).tobytes()).decode('ascii')


def chave_processo(v):
    """'860.337/2020', '860337/2020' e '009291/1967' viram a mesma chave '860337/2020' (número sem zeros à esquerda / ano)."""
    if v is None:
        return None
    m = re.fullmatch(r'\s*(\d{1,3}(?:\.\d{3})+|\d+)\s*/\s*(\d{4})\s*', str(v))
    return f"{int(m.group(1).replace('.', ''))}/{m.group(2)}" if m else None


def municipios_por_nome(texto, mapa):
    """Texto de município da fonte -> (códigos IBGE de Goiás, pedaços sem correspondência). Aceita 'SILVÂNIA/GO', 'ARAGUARI/MG, CORUMBAÍBA/GO',
    'BARRO ALTO E SANTA RITA DO NOVO DESTINO' e 'CAVALCANTE/TERESINA DE GOIÁS'; nome de outra UF é ignorado, nunca casado com Goiás."""
    t = re.sub(r'\s+', ' ', sem_acento(texto))
    if t in mapa:
        return [mapa[t]], []
    pares = re.findall(r'([^,/;]+?)\s*/\s*([A-Z]{2})\b', t)
    nomes = [n for n, uf in pares if uf == 'GO'] if pares else re.split(r'\s*(?:,|/|;|\bE\b)\s*', t)
    codigos, fora = set(), []
    for n in nomes:
        n = re.sub(r'\s*-\s*GO$', '', n.strip())
        if n in mapa:
            codigos.add(mapa[n])
        elif n:
            fora.append(n)
    return sorted(codigos), fora


def data_iso(v):
    s = str(v).strip()
    m = re.match(r'(\d{4})[/-](\d{2})[/-](\d{2})', s)
    if m:
        return f'{m.group(1)}-{m.group(2)}-{m.group(3)}'
    m = re.match(r'(\d{2})[/-](\d{2})[/-](\d{4})', s)
    if m:
        return f'{m.group(3)}-{m.group(2)}-{m.group(1)}'
    return None


# ---------------------------------------------------------------- leitura
def abrir_zip(caminho):
    """Lê o shapefile de um zip do P3M em memória. Devolve (reader, texto do .prj)."""
    z = zipfile.ZipFile(caminho)
    por_ext = collections.defaultdict(list)
    for n in z.namelist():
        por_ext[n.lower().rsplit('.', 1)[-1]].append(n)
    assert len(por_ext['shp']) == 1, f'{caminho.name}: esperado um .shp, há {len(por_ext["shp"])}'
    cpg = z.read(por_ext['cpg'][0]).decode('ascii').strip() if por_ext['cpg'] else 'utf-8'
    leitor = shapefile.Reader(shp=io.BytesIO(z.read(por_ext['shp'][0])), shx=io.BytesIO(z.read(por_ext['shx'][0])),
                              dbf=io.BytesIO(z.read(por_ext['dbf'][0])), encoding=cpg or 'utf-8')
    prj = z.read(por_ext['prj'][0]).decode('utf-8', 'replace') if por_ext['prj'] else ''
    return leitor, prj


def conferir_crs(nome, prj, bbox):
    """SIRGAS 2000 geográfico, x = longitude e y = latitude, dentro da caixa de Goiás."""
    erros = []
    if 'SIRGAS' not in prj.upper() or 'PROJCS' in prj.upper():
        erros.append(f'{nome}: .prj não é SIRGAS 2000 geográfico')
    x0, y0, x1, y1 = bbox
    if CAIXA_GO[1] <= x0 and x1 <= CAIXA_GO[3] and CAIXA_GO[0] <= y0 and y1 <= CAIXA_GO[2]:
        erros.append(f'{nome}: latitude e longitude trocadas')
    elif not (CAIXA_GO[0] <= x0 and x1 <= CAIXA_GO[2] and CAIXA_GO[1] <= y0 and y1 <= CAIXA_GO[3]):
        erros.append(f'{nome}: extensão {bbox} fora da caixa de Goiás')
    return erros


def limite_goias(cfg):
    leitor, prj = abrir_zip(RAIZ / cfg['p3m']['limite_estadual'])
    assert 'SIRGAS' in prj.upper(), 'GO_UF_2024 fora de SIRGAS 2000'
    return shapely.union_all([geometria_de(s.__geo_interface__) for s in leitor.shapes()])


def indice_recorte(cfg):
    caminho = RAIZ / cfg['p3m']['pasta'] / cfg['p3m']['indice']
    with open(caminho, encoding='utf-8-sig', newline='') as f:
        return {r['arquivo']: r for r in csv.DictReader(f, delimiter=';')}


def crosswalk_minerais():
    """Grafia da substância (ANM) -> categoria da ANM, pela aba 01b da base consolidada. Grafia com mais de uma categoria fica ambígua."""
    import openpyxl
    wb = openpyxl.load_workbook(PLANILHA, read_only=True)
    linhas = list(wb['01b_crosswalk_pente_fino'].iter_rows(values_only=True))
    inicio = next(i for i, r in enumerate(linhas) if r and r[0] == 'fonte') + 1
    destinos = collections.defaultdict(set)
    for r in linhas[inicio:]:
        if r and r[0] and r[1] and str(r[4] or '').startswith('MIN_'):
            destinos[sem_acento(r[1])].add(str(r[4]).split('—', 1)[1].strip())
    return {k: next(iter(v)) for k, v in destinos.items() if len(v) == 1}, {k for k, v in destinos.items() if len(v) > 1}


def categorias_minerais():
    """As 67 categorias da ANM da aba 01_dim_minerais: (nome sem acento -> nome oficial, mineral_id -> nome oficial)."""
    import openpyxl
    wb = openpyxl.load_workbook(PLANILHA, read_only=True)
    linhas = list(wb['01_dim_minerais'].iter_rows(values_only=True))
    inicio = next(i for i, r in enumerate(linhas) if r and r[0] == 'mineral_id') + 1
    validas = [r for r in linhas[inicio:] if r and r[0] and r[1]]
    return {sem_acento(r[1]): r[1] for r in validas}, {r[0]: r[1] for r in validas}


def titulares_pj(ctx):
    """Processo (chave normalizada) -> titular publicável: nome de PJ ou o rótulo de pessoa física sem nome."""
    saida = {}
    for proc, (nome, _cnpj) in radar.titular_por_processo(ctx).items():
        k = chave_processo(proc)
        if k:
            saida[k] = publicar_titular(nome)
    return saida


def reparar_codificacao(texto):
    """Texto UTF-8 que a fonte gravou lido como Latin-1 ('CERÃ¢MICA') volta ao certo ('CERÂMICA'); texto correto passa intacto.
    A fonte às vezes passou o texto já estragado para maiúsculas: o 'µ' de 'õ' virou o 'Μ' grego ('PARTICIPAÃ§ÃΜES'); ele volta antes.
    Nome que estava todo em maiúsculas continua em maiúsculas. Sem isso, 'INÃ¡CIA' isolava um 'CIA' e o nome de pessoa passava por empresa."""
    if not isinstance(texto, str) or not re.search('[ÃÂ][\x80-\xbf\u039c]', texto):
        return texto
    try:
        certo = texto.replace('Ã\u039c', 'Ã\xb5').encode('latin-1').decode('utf-8')
    except (UnicodeEncodeError, UnicodeDecodeError):
        return texto
    return certo.upper() if texto == texto.upper() else certo


def publicar_titular(nome):
    nome = reparar_codificacao((nome or '').strip())
    if not nome:
        return None
    return radar.TITULAR_INDIVIDUAL if CPF.search(nome) else radar.titular_publico(nome)


# ---------------------------------------------------------------- geometria
def partes(geom, tipo):
    """Pontos, linhas ou anéis (lon, lat) de uma geometria, só do tipo da camada."""
    if geom is None or geom.is_empty:
        return []
    simples = [geom] if not hasattr(geom, 'geoms') else list(geom.geoms)
    if any(hasattr(g, 'geoms') for g in simples):  # coleção aninhada (make_valid)
        return [p for g in simples for p in partes(g, tipo)]
    if tipo == 'ponto':
        return [[(g.x, g.y)] for g in simples if g.geom_type == 'Point']
    if tipo == 'linha':
        return [list(g.coords) for g in simples if g.geom_type == 'LineString']
    return [list(anel.coords)[:-1] for g in simples if g.geom_type == 'Polygon' for anel in (g.exterior, *g.interiors)]


def quantizar(geoms, tipo, caixa):
    """Mesma convenção de data/atlas/processes.json: x = longitude e y = latitude invertida em Uint16 (0–65535) na caixa da camada.
    Uma 'parte' é um ponto, uma linha ou um anel; partStart[k]..partStart[k+1] são os vértices da parte k e partFeat[k] a feição."""
    lon0, lat0, lon1, lat1 = caixa['lon0'], caixa['lat0'], caixa['lon1'], caixa['lat1']

    def q(lon, lat):
        return (int(round((lon - lon0) / (lon1 - lon0) * 65535)), int(round((lat1 - lat) / (lat1 - lat0) * 65535)))

    minimo = {'ponto': 1, 'linha': 2, 'poligono': 3}[tipo]
    xy, inicio, dono = [], [0], []
    for i, (g, original) in enumerate(geoms):
        lista = []
        for pts in partes(g, tipo):
            seq = []
            for lon, lat in pts:
                k = q(lon, lat)
                if not seq or seq[-1] != k:
                    seq.append(k)
            if tipo == 'poligono' and len(seq) > 1 and seq[0] == seq[-1]:
                seq.pop()
            if len(seq) >= minimo:
                lista.append(seq)
        if not lista and original is not None and not original.is_empty:
            # feição menor que o passo da quantização (~12 m): mantém os vértices originais, mesmo repetidos, para não sumir do mapa
            lista = [[q(lon, lat) for lon, lat in pts] for pts in partes(original, tipo)[:1]]
        for seq in lista:
            for x, y in seq:
                xy.extend((x, y))
            inicio.append(inicio[-1] + len(seq))
            dono.append(i)
    return {'xy': b64(xy, 'H'), 'partStart': b64(inicio, 'I'), 'partFeat': b64(dono, 'I')}, len(dono), len(xy) // 2


def caixa_da_camada(geoms):
    x0, y0, x1, y1 = shapely.total_bounds([g for g in geoms if g is not None])
    # evita caixa degenerada (um ponto só) e arredonda para fora em 1e-6 grau
    if x1 - x0 < 1e-4:
        x0, x1 = x0 - 5e-5, x1 + 5e-5
    if y1 - y0 < 1e-4:
        y0, y1 = y0 - 5e-5, y1 + 5e-5
    return {'lon0': round(x0 - 5e-7, 6), 'lat0': round(y0 - 5e-7, 6), 'lon1': round(x1 + 5e-7, 6), 'lat1': round(y1 + 5e-7, 6)}


# ---------------------------------------------------------------- atributos
class Coluna:
    """Converte um campo da fonte para o tipo do catálogo e conta nulos e valores que não converteram."""

    def __init__(self, spec, nulos, minerais, ambiguos, posicao, mun_por_nome):
        self.spec, self.nulos = spec, nulos
        self.minerais, self.ambiguos, self.posicao, self.mun_por_nome = minerais, ambiguos, posicao, mun_por_nome
        self.n_nulos = 0
        self.nao_convertidos = collections.Counter()
        self.sem_mineral = collections.Counter()
        self.sem_municipio = collections.Counter()

    def nulo(self, v):
        if v is None:
            return True
        s = str(v).strip()
        return s in self.nulos or s.casefold() in self.nulos

    def ler(self, rec, constantes):
        sp = self.spec
        tipo = sp['tipo']
        if tipo == 'titular':
            return None  # preenchido à parte
        if tipo == 'posicao':
            v = rec.get(self.posicao['campo'])
            return self.posicao['rotulos'].get(str(v).strip()) if v is not None else None
        if 'fonte' not in sp:
            return constantes.get(sp['id'])
        if isinstance(sp['fonte'], list):  # processo partido em número e ano
            partes_ = [rec.get(f) for f in sp['fonte']]
            v = None if any(self.nulo(p) for p in partes_) else '/'.join(str(p).strip() for p in partes_)
        else:
            v = rec.get(sp['fonte'])
        if self.nulo(v):
            self.n_nulos += 1
            return None
        s = reparar_codificacao(str(v).strip())
        try:
            if tipo == 'processo':
                k = chave_processo(s)
                if k is None:
                    raise ValueError
                return k
            if tipo == 'numero':
                x = float(s.replace(',', '.')) if isinstance(v, str) else float(v)
                if sp.get('zero_e_nulo') and x == 0:
                    self.n_nulos += 1
                    return None
                x *= sp.get('fator', 1)
                return round(x, sp.get('casas', 6))
            if tipo == 'inteiro':
                return int(float(s))
            if tipo == 'ano':
                ano = int(float(s[:4]))
                if sp.get('zero_e_nulo') and ano == 0:
                    self.n_nulos += 1
                    return None
                if not 1800 <= ano <= 2100:
                    raise ValueError
                return ano
            if tipo == 'data':
                d = data_iso(s)
                if d is None:
                    raise ValueError
                return d
            if tipo == 'url':
                if not s.startswith('http'):
                    raise ValueError
                return s
            if tipo == 'municipios':
                codigos = [c.strip() for c in s.split(',')]
                if not all(re.fullmatch(r'\d{7}', c) for c in codigos):
                    raise ValueError
                return codigos
            if tipo == 'municipio':
                if not re.fullmatch(r'\d{7}', s):
                    raise ValueError
                return s
            if tipo == 'municipios_nome':
                codigos, fora = municipios_por_nome(s, self.mun_por_nome)
                for n in fora:
                    self.sem_municipio[n] += 1
                return codigos or None
            if tipo == 'mineral':
                k = sem_acento(s)
                if k in self.minerais:
                    return self.minerais[k]
                self.sem_mineral[('ambígua: ' if k in self.ambiguos else '') + s] += 1
                return None
            if tipo == 'lista':
                return [x.strip() for x in s.split(sp['separador'])] if sp.get('separador') else s
            return s  # texto, categoria
        except (ValueError, TypeError):
            self.nao_convertidos[s] += 1
            return None


def agrupar(registros, campos, chave, ordenar_por):
    """Junta os registros da fonte que são a mesma feição (mesma chave): a geometria vira uma só e cada campo segue a regra 'agregar'."""
    grupos = collections.OrderedDict()
    for r in registros:
        grupos.setdefault(r['valores'][chave], []).append(r)
    saida, conflitos, unidas = [], collections.Counter(), 0
    for k, rs in grupos.items():
        if ordenar_por:  # números da guia vêm como texto: ordena pelo valor numérico
            rs.sort(key=lambda r: (r['valores'][ordenar_por] is None,
                                   float(r['valores'][ordenar_por]) if re.fullmatch(r'\d+(\.\d+)?', str(r['valores'][ordenar_por])) else float('inf'),
                                   str(r['valores'][ordenar_por])))
        geoms = [r['geom'] for r in rs if r['geom'] is not None]
        wkbs = {g.wkb for g in geoms}
        if len(wkbs) > 1:
            unidas += 1
            geom = shapely.union_all(geoms)
        else:
            geom = geoms[0] if geoms else None
        valores = {}
        for c in campos:
            cid, regra = c['id'], c.get('agregar')
            vs = [r['valores'][cid] for r in rs]
            if regra == 'distintos':
                planos = [x for v in vs if v is not None for x in (v if isinstance(v, list) else [v])]
                valores[cid] = sorted(set(planos), key=sem_acento) or None
            elif regra == 'alinhado':
                valores[cid] = vs
            else:
                distintos = {json.dumps(v, ensure_ascii=False) for v in vs}
                if len(distintos) > 1:
                    conflitos[cid] += 1
                valores[cid] = vs[0]
        saida.append({'geom': geom, 'valores': valores, 'n_fonte': len(rs)})
    return saida, conflitos, unidas


def colunas_de_saida(feicoes, campos):
    """Atributos em colunas. Categorias, listas, minerais e municípios viram índice de um dicionário (dic) para encolher o arquivo."""
    valores, dic = {}, {}
    for c in campos:
        cid, tipo = c['id'], c['tipo']
        coluna = [f['valores'][cid] for f in feicoes]
        codificar = tipo in ('categoria', 'mineral', 'municipios', 'municipios_nome', 'posicao', 'titular') or (tipo == 'lista')
        if not codificar:
            valores[cid] = coluna
            continue
        planos = sorted({x for v in coluna if v is not None for x in (v if isinstance(v, list) else [v]) if x is not None}, key=str)
        pos = {x: i for i, x in enumerate(planos)}
        dic[cid] = planos
        valores[cid] = [None if v is None else [None if x is None else pos[x] for x in v] if isinstance(v, list) else pos[v] for v in coluna]
    return valores, dic


# ---------------------------------------------------------------- camadas do P3M
def zips_p3m(pasta):
    """Nome do zip -> caminho, em qualquer pasta temática (Squad 1/P3M é organizado por tema desde 22/10/2026)."""
    achados = collections.defaultdict(list)
    for z in pasta.rglob('*.zip'):
        achados[z.name].append(z)
    repetidos = {n: v for n, v in achados.items() if len(v) > 1}
    assert not repetidos, f'zip com o mesmo nome em mais de uma pasta: {repetidos}'
    return {n: v[0] for n, v in achados.items()}


def baixados_no_retrato(cfg):
    """Zips cuja data de download no inventário do P3M é a do retrato de 21/10/2026 (antes: os da pasta 'Baixados')."""
    with open(RAIZ / cfg['p3m']['inventario'], encoding='utf-8-sig', newline='') as f:
        return {Path(a).name for r in csv.DictReader(f, delimiter=';') if r['data_download'] == cfg['p3m']['retrato_baixados']
                for a in r['arquivo_original'].split(';') if a}


def camada_p3m(spec, cfg, go, faixa_divisa, indice, minerais, ambiguos, titular_proc, mun_por_nome):
    zips = zips_p3m(RAIZ / cfg['p3m']['pasta'])
    baixados = baixados_no_retrato(cfg)
    nulos = set(cfg['nulos_padrao']) | {s.casefold() for s in cfg['nulos_padrao']}
    tipo = spec['geometria']
    val = {'arquivos': [], 'erros': [], 'alertas': []}
    colunas = [Coluna(c, nulos | set(c.get('nulos', [])), minerais, ambiguos, spec.get('posicao'), mun_por_nome) for c in spec['campos']]
    registros, retratos = [], set()
    titular_origem = collections.Counter()
    ausentes = collections.defaultdict(list)  # campo -> arquivos da camada que não o têm (fica nulo nesses arquivos)
    for arq in spec['origem']['arquivos']:
        nome = arq['arquivo']
        leitor, prj = abrir_zip(zips[nome])
        val['erros'] += conferir_crs(nome, prj, leitor.bbox)
        n = len(leitor)
        esperado = int(indice[nome]['registros_em_goias']) if nome in indice else None
        if esperado is not None and esperado != n:
            val['erros'].append(f'{nome}: {n} registros, o índice do recorte diz {esperado}')
        retratos.add(cfg['p3m']['retrato_baixados'] if nome in baixados else cfg['p3m']['retrato_primeiros'])
        val['arquivos'].append({'arquivo': nome, 'registros': n, 'registros_no_indice': esperado,
                                'fiapos_removidos_no_recorte': int(indice[nome]['fiapos_de_divisa_removidos']) if nome in indice else None})
        campos_fonte = [f[0] for f in leitor.fields[1:]]
        for c in spec['campos']:
            for f in ([c['fonte']] if isinstance(c.get('fonte'), str) else c.get('fonte') or []):
                if f not in campos_fonte:
                    ausentes[f].append(nome)
        for sr in leitor.iterShapeRecords():
            rec = sr.record.as_dict()
            geom = None if sr.shape.shapeType == shapefile.NULL else geometria_de(sr.shape.__geo_interface__)
            if geom is not None and not geom.is_valid:
                geom = shapely.make_valid(geom)
                val['geometrias_reparadas'] = val.get('geometrias_reparadas', 0) + 1
            valores = {c.spec['id']: c.ler(rec, arq.get('constantes', {})) for c in colunas}
            if 'titular' in spec:
                t = spec['titular']
                proc = chave_processo(rec.get(t['processo'])) if t.get('processo') else None
                if proc and proc in titular_proc:
                    valores['titular'] = titular_proc[proc]
                    titular_origem['Cadastro Mineiro / SIGMINE pelo processo'] += 1
                else:
                    nome_t = rec.get(t['nome']) or (rec.get(t['alternativo']) if t.get('alternativo') else None)
                    valores['titular'] = publicar_titular(nome_t)
                    titular_origem['nome da própria camada' if valores['titular'] else 'sem titular'] += 1
            registros.append({'geom': geom, 'valores': valores})
    val['registros_fonte'] = len(registros)
    for f, arquivos in ausentes.items():
        if len(arquivos) == len(spec['origem']['arquivos']):
            val['erros'].append(f'campo {f} não existe na fonte')
    if ausentes:
        val['campos_ausentes_em_arquivos'] = dict(ausentes)
    campos = list(spec['campos'])
    if spec.get('agrupar_por'):
        feicoes, conflitos, unidas = agrupar(registros, campos, spec['agrupar_por'], spec.get('ordenar_grupo_por'))
        val['agrupamento'] = {'por': spec['agrupar_por'], 'registros': len(registros), 'feicoes': len(feicoes),
                              'geometrias_diferentes_unidas': unidas, 'campos_com_valor_diferente_no_grupo': dict(conflitos)}
        campos.append({'id': 'n_registros_fonte', 'rotulo': 'Registros na fonte', 'rotulo_en': 'Source records', 'tipo': 'inteiro'})
        for f in feicoes:
            f['valores']['n_registros_fonte'] = f['n_fonte']
    else:
        feicoes = [{'geom': r['geom'], 'valores': r['valores']} for r in registros]
    feicoes.sort(key=lambda f: (str(f['valores'].get(spec['chave'])), json.dumps(f['valores'], ensure_ascii=False, sort_keys=True, default=str)))

    # chave, geometria ausente, posição e divisa
    chaves = [f['valores'].get(spec['chave']) for f in feicoes]
    contagem = collections.Counter(chaves)
    val['chave'] = {'campo': spec['chave'], 'feicoes': len(chaves), 'distintos': len(contagem),
                    'sem_chave': contagem.get(None, 0), 'duplicados': sorted((str(k) for k, n in contagem.items() if n > 1 and k is not None))[:20]}
    if val['chave']['duplicados']:
        val['alertas'].append(f"chave {spec['chave']} repetida em {sum(1 for k, n in contagem.items() if n > 1 and k is not None)} valores")
    sem_geom = [i for i, f in enumerate(feicoes) if f['geom'] is None or f['geom'].is_empty]
    val['sem_geometria'] = len(sem_geom)
    geoms = [f['geom'] for f in feicoes]
    validas = [g for g in geoms if g is not None and not g.is_empty]
    if tipo == 'ponto':
        longe = sum(1 for g in validas if not shapely.dwithin(go, g, FOLGA_PONTO))
        val['pontos_fora_de_goias'] = longe
        if longe:
            val['erros'].append(f'{longe} pontos a mais de {FOLGA_PONTO}° do polígono de Goiás')
    else:
        na_divisa = [bool(g is not None and not g.is_empty and faixa_divisa.intersects(g)) for g in geoms]
        val['na_divisa'] = sum(na_divisa)
        campos.append({'id': 'na_divisa', 'rotulo': 'Encosta na divisa estadual (pode ter sido cortada no recorte)',
                       'rotulo_en': 'Touches the state border (may have been clipped)', 'tipo': 'booleano'})
        for f, d in zip(feicoes, na_divisa):
            f['valores']['na_divisa'] = d

    # simplificação: o detalhe fica no zip de origem; aqui só o desenho para a web
    tol = spec.get('tolerancia', 0)
    pares = []
    vert_antes = vert_depois = mantidas = 0
    for g in geoms:
        if g is None or g.is_empty:
            pares.append((None, None))
            continue
        s = g
        if tol and tipo != 'ponto':
            s = shapely.simplify(g, tol, preserve_topology=True)
            if s.is_empty or not s.is_valid:
                s, mantidas = g, mantidas + 1
        vert_antes += int(shapely.get_num_coordinates(g))
        vert_depois += int(shapely.get_num_coordinates(s))
        pares.append((s, g))
    caixa = caixa_da_camada(validas) if validas else {'lon0': 0, 'lat0': 0, 'lon1': 1, 'lat1': 1}
    geo, n_partes, n_vertices = quantizar(pares, tipo, caixa)
    val['simplificacao'] = {'tolerancia_graus': tol, 'vertices_fonte': vert_antes, 'vertices_simplificados': vert_depois,
                            'vertices_publicados': n_vertices, 'partes': n_partes, 'mantidas_sem_simplificar': mantidas}
    val['extensao'] = caixa

    if spec.get('posicao'):
        aprox = {spec['posicao']['rotulos'][v] for v in spec['posicao']['aproximada']}
        val['posicao_aproximada'] = sum(1 for f in feicoes if f['valores'].get('posicionamento') in aprox)
        val['posicao_sem_informacao'] = sum(1 for f in feicoes if f['valores'].get('posicionamento') is None)

    # titular, nulos e junções
    if 'titular' in spec:
        val['titular'] = dict(titular_origem)
    val['nulos'] = {c.spec['id']: c.n_nulos for c in colunas if c.n_nulos}
    val['nao_convertidos'] = {c.spec['id']: dict(c.nao_convertidos.most_common(10)) for c in colunas if c.nao_convertidos}
    val['mineral_sem_categoria'] = {}
    for c in colunas:
        if c.sem_mineral:
            val['mineral_sem_categoria'][c.spec['id']] = dict(c.sem_mineral.most_common(15))
        if c.sem_municipio:
            val.setdefault('municipio_sem_codigo', {})[c.spec['id']] = dict(c.sem_municipio.most_common(15))
    for c in colunas:
        if c.spec['tipo'] == 'municipios_nome':
            val.setdefault('municipios_com_codigo', {})[c.spec['id']] = sum(1 for f in feicoes if f['valores'].get(c.spec['id']))
    for cid, conv in val['nao_convertidos'].items():
        val['alertas'].append(f'{cid}: {sum(conv.values())} valores não convertidos (ex.: {next(iter(conv))!r})')

    valores, dic = colunas_de_saida(feicoes, campos)
    pacote = {'id': spec['id'], 'formato': 'mapa-v1', 'geometria': tipo, 'n': len(feicoes), 'bounds': caixa, **geo,
              'campos': [c['id'] for c in campos], 'valores': valores, 'dic': dic}
    meta = {'retratos': sorted(retratos), 'campos': campos}
    return pacote, meta, val


# ---------------------------------------------------------------- camadas que já estão no Atlas
def camada_atlas(spec, atlas, processos_atlas):
    o = spec['origem']
    val = {'arquivo': o['arquivo']}
    if o['formato'] == 'processos-atlas':
        chaves = processos_atlas['processo'].split('\x01')
        val.update(feicoes=processos_atlas['n'], distintos=len(set(chaves)), extensao=processos_atlas['bounds'])
        return val, chaves
    dados = atlas[o['chave_json']]
    if o['formato'] == 'colunas-lat-lon':
        cols = dados['cols']
        linhas = [dict(zip(cols, r)) for r in dados['rows']]
    else:
        linhas = dados
    chaves = [x[spec['chave']] for x in linhas]
    val.update(feicoes=len(linhas), distintos=len(set(chaves)))
    if o['formato'] in ('colunas-lat-lon', 'lista-lat-lon'):
        sem = [x for x in linhas if x.get('lat') is None or x.get('lon') is None]
        fora = [x for x in linhas if x.get('lat') is not None and not (CAIXA_GO[1] <= x['lat'] <= CAIXA_GO[3] and CAIXA_GO[0] <= x['lon'] <= CAIXA_GO[2])]
        val.update(sem_coordenada=len(sem), fora_da_caixa_de_goias=len(fora))
    return val, chaves


# ---------------------------------------------------------------- tabelas
def tabela_municipios(atlas, minas, radar_linhas, ctx):
    anos = [str(a) for a in atlas['cfem']['anos']]
    cfem = {l['Município']: l for l in atlas['cfem']['linhas']}
    ultimo_mes = atlas['meta']['periods']['cfem'].split(' a ')[-1]           # '2026-08'
    projetos = collections.Counter(r[atlas['projects']['cols'].index('mun')] for r in atlas['projects']['rows'])
    ocorr = collections.Counter(r[atlas['occurrences']['cols'].index('mun')] for r in atlas['occurrences']['rows'])
    # minas ativas: cada processo conta uma vez em cada município que ele toca
    minas_mun = collections.defaultdict(set)
    for proc, codigos in minas:
        for c in codigos or []:
            minas_mun[c].add(proc)
    por_nome = {m['name']: m['code'] for m in atlas['municipalities']}
    radar_mun = collections.defaultdict(collections.Counter)
    sem_mun = 0
    for p in radar_linhas:
        code = por_nome.get(p['municipio']) if p['municipio'] else None
        if code:
            radar_mun[code][p['maturidade']] += 1
        else:
            sem_mun += 1
    linhas = []
    for m in sorted(atlas['municipalities'], key=lambda m: m['code']):
        l = cfem.get(m['name'])
        linhas.append({'code': m['code'], 'name': m['name'],
                       'cfem_recolhida': {a: (round(l[a], 2) if l and l.get(a) is not None else None) for a in anos},
                       'processos_que_tocam': m['processes'],
                       'minas_ativas_que_tocam': len(minas_mun.get(m['code'], ())),
                       'radar_projetos': dict(sorted(radar_mun.get(m['code'], {}).items(), key=lambda kv: radar.HIERARQUIA.index(kv[0]))),
                       'projetos_anm': projetos.get(m['code'], 0),
                       'ocorrencias': ocorr.get(m['code'], 0)})
    medidas = {
        'cfem_recolhida': {'rotulo': 'CFEM recolhida', 'rotulo_en': 'CFEM royalties collected', 'unidade': 'R$ correntes (sem correção pela inflação)',
                           'periodos': anos, 'periodo_incompleto': {anos[-1]: f'janeiro a {MESES[int(ultimo_mes[-2:]) - 1]} de {anos[-1]}'},
                           'periodo_padrao': anos[-2] if ultimo_mes[-2:] != '12' else anos[-1],
                           'fonte': 'ANM — CFEM_Arrecadacao_2022_2026.csv, pelo Atlas (data/atlas/atlas.json)',
                           'aditiva_entre_municipios': True,
                           'nota': ('Valor recolhido pelas empresas, atribuído ao município de origem da produção no arquivo da ANM. Não é a CFEM '
                                    'distribuída (repasse a estado e municípios). 0 = nenhum recolhimento no arquivo naquele ano. O último ano é '
                                    'parcial e não se compara com os anos completos.')},
        'processos_que_tocam': {'rotulo': 'Processos minerários que tocam o município', 'rotulo_en': 'Mining claims touching the municipality',
                                'unidade': 'processos distintos', 'retrato': 'SIGMINE de 10/09/2026', 'aditiva_entre_municipios': False,
                                'nota': 'Processo que cruza vários municípios conta em cada um; a soma dos municípios passa do total do estado.'},
        'minas_ativas_que_tocam': {'rotulo': 'Minas ativas (SGB) que tocam o município', 'rotulo_en': 'Active mines (SGB) touching the municipality',
                                   'unidade': 'processos distintos', 'retrato': 'P3M, 21/10/2026', 'aditiva_entre_municipios': False,
                                   'nota': 'Pelo código de município da própria camada; processo em mais de um município conta em cada um.'},
        'radar_projetos': {'rotulo': 'Projetos do Radar com município principal aqui, por maturidade', 'rotulo_en': 'Radar projects by main municipality and maturity',
                           'unidade': 'projetos (ID distinto)', 'aditiva_entre_municipios': True,
                           'nota': f'Cada projeto conta só no município principal. {sem_mun} projetos sem município principal ficam fora.'},
        'projetos_anm': {'rotulo': 'Projetos que ainda não produzem (aba 04)', 'rotulo_en': 'Pre-production projects (sheet 04)', 'unidade': 'projetos',
                         'aditiva_entre_municipios': True, 'retrato': 'SIGMINE de 10/09/2026'},
        'ocorrencias': {'rotulo': 'Ocorrências e depósitos do RECMIN', 'rotulo_en': 'RECMIN occurrences and deposits', 'unidade': 'pontos',
                        'aditiva_entre_municipios': True, 'retrato': 'RECMIN de 12/09/2026'},
    }
    return {'id': 'municipios', 'medidas': medidas, 'linhas': linhas}, sem_mun


def tabela_radar(projetos, chaves_processos, ctx, categorias, minerais):
    por_nome = {n: c for c, n in ctx.mun_por_codigo.items()}
    no_mapa = set(chaves_processos)
    linhas, ligacao = [], collections.Counter()
    for p in projetos:
        def v(c):
            return None if p[c] == 'NA' else p[c]
        procs = sorted({k for k in (chave_processo(x) for x in p['_processos']) if k}, key=lambda k: (int(k.split('/')[1]), int(k.split('/')[0])))
        mapeaveis = [k for k in procs if k in no_mapa]
        mun = v('Município')
        codigos = sorted({por_nome[m] for m in ([mun] if mun else []) + list(p['_municipios']) if m in por_nome})
        tipo = 'processos' if mapeaveis else 'municipio' if codigos else 'nenhuma'
        ligacao[tipo] += 1
        mineral = v('Mineral principal')
        k = sem_acento(mineral) if mineral else None
        linhas.append({'id': p['ID'], 'projeto': p['Projeto'], 'empresa': v('Empresa'), 'mineral': mineral,
                       'mineral_categoria': (categorias.get(k) or minerais.get(k)) if k else None,
                       'municipio': mun, 'municipios_codigos': codigos, 'fase': v('Fase'), 'maturidade': p['Maturidade'],
                       'status': v('Status atual'), 'capacidade': v('Capacidade anunciada'), 'unidade_capacidade': v('Unidade da capacidade'),
                       'capex': v('CAPEX'), 'moeda_capex': v('Moeda CAPEX'), 'ano_capex': v('Ano do CAPEX'),
                       'previsao': v('Previsão de entrada em operação'), 'confianca': p['Grau de confiança'],
                       'data_informacao': v('Data da informação mais recente'), 'link': v('Link principal'),
                       'origem': p['_origem'], 'processos': procs, 'processos_no_mapa': len(mapeaveis), 'ligacao': tipo})
    resumo = {'projetos': len(linhas), 'com_processo': sum(1 for l in linhas if l['processos']),
              'ligados_por_processo': ligacao['processos'], 'so_municipio': ligacao['municipio'], 'sem_ligacao': ligacao['nenhuma'],
              'processos_citados': len({k for l in linhas for k in l['processos']}),
              'processos_fora_do_mapa': len({k for l in linhas for k in l['processos']} - no_mapa),
              'sem_categoria_mineral': dict(collections.Counter(l['mineral'] for l in linhas if l['mineral'] and not l['mineral_categoria']).most_common(10))}
    return {'id': 'radar_projetos', 'fonte': 'Squad 1/Radar de Projetos/projetos_minerais_goias.xlsx (versão de 21/10/2026)',
            'ligacao': {'processos': 'desenhar pelos polígonos dos processos (camada processos)',
                        'municipio': 'só no nível do município (sem processo no mapa)', 'nenhuma': 'sem processo nem município'},
            'linhas': linhas}, resumo


def tabela_complemento(spec, chaves_processos, titular_proc, categorias_id, mun_por_nome):
    """Titular, municípios e mineral de cada processo do Atlas, na mesma ordem de /api/atlas/processes.
    Municípios e mineral vêm da aba 03_dim_operacoes da base consolidada (junção espacial em resolução total com a malha do IBGE 2025 e
    mineral_ids), a mesma base das contagens do Atlas; assim o filtro por município e o perfil do município dão o mesmo número."""
    import openpyxl
    wb = openpyxl.load_workbook(PLANILHA, read_only=True)
    linhas = wb[spec['aba']].iter_rows(values_only=True)
    cab = next(r for r in linhas if r and r[0] == 'operation_id')
    ix = {h: k for k, h in enumerate(cab)}
    base = {}
    for r in linhas:
        if r and r[0]:
            base[r[ix['processo_anm']]] = (r[ix['municipios_intersectados']], r[ix['mineral_ids']])
    titular, municipios, mineral, sem_codigo = [], [], [], collections.Counter()
    for k in chaves_processos:
        titular.append(titular_proc.get(k))
        nomes, ids = base.get(k, (None, None))
        cods = set()
        for n in str(nomes or '').split(';'):
            if n.strip():
                c = mun_por_nome.get(sem_acento(n))
                if c:
                    cods.add(c)
                else:
                    sem_codigo[n.strip()] += 1
        municipios.append(sorted(cods) or None)
        mineral.append(sorted({categorias_id[x.strip()] for x in str(ids or '').split(';') if x.strip() in categorias_id}) or None)
    dic = {'titular': sorted({x for x in titular if x}), 'municipios': sorted({c for x in municipios if x for c in x}),
           'mineral': sorted({m for x in mineral if x for m in x})}
    pos = {c: {v: j for j, v in enumerate(d)} for c, d in dic.items()}
    tabela = {'id': 'processos_complemento', 'processos': chaves_processos,
              'titular': [pos['titular'].get(x) for x in titular],
              'municipios': [[pos['municipios'][c] for c in x] if x else None for x in municipios],
              'mineral': [[pos['mineral'][m] for m in x] if x else None for x in mineral], 'dic': dic}
    resumo = {'processos': len(chaves_processos), 'na_aba_03': sum(1 for k in chaves_processos if k in base),
              'titular': dict(collections.Counter('sem titular' if n is None else 'pessoa física (sem nome)' if n == radar.TITULAR_INDIVIDUAL else 'pessoa jurídica' for n in titular)),
              'sem_municipio': sum(1 for x in municipios if not x), 'municipio_sem_codigo': dict(sem_codigo),
              'sem_mineral': sum(1 for x in mineral if not x), 'mais_de_um_mineral': sum(1 for x in mineral if x and len(x) > 1)}
    return tabela, resumo


# ---------------------------------------------------------------- catálogo e escrita
def gravar(caminho, objeto):
    texto = json.dumps(objeto, ensure_ascii=False, separators=(',', ':'))
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(texto, encoding='utf-8')
    return len(texto.encode('utf-8'))


def entrada_catalogo(spec, cfg, meta, n, n_fonte, nbytes, val=None):
    o = spec['origem']
    publicos = ('id', 'nome', 'nome_en', 'grupo', 'geometria', 'chave', 'carga', 'visivel_padrao', 'filtros', 'legenda', 'papeis', 'ponto_ate_zoom',
                'entidade', 'entidade_en', 'registros_fonte_rotulo', 'registros_fonte_rotulo_en', 'omitidos', 'notas', 'tabela')
    e = {k: spec[k] for k in publicos if k in spec}
    if o['tipo'] == 'atlas':
        e['dados'] = {'endpoint': o['endpoint'], 'arquivo': o['arquivo'], 'formato': o['formato'], **({'chave_json': o['chave_json']} if 'chave_json' in o else {})}
        e['data_retrato'] = spec.get('data_retrato')
        e['campos'] = spec['campos']
    else:
        e['dados'] = {'endpoint': f"/api/mapa/camadas/{spec['id']}", 'arquivo': f"data/mapa/camadas/{spec['id']}.json", 'formato': 'mapa-v1'}
        retratos = meta['retratos']
        e['data_retrato'] = retratos[0] if len(retratos) == 1 else retratos
        e['campos'] = meta['campos']
        e['fonte_arquivos'] = [a['arquivo'] for a in o['arquivos']]
        e['recorte'] = ('Cortada pelo limite estadual do IBGE (GO_UF_2024): pontos dentro ou na divisa; linhas e polígonos que cruzam a divisa '
                        'cortados no limite, com os atributos da feição inteira (área, extensão e contagens não são rateados).')
        if spec.get('tolerancia'):
            e['simplificacao'] = {'tolerancia_graus': spec['tolerancia'], 'nota': spec.get('nota_tolerancia', 'Douglas-Peucker preservando topologia; o detalhe e os identificadores ficam no zip de origem.')}
    e['fonte'] = spec['fonte']
    e['temporalidade'] = 'retrato'
    e['periodo_referencia'] = spec.get('periodo_referencia')
    if val and 'posicao_aproximada' in val:
        e['n_posicao_aproximada'] = val['posicao_aproximada']
    e['crs'] = UNIDADE_CRS
    e['n_feicoes'] = n
    if n_fonte is not None and n_fonte != n:
        e['n_registros_fonte'] = n_fonte
    e['bytes'] = nbytes
    return e


def montar(cfg):
    atlas = json.loads(ATLAS.read_text(encoding='utf-8'))
    processos_atlas = json.loads(PROCESSOS_ATLAS.read_text(encoding='utf-8'))
    go = limite_goias(cfg)
    shapely.prepare(go)
    faixa_divisa = shapely.buffer(go.boundary, FOLGA_DIVISA)
    shapely.prepare(faixa_divisa)
    indice = indice_recorte(cfg)
    minerais, ambiguos = crosswalk_minerais()
    categorias, categorias_id = categorias_minerais()
    projetos, _noticias, _resumo, ctx = radar.montar(RAIZ)
    titular_proc = titulares_pj(ctx)
    mun_por_nome = {sem_acento(n): c for c, n in ctx.mun_por_codigo.items()}
    # grafias da fonte que não são o nome do IBGE (erro de digitação ou nome sem 'de Goiás'), listadas no catálogo
    mun_por_nome.update({sem_acento(a): mun_por_nome[sem_acento(n)] for a, n in cfg.get('apelidos_municipios', {}).items()})

    grupos = {g['id'] for g in cfg['grupos']}
    ids = [c['id'] for c in cfg['camadas']]
    assert len(ids) == len(set(ids)), 'id de camada repetido no catálogo'
    camadas_saida, entradas, validacao = {}, [], {'camadas': {}, 'erros': [], 'alertas': []}
    chaves_processos = None
    minas_por_mun = []
    for spec in cfg['camadas']:
        assert spec['grupo'] in grupos, f"{spec['id']}: grupo {spec['grupo']} não existe"
        if spec['origem']['tipo'] == 'atlas':
            val, chaves = camada_atlas(spec, atlas, processos_atlas)
            if spec['origem']['formato'] == 'processos-atlas':
                chaves_processos = chaves
            arquivo = RAIZ / spec['origem']['arquivo']
            entradas.append(entrada_catalogo(spec, cfg, None, val['feicoes'], None, arquivo.stat().st_size))
            validacao['camadas'][spec['id']] = {'origem': 'atlas', **val}
            if val['distintos'] != val['feicoes']:
                validacao['alertas'].append(f"{spec['id']}: {val['feicoes'] - val['distintos']} chaves repetidas no Atlas")
            continue
        pacote, meta, val = camada_p3m(spec, cfg, go, faixa_divisa, indice, minerais, ambiguos, titular_proc, mun_por_nome)
        if spec['id'] == 'minas_ativas':
            cods = pacote['dic']['municipios']
            minas_por_mun = [(p, [cods[i] for i in (c or [])]) for p, c in zip(pacote['valores']['processo'], pacote['valores']['municipios'])]
        nbytes = len(json.dumps(pacote, ensure_ascii=False, separators=(',', ':')).encode('utf-8'))
        camadas_saida[spec['id']] = pacote
        entradas.append(entrada_catalogo(spec, cfg, meta, pacote['n'], val['registros_fonte'], nbytes, val))
        val['bytes'] = nbytes
        validacao['camadas'][spec['id']] = {'origem': 'p3m', **val}
        validacao['erros'] += [f"{spec['id']}: {e}" for e in val.pop('erros')]
        validacao['alertas'] += [f"{spec['id']}: {a}" for a in val.pop('alertas')]
    assert chaves_processos is not None, 'o catálogo precisa da camada de processos do Atlas'

    tab_radar, resumo_radar = tabela_radar(projetos, chaves_processos, ctx, categorias, minerais)
    tab_mun, _ = tabela_municipios(atlas, minas_por_mun, tab_radar['linhas'], ctx)
    spec_comp = next(t for t in cfg['tabelas'] if t['id'] == 'processos_complemento')
    tab_comp, resumo_comp = tabela_complemento(spec_comp, chaves_processos, titular_proc, categorias_id, mun_por_nome)
    tabelas = {'municipios': tab_mun, 'radar_projetos': tab_radar, 'processos_complemento': tab_comp}

    tab_cat = []
    for t in cfg['tabelas']:
        nbytes = len(json.dumps(tabelas[t['id']], ensure_ascii=False, separators=(',', ':')).encode('utf-8'))
        e = {k: v for k, v in t.items() if k != 'aba'}
        e.update(endpoint=f"/api/mapa/tabelas/{t['id']}", arquivo=f"data/mapa/tabelas/{t['id']}.json", bytes=nbytes)
        e['linhas'] = len(tabelas[t['id']].get('linhas') or tabelas[t['id']].get('processos'))
        if t['id'] == 'municipios':
            e['medidas'] = tab_mun['medidas']
        if t['id'] == 'radar_projetos':
            e['resumo'] = resumo_radar
        if t['id'] == 'processos_complemento':
            e['resumo'] = {k: resumo_comp[k] for k in ('na_aba_03', 'sem_municipio', 'sem_mineral', 'mais_de_um_mineral')}
        tab_cat.append(e)

    # contagens que o mapa precisa mostrar
    sem_geom = {cid: v['sem_geometria'] for cid, v in validacao['camadas'].items() if v.get('sem_geometria')}
    validacao['radar_projetos'] = resumo_radar
    validacao['processos_complemento'] = resumo_comp
    validacao['municipios'] = {'linhas': len(tab_mun['linhas']), 'codigos_distintos': len({l['code'] for l in tab_mun['linhas']}),
                               'cfem_sem_linha_no_atlas': sum(1 for l in tab_mun['linhas'] if all(v is None for v in l['cfem_recolhida'].values()))}
    validacao['sem_geometria'] = sem_geom
    if validacao['municipios']['linhas'] != 246 or validacao['municipios']['codigos_distintos'] != 246:
        validacao['erros'].append('tabela municipios não tem os 246 municípios de Goiás')
    texto_publicado = json.dumps([camadas_saida, tabelas], ensure_ascii=False)
    if CPF.search(texto_publicado):
        validacao['erros'].append('CPF nos dados publicados')

    # minerais do filtro: categorias da ANM que aparecem em alguma base do mapa
    presentes = {x for p in camadas_saida.values() for c, d in p['dic'].items() if c == 'mineral' for x in d}
    presentes |= set(tab_comp['dic']['mineral']) | {l['mineral_categoria'] for l in tab_radar['linhas'] if l['mineral_categoria']}
    presentes |= {categorias[sem_acento(r[atlas['projects']['cols'].index('mineral')])] for r in atlas['projects']['rows']
                  if sem_acento(r[atlas['projects']['cols'].index('mineral')]) in categorias}
    presentes |= {categorias[sem_acento(x)] for r in atlas['occurrences']['rows'] for x in str(r[atlas['occurrences']['cols'].index('substancias')] or '').split(';')
                  if sem_acento(x) in categorias}
    catalogo = {'versao': cfg['versao'], 'titulo': 'Mapa Mineral de Goiás', 'descricao': cfg['descricao'],
                'crs': UNIDADE_CRS, 'p3m': {k: cfg['p3m'][k] for k in ('portal', 'servico', 'nota_retrato')},
                'temporalidade': ('Toda camada é um retrato na data_retrato (situação naquele dia); escolher um ano anterior não a transforma '
                                  'em histórico. Séries anuais só existem nas medidas da tabela municipios, cada uma com seus períodos.'),
                'formato_camadas': {
                    'mapa-v1': ('xy: pares Uint16 (x = longitude, y = latitude invertida) em base64; partStart: Uint32 (início de cada parte, '
                                'mais o total); partFeat: Uint32 (feição de cada parte). Parte = ponto, linha ou anel; anéis da mesma feição '
                                'desenham-se juntos com preenchimento evenodd. lat = bounds.lat1 − y/65535·(lat1 − lat0); '
                                'lon = bounds.lon0 + x/65535·(lon1 − lon0). valores[campo][i] é o valor da feição i; para campos em dic, '
                                'o valor (ou cada item da lista) é o índice em dic[campo].'),
                    'processos-atlas': 'formato de /api/atlas/processes (public/processes.js)',
                    'colunas-lat-lon': "atlas.json[chave_json] = {cols, rows}, com colunas lat e lon",
                    'lista-lat-lon': 'atlas.json[chave_json] = lista de objetos com lat e lon',
                    'municipios-atlas': 'atlas.json.municipalities: code, name e rings ([lat, lon])'},
                'minerais': sorted(presentes, key=sem_acento),
                'grupos': cfg['grupos'], 'camadas': entradas, 'tabelas': tab_cat}
    return catalogo, camadas_saida, tabelas, validacao


def escrever(catalogo, camadas_saida, tabelas, validacao):
    destino_camadas = SAIDA / 'camadas'
    destino_tabelas = SAIDA / 'tabelas'
    for pasta, ids in ((destino_camadas, camadas_saida), (destino_tabelas, tabelas)):
        if pasta.exists():
            for velho in pasta.glob('*.json'):
                if velho.stem not in ids:
                    velho.unlink()
    for cid, pacote in camadas_saida.items():
        gravar(destino_camadas / f'{cid}.json', pacote)
    for tid, tabela in tabelas.items():
        gravar(destino_tabelas / f'{tid}.json', tabela)
    gravar(SAIDA / 'catalogo.json', catalogo)
    (SAIDA / 'validacao.json').write_text(json.dumps(validacao, ensure_ascii=False, indent=1), encoding='utf-8')


def resumo_texto(catalogo, validacao):
    linhas = []
    for e in catalogo['camadas']:
        v = validacao['camadas'][e['id']]
        extra = f" de {v['registros_fonte']} registros" if v.get('registros_fonte') not in (None, e['n_feicoes']) else ''
        linhas.append(f"{e['id']:24} {e['geometria']:9} {e['n_feicoes']:>6}{extra:>18}  {e['bytes'] / 1024:8.0f} KB  {e['carga']}")
    for t in catalogo['tabelas']:
        linhas.append(f"tabela {t['id']:17} {t['linhas']:>16}{'':>18}  {t['bytes'] / 1024:8.0f} KB")
    linhas.append(json.dumps({'radar': validacao['radar_projetos'], 'processos': validacao['processos_complemento']}, ensure_ascii=False))
    linhas += [f'ERRO {e}' for e in validacao['erros']] + [f'alerta {a}' for a in validacao['alertas']]
    return '\n'.join(linhas)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--checar', action='store_true', help='só valida e mostra o resumo, sem gravar')
    args = ap.parse_args()
    cfg = json.loads(CATALOGO.read_text(encoding='utf-8'))
    catalogo, camadas_saida, tabelas, validacao = montar(cfg)
    print(resumo_texto(catalogo, validacao))
    if validacao['erros']:
        sys.exit('erros na validação: nada foi gravado')
    if not args.checar:
        escrever(catalogo, camadas_saida, tabelas, validacao)
        print(f'gravado em {SAIDA.relative_to(RAIZ)}')


if __name__ == '__main__':
    main()
