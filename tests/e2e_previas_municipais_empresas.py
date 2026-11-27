"""Roteiro de navegador das prévias municipais do dossiê (aba Empresas), contra um servidor no ar.

    python tests/e2e_previas_municipais_empresas.py --base https://<servidor> --capturas DIR --saida ARQ [--canal chromium|chrome|msedge]

Contas só por variável de ambiente: ATLAS_E2E_USUARIO / ATLAS_E2E_SENHA (senha já trocada). Nenhuma conta nem senha no código.

Confere, para Maracá, CMOC e Nexa, nos três lugares do dossiê (cabeçalho, Perfil e coluna Municípios da tabela Território → Processos
ANM): cada nome é um link próprio; ~650 ms de mouse parado abrem a prévia (antes, não); a prévia tem o contorno real do município (SVG,
sem segundo mapa Leaflet), só os processos da empresa daquele dossiê, ponto só onde o centroide cai dentro do município e a ressalva
quando cai fora; não fecha sozinha; fecha ao redesenhar a tabela (filtro, paginação) e ao rolar a tabela; funciona em linhas novas
(outra página) e em células com vários municípios; o clique leva ao Explorar com o município escolhido e destacado e a empresa
preservada; no toque, o toque navega direto, sem prévia; pelo teclado, o foco abre a prévia; em inglês, a prévia vem em inglês.
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ap = argparse.ArgumentParser()
ap.add_argument('--base', required=True)
ap.add_argument('--canal', default='chromium')
ap.add_argument('--capturas', required=True, help='pasta das capturas, fora do repositório')
ap.add_argument('--saida', required=True, help='relatório JSON, fora do repositório')
args = ap.parse_args()
BASE = args.base.rstrip('/')
CAPT = Path(args.capturas)
CAPT.mkdir(parents=True, exist_ok=True)
U1, S1 = os.environ.get('ATLAS_E2E_USUARIO', ''), os.environ.get('ATLAS_E2E_SENHA', '')
if not U1 or not S1:
    sys.exit('Faltam credenciais: defina ATLAS_E2E_USUARIO/ATLAS_E2E_SENHA.')
A = 'window.EmpresasAtlas'
EMPRESAS = [('86902053', 'Maracá'), ('26108898', 'CMOC'), ('42416651', 'Nexa')]
resultados = []


def check(nome, cond, detalhe=''):
    resultados.append({'verificacao': nome, 'resultado': 'APROVADO' if cond else 'FALHOU', 'detalhe': str(detalhe)[:500]})
    print(('  OK   ' if cond else '  FALHA ') + nome + (f' — {detalhe}' if detalhe and not cond else ''), flush=True)
    return cond


def entrar(ctx):
    p = ctx.new_page()
    erros = []
    p.on('pageerror', lambda e: erros.append(('pageerror', str(e))))
    p.on('console', lambda m: m.type == 'error' and 'status of 401' not in m.text and erros.append(('console', m.text)))
    p.goto(BASE + '/login.html')
    p.fill('#username', U1)
    p.fill('#password', S1)
    p.click('#login-form button[type=submit]')
    p.wait_for_url('**/painel.html*', timeout=20000)
    p.wait_for_selector('#loading', state='hidden', timeout=20000)
    return p, erros


def abrir_dossie(p, cnpj, aba='perfil'):
    p.evaluate(f"location.hash='#empresas/{cnpj}'")
    p.wait_for_selector('#ea-ficha:not([hidden])', timeout=30000)
    p.wait_for_function(f"document.getElementById('ea-ficha').dataset.cnpj==='{cnpj}'", timeout=15000)
    p.click(f'#ea-abas [data-aba="{aba}"]')
    p.wait_for_timeout(250)


def previa(p):
    return p.evaluate(f'{A}.previa()')


def pairar(p, loc, esperar=None):
    """Mouse parado no centro do link; devolve (prévia aos ~300 ms, prévia depois de esperar)."""
    loc.scroll_into_view_if_needed()
    p.mouse.move(5, 5)
    p.wait_for_timeout(120)
    b = loc.bounding_box()
    p.mouse.move(b['x'] + b['width'] / 2, b['y'] + b['height'] / 2)
    t0 = time.time()
    p.wait_for_timeout(300)
    cedo = previa(p)
    p.wait_for_timeout(esperar or 600)
    return cedo, previa(p), time.time() - t0


def capturar(p, loc, nome):
    caixa = loc.bounding_box()
    pv = p.locator('#ea-previa').bounding_box() if p.is_visible('#ea-previa') else None
    xs = [caixa['x'], caixa['x'] + caixa['width']] + ([pv['x'], pv['x'] + pv['width']] if pv else [])
    ys = [caixa['y'], caixa['y'] + caixa['height']] + ([pv['y'], pv['y'] + pv['height']] if pv else [])
    vw, vh = p.viewport_size['width'], p.viewport_size['height']
    x0, y0 = max(0, min(xs) - 40), max(0, min(ys) - 30)
    x1, y1 = min(vw, max(xs) + 40), min(vh, max(ys) + 30)
    p.screenshot(path=str(CAPT / f'{nome}.png'), clip={'x': x0, 'y': y0, 'width': x1 - x0, 'height': y1 - y0})


def conferir_previa(rotulo, cnpj, ibge_link, pv, tela):
    ok = check(f'{rotulo}: prévia abre depois de ~650 ms parado', bool(pv), pv)
    if not ok:
        return
    check(f'{rotulo}: prévia é do município do link', pv.get('ibge') == ibge_link, (pv.get('ibge'), ibge_link))
    n, pts, fora = int(pv['n']), int(pv['pontos']), int(pv['fora'])
    check(f'{rotulo}: pontos só onde o centroide cai no município (pontos + fora ≤ processos)', pts + fora <= n, (pts, fora, n))
    if fora:
        check(f'{rotulo}: ressalva quando o centroide fica fora do município', 'sem ponto aqui' in pv['texto'] or 'without a dot' in pv['texto'], pv['texto'])
    if pv.get('geo') == '1':
        check(f'{rotulo}: contorno geográfico real (SVG), sem segundo mapa Leaflet',
              tela['svg'] and tela['leaflet_na_aba'] == 1 and tela['leaflet_na_previa'] == 0, tela)
    check(f'{rotulo}: prévia só com processos da empresa do dossiê', pv.get('n') == str(tela['esperados']), (pv.get('n'), tela['esperados']))


def estado_tela(p, cnpj, ibge):
    return p.evaluate(f"""(()=>{{const pv=document.getElementById('ea-previa');
      return {{svg:!!(pv&&pv.querySelector('svg path.ea-pv-mun')),leaflet_na_aba:document.querySelectorAll('#empresas-view .leaflet-container').length,
        leaflet_na_previa:pv?pv.querySelectorAll('.leaflet-container').length:0,esperados:{A}.processosDaEmpresaNoMunicipio?{A}.processosDaEmpresaNoMunicipio('{cnpj}','{ibge}'):null}}}})()""")


with sync_playwright() as pw:
    nav = pw.chromium.launch(headless=True, **({} if args.canal in ('', 'chromium') else {'channel': args.canal}))
    ctx = nav.new_context(viewport={'width': 1440, 'height': 900}, locale='pt-BR')
    page, erros = entrar(ctx)
    page.click('[data-view="empresas"]')
    page.mouse.move(900, 450)   # a barra lateral só se recolhe quando o mouse sai dela
    page.wait_for_timeout(400)
    page.wait_for_selector('#ea-area-explorar:not([hidden]), #ea-area-dossie:not([hidden])', timeout=30000)
    page.wait_for_function(f'!!{A}&&{A}.temEmpresa&&{A}.temEmpresa("26108898")', timeout=30000)
    # contagem independente dos processos da empresa em cada município, do mesmo pacote que a página recebe (/api/empresas/atlas)
    page.evaluate("""async()=>{const r=await fetch('/api/empresas/atlas');const d=await r.json();const C=d.processos.cols,ie=C.indexOf('empresa'),im=C.indexOf('municipios');
      const cnpj=new Map(d.empresas.map(e=>[e.i,e.cnpj])),ibge=d.dims.mun.map(m=>String(m[0]));
      window.__contagem=(c,g)=>d.processos.rows.filter(r=>cnpj.get(r[ie])===c&&r[im].some(k=>ibge[k]===g)).length;
      window.EmpresasAtlas.processosDaEmpresaNoMunicipio=window.__contagem}""")

    for cnpj, nome in EMPRESAS:
        print(f'== {nome} ({cnpj})', flush=True)
        # ------------------------------------------------ 1. cabeçalho do dossiê
        abrir_dossie(page, cnpj, 'perfil')
        sumario = page.locator('#ea-ficha-fatos details.ea-terr-mais summary')
        if sumario.count():
            sumario.first.click()
            page.wait_for_timeout(200)
        links = page.locator('#ea-ficha-fatos .ea-mun-link')
        n_links = links.count()
        ibges = [links.nth(i).get_attribute('data-mun-ibge') for i in range(n_links)]
        # cada nome é um link próprio: um código IBGE e um só nome por link (a operação documentada aparece no topo e de novo no grupo
        # "Operação documentada" do "Ver os N municípios"; um município com operação também tem direitos vigentes — não é duplicidade)
        textos = page.eval_on_selector_all('#ea-ficha-fatos .ea-mun-link', "xs=>xs.map(x=>x.firstChild?x.firstChild.textContent.trim():'')")
        check(f'{nome} · cabeçalho: cada município é um link próprio (um código IBGE e um nome por link)',
              n_links > 0 and all(i and i.isdigit() and len(i) == 7 for i in ibges) and all(t and ',' not in t for t in textos),
              (n_links, len(set(ibges)), [t for t in textos if not t or ',' in t][:3]))
        alvo = links.first
        cedo, pv, _ = pairar(page, alvo)
        check(f'{nome} · cabeçalho: nada antes de ~650 ms', cedo is None, cedo)
        conferir_previa(f'{nome} · cabeçalho', cnpj, ibges[0], pv, estado_tela(page, cnpj, ibges[0]))
        capturar(page, alvo, f'{cnpj}_1_cabecalho')
        page.wait_for_timeout(1500)
        check(f'{nome} · cabeçalho: prévia não fecha sozinha com o mouse parado', previa(page) is not None)
        # todos os municípios do cabeçalho (vínculo por origem): procura um com centroide fora, para conferir a ressalva
        foras = 0
        for i in range(min(n_links, 40)):
            _, pv_i, _ = pairar(page, links.nth(i), 520)
            if pv_i and int(pv_i['fora']) > 0:
                foras += 1
                if foras == 1:
                    conferir_previa(f'{nome} · cabeçalho (centroide fora)', cnpj, ibges[i], pv_i, estado_tela(page, cnpj, ibges[i]))
                    capturar(page, links.nth(i), f'{cnpj}_1b_cabecalho_centroide_fora')
            elif pv_i:
                if int(pv_i['pontos']) + int(pv_i['fora']) > int(pv_i['n']):
                    check(f'{nome} · cabeçalho: {ibges[i]} pontos coerentes', False, pv_i)
        resultados.append({'verificacao': f'{nome} · cabeçalho: municípios percorridos', 'resultado': 'INFO', 'detalhe': f'{min(n_links, 40)} prévias; {foras} com centroide fora'})
        page.mouse.move(5, 5)

        # ------------------------------------------------ 2. Perfil
        links = page.locator('#ea-corpo .ea-mun-link')
        n_links = links.count()
        check(f'{nome} · Perfil: municípios clicáveis', n_links > 0, n_links)
        if n_links:
            alvo = links.nth(min(1, n_links - 1))
            ib = alvo.get_attribute('data-mun-ibge')
            cedo, pv, _ = pairar(page, alvo)
            check(f'{nome} · Perfil: nada antes de ~650 ms', cedo is None, cedo)
            conferir_previa(f'{nome} · Perfil', cnpj, ib, pv, estado_tela(page, cnpj, ib))
            capturar(page, alvo, f'{cnpj}_2_perfil')
        page.mouse.move(5, 5)

        # ------------------------------------------------ 3. Território → Processos ANM, coluna Municípios
        page.click('#ea-abas [data-aba="territorio"]')
        page.wait_for_selector('#ea-terr-tab .ea-mun-link', timeout=15000)
        celulas = page.locator('#ea-terr-tab tbody tr td:nth-child(5)')
        com_varios = None
        for i in range(celulas.count()):
            if celulas.nth(i).locator('.ea-mun-link').count() >= 2:
                com_varios = celulas.nth(i)
                break
        cls = page.eval_on_selector_all('#ea-terr-tab .ea-mun-link', 'xs=>xs.map(x=>x.className)')
        check(f'{nome} · tabela: nenhum link de município com ea-sem-previa', cls and not any('ea-sem-previa' in c for c in cls), set(cls))
        alvo = (com_varios.locator('.ea-mun-link').nth(1) if com_varios else page.locator('#ea-terr-tab .ea-mun-link').first)
        ib = alvo.get_attribute('data-mun-ibge')
        cedo, pv, _ = pairar(page, alvo)
        check(f'{nome} · tabela: nada antes de ~650 ms', cedo is None, cedo)
        conferir_previa(f'{nome} · tabela', cnpj, ib, pv, estado_tela(page, cnpj, ib))
        capturar(page, alvo, f'{cnpj}_3_tabela')
        page.wait_for_timeout(1500)
        check(f'{nome} · tabela: prévia não fecha sozinha com o mouse parado', previa(page) is not None)
        if com_varios:
            outro = com_varios.locator('.ea-mun-link').nth(0)
            ib2 = outro.get_attribute('data-mun-ibge')
            _, pv2, _ = pairar(page, outro)
            check(f'{nome} · tabela: célula com vários municípios, cada nome com a sua prévia', pv2 and pv2['ibge'] == ib2 and ib2 != ib, (ib, ib2, pv2 and pv2['ibge']))
        # redesenho da tabela com a prévia aberta (filtro): a prévia fecha junto, sem ficar órfã
        _, pv, _ = pairar(page, page.locator('#ea-terr-tab .ea-mun-link').first)
        page.evaluate("(()=>{const q=document.getElementById('ea-terr-q');q.value='';q.dispatchEvent(new Event('input',{bubbles:true}))})()")
        page.evaluate("(()=>{const q=document.getElementById('ea-terr-q');q.value=' ';q.dispatchEvent(new Event('input',{bubbles:true}))})()")
        page.wait_for_timeout(400)
        check(f'{nome} · tabela: redesenhar com a prévia aberta não deixa prévia órfã', pv is not None and previa(page) is None, (bool(pv), previa(page)))
        page.evaluate("(()=>{const q=document.getElementById('ea-terr-q');q.value='';q.dispatchEvent(new Event('input',{bubbles:true}))})()")
        page.wait_for_timeout(300)
        # paginação: linhas novas (renderizadas depois) também têm prévia
        prox = page.locator('#ea-terr-tab [data-ppag="1"]')
        if prox.count() and prox.is_enabled():
            prox.click()
            page.wait_for_timeout(400)
            alvo = page.locator('#ea-terr-tab .ea-mun-link').first
            ib = alvo.get_attribute('data-mun-ibge')
            _, pv, _ = pairar(page, alvo)
            conferir_previa(f'{nome} · tabela, página 2', cnpj, ib, pv, estado_tela(page, cnpj, ib))
        page.mouse.move(5, 5)

        # ------------------------------------------------ 4. clique: Explorar com o município, empresa preservada
        alvo = page.locator('#ea-terr-tab .ea-mun-link').first
        ib = alvo.get_attribute('data-mun-ibge')
        alvo.click()
        page.wait_for_timeout(900)
        mun = page.evaluate(f'{A}.municipio()')
        cont = page.evaluate(f'{A}.contorno()')
        check(f'{nome} · clique na tabela: Explorar com o município escolhido e destacado, empresa preservada',
              page.evaluate(f'{A}.area()') == 'explorar' and mun and mun['ibge'] == ib and page.evaluate(f'{A}.selecionada()') == cnpj and bool(cont),
              (page.evaluate(f'{A}.area()'), mun, page.evaluate(f'{A}.selecionada()'), bool(cont)))
        check(f'{nome} · clique: endereço leva o município (/mun/IBGE)', f'/mun/{ib}' in page.url, page.url)
        page.screenshot(path=str(CAPT / f'{cnpj}_4_explorar_municipio.png'))

    # ------------------------------------------------ 5. rolagem horizontal da tabela fecha a prévia (tela estreita)
    page.set_viewport_size({'width': 820, 'height': 1000})
    abrir_dossie(page, '86902053', 'territorio')
    page.wait_for_selector('#ea-terr-tab .ea-mun-link', timeout=15000)
    rola = page.evaluate("(()=>{const w=document.querySelector('#ea-terr-tab .table-wrap');return w?[w.scrollWidth,w.clientWidth]:null})()")
    _, pv, _ = pairar(page, page.locator('#ea-terr-tab .ea-mun-link').first)
    page.evaluate("(()=>{const w=document.querySelector('#ea-terr-tab .table-wrap');w.scrollLeft+=60;w.dispatchEvent(new Event('scroll'))})()")
    page.wait_for_timeout(300)
    check('Tabela em tela estreita (820 px): rolar a tabela fecha a prévia', pv is not None and previa(page) is None, (rola, bool(pv), previa(page)))
    page.mouse.move(5, 5)

    # ------------------------------------------------ 6. teclado: foco visível abre a prévia
    page.set_viewport_size({'width': 1440, 'height': 900})
    abrir_dossie(page, '26108898', 'perfil')
    page.locator('#ea-corpo .ea-mun-link').first.scroll_into_view_if_needed()
    page.focus('#ea-tab-perfil')
    achou = False
    for _ in range(80):
        page.keyboard.press('Tab')
        if page.evaluate("document.activeElement&&document.activeElement.classList.contains('ea-mun-link')"):
            achou = True
            break
    page.wait_for_timeout(900)
    check('Teclado: o foco num município abre a prévia', achou and previa(page) is not None, (achou, previa(page)))
    page.keyboard.press('Escape')
    page.wait_for_timeout(200)
    check('Teclado: Esc fecha a prévia', previa(page) is None)

    # ------------------------------------------------ 7. inglês
    page.evaluate("localStorage.setItem('minera-lang','en')")
    page.goto(BASE + '/painel.html?lang=en#empresas/26108898')
    page.wait_for_selector('#ea-ficha:not([hidden])', timeout=30000)
    page.click('#ea-abas [data-aba="territorio"]')
    page.wait_for_selector('#ea-terr-tab .ea-mun-link', timeout=15000)
    alvo = page.locator('#ea-terr-tab .ea-mun-link').first
    _, pv, _ = pairar(page, alvo)
    check('Inglês: a prévia vem em inglês', pv is not None and 'mining rights' in pv['texto'], pv and pv['texto'][:160])
    capturar(page, alvo, '26108898_5_tabela_en')
    page.evaluate("localStorage.setItem('minera-lang','pt')")
    erros_ok = [e for e in erros if 'tile.openstreetmap.org' not in e[1]]
    check('Console sem erros de JavaScript nas jornadas das prévias', not erros_ok, erros_ok[:5])
    ctx.close()

    # ------------------------------------------------ 8. toque (celular): toque navega direto, sem prévia
    ctx = nav.new_context(**pw.devices['iPhone 13'], locale='pt-BR')
    p2, erros2 = entrar(ctx)
    # link direto do dossiê: carregamento de verdade (do painel para o painel com outra âncora o navegador só troca a âncora)
    p2.goto('about:blank')
    p2.goto(BASE + '/painel.html#empresas/26108898')
    p2.wait_for_selector('#ea-ficha:not([hidden])', timeout=30000)
    p2.click('#ea-abas [data-aba="territorio"]')
    p2.wait_for_selector('#ea-terr-tab .ea-mun-link', timeout=15000)
    alvo = p2.locator('#ea-terr-tab .ea-mun-link').first
    alvo.scroll_into_view_if_needed()
    ib = alvo.get_attribute('data-mun-ibge')
    alvo.tap()
    p2.wait_for_timeout(1000)
    mun = p2.evaluate(f'{A}.municipio()')
    check('Celular: tocar no município navega direto ao Explorar (sem exigir hover), empresa preservada',
          p2.evaluate(f'{A}.area()') == 'explorar' and mun and mun['ibge'] == ib and p2.evaluate(f'{A}.selecionada()') == '26108898',
          (p2.evaluate(f'{A}.area()'), mun))
    check('Celular: nenhuma prévia aberta pelo toque', p2.evaluate(f'{A}.previa()') is None)
    larg = p2.evaluate('[document.documentElement.scrollWidth, innerWidth]')
    check('Celular: sem rolagem horizontal da página', larg[0] <= larg[1] + 1, larg)
    p2.screenshot(path=str(CAPT / '26108898_6_celular_toque_explorar.png'))
    ctx.close()
    nav.close()

falhas = [r for r in resultados if r['resultado'] == 'FALHOU']
Path(args.saida).parent.mkdir(parents=True, exist_ok=True)
Path(args.saida).write_text(json.dumps({'executado_em': time.strftime('%Y-%m-%d %H:%M:%S'), 'base': BASE, 'navegador': args.canal,
                                         'total': sum(r['resultado'] != 'INFO' for r in resultados), 'falhas': len(falhas),
                                         'verificacoes': resultados}, ensure_ascii=False, indent=1), encoding='utf-8')
print(f"\n{sum(r['resultado'] == 'APROVADO' for r in resultados)}/{sum(r['resultado'] != 'INFO' for r in resultados)} verificações aprovadas")
sys.exit(1 if falhas else 0)
