# -*- coding: utf-8 -*-
"""Pacote do Atlas Empresarial (data/empresas/atlas_empresas.json), servido em /api/empresas/atlas, atrás da sessão.

    python scripts/build_atlas_empresas.py              # usa a raiz do repositório onde está este script
    python scripts/build_atlas_empresas.py --verificar  # só diz se o pacote está desatualizado

Nada aqui é medição nova: o gerador só junta, por CHAVE, bases que o repositório já publica.

- Identidade da empresa = CNPJ raiz do titular PJ (data/panorama/panorama.json, dims.emp, id `COM_CNPJ_<raiz>`). Pessoa física
  não é nomeada: entra só em contagens, como no Mapa mineral.
- Processos ANM (panorama.proc): fase, situação do panorama, mineral, área, CFEM 2022–2026 e titular. Municípios IBGE vêm de
  data/mapa/tabelas/processos_complemento.json (municípios que o polígono intersecta). O centroide de cada processo é calculado
  da mesma geometria que /api/atlas/processes serve — é um ponto INDICATIVO do direito minerário, não a localização de uma mina.
- CFEM por titular, ano, município e mineral (panorama.cfem) e, quando o CSV corrigido da ANM está no repositório, CFEM por
  processo e ano, casada só pela chave processo+ano do processo e CNPJ raiz.
- Carga CCEE por CNPJ raiz e ano (panorama.ccee), com o mesmo critério de anualização e qualidade de data/empresas/README.md.
- 'Minas ativas (SGB)' (data/mapa/camadas/minas_ativas.json) marca os processos que o SGB classifica assim; o critério é do SGB.
- Projetos: Radar de Projetos ligado pelos processos ANM que cada projeto cita; levantamentos de projetos e Mercado ligados pela
  lista revisada data/empresas/curadoria_atlas.json (projetos_cnpj).
- Notícias: acervo do coletor (public/data/noticias/meses), casado por alias revisado na curadoria, com contexto de Goiás exigido
  para nomes de grupo e exclusão explícita de outras UFs e de menções indiretas. Cada vínculo diz o alias, o método e a confiança.
- Minerais estratégicos (federal) e críticos (Goiás) vêm da curadoria, separados, com norma e link.

Dois arquivos de saída (ajustes finais, 26/11/2026):
- atlas_empresas.json: o pacote que a aba recebe. Só textos públicos — fontes institucionais (ANM, CCEE, SGB, IBGE, empresas, veículos),
  método e cobertura —, sem nome de equipe, caminho de arquivo nem nome de script;
- atlas_empresas_proveniencia.json (mesma pasta, NÃO servido pela API): o rastreamento técnico de reprodutibilidade — que script gerou o
  pacote e o SHA-256 de cada entrada. O --verificar confere os dois.
"""
import argparse
import base64
import csv
import glob
import hashlib
import json
import re
import struct
import sys
import unicodedata
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('--repo', default=str(Path(__file__).resolve().parents[1]))
parser.add_argument('--saida')
parser.add_argument('--verificar', action='store_true')
args = parser.parse_args()
REPO = Path(args.repo)
SAIDA = Path(args.saida) if args.saida else REPO / 'data' / 'empresas' / 'atlas_empresas.json'
# rastreamento técnico (script, entradas, hashes): ao lado do pacote, fora do que a API serve
PROVENIENCIA = SAIDA.with_name(SAIDA.stem + '_proveniencia.json')

ENTRADAS = {
    'panorama': 'data/panorama/panorama.json',
    'complemento': 'data/mapa/tabelas/processos_complemento.json',
    'geometria': 'data/atlas/processes.json',
    'minas_sgb': 'data/mapa/camadas/minas_ativas.json',
    'empresas': 'data/empresas/empresas.json',
    'producao': 'data/producao/producao.json',
    'projetos': 'data/projetos/projetos.json',
    'radar_projetos': 'data/mapa/tabelas/radar_projetos.json',
    'mercado_projetos': 'public/data/mercado/projetos_go_v1.json',
    'curadoria': 'data/empresas/curadoria_atlas.json',
}
CFEM_CSV = 'Squad 1/Dados corrigidos/ANM - CFEM/CFEM_Arrecadacao_2022_2026_GO.csv'
NOTICIAS = 'public/data/noticias/meses/*.json'


def ler(rel):
    return json.loads((REPO / rel).read_text(encoding='utf-8'))


def sha(rel):
    # Quebra de linha normalizada: a mesma entrada dá o mesmo hash num checkout Windows (CRLF) e no Linux (LF),
    # senão o --verificar e o teste de idempotência acusariam "desatualizado" só por causa do sistema.
    return hashlib.sha256((REPO / rel).read_bytes().replace(b'\r\n', b'\n')).hexdigest()[:16]


def sem_acento(s):
    s = unicodedata.normalize('NFKD', str(s or ''))
    return ''.join(c for c in s if not unicodedata.combining(c)).lower()


def r2(v):
    return round(float(v), 2)


# ---------------------------------------------------------------- bases
PN = ler(ENTRADAS['panorama'])
DIMS = PN['dims']
EMP = DIMS['emp']                      # [id, nome, cnpj_raiz, 'pj'|'oculto']
MUN = DIMS['mun']                      # [ibge, nome, pop, pib]
MIN = DIMS['min']                      # [MIN_xxx, nome, classe]
FASE = DIMS['fase']
STATUS = DIMS['status']
USO = DIMS['uso']
MUN_IDX = {m[0]: i for i, m in enumerate(MUN)}
MIN_IDX = {m[1]: i for i, m in enumerate(MIN)}
PJ = {i for i, e in enumerate(EMP) if e[3] == 'pj' and e[2]}
CNPJ_EMP = {EMP[i][2]: i for i in PJ}

# Grupo jurídico de cada fase, com o mesmo critério de 'Squad 3/backend/radar_api.py' (CONFIRMED / OPENING).
LAVRA = {'CONCESSÃO DE LAVRA', 'LAVRA GARIMPEIRA', 'LICENCIAMENTO', 'REGISTRO DE EXTRAÇÃO'}
DISPONIBILIDADE = {'DISPONIBILIDADE', 'APTO PARA DISPONIBILIDADE'}
PESQUISA = {'AUTORIZAÇÃO DE PESQUISA', 'REQUERIMENTO DE PESQUISA', 'RECONHECIMENTO GEOLÓGICO'}
REQ_LAVRA = {'REQUERIMENTO DE LAVRA', 'DIREITO DE REQUERER A LAVRA', 'REQUERIMENTO DE LICENCIAMENTO',
             'REQUERIMENTO DE LAVRA GARIMPEIRA', 'REQUERIMENTO DE REGISTRO DE EXTRAÇÃO'}


def grupo_da_fase(nome):
    if nome in LAVRA:
        return 'lavra_autorizada'
    if nome in REQ_LAVRA:
        return 'requerimento_lavra'
    if nome in PESQUISA:
        return 'pesquisa'
    if nome in DISPONIBILIDADE:
        return 'disponibilidade'
    return 'outro'


# ---------------------------------------------------------------- geometria → centroide indicativo
def centroides():
    p = ler(ENTRADAS['geometria'])
    b = p['bounds']

    def arr(chave, fmt, tam):
        raw = base64.b64decode(p[chave])
        return struct.unpack('<%d%s' % (len(raw) // tam, fmt), raw)
    xy, rs, rp = arr('xy', 'H', 2), arr('ringStart', 'I', 4), arr('ringPoly', 'H', 2)
    ids = p['processo'].split('\x01')
    acc = defaultdict(lambda: [0.0, 0.0, 0.0, 0.0, 0.0, 0])   # soma A·x, A·y, A, soma x, soma y, n
    for r in range(len(rp)):
        pts = [(b['lon0'] + xy[2 * i] / 65535 * (b['lon1'] - b['lon0']),
                b['lat1'] - xy[2 * i + 1] / 65535 * (b['lat1'] - b['lat0'])) for i in range(rs[r], rs[r + 1])]
        if not pts:
            continue
        a = cx = cy = 0.0
        for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]):
            f = x0 * y1 - x1 * y0
            a += f
            cx += (x0 + x1) * f
            cy += (y0 + y1) * f
        c = acc[rp[r]]
        if abs(a) > 1e-12:
            # anel interno (buraco) tem orientação contrária e entra com sinal oposto; usa-se o valor absoluto do total
            c[0] += cx / 3
            c[1] += cy / 3
            c[2] += a
        c[3] += sum(x for x, _ in pts)
        c[4] += sum(y for _, y in pts)
        c[5] += len(pts)
    out = {}
    for poly, c in acc.items():
        if abs(c[2]) > 1e-12:
            lon, lat = c[0] / c[2], c[1] / c[2]
        else:
            lon, lat = c[3] / c[5], c[4] / c[5]
        out[ids[poly]] = (round(lat, 4), round(lon, 4))
    return out, p['n']


# ---------------------------------------------------------------- processos
def processos():
    cols = {c: i for i, c in enumerate(PN['proc']['cols'])}
    comp = ler(ENTRADAS['complemento'])
    comp_mun = {pid: [comp['dic']['municipios'][k] for k in ms] for pid, ms in zip(comp['processos'], comp['municipios'])}
    cent, n_geo = centroides()
    sgb = ler(ENTRADAS['minas_sgb'])
    em_sgb = set(sgb['valores']['processo']) | set(x for x in sgb['valores'].get('grupamento', []) if x)
    linhas = []
    for row in PN['proc']['rows']:
        pid = row[cols['processo']]
        emp = row[cols['emp']]
        muns = [MUN_IDX[c] for c in comp_mun.get(pid, []) if c in MUN_IDX] or ([row[cols['mun']]] if row[cols['mun']] >= 0 else [])
        lat, lon = cent.get(pid, (None, None))
        linhas.append({
            'p': pid,
            'e': emp if emp in PJ else (-2 if emp >= 0 else -1),   # -2 = pessoa física (não nomeada), -1 = sem titular
            'f': row[cols['fase']], 's': row[cols['status']], 'm': row[cols['min']], 'u': row[cols['uso']],
            'mu': muns, 'a': row[cols['area_ha']], 'ap': row[cols['ano_processo']],
            'c': r2(row[cols['cfem_2022_2026']] or 0), 'la': lat, 'lo': lon, 'sgb': 1 if pid in em_sgb else 0,
        })
    return linhas, n_geo, len(em_sgb)


def cfem_por_processo(processos_ids):
    """CFEM por processo e ano, do CSV corrigido da ANM. Só PJ (pessoa física não é exposta) e só processos do SIGMINE."""
    caminho = REPO / CFEM_CSV
    if not caminho.is_file():
        return None, None
    texto = caminho.read_bytes().decode('utf-8-sig', errors='replace')
    leitor = csv.reader(texto.splitlines(), delimiter=';')
    cab = [sem_acento(c) for c in next(leitor)]
    ix = {c: i for i, c in enumerate(cab)}
    por = defaultdict(lambda: defaultdict(float))
    casou = fora = 0
    for linha in leitor:
        if len(linha) < len(cab) or linha[ix['tipo_pf_pj']].strip().upper() != 'PJ':
            continue
        pid = f"{linha[ix['processo']].strip()}/{linha[ix['anodoprocesso']].strip()}"
        valor = float((linha[ix['valorrecolhido']] or '0').replace('.', '').replace(',', '.') or 0)
        if pid in processos_ids:
            por[pid][int(linha[ix['ano']])] += valor
            casou += 1
        else:
            fora += 1
    return {p: {str(a): r2(v) for a, v in sorted(d.items())} for p, d in por.items()}, {'linhas_casadas': casou, 'linhas_sem_processo_no_sigmine': fora}


# ---------------------------------------------------------------- CFEM por titular e carga CCEE
def cfem_titular():
    cols = {c: i for i, c in enumerate(PN['cfem']['cols'])}
    agg = defaultdict(float)
    meses_2026 = set()
    for r in PN['cfem']['rows']:
        if r[cols['ano']] == 2026:
            meses_2026.add(r[cols['mes']])
        e = r[cols['emp']]
        if e in PJ:
            agg[(e, r[cols['ano']], r[cols['mun']], r[cols['min']])] += r[cols['valor']]
    linhas = [[e, a, mu, mi, r2(v)] for (e, a, mu, mi), v in sorted(agg.items())]
    return linhas, sorted(meses_2026)


def qualidade(meses):
    return 'observado_completo' if meses >= 12 else 'estimado_alto' if meses >= 9 else 'estimado_medio' if meses >= 6 else 'estimado_baixo'


def ccee_por_cnpj():
    cols = {c: i for i, c in enumerate(PN['ccee']['cols'])}
    ce = DIMS['ce']
    soma = defaultdict(float)
    meses = defaultdict(set)
    for r in PN['ccee']['rows']:
        cnpj = ce[r[cols['empresa']]][0]
        if cnpj not in CNPJ_EMP:
            continue
        ano, mes = divmod(r[cols['mes']], 100)
        soma[(cnpj, ano)] += r[cols['total_mwh']]
        meses[(cnpj, ano)].add(mes)
    out = defaultdict(dict)
    for (cnpj, ano), v in soma.items():
        n = len(meses[(cnpj, ano)])
        out[cnpj][str(ano)] = {'obs': round(v, 3), 'meses': n, 'anual': round(v / n * 12, 3), 'q': qualidade(n)}
    return out


# ---------------------------------------------------------------- notícias
def veiculo(titulo, fonte):
    m = re.search(r'\s[-–]\s([^-–]{2,60})$', titulo)
    return m.group(1).strip() if m else (fonte or '').replace('Busca · ', '')


def termo(texto_norm, t):
    t = sem_acento(t)
    return re.search(r'(?<![a-z0-9])' + re.escape(t) + r'(?![a-z0-9])', texto_norm) is not None


def noticias(cur):
    regras = cur['noticias']
    geral = [sem_acento(x) for x in regras['contexto_go_geral']]
    indiretos = [sem_acento(x) for x in regras['padroes_indiretos']]
    itens, vistos = [], set()
    for f in sorted(glob.glob(str(REPO / NOTICIAS))):
        d = json.loads(Path(f).read_text(encoding='utf-8'))
        for it in (d['itens'] if isinstance(d, dict) else d):
            base = re.sub(r'\s[-–]\s[^-–]{2,60}$', '', it['title']).strip()
            chave = (sem_acento(base), (it.get('published_at') or '')[:10])
            if chave in vistos:
                continue
            vistos.add(chave)
            itens.append(it)
    vinculos, descartes = [], Counter()
    exemplos_descarte = []
    for it in itens:
        # o nome do veículo no fim do título ('… - Zap Catalão') não é contexto da matéria
        tn = sem_acento(re.sub(r'\s[-–]\s[^-–]{2,60}$', '', it['title']))
        tem_go = any((g in tn) if not g[0].isalnum() else termo(tn, g) for g in geral)
        for cnpj, r in regras['empresas'].items():
            if cnpj not in CNPJ_EMP:
                continue
            ent = next((a for a in r['entidade'] if termo(tn, a)), None)
            grp = next((a for a in r['grupo'] if termo(tn, a)), None)
            if not ent and not grp:
                continue
            ctx_local = any(termo(tn, c) for c in r['contexto'])
            ctx = tem_go or ctx_local
            fora = next((o for o in r['outra_uf'] if termo(tn, o)), None)
            alias, metodo = (ent, 'alias_entidade') if ent else (grp, 'alias_grupo')
            motivo = None
            if fora and not tem_go and not ctx_local:
                motivo = 'outra_uf'
            elif ent and r.get('exige_contexto_entidade') and not grp and not any(termo(tn, c) for c in r['exige_contexto_entidade']) and not tem_go:
                motivo = 'nome_ambiguo_sem_contexto'
            elif not ent and not ctx:
                motivo = 'grupo_sem_contexto_go'
            elif r.get('multi_uf') and not ctx:
                motivo = 'empresa_multi_uf_sem_contexto_go'
            indireta = any(x in tn for x in indiretos)
            if motivo:
                descartes[motivo] += 1
                if len(exemplos_descarte) < 60:
                    exemplos_descarte.append({'e': CNPJ_EMP[cnpj], 't': it['title'][:200], 'motivo': motivo, 'alias': alias,
                                              'd': (it.get('published_at') or '')[:10]})
                continue
            conf = 'alta' if (ent and (tem_go or ctx)) else 'media'
            if fora:
                conf = 'media'   # cita Goiás (ou a operação goiana) e outra UF: a matéria é da empresa, mas não só da operação em Goiás
            vinculos.append({
                'e': CNPJ_EMP[cnpj], 'd': (it.get('published_at') or '')[:10], 't': it['title'][:300], 'u': it['link'],
                'v': veiculo(it['title'], it.get('fonte')), 'alias': alias, 'metodo': metodo, 'conf': conf,
                'tipo': 'indireta' if indireta else 'empresa', 'go': 1 if tem_go else 0,
                'subs': it.get('substancias') or [],
            })
    vinculos.sort(key=lambda x: (x['d'], x['t']), reverse=True)
    return vinculos, {'acervo_deduplicado': len(itens), 'vinculadas': len(vinculos), 'descartadas': dict(descartes)}, exemplos_descarte


# ---------------------------------------------------------------- projetos
# Fonte pública de um link: só o que o próprio endereço documenta. Os arquivos de dados abertos da ANM ganham o nome do conjunto; os demais,
# o domínio do site. O tipo do registro (Radar, Carteira, Levantamento) vai em 'fonte'; quem publicou, em 'fonte_nome'.
DADOS_ABERTOS_ANM = (('dadosabertos.anm.gov.br/sigmine', 'ANM · SIGMINE (dados abertos)'),
                     ('dadosabertos.anm.gov.br/scm', 'ANM · Cadastro Mineiro (dados abertos)'),
                     ('dadosabertos.anm.gov.br/cfem', 'ANM · CFEM (dados abertos)'))


def fonte_do_link(url):
    if not url:
        return None
    u = url.lower()
    for trecho, nome in DADOS_ABERTOS_ANM:
        if trecho in u:
            return nome
    host = re.sub(r'^https?://', '', u).split('/', 1)[0]
    return 'ANM' if host.endswith('anm.gov.br') else re.sub(r'^www\.', '', host) or None


def projetos(cur, proc_por_id):
    mapa = {k: v for k, v in cur['projetos_cnpj'].items() if not k.startswith('_')}
    out = []

    def ligar_nome(nome):
        v = mapa.get(nome)
        if v and v['cnpj_raiz'] in CNPJ_EMP:
            return [CNPJ_EMP[v['cnpj_raiz']]], 'curadoria_cnpj', v['confianca']
        return [], 'sem_vinculo_verificado', None

    na = lambda v: None if v in (None, 'NA', '') else v
    pj = ler(ENTRADAS['projetos'])
    for p in pj['projetos']:
        es, metodo, conf = ligar_nome(p['empresa'])
        out.append({'id': p['id'], 'fonte': 'projetos', 'nome': p['projeto'], 'empresa_txt': na(p['empresa']), 'controladora': na(p['controladora']),
                    'e': es, 'metodo': metodo, 'conf': conf, 'mineral': na(p['mineral']), 'mun': na(p['municipio']),
                    'maturidade': na(p['maturidade']), 'fase': na(p['fase']), 'status': na(p['status']),
                    'capacidade': na(p['capacidade']), 'cap_unidade': na(p['cap_unidade']), 'producao': na(p['producao']), 'prod_unidade': na(p['prod_unidade']),
                    'capex': na(p['capex']), 'moeda': na(p['moeda']), 'ano_capex': na(p['ano_capex']), 'entrada': na(p.get('ano_entrada')),
                    'confianca_fonte': na(p['confianca']), 'link': na(p['link']), 'fonte_nome': na(p['fonte']), 'data': na(p.get('recente')),
                    'evidencias': [{'d': ev['data'], 't': ev['titulo'], 'v': ev['veiculo'], 'u': na(ev['link']), 'tipo': ev['tipo']}
                                   for ev in pj['evidencias'] if ev['projeto_id'] == p['id']]})
    mg = ler(ENTRADAS['mercado_projetos'])
    for p in mg['projetos']:
        es, metodo, conf = ligar_nome(p['empresa'])
        cap = p.get('capacidade') or {}
        out.append({'id': 'MK-' + p['id'], 'fonte': 'mercado', 'nome': p['projeto'], 'empresa_txt': p['empresa'], 'controladora': p.get('controladora'),
                    'e': es, 'metodo': metodo, 'conf': conf, 'mineral': p.get('mineral'), 'mun': p.get('municipio'),
                    'maturidade': p.get('maturidade'), 'fase': p.get('fase'), 'status': p.get('status'),
                    'capacidade': cap.get('valor') if isinstance(cap, dict) else None, 'cap_unidade': cap.get('unidade') if isinstance(cap, dict) else None,
                    'capex': (p.get('capex') or {}).get('valor') if isinstance(p.get('capex'), dict) else p.get('capex'),
                    'moeda': (p.get('capex') or {}).get('moeda') if isinstance(p.get('capex'), dict) else None,
                    'ano_capex': (p.get('capex') or {}).get('ano') if isinstance(p.get('capex'), dict) else None,
                    # a carteira de Mercado documenta a fonte de cada projeto (tipo de documento e link): vai como está
                    'confianca_fonte': p.get('confianca'), 'link': na(p.get('link')), 'fonte_nome': na(p.get('fonte')) or fonte_do_link(p.get('link')),
                    'data': p.get('data_informacao'),
                    'evidencias': [{'d': n['data'], 't': n['titulo'], 'v': n['veiculo'], 'u': n.get('link'), 'tipo': n.get('tipo_fonte')}
                                   for n in mg['noticias'] if n['projeto_id'] == p['id']]})
    rp = ler(ENTRADAS['radar_projetos'])
    for p in rp['linhas']:
        es = sorted({proc_por_id[x]['e'] for x in (p.get('processos') or []) if x in proc_por_id and proc_por_id[x]['e'] >= 0})
        if not es:
            continue   # sem processo de titular PJ: o projeto não se liga a nenhuma empresa do índice
        out.append({'id': 'RD-' + p['id'], 'fonte': 'radar', 'nome': p['projeto'], 'empresa_txt': p.get('empresa'), 'controladora': None,
                    'e': es, 'metodo': 'processo_anm', 'conf': 'alta' if len(es) == 1 else 'media', 'processos': p.get('processos'),
                    'mineral': p.get('mineral'), 'mun': p.get('municipio'), 'maturidade': p.get('maturidade'), 'fase': p.get('fase'),
                    'status': p.get('status'), 'capacidade': p.get('capacidade'), 'cap_unidade': p.get('unidade_capacidade'),
                    'capex': p.get('capex'), 'moeda': p.get('moeda_capex'), 'ano_capex': p.get('ano_capex'),
                    'confianca_fonte': p.get('confianca'), 'link': p.get('link'), 'fonte_nome': fonte_do_link(p.get('link')),
                    'data': p.get('data_informacao'), 'evidencias': []})
    return out


def localizar_projetos(projs, procs):
    """Grava em cada projeto onde ele pode ser desenhado, só com a precisão que a fonte sustenta: 'p' = processos ANM citados
    (índices das linhas de processos com centroide, maior área primeiro); 'm' = municípios informados (índices de dims.mun); sem nada, None."""
    idx = {p['p']: k for k, p in enumerate(procs)}
    mun_nome = {sem_acento(m[1]): i for i, m in enumerate(MUN)}
    for pr in projs:
        ks = [idx[x] for x in (pr.get('processos') or []) if x in idx and procs[idx[x]]['la'] is not None]
        ks = sorted(set(ks), key=lambda k: (-(procs[k]['a'] or 0), k))
        if ks:
            pr['loc'] = {'t': 'p', 'k': ks}
            continue
        ms = []
        for parte in re.split(r'\s*(?:[,/;]|\be\b)\s*', pr.get('mun') or ''):
            i = mun_nome.get(sem_acento(parte.strip()))
            if i is not None and i not in ms:
                ms.append(i)
        pr['loc'] = {'t': 'm', 'm': ms} if ms else None
    return projs


# ---------------------------------------------------------------- minerais estratégicos e críticos
def criticos(cur):
    out = {}
    for esfera in ('federal', 'estadual'):
        c = cur['criticos'][esfera]
        cats = []
        for cat in c['categorias']:
            itens = []
            for texto, nomes in cat['itens']:
                idx = [MIN_IDX[n] for n in nomes if n in MIN_IDX]
                faltou = [n for n in nomes if n not in MIN_IDX]
                if faltou:
                    sys.exit(f'curadoria: categoria mineral inexistente {faltou}')
                itens.append({'texto': texto, 'min': idx})
            cats.append({'id': cat['id'], 'nome': cat['nome'], 'itens': itens,
                         'por_uso': [USO.index(u) for u in cat.get('por_uso_anm', []) if u in USO]})
        out[esfera] = {k: c[k] for k in ('nome', 'norma', 'jurisdicao', 'link', 'consultado_em', 'situacao', 'ressalvas') if k in c}
        out[esfera]['fontes_situacao'] = c.get('fontes_situacao', [])
        out[esfera]['categorias'] = cats
    return out


# ---------------------------------------------------------------- empresas enriquecidas (produção declarada)
def enriquecidas():
    prod = ler(ENTRADAS['producao'])
    emp = ler(ENTRADAS['empresas'])
    por = defaultdict(lambda: {'registros': [], 'ri': {}, 'operacoes': set(), 'municipios': set(), 'grupo': None, 'nome': None})
    for r in prod['registros']:
        d = por[r['cnpj_raiz']]
        d['grupo'], d['nome'] = r['grupo'], r['empresa']
        d['operacoes'].add(r['operacao'])
        d['municipios'].update(r['municipios'])
        d['registros'].append({k: r.get(k) for k in ('id', 'operacao', 'nivel', 'mineral', 'produto', 'valor', 'valor_max', 'unidade', 'medida',
                                                      'periodo_tipo', 'periodo', 'escopo', 'tipo_valor', 'fonte_nome', 'fonte_url',
                                                      'fonte_tipo', 'confianca', 'status_validacao', 'observacao')})
        if r.get('fonte_tipo') == 'ri_empresa' and r.get('fonte_url'):
            d['ri'][r['fonte_url']] = r['fonte_nome']
    out = {}
    for cnpj, d in por.items():
        out[cnpj] = {'grupo': d['grupo'], 'operacoes': sorted(d['operacoes']), 'municipios_operacao': sorted(d['municipios']),
                     'producao': sorted(d['registros'], key=lambda x: (str(x['periodo']), x['mineral'] or '')),
                     'ri': [{'u': u, 't': t} for u, t in d['ri'].items()],
                     'rateio': next((l['rateio_ccee'] for l in emp['linhas'] if l['cnpj_raiz'] == cnpj), None),
                     'notas_energia': next((l['notas_energia'] for l in emp['linhas'] if l['cnpj_raiz'] == cnpj), [])}
    return out


# ---------------------------------------------------------------- montagem
def montar():
    cur = ler(ENTRADAS['curadoria'])
    procs, n_geo, n_sgb = processos()
    por_id = {p['p']: p for p in procs}
    cfem_proc, cfem_proc_meta = cfem_por_processo(set(por_id))
    cfem_rows, meses_2026 = cfem_titular()
    ccee = ccee_por_cnpj()
    enr = enriquecidas()
    news, news_meta, news_desc = noticias(cur)
    projs = projetos(cur, por_id)

    # índice de empresas: PJ com processo, CFEM ou carga CCEE em Goiás
    agg = defaultdict(lambda: {'n': 0, 'area': 0.0, 'fases': Counter(), 'grupos': Counter(), 'status': Counter(),
                               'mun': Counter(), 'min': Counter(), 'sgb': 0, 'cfem_proc': 0.0})
    for p in procs:
        if p['e'] < 0:
            continue
        a = agg[p['e']]
        a['n'] += 1
        a['area'] += p['a'] or 0
        a['fases'][p['f']] += 1
        a['grupos'][grupo_da_fase(FASE[p['f']])] += 1
        a['status'][p['s']] += 1
        a['sgb'] += p['sgb']
        a['cfem_proc'] += p['c']
        for m in p['mu']:
            a['mun'][m] += 1
        a['min'][p['m']] += 1
    cfem_emp = defaultdict(lambda: defaultdict(float))
    cfem_mun = defaultdict(set)
    cfem_min = defaultdict(set)
    for e, ano, mu, mi, v in cfem_rows:
        cfem_emp[e][str(ano)] += v
        if mu >= 0:
            cfem_mun[e].add(mu)
        cfem_min[e].add(mi)
    ids = sorted(set(agg) | set(cfem_emp) | {CNPJ_EMP[c] for c in ccee}, key=lambda i: EMP[i][1])
    proj_por_emp = Counter(e for p in projs for e in p['e'])
    news_por_emp = Counter(n['e'] for n in news)
    # nomes alternativos: só os revisados na curadoria (aliases de notícia) e a razão social citada nos projetos já vinculados
    aliases = defaultdict(set)
    for cnpj, r in cur['noticias']['empresas'].items():
        if cnpj in CNPJ_EMP:
            aliases[CNPJ_EMP[cnpj]].update(r['entidade'] + r['grupo'])
    for p in projs:
        if p['metodo'] == 'curadoria_cnpj' and p.get('empresa_txt'):
            for e in p['e']:
                aliases[e].add(p['empresa_txt'])
    # Ponto da empresa no modo Empresas do mapa: o processo dela que mais recolheu CFEM em 2022–2026; sem CFEM, o maior título de lavra;
    # senão, o maior processo (mesma regra de scripts/build_mapa_empresas.py). É o centroide de um direito minerário, não a mina.
    ponto = {}
    for k, p in enumerate(procs):
        if p['e'] < 0 or p['la'] is None:
            continue
        chave = (p['c'] or 0, grupo_da_fase(FASE[p['f']]) == 'lavra_autorizada', round(p['a'] or 0, 1))
        if p['e'] not in ponto or chave > ponto[p['e']][0]:
            ponto[p['e']] = (chave, k)
    local_proj = localizar_projetos(projs, procs)
    empresas = []
    for i in ids:
        e = EMP[i]
        a = agg.get(i)
        x = enr.get(e[2])
        empresas.append({
            'i': i, 'id': e[0], 'nome': e[1], 'cnpj': e[2],
            'n': a['n'] if a else 0, 'area': round(a['area'], 2) if a else 0,
            'grupos': dict(a['grupos']) if a else {}, 'fases': {str(k): v for k, v in a['fases'].items()} if a else {},
            'status': {str(k): v for k, v in a['status'].items()} if a else {},
            'mun': sorted(set(a['mun']) | cfem_mun[i]) if a else sorted(cfem_mun[i]),
            'min': sorted(set(a['min']) | cfem_min[i]) if a else sorted(cfem_min[i]),
            'sgb': a['sgb'] if a else 0,
            'cfem': {k: r2(v) for k, v in sorted(cfem_emp[i].items())},
            'ccee': ccee.get(e[2], {}),
            'enr': 1 if x else 0, 'grupo': x['grupo'] if x else None,
            'alias': sorted(a for a in aliases.get(i, ()) if sem_acento(a) != sem_acento(e[1])),
            'np': proj_por_emp.get(i, 0), 'nn': news_por_emp.get(i, 0),
            'pt': ponto[i][1] if i in ponto else -1,
        })
    detalhes = {str(CNPJ_EMP[c]): v for c, v in enr.items() if c in CNPJ_EMP}

    pf = sum(1 for p in procs if p['e'] == -2)
    sem = sum(1 for p in procs if p['e'] == -1)
    cfem_total_pj = sum(v for *_, v in cfem_rows)
    # rastreamento técnico: vai para PROVENIENCIA (não para o pacote que a aba recebe)
    proveniencia = {
        'gerado_por': 'scripts/build_atlas_empresas.py',
        'entradas': {k: {'arquivo': v, 'sha256': sha(v)} for k, v in ENTRADAS.items()},
        'cfem_csv': {'arquivo': CFEM_CSV, 'sha256': sha(CFEM_CSV)} if cfem_proc is not None else None,
    }
    meta = {
        'built_on': date.today().isoformat(),
        'versao': 'v2',
        'cfem_por_processo': cfem_proc_meta if cfem_proc is not None else None,
        'periodo_cfem': [2022, 2026], 'meses_cfem_2026': meses_2026,
        'periodo_ccee': PN['meta']['periods']['ccee'],
        'cobertura': {
            'processos': len(procs), 'processos_com_geometria': n_geo, 'processos_pj': len(procs) - pf - sem,
            'processos_pf_nao_nomeados': pf, 'processos_sem_titular': sem, 'processos_em_minas_ativas_sgb': sum(p['sgb'] for p in procs),
            'empresas_indice': len(empresas), 'empresas_com_processo': sum(1 for e in empresas if e['n']),
            'empresas_com_cfem': sum(1 for e in empresas if e['cfem']), 'empresas_com_ccee': sum(1 for e in empresas if e['ccee']),
            'empresas_enriquecidas': len(detalhes), 'cfem_pj_2022_2026': r2(cfem_total_pj),
            'projetos_vinculados': sum(1 for p in projs if p['e']), 'projetos_sem_vinculo': sum(1 for p in projs if not p['e']),
            'noticias': news_meta,
            'empresas_com_ponto': sum(1 for e in empresas if e['pt'] >= 0),
            'projetos_localizacao': dict(Counter((p.get('loc') or {}).get('t', 'sem') for p in projs)),
        },
        'regras': {
            'identidade': 'Uma empresa = um CNPJ raiz de titular PJ. Nome não é chave. Pessoa física não é nomeada (só contada).',
            'fase': 'Grupo jurídico da fase ANM pelo critério do Radar: lavra autorizada (concessão de lavra, lavra garimpeira, licenciamento, registro de extração) — autoriza lavra, não comprova operação; requerimento de lavra; pesquisa; disponibilidade.',
            'situacao': 'A situação do processo é a do Panorama do Minera Goiás (Cadastro Mineiro e CFEM da ANM): "Operação ativa" = título de lavra + CFEM recolhida em 2024–2026. É evidência de comercialização declarada à ANM, não medição de produção.',
            'centroide': 'Ponto = centroide geométrico do polígono do processo (SIGMINE). Indica onde está o direito minerário, não onde está a mina, a planta ou a cava.',
            'municipio': 'Municípios IBGE intersectados pelo polígono do processo (polígono do SIGMINE cruzado com a malha municipal do IBGE).',
            'cfem': 'CFEM recolhida (R$ correntes) por titular CNPJ raiz, ano, município e mineral (ANM). 2026 é parcial.',
            'ccee': 'Carga CCEE do agente por CNPJ raiz e ano. Anualizado = observado ÷ meses × 12; a qualidade (observado completo, estimado alto, médio ou baixo) depende dos meses observados.',
            'top_n': 'Top N ordena as empresas do recorte pela métrica escolhida, no período escolhido; o universo é o conjunto de empresas que passa pelos filtros.',
            'puxadores': 'Puxadores do mercado = o menor grupo de empresas que, somado, responde por 80% da CFEM recolhida no recorte e no período (curva de Pareto).',
            'noticias': 'Notícia ligada por nome revisado pela curadoria do Minera Goiás. Nome de grupo exige contexto de Goiás no título; título que fala de outra UF/país sem citar Goiás é descartado; menção indireta (ex-funcionários, "próximo da mina") é marcada como tal.',
            'projetos': 'Radar de Projetos: vínculo pelos processos ANM citados no projeto. Levantamento de projetos e Carteira de projetos: vínculo pela lista revisada empresa→CNPJ raiz. A fonte de cada projeto é a que o registro documenta (dados abertos da ANM, documento da empresa ou site), e o link abre esse endereço.',
            'ponto_empresa': 'Modo Empresas do mapa: um ponto por empresa, no centroide do processo dela que mais recolheu CFEM em 2022–2026 (sem CFEM, o maior título de lavra; senão, o maior processo). É um direito minerário de referência, não a sede nem a mina.',
            'local_projeto': 'Modo Projetos do mapa: projeto com processo ANM citado fica no centroide do maior desses processos (indicativo); sem processo, na referência do município informado (aproximada); sem município reconhecido, só na lista. Nenhuma fonte traz coordenada documentada de mina ou planta.',
        },
        'avisos': [
            'Título minerário não é mina ativa: concessão de lavra autoriza, não comprova operação.',
            'Ponto no mapa é o centroide do direito minerário ou a referência do município, nunca a localização exata de uma mina.',
            'Produção declarada (10 empresas) não foi conferida no documento de origem.',
            'Notícias vêm de busca automática; o vínculo é por alias e pode ter omissões.',
        ],
    }
    return proveniencia, {
        'meta': meta,
        'dims': {
            'mun': [[m[0], m[1]] for m in MUN],
            'min': [[m[1], m[2]] for m in MIN],
            'fase': [{'nome': f, 'grupo': grupo_da_fase(f)} for f in FASE],
            'status': STATUS, 'uso': USO,
        },
        'criticos': criticos(cur),
        'empresas': empresas,
        'detalhes': detalhes,
        'processos': {
            'cols': ['processo', 'empresa', 'fase', 'status', 'mineral', 'uso', 'municipios', 'area_ha', 'ano_processo',
                     'cfem_2022_2026', 'lat', 'lon', 'minas_ativas_sgb'],
            'rows': [[p['p'], p['e'], p['f'], p['s'], p['m'], p['u'], p['mu'], p['a'], p['ap'], p['c'], p['la'], p['lo'], p['sgb']] for p in procs],
        },
        'cfem_processo_ano': cfem_proc,
        'cfem': {'cols': ['empresa', 'ano', 'mun', 'min', 'valor'], 'rows': cfem_rows},
        'projetos': projs,
        'noticias': news,
        'noticias_descartadas_exemplos': news_desc,
    }


def serializar(pacote):
    return json.dumps(pacote, ensure_ascii=False, separators=(',', ':'), sort_keys=False)


if __name__ == '__main__':
    proveniencia, pacote = montar()
    novo = serializar(pacote)
    prov = json.dumps(proveniencia, ensure_ascii=False, indent=1) + '\n'
    if args.verificar:
        atual = SAIDA.read_text(encoding='utf-8') if SAIDA.exists() else ''
        prov_atual = PROVENIENCIA.read_text(encoding='utf-8') if PROVENIENCIA.exists() else ''
        sem_data = lambda s: re.sub(r'"built_on":"[0-9-]+"', '', s)
        ok = sem_data(atual) == sem_data(novo) and prov_atual == prov
        print('atualizado' if ok else 'DESATUALIZADO')
        sys.exit(0 if ok else 1)
    SAIDA.write_text(novo, encoding='utf-8')
    PROVENIENCIA.write_text(prov, encoding='utf-8', newline='\n')
    c = pacote['meta']['cobertura']
    nome = SAIDA.relative_to(REPO) if SAIDA.is_relative_to(REPO) else SAIDA
    print(f"{nome}: {len(novo)/1e6:.2f} MB · {c['empresas_indice']} empresas · {c['processos']} processos · "
          f"{c['projetos_vinculados']} projetos vinculados · {c['noticias']['vinculadas']} notícias vinculadas")
