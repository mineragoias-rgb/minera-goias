"""Roteiro de navegador da auditoria crítica (27/11/2026) da aba Empresas, contra um servidor no ar: confere o SIGNIFICADO do que a tela diz
contra um oráculo que lê as fontes por outro caminho (tests/oraculo_empresas.py), não só os cliques.

    python tests/e2e_auditoria_critica_empresas.py --base https://<servidor> --capturas DIR --saida ARQ [--canal chromium|chrome|msedge]

Cobre: a sequência Maracá → CMOC → Nexa por vários caminhos (busca, cartão, dossiê, projeto, Comparar, Voltar/Avançar, link direto) com CNPJ,
processos, municípios por origem e operação documentada; nenhuma "Operação ativa" na tela nem nos arquivos; clique direto no município sem
ligar nada; pontos das empresas dentro do município no recorte; enquadramento que não foge do município; CFEM do recorte × do município;
Território com filtro e municípios clicáveis; prévia com a origem do vínculo; município no endereço; EN; console.
Contas: ATLAS_E2E_USUARIO / ATLAS_E2E_SENHA (só por variável de ambiente). Nenhuma senha no código."""
import argparse
import csv
import io
import json
import math
import os
import re
import sys
import time
import unicodedata
import zipfile
from pathlib import Path

from playwright.sync_api import sync_playwright

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / 'tests'))
import oraculo_empresas as O   # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument('--base', required=True)
ap.add_argument('--canal', default='chromium')
ap.add_argument('--capturas', required=True, help='pasta das capturas, fora do repositório')
ap.add_argument('--saida', required=True, help='relatório JSON, fora do repositório')
args = ap.parse_args()
BASE = args.base.rstrip('/')
CAPT = Path(args.capturas)
CAPT.mkdir(parents=True, exist_ok=True)
BAIX = Path(args.saida).parent / 'arquivos_exportados'
BAIX.mkdir(parents=True, exist_ok=True)
U1 = os.environ.get('ATLAS_E2E_USUARIO', '')
CONTAS = {}
if os.environ.get('ATLAS_E2E_SENHA'):
    CONTAS[U1] = os.environ['ATLAS_E2E_SENHA']
if not U1 or U1 not in CONTAS:
    sys.exit('Faltam credenciais: defina ATLAS_E2E_USUARIO/ATLAS_E2E_SENHA.')

ATLAS = json.loads((RAIZ / 'data' / 'empresas' / 'atlas_empresas.json').read_text(encoding='utf-8'))
GEO = json.loads((RAIZ / 'data' / 'atlas' / 'atlas.json').read_text(encoding='utf-8'))
PC = {c: i for i, c in enumerate(ATLAS['processos']['cols'])}
R = ATLAS['processos']['rows']
EMP = {e['cnpj']: e for e in ATLAS['empresas']}
POR_I = {e['i']: e for e in ATLAS['empresas']}
MARACA, CMOC, NEXA = '86902053', '26108898', '42416651'
CATALAO, OUVIDOR = '5205109', '5215504'
NOME_MUN = {str(m['code']): m['name'] for m in GEO['municipalities']}
norm = lambda s: unicodedata.normalize('NFD', str(s)).encode('ascii', 'ignore').decode().lower()


def merc(lat, lon):
    s = math.sin(math.radians(lat))
    return (lon + 180) / 360 * 256, (0.5 - math.log((1 + s) / (1 - s)) / (4 * math.pi)) * 256


def dentro(aneis, x, y):
    d = False
    for a in aneis:
        j = len(a) - 1
        for i in range(len(a)):
            (xi, yi), (xj, yj) = a[i], a[j]
            if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
                d = not d
            j = i
    return d


GEOMUN = {str(m['code']): [[merc(p[0], p[1]) for p in r] for r in (m.get('rings') or []) if len(r) > 2] for m in GEO['municipalities']}
LATLON = {r[PC['processo']]: (r[PC['lat']], r[PC['lon']]) for r in R}


def universo_mun(ibge, per=(2022, 2025)):
    k = next(i for i, m in enumerate(ATLAS['dims']['mun']) if str(m[0]) == ibge)
    procs, cfe = {}, {}
    for r in R:
        if r[PC['empresa']] >= 0 and k in r[PC['municipios']]:
            procs[r[PC['empresa']]] = procs.get(r[PC['empresa']], 0) + 1
    tot = 0
    for e, ano, m, _mi, v in ATLAS['cfem']['rows']:
        if m == k and per[0] <= ano <= per[1]:
            cfe[e] = cfe.get(e, 0) + v
            tot += v
    return len(set(procs) | {e for e, v in cfe.items() if v > 0}), sum(procs.values()), tot


resultados = []


def check(nome, cond, detalhe=''):
    resultados.append({'verificacao': nome, 'resultado': 'APROVADO' if cond else 'FALHOU', 'detalhe': str(detalhe)[:400]})
    print(('  OK   ' if cond else '  FALHA ') + nome + (f' — {detalhe}' if detalhe and not cond else ''), flush=True)
    return cond


def observar(page):
    ruido = []
    page.on('console', lambda m: m.type == 'error' and ruido.append(('console', m.text)))
    page.on('pageerror', lambda e: ruido.append(('pageerror', str(e))))
    page.on('response', lambda r: r.status >= 400 and ruido.append(('http', f'{r.status} {r.url}')))
    return ruido


def erros_relevantes(ruido):
    erros = [r for r in ruido if not ('tile.openstreetmap.org' in r[1] or 'fonts.g' in r[1])]
    return [r for r in erros if not ('/api/auth/me' in r[1] or (r[0] == 'console' and 'status of 401' in r[1]))]


A = 'window.EmpresasAtlas'


def entrar(ctx, url='', lingua='pt'):
    page = ctx.new_page()
    ruido = observar(page)
    page.goto(BASE + '/login.html')
    page.fill('#username', U1)
    page.fill('#password', CONTAS[U1])
    page.click('#login-form button[type=submit]')
    page.wait_for_url('**/painel.html*', timeout=20000)
    page.wait_for_selector('#loading', state='hidden', timeout=20000)
    if lingua == 'en':
        page.click('.lang-switch [data-lang="en"]')
        page.wait_for_timeout(600)
    if url:
        page.goto(BASE + url)
        page.wait_for_selector('#ea-content:not([hidden])', timeout=40000)
    else:
        page.click('[data-view="empresas"]')
        page.wait_for_selector('#ea-content:not([hidden])', timeout=40000)
    page.wait_for_function("document.querySelectorAll('#ea-lista .ea-item').length>0", timeout=30000)
    page.wait_for_function(f'{A}.contorno&&{A}.contorno()!==undefined', timeout=10000)
    page.wait_for_timeout(1800)
    return page, ruido


def ev(page, s):
    return page.evaluate(s)


def estado(page):
    return ev(page, f"({{area:{A}.area(),sel:{A}.selecionada(),foco:{A}.foco(),mun:{A}.municipio(),ficha:document.getElementById('ea-ficha').dataset.cnpj||'',"
                    f"hash:location.hash,hist:history.length,zoom:{A}.mapa().getZoom()}})")


def buscar(page, texto, tipo):
    page.fill('#ea-busca', texto)
    page.wait_for_timeout(500)
    page.locator('#ea-sugestoes li[data-j]', has=page.locator('.ea-sug-tipo', has_text=tipo)).first.dispatch_event('mousedown')
    page.wait_for_timeout(1400)


def clicar(page, xy, espera=1000):
    caixa = page.locator('#ea-map').bounding_box()
    page.mouse.click(caixa['x'] + xy[0], caixa['y'] + xy[1])
    page.wait_for_timeout(espera)


def ver(page, lat, lon, z):
    ev(page, f"(()=>{{const m={A}.mapa();m.stop();m.setView([{lat},{lon}],{z},{{animate:false}})}})()")
    page.wait_for_timeout(900)


def limites(page):
    return ev(page, f"(()=>{{const b={A}.mapa().getBounds();return [b.getSouth(),b.getWest(),b.getNorth(),b.getEast()]}})()")


def contem(b, lat, lon, folga=1e-6):
    return b[0] - folga <= lat <= b[2] + folga and b[1] - folga <= lon <= b[3] + folga


def contem_mun(b, ibge):
    pts = [p for r in next(m for m in GEO['municipalities'] if str(m['code']) == ibge)['rings'] for p in r]
    return all(contem(b, p[0], p[1], 1e-3) for p in pts)


def conferir_dossie(page, cnpj, caminho):
    """Lê o dossiê aberto e compara com o oráculo das fontes: CNPJ, nome, processos, operação documentada e municípios por origem."""
    o = O.empresa(cnpj)
    st = estado(page)
    fatos = page.inner_text('#ea-ficha-fatos')
    ok = st['area'] == 'dossie' and st['sel'] == cnpj and st['ficha'] == cnpj and page.inner_text('#ea-ficha-titulo') == EMP[cnpj]['nome']
    ok &= f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:]}" in page.inner_text('#ea-ficha-sub')
    ok &= all(NOME_MUN[m] in fatos for m in o['op']) if o['op'] else 'não documentada nesta base' in fatos
    ok &= f"Ver os {len(o['todos'])} municípios vinculados" in fatos and f"{len(o['vig'])} com direitos vigentes" in fatos
    if o['disp']:
        ok &= f"{len(o['disp'])} só em disponibilidade" in fatos
    page.click('#ea-tab-perfil')
    page.wait_for_timeout(350)
    grupos = ev(page, """[...document.querySelectorAll('#ea-corpo .ea-muns-links .ea-mun-grupo')].map(g=>[g.querySelector('.ea-mun-rot').innerText,
        [...g.querySelectorAll('[data-mun-ibge]')].map(a=>a.dataset.munIbge)])""")
    por = {'op': set(), 'vig': set(), 'disp': set(), 'cfem': set()}
    for rot, ibges in grupos:
        chave = 'op' if rot.startswith('Operação documentada') else 'vig' if rot.startswith('Direitos ANM vigentes') else 'disp' if rot.startswith('Só processos em disponibilidade') else 'cfem'
        por[chave] = set(ibges)
    ok &= all(por[k] == o[k] for k in por)
    page.click('#ea-tab-territorio')
    page.wait_for_timeout(450)
    terr = page.inner_text('#ea-corpo')
    ok &= f"Processos ANM ({o['processos']:,})".replace(',', '.') in terr
    ok &= all(op in terr for op in o['operacoes']) if o['operacoes'] else 'Nenhuma operação documentada nesta base' in terr
    if o['disponibilidade']:
        ok &= bool(re.search(rf"\b{o['disponibilidade']}\s+em disponibilidade", terr))
    ok &= not re.search(r'(?i)opera[çc][ãa]o ativa', terr)
    return check(f'Sequência · {caminho}: dossiê de {EMP[cnpj]["nome"][:28]} bate com as fontes (CNPJ, {o["processos"]} processos, {len(o["todos"])} municípios por origem, operação)',
                 ok, (st, {k: (len(por[k]), len(o[k])) for k in por}, fatos.replace('\n', ' | ')[:200]))


with sync_playwright() as pw:
    nav = pw.chromium.launch(headless=True, **({} if args.canal in ('', 'chromium') else {'channel': args.canal}))
    ctx = nav.new_context(viewport={'width': 1440, 'height': 900}, accept_downloads=True, locale='pt-BR')
    page, ruido = entrar(ctx)
    page.locator('#ea-map').scroll_into_view_if_needed()

    # ================================================================ P1.1: clique direto no município, desde a primeira visita
    # primeira visita: só aproxima a vista (no estado inteiro, Catalão fica coberto de pontos de empresa); nenhum filtro, nenhuma opção
    ver(page, -18.0, -47.9, 8)
    xy = ev(page, f"{A}.telaMunicipio('{CATALAO}')")
    clicar(page, xy, 1400)
    st = estado(page)
    check('P1.1 · Primeira visita: clicar no fundo de Catalão seleciona e contorna Catalão, sem abrir nem ligar nada em Camadas',
          (st['mun'] or {}).get('ibge') == CATALAO and ev(page, f'{A}.contorno()')['ibge'] == CATALAO
          and not ev(page, "document.getElementById('ea-camadas').open"), st)
    page.locator('#empresas-view .ea-map-panel').screenshot(path=str(CAPT / 'a01_clique_direto_catalao.png'))
    check('P2.3 · O endereço leva o município (#…/mun/<IBGE>) sem criar entrada nova no histórico', st['hash'].endswith('/mun/' + CATALAO), st['hash'])
    h0 = st['hist']
    xy = ev(page, f"{A}.telaMunicipio('{OUVIDOR}')")
    clicar(page, xy, 1200)
    check('P1.1 · Outro município troca em um clique (Catalão → Ouvidor), sem entrada nova no histórico',
          (estado(page)['mun'] or {}).get('ibge') == OUVIDOR and estado(page)['hist'] == h0 and estado(page)['hash'].endswith('/mun/' + OUVIDOR), estado(page))
    ver(page, -18.2, -47.85, 10)   # Ouvidor é pequeno: aproxima para achar um ponto livre dele (a vista não é estado da aba)
    xy = ev(page, f"{A}.telaMunicipio('{OUVIDOR}')")
    caixa = page.locator('#ea-map').bounding_box()
    page.mouse.move(caixa['x'] + xy[0], caixa['y'] + xy[1])
    page.wait_for_timeout(450)
    dica = page.inner_text('#ea-map .leaflet-tooltip.ea-tip') if page.locator('#ea-map .leaflet-tooltip.ea-tip').count() else ''
    clicar(page, xy, 900)
    check('P1.1 · No município já escolhido, a dica anuncia e o segundo clique tira o recorte', 'tirar do recorte' in dica and estado(page)['mun'] is None, dica)

    # ================================================================ P1.2: pontos das empresas dentro do município no recorte
    buscar(page, 'Catalão', 'Município')
    pontos = ev(page, f'{A}.pontosEmpresas()')
    sem = ev(page, f'{A}.semPontoLocal()')
    tot = ev(page, f'{A}.totais()')
    fora = [p for p in pontos if p[2] != CATALAO]
    ruins = [p for p in pontos if p[1] not in O.processos_no_municipio(p[0], CATALAO) or not dentro(GEOMUN[CATALAO], *merc(*LATLON[p[1]]))]
    check('P1.2 · Recorte em Catalão: todo ponto de empresa é um direito dela ligado a Catalão (fontes) com centroide dentro do contorno',
          pontos and not fora and not ruins, (len(pontos), fora[:3], ruins[:3]))
    check('P1.2 · Quem não tem esse direito fica sem ponto e é contado: pontos + "sem ponto aqui" = empresas do recorte',
          len(pontos) + len(sem) == tot['empresas'] and len(sem) > 0, (len(pontos), len(sem), tot['empresas']))
    itens = ev(page, "[...document.querySelectorAll('#ea-lista .ea-item')].map(b=>[+b.dataset.i,!!b.querySelector('.ea-tag-sempt')])")
    marcados = {POR_I[i]['cnpj'] for i, m in itens if m}
    check('P1.2 · Na lista, as empresas sem ponto local levam a marca "sem ponto aqui" (e só elas)',
          marcados == {POR_I[i]['cnpj'] for i, _m in itens} & set(sem), (len(marcados), len(sem)))
    page.locator('#empresas-view .ea-map-panel').screenshot(path=str(CAPT / 'a02_catalao_pontos_locais.png'))

    # ================================================================ P1.3 e P1.4: enquadramento e realce com município no recorte
    buscar(page, 'maraca industria', 'Empresa')
    b = limites(page)
    check('P1.3 · Maracá (fora de Catalão) selecionada com Catalão no recorte: o mapa não foge para o estado, Catalão continua inteiro na tela',
          contem_mun(b, CATALAO) and estado(page)['zoom'] >= 8.5 and ev(page, f'{A}.realce()') == [], (b, estado(page)['zoom']))
    check('P1.3 · O cartão diz que a Maracá está fora do recorte e oferece a atuação estadual como ação explícita',
          'Fora do recorte' in page.inner_text('#ea-resumo') and page.is_visible('#ea-resumo [data-estadual]'))
    buscar(page, 'cmoc', 'Empresa')
    ligados = O.processos_no_municipio(CMOC, CATALAO)
    realce = ev(page, f'{A}.realce()')
    b = limites(page)
    fora_contorno = [p for p in ligados if not dentro(GEOMUN[CATALAO], *merc(*LATLON[p]))]
    check(f'P1.3/P1.4 · CMOC com Catalão: realce = os {len(ligados)} processos ligados a Catalão (fontes), todos na tela, inclusive os {len(fora_contorno)} de centroide fora do contorno',
          sorted(realce) == ligados and all(contem(b, *LATLON[p]) for p in ligados) and contem_mun(b, CATALAO) and len(fora_contorno) == 3,
          (len(realce), len(ligados), fora_contorno))
    pt = ev(page, f"{A}.telaEmpresa('{CMOC}')")
    check('P1.2 · O ponto da CMOC no recorte fica dentro de Catalão', pt and ev(page, f'{A}.munNoPixel([{pt[0]},{pt[1]}])') == CATALAO, pt)
    page.locator('#empresas-view .ea-map-panel').screenshot(path=str(CAPT / 'a03_cmoc_catalao_enquadramento.png'))
    page.click('#ea-resumo [data-estadual]')
    page.wait_for_timeout(1200)
    todos = sorted(r[PC['processo']] for r in R if r[PC['empresa']] == EMP[CMOC]['i'] and r[PC['lat']] is not None)
    b = limites(page)
    check('P1.3 · "Ver atuação em todo o estado" (só por pedido): realce e enquadramento com os 57 direitos', sorted(ev(page, f'{A}.realce()')) == todos
          and all(contem(b, *LATLON[p]) for p in todos), len(ev(page, f'{A}.realce()')))
    page.click('#ea-resumo [data-estadual]')
    page.wait_for_timeout(1200)
    check('P1.3 · "Voltar a Catalão" devolve o realce local', sorted(ev(page, f'{A}.realce()')) == ligados)
    # P1.4 no modo Processos: os ligados com centroide fora aparecem, e o cartão do município conta
    page.click('#ea-modos [data-modo="processos"]')
    page.wait_for_timeout(800)
    page.click('#ea-mun-etq .ea-mun-etq-nome')
    page.wait_for_timeout(400)
    n_fora = int(page.get_attribute('#ea-resumo', 'data-fora') or -1)
    _e, n_proc, _c = universo_mun(CATALAO)
    esperado_fora = sum(1 for r in R if r[PC['empresa']] >= 0 and r[PC['lat']] is not None and 54 in r[PC['municipios']]
                        and not dentro(GEOMUN[CATALAO], *merc(r[PC['lat']], r[PC['lon']])))
    check('P1.4 · Cartão do município conta os processos vinculados com centroide fora do contorno (mesmo número das fontes + geometria)',
          n_fora == esperado_fora and f'{n_fora} dos {n_proc} processos vinculados' in page.inner_text('#ea-resumo'), (n_fora, esperado_fora))
    page.click('#ea-modos [data-modo="empresas"]')
    page.wait_for_timeout(500)

    # ================================================================ P1.5: CFEM do recorte × CFEM do município
    page.click('#ea-mun-etq .ea-mun-etq-x')
    page.keyboard.press('Escape')
    page.wait_for_timeout(300)
    page.fill('#ea-busca', 'cmoc')   # a busca filtra a lista enquanto digita (sem escolher sugestão)
    page.wait_for_timeout(600)
    page.locator('#ea-lista-titulo').click()   # tira o foco do campo (Esc num campo de busca o limparia: comportamento do navegador)
    page.wait_for_timeout(300)
    page.click('#ea-filtros-btn')
    page.select_option('#ea-mun', CATALAO and str(next(i for i, m in enumerate(ATLAS['dims']['mun']) if str(m[0]) == CATALAO)))
    page.wait_for_timeout(900)
    page.click('#ea-filtros-btn')
    card = page.inner_text('#ea-resumo') if page.is_visible('#ea-resumo') else ''
    e_t, p_t, c_t = universo_mun(CATALAO)
    cf_t = f"{c_t / 1e6:.1f}".replace('.', ',')
    check('P1.5 · Com a busca "cmoc" e Catalão: o cartão diz "CFEM do recorte em Catalão" e dá o município inteiro à parte (fontes)',
          'CFEM do recorte em Catalão' in card and f'Município inteiro, sem esses filtros: {e_t} empresas · {p_t} processos · CFEM R$ {cf_t} mi' in card
          and 'Empresas no recorte' in card, card.replace('\n', ' | ')[:300])
    page.locator('#empresas-view .ea-map-panel').screenshot(path=str(CAPT / 'a04_cfem_recorte_x_municipio.png'))
    page.fill('#ea-busca', '')
    page.wait_for_timeout(500)
    page.locator('#ea-lista-titulo').click()
    page.wait_for_timeout(300)
    card = page.inner_text('#ea-resumo') if page.is_visible('#ea-resumo') else ''
    check('P1.5 · Sem outros filtros, o rótulo volta a "CFEM no município" e o número é o do município', 'CFEM no município' in card and 'Município inteiro' not in card,
          card.replace('\n', ' | ')[:200])
    if page.is_visible('#ea-reset'):
        page.click('#ea-reset')
        page.wait_for_timeout(500)

    # ================================================================ Sequência Maracá → CMOC → Nexa por caminhos diferentes
    # 1) busca + "Abrir o dossiê" do cartão
    buscar(page, 'maraca industria', 'Empresa')
    page.click('#ea-resumo [data-ir="dossie"]')
    page.wait_for_timeout(900)
    conferir_dossie(page, MARACA, 'busca → cartão → dossiê')
    page.click('#ea-tab-perfil')
    page.wait_for_timeout(300)
    page.evaluate('scrollTo(0,0)')
    page.locator('#ea-ficha-fatos details').first.evaluate('d=>d.open=true')
    page.wait_for_timeout(300)
    page.locator('#ea-ficha .ea-ficha-cab').screenshot(path=str(CAPT / 'a05_maraca_cabecalho_origens.png'))
    # 2) busca no alto, com o dossiê aberto
    buscar(page, 'cmoc', 'Empresa')
    conferir_dossie(page, CMOC, 'busca no dossiê aberto')
    # 3) Comparar: as três, depois o nome da vaga da Nexa
    for c in (MARACA, CMOC, NEXA):
        ev(page, f"{A}.selecionarCnpj('{c}')")
        page.wait_for_timeout(250)
        if c not in ev(page, f'{A}.comparacao()'):
            page.click('#ea-cmp-add')
            page.wait_for_timeout(250)
    page.click('#ea-nav-comparar')
    page.wait_for_timeout(800)
    page.locator('[data-cmp-sel]', has_text='NEXA').first.click()
    page.wait_for_timeout(700)
    if estado(page)['area'] != 'dossie':
        page.click('#ea-nav-dossie')
        page.wait_for_timeout(700)
    conferir_dossie(page, NEXA, 'vaga do Comparar')
    # 4) projeto (Chapada, da Maracá): balão do projeto → dossiê
    page.click('#ea-nav-explorar')
    page.wait_for_timeout(600)
    page.click('#ea-modos [data-modo="projetos"]')
    page.wait_for_timeout(700)
    p = ev(page, f"{A}.telaProjeto('GO-001')")
    ver(page, p[2], p[3], 10)
    p = ev(page, f"{A}.telaProjeto('GO-001')")
    clicar(page, p[:2], 900)
    if page.locator('.leaflet-popup .ea-pop [data-j]').count():
        for b_ in page.locator('.leaflet-popup .ea-pop [data-j]').all():
            if 'Chapada' in b_.inner_text():
                b_.click()
                break
        page.wait_for_timeout(700)
    page.locator('.leaflet-popup [data-dossie]').first.click()
    page.wait_for_timeout(900)
    conferir_dossie(page, MARACA, 'balão do projeto Chapada → dossiê')
    page.click('#ea-nav-explorar')
    page.wait_for_timeout(500)
    page.click('#ea-modos [data-modo="empresas"]')
    page.wait_for_timeout(500)
    # 5) Voltar e Avançar: a ficha nunca fica com outra empresa (visível ou escondida)
    obsoletos = []
    for passo in ['back'] * 6 + ['forward'] * 4:
        (page.go_back if passo == 'back' else page.go_forward)()
        page.wait_for_timeout(900)
        st = estado(page)
        if st['ficha'] and st['ficha'] != st['sel']:
            obsoletos.append(st)
        if st['area'] == 'dossie' and st['sel'] in (MARACA, CMOC, NEXA):
            conferir_dossie(page, st['sel'], f'Voltar/Avançar ({passo})')
    check('Sequência · Voltar/Avançar: a ficha (mesmo escondida) nunca guarda outra empresa', not obsoletos, obsoletos[:2])
    # 6) link direto
    p2, r2 = entrar(nav.new_context(viewport={'width': 1440, 'height': 900}, locale='pt-BR'), url=f'/painel.html?r=n#empresas/{NEXA}')
    conferir_dossie(p2, NEXA, 'link direto #empresas/<cnpj>')
    p2.context.close()

    # ================================================================ P0.3: nenhuma "Operação ativa" na tela nem nos arquivos
    ev(page, f"{A}.selecionarCnpj('{CMOC}')")
    page.click('#ea-nav-dossie')
    page.wait_for_timeout(700)
    page.click('#ea-tab-territorio')
    page.wait_for_timeout(500)
    terr = page.inner_text('#ea-corpo')
    check('P0.3 · Território: a situação "Operação ativa" aparece como "Lavra com CFEM recente · indício de atividade, não confirmação"',
          'indício de atividade, não confirmação' in terr and not re.search(r'(?i)opera[çc][ãa]o ativa', terr))
    page.locator('#ea-corpo .ea-explora').screenshot(path=str(CAPT / 'a06_territorio_tres_blocos.png'))
    with page.expect_download() as d:
        page.click('#ea-corpo [data-exp="proc-csv"]')
    arq = BAIX / d.value.suggested_filename
    d.value.save_as(arq)
    txt = arq.read_bytes().decode('utf-8-sig')
    linhas = list(csv.DictReader(io.StringIO(txt, newline=''), delimiter=';'))
    check('P0.3 · CSV de processos: sem "Operação ativa"; a situação diz "indício"; municípios com código IBGE',
          not re.search(r'(?i)opera[çc][ãa]o ativa', txt) and any('indício' in l['situacao_panorama'] for l in linhas)
          and all(l['municipios_ibge'] for l in linhas), len(linhas))
    with page.expect_download() as d:
        page.click('#ea-ficha-xlsx')
    arq = BAIX / d.value.suggested_filename
    d.value.save_as(arq)
    xml = ' '.join(zipfile.ZipFile(arq).read(n).decode('utf-8') for n in zipfile.ZipFile(arq).namelist() if n.endswith('.xml'))
    check('P0.1 · Dossiê em Excel: municípios separados por origem (operação documentada, direitos vigentes, só disponibilidade, só CFEM)',
          all(k in xml for k in ('municipios_operacao_documentada', 'municipios_direitos_vigentes', 'municipios_so_disponibilidade', 'municipios_so_cfem'))
          and 'Santa Fé de Goiás' in xml and not re.search(r'(?i)opera[çc][ãa]o ativa', xml))

    # ================================================================ P1.6/P1.7/P2.1: Território da Maracá (173) e da Nexa (201)
    ev(page, f"{A}.selecionarCnpj('{MARACA}')")
    page.wait_for_timeout(600)
    page.click('#ea-tab-territorio')
    page.wait_for_timeout(500)
    sobra = ev(page, "(()=>{const w=document.querySelector('#ea-corpo .table-wrap');return w.scrollWidth-w.clientWidth})()")
    check('P2.1 · Tabela de 173 processos: CFEM com total e "série" fechada (sem estourar a largura em 1440 px)',
          sobra <= 1 and page.locator('#ea-corpo .ea-serie').count() > 0 and page.locator('#ea-corpo .ea-serie[open]').count() == 0, sobra)
    page.fill('#ea-terr-q', 'Paraúna')
    page.wait_for_timeout(500)
    esperado = sum(1 for pid, _f, muns in O.indices()[1][MARACA] if any('parauna' in norm(NOME_MUN[m]) for m in muns))
    cont = page.inner_text('#ea-terr-n')
    check(f'P1.7 · Filtro do Território: "Paraúna" → {esperado} de 173 processos (Paraúna e São João da Paraúna, pelas fontes), foco no campo',
          cont == f'{esperado} de 173 processos' and ev(page, "document.activeElement.id") == 'ea-terr-q', cont)
    linhas_vis = ev(page, "[...document.querySelectorAll('#ea-corpo tr[data-linha-proc]')].map(r=>r.className)")
    check('P0.2 · Os processos de Paraúna aparecem como disponibilidade (linha apagada), não como direito vigente',
          linhas_vis and all('ea-linha-disp' in c for c in linhas_vis), linhas_vis[:3])
    page.locator('#ea-corpo').screenshot(path=str(CAPT / 'a07_territorio_filtro_parauna.png'))
    lk = page.locator('#ea-corpo tr[data-linha-proc] .ea-mun-link', has_text='Paraúna').first
    ibge_parauna = lk.get_attribute('data-mun-ibge')
    lk.click()
    page.wait_for_timeout(1500)
    check('P1.6 · Município na tabela do Território → Explorar com aquele município (IBGE) e a empresa mantida',
          (estado(page)['mun'] or {}).get('ibge') == ibge_parauna and estado(page)['sel'] == MARACA and estado(page)['area'] == 'explorar', estado(page))
    page.go_back()
    page.wait_for_timeout(1200)
    ev(page, f"{A}.selecionarCnpj('{NEXA}')")
    page.wait_for_timeout(500)
    if estado(page)['area'] != 'dossie':
        page.click('#ea-nav-dossie')
        page.wait_for_timeout(600)
    page.click('#ea-tab-territorio')
    page.wait_for_timeout(500)
    t0 = time.time()
    page.fill('#ea-terr-q', 'Campos Verdes')
    page.wait_for_function("document.getElementById('ea-terr-n')&&document.getElementById('ea-terr-n').textContent.length>0", timeout=5000)
    dt = time.time() - t0
    esp = sum(1 for _pid, _f, muns in O.indices()[1][NEXA] if any(NOME_MUN[m] == 'Campos Verdes' for m in muns))
    check(f'P1.7 · Nexa (201 processos): filtro "Campos Verdes" → {esp} de 201, em menos de 1 s', page.inner_text('#ea-terr-n') == f'{esp} de 201 processos' and dt < 1,
          (page.inner_text('#ea-terr-n'), round(dt, 2)))

    # ================================================================ P2.4 e P0.2: a prévia diz a origem do vínculo
    ev(page, f"{A}.selecionarCnpj('{MARACA}')")
    page.wait_for_timeout(500)
    page.click('#ea-tab-perfil')
    page.wait_for_timeout(400)
    lk = page.locator('#ea-corpo .ea-mun-hist .ea-mun-link', has_text='Paraúna').first
    lk.scroll_into_view_if_needed()
    lk.hover()
    page.wait_for_timeout(1100)
    pv = ev(page, f'{A}.previa()') or {}
    check('P0.2 · Prévia de Paraúna (Maracá): "todos em disponibilidade: vínculo histórico, não direito vigente"',
          'Todos em disponibilidade' in pv.get('texto', '') and pv.get('vig') == '0', pv.get('texto', '')[:200])
    page.locator('#ea-previa').screenshot(path=str(CAPT / 'a08_previa_disponibilidade.png'))
    page.mouse.move(700, 60)
    so_cfem = O.empresas_com_municipio_so_cfem()[0]
    ibge_cf = sorted(O.empresa(so_cfem)['cfem'])[0]
    ev(page, f"{A}.selecionarCnpj('{so_cfem}')")
    page.wait_for_timeout(600)
    page.click('#ea-tab-perfil')
    page.wait_for_timeout(400)
    lk = page.locator(f'#ea-corpo .ea-mun-cfem [data-mun-ibge="{ibge_cf}"]').first
    lk.scroll_into_view_if_needed()
    lk.hover()
    page.wait_for_timeout(1100)
    pv = ev(page, f'{A}.previa()') or {}
    check('P2.4 · Município só com CFEM: a prévia diz "CFEM registrada aqui; nenhum direito ANM da empresa vinculado na base"',
          'CFEM registrada aqui' in pv.get('texto', '') and pv.get('n') == '0', (so_cfem, ibge_cf, pv.get('texto', '')[:200]))
    page.mouse.move(700, 60)

    # ================================================================ P2.3: link com município
    p3, r3 = entrar(nav.new_context(viewport={'width': 1440, 'height': 900}, locale='pt-BR'), url=f'/painel.html?r=m#empresas/explorar/{CMOC}/mun/{CATALAO}')
    p3.wait_for_timeout(1200)
    st = estado(p3)
    check('P2.3 · Link #empresas/explorar/<cnpj>/mun/<IBGE> abre a CMOC com Catalão recortado e enquadrado', st['sel'] == CMOC and (st['mun'] or {}).get('ibge') == CATALAO
          and contem_mun(limites(p3), CATALAO), st)
    check('Console sem erros (link com município)', not erros_relevantes(r3), erros_relevantes(r3)[:4])
    p3.context.close()
    check('Console e rede sem erros (roteiro principal, PT)', not erros_relevantes(ruido), erros_relevantes(ruido)[:6])
    ctx.close()

    # ================================================================ EN
    ctx = nav.new_context(viewport={'width': 1440, 'height': 900}, locale='en-US')
    page, ruido = entrar(ctx, lingua='en')
    ev(page, f"{A}.selecionarCnpj('{MARACA}')")
    page.click('#ea-nav-dossie')
    page.wait_for_timeout(700)
    page.click('#ea-tab-territorio')
    page.wait_for_timeout(500)
    t_en = page.inner_text('#ea-corpo')
    check('EN · Territory: documented operation × signs of activity × rights, and the status as a sign, not confirmation',
          'DOCUMENTED OPERATION' in t_en.upper() and 'SIGNS OF ACTIVITY' in t_en.upper() and 'sign of activity, not confirmation' in t_en
          and 'in availability' in t_en, t_en[:200])
    check('EN · console sem erros', not erros_relevantes(ruido), erros_relevantes(ruido)[:4])
    ctx.close()
    nav.close()

falhas = [r for r in resultados if r['resultado'] != 'APROVADO']
Path(args.saida).parent.mkdir(parents=True, exist_ok=True)
Path(args.saida).write_text(json.dumps({'executado_em': time.strftime('%Y-%m-%d %H:%M:%S'), 'base': BASE, 'navegador': args.canal,
                                         'total': len(resultados), 'falhas': len(falhas), 'verificacoes': resultados},
                                        ensure_ascii=False, indent=1), encoding='utf-8')
print(f'\n{len(resultados) - len(falhas)}/{len(resultados)} verificações aprovadas')
sys.exit(1 if falhas else 0)
