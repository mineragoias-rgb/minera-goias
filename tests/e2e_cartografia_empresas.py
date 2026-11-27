"""Roteiro de navegador da cartografia da aba Empresas: empresa × direito ANM × município × operação, contra um servidor no ar.
Cobre os 17 testes de aceitação da missão de cartografia (cartão único, clique só na camada do modo, processos sobrepostos, processo →
dossiê → mapa, seleção municipal por código IBGE pelas três portas, recorte, prévia municipal no dossiê, casos de borda, exportação,
mesa/tablet/celular, PT/EN e console), sempre com os dados reais do pacote.

    python tests/e2e_cartografia_empresas.py --base https://<servidor> --capturas DIR --saida ARQ [--canal chromium|chrome|msedge]

Contas: variáveis ATLAS_E2E_USUARIO / ATLAS_E2E_SENHA (só por variável de ambiente). Nenhuma senha no código.
Os números esperados (processos vinculados por código IBGE, pontos da prévia dentro do contorno) são recalculados aqui, dos mesmos
arquivos que a API serve, com a mesma projeção do mapa — não são números fixos."""
import argparse
import csv
import io
import json
import math
import os
import re
import sys
import time
import zipfile
from pathlib import Path

from playwright.sync_api import sync_playwright

RAIZ = Path(__file__).resolve().parents[1]
ap = argparse.ArgumentParser()
ap.add_argument('--base', required=True)
ap.add_argument('--canal', default='chromium')
ap.add_argument('--capturas', required=True, help='pasta das capturas, fora do repositório')
ap.add_argument('--saida', required=True, help='relatório JSON, fora do repositório')
args = ap.parse_args()
BASE = args.base.rstrip('/')
CAPT = Path(args.capturas)
CAPT.mkdir(parents=True, exist_ok=True)
BAIX = Path(args.saida).parent / 'arquivos_exportados_cartografia'
BAIX.mkdir(parents=True, exist_ok=True)

U1 = os.environ.get('ATLAS_E2E_USUARIO', '')
CONTAS = {}
if os.environ.get('ATLAS_E2E_SENHA'):
    CONTAS[U1] = os.environ['ATLAS_E2E_SENHA']
if not U1 or U1 not in CONTAS:
    sys.exit('Faltam credenciais: defina ATLAS_E2E_USUARIO/ATLAS_E2E_SENHA.')

# ---------------------------------------------------------------- dados reais, para conferir a tela
ATLAS = json.loads((RAIZ / 'data' / 'empresas' / 'atlas_empresas.json').read_text(encoding='utf-8'))
GEO = json.loads((RAIZ / 'data' / 'atlas' / 'atlas.json').read_text(encoding='utf-8'))
PC = {c: i for i, c in enumerate(ATLAS['processos']['cols'])}
R = ATLAS['processos']['rows']
MUN = ATLAS['dims']['mun']
KMUN = {str(m[0]): k for k, m in enumerate(MUN)}
EMP = {e['cnpj']: e for e in ATLAS['empresas']}
FASES = ATLAS['dims']['fase']
CATALAO, OUVIDOR, MINEIROS = '5205109', '5215504', '5213103'
ITAGUARI = next(str(m[0]) for m in MUN if m[1] == 'Itaguari')
CMOC = '26108898'


def merc(lat, lon):
    """Mesma projeção do mapa (EPSG:3857 no zoom 0), para o teste de ponto no contorno dar o mesmo que no navegador."""
    x = (lon + 180) / 360 * 256
    s = math.sin(math.radians(lat))
    y = (0.5 - math.log((1 + s) / (1 - s)) / (4 * math.pi)) * 256
    return x, y


def dentro(aneis, x, y):
    d = False
    for a in aneis:
        j = len(a) - 1
        for i in range(len(a)):
            xi, yi = a[i]
            xj, yj = a[j]
            if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
                d = not d
            j = i
    return d


GEOMUN = {str(m['code']): [[merc(p[0], p[1]) for p in r] for r in (m.get('rings') or []) if len(r) > 2] for m in GEO['municipalities']}


def procs_da_empresa_no_mun(cnpj, ibge):
    i, k = EMP[cnpj]['i'], KMUN[ibge]
    ks = [r for r in R if r[PC['empresa']] == i and k in r[PC['municipios']]]
    dentro_ = [r for r in ks if r[PC['lat']] is not None and dentro(GEOMUN[ibge], *merc(r[PC['lat']], r[PC['lon']]))]
    return ks, dentro_


def universo_mun(ibge, per=(2022, 2025)):
    """Empresas e processos do recorte municipal como a aba calcula: processo vinculado pelo código IBGE (não pelo centroide) ou CFEM
    recolhida no município no período."""
    k = KMUN[ibge]
    procs = {}
    for r in R:
        if r[PC['empresa']] >= 0 and k in r[PC['municipios']]:
            procs[r[PC['empresa']]] = procs.get(r[PC['empresa']], 0) + 1
    cf = {}
    for e, ano, m, _min, v in ATLAS['cfem']['rows']:
        if m == k and per[0] <= ano <= per[1]:
            cf[e] = cf.get(e, 0) + v
    emp = set(procs) | {e for e, v in cf.items() if v > 0}
    return len(emp), sum(procs.values()), sum(cf.values())


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


def entrar(ctx, lingua='pt'):
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
    page.click('[data-view="empresas"]')
    page.wait_for_selector('#ea-content:not([hidden])', timeout=40000)
    page.wait_for_function("document.querySelectorAll('#ea-lista .ea-item').length>0", timeout=30000)
    page.wait_for_function('window.EmpresasAtlas.contorno!==undefined', timeout=10000)
    page.wait_for_timeout(1500)
    return page, ruido


A = 'window.EmpresasAtlas'


def ev(page, s):
    return page.evaluate(s)


def estado(page):
    return ev(page, f"({{area:{A}.area(),sel:{A}.selecionada(),foco:{A}.foco(),proc:{A}.processoFoco(),mun:{A}.municipio(),modo:{A}.modo(),"
                    f"zoom:{A}.mapa().getZoom(),url:location.href,hist:history.length}})")


def ver(page, lat, lon, z):
    ev(page, f"(()=>{{const m={A}.mapa();m.stop();m.setView([{lat},{lon}],{z},{{animate:false}})}})()")
    page.wait_for_timeout(900)


def ir_processo(page, proc, z=13):
    p = ev(page, f"{A}.processo('{proc}')")
    page.locator('#ea-map').scroll_into_view_if_needed()
    ver(page, p['lat'], p['lon'], z)
    return ev(page, f"(()=>{{const p={A}.mapa().latLngToContainerPoint([{p['lat']},{p['lon']}]);return [p.x,p.y]}})()")


def clicar(page, xy, espera=900):
    caixa = page.locator('#ea-map').bounding_box()
    page.mouse.click(caixa['x'] + xy[0], caixa['y'] + xy[1])
    page.wait_for_timeout(espera)


def mover(page, xy):
    caixa = page.locator('#ea-map').bounding_box()
    page.mouse.move(caixa['x'] + xy[0], caixa['y'] + xy[1])
    page.wait_for_timeout(450)


def modo(page, m):
    page.click(f'#ea-modos [data-modo="{m}"]')
    page.wait_for_timeout(600)


def zerar(page):
    """Sem empresa, sem processo, sem município, sem filtros: o Explorar do começo."""
    ev(page, "(()=>{const m=window.EmpresasAtlas.mapa();if(m)m.closePopup()})()")
    if ev(page, f'{A}.area()') != 'explorar':
        page.click('#ea-nav-explorar')
        page.wait_for_timeout(500)
    for _ in range(6):
        if ev(page, f'{A}.selecionada()') is None and ev(page, f'{A}.processoFoco()') is None and ev(page, f'{A}.municipio()') is None:
            break
        page.keyboard.press('Escape')
        page.wait_for_timeout(250)
    if page.is_visible('#ea-reset'):
        page.click('#ea-reset')
        page.wait_for_timeout(400)


def buscar(page, texto, tipo):
    page.fill('#ea-busca', texto)
    page.wait_for_timeout(500)
    sug = page.locator('#ea-sugestoes li[data-j]', has=page.locator('.ea-sug-tipo', has_text=tipo)).first
    rot = sug.inner_text()
    sug.dispatch_event('mousedown')
    page.wait_for_timeout(1500)
    return rot


def baixar(page, seletor, pasta):
    with page.expect_download() as d:
        page.click(seletor)
    destino = Path(pasta) / d.value.suggested_filename
    d.value.save_as(destino)
    return destino


with sync_playwright() as pw:
    nav = pw.chromium.launch(headless=True, **({} if args.canal in ('', 'chromium') else {'channel': args.canal}))
    ctx = nav.new_context(viewport={'width': 1440, 'height': 900}, accept_downloads=True, locale='pt-BR')
    page, ruido = entrar(ctx)
    page.locator('#ea-map').scroll_into_view_if_needed()

    # ================================================================ 1 e 9. modo Empresas: só os pontos de empresa respondem
    ev(page, f"{A}.selecionarCnpj('{CMOC}')")
    page.wait_for_timeout(1500)
    xy = ir_processo(page, '861461/2015', 12)   # pesquisa da CMOC em Catalão, longe do ponto de referência da empresa
    acerto = ev(page, f'{A}.acerto([{xy[0]},{xy[1]}])')
    mover(page, xy)
    tip = page.locator('#ea-map .leaflet-tooltip.ea-tip')
    cursor = ev(page, f'{A}.mapa().getContainer().style.cursor')
    # sem alvo de processo: nenhuma dica do processo; desde a auditoria crítica o fundo é alvo de MUNICÍPIO, então a dica (e a mão) são do município
    dica = tip.inner_text() if tip.count() and tip.is_visible() else ''
    check('1 · Empresas: processo da empresa selecionada é realce sem alvo (a dica sob o cursor é a do município, não a do processo)',
          acerto is None and '861461/2015' not in dica and (not dica or '· GO' in dica), (acerto, cursor, dica[:80]))
    clicar(page, xy)
    st = estado(page)
    check('1 · Empresas: clicar no realce do processo NÃO seleciona processo nem abre cartão de processo', st['proc'] is None and st['foco'] != 'processo', st)
    page.locator('.ea-map-panel').screenshot(path=str(CAPT / 'c01_empresas_realce_sem_clique.png'))
    zerar(page)
    ver(page, -18.15, -47.95, 9)
    xy_emp = ev(page, f"{A}.telaEmpresa('{CMOC}')")
    clicar(page, xy_emp)
    if page.locator('.leaflet-popup .ea-pop [data-i]').count():
        page.locator('.leaflet-popup .ea-pop [data-i]', has_text='CMOC').first.click()
        page.wait_for_timeout(600)
    check('9 · Empresas: o ponto da empresa (mesmo sobre um título ANM) abre o cartão da EMPRESA', estado(page)['foco'] == 'empresa' and estado(page)['sel'] == CMOC,
          estado(page))
    check('9 · Empresas: nenhum objeto Leaflet interativo por ponto ou polígono; marcador de operação sem clique',
          page.locator('#ea-map .leaflet-interactive').count() == 0 and page.locator('#ea-map .ea-op-icone.leaflet-interactive').count() == 0)
    page.locator('.ea-map-panel').screenshot(path=str(CAPT / 'c02_cartao_empresa.png'))
    card = page.inner_text('#ea-resumo')
    check('1 · Cartão da empresa diz que o ponto é um direito de referência (não sede nem mina)', 'não sede nem mina' in card, card[:200])

    # ================================================================ 2. Processos: o processo exato, não a empresa por substituição
    zerar(page)
    modo(page, 'processos')
    xy = ir_processo(page, '803343/1973', 13)
    clicar(page, xy, 1400)
    st = estado(page)
    card = page.inner_text('#ea-resumo')
    r = next(x for x in R if x[PC['processo']] == '803343/1973')
    href = page.get_attribute('#ea-resumo .ea-card-anm a', 'href') or ''
    check('2 · Processos: clicar seleciona o processo exato (foco processo), sem selecionar a empresa no lugar', st['foco'] == 'processo'
          and st['proc'] == '803343/1973' and st['sel'] is None and st['zoom'] == 13, st)
    check('2 · Cartão do processo: número ANM, fase exata, mineral, área (ha), município e titular correto',
          '803343/1973' in card and FASES[r[PC['fase']]]['nome'] in card and 'Nióbio' in card and '980,00' in card and 'ha' in card
          and 'Catalão' in card and EMP[CMOC]['nome'] in card, card.replace('\n', ' | ')[:300])
    check('2 · Cartão do processo: CFEM só do processo, com período e fonte; nada da CFEM do titular',
          'CFEM do processo · 2022–2025' in card and 'por processo' in card and '123,5' not in card, card.replace('\n', ' | ')[:300])
    check('2 · Cartão do processo: Ver processo no dossiê, Ver empresa titular e Consultar na ANM (URL oficial válida)',
          page.is_visible('#ea-resumo [data-proc-dossie]') and page.is_visible('#ea-resumo [data-proc-titular]')
          and re.fullmatch(r'https://sistemas\.anm\.gov\.br/SCM/Extra/site/admin/dadosProcesso\.aspx\?numero=803343&ano=1973', href), href)
    check('2 · Cartão do processo: microtexto "centroide do título, não a mina; título não comprova operação"',
          'não a mina' in card and 'não comprova' in card)
    page.mouse.move(5, 5)
    page.locator('.ea-map-panel').screenshot(path=str(CAPT / 'c03_cartao_processo.png'))
    check('12 · Um cartão só sobre o mapa (nenhum outro cartão ou balão concorrente)', page.locator('#empresas-view .ea-card:visible').count() == 1
          and page.locator('.leaflet-popup').count() == 0)
    clicar(page, xy)
    check('Desmarcar o processo: clicar de novo no mesmo', estado(page)['proc'] is None and page.is_hidden('#ea-resumo'))
    clicar(page, xy)
    page.keyboard.press('Escape')
    page.wait_for_timeout(300)
    check('Desmarcar o processo: Esc', estado(page)['proc'] is None)
    clicar(page, xy)
    page.click('#ea-resumo .ea-card-x')
    page.wait_for_timeout(300)
    check('Desmarcar o processo: × do cartão', estado(page)['proc'] is None and page.is_hidden('#ea-resumo'))

    # ================================================================ 3. sobrepostos: mesma empresa e empresas diferentes, sem escolha silenciosa
    for par, rot in ((['860436/2014', '860684/2004'], 'mesmo titular'), (['862299/2011', '860021/2007'], 'titulares diferentes')):
        zerar(page)
        modo(page, 'processos')
        xy = ir_processo(page, par[0], 13)
        clicar(page, xy, 1000)
        itens = page.locator('.leaflet-popup .ea-pop [data-k]')
        txt = page.inner_text('.leaflet-popup') if page.locator('.leaflet-popup').count() else ''
        porI = {e['i']: e['nome'] for e in ATLAS['empresas']}
        titulares = {porI.get(next(x for x in R if x[PC['processo']] == p_)[PC['empresa']], '') for p_ in par}
        check(f'3 · Sobrepostos ({rot}): lista com número ANM + mineral + fase e titular, nenhum escolhido em silêncio',
              itens.count() >= 2 and all(p in txt for p in par) and all(t_ in txt for t_ in titulares) and estado(page)['proc'] is None,
              (itens.count(), txt.replace('\n', ' | ')[:240], estado(page)['proc']))
        foco_ok = ev(page, "!!document.activeElement&&!!document.activeElement.closest('.leaflet-popup')")
        page.keyboard.press('ArrowDown')
        segundo = ev(page, "document.activeElement&&document.activeElement.dataset.k!=null?document.activeElement.innerText.trim():null")
        page.keyboard.press('Enter')
        page.wait_for_timeout(800)
        check(f'3 · Sobrepostos ({rot}): teclado (foco na lista, ↓, Enter) escolhe o processo indicado', foco_ok and segundo and estado(page)['proc'] == segundo.split()[-1],
              (foco_ok, segundo, estado(page)['proc']))
        if rot == 'mesmo titular':
            page.locator('.ea-map-panel').screenshot(path=str(CAPT / 'c04_sobrepostos_escolhido.png'))
    # lista grande: rolagem e filtro, sem corte
    zerar(page)
    modo(page, 'processos')
    ver(page, -14.45, -48.35, 9)   # Niquelândia / Minaçu: títulos muito próximos
    denso = None
    for y in range(80, 520, 14):
        for x in range(80, 700, 14):
            a_ = ev(page, f'{A}.acerto([{x},{y}])')
            if a_ and a_['tipo'] == 'ponto' and a_['n'] > 8 and (not denso or a_['n'] > denso[1]):
                denso = ((x, y), a_['n'])
        if denso and denso[1] > 14:
            break
    if denso:
        clicar(page, denso[0], 1000)
        n_lista = page.locator('.leaflet-popup .ea-pop [data-k]').count()
        filtro = page.locator('.leaflet-popup .ea-pop-filtro')
        # o que o mapa achou no pixel exato do clique (o balão fica nesse ponto): a lista tem de ter todos
        no_clique = ev(page, f"(()=>{{const m={A}.mapa(),c=m.latLngToContainerPoint(m._popup.getLatLng());return {A}.acerto([c.x,c.y])}})()")
        ids_lista = set(t_.strip().split()[-1] for t_ in page.locator('.leaflet-popup .ea-pop [data-k]').all_inner_texts())
        check('3 · Muitos sobrepostos: a lista traz todos (sem corte) e tem filtro', n_lista > 8 and filtro.count() == 1 and no_clique
              and n_lista == no_clique['n'] and ids_lista == set(no_clique['ids']), (n_lista, no_clique and no_clique['n']))
        alvo = page.locator('.leaflet-popup .ea-pop [data-k]').nth(n_lista - 1).inner_text().strip().split()[-1]
        filtro.fill(alvo.split('/')[0])
        page.wait_for_timeout(300)
        vis = page.locator('.leaflet-popup .ea-pop li:not([hidden]) [data-k]').count()
        check('3 · Filtro da lista encontra o último processo pelo número', 1 <= vis < n_lista, (vis, n_lista, alvo))
        page.locator('.ea-map-panel').screenshot(path=str(CAPT / 'c05_sobrepostos_lista_filtro.png'))
        page.keyboard.press('Escape')
        page.wait_for_timeout(300)
        check('Esc fecha a lista de escolha primeiro (sem mexer no resto)', page.locator('.leaflet-popup').count() == 0)
    else:
        check('3 · Muitos sobrepostos: ponto denso encontrado para o teste', False, 'nenhum pixel com mais de 8 processos')

    # ================================================================ 4. processo → dossiê → Território (paginação) → mapa
    zerar(page)
    filtro_per = page.is_visible('#ea-filtros')
    if not filtro_per:
        page.click('#ea-filtros-btn')
    page.select_option('#ea-ano-ini', '2023')
    page.wait_for_timeout(400)
    page.click('#ea-filtros-btn')
    modo(page, 'processos')
    alvo = '861461/2015'
    i_cmoc = EMP[CMOC]['i']
    ordem = sorted([k for k, x in enumerate(R) if x[PC['empresa']] == i_cmoc], key=lambda k: (-R[k][PC['cfem_2022_2026']], -(R[k][PC['area_ha']] or 0), k))
    pos = [R[k][PC['processo']] for k in ordem].index(alvo)
    pag_esperada, n_pags = pos // 15 + 1, math.ceil(len(ordem) / 15)
    xy = ir_processo(page, alvo, 13)
    clicar(page, xy, 1200)
    antes = estado(page)
    centro0 = ev(page, f'(()=>{{const c={A}.mapa().getCenter();return [c.lat,c.lng]}})()')
    page.click('#ea-resumo [data-proc-dossie]')
    page.wait_for_timeout(1800)
    st = estado(page)
    linha = page.locator('#ea-corpo tr.ea-destaque')
    pag_txt = page.inner_text('#ea-corpo .ea-pag') if page.locator('#ea-corpo .ea-pag').count() else ''
    vis = ev(page, "(()=>{const r=document.querySelector('#ea-corpo tr.ea-destaque');if(!r)return false;const b=r.getBoundingClientRect();return b.top>=0&&b.bottom<=innerHeight})()")
    check('4 · "Ver processo no dossiê": Dossiê → Território da titular, sem nova aba do navegador', st['area'] == 'dossie' and st['sel'] == CMOC
          and page.get_attribute('#ea-tab-territorio', 'aria-selected') == 'true' and len(ctx.pages) == 1, st)
    check(f'4 · Território abre na página do processo ({pag_esperada} de {n_pags}), realça a linha certa e rola até ela',
          linha.count() == 1 and linha.get_attribute('data-linha-proc') == alvo and f'página {pag_esperada} de {n_pags}' in pag_txt and vis,
          (linha.count(), pag_txt.replace('\n', ' '), vis))
    page.screenshot(path=str(CAPT / 'c06_dossie_territorio_processo.png'))
    check('4 · Atalho discreto "Voltar ao mapa (processo …)" no topo do dossiê', page.is_visible('#ea-volta-analise [data-volta-mapa]')
          and alvo in page.inner_text('#ea-volta-analise'))
    page.click('#ea-volta-analise [data-volta-mapa]')
    page.wait_for_timeout(1500)
    st = estado(page)
    centro1 = ev(page, f'(()=>{{const c={A}.mapa().getCenter();return [c.lat,c.lng]}})()')
    check('4 · Voltar ao mapa: mesmo processo em foco, mesmo modo, mesmo zoom e centro, filtros intactos',
          st['area'] == 'explorar' and st['proc'] == alvo and st['modo'] == 'processos' and st['zoom'] == antes['zoom']
          and abs(centro1[0] - centro0[0]) < 1e-4 and abs(centro1[1] - centro0[1]) < 1e-4 and page.input_value('#ea-ano-ini') == '2023',
          (st, centro0, centro1))
    page.go_forward()
    page.wait_for_timeout(1200)
    check('14 · Avançar volta ao dossiê com o atalho de volta', estado(page)['area'] == 'dossie' and page.is_visible('#ea-volta-analise [data-volta-mapa]'))
    page.go_back()
    page.wait_for_timeout(1200)
    check('14 · Voltar de novo: o mapa com o mesmo processo (nenhum selecionado obsoleto)', estado(page)['proc'] == alvo and estado(page)['area'] == 'explorar')
    # Ver empresa titular → Perfil, sem trocar o processo
    page.click('#ea-resumo [data-proc-titular]')
    page.wait_for_timeout(1200)
    st = estado(page)
    check('4 · "Ver empresa titular": Perfil do dossiê da titular, sem trocar o processo pesquisado', st['area'] == 'dossie' and st['sel'] == CMOC
          and page.get_attribute('#ea-tab-perfil', 'aria-selected') == 'true' and st['proc'] == alvo, st)
    page.go_back()
    page.wait_for_timeout(1200)
    # processo de pessoa física (busca): mostra o processo, sem nome, sem dossiê impossível
    zerar(page)
    pf = next(x[PC['processo']] for x in R if x[PC['empresa']] == -2 and x[PC['lat']] is not None)
    page.fill('#ea-busca', pf)
    page.wait_for_timeout(500)
    page.keyboard.press('Enter')
    page.wait_for_timeout(1800)
    card = page.inner_text('#ea-resumo') if page.is_visible('#ea-resumo') else ''
    check('13 · Processo de pessoa física: cartão do processo, sem nome, sem botão de dossiê nem de titular; ANM disponível',
          estado(page)['proc'] == pf and 'Pessoa física' in card and page.locator('#ea-resumo [data-proc-dossie], #ea-resumo [data-proc-titular]').count() == 0
          and page.locator('#ea-resumo .ea-card-anm a').count() == 1 and estado(page)['sel'] is None, card.replace('\n', ' | ')[:200])
    page.locator('.ea-map-panel').screenshot(path=str(CAPT / 'c07_processo_pessoa_fisica.png'))

    # ================================================================ 8 e 10. município: busca, ferramenta do mapa, dossiê → o mesmo código IBGE
    zerar(page)
    modo(page, 'empresas')
    ev(page, f"{A}.selecionarCnpj('{CMOC}')")
    page.wait_for_timeout(1200)
    rot = buscar(page, 'Catalão', 'Município')
    st = estado(page)
    cont = ev(page, f'{A}.contorno()')
    enq = ev(page, f"(()=>{{const b={A}.mapa().getBounds();return [b.getSouth(),b.getWest(),b.getNorth(),b.getEast()]}})()")
    anel = [p for r_ in next(m for m in GEO['municipalities'] if str(m['code']) == CATALAO)['rings'] for p in r_]
    cabe = enq[0] <= min(p[0] for p in anel) and enq[2] >= max(p[0] for p in anel) and enq[1] <= min(p[1] for p in anel) and enq[3] >= max(p[1] for p in anel)
    check('8 · Busca: sugestão "Catalão · GO" marcada como Município seleciona pelo IBGE, sem ligar a ferramenta',
          'Catalão · GO' in rot and 'município' in rot.lower() and st['mun'] and st['mun']['ibge'] == CATALAO, (rot, st['mun']))
    check('8 · Contorno real destacado e município inteiro enquadrado, sem zoom excessivo', cont and cont['ibge'] == CATALAO and cabe and st['zoom'] <= 11,
          (cont, enq, st['zoom']))
    check('8 · Etiqueta removível "Catalão · GO ×" no alto do mapa e cartão do território', page.is_visible('#ea-mun-etq')
          and 'Catalão · GO' in page.inner_text('#ea-mun-etq') and st['foco'] == 'municipio')
    n_emp, n_proc, cf = universo_mun(CATALAO)
    tot = ev(page, f'{A}.totais()')
    ks_cmoc, dentro_cmoc = procs_da_empresa_no_mun(CMOC, CATALAO)
    check('10 · Recorte pelo vínculo processo–município (IBGE): empresas, processos e CFEM do município batem com o pacote',
          tot['empresas'] == n_emp and tot['processos'] == n_proc and abs(tot['cfem'] - cf) < 1, (tot, n_emp, n_proc, round(cf, 2)))
    check('10 · Não é pela posição do centroide: processos da CMOC com centroide fora de Catalão continuam no recorte',
          len(ks_cmoc) > len(dentro_cmoc) and str(len(ks_cmoc)) in page.inner_text('#ea-resumo'), (len(ks_cmoc), len(dentro_cmoc)))
    card = page.inner_text('#ea-resumo')
    check('12 · Município + empresa: um cartão só, do território, com a empresa de interesse numa linha', page.locator('#empresas-view .ea-card:visible').count() == 1
          and 'Catalão · GO' in card and 'IBGE 5205109' in card and 'Empresa de interesse' in card and 'CMOC' in card, card.replace('\n', ' | ')[:300])
    check('10 · Lista e indicadores no recorte (etiqueta do filtro, lista menor)', 'Catalão · GO' in page.inner_text('#ea-context')
          and page.locator('#ea-lista .ea-item').count() <= n_emp)
    page.locator('.ea-map-panel').screenshot(path=str(CAPT / 'c08_municipio_contorno_recorte.png'))
    page.screenshot(path=str(CAPT / 'c08b_municipio_pagina.png'))
    # 11. Catalão → Ouvidor num clique; fora dos municípios tira; × tira só o município
    xy = ev(page, f"{A}.telaMunicipio('{OUVIDOR}')")
    if xy:
        clicar(page, xy, 1200)
    st = estado(page)
    check('11 · Com município escolhido, um clique no território de Ouvidor troca direto (empresa mantida)', bool(xy) and st['mun'] and st['mun']['ibge'] == OUVIDOR
          and st['sel'] == CMOC, (xy, st['mun']))
    page.click('#ea-filtros-btn')
    page.select_option('#ea-ano-fim', '2026')
    page.wait_for_timeout(400)
    page.click('#ea-filtros-btn')
    es_ano = page.input_value('#es-ano')
    page.click('#ea-mun-etq .ea-mun-etq-x')
    page.wait_for_timeout(700)
    st = estado(page)
    check('11 · × da etiqueta tira só o município: a empresa, o período e os filtros das análises ficam', st['mun'] is None and st['sel'] == CMOC
          and page.input_value('#ea-ano-fim') == '2026' and page.input_value('#es-ano') == es_ano and page.is_hidden('#ea-mun-etq'), st)
    page.click('#ea-context [data-limpa="ea-periodo"]')
    page.wait_for_timeout(300)
    buscar(page, 'Catalão', 'Município')
    ver(page, -18.0, -47.9, 7.5)
    fora = ev(page, f'{A}.telaMunicipio(null)')
    if fora:
        clicar(page, fora, 900)
    check('11 · Clique numa área fora dos municípios de Goiás remove o recorte (empresa fica)', bool(fora) and estado(page)['mun'] is None
          and estado(page)['sel'] == CMOC, fora)
    # ferramenta do mapa (Camadas)
    page.click('#ea-camadas summary')
    check('P1.1 · Camadas: a opção de município vem ligada (clique direto, sem configurar nada)', page.is_checked('#ea-sel-mun'))
    page.keyboard.press('Escape')
    page.wait_for_timeout(300)
    check('Esc fecha o menu Camadas antes de qualquer outra coisa', not ev(page, "document.getElementById('ea-camadas').open") and estado(page)['sel'] == CMOC)
    ver(page, -18.1, -47.9, 9)
    xy = ev(page, f"{A}.telaMunicipio('{CATALAO}')")
    mover(page, xy)
    dica = page.inner_text('#ea-map .leaflet-tooltip.ea-tip') if page.locator('#ea-map .leaflet-tooltip.ea-tip').count() else ''
    check('9 · Ferramenta ligada: o fundo livre mostra o município sob o cursor e a mão', 'Catalão · GO' in dica
          and ev(page, f'{A}.mapa().getContainer().style.cursor') == 'pointer', dica)
    clicar(page, xy, 1200)
    check('8 · Ferramenta do mapa (Camadas): clique no fundo seleciona o mesmo município pelo IBGE', (estado(page)['mun'] or {}).get('ibge') == CATALAO)
    # a empresa estava selecionada: reabre o cartão dela pela linha de interesse e desmarca pelo ×; depois clica no ponto dela
    page.click('#ea-resumo [data-interesse]')
    page.wait_for_timeout(300)
    page.click('#ea-resumo .ea-card-x')
    page.wait_for_timeout(400)
    check('12 · Desmarcar a empresa não tira o município (o cartão volta ao território)', estado(page)['sel'] is None
          and (estado(page)['mun'] or {}).get('ibge') == CATALAO and estado(page)['foco'] == 'municipio', estado(page))
    xy_emp = ev(page, f"{A}.telaEmpresa('{CMOC}')")
    clicar(page, xy_emp, 900)
    if page.locator('.leaflet-popup .ea-pop [data-i]').count():
        page.locator('.leaflet-popup .ea-pop [data-i]', has_text='CMOC').first.click()
        page.wait_for_timeout(600)
    st = estado(page)
    check('9 · Ferramenta ligada: marcador ativo do modo tem prioridade sobre o fundo municipal (e o recorte fica)',
          st['foco'] == 'empresa' and (st['mun'] or {}).get('ibge') == CATALAO, st)
    page.click('#ea-camadas summary')
    page.uncheck('#ea-sel-mun')
    page.click('#ea-camadas summary')
    page.click('#ea-mun-etq .ea-mun-etq-x')
    page.wait_for_timeout(500)
    vazio = ev(page, f'{A}.pontoVazio()')
    clicar(page, vazio, 700)
    check('9 · Opção de município desligada (Camadas) e sem município: o fundo volta ao normal (clique no vazio desmarca a empresa)',
          estado(page)['mun'] is None and estado(page)['sel'] is None, estado(page))
    # multipartes: Mineiros (três anéis), clique numa parte separada
    rot = buscar(page, 'Mineiros', 'Município')
    cont = ev(page, f'{A}.contorno()')
    check('13 · Multipartes: Mineiros com o contorno de todas as partes', cont and cont['ibge'] == MINEIROS and cont['aneis'] == 3, cont)
    page.click('#ea-mun-etq .ea-mun-etq-x')
    page.click('#ea-camadas summary')
    page.check('#ea-sel-mun')
    page.click('#ea-camadas summary')
    ver(page, -18.53, -52.9, 10)
    xy = ev(page, f"{A}.telaMunicipio('{MINEIROS}',0)")
    if xy:
        clicar(page, xy, 1000)
    check('13 · Multipartes: clicar na parte separada (ao sul) seleciona Mineiros', bool(xy) and (estado(page)['mun'] or {}).get('ibge') == MINEIROS, xy)
    portel = next(str(m[0]) for m in MUN if m[1] == 'Portelândia')
    ver(page, -17.35, -52.68, 10)
    xy = ev(page, f"{A}.telaMunicipio('{portel}')")
    if xy:
        clicar(page, xy, 1000)
    check('13 · Buraco: o enclave de Portelândia dentro de Mineiros seleciona Portelândia, não Mineiros', bool(xy)
          and (estado(page)['mun'] or {}).get('ibge') == portel, (xy, estado(page)['mun']))
    page.click('#ea-camadas summary')
    page.uncheck('#ea-sel-mun')
    page.click('#ea-camadas summary')
    # município sem dados (sem empresa nem CFEM): estado vazio honesto
    rot = buscar(page, 'Itaguari', 'Município')
    card = page.inner_text('#ea-resumo') if page.is_visible('#ea-resumo') else ''
    check('13 · Município sem empresa nem CFEM: cartão com zero, "sem CFEM", só a contagem de pessoa física/sem titular, lista vazia',
          (estado(page)['mun'] or {}).get('ibge') == ITAGUARI and 'sem CFEM' in card and page.locator('#ea-lista .ea-item').count() == 0,
          card.replace('\n', ' | ')[:240])
    page.click('#ea-mun-etq .ea-mun-etq-x')
    page.wait_for_timeout(400)
    # processo em dois municípios: entra no recorte de cada um
    multi = next(x for x in R if x[PC['processo']] == '801244/1968')
    nomes = [MUN[m][1] for m in multi[PC['municipios']]]
    modo(page, 'processos')
    xy = ir_processo(page, '801244/1968', 13)
    clicar(page, xy, 1200)
    if page.locator('.leaflet-popup .ea-pop [data-k]').count():
        page.locator('.leaflet-popup .ea-pop [data-k]', has_text='801244/1968').first.click()
        page.wait_for_timeout(700)
    card = page.inner_text('#ea-resumo')
    check('13 · Processo em mais de um município: o cartão lista todos (Catalão, Ouvidor)', all(n in card for n in nomes) and 'Municípios vinculados · 2' in card,
          card.replace('\n', ' | ')[:240])
    modo(page, 'empresas')
    check('14 · Trocar de modo limpa o processo em foco (incompatível) sem perder a empresa de interesse', estado(page)['proc'] is None
          and estado(page)['foco'] != 'processo')

    # ================================================================ 15. exportação com o recorte municipal
    zerar(page)
    buscar(page, 'Catalão', 'Município')
    arq = baixar(page, '#ea-exp-csv', BAIX)
    txt = arq.read_bytes().decode('utf-8-sig')
    linhas = list(csv.DictReader(io.StringIO(txt, newline=''), delimiter=';'))
    tot = ev(page, f'{A}.totais()')
    check('15 · CSV do recorte: código IBGE do município em toda linha e processos do recorte = indicador da tela',
          linhas and all(l['filtro_municipio_ibge'] == CATALAO and l['filtro_municipio'] == 'Catalão' for l in linhas)
          and sum(int(l['processos_no_recorte']) for l in linhas) == tot['processos'] and len(linhas) == tot['empresas'], (len(linhas), tot))
    arq = baixar(page, '#ea-exp-xlsx', BAIX)
    z = zipfile.ZipFile(arq)
    xml = ' '.join(z.read(n).decode('utf-8') for n in z.namelist() if n.startswith('xl/') and n.endswith('.xml'))
    check('15 · Planilha: a área do recorte avisa que é do processo inteiro e os metadados explicam o recorte municipal',
          'não é a área dentro do município' in xml and 'aviso_municipio' in xml and 'filtro_municipio_ibge' in xml)
    page.click('#ea-mun-etq .ea-mun-etq-x')

    # ================================================================ 5, 6 e 7. dossiê: link discreto, prévia com os direitos da empresa, navegação
    ev(page, f"{A}.selecionarCnpj('{CMOC}')")
    page.wait_for_timeout(800)
    page.click('#ea-nav-dossie')
    page.wait_for_timeout(900)
    page.click('#ea-tab-perfil')
    page.wait_for_timeout(500)
    page.evaluate('scrollTo(0,0)')
    link = page.locator('#ea-ficha-fatos .ea-mun-link', has_text='Catalão').first
    check('5 · Cabeçalho e Perfil: municípios como links discretos de texto (código IBGE), sem pílulas',
          link.get_attribute('data-mun-ibge') == CATALAO
          and len(set(page.locator('#ea-corpo .ea-muns-links .ea-mun-link').evaluate_all('xs=>xs.map(x=>x.dataset.munIbge)'))) == len(EMP[CMOC]['mun'])
          and page.locator('#ea-corpo .ea-muns .ea-chip, #ea-corpo [data-mun-ibge].ea-chip').count() == 0)
    antes = estado(page)
    link.hover()
    page.wait_for_timeout(300)
    cedo = ev(page, f'{A}.previa()')
    page.wait_for_timeout(700)
    pv = ev(page, f'{A}.previa()')
    depois = estado(page)
    check('5 · Prévia só depois de ~650 ms com o mouse parado (nada aos 300 ms)', cedo is None and pv is not None, (cedo, bool(pv)))
    check('5 · Passar o mouse não navega nem filtra (área, seleção, município, URL e histórico iguais)',
          {k: antes[k] for k in ('area', 'sel', 'mun', 'url', 'hist', 'zoom')} == {k: depois[k] for k in ('area', 'sel', 'mun', 'url', 'hist', 'zoom')}, (antes, depois))
    pbox, lbox = page.locator('#ea-previa').bounding_box(), link.bounding_box()
    sobre = not (pbox['y'] >= lbox['y'] + lbox['height'] or pbox['y'] + pbox['height'] <= lbox['y'] or pbox['x'] >= lbox['x'] + lbox['width'] or pbox['x'] + pbox['width'] <= lbox['x'])
    check('5 · Prévia com contorno (SVG, sem segundo mapa Leaflet), dentro da tela, sem cobrir o link',
          pv['geo'] == '1' and page.locator('#ea-previa svg path.ea-pv-mun').count() == 1 and page.locator('#ea-previa .leaflet-container').count() == 0
          and page.locator('#empresas-view .leaflet-container').count() == 1 and not sobre and pbox['x'] >= 0 and pbox['y'] >= 0
          and pbox['x'] + pbox['width'] <= 1440 and pbox['y'] + pbox['height'] <= 900, (pbox, lbox))
    check('6 · Prévia: só os direitos da empresa vinculados ao município (contagem do pacote) e pontos só onde o centroide cai dentro',
          int(pv['n']) == len(ks_cmoc) and int(pv['pontos']) == len(dentro_cmoc) and int(pv['fora']) == len(ks_cmoc) - len(dentro_cmoc),
          (pv, len(ks_cmoc), len(dentro_cmoc)))
    check('6 · Prévia explica a diferença (sem ponto inventado) e agrupa os sobrepostos com contador',
          'sem ponto aqui' in pv['texto'] and int(pv['grupos']) <= int(pv['pontos']) and page.locator('#ea-previa circle').count() == int(pv['grupos'])
          and 'não uma mina' in pv['texto'] and 'Direitos minerários da empresa neste município' in pv['texto'], pv['texto'][:300])
    page.screenshot(path=str(CAPT / 'c09_previa_municipio_dossie.png'))
    page.locator('#ea-previa').screenshot(path=str(CAPT / 'c09b_previa_recorte.png'))
    page.mouse.move(700, 120)
    page.wait_for_timeout(400)
    check('5 · Sair do link fecha a prévia', ev(page, f'{A}.previa()') is None)
    # Perfil: o mesmo comportamento
    lp = page.locator('#ea-corpo .ea-muns-links .ea-mun-link', has_text='Ouvidor').first
    lp.scroll_into_view_if_needed()
    lp.hover()
    page.wait_for_timeout(1000)
    pv2 = ev(page, f'{A}.previa()')
    check('5 · Perfil: prévia de Ouvidor com os direitos da empresa ali', pv2 is not None and pv2['ibge'] == OUVIDOR
          and int(pv2['n']) == len(procs_da_empresa_no_mun(CMOC, OUVIDOR)[0]), pv2)
    page.mouse.move(700, 60)
    page.wait_for_timeout(300)
    # teclado: Tab até o link, prévia pelo foco; Esc fecha; Enter navega
    page.evaluate('scrollTo(0,0)')
    page.focus('#ea-ficha-exp')   # último botão do cabeçalho; o próximo Tab é o primeiro município
    for _ in range(4):
        page.keyboard.press('Tab')
        if ev(page, "document.activeElement&&document.activeElement.classList.contains('ea-mun-link')"):
            break
    foco_link = ev(page, "document.activeElement&&document.activeElement.classList.contains('ea-mun-link')?document.activeElement.dataset.munIbge:null")
    page.wait_for_timeout(1000)
    pv3 = ev(page, f'{A}.previa()')
    page.keyboard.press('Escape')
    page.wait_for_timeout(200)
    check('7 · Teclado: foco no link abre a prévia; Esc fecha só a prévia', foco_link is not None and pv3 is not None and ev(page, f'{A}.previa()') is None
          and estado(page)['sel'] == CMOC and estado(page)['area'] == 'dossie', (foco_link, bool(pv3)))
    page.evaluate('scrollTo(0,0)')
    link = page.locator('#ea-ficha-fatos .ea-mun-link', has_text='Catalão').first
    link.click()
    page.wait_for_timeout(1800)
    st = estado(page)
    card = page.inner_text('#ea-resumo') if page.is_visible('#ea-resumo') else ''
    check('5 e 7 · Clique no município do dossiê: Explorar com Catalão destacado e recortado, empresa de interesse mantida (não como filtro)',
          st['area'] == 'explorar' and (st['mun'] or {}).get('ibge') == CATALAO and st['sel'] == CMOC and st['foco'] == 'municipio'
          and ev(page, f'{A}.contorno()')['ibge'] == CATALAO and ev(page, f'{A}.totais()')['empresas'] == universo_mun(CATALAO)[0], st)
    check('7 · Cartão prioriza o território, com a empresa de interesse compacta e "Voltar ao dossiê"', 'Catalão · GO' in card and 'Empresa de interesse' in card
          and page.is_visible('#ea-resumo [data-volta-dossie]'), card.replace('\n', ' | ')[:240])
    page.locator('.ea-map-panel').screenshot(path=str(CAPT / 'c10_dossie_para_explorar_municipio.png'))
    page.click('#ea-resumo [data-interesse]')
    page.wait_for_timeout(500)
    check('12 · A empresa de interesse reabre por clique (cartão da empresa), o município continua como recorte',
          estado(page)['foco'] == 'empresa' and (estado(page)['mun'] or {}).get('ibge') == CATALAO and page.is_visible('#ea-mun-etq'))
    page.click('#ea-mun-etq .ea-mun-etq-nome')
    page.wait_for_timeout(400)
    page.click('#ea-resumo [data-volta-dossie]')
    page.wait_for_timeout(1500)
    st = estado(page)
    check('7 · "Voltar ao dossiê": a ficha da mesma empresa, na mesma seção (Perfil)', st['area'] == 'dossie' and st['sel'] == CMOC
          and page.get_attribute('#ea-tab-perfil', 'aria-selected') == 'true', st)
    check('Console e rede sem erros (mesa, PT)', not erros_relevantes(ruido), erros_relevantes(ruido)[:6])
    ctx.close()

    # ================================================================ 16. EN, tablet e celular
    ctx = nav.new_context(viewport={'width': 1440, 'height': 900}, locale='en-US')
    page, ruido = entrar(ctx, 'en')
    page.locator('#ea-map').scroll_into_view_if_needed()
    modo(page, 'processos')
    xy = ir_processo(page, '803343/1973', 13)
    clicar(page, xy, 1300)
    card = page.inner_text('#ea-resumo')
    check('16 · EN: process card in English (ANM claim, Claim area, Holder, Check at ANM)', 'ANM CLAIM' in card.upper() and 'Claim area' in card
          and 'Holder' in card and 'Check at ANM' in card, card.replace('\n', ' | ')[:200])
    rot = buscar(page, 'Catalão', 'Municip')
    card = page.inner_text('#ea-resumo')
    check('16 · EN: municipality card and label in English', 'MUNICIPALITY' in card.upper() and 'Companies' in card and 'CFEM in the municipality' in card
          and 'Catalão · GO' in page.inner_text('#ea-mun-etq'),
          card.replace('\n', ' | ')[:200])
    page.locator('.ea-map-panel').screenshot(path=str(CAPT / 'c11_en_municipio.png'))
    check('16 · EN: console sem erros', not erros_relevantes(ruido), erros_relevantes(ruido)[:6])
    ctx.close()
    for nome, vp, toque in (('tablet', {'width': 820, 'height': 1180}, True), ('celular', {'width': 390, 'height': 844}, True)):
        ctx = nav.new_context(viewport=vp, is_mobile=nome == 'celular', has_touch=toque, device_scale_factor=2, locale='pt-BR')
        page, ruido = entrar(ctx)
        page.locator('#ea-map').scroll_into_view_if_needed()
        rot = buscar(page, 'Catalão', 'Município')
        page.locator('#ea-map').scroll_into_view_if_needed()
        page.wait_for_timeout(600)
        cb, tb = page.locator('#ea-resumo').bounding_box(), page.locator('#empresas-view .ea-map-tools').bounding_box()
        zb = page.locator('#ea-map .leaflet-control-zoom').bounding_box()
        cobre = lambda a, b: not (a['y'] >= b['y'] + b['height'] or a['y'] + a['height'] <= b['y'] or a['x'] >= b['x'] + b['width'] or a['x'] + a['width'] <= b['x'])
        check(f'16 · {nome}: cartão do município não cobre os modos, a etiqueta nem a busca', cb and tb and not cobre(cb, tb) and page.is_visible('#ea-mun-etq'),
              (cb, tb))
        if nome == 'celular':
            check('16 · celular: cartão compacto (até ~60% da altura do mapa)', cb['height'] <= 0.62 * page.locator('#ea-map').bounding_box()['height'], cb)
        page.locator('.ea-map-panel').screenshot(path=str(CAPT / f'c12_{nome}_municipio.png'))
        # toque: processo no modo Processos
        page.click('#ea-mun-etq .ea-mun-etq-x')
        modo(page, 'processos')
        xy = ir_processo(page, '803343/1973', 13)
        caixa = page.locator('#ea-map').bounding_box()
        page.touchscreen.tap(caixa['x'] + xy[0], caixa['y'] + xy[1])
        page.wait_for_timeout(1300)
        check(f'16 · {nome}: toque no ponto seleciona o processo exato', estado(page)['proc'] == '803343/1973', estado(page))
        page.locator('.ea-map-panel').screenshot(path=str(CAPT / f'c13_{nome}_processo.png'))
        # dossiê: toque no município navega direto, sem prévia
        page.locator('#ea-resumo [data-proc-titular]').tap()
        page.wait_for_timeout(1200)
        lk = page.locator('#ea-ficha-fatos .ea-mun-link', has_text='Catalão').first
        lk.scroll_into_view_if_needed()
        bx = lk.bounding_box()
        lk.tap()
        page.wait_for_timeout(1500)
        st = estado(page)
        check(f'7 · {nome}: tocar no município do dossiê navega na hora (sem prévia), com área de toque confortável',
              st['area'] == 'explorar' and (st['mun'] or {}).get('ibge') == CATALAO and ev(page, f'{A}.previa()') is None and bx['height'] >= 24 if nome == 'celular' else
              st['area'] == 'explorar' and (st['mun'] or {}).get('ibge') == CATALAO and ev(page, f'{A}.previa()') is None, (st, bx))
        w = ev(page, '[document.documentElement.scrollWidth, innerWidth]')
        check(f'16 · {nome}: sem rolagem horizontal e console sem erros', w[0] <= w[1] + 1 and not erros_relevantes(ruido), (w, erros_relevantes(ruido)[:4]))
        ctx.close()
    nav.close()

falhas = [r for r in resultados if r['resultado'] != 'APROVADO']
Path(args.saida).parent.mkdir(parents=True, exist_ok=True)
Path(args.saida).write_text(json.dumps({'executado_em': time.strftime('%Y-%m-%d %H:%M:%S'), 'base': BASE, 'navegador': args.canal,
                                         'total': len(resultados), 'falhas': len(falhas), 'verificacoes': resultados},
                                        ensure_ascii=False, indent=1), encoding='utf-8')
print(f'\n{len(resultados) - len(falhas)}/{len(resultados)} verificações aprovadas')
sys.exit(1 if falhas else 0)
