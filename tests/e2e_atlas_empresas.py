"""Roteiro de navegador do Atlas Empresarial, contra um servidor no ar (homologação ou produção).

    python tests/e2e_atlas_empresas.py --base https://<servidor> [--canal chromium|chrome|msedge] [--capturas DIR] [--saida ARQ]

Contas (duas, com a senha já trocada; a segunda pode ser de qualquer papel), só por variável de ambiente:
ATLAS_E2E_USUARIO / ATLAS_E2E_SENHA e ATLAS_E2E_USUARIO2 / ATLAS_E2E_SENHA2. Nenhuma conta nem senha fica no código. Não roda no CI (precisa do servidor no ar). --canal chromium usa o Chromium do Playwright
(`playwright install chromium`); msedge/chrome usam o navegador instalado. Cada verificação vira uma linha APROVADO/FALHOU no
relatório --saida; o processo sai com código 1 se alguma falhar.
"""
import argparse
import json
import os
import sys
import time
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

U1 = os.environ.get('ATLAS_E2E_USUARIO', '')
U2 = os.environ.get('ATLAS_E2E_USUARIO2', '')
CONTAS = {}
for _u, _v in ((U1, 'ATLAS_E2E_SENHA'), (U2, 'ATLAS_E2E_SENHA2')):
    if _u and os.environ.get(_v):
        CONTAS[_u] = os.environ[_v]
if not U1 or not U2 or U1 not in CONTAS or U2 not in CONTAS:
    sys.exit('Faltam credenciais: defina ATLAS_E2E_USUARIO/ATLAS_E2E_SENHA e ATLAS_E2E_USUARIO2/ATLAS_E2E_SENHA2.')

resultados = []


def check(nome, cond, detalhe=''):
    resultados.append({'verificacao': nome, 'resultado': 'APROVADO' if cond else 'FALHOU', 'detalhe': str(detalhe)[:400]})
    print(('  OK   ' if cond else '  FALHA ') + nome + (f' — {detalhe}' if detalhe and not cond else ''), flush=True)
    return cond


def observar(page, nome):
    """Erros de console, exceções de página e respostas >= 400 da jornada."""
    ruido = []
    page.on('console', lambda m: m.type == 'error' and ruido.append(('console', m.text)))
    page.on('pageerror', lambda e: ruido.append(('pageerror', str(e))))
    page.on('response', lambda r: r.status >= 400 and ruido.append(('http', f'{r.status} {r.url}')))
    return ruido


def login(page, usuario):
    page.goto(BASE + '/login.html')
    page.fill('#username', usuario)
    page.fill('#password', CONTAS[usuario])
    page.click('#login-form button[type=submit]')
    page.wait_for_url('**/painel.html*', timeout=20000)
    page.wait_for_selector('#loading', state='hidden', timeout=20000)


def abrir_empresas(page):
    page.click('[data-view="empresas"]')
    page.wait_for_selector('#ea-content:not([hidden])', timeout=30000)
    page.wait_for_function("document.querySelectorAll('#ea-lista .ea-item').length>0", timeout=30000)


def ficha_titulo(page):
    return page.inner_text('#ea-ficha-titulo')


def clicar_processo_no_mapa(page, processo):
    """Leva o mapa até o centroide do processo e clica no pixel dele (clique real do mouse)."""
    pos = page.evaluate(f"window.EmpresasAtlas.processo('{processo}')")
    page.locator('#ea-map').scroll_into_view_if_needed()
    page.evaluate(f"window.EmpresasAtlas.mapa().setView([{pos['lat']},{pos['lon']}],13,{{animate:false}});0")
    page.wait_for_timeout(700)
    caixa = page.locator('#ea-map').bounding_box()
    ponto = page.evaluate(f"(()=>{{const p=window.EmpresasAtlas.mapa().latLngToContainerPoint([{pos['lat']},{pos['lon']}]);return [p.x,p.y]}})()")
    page.mouse.click(caixa['x'] + ponto[0], caixa['y'] + ponto[1])
    page.wait_for_timeout(900)


with sync_playwright() as pw:
    nav = pw.chromium.launch(headless=True, **({} if args.canal in ('', 'chromium') else {'channel': args.canal}))

    # ---------------------------------------------------------------- 1. login, abas antigas e console
    ctx = nav.new_context(viewport={'width': 1440, 'height': 900}, accept_downloads=True, locale='pt-BR')
    page = ctx.new_page()
    ruido = observar(page, 'principal')
    t0 = time.time()
    login(page, U1)
    check('Login', '/painel.html' in page.url)
    page.screenshot(path=str(CAPT / '01_atlas_panorama.png'))
    for aba in ['indicadores', 'mapa', 'radar', 'mercado', 'comex', 'previsao', 'territorio', 'bases', 'metodologia']:
        page.click(f'[data-view="{aba}"]')
        page.wait_for_timeout(2500 if aba in ('mapa', 'radar') else 1200)
        visivel = page.is_visible(f'#{aba}-view')
        erro = page.inner_text(f'#{aba}-error') if page.locator(f'#{aba}-error').count() else ''
        check(f'Aba {aba} abre sem erro', visivel and not erro.strip(), erro)
        page.screenshot(path=str(CAPT / f'02_aba_{aba}.png'))

    # ---------------------------------------------------------------- 2. Empresas: carga, métricas, Top N
    t1 = time.time()
    abrir_empresas(page)
    check('Aba Empresas carrega o atlas', page.is_visible('#ea-map') and page.is_visible('#ea-lista'), f'{time.time()-t1:.1f}s')
    check('Indicadores do recorte preenchidos', page.locator('#ea-metrics .metric').count() == 4)
    ctx_txt = page.inner_text('#ea-context')
    check('Top N declara métrica, período e universo', 'Top 10' in ctx_txt and '2022' in ctx_txt and 'CFEM' in ctx_txt, ctx_txt)
    check('Mesmo layout das outras abas (sidebar, cabeçalho, PT/EN)', page.is_visible('.sidebar') and page.is_visible('.app-header') and page.is_visible('.lang-switch'))
    check('Um único mapa Leaflet na aba', page.locator('#ea-map.leaflet-container').count() == 1)
    page.screenshot(path=str(CAPT / '03_empresas_visao_geral.png'), full_page=False)

    # ---------------------------------------------------------------- 2b. mapa: pontos finos e navegação
    page.wait_for_function('window.EmpresasAtlas.pontosNaTela()>5000', timeout=15000)
    check('Mapa em pontos finos: nenhum objeto Leaflet por ponto', page.locator('#ea-map .leaflet-interactive').count() == 0,
          page.locator('#ea-map .leaflet-interactive').count())
    [page.evaluate('window.EmpresasAtlas.redesenhoMs()') for _ in range(3)]
    tempos = sorted(page.evaluate('window.EmpresasAtlas.redesenhoMs()') for _ in range(7))
    check('Redesenho de todos os pontos do estado abaixo de 50 ms', tempos[3] < 50, f'mediana {tempos[3]:.1f} ms')
    page.locator('.ea-map-panel').screenshot(path=str(CAPT / '03b_mapa_pontos_finos_estado.png'))
    # hierarquia de fase (lavra maior e mais forte) e legenda que liga/desliga fases no mapa
    rl, rp = page.evaluate('[window.EmpresasAtlas.raioFase(0), window.EmpresasAtlas.raioFase(2)]')
    check('Hierarquia: ponto de lavra autorizada maior que o de pesquisa', rl > rp * 1.5, f'{rl:.1f} × {rp:.1f} px')
    antes = page.evaluate('window.EmpresasAtlas.pontosNaTela()')
    page.click('#ea-legenda .ea-fase[data-g="2"]')
    page.wait_for_timeout(400)
    sem = page.evaluate('window.EmpresasAtlas.pontosNaTela()')
    check('Legenda: clicar em Pesquisa esconde os pontos de pesquisa no mapa',
          sem < antes - 5000 and page.get_attribute('#ea-legenda .ea-fase[data-g="2"]', 'aria-pressed') == 'false', f'{antes} → {sem}')
    page.locator('.ea-map-panel').screenshot(path=str(CAPT / '03c_mapa_sem_pesquisa.png'))
    page.click('#ea-legenda .ea-fase[data-g="2"]')
    page.wait_for_timeout(400)
    check('Legenda: clicar de novo mostra a pesquisa', page.evaluate('window.EmpresasAtlas.pontosNaTela()') == antes)
    page.locator('#ea-map').scroll_into_view_if_needed()
    caixa = page.locator('#ea-map').bounding_box()
    cx, cy = caixa['x'] + caixa['width'] / 2, caixa['y'] + caixa['height'] / 2
    z0 = page.evaluate('window.EmpresasAtlas.mapa().getZoom()')
    page.mouse.move(cx, cy)
    page.mouse.wheel(0, -100)   # um dente de roda de mouse comum
    page.wait_for_timeout(900)
    z1 = page.evaluate('window.EmpresasAtlas.mapa().getZoom()')
    check('Um dente da roda aproxima 1 nível, sem clicar antes no mapa', z1 - z0 >= 1, f'{z0} → {z1}')
    page.mouse.down()
    page.mouse.move(cx + 1400, cy + 900, steps=12)
    page.mouse.up()
    page.wait_for_timeout(1200)
    centro = page.evaluate('(()=>{const c=window.EmpresasAtlas.mapa().getCenter();return [c.lat,c.lng]})()')
    lim = page.evaluate('window.EmpresasAtlas.limites()')
    check('Arrastar não leva o mapa para fora de Goiás', bool(lim) and lim[0] - .01 <= centro[0] <= lim[2] + .01 and lim[1] - .01 <= centro[1] <= lim[3] + .01, centro)
    page.click('#ea-map .ea-ctl [data-a="go"]')
    page.wait_for_timeout(900)
    check('Botão "Voltar para Goiás" do mapa volta ao estado inteiro', page.evaluate('window.EmpresasAtlas.mapa().getZoom()') < 7.5)
    pos = page.evaluate("window.EmpresasAtlas.processo('861427/2010')")
    page.evaluate(f"window.EmpresasAtlas.mapa().setView([{pos['lat']},{pos['lon']}],12,{{animate:false}});0")
    page.wait_for_timeout(800)
    caixa = page.locator('#ea-map').bounding_box()
    pp = page.evaluate(f"(()=>{{const p=window.EmpresasAtlas.mapa().latLngToContainerPoint([{pos['lat']},{pos['lon']}]);return [p.x,p.y]}})()")
    page.mouse.move(caixa['x'] + pp[0], caixa['y'] + pp[1])
    page.wait_for_timeout(500)
    tip = page.locator('#ea-map .leaflet-tooltip.ea-tip')
    check('Passar o mouse no ponto mostra processo, fase e empresa', tip.count() == 1 and '861427/2010' in tip.inner_text(), tip.inner_text() if tip.count() else '')
    page.mouse.move(5, 5)
    page.click('#ea-map .ea-ctl [data-a="go"]')
    page.wait_for_timeout(700)

    # ---------------------------------------------------------------- 3. busca com autocomplete e teclado
    page.click('#ea-busca')
    page.keyboard.type('cmoc', delay=40)
    page.wait_for_selector('#ea-sugestoes:not([hidden]) li[data-j]', timeout=5000)
    check('Autocomplete mostra a empresa ao digitar', 'CMOC' in page.inner_text('#ea-sugestoes'))
    check('Lista e mapa filtram enquanto digita', page.locator('#ea-lista .ea-item').count() == 1)
    page.keyboard.press('ArrowDown')
    page.keyboard.press('Enter')
    page.wait_for_selector('#ea-ficha:not([hidden])', timeout=5000)
    check('Selecionar pela busca (teclado) abre a ficha', 'CMOC' in ficha_titulo(page))
    check('URL própria da empresa (#empresas/<cnpj>)', page.url.endswith('#empresas/26108898'), page.url)
    page.wait_for_timeout(2500)  # polígonos sob demanda
    page.screenshot(path=str(CAPT / '04_ficha_cmoc_perfil.png'), full_page=False)
    page.locator('#ea-ficha').screenshot(path=str(CAPT / '05_ficha_cmoc_perfil_detalhe.png'))
    corpos = {}
    for aba in ['perfil', 'territorio', 'economia', 'projetos', 'noticias', 'historico']:
        page.click(f'[data-aba="{aba}"]')
        page.wait_for_timeout(300)
        corpos[aba] = page.inner_text('#ea-corpo')
        page.locator('#ea-ficha').screenshot(path=str(CAPT / f'06_ficha_cmoc_{aba}.png'))
    check('Perfil: CNPJ raiz, grupo e minerais críticos com base legal', '26.108.898' in corpos['perfil'] and 'CMOC Group' in corpos['perfil'] and 'CRÍTICO (GO)' in corpos['perfil'].upper())
    check('Território: já explora × pode explorar com evidência', 'JÁ EXPLORA' in corpos['territorio'].upper() and 'PODE EXPLORAR' in corpos['territorio'].upper())
    check('Território: título de lavra não é chamado de mina ativa', 'não comprova operação' in corpos['perfil'] and 'mina ativa' not in corpos['territorio'].lower().replace('"minas ativas"', ''))
    check('Economia: CFEM, CCEE com meses observados e produção com tipo', 'meses observados' in corpos['economia'] and 'Metal em concentrado' in corpos['economia'] or 'Produto acabado' in corpos['economia'])
    check('Economia: venda/embarque não chamados de produção', ('não é produção' in corpos['economia']) or ('Embarque' not in corpos['economia']))
    check('Projetos: vínculo e confiança informados', 'Confiança' in corpos['projetos'] and ('Processo ANM' in corpos['projetos'] or 'Curadoria' in corpos['projetos']))
    check('Notícias: título, data, veículo e método de vínculo', 'Catalão' in corpos['noticias'] and 'contexto de Goiás' in corpos['noticias'])
    check('Histórico: série anual com unidades separadas', 'MWh' in corpos['historico'] and 'R$' in corpos['historico'])
    # o coeficiente da ficha leva à sub-aba Produção declarada e energia, já filtrada pela empresa; e volta ao Atlas
    page.click('[data-aba="economia"]')
    page.click('#ea-corpo [data-ir="painel-energia"]')
    page.wait_for_timeout(700)
    emp_decl = page.eval_on_selector('#ep-emp', 'e=>e.value')
    check('Ficha abre a sub-aba Produção declarada e energia filtrada pela empresa',
          page.is_visible('#ep-aba-declarada') and not page.is_visible('#ep-aba-atlas') and 'CMOC' in emp_decl.upper(), emp_decl)
    page.click('#ep-tabs [data-ep="atlas"]')
    page.wait_for_timeout(500)
    page.click('[data-aba="perfil"]')

    # ---------------------------------------------------------------- 4. seleção pelo mapa (clique real)
    clicar_processo_no_mapa(page, '861427/2010')  # processo de lavra da Serra Verde, em Minaçu
    sel = page.evaluate('window.EmpresasAtlas.selecionada()')
    if sel != '08842895' and page.locator('.leaflet-popup .ea-pop [data-i]').count():
        page.click('.leaflet-popup .ea-pop [data-i]')
        page.wait_for_timeout(600)
        sel = page.evaluate('window.EmpresasAtlas.selecionada()')
    check('Clique no ponto do mapa seleciona a empresa e abre a ficha', sel == '08842895' and 'SERRA VERDE' in ficha_titulo(page), sel)
    page.wait_for_timeout(2500)
    page.locator('.ea-map-panel').screenshot(path=str(CAPT / '07_mapa_serra_verde_poligonos.png'))
    page.click('[data-aba="noticias"]')
    nv = page.inner_text('#ea-corpo')
    check('Notícias Serra Verde: ex-funcionários marcados como menção indireta', 'Menções indiretas' in nv)
    sv = {}
    for aba in ['perfil', 'territorio', 'economia', 'projetos', 'noticias', 'historico']:
        page.click(f'[data-aba="{aba}"]')
        page.wait_for_timeout(250)
        sv[aba] = page.inner_text('#ea-corpo')
    mudou = all(sv[a] != corpos[a] for a in sv)
    check('Ficha muda de contexto em todas as áreas (6 seções diferentes da CMOC)',
          mudou and '08.842.895' in sv['perfil'] and 'Minaçu' in sv['territorio'] and 'terras' in (sv['noticias'] + sv['projetos']).lower(),
          {a: sv[a][:60] for a in sv})
    check('Painel de produção e energia acompanha a empresa', page.eval_on_selector('#ep-emp', 'e=>e.value') == 'SERRA VERDE PESQUISA E MINERACAO LTDA',
          page.eval_on_selector('#ep-emp', 'e=>e.value'))
    # polígono: clicar dentro do polígono de outro processo da mesma empresa
    page.click('[data-aba="territorio"]')
    page.click('#ea-corpo [data-proc]')
    page.wait_for_timeout(1500)
    check('Processo da tabela destacado e enquadrado no mapa', page.locator('#ea-corpo tr.ea-destaque').count() == 1)

    # digitar rápido e apertar Enter antes da espera da busca (160 ms) também escolhe a empresa
    page.fill('#ea-busca', 'mosaic fert')
    page.keyboard.press('Enter')
    page.wait_for_timeout(700)
    check('Enter imediato após digitar escolhe a empresa', 'MOSAIC' in ficha_titulo(page), ficha_titulo(page))
    page.go_back()
    page.wait_for_timeout(800)

    # ---------------------------------------------------------------- 5. voltar do navegador
    page.go_back()
    page.wait_for_timeout(1200)
    check('Voltar do navegador restaura a empresa anterior', page.evaluate('window.EmpresasAtlas.selecionada()') == '26108898', page.evaluate('window.EmpresasAtlas.selecionada()'))

    # ---------------------------------------------------------------- 6. filtros combinados, Top N e puxadores
    page.select_option('#ea-mun', label='Catalão')
    page.wait_for_timeout(500)
    lista_catalao = page.inner_text('#ea-lista')
    check('Filtro de município reduz lista e indicadores', 'CMOC' in lista_catalao and 'MOSAIC' in lista_catalao, lista_catalao[:200])
    page.select_option('#ea-min', label='Fosfato')
    page.wait_for_timeout(400)
    check('Filtro de mineral combinado ao município', 'MOSAIC' in page.inner_text('#ea-lista'))
    page.select_option('#ea-grupo', 'lavra_autorizada')
    page.select_option('#ea-metrica', 'processos')
    page.select_option('#ea-top', '20')
    page.wait_for_timeout(400)
    check('Métrica e Top N refletidos no contexto', 'processos' in page.inner_text('#ea-context').lower())
    page.screenshot(path=str(CAPT / '08_filtros_catalao_fosfato.png'))
    page.click('#ea-reset')
    page.select_option('#ea-dado', 'crit_est')
    page.wait_for_timeout(400)
    n_crit = page.locator('#ea-lista .ea-item').count()
    check('Filtro "mineral crítico (GO)" funciona', n_crit > 0)
    page.select_option('#ea-dado', '')
    page.select_option('#ea-ano-ini', '2025')
    page.select_option('#ea-ano-fim', '2025')
    page.wait_for_timeout(400)
    m = page.inner_text('#ea-metrics')
    check('Período altera CFEM e puxadores', '2025' in m and 'Puxadores' in m)
    check('Puxadores com definição numérica (80% da CFEM)', '80%' in m)

    # ---------------------------------------------------------------- 7. exportações
    with page.expect_download() as d:
        page.click('#ea-exp-csv')
    csv_txt = Path(d.value.path()).read_text(encoding='utf-8-sig')
    check('Exportação CSV do recorte (cabeçalho + linhas)', csv_txt.startswith('#') and 'cnpj_raiz' in csv_txt and csv_txt.count('\n') >= 5, d.value.suggested_filename)
    with page.expect_download() as d:
        page.click('#ea-exp-json')
    js = json.loads(Path(d.value.path()).read_text(encoding='utf-8'))
    check('Exportação JSON leva recorte, regras e empresas', js['recorte']['periodo'] == [2025, 2025] and len(js['empresas']) == 10 and 'puxadores' in js['regras'])
    with page.expect_download() as d:
        page.click('#ea-ficha-exp')
    fj = json.loads(Path(d.value.path()).read_text(encoding='utf-8'))
    check('Exportação da ficha (JSON) com processos', fj['empresa']['cnpj'] == '26108898' and len(fj['processos']) == 57)
    page.click('[data-aba="territorio"]')
    with page.expect_download() as d:
        page.click('[data-exp="proc-csv"]')
    check('Exportação CSV dos processos da empresa', 'centroide_lat_indicativo' in Path(d.value.path()).read_text(encoding='utf-8-sig'))

    # ---------------------------------------------------------------- 8. comparação
    page.click('#ea-cmp-add')
    page.fill('#ea-busca', '')
    page.click('#ea-busca')
    page.keyboard.type('mosaic', delay=30)
    page.wait_for_selector('#ea-sugestoes li[data-j]')
    page.keyboard.press('Enter')
    page.wait_for_timeout(800)
    page.click('#ea-cmp-add')
    page.wait_for_timeout(500)
    cmp_txt = page.inner_text('#ea-cmp')
    check('Comparação de 2 empresas lado a lado', 'CMOC' in cmp_txt and 'MOSAIC' in cmp_txt and 'CFEM 2025' in cmp_txt)
    page.locator('#ea-cmp').screenshot(path=str(CAPT / '09_comparacao.png'))
    page.click('[data-aba="noticias"]')
    mosaic_news = page.inner_text('#ea-corpo')
    itens_mosaic = page.locator('#ea-corpo .rd-news li').all_inner_texts()
    check('Mosaic: notícias de MG sem Goiás não atribuídas',
          bool(itens_mosaic) and all(('Catalão' in i) or ('GO' in i.split()) for i in itens_mosaic), itens_mosaic)

    # ---------------------------------------------------------------- 9. metodologia e base legal
    page.click('#ea-metodo summary')
    met = page.inner_text('#ea-metodo')
    check('Base legal: federal e estadual separadas', 'Resolução nº 2' in met and '23.597' in met)
    page.locator('#ea-metodo').screenshot(path=str(CAPT / '10_metodologia.png'))

    # ---------------------------------------------------------------- 10. troca de abas e retorno
    page.click('[data-view="mapa"]')
    page.wait_for_timeout(1200)
    page.click('[data-view="empresas"]')
    page.wait_for_timeout(800)
    check('Sair e voltar não duplica o mapa nem perde a seleção', page.locator('#ea-map.leaflet-container').count() == 1 and page.evaluate('window.EmpresasAtlas.selecionada()') is not None)

    # sub-abas da aba Empresas (mantidas da main): abrem sem erro e, ao voltar, o mapa do Atlas tem tamanho e a seleção continua
    sub_ok = {}
    for sub in ['mapa', 'estimada', 'declarada', 'direitos']:
        page.click(f'#ep-tabs [data-ep="{sub}"]')
        page.wait_for_timeout(2500 if sub in ('mapa', 'direitos') else 1200)
        erro_sub = ' '.join(page.locator(f'#ep-aba-{sub} .error').all_inner_texts()).strip()
        sub_ok[sub] = page.is_visible(f'#ep-aba-{sub}') and not page.is_visible('#ep-aba-atlas') and not erro_sub
    check('Sub-abas Mapa das empresas, Produção por empresa, Declarada e Arrecadação abrem sem erro', all(sub_ok.values()), sub_ok)
    page.click('#ep-tabs [data-ep="atlas"]')
    page.wait_for_timeout(600)
    tam = page.evaluate('(()=>{const s=window.EmpresasAtlas.mapa().getSize();return [s.x,s.y]})()')
    check('Voltar à sub-aba Atlas: mapa com tamanho e seleção mantida', tam[0] > 300 and tam[1] > 200
          and page.evaluate('window.EmpresasAtlas.selecionada()') is not None, tam)
    page.click('#ep-tabs [data-ep="declarada"]')
    page.keyboard.press('Escape')
    page.wait_for_timeout(300)
    sel_esc = page.evaluate('window.EmpresasAtlas.selecionada()')
    page.click('#ep-tabs [data-ep="atlas"]')
    check('Esc em outra sub-aba não desmarca a empresa do Atlas', sel_esc is not None, sel_esc)

    erros = [r for r in ruido if not ('tile.openstreetmap.org' in r[1] or 'fonts.g' in r[1])]
    # A tela de login pergunta /api/auth/me antes de entrar para saber se já há sessão: o 401 ali é a resposta esperada
    # (comportamento original de public/login.js), e o navegador o registra também como erro de console.
    erros = [r for r in erros if not ('/api/auth/me' in r[1] or (r[0] == 'console' and 'status of 401' in r[1]))]
    check('Console e rede sem erros nas jornadas principais', not erros, erros[:6])

    # ---------------------------------------------------------------- 11. dois usuários ao mesmo tempo
    ctx2 = nav.new_context(viewport={'width': 1280, 'height': 860})
    p2 = ctx2.new_page()
    login(p2, U2)
    abrir_empresas(p2)
    p2.click('#ea-lista .ea-item >> nth=2')
    p2.wait_for_timeout(600)
    sel2 = p2.evaluate('window.EmpresasAtlas.selecionada()')
    sel1 = page.evaluate('window.EmpresasAtlas.selecionada()')
    check('Dois usuários navegando ao mesmo tempo, seleções independentes', sel2 and sel1 and sel1 != sel2, f'{sel1} / {sel2}')
    ctx2.close()

    # ---------------------------------------------------------------- 12. falha de API e estado de erro
    ctx3 = nav.new_context(viewport={'width': 1280, 'height': 860})
    p3 = ctx3.new_page()
    login(p3, U1)
    p3.route('**/api/empresas/atlas', lambda r: r.fulfill(status=500, body='{"detail":"Falha simulada no teste"}', content_type='application/json'))
    p3.click('[data-view="empresas"]')
    p3.wait_for_selector('#ea-retry', timeout=10000)
    check('Falha da API mostra erro e "tentar de novo"', 'Falha simulada' in p3.inner_text('#ea-error'))
    p3.unroute('**/api/empresas/atlas')
    p3.click('#ea-retry')
    p3.wait_for_selector('#ea-content:not([hidden])', timeout=20000)
    check('"Tentar de novo" recupera a aba', p3.is_visible('#ea-map'))
    ctx3.close()

    # ---------------------------------------------------------------- 12b. desmarcar pelo mapa e zoom alto com polígonos
    ctx6 = nav.new_context(viewport={'width': 1440, 'height': 900})
    p6 = ctx6.new_page()
    login(p6, U1)
    abrir_empresas(p6)
    p6.wait_for_function('window.EmpresasAtlas.pontosNaTela()>5000', timeout=15000)

    def marcar_serra_verde():
        clicar_processo_no_mapa(p6, '861427/2010')
        if p6.evaluate('window.EmpresasAtlas.selecionada()') != '08842895' and p6.locator('.leaflet-popup .ea-pop [data-i]').count():
            p6.click('.leaflet-popup .ea-pop [data-i]')
            p6.wait_for_timeout(600)
        return p6.evaluate('window.EmpresasAtlas.selecionada()') == '08842895'

    ok = marcar_serra_verde()
    check('Selecionar pelo mapa não muda o zoom (sem salto)', ok and p6.evaluate('window.EmpresasAtlas.mapa().getZoom()') == 13,
          p6.evaluate('window.EmpresasAtlas.mapa().getZoom()'))
    check('Etiqueta da seleção no mapa mostra a empresa', p6.is_visible('#ea-map .ea-chip-sel') and 'SERRA VERDE' in p6.inner_text('#ea-map .ea-chip-sel'))
    p6.wait_for_timeout(2500)   # polígonos sob demanda
    [p6.evaluate('window.EmpresasAtlas.redesenhoMs()') for _ in range(3)]
    tz = sorted(p6.evaluate('window.EmpresasAtlas.redesenhoMs()') for _ in range(7))
    check('Redesenho no zoom 13 com polígonos abaixo de 50 ms', tz[3] < 50, f'mediana {tz[3]:.1f} ms')
    camadas = p6.evaluate('Object.keys(window.EmpresasAtlas.mapa()._layers).length')
    check('Polígonos sem objetos Leaflet (camadas no mapa < 30)', camadas < 30, camadas)
    p6.locator('.ea-map-panel').screenshot(path=str(CAPT / '07b_mapa_etiqueta_selecao.png'))
    clicar_processo_no_mapa(p6, '861427/2010')
    check('Desmarcar: clicar de novo no processo destacado', p6.evaluate('window.EmpresasAtlas.selecionada()') is None and p6.is_hidden('#ea-ficha'))
    marcar_serra_verde()
    p6.keyboard.press('Escape')
    p6.wait_for_timeout(500)
    check('Desmarcar: tecla Esc', p6.evaluate('window.EmpresasAtlas.selecionada()') is None)
    marcar_serra_verde()
    p6.click('#ea-map .ea-chip-sel button')
    p6.wait_for_timeout(500)
    check('Desmarcar: × da etiqueta', p6.evaluate('window.EmpresasAtlas.selecionada()') is None and p6.is_hidden('#ea-map .ea-chip-sel'))
    marcar_serra_verde()
    p6.evaluate('window.EmpresasAtlas.mapa().setView([-16.2,-50.6],9,{animate:false});0')
    p6.wait_for_timeout(700)
    vazio = p6.evaluate('window.EmpresasAtlas.pontoVazio()')
    caixa = p6.locator('#ea-map').bounding_box()
    if vazio:
        p6.mouse.click(caixa['x'] + vazio[0], caixa['y'] + vazio[1])
        p6.wait_for_timeout(500)
    check('Desmarcar: clique numa área vazia do mapa', bool(vazio) and p6.evaluate('window.EmpresasAtlas.selecionada()') is None, vazio)
    ctx6.close()

    # ---------------------------------------------------------------- 13. inglês
    ctx4 = nav.new_context(viewport={'width': 1440, 'height': 900})
    p4 = ctx4.new_page()
    login(p4, U1)
    p4.goto(BASE + '/painel.html?lang=en#empresas')
    p4.wait_for_selector('#ea-content:not([hidden])', timeout=30000)
    check('Interface em inglês (EN)', 'Company atlas' in p4.inner_text('#ep-tabs [data-ep="atlas"]')
          and 'Search company' in p4.inner_text('#ep-aba-atlas'), p4.inner_text('#ep-tabs'))
    p4.screenshot(path=str(CAPT / '11_empresas_en.png'))
    p4.evaluate("localStorage.setItem('minera-lang','pt')")
    ctx4.close()

    # ---------------------------------------------------------------- 14. celular
    ctx5 = nav.new_context(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True, device_scale_factor=2)
    p5 = ctx5.new_page()
    login(p5, U1)
    abrir_empresas(p5)
    largura = p5.evaluate('[document.documentElement.scrollWidth, innerWidth]')
    check('Celular (390 px): sem rolagem horizontal da página', largura[0] <= largura[1] + 1, largura)
    p5.screenshot(path=str(CAPT / '12_celular_topo.png'))
    p5.click('#ea-lista .ea-item >> nth=0')
    p5.wait_for_timeout(1500)
    check('Celular: ficha abre ao tocar na empresa', p5.is_visible('#ea-ficha'))
    p5.screenshot(path=str(CAPT / '13_celular_ficha.png'))
    largura = p5.evaluate('[document.documentElement.scrollWidth, innerWidth]')
    check('Celular: ficha sem rolagem horizontal da página', largura[0] <= largura[1] + 1, largura)
    ctx5.close()

    nav.close()

falhas = [r for r in resultados if r['resultado'] != 'APROVADO']
Path(args.saida).parent.mkdir(parents=True, exist_ok=True)
Path(args.saida).write_text(json.dumps({'executado_em': time.strftime('%Y-%m-%d %H:%M:%S'), 'base': BASE, 'navegador': args.canal,
                                         'total': len(resultados), 'falhas': len(falhas), 'verificacoes': resultados},
                                        ensure_ascii=False, indent=1), encoding='utf-8')
print(f'\n{len(resultados) - len(falhas)}/{len(resultados)} verificações aprovadas')
sys.exit(1 if falhas else 0)
