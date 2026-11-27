"""Oráculo independente da interface e do gerador da aba Empresas: lê as FONTES (não o pacote atlas_empresas.json) e diz, para um CNPJ raiz,
quais processos ANM a empresa tem, em que fase, em que municípios (por código IBGE), onde recolheu CFEM e quais operações ela mesma divulga.

Fontes (as mesmas de que o gerador parte, lidas aqui por outro caminho de código):
- data/panorama/panorama.json: processos (titular por CNPJ raiz, fase, município principal) e CFEM (ano, município de origem, titular);
- data/mapa/tabelas/processos_complemento.json: todos os municípios de cada processo (quando há mais de um);
- data/producao/producao.json: operações e municípios que a própria empresa divulga (operação documentada).

Usado por tests/test_atlas_empresas.py (AuditoriaCriticaTests) e tests/e2e_auditoria_critica_empresas.py, para conferir significado, não só
cliques: o que a tela diz tem de bater com o que as fontes dizem."""
import json
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
DISPONIBILIDADE = {'DISPONIBILIDADE', 'APTO PARA DISPONIBILIDADE'}


@lru_cache(maxsize=1)
def fontes():
    pn = json.loads((RAIZ / 'data' / 'panorama' / 'panorama.json').read_text(encoding='utf-8'))
    comp = json.loads((RAIZ / 'data' / 'mapa' / 'tabelas' / 'processos_complemento.json').read_text(encoding='utf-8'))
    prod = json.loads((RAIZ / 'data' / 'producao' / 'producao.json').read_text(encoding='utf-8'))
    return pn, comp, prod


@lru_cache(maxsize=1)
def indices():
    pn, comp, prod = fontes()
    nome_mun = {str(m[0]): m[1] for m in pn['dims']['mun']}
    cod_por_nome = {m[1]: str(m[0]) for m in pn['dims']['mun']}
    comp_mun = {pid: [str(comp['dic']['municipios'][k]) for k in ms] for pid, ms in zip(comp['processos'], comp['municipios'])}
    C = {c: i for i, c in enumerate(pn['proc']['cols'])}
    emp = pn['dims']['emp']
    procs = defaultdict(list)   # cnpj raiz -> [(processo, fase, [ibge...])]
    for r in pn['proc']['rows']:
        e = r[C['emp']]
        if e is None or e < 0 or emp[e][3] != 'pj':
            continue
        pid = r[C['processo']]
        muns = [c for c in comp_mun.get(pid, []) if c in nome_mun] or ([str(pn['dims']['mun'][r[C['mun']]][0])] if r[C['mun']] is not None and r[C['mun']] >= 0 else [])
        procs[emp[e][2]].append((pid, pn['dims']['fase'][r[C['fase']]], muns))
    CF = {c: i for i, c in enumerate(pn['cfem']['cols'])}
    cfem = defaultdict(lambda: defaultdict(float))   # cnpj raiz -> ibge -> R$ (todos os anos)
    for r in pn['cfem']['rows']:
        e, m = r[CF['emp']], r[CF['mun']]
        if e is None or e < 0 or emp[e][3] != 'pj' or m is None or m < 0:
            continue
        cfem[emp[e][2]][str(pn['dims']['mun'][m][0])] += r[CF['valor']]
    ops = defaultdict(lambda: {'operacoes': set(), 'municipios': set()})
    for r in prod['registros']:
        ops[r['cnpj_raiz']]['operacoes'].add(r['operacao'])
        ops[r['cnpj_raiz']]['municipios'].update(cod_por_nome[n] for n in r['municipios'] if n in cod_por_nome)
    return nome_mun, procs, cfem, ops


def empresa(cnpj):
    """Tudo o que as fontes dizem da empresa, com os municípios separados pela origem do vínculo (códigos IBGE)."""
    nome_mun, procs, cfem, ops = indices()
    ps = procs.get(cnpj, [])
    vig, disp = set(), set()
    for _pid, fase, muns in ps:
        (disp if fase in DISPONIBILIDADE else vig).update(muns)
    cf = {m for m, v in cfem.get(cnpj, {}).items() if v}
    o = ops.get(cnpj, {'operacoes': set(), 'municipios': set()})
    return {
        'processos': len(ps),
        'disponibilidade': sum(1 for _p, f, _m in ps if f in DISPONIBILIDADE),
        'vig': vig, 'disp': disp - vig, 'cfem': cf - vig - disp,
        'todos': vig | disp | cf,
        'op': set(o['municipios']), 'operacoes': set(o['operacoes']),
        'nome': lambda c: nome_mun[c],
    }


def processos_no_municipio(cnpj, ibge):
    _n, procs, _c, _o = indices()
    return sorted(pid for pid, _f, muns in procs.get(cnpj, []) if ibge in muns)


def pares_so_disponibilidade():
    """Pares empresa × município ligados SÓ por processos em disponibilidade (vínculo histórico)."""
    _n, procs, _c, _o = indices()
    pares = []
    for cnpj in procs:
        e = empresa(cnpj)
        pares += [(cnpj, m) for m in e['disp']]
    return pares


def empresas_com_municipio_so_cfem():
    _n, procs, cfem, _o = indices()
    return sorted(c for c in set(procs) | set(cfem) if empresa(c)['cfem'])
