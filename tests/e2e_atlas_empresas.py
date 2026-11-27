"""Roteiro de navegador da aba Empresas consolidada (Explorar · Dossiê · Análises · Comparar), contra um servidor no ar.
A seção 19 cobre a auditoria final (comparação, exportações lidas do arquivo baixado, limite de três, histórico); a 20, os ajustes finais
(análise → dossiê → análise, linguagem pública em PT e EN, histórico, exportações das análises, município → mapa).

    python tests/e2e_atlas_empresas.py --base https://<servidor> --capturas DIR --saida ARQ [--canal chromium|chrome|msedge]

Contas (duas, com a senha já trocada; a segunda pode ser de qualquer papel):
- variáveis ATLAS_E2E_USUARIO / ATLAS_E2E_SENHA e ATLAS_E2E_USUARIO2 / ATLAS_E2E_SENHA2; ou
Nenhuma senha fica no código. Não roda no CI (precisa do servidor no ar). --canal chromium usa o Chromium do Playwright
(`playwright install chromium`); msedge/chrome usam o navegador instalado. Cada verificação vira uma linha APROVADO/FALHOU no
relatório --saida; o processo sai com código 1 se alguma falhar. Os totais são conferidos contra os arquivos de dados do repositório.
"""
import argparse
import json
import os
import re
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
ap.add_argument('--baixados', default='', help='pasta dos arquivos exportados no teste (padrão: arquivos_exportados ao lado de --saida)')
args = ap.parse_args()
BASE = args.base.rstrip('/')
CAPT = Path(args.capturas)
CAPT.mkdir(parents=True, exist_ok=True)
BAIX = Path(args.baixados or Path(args.saida).parent / 'arquivos_exportados')
BAIX.mkdir(parents=True, exist_ok=True)

U1 = os.environ.get('ATLAS_E2E_USUARIO', '')
U2 = os.environ.get('ATLAS_E2E_USUARIO2', '')
CONTAS = {}
for _u, _v in ((U1, 'ATLAS_E2E_SENHA'), (U2, 'ATLAS_E2E_SENHA2')):
    if os.environ.get(_v):
        CONTAS[_u] = os.environ[_v]
if not U1 or not U2 or U1 not in CONTAS or U2 not in CONTAS:
    sys.exit('Faltam credenciais: defina ATLAS_E2E_USUARIO/ATLAS_E2E_SENHA e ATLAS_E2E_USUARIO2/ATLAS_E2E_SENHA2.')

# Totais esperados, lidos dos mesmos arquivos que a API serve (conferência com as fontes, não números fixos).
ATLAS = json.loads((RAIZ / 'data' / 'empresas' / 'atlas_empresas.json').read_text(encoding='utf-8'))
BASE_EMP = json.loads((RAIZ / 'data' / 'empresas' / 'empresas.json').read_text(encoding='utf-8'))
CFEM_22_25 = sum(r[4] for r in ATLAS['cfem']['rows'] if 2022 <= r[1] <= 2025)
CFEM_22_26 = ATLAS['meta']['cobertura']['cfem_pj_2022_2026']
EST = BASE_EMP['estimada']
EC = {c: i for i, c in enumerate(EST['colunas'])}
EST_2025_BEN = [r for r in EST['linhas'] if r[EC['ano']] == 2025 and r[EC['base']] == 'beneficiada']

resultados = []


def check(nome, cond, detalhe=''):
    resultados.append({'verificacao': nome, 'resultado': 'APROVADO' if cond else 'FALHOU', 'detalhe': str(detalhe)[:400]})
    print(('  OK   ' if cond else '  FALHA ') + nome + (f' — {detalhe}' if detalhe and not cond else ''), flush=True)
    return cond


def observar(page):
    """Erros de console, exceções de página e respostas >= 400 da jornada."""
    ruido = []
    page.on('console', lambda m: m.type == 'error' and ruido.append(('console', m.text)))
    page.on('pageerror', lambda e: ruido.append(('pageerror', str(e))))
    page.on('response', lambda r: r.status >= 400 and ruido.append(('http', f'{r.status} {r.url}')))
    return ruido


def erros_relevantes(ruido):
    erros = [r for r in ruido if not ('tile.openstreetmap.org' in r[1] or 'fonts.g' in r[1])]
    # A tela de login pergunta /api/auth/me antes de entrar: o 401 ali é a resposta esperada (public/login.js).
    return [r for r in erros if not ('/api/auth/me' in r[1] or (r[0] == 'console' and 'status of 401' in r[1]))]


def n_acontecimentos(cnpj):
    # como historico() de empresas-atlas.js: notícias diretas e evidências dos projetos fora do Radar, com data
    i = POR[cnpj]['i']
    nd = sum(1 for n in ATLAS['noticias'] if n['e'] == i and n['tipo'] == 'empresa' and n.get('d'))
    ev = sum(1 for p in ATLAS['projetos'] if i in p['e'] and p['fonte'] != 'radar' for v in (p.get('evidencias') or []) if v.get('d'))
    return nd + ev


def sair_da_barra(pg):
    # tira o mouse da barra lateral (desde 3f48b2c ela só se recolhe quando o mouse sai)
    pg.mouse.move(900, 450)
    pg.wait_for_timeout(400)


def login(page, usuario):
    page.goto(BASE + '/login.html')
    page.fill('#username', usuario)
    page.fill('#password', CONTAS[usuario])
    page.click('#login-form button[type=submit]')
    page.wait_for_url('**/painel.html*', timeout=20000)
    page.wait_for_selector('#loading', state='hidden', timeout=20000)


def abrir_empresas(page):
    page.click('[data-view="empresas"]')
    sair_da_barra(page)
    page.wait_for_selector('#ea-content:not([hidden])', timeout=40000)
    page.wait_for_function("document.querySelectorAll('#ea-lista .ea-item').length>0", timeout=30000)


def sel(page):
    return page.evaluate('window.EmpresasAtlas.selecionada()')


def area(page, nome):
    page.click(f'#ea-nav-{nome}')
    page.wait_for_timeout(400)


def analise(page, nome):
    page.click(f'#ea-anal-tab-{nome}')
    page.wait_for_timeout(500)


def clicar_no_mapa(page, xy):
    caixa = page.locator('#ea-map').bounding_box()
    page.mouse.click(caixa['x'] + xy[0], caixa['y'] + xy[1])
    page.wait_for_timeout(900)


def clicar_processo_no_mapa(page, processo):
    """Leva o mapa até o centroide do processo e clica no pixel dele (clique real do mouse)."""
    pos = page.evaluate(f"window.EmpresasAtlas.processo('{processo}')")
    page.locator('#ea-map').scroll_into_view_if_needed()
    page.evaluate(f"(()=>{{const m=window.EmpresasAtlas.mapa();m.stop();m.setView([{pos['lat']},{pos['lon']}],13,{{animate:false}})}})()")
    page.wait_for_timeout(700)
    ponto = page.evaluate(f"(()=>{{const p=window.EmpresasAtlas.mapa().latLngToContainerPoint([{pos['lat']},{pos['lon']}]);return [p.x,p.y]}})()")
    clicar_no_mapa(page, ponto)


def escolher_no_popup(page, alvo):
    """Pontos sobrepostos abrem uma lista: escolhe a opção do alvo (CNPJ de empresa ou id de projeto)."""
    if sel(page) == alvo or not page.locator('.leaflet-popup .ea-pop button').count():
        return
    for b in page.locator('.leaflet-popup .ea-pop [data-i]').all():
        b.click()
        page.wait_for_timeout(600)
        if sel(page) == alvo:
            return


def proc_foco(page):
    return page.evaluate('window.EmpresasAtlas.processoFoco()')


def escolher_processo(page, processo):
    """Processos sobrepostos abrem a lista de escolha (número ANM + mineral + fase): escolhe o processo pedido."""
    if proc_foco(page) == processo or not page.locator('.leaflet-popup .ea-pop [data-k]').count():
        return
    page.locator('.leaflet-popup .ea-pop [data-k]', has_text=processo).first.click()
    page.wait_for_timeout(600)


def mediana_redesenho(page):
    [page.evaluate('window.EmpresasAtlas.redesenhoMs()') for _ in range(3)]
    return sorted(page.evaluate('window.EmpresasAtlas.redesenhoMs()') for _ in range(7))[3]


def filtros(page):
    """Os filtros do Explorar ficam recolhidos: abre o painel (se estiver fechado) antes de escolher."""
    if page.get_attribute('#ea-filtros-btn', 'aria-expanded') != 'true':
        page.click('#ea-filtros-btn')
        page.wait_for_timeout(150)


def limpar(page):
    """'Limpar filtros' só aparece com algum filtro ativo; sem filtro, não há o que limpar."""
    if page.is_visible('#ea-reset'):
        page.click('#ea-reset')
        page.wait_for_timeout(400)


def bbox(page, seletor):
    return page.locator(seletor).bounding_box()


def sem_rolagem_horizontal(page):
    w = page.evaluate('[document.documentElement.scrollWidth, innerWidth]')
    return w[0] <= w[1] + 1, w


def baixar(page, seletor, pasta):
    """Clica no botão de exportação e guarda o arquivo baixado de verdade (para ler e para os testes no Excel/pandas)."""
    with page.expect_download() as d:
        page.click(seletor)
    destino = Path(pasta) / d.value.suggested_filename
    d.value.save_as(destino)
    return destino


def ler_csv(caminho):
    """CSV da aba: BOM, ';', decimal ',' e cabeçalho na 1ª linha. Devolve (primeira linha, linhas como dict)."""
    import csv
    import io
    bruto = Path(caminho).read_bytes()
    assert bruto.startswith(b'\xef\xbb\xbf'), 'CSV sem BOM'
    txt = bruto.decode('utf-8-sig')
    return txt.split('\r\n', 1)[0], list(csv.DictReader(io.StringIO(txt, newline=''), delimiter=';'))


def numero(s):
    return None if s in ('', None) else float(s.replace(',', '.'))


def ler_xlsx(caminho):
    """Planilha da aba sem biblioteca: {aba: [linha como dict]} com o tipo de cada célula (texto, número, booleano)."""
    import zipfile
    import xml.etree.ElementTree as ET
    ns = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
    z = zipfile.ZipFile(caminho)
    rels = {r.get('Id'): r.get('Target') for r in ET.fromstring(z.read('xl/_rels/workbook.xml.rels'))}
    abas = {}
    for s in ET.fromstring(z.read('xl/workbook.xml')).find(ns + 'sheets'):
        xml = ET.fromstring(z.read('xl/' + rels[s.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')]))
        linhas = []
        for row in xml.find(ns + 'sheetData'):
            vals = {}
            for c in row:
                col, t = re.match(r'[A-Z]+', c.get('r')).group(0), c.get('t')
                vals[col] = (''.join(x.text or '' for x in c.iter(ns + 't')) if t == 'inlineStr' else c.find(ns + 'v').text == '1' if t == 'b'
                             else float(c.find(ns + 'v').text))
            linhas.append(vals)
        cab = linhas[0] if linhas else {}
        abas[s.get('name')] = [{cab[k]: r[k] for k in r} for r in linhas[1:]]
    z.close()
    return abas


with sync_playwright() as pw:
    nav = pw.chromium.launch(headless=True, **({} if args.canal in ('', 'chromium') else {'channel': args.canal}))

    # ================================================================ 1. login e demais abas da plataforma
    ctx = nav.new_context(viewport={'width': 1440, 'height': 900}, accept_downloads=True, locale='pt-BR')
    page = ctx.new_page()
    ruido = observar(page)
    login(page, U1)
    check('Login', '/painel.html' in page.url)
    page.wait_for_selector('#pn-content:not([hidden])', timeout=40000)
    check('Atlas e Panorama abrem (o Panorama perdeu só a sub-aba de empresas, que está na aba Empresas)',
          page.locator('#pn-tabs [data-tab]').count() >= 6 and not page.locator('#pn-tabs [data-tab="empresas"]').count())
    for aba in ['mapa', 'previsao', 'mercado', 'radar', 'bases', 'territorio']:
        page.click(f'[data-view="{aba}"]')
        sair_da_barra(page)
        page.wait_for_timeout(2500 if aba in ('mapa', 'radar') else 1200)
        erro = page.inner_text(f'#{aba}-error') if page.locator(f'#{aba}-error').count() else ''
        check(f'Aba {aba} abre sem erro', page.is_visible(f'#{aba}-view') and not erro.strip(), erro)

    # ================================================================ 2. Explorar: carga, mapa no modo Empresas, indicadores
    t1 = time.time()
    abrir_empresas(page)
    carga = time.time() - t1
    check('Aba Empresas abre em Explorar com o mapa no modo Empresas', page.is_visible('#ea-area-explorar') and page.evaluate('window.EmpresasAtlas.modo()') == 'empresas'
          and page.get_attribute('#ea-modos [data-modo="empresas"]', 'aria-checked') == 'true', f'{carga:.1f}s')
    check('Carga da aba (atlas + análises) abaixo de 8 s', carga < 8, f'{carga:.1f}s')
    page.wait_for_function('window.EmpresasAtlas.pontosNaTela()>2000', timeout=15000)
    n_emp = page.evaluate('window.EmpresasAtlas.pontosNaTela()')
    check('Modo Empresas: um ponto por empresa com processo georreferenciado', n_emp == ATLAS['meta']['cobertura']['empresas_com_ponto'], n_emp)
    tot = page.evaluate('window.EmpresasAtlas.totais()')
    check('Conferência: CFEM 2022–2025 do recorte = soma das linhas de CFEM do pacote', abs(tot['cfem'] - CFEM_22_25) < 1, f"{tot['cfem']:.2f} × {CFEM_22_25:.2f}")
    check('Conferência: 2.261 titulares PJ e 11.144 processos PJ (regressão)', tot['empresas'] == ATLAS['meta']['cobertura']['empresas_indice']
          and tot['processos'] == ATLAS['meta']['cobertura']['processos_pj'], tot)
    lat, mapa = bbox(page, '#ea-lateral'), bbox(page, '#ea-map')
    check('Explorar: lista lateral à esquerda e mapa amplo à direita, na primeira dobra (1440 × 900)',
          lat['x'] + lat['width'] <= mapa['x'] + 2 and mapa['width'] > 2.3 * lat['width'] and mapa['y'] + mapa['height'] <= 905,
          (round(lat['width']), round(mapa['width']), round(mapa['y'] + mapa['height'])))
    check('Filtros recolhidos por padrão, busca em destaque na lateral', page.is_hidden('#ea-filtros') and page.is_visible('#ea-lateral #ea-busca')
          and page.get_attribute('#ea-filtros-btn', 'aria-expanded') == 'false')
    check('Um ranking só: a lista lateral (o ranking completo fica fechado até ser pedido)', page.locator('#empresas-view .ea-lista').count() == 1
          and page.is_hidden('#ea-ranking'))
    faixa = page.inner_text('#ea-metrics')
    check('Faixa compacta com quatro números e o período', page.locator('#ea-metrics > div').count() == 4 and '2022–2025' in faixa
          and '2.261' in page.inner_text('#ea-lista-titulo'), faixa.replace('\n', ' ')[:160])
    check('Lista: nome, referência territorial (município · mineral) e métrica', 'Catalão' in page.inner_text('#ea-lista')
          and 'Nióbio' in page.inner_text('#ea-lista') and 'R$' in page.inner_text('#ea-lista .ea-val >> nth=0'))
    check('Layout nativo do painel (sidebar, cabeçalho, PT/EN) e um mapa só', page.is_visible('.sidebar') and page.is_visible('.lang-switch')
          and page.locator('#ea-map.leaflet-container').count() == 1)
    check('Nenhum objeto Leaflet por ponto (camada Canvas)', page.locator('#ea-map .leaflet-interactive').count() == 0)
    page.screenshot(path=str(CAPT / '01_explorar_modo_empresas.png'), full_page=True)
    t_emp = mediana_redesenho(page)
    check('Redesenho do modo Empresas abaixo de 50 ms', t_emp < 50, f'{t_emp:.1f} ms')
    filtros(page)
    page.select_option('#ea-ano-fim', '2026')
    page.wait_for_timeout(400)
    tot26 = page.evaluate('window.EmpresasAtlas.totais()')
    check('Conferência: CFEM 2022–2026 = R$ do pacote (866.910.612,75 com as entradas atuais)', abs(tot26['cfem'] - CFEM_22_26) < 1, f"{tot26['cfem']:.2f}")
    check('Filtro ativo vira etiqueta removível e o botão Filtros mostra a contagem', page.locator('#ea-context [data-limpa="ea-periodo"]').count() == 1
          and page.inner_text('#ea-filtros-n') == '1')
    page.click('#ea-context [data-limpa="ea-periodo"]')
    page.wait_for_timeout(300)
    check('Remover a etiqueta volta o período padrão', page.input_value('#ea-ano-fim') == '2025' and page.is_hidden('#ea-filtros-n'))
    page.click('#ea-filtros-btn')   # recolhe de novo
    # lista: mostrar mais, ordenação por nome e por relevância
    n0 = page.locator('#ea-lista .ea-item').count()
    page.click('#ea-pag .ea-mais')
    page.wait_for_timeout(300)
    check('Lista em lotes: "Mostrar mais" acrescenta 50', n0 == 50 and page.locator('#ea-lista .ea-item').count() == 100, (n0, page.locator('#ea-lista .ea-item').count()))
    page.select_option('#ea-metrica', 'nome')
    page.wait_for_timeout(300)
    nomes = page.locator('#ea-lista .ea-nome b').all_inner_texts()[:20]
    check('Ordenar por nome (A–Z)', nomes == sorted(nomes, key=lambda x: x.lower()) or nomes[0] <= nomes[-1], nomes[:3])
    page.fill('#ea-busca', 'serra')
    page.wait_for_timeout(500)
    page.select_option('#ea-metrica', 'relevancia')
    page.wait_for_timeout(300)
    primeiro = page.locator('#ea-lista .ea-nome b').first.inner_text()
    check('Ordenar por relevância: com busca, quem casa melhor com o texto vem primeiro', primeiro.upper().startswith('SERRA') or ' SERRA' in primeiro.upper(), primeiro)
    page.fill('#ea-busca', '')
    page.keyboard.press('Escape')
    page.select_option('#ea-metrica', 'cfem')
    page.wait_for_timeout(400)
    # ranking completo e Pareto sob demanda
    page.click('#ea-ranking-btn')
    page.wait_for_timeout(600)
    rk = page.inner_text('#ea-ranking') if page.is_visible('#ea-ranking') else ''
    check('Ranking e Pareto 80% abrem sob demanda (curva, linha dos 80% e tabela)', page.locator('#ea-ranking svg.ea-pareto').count() == 1
          and page.locator('#ea-ranking .ea-p80').count() == 1 and page.locator('#ea-ranking tbody tr').count() >= 10 and '80%' in rk, rk[:120])
    page.locator('#ea-ranking').screenshot(path=str(CAPT / '01b_ranking_pareto.png'))
    page.click('#ea-ranking [data-rk-fechar]')
    page.wait_for_timeout(300)
    page.evaluate('scrollTo(0,0)')
    # tooltip e clique no ponto de uma empresa
    page.locator('#ea-map').scroll_into_view_if_needed()
    page.evaluate('window.EmpresasAtlas.mapa().setView([-18.15,-47.95],9,{animate:false});0')   # Catalão
    page.wait_for_timeout(700)
    xy = page.evaluate("window.EmpresasAtlas.telaEmpresa('26108898')")
    caixa = page.locator('#ea-map').bounding_box()
    page.mouse.move(caixa['x'] + xy[0], caixa['y'] + xy[1])
    page.wait_for_timeout(500)
    tip = page.inner_text('#ea-map .leaflet-tooltip.ea-tip') if page.locator('#ea-map .leaflet-tooltip.ea-tip').count() else ''
    check('Passar o mouse no ponto da empresa: nome, métrica e "não é a mina"', 'CMOC' in tip and 'não a sede nem a mina' in tip, tip[:160])
    clicar_no_mapa(page, xy)
    escolher_no_popup(page, '26108898')
    check('Clique no ponto da empresa seleciona a empresa (modo Empresas)', sel(page) == '26108898', sel(page))
    card = page.inner_text('#ea-resumo') if page.is_visible('#ea-resumo') else ''
    check('Cartão da seleção sobre o mapa: nome, onde atua, minerais, CFEM, processos, dados e "Abrir o dossiê"',
          'CMOC' in card and 'Catalão' in card and 'Nióbio' in card and 'CFEM 2022–2025' in card and 'Processos ANM' in card
          and 'Prod. estimada' in card and page.is_visible('#ea-resumo [data-ir="dossie"]'), card.replace('\n', ' ')[:200])
    check('Empresa selecionada destacada na lista', page.locator('#ea-lista .ea-item.on').count() == 1
          and 'CMOC' in page.locator('#ea-lista .ea-item.on').inner_text())
    c_, m_ = bbox(page, '#ea-resumo'), bbox(page, '#ea-map')
    check('O cartão ocupa menos de um quinto do mapa', c_['width'] * c_['height'] < 0.2 * m_['width'] * m_['height'],
          f"{c_['width'] * c_['height'] / (m_['width'] * m_['height']):.0%}")
    page.screenshot(path=str(CAPT / '02_explorar_empresa_selecionada.png'))

    # ================================================================ 3. modos Processos e Projetos preservam filtros e seleção
    filtros(page)
    page.select_option('#ea-mun', label='Catalão')
    page.wait_for_timeout(500)
    n_mun = page.evaluate('window.EmpresasAtlas.totais()')['empresas']
    page.click('#ea-modos [data-modo="processos"]')
    page.wait_for_timeout(800)
    check('Trocar para Processos preserva o filtro e a empresa', page.evaluate('window.EmpresasAtlas.totais()')['empresas'] == n_mun and sel(page) == '26108898'
          and page.input_value('#ea-mun') != '')
    page.click('#ea-modos [data-modo="projetos"]')
    page.wait_for_timeout(800)
    check('Trocar para Projetos preserva o filtro e a empresa', sel(page) == '26108898' and page.input_value('#ea-mun') != ''
          and 'projetos no recorte' in page.inner_text('#ea-lista-titulo'))
    page.screenshot(path=str(CAPT / '03_explorar_projetos_catalao.png'))
    limpar(page)
    proj = page.evaluate('window.EmpresasAtlas.projetos()')
    loc = ATLAS['meta']['cobertura']['projetos_localizacao']
    check('Projetos: lista inclui os sem localização, o mapa só desenha os localizados', proj['recorte'] == len(ATLAS['projetos'])
          and proj['comLocal'] == loc['p'] + loc['m'], proj)
    sub = page.inner_text('#ea-lista-sub')
    check('Projetos: a lista diz quantos estão no processo, no município e sem localização', str(loc['sem']) in sub and 'sem localização' in sub, sub)
    t_proj = mediana_redesenho(page)
    check('Redesenho do modo Projetos abaixo de 50 ms', t_proj < 50, f'{t_proj:.1f} ms')
    # projeto na referência do município (Chapada, Alto Horizonte) e projeto no centroide de processo
    page.evaluate("(()=>{const p=window.EmpresasAtlas.telaProjeto('GO-001');window.EmpresasAtlas.mapa().setView([p[2],p[3]],10,{animate:false})})()")
    page.wait_for_timeout(700)
    xy = page.evaluate("window.EmpresasAtlas.telaProjeto('GO-001')")
    clicar_no_mapa(page, xy[:2])
    if page.locator('.leaflet-popup .ea-pop [data-j]').count():
        for b in page.locator('.leaflet-popup .ea-pop [data-j]').all():
            if 'Chapada' in b.inner_text():
                b.click()
                break
        page.wait_for_timeout(700)
    pop = page.inner_text('.leaflet-popup') if page.locator('.leaflet-popup').count() else ''
    check('Projeto no município: balão diz "referência do município (aproximada)" e seleciona a empresa',
          'Chapada' in pop and 'município' in pop and sel(page) == '86902053', (pop[:160], sel(page)))
    page.locator('.ea-map-panel').screenshot(path=str(CAPT / '04_projeto_referencia_municipio.png'))
    page.keyboard.press('Escape')
    xy = page.evaluate("window.EmpresasAtlas.telaProjeto('RD-GO-0003')")
    page.evaluate("(()=>{const p=window.EmpresasAtlas.telaProjeto('RD-GO-0003');window.EmpresasAtlas.mapa().setView([p[2],p[3]],12,{animate:false})})()")
    page.wait_for_timeout(700)
    xy = page.evaluate("window.EmpresasAtlas.telaProjeto('RD-GO-0003')")
    clicar_no_mapa(page, xy[:2])
    if page.locator('.leaflet-popup .ea-pop [data-j]').count():
        page.locator('.leaflet-popup .ea-pop [data-j]').first.click()
        page.wait_for_timeout(700)
    pop = page.inner_text('.leaflet-popup') if page.locator('.leaflet-popup').count() else ''
    check('Projeto com processo citado: balão diz "centroide do processo citado (indicativo)"', 'processo citado' in pop, pop[:160])
    page.keyboard.press('Escape')

    # ================================================================ 4. Processos: pontos, hierarquia, legenda, navegação, polígonos
    page.click('#ea-modos [data-modo="processos"]')
    page.click('#ea-map .ea-ctl [data-a="go"]')
    page.wait_for_timeout(900)
    page.keyboard.press('Escape')   # sem empresa: tudo colorido
    page.wait_for_timeout(300)
    if sel(page):
        page.click('#ea-resumo .ea-card-x')
    page.wait_for_function('window.EmpresasAtlas.pontosNaTela()>5000', timeout=15000)
    t_proc = mediana_redesenho(page)
    check('Modo Processos: redesenho de todos os pontos do estado abaixo de 50 ms', t_proc < 50, f'{t_proc:.1f} ms')
    rl, rp = page.evaluate('[window.EmpresasAtlas.raioFase(0), window.EmpresasAtlas.raioFase(2)]')
    check('Hierarquia: ponto de lavra autorizada maior que o de pesquisa', rl > rp * 1.5, f'{rl:.1f} × {rp:.1f} px')
    antes = page.evaluate('window.EmpresasAtlas.pontosNaTela()')
    page.click('#ea-legenda .ea-fase[data-g="2"]')
    page.wait_for_timeout(400)
    sem = page.evaluate('window.EmpresasAtlas.pontosNaTela()')
    check('Legenda: clicar em Pesquisa esconde os pontos de pesquisa', sem < antes - 5000, f'{antes} → {sem}')
    page.click('#ea-legenda .ea-fase[data-g="2"]')
    page.wait_for_timeout(400)
    page.locator('#ea-map').scroll_into_view_if_needed()
    caixa = page.locator('#ea-map').bounding_box()
    cx, cy = caixa['x'] + caixa['width'] / 2, caixa['y'] + caixa['height'] / 2
    z0 = page.evaluate('window.EmpresasAtlas.mapa().getZoom()')
    page.mouse.move(cx, cy)
    page.mouse.wheel(0, -100)
    page.wait_for_timeout(900)
    check('Um dente da roda aproxima 1 nível', page.evaluate('window.EmpresasAtlas.mapa().getZoom()') - z0 >= 1)
    # arrastos dentro da janela (um mouseup fora dela não chega à página e deixaria o arrasto "preso")
    for _ in range(4):
        page.mouse.move(cx - 300, cy - 180)
        page.mouse.down()
        page.mouse.move(cx + 300, cy + 180, steps=10)
        page.mouse.up()
        page.wait_for_timeout(300)
    page.wait_for_timeout(1200)
    centro = page.evaluate('(()=>{const c=window.EmpresasAtlas.mapa().getCenter();return [c.lat,c.lng]})()')
    lim = page.evaluate('window.EmpresasAtlas.limites()')
    check('Arrastar não leva o mapa para fora de Goiás', lim[0] - .01 <= centro[0] <= lim[2] + .01 and lim[1] - .01 <= centro[1] <= lim[3] + .01, centro)
    clicar_processo_no_mapa(page, '861427/2010')   # lavra da Serra Verde, em Minaçu
    escolher_processo(page, '861427/2010')
    check('Clique num processo seleciona o processo exato (cartão do processo), sem trocar a empresa e sem mudar o zoom',
          proc_foco(page) == '861427/2010' and sel(page) is None and page.evaluate('window.EmpresasAtlas.mapa().getZoom()') == 13
          and 'SERRA VERDE' in page.inner_text('#ea-resumo').upper(), (proc_foco(page), sel(page)))
    page.wait_for_timeout(2500)   # polígonos sob demanda
    t13 = mediana_redesenho(page)
    check('Zoom 13 com polígonos: redesenho abaixo de 50 ms e menos de 30 camadas Leaflet', t13 < 50 and page.evaluate('Object.keys(window.EmpresasAtlas.mapa()._layers).length') < 30, f'{t13:.1f} ms')
    page.locator('.ea-map-panel').screenshot(path=str(CAPT / '05_processos_poligonos_serra_verde.png'))
    clicar_processo_no_mapa(page, '861427/2010')
    check('Desmarcar: clicar de novo no processo destacado', proc_foco(page) is None)
    clicar_processo_no_mapa(page, '861427/2010')
    escolher_processo(page, '861427/2010')
    page.keyboard.press('Escape')
    page.wait_for_timeout(400)
    check('Desmarcar: Esc', proc_foco(page) is None)
    clicar_processo_no_mapa(page, '861427/2010')
    escolher_processo(page, '861427/2010')
    page.click('#ea-resumo .ea-card-x')
    page.wait_for_timeout(400)
    check('Desmarcar: × do cartão da seleção', proc_foco(page) is None and page.is_hidden('#ea-resumo'))
    clicar_processo_no_mapa(page, '861427/2010')
    escolher_processo(page, '861427/2010')
    page.evaluate('window.EmpresasAtlas.mapa().setView([-16.2,-50.6],9,{animate:false});0')
    page.wait_for_timeout(700)
    vazio = page.evaluate('window.EmpresasAtlas.pontoVazio()')
    if vazio:
        clicar_no_mapa(page, vazio)
    # desde a auditoria crítica, o fundo livre de Goiás seleciona o município (clique direto): o processo sai do foco e o município vira recorte
    check('Clique numa área livre de Goiás: o processo sai do foco e o município do ponto vira o recorte', bool(vazio) and proc_foco(page) is None
          and page.evaluate('window.EmpresasAtlas.municipio()') is not None, vazio)
    limpar(page)

    # ================================================================ 5. busca: nome, CNPJ, município, mineral, processo
    page.click('#ea-busca')
    page.keyboard.type('cmoc', delay=40)
    page.wait_for_selector('#ea-sugestoes:not([hidden]) li[data-j]', timeout=5000)
    check('Busca por nome: autocomplete e lista filtrando enquanto digita', 'CMOC' in page.inner_text('#ea-sugestoes') and page.locator('#ea-lista .ea-item').count() == 1)
    page.keyboard.press('ArrowDown')
    page.keyboard.press('Enter')
    page.wait_for_timeout(700)
    check('Busca por nome (teclado) seleciona a empresa e grava a URL', sel(page) == '26108898' and page.url.endswith('#empresas/explorar/26108898'), page.url)
    page.fill('#ea-busca', '42.184.226')
    page.wait_for_timeout(400)
    page.keyboard.press('Enter')
    page.wait_for_timeout(700)
    check('Busca por CNPJ formatado', sel(page) == '42184226', sel(page))
    page.fill('#ea-busca', 'catalão')
    page.wait_for_timeout(400)
    page.locator('#ea-sugestoes li[data-j]', has_text='Município').first.dispatch_event('mousedown')
    page.wait_for_timeout(700)
    check('Busca por município vira recorte (código IBGE) e enquadra o município', page.locator('#ea-mun option:checked').inner_text() == 'Catalão'
          and (page.evaluate('window.EmpresasAtlas.municipio()') or {}).get('ibge') == '5205109' and page.evaluate('window.EmpresasAtlas.mapa().getZoom()') >= 8.5)
    limpar(page)
    page.fill('#ea-busca', 'nióbio')
    page.wait_for_timeout(400)
    page.locator('#ea-sugestoes li[data-j]', has_text='Mineral').first.dispatch_event('mousedown')
    page.wait_for_timeout(600)
    check('Busca por mineral vira filtro', 'Nióbio' in page.locator('#ea-min option:checked').inner_text() and page.evaluate('window.EmpresasAtlas.totais()')['empresas'] < 100)
    limpar(page)
    page.fill('#ea-busca', '861427/2010')
    page.wait_for_timeout(400)
    page.keyboard.press('Enter')
    page.wait_for_timeout(1500)
    check('Busca por processo: modo Processos e o próprio processo em foco (a empresa selecionada não muda)', page.evaluate('window.EmpresasAtlas.modo()') == 'processos'
          and proc_foco(page) == '861427/2010' and sel(page) == '42184226', (proc_foco(page), sel(page)))
    page.fill('#ea-busca', 'mosaic fert')
    page.keyboard.press('Enter')
    page.wait_for_timeout(700)
    check('Enter imediato após digitar escolhe a empresa', sel(page) == '33931486', sel(page))
    page.go_back()
    page.wait_for_timeout(900)
    check('Voltar do navegador restaura a empresa anterior (e o processo que estava em foco)', sel(page) == '42184226' and proc_foco(page) == '861427/2010',
          (sel(page), proc_foco(page)))

    # ================================================================ 6. empresas com muitos processos e filtros combinados
    limpar(page)
    page.select_option('#ea-metrica', 'processos')
    page.wait_for_timeout(500)
    topo = page.locator('#ea-lista .ea-item').first.get_attribute('data-i')
    page.locator('#ea-lista .ea-item').first.click()
    page.wait_for_timeout(1500)
    e_top = next(e for e in ATLAS['empresas'] if str(e['i']) == topo)
    check('Empresa com mais processos: seleciona e desenha os processos dela', sel(page) == e_top['cnpj'] and e_top['n'] > 150, f"{e_top['nome']} · {e_top['n']}")
    area(page, 'dossie')
    page.click('#ea-tab-territorio')
    page.wait_for_timeout(400)
    check('Dossiê de empresa com centenas de processos pagina a tabela', page.locator('#ea-corpo .ea-pag').count() == 1 and str(e_top['n']) in page.inner_text('#ea-corpo').replace('.', ''))
    area(page, 'explorar')
    page.select_option('#ea-metrica', 'cfem')
    filtros(page)
    page.select_option('#ea-mun', label='Catalão')
    page.select_option('#ea-min', label='Fosfato')
    page.select_option('#ea-grupo', 'lavra_autorizada')
    page.wait_for_timeout(500)
    check('Filtros combinados (município + mineral + fase) reduzem lista e indicadores', 'MOSAIC' in page.inner_text('#ea-lista') and page.evaluate('window.EmpresasAtlas.totais()')['empresas'] < 10)
    page.select_option('#ea-dado', 'crit_est')
    page.wait_for_timeout(400)
    check('Quatro filtros ativos: quatro etiquetas removíveis', page.locator('#ea-context [data-limpa]').count() == 4)
    limpar(page)
    page.click('#ea-filtros-btn')
    check('Limpar filtros volta ao universo inteiro', page.evaluate('window.EmpresasAtlas.totais()')['empresas'] == ATLAS['meta']['cobertura']['empresas_indice'])

    # ================================================================ 7. dossiê da CMOC (6 seções + resumo executivo)
    page.evaluate("window.EmpresasAtlas.selecionarCnpj('26108898')")
    page.wait_for_timeout(500)
    page.click('#ea-resumo [data-ir="dossie"]')
    page.wait_for_timeout(500)
    check('"Abrir o dossiê" do cartão abre o dossiê da empresa', page.evaluate('window.EmpresasAtlas.area()') == 'dossie' and 'CMOC' in page.inner_text('#ea-ficha-titulo'))
    fatos, dados = page.inner_text('#ea-ficha-fatos'), page.inner_text('#ea-ficha-dados')
    check('Dossiê: cabeçalho com municípios, minerais, processos por fase e situação dos dados', 'Catalão' in fatos and 'Nióbio' in fatos and 'Lavra autorizada' in fatos
          and 'CFEM' in dados and 'Prod. declarada' in dados, (fatos.replace('\n', ' ')[:120], dados.replace('\n', ' ')[:120]))
    kp = page.inner_text('#ea-kpis')
    check('Dossiê: números de abertura com período (CFEM, processos, CCEE, estimada, declarada)',
          'CFEM 2022–2025' in kp and 'Produção estimada' in kp and 'Produção declarada' in kp and 'AMB × CFEM' in kp, kp[:200])
    corpos = {}
    for aba in ['perfil', 'territorio', 'economia', 'projetos', 'noticias', 'historico']:
        page.click(f'#ea-tab-{aba}')
        page.wait_for_timeout(300)
        corpos[aba] = page.inner_text('#ea-corpo')
        page.locator('#ea-ficha').screenshot(path=str(CAPT / f'06_dossie_cmoc_{aba}.png'))
    check('Perfil: CNPJ raiz, grupo, distinção titular × grupo × operação e minerais críticos', '26.108.898' in corpos['perfil'] and 'CMOC Group' in corpos['perfil']
          and 'Grupo econômico' in corpos['perfil'] and 'CRÍTICO (GO)' in corpos['perfil'].upper())
    check('Território: operação documentada × indícios de atividade × direitos, e a tabela de processos', 'OPERAÇÃO DOCUMENTADA' in corpos['territorio'].upper()
          and 'INDÍCIOS DE ATIVIDADE' in corpos['territorio'].upper() and 'DIREITOS E INTENÇÕES' in corpos['territorio'].upper())
    eco = corpos['economia']
    check('Economia: CFEM, carga CCEE com meses, estimada e declarada no mesmo resumo, sem somar',
          'meses observados' in eco and 'Produção estimada (AMB × CFEM)' in eco and 'Produção declarada' in eco and 'não se somam' in eco)
    check('Economia: sem o painel inferior duplicado (nenhum gráfico de energia repetido)', page.locator('#ea-area-dossie #ep-energia').count() == 0
          and page.locator('#empresas-view #ep-energia').count() == 1)
    check('Projetos: maturidade, vínculo, confiança e localização', 'Confiança' in corpos['projetos'] and ('Processo ANM' in corpos['projetos'] or 'Município' in corpos['projetos']))
    check('Notícias: data, veículo e método de vínculo', 'contexto de Goiás' in corpos['noticias'] or 'Nome da empresa' in corpos['noticias'])
    check('Histórico: série anual com estimada separada da declarada', 'PRODUÇÃO ESTIMADA (AMB × CFEM)' in corpos['historico'].upper() and 'MWh' in corpos['historico'])
    page.click('#ea-tab-economia')
    page.locator('#ea-corpo [data-anal="estimada"]').first.click()
    page.wait_for_timeout(700)
    check('"Aprofundar" leva à análise com a empresa no escopo', page.evaluate('window.EmpresasAtlas.area()') == 'analises'
          and page.evaluate('window.EmpresasAtlas.analise()') == 'estimada' and page.evaluate('window.EmpresasAtlas.escopo()') == 'empresa')

    # ================================================================ 8. Análises: produção estimada (AMB × CFEM)
    linhas_cmoc = page.locator('#es-tabela tbody tr').count()
    esperadas = len([r for r in EST['linhas'] if r[EC['cnpj_raiz']] == '26108898' and r[EC['ano']] == max(x[EC['ano']] for x in EST['linhas'] if x[EC['cnpj_raiz']] == '26108898')])
    check('Estimada · empresa: só a CMOC, último ano, todas as bases (nióbio contido incluído)', linhas_cmoc == esperadas and 'Nióbio' in page.inner_text('#es-tabela')
          and 'CMOC' in page.inner_text('#es-context'), f'{linhas_cmoc} × {esperadas}')
    sint = page.inner_text('#es-sintese')
    check('Estimada: síntese numa frase (empresa, mineral, toneladas, parcela do estado, "não observada")', 'CMOC' in sint and ' t ' in sint + ' ' and '%' in sint
          and 'não produção observada' in sint, sint[:200])
    check('Três níveis: a metodologia e as tabelas de apoio ficam no detalhamento, fechadas', page.is_hidden('#es-nota') and page.is_hidden('#es-publicado')
          and page.is_visible('#es-tabela'))
    page.screenshot(path=str(CAPT / '07_analise_estimada_cmoc.png'), full_page=True)
    page.click('#ea-escopo [data-escopo="todas"]')
    page.wait_for_timeout(600)
    cnt = page.inner_text('#es-count')
    check('Estimada · todas: recorte padrão (2025, beneficiada) com a contagem do pacote', str(len(EST_2025_BEN)) in cnt.replace('.', ''), cnt)
    cf_txt = page.inner_text('#es-metrics')
    cf_esperada = sum(r[EC['cfem_brl']] or 0 for r in EST_2025_BEN if not r[EC['minerio_de_outro_mineral']])
    check('Conferência: CFEM do recorte estimado = soma do pacote (uma vez por empresa, mineral e ano)',
          f"{round(cf_esperada):,}".replace(',', '.') in cf_txt, (round(cf_esperada), cf_txt[:300]))
    page.click('#es-tabela [data-es-pag="1"]')
    page.wait_for_timeout(300)
    check('Estimada: tabela paginada (25 por página), sem página interminável', page.locator('#es-tabela tbody tr').count() == 25
          and '26–50' in page.inner_text('#es-count'), page.inner_text('#es-count'))
    page.select_option('#es-min', 'Ouro')
    page.wait_for_timeout(500)
    check('Estimada: mudar o mineral redesenha barras em toneladas do mineral', 'Ouro' in page.inner_text('#es-barrasT') and ' t' in page.inner_text('#es-barras'))
    page.select_option('#es-ano', '2023')
    page.select_option('#es-base', 'ROM')
    page.wait_for_timeout(500)
    check('Estimada: mudar ano e base', '2023' in page.inner_text('#es-context') and 'ROM' in page.inner_text('#es-tabela'))
    page.select_option('#es-base', '')
    page.wait_for_timeout(400)
    barras = page.locator('#es-barras .bar-row').count()
    check('Estimada: com "Todas as bases" cada empresa aparece uma vez (ROM e beneficiada não se somam)', barras == len(set(page.locator('#es-barras .bar-label').all_inner_texts())), barras)
    with page.expect_download() as d:
        page.click('#es-export')
    csv_est = Path(d.value.path()).read_text(encoding='utf-8-sig')
    # ajustes finais: o aviso de estimativa vai numa coluna (natureza), e o cabeçalho é a 1ª linha
    check('Estimada: exportação CSV com aviso de estimativa e colunas da fonte', csv_est.startswith('ano;mineral;base;') and 'natureza' in csv_est.splitlines()[0]
          and 'não produção observada' in csv_est and 'parcela_do_estado' in csv_est)
    page.click('#es-detalhe [data-det="publicado"]')
    page.wait_for_timeout(200)
    pub_ok = page.is_visible('#es-publicado') and page.locator('#es-publicado table, #es-publicado .mk-note').count() > 0
    page.click('.ea-ressalva [data-det-ir="es:metodo"]')
    page.wait_for_timeout(500)
    check('Estimada: comparação com o publicado e "Como se calcula" abrem o detalhamento certo', pub_ok and page.is_visible('#es-nota')
          and 'Anuário Mineral' in page.inner_text('#es-nota') and 'Correção' in page.inner_text('#es-fontes'))
    page.click('#es-detalhe [data-det="tabela"]')
    page.click('#es-reset')

    # ================================================================ 9. Análises: produção declarada e energia (o defeito do painel antigo)
    analise(page, 'declarada')
    check('Declarada · todas: as linhas das 10 empresas', page.locator('#ep-tabela tbody tr').count() == len(BASE_EMP['linhas']))
    check('Declarada: síntese numa frase e ressalva CCEE × consumo da operação', 'empresas declaram produção' in page.inner_text('#ep-sintese')
          and 'não é o consumo medido de uma mina' in page.inner_text('#ea-anal-declarada .ea-ressalva'))
    page.evaluate("window.EmpresasAtlas.selecionarCnpj('26108898')")
    page.wait_for_timeout(600)
    n_cmoc = len([l for l in BASE_EMP['linhas'] if l['cnpj_raiz'] == '26108898'])
    check('Declarada · empresa entre as 10: só as linhas dela', page.locator('#ep-tabela tbody tr').count() == n_cmoc and page.is_hidden('#ep-indisp'))
    page.evaluate("window.EmpresasAtlas.selecionarCnpj('00057240')")   # Ciplan: CFEM e títulos, sem produção declarada
    page.wait_for_timeout(600)
    check('Declarada · empresa fora das 10: "Dados não disponíveis para esta empresa"', page.is_visible('#ep-indisp') and 'Dados não disponíveis' in page.inner_text('#ep-indisp'))
    check('Declarada · empresa fora das 10: NÃO volta a mostrar todas as empresas', page.is_hidden('#empresas-content')
          and page.locator('#ep-tabela tbody tr').count() == 0, page.locator('#ep-tabela tbody tr').count())
    check('Declarada · empresa fora das 10: mostra CFEM e títulos da empresa', 'CFEM 2022–2026' in page.inner_text('#ep-indisp') and 'Títulos ANM' in page.inner_text('#ep-indisp'))
    page.screenshot(path=str(CAPT / '08_declarada_empresa_fora_das_10.png'), full_page=True)
    analise(page, 'estimada')
    check('Estimada · Ciplan: só linhas da Ciplan', set(page.locator('#es-tabela tbody td:nth-child(5)').all_inner_texts()) == {'00057240'})
    page.evaluate("window.EmpresasAtlas.selecionarCnpj('36784717')")   # empresa com CFEM e títulos, fora da divisão AMB × CFEM
    page.wait_for_timeout(600)
    check('Estimada · empresa sem estimativa: aviso, sem agregado', page.is_visible('#es-indisp') and page.is_hidden('#es-content'))
    analise(page, 'declarada')
    page.click('#ep-indisp [data-todas]')
    page.wait_for_timeout(500)
    check('"Ver as 10 empresas" troca o escopo para todas de forma explícita', page.evaluate('window.EmpresasAtlas.escopo()') == 'todas'
          and page.locator('#ep-tabela tbody tr').count() == len(BASE_EMP['linhas']))
    page.select_option('#ep-qual', 'observado_completo')
    page.wait_for_timeout(300)
    check('Declarada: filtro de qualidade', 0 < page.locator('#ep-tabela tbody tr').count() < len(BASE_EMP['linhas']))
    page.click('#ep-reset')
    with page.expect_download() as d:
        page.click('#ep-export')
    check('Declarada: exportação CSV', 'coeficiente_unidade' in Path(d.value.path()).read_text(encoding='utf-8-sig'))

    # ================================================================ 10. Análises: arrecadação, títulos e consumo
    page.evaluate("window.EmpresasAtlas.selecionarCnpj('26108898')")
    analise(page, 'direitos')
    page.wait_for_selector('#epn-content:not([hidden])', timeout=40000)
    page.wait_for_timeout(2500)
    check('Arrecadação · empresa: CFEM mensal, por mineral e por município da CMOC', page.locator('#epn-c-cfem_mes .pn-out svg').count() == 1
          and 'Catalão' in page.inner_text('#epn-c-mun_cfem') and 'CMOC' in page.inner_text('#epn-context'))
    pareto = page.locator('#epn-c-emp_lider .pill.scope-emp')
    check('Quadros que não filtram por empresa dizem "Todas as empresas"', pareto.count() == 1 and pareto.is_visible())
    page.select_option('#epn-y0', '2022')
    page.select_option('#epn-y1', '2025')
    page.wait_for_timeout(1200)
    tab = page.inner_text('#epn-c-emp_cfem')
    cmoc_22_25 = sum(r[4] for r in ATLAS['cfem']['rows'] if r[0] == next(e['i'] for e in ATLAS['empresas'] if e['cnpj'] == '26108898') and 2022 <= r[1] <= 2025)
    check('Conferência: CFEM 2022–2025 da CMOC igual no Panorama e no pacote do Atlas', f"{round(cmoc_22_25):,}".replace(',', '.') in tab.replace('R$', '').replace('\xa0', ' '),
          (round(cmoc_22_25), tab[-200:]))
    page.click('#epn-tabs [data-tab="emp_titulos"]')
    page.wait_for_timeout(1200)
    check('Títulos e processos por fase', page.locator('#epn-c-fases').is_visible() and page.locator('#epn-c-lavra_emp').is_visible())
    page.click('#epn-tabs [data-tab="emp_consumo"]')
    page.wait_for_timeout(1200)
    check('Consumo (CCEE) da empresa, com série mensal', page.locator('#epn-c-ee_mes').is_visible() and page.locator('#epn-c-ee_emp').is_visible())
    page.screenshot(path=str(CAPT / '09_direitos_consumo_cmoc.png'), full_page=True)
    page.click('#ea-escopo [data-escopo="todas"]')
    page.wait_for_timeout(1200)
    check('Arrecadação · todas as empresas: o filtro de titular por nome volta', page.is_visible('#epn-emp') and 'CMOC' not in page.inner_text('#epn-context'))

    # ================================================================ 11. comparação
    area(page, 'comparar')
    for termo in ('cmoc', 'mosaic fert', 'maraca'):
        page.fill('#ea-cmp-busca', termo)
        page.wait_for_timeout(400)
        page.keyboard.press('Enter')
        page.wait_for_timeout(500)
    cmp_txt = page.inner_text('#ea-cmp-corpo')
    check('Comparar três empresas lado a lado', len(page.evaluate('window.EmpresasAtlas.comparacao()')) == 3 and 'MOSAIC' in cmp_txt and 'MARACA' in cmp_txt)
    check('Comparação com grupos e unidades harmonizadas', all(g in cmp_txt.upper() for g in ('ARRECADAÇÃO (CFEM', 'CARGA DO AGENTE CCEE', 'PRODUÇÃO ESTIMADA AMB × CFEM (T)'))
          and 'não é o consumo medido de uma mina' in cmp_txt)
    with page.expect_download() as d:
        page.click('#ea-cmp-csv')
    check('Comparação: exportação CSV (formato longo, cabeçalho na 1ª linha)', Path(d.value.path()).read_text(encoding='utf-8-sig').startswith('empresa_ordem;cnpj_raiz;empresa;'))
    check('Comparação: três vagas com a empresa e o maior valor de cada linha em destaque', page.locator('#ea-cmp-slots .ea-slot:not(.vazio)').count() == 3
          and page.locator('#ea-cmp-corpo td.ea-max').count() > 5 and page.is_hidden('#ea-cmp-add-box'))
    page.locator('#ea-cmp').screenshot(path=str(CAPT / '10_comparacao.png'))
    page.locator('#ea-cmp-slots [data-cmp-rm]').first.click()
    page.wait_for_timeout(300)
    check('Tirar da comparação', len(page.evaluate('window.EmpresasAtlas.comparacao()')) == 2)

    # ================================================================ 12. exportações do Explorar e metodologia
    area(page, 'explorar')
    page.click('#ea-modos [data-modo="empresas"]')
    with page.expect_download() as d:
        page.click('#ea-exp-csv')
    csv_txt = Path(d.value.path()).read_text(encoding='utf-8-sig')
    check('Exportação CSV do ranking com o processo de referência do ponto', 'ponto_processo_referencia' in csv_txt and 'fase_mais_avancada' in csv_txt)
    with page.expect_download() as d:
        page.click('#ea-exp-json')
    js = json.loads(Path(d.value.path()).read_text(encoding='utf-8'))
    universo = page.evaluate('window.EmpresasAtlas.totais()')['empresas']
    check('Exportação JSON com recorte inteiro, ordem e regras (inclusive a do ponto da empresa)', 'ponto_empresa' in js['regras'] and len(js['empresas']) == universo
          and js['recorte']['ordem'] == 'cfem', (len(js['empresas']), universo))
    page.click('#ea-modos [data-modo="projetos"]')
    with page.expect_download() as d:
        page.click('#ea-exp-csv')
    check('Exportação CSV dos projetos com o tipo de localização', 'referencia_municipio' in Path(d.value.path()).read_text(encoding='utf-8-sig'))
    area(page, 'dossie')
    with page.expect_download() as d:
        page.click('#ea-ficha-exp')
    fj = json.loads(Path(d.value.path()).read_text(encoding='utf-8'))
    check('Exportação do dossiê (JSON) com processos, estimada e declarada', fj['empresa']['cnpj'] == '26108898' and len(fj['processos']) == 57
          and fj['producao_estimada_amb_cfem']['linhas'] and fj['producao_declarada_e_energia'])
    page.click('#ea-metodo summary')
    met = page.inner_text('#ea-metodo')
    check('Metodologia: base legal federal e estadual, ponto da empresa e estimativa', 'Resolução nº 2' in met and '23.597' in met and 'não a sede nem a mina' in met
          and 'Anuário Mineral' in met)

    # ================================================================ 13. troca de abas e dados protegidos
    page.click('[data-view="mapa"]')
    sair_da_barra(page)
    page.wait_for_timeout(1200)
    page.click('[data-view="empresas"]')
    sair_da_barra(page)
    page.wait_for_timeout(800)
    check('Sair e voltar não duplica o mapa nem perde a seleção', page.locator('#ea-map.leaflet-container').count() == 1 and sel(page) is not None)
    texto = page.inner_text('#empresas-view')
    check('Nenhum CPF na página', not re.search(r'\b\d{3}\.\d{3}\.\d{3}-\d{2}\b', texto))
    check('Console e rede sem erros nas jornadas', not erros_relevantes(ruido), erros_relevantes(ruido)[:6])
    ctx.close()

    # ================================================================ 14. dois usuários ao mesmo tempo
    ca, cb = nav.new_context(viewport={'width': 1280, 'height': 860}), nav.new_context(viewport={'width': 1280, 'height': 860})
    pa, pb = ca.new_page(), cb.new_page()
    login(pa, U1)
    login(pb, U2)
    abrir_empresas(pa)
    abrir_empresas(pb)
    pa.locator('#ea-lista .ea-item').nth(0).click()
    pb.locator('#ea-lista .ea-item').nth(3).click()
    pa.wait_for_timeout(600)
    check('Dois usuários ao mesmo tempo, seleções independentes', sel(pa) and sel(pb) and sel(pa) != sel(pb), f'{sel(pa)} / {sel(pb)}')
    ca.close()
    cb.close()

    # ================================================================ 15. falhas simuladas da API
    c3 = nav.new_context(viewport={'width': 1280, 'height': 860})
    p3 = c3.new_page()
    login(p3, U1)
    p3.route('**/api/empresas/atlas', lambda r: r.fulfill(status=500, body='{"detail":"Falha simulada no teste"}', content_type='application/json'))
    p3.click('[data-view="empresas"]')
    sair_da_barra(p3)
    p3.wait_for_selector('#ea-retry', timeout=10000)
    check('Falha do pacote do Atlas: erro e "Tentar de novo"', 'Falha simulada' in p3.inner_text('#ea-error'))
    p3.unroute('**/api/empresas/atlas')
    p3.click('#ea-retry')
    p3.wait_for_selector('#ea-content:not([hidden])', timeout=30000)
    check('"Tentar de novo" recupera a aba', p3.is_visible('#ea-map'))
    c3.close()
    c4 = nav.new_context(viewport={'width': 1280, 'height': 860})
    p4 = c4.new_page()
    login(p4, U1)
    p4.route('**/api/empresas', lambda r: r.fulfill(status=503, body='{"detail":"Análises indisponíveis (teste)"}', content_type='application/json'))
    abrir_empresas(p4)
    p4.click('#ea-nav-analises')
    p4.wait_for_timeout(800)
    check('Falha só das análises: Explorar funciona e a análise mostra erro com "Tentar de novo"', p4.locator('#ea-lista .ea-item').count() > 0
          and 'indisponíveis' in p4.inner_text('#es-error') and p4.locator('#es-error button').count() == 1)
    p4.unroute('**/api/empresas')
    p4.click('#es-error button')
    p4.wait_for_selector('#es-content:not([hidden])', timeout=20000)
    check('Análises recuperadas pelo "Tentar de novo"', p4.locator('#es-tabela tbody tr').count() > 0)
    c4.close()
    # o pacote do Panorama é carregado uma vez e compartilhado pelas duas instâncias: a falha é simulada antes do login
    c7 = nav.new_context(viewport={'width': 1280, 'height': 860})
    p7 = c7.new_page()
    p7.route('**/api/panorama', lambda r: r.fulfill(status=500, body='{"detail":"Panorama fora (teste)"}', content_type='application/json'))
    login(p7, U1)
    abrir_empresas(p7)
    p7.click('#ea-nav-analises')
    p7.click('#ea-anal-tab-direitos')
    p7.wait_for_timeout(1500)
    check('Falha do Panorama: erro só em "Arrecadação, títulos e consumo"; Explorar segue',
          'Panorama fora' in p7.inner_text('#epn-error') and p7.locator('#ea-lista .ea-item').count() > 0)
    p7.click('#ea-anal-tab-estimada')
    p7.wait_for_timeout(500)
    check('… e a produção estimada continua funcionando', p7.locator('#es-tabela tbody tr').count() > 0)
    c7.close()

    # ================================================================ 16. inglês
    c5 = nav.new_context(viewport={'width': 1440, 'height': 900})
    p5 = c5.new_page()
    login(p5, U1)
    p5.goto(BASE + '/painel.html?lang=en#empresas/analises')
    p5.wait_for_selector('#ea-content:not([hidden])', timeout=40000)
    p5.wait_for_timeout(1200)
    check('Inglês: título, áreas e análise', 'Companies' in p5.inner_text('#empresas-view h1') and 'Explore companies' in p5.inner_text('#ea-nav')
          and 'Estimated production' in p5.inner_text('#ea-anal-nav'))
    p5.screenshot(path=str(CAPT / '11_empresas_en_analises.png'))
    p5.evaluate("localStorage.setItem('minera-lang','pt')")
    c5.close()

    # ================================================================ 17. celular
    c6 = nav.new_context(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True, device_scale_factor=2)
    p6 = c6.new_page()
    login(p6, U1)
    abrir_empresas(p6)
    ok, w = sem_rolagem_horizontal(p6)
    check('Celular (390 px): Explorar sem rolagem horizontal', ok, w)
    p6.screenshot(path=str(CAPT / '12_celular_explorar.png'))
    check('Celular: busca e modos do mapa à vista, lista fechada numa gaveta', p6.is_visible('#ea-busca') and p6.is_visible('#ea-modos')
          and p6.is_visible('#ea-lista-btn') and not p6.locator('#ea-lateral.aberta').count())
    p6.click('#ea-lista-btn')
    p6.wait_for_timeout(500)
    check('Celular: a gaveta abre a lista e os filtros por cima do mapa', p6.locator('#ea-lateral.aberta').count() == 1 and p6.is_visible('#ea-lista .ea-item >> nth=0'))
    p6.screenshot(path=str(CAPT / '12b_celular_gaveta.png'))
    p6.locator('#ea-lista .ea-item').nth(0).click()
    p6.wait_for_timeout(1000)
    check('Celular: escolher na lista fecha a gaveta e mostra o cartão compacto', not p6.locator('#ea-lateral.aberta').count() and p6.is_visible('#ea-resumo'))
    p6.screenshot(path=str(CAPT / '12c_celular_cartao.png'))
    for a_ in ('dossie', 'analises', 'comparar'):
        p6.click(f'#ea-nav-{a_}')
        p6.wait_for_timeout(900)
        ok, w = sem_rolagem_horizontal(p6)
        check(f'Celular: área {a_} sem rolagem horizontal', ok, w)
        if a_ == 'dossie':
            check('Celular: as seis seções do dossiê rolam de lado, com a borda esmaecida como pista',
                  p6.evaluate("(()=>{const a=document.getElementById('ea-abas');return a.classList.contains('ea-rola')&&a.scrollWidth>a.clientWidth})()"))
        p6.screenshot(path=str(CAPT / f'13_celular_{a_}.png'))
    c6.close()

    # ================================================================ 18. tablet (768 px)
    c8 = nav.new_context(viewport={'width': 768, 'height': 1024})
    p8 = c8.new_page()
    login(p8, U1)
    abrir_empresas(p8)
    m8 = bbox(p8, '#ea-map')
    check('Tablet (768 px): mapa na largura toda, lista em gaveta, sem rolagem horizontal', m8['width'] > 560 and p8.is_visible('#ea-lista-btn')
          and sem_rolagem_horizontal(p8)[0], round(m8['width']))
    p8.evaluate("window.EmpresasAtlas.selecionarCnpj('26108898')")
    for a_ in ('dossie', 'analises', 'comparar'):
        p8.click(f'#ea-nav-{a_}')
        p8.wait_for_timeout(800)
        ok, w = sem_rolagem_horizontal(p8)
        check(f'Tablet: área {a_} sem rolagem horizontal', ok, w)
    c8.close()

    # ================================================================ 19. auditoria de consultoria: comparação, exportações e navegação
    # Casos da auditoria final (26/11/2026), com os arquivos efetivamente baixados (guardados em --baixados para o Excel e o pandas).
    POR = {e['cnpj']: e for e in ATLAS['empresas']}
    c9 = nav.new_context(viewport={'width': 1440, 'height': 900}, accept_downloads=True, locale='pt-BR')
    p9 = c9.new_page()
    ruido9 = observar(p9)
    login(p9, U1)
    abrir_empresas(p9)
    p9.wait_for_function('window.EmpresasAnalises&&window.EmpresasAnalises.pronto()', timeout=30000)
    area_ = lambda pg: pg.evaluate('window.EmpresasAtlas.area()')
    cmp_ = lambda pg: pg.evaluate('window.EmpresasAtlas.comparacao()')
    enq = lambda pg: pg.evaluate('(()=>{const m=window.EmpresasAtlas.mapa(),c=m.getCenter();return [m.getZoom(),+c.lat.toFixed(6),+c.lng.toFixed(6)]})()')

    # 19a. CMOC com o filtro Fosfato: o arquivo tem os números da tela, com as fases do recorte
    filtros(p9)
    p9.select_option('#ea-min', label='Fosfato')
    p9.wait_for_timeout(700)
    p9.evaluate("window.EmpresasAtlas.selecionarCnpj('26108898')")
    p9.wait_for_timeout(700)
    check('Auditoria · cartão com filtro: diz como a selecionada fica no recorte', 'No recorte filtrado: 7 processos' in p9.inner_text('#ea-resumo'),
          p9.inner_text('#ea-resumo')[:300])
    tot = p9.evaluate('window.EmpresasAtlas.totais()')
    cab, ls = ler_csv(baixar(p9, '#ea-exp-csv', BAIX))
    cmoc = next((l for l in ls if l['cnpj_raiz'] == '26108898'), None)
    check('Auditoria · CSV do recorte: BOM, ";" e cabeçalho na 1ª linha (sem linha de comentário)', cab.startswith('posicao;posicao_cfem;cnpj_raiz;empresa;'), cab[:80])
    check('Auditoria · CMOC + Fosfato: 7 processos e 0 lavras no recorte; as 5 lavras (nióbio) só no total da empresa, rotulado',
          bool(cmoc) and cmoc['processos_no_recorte'] == '7' and cmoc['lavra_autorizada_no_recorte'] == '0' and cmoc['lavra_autorizada_empresa_total'] == '5'
          and cmoc['processos_empresa_total'] == '57' and cmoc['filtro_mineral'] == 'Fosfato',
          cmoc and {k: cmoc[k] for k in ('processos_no_recorte', 'lavra_autorizada_no_recorte', 'lavra_autorizada_empresa_total', 'processos_empresa_total')})
    check('Auditoria · arquivo = tela: empresas, processos e CFEM do recorte', len(ls) == tot['empresas'] and sum(int(l['processos_no_recorte']) for l in ls) == tot['processos']
          and abs(sum(numero(l['cfem_periodo_rs']) or 0 for l in ls) - tot['cfem']) < 1, (len(ls), tot))
    ab = ler_xlsx(baixar(p9, '#ea-exp-xlsx', BAIX))
    xc = next((l for l in ab.get('Empresas', []) if l.get('cnpj_raiz') == '26108898'), None)
    check('Auditoria · Excel do recorte: abas Empresas, Colunas e Metadados; números como número',
          list(ab) == ['Empresas', 'Colunas', 'Metadados'] and bool(xc) and xc['processos_no_recorte'] == 7.0 and xc['lavra_autorizada_no_recorte'] == 0.0
          and isinstance(xc['cfem_periodo_rs'], float) and len(ab['Empresas']) == len(ls), list(ab))
    zeros = [l for l in ab['Empresas'] if l['cnpj_raiz'].startswith('0')]
    check('Auditoria · Excel: CNPJ raiz como texto, com o zero à esquerda', bool(zeros) and all(isinstance(l['cnpj_raiz'], str) and len(l['cnpj_raiz']) == 8 for l in ab['Empresas']),
          len(zeros))
    js_ = json.loads(baixar(p9, '#ea-exp-json', BAIX).read_text(encoding='utf-8'))
    jc = next(l for l in js_['empresas'] if l['cnpj_raiz'] == '26108898')
    check('Auditoria · JSON igual ao CSV, com o recorte e o dicionário de colunas', jc['lavra_autorizada_no_recorte'] == 0 and js_['recorte']['filtro_mineral'] == 'Fosfato'
          and 'total do agente' in js_['colunas']['ccee_mwh_agente_periodo']['descricao'])
    p9.select_option('#ea-metrica', 'ccee')
    p9.wait_for_timeout(600)
    check('Auditoria · lista por CCEE com filtro de mineral: avisa que é a carga total do agente', 'total do agente' in p9.inner_text('#ea-lista-sub'))
    sem_ccee = [l for l in ls if not l['ccee_mwh_agente_periodo']]
    check('Auditoria · CCEE de quem não é agente sai vazio no arquivo, não zero', bool(sem_ccee) and all(l['ccee_meses_observados_periodo'] == '' for l in sem_ccee), len(sem_ccee))
    p9.select_option('#ea-metrica', 'cfem')
    p9.wait_for_timeout(400)
    p9.evaluate("window.EmpresasAtlas.selecionarCnpj('42445403')")   # Serra Grande: ouro, nenhum processo nem CFEM de fosfato
    p9.wait_for_timeout(600)
    check('Auditoria · selecionada fora do filtro: o cartão avisa, sem trocar a empresa nem limpar o filtro',
          'Fora do recorte atual' in p9.inner_text('#ea-resumo') and sel(p9) == '42445403' and p9.locator('#ea-min option:checked').inner_text() == 'Fosfato')
    p9.screenshot(path=str(CAPT / '19a_recorte_fosfato_fora.png'))
    limpar(p9)
    p9.select_option('#ea-metrica', 'nome')
    p9.wait_for_timeout(500)
    jn = json.loads(baixar(p9, '#ea-exp-json', BAIX).read_text(encoding='utf-8'))['empresas']
    check('Auditoria · ordem por nome: CNPJ raiz sem razão social vai para o fim, sem sumir', not jn[0]['empresa'].startswith('(nome')
          and jn[-1]['empresa'].startswith('(nome') and len(jn) == p9.evaluate('window.EmpresasAtlas.totais()')['empresas'], (jn[0]['empresa'], jn[-1]['empresa']))
    p9.select_option('#ea-metrica', 'cfem')
    p9.wait_for_timeout(400)
    p9.click('#ea-ranking-btn')
    p9.wait_for_timeout(700)
    n0 = p9.locator('#ea-ranking .ea-rk-tab tbody tr').count()
    p9.click('#ea-ranking [data-rk-mais]')
    p9.wait_for_timeout(500)
    n1 = p9.locator('#ea-ranking .ea-rk-tab tbody tr').count()
    check('Auditoria · ranking: "Mostrar mais" passa das 50 primeiras', n0 == 50 and n1 == 100, (n0, n1))
    p9.click('#ea-ranking [data-rk-fechar]')

    # 19b. comparação: Chapada (Maracá) × Mara Rosa (Amarillo) e CMOC × Mosaic
    for c in ('86902053', '42799486'):
        p9.evaluate(f"window.EmpresasAtlas.selecionarCnpj('{c}')")
        p9.wait_for_timeout(400)
        p9.click('#ea-resumo [data-cmp]')
        p9.wait_for_timeout(300)
    area(p9, 'comparar')
    LINHAS = ("[...document.querySelectorAll('#ea-cmp-corpo .ea-cmp-tab tbody tr:not(.ea-cmp-grupo):not(.ea-cmp-corte)')]"
              ".map(r=>({rot:r.querySelector('th').innerText,max:!!r.querySelector('.ea-max')}))")
    FORA = "(document.querySelector('#ea-cmp-corpo .ea-cmp-fora')||{textContent:''}).textContent"
    lc1 = p9.evaluate(LINHAS)
    dec = [l for l in lc1 if l['rot'].startswith('Declarada')]
    check('Auditoria · Chapada × Mara Rosa: Ouro 2025 em oz (consolidado global realizado × guidance em Goiás) não vira linha comparável',
          not [l for l in dec if l['rot'].startswith('Declarada 2025 · Ouro')], [l['rot'][:70] for l in dec])
    fora = p9.evaluate(FORA)
    check('Auditoria · … os dois registros ficam acessíveis fora da tabela, com o motivo', 'Guidance' in fora and 'Consolidado global' in fora, fora[:200])
    ouro24 = [l for l in dec if l['rot'].startswith('Declarada 2024 · Ouro')]
    check('Auditoria · Ouro 2024: “ouro em concentrado” × “ouro equivalente (GEO)” em linhas separadas, marcadas e sem "maior"',
          len(ouro24) == 2 and not any(l['max'] for l in ouro24) and all('não compare entre linhas' in l['rot'] for l in ouro24), [l['rot'][:90] for l in ouro24])
    c24 = next(l for l in lc1 if l['rot'].startswith('Carga CCEE 2024'))
    c25 = next(l for l in lc1 if l['rot'].startswith('Carga CCEE 2025'))
    check('Auditoria · CCEE 2024 com 8 × 9 meses: sem destaque do maior e com a nota de cobertura', not c24['max'] and 'Meses observados diferentes' in c24['rot'], c24)
    check('Auditoria · CCEE 2025 com 12 × 12 meses: o maior continua em destaque', c25['max'], c25)
    p9.locator('#ea-cmp').screenshot(path=str(CAPT / '19b_comparacao_chapada_mararosa.png'))
    cab, lcsv = ler_csv(baixar(p9, '#ea-cmp-csv', BAIX))
    o25 = [l for l in lcsv if l['indicador'] == 'producao_declarada' and l['periodo'] == '2025' and l['mineral'] == 'Ouro']
    check('Auditoria · CSV da comparação: Ouro 2025 com escopo, tipo de valor, fonte e motivo, marcado fora da tabela',
          {(l['cnpj_raiz'], l['escopo'], l['tipo_valor'], l['na_tabela']) for l in o25} == {('86902053', 'consolidado_global', 'realizado', 'false'),
                                                                                            ('42799486', 'operacao_goias', 'guidance', 'false')}
          and all(l['fonte_url'].startswith('http') and l['observacao'] and l['confianca'] for l in o25), o25)
    n_det = sum(len(ATLAS['detalhes'][str(POR[c]['i'])]['producao']) for c in ('86902053', '42799486'))
    check('Auditoria · a exportação da comparação leva todos os registros declarados, inclusive os de fora da tabela',
          len([l for l in lcsv if l['indicador'] == 'producao_declarada']) == n_det, n_det)
    cc = [l for l in lcsv if l['indicador'] == 'ccee_carga_agente' and l['periodo'] == '2024']
    check('Auditoria · CSV: CCEE com meses observados e valor numérico em colunas próprias', len(cc) == 2 and {l['meses_observados'] for l in cc} == {'8', '9'}
          and all(numero(l['valor']) > 0 and 'Meses observados diferentes' in l['observacao'] for l in cc), cc)
    xcmp = ler_xlsx(baixar(p9, '#ea-cmp-xlsx', BAIX))
    check('Auditoria · Excel da comparação: Dados (longo), Tabela (larga), Colunas e Metadados', list(xcmp) == ['Dados', 'Tabela', 'Colunas', 'Metadados']
          and len(xcmp['Dados']) == len(lcsv) and all(isinstance(l['valor'], float) for l in xcmp['Dados'] if 'valor' in l), list(xcmp))
    p9.click('#ea-cmp-limpar')
    for termo in ('cmoc', 'mosaic fert'):
        p9.fill('#ea-cmp-busca', termo)
        p9.wait_for_timeout(400)
        p9.keyboard.press('Enter')
        p9.wait_for_timeout(500)
    lc2 = p9.evaluate(LINHAS)
    fora2 = p9.evaluate(FORA)
    check('Auditoria · CMOC × Mosaic: Fosfato 2023 em t (fertilizantes fosfatados × rocha fosfática, consolidado Brasil) não é comparado',
          not [l for l in lc2 if l['rot'].startswith('Declarada 2023 · Fosfato')] and 'rocha fosfática' in fora2 and 'fertilizantes fosfatados' in fora2,
          [l['rot'][:60] for l in lc2 if l['rot'].startswith('Declarada')])

    # 19c. três empresas: a quarta não entra por nenhum caminho e ninguém sai
    p9.fill('#ea-cmp-busca', 'maraca')
    p9.wait_for_timeout(400)
    p9.keyboard.press('Enter')
    p9.wait_for_timeout(500)
    tres = cmp_(p9)
    check('Auditoria · com três empresas, a busca do Comparar some e o limite é dito', len(tres) == 3 and p9.is_hidden('#ea-cmp-add-box')
          and 'limite' in p9.inner_text('#ea-cmp-slots'), tres)
    corte = p9.locator('#ea-cmp-corpo .ea-cmp-corte').first
    m_ = re.search(r'Mostrando (\d+) de (\d+)', corte.inner_text()) if corte.count() else None
    g_ = corte.locator('[data-cmp-tudo]').get_attribute('data-cmp-tudo') if corte.count() else None
    antes = len([l for l in p9.evaluate(LINHAS) if l['rot'].startswith({'est': 'Estimada', 'dec': 'Declarada', 'coef': 'Coeficiente'}.get(g_, '?'))])
    if g_:
        corte.locator('[data-cmp-tudo]').click()
        p9.wait_for_timeout(400)
    depois = len([l for l in p9.evaluate(LINHAS) if l['rot'].startswith({'est': 'Estimada', 'dec': 'Declarada', 'coef': 'Coeficiente'}.get(g_, '?'))])
    check('Auditoria · comparação: "Mostrando N de X" e "Mostrar todas" abre o resto', bool(m_) and antes == int(m_.group(1)) and depois == int(m_.group(2)),
          (g_, m_ and m_.group(0), antes, depois))
    area(p9, 'explorar')
    p9.evaluate("window.EmpresasAtlas.selecionarCnpj('42445403')")
    p9.wait_for_timeout(500)
    p9.click('#ea-resumo [data-cmp]')
    p9.wait_for_timeout(300)
    check('Auditoria · 4ª empresa pelo cartão do mapa: não entra, ninguém sai e o aviso explica', cmp_(p9) == tres and p9.is_visible('#ea-aviso')
          and 'limite' in p9.inner_text('#ea-aviso'), cmp_(p9))
    p9.screenshot(path=str(CAPT / '19c_limite_tres.png'))
    area(p9, 'dossie')
    p9.click('#ea-cmp-add')
    p9.wait_for_timeout(300)
    check('Auditoria · 4ª empresa pelo dossiê: não entra e ninguém sai', cmp_(p9) == tres and p9.is_visible('#ea-aviso'))
    p9.click('#ea-aviso [data-aviso-acao]')
    p9.wait_for_timeout(500)
    check('Auditoria · o aviso leva ao Comparar, onde se remove uma', area_(p9) == 'comparar' and p9.is_hidden('#ea-aviso'))

    # 19d. notícias: empresa com 141 diretas chega à 41ª e além; as do grupo levam a marca
    p9.evaluate("window.EmpresasAtlas.selecionarCnpj('08842895')")
    area(p9, 'dossie')
    p9.click('#ea-tab-noticias')
    p9.wait_for_timeout(500)
    itens = '#ea-corpo .rd-news:not(.ea-indiretas) > li'
    n40 = p9.locator(itens).count()
    p9.click('#ea-corpo [data-news-mais]')
    p9.wait_for_timeout(500)
    n80 = p9.locator(itens).count()
    diretas = [n for n in ATLAS['noticias'] if n['e'] == POR['08842895']['i'] and n['tipo'] == 'empresa']
    check(f'Auditoria · notícias: {len(diretas)} diretas (pacote); "Mostrar mais" leva à 41ª e além, com a contagem', len(diretas) > 80 and n40 == 40 and n80 == 80
          and p9.locator(itens).nth(40).is_visible() and f'80 de {len(diretas)}' in p9.inner_text('#ea-corpo .ea-pag'), (n40, n80, len(diretas)))
    check('Auditoria · notícias pelo nome do grupo ganham a marca discreta "via grupo"',
          p9.locator('#ea-corpo .rd-news:not(.ea-indiretas) .ea-tag-grupo').count() == sum(1 for n in diretas[:80] if n['metodo'] == 'alias_grupo'))
    p9.screenshot(path=str(CAPT / '19d_noticias_mais.png'), full_page=True)
    xd = ler_xlsx(baixar(p9, '#ea-ficha-xlsx', BAIX))
    check('Auditoria · dossiê em Excel: uma aba por assunto, com todos os processos e notícias',
          list(xd) == ['Empresa', 'CFEM e CCEE', 'Processos', 'Produção declarada', 'Produção estimada', 'Energia e coeficiente', 'Projetos', 'Notícias']
          and len(xd['Processos']) == POR['08842895']['n'] and len(xd['Notícias']) == len([n for n in ATLAS['noticias'] if n['e'] == POR['08842895']['i']])
          and all(l['processo'] and isinstance(l.get('area_ha', 0.0), float) for l in xd['Processos']), list(xd))

    # 19e. Voltar/Avançar a partir de #empresas sem history.state, e mapa → dossiê → mapa
    p9.goto(BASE + '/painel.html?nav=1#empresas')
    p9.wait_for_selector('#ea-content:not([hidden])', timeout=40000)
    p9.wait_for_function("document.querySelectorAll('#ea-lista .ea-item').length>0", timeout=30000)
    p9.wait_for_timeout(1200)
    p9.locator('#ea-lista .ea-item').first.click()
    p9.wait_for_timeout(1500)
    # o enquadramento espera a geometria dos processos (assíncrona): lê a posição só com o mapa parado
    z1, t0 = enq(p9), time.time()
    while time.time() - t0 < 10:
        p9.wait_for_timeout(400)
        z1, antes_ = enq(p9), z1
        if z1 == antes_:
            break
    c1 = sel(p9)
    check('Auditoria · seleção no mapa grava #empresas/explorar/<cnpj>', bool(c1) and p9.url.endswith(f'#empresas/explorar/{c1}'), p9.url)
    p9.click('#ea-resumo [data-ir="dossie"]')
    p9.wait_for_timeout(700)
    check('Auditoria · "Abrir o dossiê" vira entrada no histórico (#empresas/dossie/<cnpj>)', area_(p9) == 'dossie' and p9.url.endswith(f'#empresas/dossie/{c1}'), p9.url)
    p9.go_back()
    p9.wait_for_timeout(1000)
    check('Auditoria · Voltar do dossiê: mapa com a mesma seleção e o mesmo enquadramento', area_(p9) == 'explorar' and sel(p9) == c1 and enq(p9) == z1, (enq(p9), z1))
    p9.go_back()
    p9.wait_for_timeout(1000)
    check('Auditoria · Voltar até #empresas (entrada sem history.state): desmarca', sel(p9) is None and p9.url.endswith('#empresas'), p9.url)
    p9.go_forward()
    p9.wait_for_timeout(1000)
    check('Auditoria · Avançar restaura a empresa', sel(p9) == c1 and area_(p9) == 'explorar')
    p9.go_forward()
    p9.wait_for_timeout(800)
    check('Auditoria · Avançar de novo volta ao dossiê', area_(p9) == 'dossie' and sel(p9) == c1)
    area(p9, 'explorar')
    p9.wait_for_timeout(500)
    z3 = enq(p9)
    area(p9, 'dossie')
    area(p9, 'explorar')
    p9.wait_for_timeout(500)
    check('Auditoria · Explorar → Dossiê → Explorar pelas abas mantém seleção e zoom', sel(p9) == c1 and enq(p9) == z3, (enq(p9), z3))
    p9.goto(BASE + '/painel.html?nav=2#empresas/explorar/26108898')
    p9.wait_for_selector('#ea-content:not([hidden])', timeout=40000)
    p9.wait_for_timeout(1500)
    check('Auditoria · link #empresas/explorar/<cnpj> abre o mapa com a empresa', area_(p9) == 'explorar' and sel(p9) == '26108898')
    p9.goto(BASE + '/painel.html?nav=3#empresas/26108898')
    p9.wait_for_selector('#ea-content:not([hidden])', timeout=40000)
    p9.wait_for_timeout(1500)
    check('Auditoria · link curto #empresas/<cnpj> abre o dossiê', area_(p9) == 'dossie' and sel(p9) == '26108898')
    check('Auditoria · console e rede sem erros', not erros_relevantes(ruido9), erros_relevantes(ruido9)[:6])
    c9.close()

    # ================================================================ 20. ajustes finais: análise → dossiê → análise, linguagem pública, histórico,
    # exportações das análises, município → mapa e o aviso de recorte no dossiê
    BASTIDOR = re.compile(r'Squad\s*\d|\bsquads?\b|scripts?/|(?<![\w/.])data/|\bpublic/|\.json\b|\.py\b|pipeline|reposit[óo]rio|repository|GitHub|'
                          r'Dados brutos|Bases consolidadas|Dados corrigidos|build_\w+|\bcoletor\b', re.I)
    SEC = re.compile(r'https?://www\.sec\.gov/Archives/edgar/data/\S*')
    POR = {e['cnpj']: e for e in ATLAS['empresas']}
    c10 = nav.new_context(viewport={'width': 1440, 'height': 900}, accept_downloads=True, locale='pt-BR')
    p10 = c10.new_page()
    ruido10 = observar(p10)
    login(p10, U1)
    p10.goto(BASE + '/painel.html?r=20#empresas')
    p10.wait_for_selector('#ea-content:not([hidden])', timeout=40000)
    p10.wait_for_function('window.EmpresasAnalises&&window.EmpresasAnalises.pronto()', timeout=30000)
    p10.wait_for_timeout(800)
    ESTADO = ("({ano:document.getElementById('es-ano').value,base:document.getElementById('es-base').value,min:document.getElementById('es-min').value,"
              "cont:document.getElementById('es-count').textContent,esc:window.EmpresasAtlas.escopo(),anal:window.EmpresasAtlas.analise(),"
              "area:window.EmpresasAtlas.area(),sel:window.EmpresasAtlas.selecionada(),y:Math.round(scrollY)})")
    est10 = lambda: p10.evaluate(ESTADO)

    # 20a. produção estimada, todas as empresas, 2023, beneficiada, página 2 da tabela
    area(p10, 'analises')
    p10.select_option('#es-ano', '2023')
    p10.select_option('#es-base', 'beneficiada')
    p10.wait_for_timeout(500)
    p10.click('#es-tabela [data-es-pag="1"]')
    p10.wait_for_timeout(400)
    alvo = p10.locator('#es-tabela [data-emp-cnpj]').nth(1)
    alvo.scroll_into_view_if_needed()
    p10.wait_for_timeout(300)
    antes = est10()
    cn = alvo.get_attribute('data-emp-cnpj')
    h0 = p10.evaluate('history.length')
    pf_link = p10.evaluate("[...document.querySelectorAll('#es-tabela tr')].filter(r=>/pessoa f/i.test(r.innerText)).some(r=>r.querySelector('[data-emp-cnpj]'))")
    check('Ajustes · estimada: nomes de empresa com CNPJ raiz são atalhos; pessoa física e linhas do estado continuam texto',
          p10.locator('#es-tabela [data-emp-cnpj]').count() > 5 and not pf_link and p10.locator('#es-cobertura [data-emp-cnpj]').count() == 0
          and p10.locator('#es-barras [data-emp-cnpj]').count() > 0, (p10.locator('#es-tabela [data-emp-cnpj]').count(), pf_link))
    alvo.click()
    p10.wait_for_timeout(900)
    d = est10()
    check('Ajustes · clique no nome → Dossiê da empresa certa, numa entrada só do histórico', d['area'] == 'dossie' and d['sel'] == cn
          and p10.evaluate('history.length') - h0 == 1 and p10.url.endswith(f'#empresas/dossie/{cn}'), (d, cn))
    check('Ajustes · a análise não muda ao abrir o dossiê (filtros, página, escopo "todas")',
          (d['ano'], d['base'], d['min'], d['cont'], d['esc']) == (antes['ano'], antes['base'], antes['min'], antes['cont'], 'todas'), (antes, d))
    check('Ajustes · no dossiê aberto a partir da análise, o atalho discreto "Voltar à análise"', p10.is_visible('#ea-volta-analise [data-volta-analise]')
          and 'Produção estimada' in p10.inner_text('#ea-volta-analise'))
    p10.screenshot(path=str(CAPT / '20a_analise_para_dossie.png'))
    p10.go_back()
    p10.wait_for_timeout(1000)
    v = est10()
    check('Ajustes · Voltar devolve a mesma análise: filtros, página da tabela, escopo e rolagem',
          (v['area'], v['anal'], v['ano'], v['base'], v['min'], v['cont'], v['esc']) == ('analises', 'estimada', antes['ano'], antes['base'], antes['min'], antes['cont'], 'todas')
          and abs(v['y'] - antes['y']) <= 5, (antes, v))
    p10.screenshot(path=str(CAPT / '20b_volta_a_analise.png'))
    p10.go_forward()
    p10.wait_for_timeout(900)
    check('Ajustes · Avançar volta ao dossiê, com o atalho de volta', est10()['area'] == 'dossie' and p10.is_visible('#ea-volta-analise [data-volta-analise]'))
    p10.click('#ea-volta-analise [data-volta-analise]')
    p10.wait_for_timeout(900)
    v2 = est10()
    check('Ajustes · "Voltar à análise" devolve o mesmo contexto', (v2['area'], v2['cont'], v2['ano']) == ('analises', antes['cont'], antes['ano'])
          and abs(v2['y'] - antes['y']) <= 5, v2)
    # teclado: foco no nome e Enter
    p10.locator('#es-tabela [data-emp-cnpj]').first.focus()
    p10.keyboard.press('Enter')
    p10.wait_for_timeout(900)
    check('Ajustes · teclado: Enter no nome abre o dossiê e o foco vai para o título', est10()['area'] == 'dossie'
          and p10.evaluate("document.activeElement&&document.activeElement.id") == 'ea-ficha-titulo')
    p10.go_back()
    p10.wait_for_timeout(800)
    # barra (gráfico por empresa)
    b_ = p10.locator('#es-barras [data-emp-cnpj]').first
    cb = b_.get_attribute('data-emp-cnpj')
    b_.click()
    p10.wait_for_timeout(800)
    check('Ajustes · nome numa barra do gráfico por empresa também abre o dossiê', est10()['sel'] == cb and est10()['area'] == 'dossie', cb)
    p10.go_back()
    p10.wait_for_timeout(800)

    # 20b. escopo "empresa" fica como estava
    p10.evaluate("window.EmpresasAtlas.selecionarCnpj('26108898')")
    area(p10, 'analises')
    p10.wait_for_timeout(500)
    a0 = est10()
    p10.locator('#es-tabela [data-emp-cnpj="26108898"]').first.click()
    p10.wait_for_timeout(800)
    p10.go_back()
    p10.wait_for_timeout(900)
    a1 = est10()
    check('Ajustes · com a análise recortada na empresa, ir ao dossiê e voltar mantém o escopo e os filtros',
          a1['esc'] == 'empresa' and (a1['ano'], a1['base'], a1['min'], a1['cont']) == (a0['ano'], a0['base'], a0['min'], a0['cont']), (a0, a1))
    p10.click('#ea-escopo [data-escopo="todas"]')
    p10.wait_for_timeout(500)

    # 20c. produção declarada (empresa com dois minerais: Maracá, cobre e ouro) e o quadro de titulares do Panorama
    analise(p10, 'declarada')
    mar = p10.locator('#ep-tabela [data-emp-cnpj="86902053"]')
    check('Ajustes · declarada: as linhas de cada mineral da mesma empresa levam ao mesmo CNPJ raiz', mar.count() >= 2
          and len(set(p10.evaluate("[...document.querySelectorAll('#ep-tabela [data-emp-cnpj]')].map(b=>b.dataset.empCnpj)"))) == 10, mar.count())
    mar.first.click()
    p10.wait_for_timeout(800)
    check('Ajustes · declarada → dossiê da Maracá', est10()['sel'] == '86902053' and est10()['area'] == 'dossie')
    p10.go_back()
    p10.wait_for_timeout(900)
    check('Ajustes · … e de volta à declarada', est10()['anal'] == 'declarada' and est10()['area'] == 'analises')
    analise(p10, 'direitos')
    p10.wait_for_timeout(2500)
    tit = p10.locator('[id^="epn-c-emp_cfem"] [data-emp-cnpj]').first
    linha = tit.locator('xpath=ancestor::tr')
    cnpj_celula = re.sub(r'\D', '', linha.locator('td').nth(2).inner_text())
    ct = tit.get_attribute('data-emp-cnpj')
    check('Ajustes · Panorama: o titular com CNPJ raiz na mesma linha vira atalho (chave = CNPJ da linha)', ct == cnpj_celula and len(ct) == 8, (ct, cnpj_celula))
    tit.click()
    p10.wait_for_timeout(800)
    check('Ajustes · Panorama → dossiê do titular, e Voltar devolve "Arrecadação, títulos e consumo"', est10()['sel'] == ct)
    p10.go_back()
    p10.wait_for_timeout(1200)
    check('Ajustes · … de volta ao Panorama da aba', est10()['anal'] == 'direitos' and est10()['area'] == 'analises')

    # 20d. exportações das análises (estimada e declarada), lidas do arquivo baixado
    analise(p10, 'estimada')
    p10.select_option('#es-ano', '2023')
    p10.select_option('#es-min', 'Ouro')
    p10.wait_for_timeout(400)
    cab, le = ler_csv(baixar(p10, '#es-export', BAIX))
    num_ok = all(numero(l['producao_t']) is not None for l in le)
    check('Ajustes · CSV da estimada: cabeçalho na 1ª linha, decimal vírgula, CNPJ com 8 dígitos e o recorte em colunas',
          cab.startswith('ano;mineral;base;empresa;cnpj_raiz;') and 'filtro_mineral' in cab and le and num_ok
          and all(l['filtro_mineral'] == 'Ouro' and l['filtro_ano'] == '2023' for l in le)
          and all(re.fullmatch(r'\d{8}', l['cnpj_raiz']) or not l['cnpj_raiz'] for l in le) and any(',' in l['producao_t'] for l in le), cab[:120])
    analise(p10, 'declarada')
    cab2, ld = ler_csv(baixar(p10, '#ep-export', BAIX))
    check('Ajustes · CSV da declarada: cabeçalho na 1ª linha, produto e períodos da produção, recorte e fonte em colunas',
          cab2.startswith('empresa;grupo;cnpj_raiz;') and 'producao_periodos' in cab2 and 'fonte' in cab2 and len(ld) == len(BASE_EMP['linhas'])
          and all(re.fullmatch(r'\d{8}', l['cnpj_raiz']) for l in ld), (cab2[:100], len(ld)))

    # 20e. histórico além dos 25 primeiros (Serra Verde: 141 notícias diretas e 5 evidências de projeto)
    p10.evaluate("window.EmpresasAtlas.selecionarCnpj('08842895')")
    area(p10, 'dossie')
    p10.click('#ea-tab-historico')
    p10.wait_for_timeout(400)
    n25 = p10.locator('#ea-corpo .ea-timeline > li').count()
    p10.click('#ea-corpo [data-ev-mais]')
    p10.wait_for_timeout(400)
    n50 = p10.locator('#ea-corpo .ea-timeline > li').count()
    datas = p10.evaluate("[...document.querySelectorAll('#ea-corpo .ea-timeline .rd-data')].map(x=>x.textContent)")
    conta = p10.inner_text('#ea-corpo .ea-pag')
    check('Ajustes · histórico: "Mostrar mais" leva ao 26º acontecimento e além, em ordem cronológica, com a contagem',
          n25 == 25 and n50 == 50 and p10.locator('#ea-corpo .ea-timeline > li').nth(25).is_visible() and datas == sorted(datas, reverse=True)
          and f'50 de {n_acontecimentos("08842895")} ' in conta, (n25, n50, conta, n_acontecimentos('08842895')))
    check('Ajustes · histórico diz que notícia não prova operação local', 'não prova de operação' in p10.inner_text('#ea-corpo'))
    p10.locator('#ea-corpo').screenshot(path=str(CAPT / '20c_historico_mais.png'))

    # 20f. município do dossiê → Explorar com o município como recorte (código IBGE) e a empresa como empresa de interesse
    p10.evaluate("window.EmpresasAtlas.selecionarCnpj('26108898')")
    area(p10, 'dossie')
    p10.click('#ea-tab-perfil')
    p10.wait_for_timeout(300)
    chip = p10.locator('#ea-corpo .ea-mun-link[data-mun-ibge]', has_text='Catalão').first
    check('Ajustes · municípios do dossiê identificados pelo código IBGE', chip.count() == 1 and re.fullmatch(r'\d{7}', chip.get_attribute('data-mun-ibge') or ''),
          chip.get_attribute('data-mun-ibge'))
    chip.click()
    p10.wait_for_timeout(1500)
    check('Ajustes · município do dossiê → Explorar com o município como recorte, a empresa mantida (não como filtro)',
          est10()['area'] == 'explorar' and est10()['sel'] == '26108898' and p10.locator('#ea-mun option:checked').inner_text() == 'Catalão'
          and p10.evaluate('window.EmpresasAtlas.foco()') == 'municipio' and p10.evaluate('window.EmpresasAtlas.mapa().getZoom()') >= 8.5,
          p10.evaluate('window.EmpresasAtlas.mapa().getZoom()'))
    p10.screenshot(path=str(CAPT / '20d_municipio_no_mapa.png'))
    p10.click('#ea-mun-etq .ea-mun-etq-x')
    p10.wait_for_timeout(700)
    check('Ajustes · o × da etiqueta tira o município e a empresa fica', p10.input_value('#ea-mun') == '' and est10()['sel'] == '26108898')
    limpar(p10)

    # 20g. dossiê com filtro do Explorar ativo: frase curta, números da empresa inteira
    filtros(p10)
    p10.select_option('#ea-min', label='Fosfato')
    p10.wait_for_timeout(500)
    area(p10, 'dossie')
    p10.wait_for_timeout(400)
    check('Ajustes · com filtro no Explorar, o dossiê diz que os números são da empresa inteira', p10.is_visible('#ea-ficha-recorte')
          and 'Fosfato' in p10.inner_text('#ea-ficha-recorte') and 'todos os municípios e minerais' in p10.inner_text('#ea-kpis'))
    area(p10, 'explorar')
    limpar(p10)
    area(p10, 'dossie')
    check('Ajustes · sem filtro, a frase some', not p10.is_visible('#ea-ficha-recorte'))

    # 20h. linguagem pública renderizada (PT e EN): todas as áreas, as seis seções, a metodologia, títulos (tooltips) e links
    def varrer(pg, rotulo):
        achados = []
        def coleta(onde):
            t_ = pg.evaluate("(()=>{const v=document.getElementById('empresas-view');return v.innerText+' | '+[...v.querySelectorAll('[title],[aria-label]')]"
                             ".map(x=>(x.getAttribute('title')||'')+' '+(x.getAttribute('aria-label')||'')).join(' | ')})()")
            for m in BASTIDOR.finditer(SEC.sub(' ', t_)):
                achados.append(f"{onde}: …{t_[max(0, m.start() - 50):m.end() + 30]}…")
        pg.evaluate("window.EmpresasAtlas.selecionarCnpj('08842895')")
        area(pg, 'explorar')
        coleta('explorar')
        for emp in ('08842895', '26108898', '33931486'):
            pg.evaluate(f"window.EmpresasAtlas.selecionarCnpj('{emp}')")
            area(pg, 'dossie')
            for sec_ in ('perfil', 'territorio', 'economia', 'projetos', 'noticias', 'historico'):
                pg.click(f'#ea-tab-{sec_}')
                pg.wait_for_timeout(250)
                coleta(f'dossiê {emp}/{sec_}')
        pg.click('#ea-metodo summary')
        coleta('metodologia')
        area(pg, 'analises')
        pg.click('#ea-escopo [data-escopo="todas"]')
        for an in ('estimada', 'declarada'):
            analise(pg, an)
            for tab in pg.locator(f'#ea-anal-{an} [data-det]').all():
                tab.click()
                pg.wait_for_timeout(150)
                coleta(f'análise {an}/{tab.get_attribute("data-det")}')
        analise(pg, 'direitos')
        pg.wait_for_timeout(2000)
        for tb in ('emp_arrec', 'emp_titulos', 'emp_consumo'):
            pg.click(f'#epn-tabs [data-tab="{tb}"]')
            pg.wait_for_timeout(1200)
            coleta(f'panorama {tb}')
        area(pg, 'comparar')
        coleta('comparar')
        return achados
    ach = varrer(p10, 'pt')
    check('Ajustes · PT: nenhuma linguagem de bastidor no texto, nos títulos e nos rótulos renderizados da aba', not ach, ach[:6])
    p10.evaluate("window.EmpresasAtlas.selecionarCnpj('26108898')")
    area(p10, 'dossie')
    p10.click('#ea-tab-projetos')
    p10.wait_for_timeout(300)
    lk = p10.evaluate("[...document.querySelectorAll('#ea-corpo a[href^=\"http\"]')].map(a=>[a.href,a.innerText])")
    ruins = [(h, tx) for h, tx in lk if '↗' in tx and not (('anm.gov.br' in h and 'ANM' in tx) or re.sub(r'^www\.', '', h.split('/')[2]) in tx or tx.startswith(('ver fonte', 'see source')))]
    check('Ajustes · links de fonte dos projetos dizem o destino (ANM pelo nome, outros sites pelo domínio)', lk and not ruins, ruins[:4])
    p10.screenshot(path=str(CAPT / '20e_projetos_fontes.png'), full_page=True)
    # arquivos exportados nesta jornada e na seção 19: nada de bastidor
    import zipfile
    sujos = []
    for f in sorted(BAIX.glob('*')):
        if f.suffix in ('.csv', '.json'):
            txt = f.read_text(encoding='utf-8-sig')
        elif f.suffix == '.xlsx':
            with zipfile.ZipFile(f) as z:
                txt = ' '.join(z.read(n).decode('utf-8') for n in z.namelist() if n.startswith('xl/worksheets/'))
        else:
            continue
        sujos += [f'{f.name}: {m.group(0)}' for m in BASTIDOR.finditer(SEC.sub(' ', txt))]
    check('Ajustes · arquivos exportados (CSV, XLSX e JSON) sem linguagem de bastidor', not sujos, sujos[:6])
    check('Ajustes · console e rede sem erros', not erros_relevantes(ruido10), erros_relevantes(ruido10)[:6])
    c10.close()
    c11 = nav.new_context(viewport={'width': 1440, 'height': 900}, locale='en-US')
    p11 = c11.new_page()
    login(p11, U1)
    p11.goto(BASE + '/painel.html?lang=en#empresas')
    p11.wait_for_selector('#ea-content:not([hidden])', timeout=40000)
    p11.wait_for_function('window.EmpresasAnalises&&window.EmpresasAnalises.pronto()', timeout=30000)
    p11.wait_for_timeout(800)
    ach_en = varrer(p11, 'en')
    check('Ajustes · EN: nenhuma linguagem de bastidor no texto, nos títulos e nos rótulos renderizados da aba', not ach_en, ach_en[:6])
    p11.evaluate("localStorage.setItem('minera-lang','pt')")
    c11.close()

    # 20i. celular: análise → dossiê → análise com toque
    c12 = nav.new_context(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True, device_scale_factor=2)
    p12 = c12.new_page()
    login(p12, U1)
    p12.goto(BASE + '/painel.html?r=21#empresas/analises')
    p12.wait_for_selector('#ea-content:not([hidden])', timeout=40000)
    p12.wait_for_function('window.EmpresasAnalises&&window.EmpresasAnalises.pronto()', timeout=30000)
    p12.wait_for_timeout(1000)
    p12.select_option('#es-ano', '2023')
    p12.wait_for_timeout(400)
    lk12 = p12.locator('#es-tabela [data-emp-cnpj]').first
    lk12.scroll_into_view_if_needed()
    box12 = lk12.bounding_box()
    ant12 = p12.evaluate(ESTADO)
    p12.screenshot(path=str(CAPT / '20f_celular_analise.png'))
    lk12.tap()
    p12.wait_for_timeout(900)
    check('Ajustes · celular: tocar no nome abre o dossiê, com área de toque confortável', p12.evaluate('window.EmpresasAtlas.area()') == 'dossie'
          and box12['height'] >= 30, round(box12['height']))
    p12.screenshot(path=str(CAPT / '20g_celular_dossie.png'))
    p12.go_back()
    p12.wait_for_timeout(1000)
    dep12 = p12.evaluate(ESTADO)
    check('Ajustes · celular: Voltar devolve a mesma análise e a rolagem, sem rolagem horizontal',
          (dep12['area'], dep12['ano'], dep12['cont']) == ('analises', ant12['ano'], ant12['cont']) and abs(dep12['y'] - ant12['y']) <= 5
          and sem_rolagem_horizontal(p12)[0], (ant12, dep12))
    p12.screenshot(path=str(CAPT / '20h_celular_volta.png'))
    c12.close()

    nav.close()

falhas = [r for r in resultados if r['resultado'] != 'APROVADO']
Path(args.saida).parent.mkdir(parents=True, exist_ok=True)
Path(args.saida).write_text(json.dumps({'executado_em': time.strftime('%Y-%m-%d %H:%M:%S'), 'base': BASE, 'navegador': args.canal,
                                         'total': len(resultados), 'falhas': len(falhas), 'verificacoes': resultados},
                                        ensure_ascii=False, indent=1), encoding='utf-8')
print(f'\n{len(resultados) - len(falhas)}/{len(resultados)} verificações aprovadas')
sys.exit(1 if falhas else 0)
