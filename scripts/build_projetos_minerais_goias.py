# -*- coding: utf-8 -*-
"""Radar de Projetos de Goiás: base consolidada de projetos minerais em `Squad 1/Radar de Projetos/projetos_minerais_goias.xlsx`.

    python scripts/build_projetos_minerais_goias.py            # escreve a planilha
    python scripts/build_projetos_minerais_goias.py --checar   # só roda o controle de qualidade e imprime as contagens

Junta quatro origens, nesta ordem de prioridade (a de cima absorve as de baixo quando é o mesmo empreendimento):

1. **Pesquisa na web** (`Squad 1/Radar de Projetos/curadoria_web.json`): projetos com notícia, documento da empresa, de governo ou
   regulatório, cada um com as fontes que o sustentam. É a única origem que preenche capacidade, CAPEX e cronograma.
2. **Operações com CFEM em 2025** (ANM): titular pessoa jurídica que recolheu CFEM em 2025. Agregados para construção civil só a partir
   de R$ 300 mil no ano; água mineral fica fora.
3. **Carteira ANM** (aba `04_dim_projetos` da base consolidada v17 do Squad 1): projetos que ainda não produzem, com a classificação de
   maturidade do próprio Squad 1 (teto PROVÁVEL). Fora: pessoa física, agregados para construção civil e água mineral.
4. **Portfólios de pesquisa** (Cadastro Mineiro): titular PJ com 5 ou mais títulos de pesquisa de um mesmo mineral crítico ou
   estratégico, classificado como SINAL.

Uma linha de origem 2–4 do mesmo titular (CNPJ raiz ou processo), mesmo mineral e mesmo município de um projeto pesquisado não vira linha
nova: entra como evidência desse projeto na aba NOTÍCIAS. Nada é estimado: o que a fonte não traz fica `NA`.
"""
import argparse
import collections
import csv
import io
import json
import re
import sys
import unicodedata
import zipfile
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
PASTA = Path('Squad 1') / 'Radar de Projetos'
CURADORIA = PASTA / 'curadoria_web.json'
SAIDA = PASTA / 'projetos_minerais_goias.xlsx'
BRUTOS = Path('Squad 1') / 'Dados brutos'
BASE_V17 = Path('Squad 1') / 'Bases consolidadas' / 'documentacao' / 'prototipo_bases_consolidadas_v17.xlsx'
ATLAS = Path('data') / 'atlas' / 'atlas.json'

HIERARQUIA = ['OPERAÇÃO', 'EXPANSÃO', 'CONSTRUÇÃO', 'DEFINIDO', 'PROVÁVEL', 'POSSÍVEL', 'SINAL']
CONFIANCA = ['ALTO', 'MÉDIO', 'BAIXO']
URL_CFEM = 'https://dadosabertos.anm.gov.br/CFEM/CFEM_Arrecadacao_2022_2026.csv'
URL_SIGMINE = 'https://dadosabertos.anm.gov.br/SIGMINE/PROCESSOS_MINERARIOS/GO.zip'
URL_ALVARA = 'https://dadosabertos.anm.gov.br/SCM/Alvara_de_Pesquisa.csv'
URL_REQ_PESQ = 'https://dadosabertos.anm.gov.br/SCM/Requerimento_de_Pesquisa.csv'
ACESSO_ANM = '2026-09-10'   # data de download dos arquivos da ANM pelo Squad 1 (Dados brutos/LEIA-ME.md)
ANO_CFEM = '2025'
LIMIAR_AGREGADO = 300_000.0
MIN_TITULOS = 5

COLUNAS = ['ID', 'Projeto', 'Empresa', 'Empresa controladora', 'Parceiros / JV', 'Mineral principal', 'Outros minerais', 'Município',
           'Estado', 'Fase', 'Maturidade', 'Estágio detalhado', 'Status atual', 'Capacidade anunciada', 'Unidade da capacidade',
           'Produção anual', 'Unidade da produção', 'CAPEX', 'Moeda CAPEX', 'Ano do CAPEX', 'Previsão de entrada em operação',
           'Ano previsto', 'Data do anúncio', 'Data da informação mais recente', 'Grau de confiança', 'Evidência principal',
           'Fonte principal', 'Link principal', 'Outras evidências', 'Links adicionais', 'Observações']
COLUNAS_NOT = ['ID da notícia', 'ID do projeto', 'Projeto', 'Empresa', 'Mineral', 'Município', 'Estado', 'Data', 'Título', 'Veículo',
               'Tipo de fonte', 'Evidência extraída', 'Relevância', 'Link', 'Data de acesso', 'Observações']
CAMPO = {'Projeto': 'projeto', 'Empresa': 'empresa', 'Empresa controladora': 'controladora', 'Parceiros / JV': 'parceiros',
         'Mineral principal': 'mineral', 'Outros minerais': 'outros', 'Município': 'municipio', 'Fase': 'fase',
         'Maturidade': 'maturidade', 'Estágio detalhado': 'estagio', 'Status atual': 'status', 'Capacidade anunciada': 'cap',
         'Unidade da capacidade': 'cap_un', 'Produção anual': 'prod', 'Unidade da produção': 'prod_un', 'CAPEX': 'capex',
         'Moeda CAPEX': 'capex_moeda', 'Ano do CAPEX': 'capex_ano', 'Previsão de entrada em operação': 'previsao',
         'Ano previsto': 'ano_prev', 'Data do anúncio': 'data_anuncio', 'Data da informação mais recente': 'data_info',
         'Grau de confiança': 'confianca', 'Evidência principal': 'evidencia', 'Fonte principal': 'fonte', 'Link principal': 'link',
         'Outras evidências': 'outras_evid', 'Links adicionais': 'links_add', 'Observações': 'obs'}

# Agregados para construção civil e água: entram nas operações só acima do limiar e ficam fora da carteira e dos portfólios.
AGREGADOS_CFEM = {'AREIA', 'CASCALHO', 'SAIBRO', 'ARGILA', 'BASALTO', 'GRANITO', 'GNAISSE', 'MICAXISTO', 'XISTO', 'DIORITO',
                  'GRANULITO', 'GRANODIORITO', 'FILITO', 'ARENITO', 'BRITA', 'CASCALHO E AREIA', 'QUARTZITO P/ BRITA'}
AGUAS = {'ÁGUA MINERAL', 'ÁGUA POTÁVEL DE MESA', 'ÁGUAS TERMAIS', 'ÁGUA TERMAL'}
AGREGADOS_ABA04 = {'Areia', 'Rochas (Britadas) e Cascalho', 'Argilas', 'Saibro', 'Água Mineral'}
NOME_ABA04 = {'Monazita e Terras-Raras': 'Terras raras', 'Alumínio (Bauxita)': 'Bauxita', 'Vermiculita e Perlita': 'Vermiculita',
              'Quartzo (Cristal) e outros Piezelétricos': 'Quartzo', 'Dolomito e Magnesita': 'Dolomito',
              'Feldspato, Leucita e Nefelina-Sienito': 'Feldspato e nefelina-sienito', 'Talco e outras Cargas Minerais': 'Talco',
              'Cianita e outros minerais refratários': 'Cianita', 'Minerais Industriais (Outros)': 'Minerais industriais (outros)',
              'Rochas Ornamentais - Outras': 'Rochas ornamentais', 'Rochas Ornamentais': 'Rochas ornamentais',
              'Calcário Dolomítico': 'Calcário dolomítico', 'Calcário Calcítico': 'Calcário calcítico',
              'Laterita (perfil de intemperismo, não classificado)': 'Laterita (não classificada)', 'Ferro': 'Minério de ferro'}
ESTAGIO_FASE = {'lavra_autorizada_sem_producao': 'Licenciamento (lavra concedida, sem produção)',
                'requerimento_de_lavra': 'Licenciamento (lavra requerida)',
                'direito_de_requerer_lavra': 'Pesquisa mineral concluída (relatório final aprovado, lavra a requerer)',
                'requerimento_de_licenciamento_ou_lavra_garimpeira': 'Licenciamento (regime de licenciamento ou lavra garimpeira)'}
# Minerais críticos e estratégicos dos portfólios de pesquisa: rótulo -> trechos do nome da substância na ANM.
CRITICOS = {'Terras raras': ['TERRAS RARAS', 'MONAZITA', 'XENOTIMA'], 'Níquel': ['NÍQUEL'], 'Cobre': ['COBRE'], 'Cobalto': ['COBALTO'],
            'Lítio': ['LÍTIO', 'LEPIDOLITA', 'ESPODUMÊNIO', 'PETALITA', 'AMBLIGONITA'], 'Grafita': ['GRAFITA', 'GRAFITE'],
            'Nióbio': ['NIÓBIO', 'PIROCLORO', 'COLUMBITA'], 'Tântalo': ['TÂNTALO', 'TANTALITA'],
            'Titânio': ['TITÂNIO', 'ILMENITA', 'RUTILO', 'ANATÁSIO'], 'Vanádio': ['VANÁDIO'], 'Manganês': ['MANGANÊS'],
            'Fosfato': ['FOSFATO', 'APATITA'], 'Potássio': ['POTÁSS', 'SILVINITA'], 'Estanho': ['ESTANHO', 'CASSITERITA'],
            'Tungstênio': ['TUNGST', 'WOLFRAMITA', 'SCHEELITA'], 'Fluorita': ['FLUORITA'], 'Platina e metais do grupo': ['PLATINA', 'PALÁDIO'],
            'Ouro': ['OURO'], 'Diamante': ['DIAMANTE']}


def sem_acento(s):
    return ''.join(c for c in unicodedata.normalize('NFD', str(s)) if unicodedata.category(c) != 'Mn').upper().strip()


# Marcas de nome empresarial. Titular com CNPJ cujo nome não tem nenhuma delas é empresário individual ou espólio: nome de pessoa,
# que o projeto não publica (mesma regra do atlas e da base consolidada para pessoa física).
MARCA_EMPRESA = re.compile(r'\b(LTDA|LIMITADA|S/?A|S\.\s?A\.?|EIRELI|EPP|CIA|COMPANHIA|COOPERATIVA|CONS[OÓ]RCIO|ASSOCIA[CÇ][AÃ]O|MUNIC[IÍ]PIO|'
                           r'PREFEITURA|MINERA\w*|MINER[AÁ]\w*|MIN[EÉ]RIOS?|MINING|MINERALS|RESOURCES|EXTRA[CÇ][AÃ]O|PEDRAS?|PEDREIRA|GRANITOS?|'
                           r'M[AÁ]RMORES?|CALC[AÁ]RIO|AREIA|INDUSTRIA|IND[UÚ]STRIA|COM[EÉ]RCIO|PARTICIPA[CÇ][OÕ]ES|HOLDING|GROUP|INC|CORP|PLC|'
                           r'LIMITED|EMPRESA|EMPREENDIMENTOS|SERVI[CÇ]OS?|CONSTRU\w*|ENGENHARIA|CONSULTORIA|TRANSPORTES?|LOG[IÍ]STICA|'
                           r'FERTILIZANTES|ESTUDOS|GEOLOGIA|GEST[AÃ]O|CAPITAL|INVESTIMENTOS|AGRO\w*|CORRETIVOS|CPRM|INB)\b', re.I)
TITULAR_INDIVIDUAL = 'Titular individual (nome não publicado)'
TITULARES_INDIVIDUAIS = 'Titulares pessoa física (nomes não publicados)'


def titular_publico(nome):
    nome = (nome or '').strip()
    return nome if MARCA_EMPRESA.search(nome) else TITULAR_INDIVIDUAL


def ler_csv(caminho):
    for enc in ('utf-8-sig', 'latin-1'):
        try:
            texto = caminho.read_text(encoding=enc)
            break
        except UnicodeDecodeError:
            continue
    return list(csv.DictReader(texto.splitlines(), delimiter=',' if texto[:300].count('","') else ';'))


def reais(v):
    return f"R$ {v:,.0f}".replace(',', '.') if v >= 1000 else f"R$ {v:,.2f}".replace('.', '#').replace(',', '.').replace('#', ',')


def fmt_mil(v):
    return f'{v:,.0f}'.replace(',', '.')


class Contexto:
    def __init__(self, raiz):
        self.raiz = raiz
        atlas = json.loads((raiz / ATLAS).read_text(encoding='utf-8'))
        self.mun_por_codigo = {m['code']: m['name'] for m in atlas['municipalities']}
        self.mun_por_chave = {sem_acento(n): n for n in self.mun_por_codigo.values()}

    def municipio(self, texto):
        """Nome oficial do IBGE para um município de Goiás; None se for de outra UF ou desconhecido."""
        t = sem_acento(texto)
        if t.endswith(' - GO'):
            t = t[:-5]
        elif re.search(r' - [A-Z]{2}$', t):
            return None
        return self.mun_por_chave.get(t)

    def municipios(self, texto):
        return [m for m in (self.municipio(x) for x in str(texto or '').split(',')) if m]


def titular_por_processo(ctx):
    """Processo 'NNNNNN/AAAA' -> (titular, CNPJ raiz ou '', só PJ conhecido). Cadastro Mineiro primeiro, SIGMINE depois."""
    import shapefile  # pyshp
    mapa = {}
    for f in sorted((ctx.raiz / BRUTOS / 'ANM - Cadastro Mineiro').glob('*.csv')):
        for r in ler_csv(f):
            doc = re.sub(r'\D', '', r.get('CPF/CNPJ do titular') or '')
            proc = (r.get('Processo') or '').strip()
            if proc and len(doc) == 14:
                mapa[proc] = ((r.get('Titular') or '').strip().upper(), doc[:8])
    # Nome do SIGMINE de um titular que também está no Cadastro herda o CNPJ e a grafia do Cadastro.
    por_nome = {sem_acento(n): (n, c) for n, c in mapa.values()}
    z = zipfile.ZipFile(ctx.raiz / BRUTOS / 'ANM - SIGMINE' / 'GO.zip')
    nome = [n for n in z.namelist() if n.lower().endswith('.dbf')][0]
    for rec in shapefile.Reader(dbf=io.BytesIO(z.read(nome)), encoding='latin-1').iterRecords(fields=['PROCESSO', 'NOME']):
        nome_sig = rec['NOME'].strip().upper()
        mapa.setdefault(rec['PROCESSO'].strip(), por_nome.get(sem_acento(nome_sig), (nome_sig, '')))
    return mapa


def mineral_cfem(sub):
    s = sub.strip().upper()
    s = {'APATITA': 'FOSFATO', 'MINÉRIO DE ALUMÍNIO': 'BAUXITA'}.get(s, s)
    if s.startswith('MINÉRIO DE ') and s != 'MINÉRIO DE FERRO':
        s = s[len('MINÉRIO DE '):]
    return s.capitalize()


# ---------------------------------------------------------------- origem 2: operações com CFEM
def operacoes_cfem(ctx, proc_titular):
    agg = collections.defaultdict(lambda: {'v': 0.0, 'v_agreg': 0.0, 'subs': collections.Counter(), 'mun': collections.Counter(),
                                           'proc': set(), 'qtd': collections.Counter(), 'ultima': '',
                                           'nomes': collections.Counter(), 'cnpj': ''})
    sem_titular = collections.Counter()
    for r in ler_csv(ctx.raiz / BRUTOS / 'ANM - CFEM' / 'CFEM_Arrecadacao_2022_2026_GO.csv'):
        if r['Ano'] != ANO_CFEM or r['Tipo_PF_PJ'] != 'PJ':
            continue
        sub = r['Substância'].strip().upper()
        if sub in AGUAS:
            continue
        v = float(r['ValorRecolhido'].replace('.', '').replace(',', '.') if ',' in r['ValorRecolhido'] else r['ValorRecolhido'] or 0)
        proc = f"{int(r['Processo'])}/{r['AnoDoProcesso']}"
        tit = proc_titular.get(proc)
        if not tit:
            sem_titular[proc] += v
            continue
        a = agg[tit[1] or sem_acento(tit[0])]
        a['nomes'][tit[0]] += v
        a['cnpj'] = tit[1]
        a['v'] += v
        if sub in AGREGADOS_CFEM:
            a['v_agreg'] += v
        a['subs'][sub] += v
        a['mun'][ctx.mun_por_codigo.get(r['CodigoMunicipio'].strip(), r['Município'].title())] += v
        a['proc'].add(proc)
        unidade = r['UnidadeDeMedida'].strip()
        try:
            a['qtd'][(mineral_cfem(sub), unidade)] += float(r['QuantidadeComercializada'].replace('.', '').replace(',', '.'))
        except ValueError:
            pass
        d = r['DataCriacao'].strip()[:10]
        if re.fullmatch(r'\d{2}/\d{2}/\d{4}', d):
            iso = f'{d[6:]}-{d[3:5]}-{d[:2]}'
            a['ultima'] = max(a['ultima'], iso)
    linhas = []
    for a in agg.values():
        titular, cnpj = a['nomes'].most_common(1)[0][0], a['cnpj']
        incluidas = {s: v for s, v in a['subs'].items() if s not in AGREGADOS_CFEM or a['v_agreg'] >= LIMIAR_AGREGADO}
        if not incluidas or sum(incluidas.values()) <= 0:
            continue
        minerais = []
        for s, _ in sorted(incluidas.items(), key=lambda x: -x[1]):
            m = mineral_cfem(s)
            if m not in minerais:
                minerais.append(m)
        muns = [m for m, _ in a['mun'].most_common()]
        qtd = '; '.join(f"{m}: {fmt_mil(q)} {u}" for (m, u), q in sorted(a['qtd'].items(), key=lambda x: -x[1]) if q > 0 and m in minerais)
        nome = titular_publico(titular.replace(' [SIGMINE]', ''))
        procs = sorted(a['proc'])
        linhas.append({
            'origem': 'cfem', 'cnpj': cnpj, 'titular': nome, 'minerais': minerais, 'municipios': muns, 'processos': procs, 'valor': a['v'],
            'projeto': (f"Operação de {minerais[0].lower()} — {nome} ({muns[0]})" if nome != TITULAR_INDIVIDUAL else
                        f"Operação de {minerais[0].lower()} — titular individual, processo {procs[0]} ({muns[0]})"),
            'empresa': nome, 'mineral': minerais[0],
            'outros': ', '.join(minerais[1:]) or 'NA', 'municipio': muns[0], 'fase': 'Operação', 'maturidade': 'OPERAÇÃO',
            'estagio': f'Lavra com CFEM recolhida em {ANO_CFEM}', 'status': f'Em operação (CFEM {ANO_CFEM})',
            'data_info': a['ultima'] or 'NA', 'confianca': 'ALTO',
            'evidencia': (f"{nome} recolheu {reais(a['v'])} de CFEM em {ANO_CFEM} sobre {', '.join(m.lower() for m in minerais)} "
                          f"em {', '.join(muns[:4])}{' e outros' if len(muns) > 4 else ''} ({len(procs)} processo{'s' if len(procs) > 1 else ''})."),
            'fonte': 'ANM — CFEM (arrecadação 2022–2026, recorte Goiás)', 'link': URL_CFEM,
            'outras_evid': 'ANM — Cadastro Mineiro e SIGMINE: titular e situação dos processos.', 'links_add': URL_SIGMINE,
            'obs': (f"Linha derivada da ANM. Processos: {', '.join(procs[:12])}{' …' if len(procs) > 12 else ''}. "
                    + (f"Quantidade comercializada declarada na CFEM {ANO_CFEM} (não é produção): {qtd}. " if qtd else '')
                    + (f"Municípios: {', '.join(muns)}. " if len(muns) > 1 else '')
                    + 'Capacidade, produção, CAPEX e cronograma não divulgados nas fontes oficiais usadas (NA).').strip(),
            'noticia': {'data': a['ultima'] or 'NA', 'titulo': f'CFEM {ANO_CFEM} — {nome}', 'veiculo': 'Agência Nacional de Mineração',
                        'tipo': 'Documento oficial/regulatório',
                        'evidencia': f"CFEM de {ANO_CFEM}: {reais(a['v'])} ({', '.join(m.lower() for m in minerais)}; processos {', '.join(procs[:8])}{' …' if len(procs) > 8 else ''}).",
                        'relevancia': 'Alta', 'link': URL_CFEM, 'acesso': ACESSO_ANM,
                        'obs': 'Data = último registro de CFEM do titular no ano.'}})
    return linhas, sem_titular


# ---------------------------------------------------------------- origem 3: carteira ANM (aba 04)
def carteira_aba04(ctx):
    import openpyxl
    wb = openpyxl.load_workbook(ctx.raiz / BASE_V17, read_only=True)
    it = wb['04_dim_projetos'].iter_rows(values_only=True)
    for _ in range(3):
        next(it)
    cab = next(it)
    grupos, fora = collections.defaultdict(list), collections.Counter()
    for valores in it:
        r = dict(zip(cab, valores))
        if not r['project_id']:
            continue
        cid = str(r['company_id'] or '')
        razao = str(r['razao_social'] or '').strip()
        pj = cid.startswith('COM_CNPJ') or (not cid and re.search(r'\b(LTDA|S/?A|S\.A\.?|EIRELI|CPRM|COOPERATIVA|MINERA)', razao.upper()))
        if r['mineral_name'] in AGREGADOS_ABA04:
            fora['agregado ou água'] += 1
            continue
        mineral = NOME_ABA04.get(r['mineral_name'], r['mineral_name']) or 'NA'
        mun = ctx.municipio(r['municipality_name']) or r['municipality_name']
        # Pessoa física: sem nome, agregada por mineral e município (o arranjo de garimpeiros de um lugar é um empreendimento só).
        grupos[(cid or razao if pj else 'PF', mineral, mun)].append(r)
        if not pj:
            fora['pessoa física (agregada por mineral e município, sem nome)'] += 1
    # Áreas não contíguas do mesmo titular, mineral e município são um empreendimento só: a linha herda o bloco mais avançado.
    ordem = {m: i for i, m in enumerate(HIERARQUIA)}
    classe = lambda r: r['classificacao_maturidade'].upper().replace('PROVAVEL', 'PROVÁVEL').replace('POSSIVEL', 'POSSÍVEL')
    linhas = []
    for (chave, mineral, mun), rs in grupos.items():
        rs = sorted(rs, key=lambda r: (ordem[classe(r)], -(r['area_ha'] or 0)))
        r = rs[0]
        cid = str(r['company_id'] or '') if chave != 'PF' else ''
        razao = titular_publico(str(r['razao_social'] or '')) if chave != 'PF' else TITULARES_INDIVIDUAIS
        n_tit = len({x['company_id'] for x in rs})
        rotulo = mineral.lower() if mineral != 'NA' else 'mineral não informado'
        procs = sorted({p.strip() for x in rs for p in str(x['processos_anm']).split(';') if p.strip()})
        area = sum(x['area_ha'] or 0 for x in rs)
        datas = [str(x['data_evidencia'])[:10] for x in rs if x['data_evidencia']]
        ids = ', '.join(x['project_id'] for x in rs)
        fase = ESTAGIO_FASE.get(r['estagio'], r['estagio'])
        blocos = f"{len(rs)} blocos não contíguos ({ids}); " if len(rs) > 1 else f"{r['project_id']}; "
        adj = '; '.join(sorted({str(x['operacao_adjacente']) for x in rs if x['operacao_adjacente']}))
        noticias = [{'data': str(x['data_evidencia'] or 'NA')[:10], 'titulo': f"SIGMINE/Cadastro Mineiro — processo {x['processo_ancora']}",
                     'veiculo': 'Agência Nacional de Mineração', 'tipo': 'Documento oficial/regulatório',
                     'evidencia': (f"{razao}: {rotulo} em {mun}, {str(x['estagio']).replace('_', ' ')} ({x['qtd_processos']} processo(s), "
                                   f"{fmt_mil(x['area_ha'] or 0)} ha), classificação {classe(x)}; último evento: {x['ultimo_evento']}."),
                     'relevancia': 'Média', 'link': URL_SIGMINE, 'acesso': ACESSO_ANM,
                     'obs': f"Projeto {x['project_id']} da aba 04 da base consolidada v17. Data = último evento do processo-âncora."} for x in rs]
        if len(rs) > 5:
            # Grupo grande (garimpo, arranjo produtivo): uma evidência-resumo em vez de uma por projeto da ANM.
            por_classe = collections.Counter(classe(x) for x in rs)
            noticias = [{'data': max(datas) if datas else 'NA', 'titulo': f"SIGMINE/Cadastro Mineiro — {len(rs)} projetos de {rotulo} em {mun}",
                         'veiculo': 'Agência Nacional de Mineração', 'tipo': 'Documento oficial/regulatório',
                         'evidencia': (f"{len(rs)} projetos da aba 04 ({', '.join(f'{n} {c}' for c, n in por_classe.most_common())}), "
                                       f"{len(procs)} processos, {fmt_mil(area)} ha; processos-âncora: "
                                       f"{', '.join(x['processo_ancora'] for x in rs[:25])}{' …' if len(rs) > 25 else ''}."),
                         'relevancia': 'Média', 'link': URL_SIGMINE, 'acesso': ACESSO_ANM,
                         'obs': 'Resumo de vários projetos da aba 04 da base consolidada v17. Data = evento mais recente do grupo.'}]
        linhas.append({
            'origem': 'aba04', 'cnpj': cid[-8:] if cid.startswith('COM_CNPJ') else '', 'titular': razao, 'minerais': [mineral],
            'municipios': [mun], 'processos': procs,
            'projeto': (f"Projetos de {rotulo} de titulares individuais ({mun})" if chave == 'PF' else
                        f"Projeto de {rotulo} — {razao} ({mun})" if razao != TITULAR_INDIVIDUAL else
                        f"Projeto de {rotulo} — titular individual, processo {r['processo_ancora']} ({mun})"),
            'empresa': razao, 'mineral': mineral, 'outros': 'NA',
            'municipio': mun, 'fase': fase, 'maturidade': classe(r),
            'estagio': r['criterio_classificacao'], 'status': f"Último evento na ANM: {r['ultimo_evento']}",
            'data_info': max(datas) if datas else 'NA', 'confianca': 'ALTO',
            'evidencia': ((f"{n_tit} titula{'res individuais' if n_tit > 1 else 'r individual'}, " if chave == 'PF' else '') +
                          f"{len(procs)} processo{'s' if len(procs) != 1 else ''} da ANM ({fmt_mil(area)} ha); bloco mais avançado com processo-âncora "
                          f"{r['processo_ancora']} em {fase.lower()}: {r['criterio_classificacao']}."),
            'fonte': 'ANM — SIGMINE e Cadastro Mineiro, pela base consolidada do Squad 1 (v17, aba 04_dim_projetos)', 'link': URL_SIGMINE,
            'outras_evid': (f"Relatório final de pesquisa aprovado: {r['relatorio_final_aprovado']}; evento de licenciamento ambiental: "
                            f"{r['evento_licenciamento_ambiental']}" + (f"; operação adjacente: {adj}" if adj else '') + '.'),
            'links_add': f'{URL_CFEM}; https://dadosabertos.anm.gov.br/SCM/',
            'obs': (f"Linha derivada da ANM: {blocos}processos {', '.join(procs[:12])}{' …' if len(procs) > 12 else ''}. "
                    + (f"{r['observacao']}. " if r['observacao'] else '')
                    + 'Maturidade pela regra do Squad 1 (teto PROVÁVEL; DEFINIDO, CONSTRUÇÃO e EXPANSÃO exigem documento da empresa ou do órgão ambiental). '
                    'Capacidade, CAPEX e cronograma não divulgados (NA).'),
            'noticias': noticias})
    return linhas, fora


# ---------------------------------------------------------------- origem 4: portfólios de pesquisa
def portfolios(ctx):
    grupos = collections.defaultdict(lambda: {'proc': set(), 'mun': collections.Counter(), 'fase': collections.Counter(), 'titular': ''})
    pasta = ctx.raiz / BRUTOS / 'ANM - Cadastro Mineiro'
    for arquivo in ('Alvara_de_Pesquisa.csv', 'Requerimento_de_Pesquisa.csv'):
        for r in ler_csv(pasta / arquivo):
            doc = re.sub(r'\D', '', r.get('CPF/CNPJ do titular') or '')
            if len(doc) != 14:
                continue
            subs = sem_acento(r.get('Substância(s)') or '')
            for rotulo, trechos in CRITICOS.items():
                if any(sem_acento(t) in subs for t in trechos):
                    g = grupos[(doc[:8], rotulo)]
                    g['proc'].add(r['Processo'].strip())
                    g['titular'] = titular_publico((r.get('Titular') or '').strip().upper())
                    g['fase'][r.get('Fase Atual')] += 1
                    for m in ctx.municipios(r.get('Municipio(s)')):
                        g['mun'][m] += 1
    linhas = []
    for (cnpj, mineral), g in grupos.items():
        if len(g['proc']) < MIN_TITULOS or not g['mun']:
            continue
        muns = [m for m, _ in g['mun'].most_common()]
        procs = sorted(g['proc'])
        fases = '; '.join(f'{n} em {f.lower()}' for f, n in g['fase'].most_common())
        linhas.append({
            'origem': 'pesquisa', 'cnpj': cnpj, 'titular': g['titular'], 'minerais': [mineral], 'municipios': muns, 'processos': procs,
            'projeto': (f"Portfólio de pesquisa de {mineral.lower()} — {g['titular']}" if g['titular'] != TITULAR_INDIVIDUAL else
                        f"Portfólio de pesquisa de {mineral.lower()} — titular individual, processo {procs[0]}"),
            'empresa': g['titular'], 'mineral': mineral,
            'outros': 'NA', 'municipio': muns[0], 'fase': 'Pesquisa mineral', 'maturidade': 'SINAL',
            'estagio': f"{len(procs)} títulos de pesquisa ({fases})", 'status': 'Em pesquisa (situação cadastral na ANM)',
            'data_info': 'NA', 'confianca': 'ALTO',
            'evidencia': (f"{g['titular']} detém {len(procs)} títulos de pesquisa de {mineral.lower()} em Goiás "
                          f"({', '.join(muns[:5])}{' e outros' if len(muns) > 5 else ''})."),
            'fonte': 'ANM — Cadastro Mineiro (alvarás e requerimentos de pesquisa, recorte Goiás)', 'link': URL_ALVARA,
            'outras_evid': 'NA', 'links_add': URL_REQ_PESQ,
            'obs': (f"Linha derivada da ANM: aquisição de direitos minerários (SINAL). Processos: {', '.join(procs[:12])}{' …' if len(procs) > 12 else ''}. "
                    + (f"Municípios: {', '.join(muns)}. " if len(muns) > 1 else '')
                    + 'Título de pesquisa não comprova depósito nem projeto econômico; capacidade, CAPEX e cronograma inexistentes (NA).'),
            'noticia': {'data': 'NA', 'titulo': f"Cadastro Mineiro — títulos de pesquisa de {mineral.lower()} de {g['titular']}",
                        'veiculo': 'Agência Nacional de Mineração', 'tipo': 'Documento oficial/regulatório',
                        'evidencia': f"{len(procs)} títulos de pesquisa de {mineral.lower()} ({fases}) em {', '.join(muns[:6])}.",
                        'relevancia': 'Baixa', 'link': URL_ALVARA, 'acesso': ACESSO_ANM,
                        'obs': 'Arquivos da ANM baixados em 10/09/2026; o cadastro não traz data por título.'}})
    return linhas


# ---------------------------------------------------------------- deduplicação e montagem
def mesmo_mineral(a, b):
    a, b = sem_acento(a), sem_acento(b)
    return a == b or a in b or b in a


def absorvedor(linha, pesquisados):
    """Projeto pesquisado que já representa esta linha da ANM, ou None.

    Mesmo processo basta. Sem processo em comum, exige mesmo CNPJ raiz, mesmo mineral e mesmo município; entre vários candidatos fica
    o de mesmo mineral principal. Títulos de pesquisa só se juntam a projeto pesquisado que também está em pesquisa: em volta de uma
    operação eles são exploração nova, economicamente distinta, e ficam como linha própria de portfólio."""
    for p in pesquisados:
        procs = set(p['_processos'])
        if procs and procs & set(linha['processos']):
            return p
    melhor, nota_melhor = None, 0
    for p in pesquisados:
        apl = p.get('_arranjo') and not linha['cnpj']
        if not apl and (not p['_cnpj_raiz'] or p['_cnpj_raiz'] != linha['cnpj']):
            continue
        if linha['origem'] == 'pesquisa' and 'pesquisa' not in p['fase'].lower():
            continue
        muns = linha['municipios'][:1] if linha['origem'] == 'pesquisa' else linha['municipios']
        if not set(p['_municipios']) & set(muns):
            continue
        outros = [x.strip() for x in re.split(r'[,;()]', p.get('outros') or '') if x.strip()]
        nota = 2 if mesmo_mineral(linha['minerais'][0], p['mineral']) else 1 if any(mesmo_mineral(linha['minerais'][0], x) for x in outros) else 0
        if nota > nota_melhor:
            melhor, nota_melhor = p, nota
    return melhor


def na(v):
    v = '' if v is None else str(v).strip()
    return v if v else 'NA'


def montar(raiz):
    ctx = Contexto(raiz)
    cur = json.loads((raiz / CURADORIA).read_text(encoding='utf-8'))
    pesquisados = cur['projetos']
    fontes = collections.defaultdict(list)
    for f in cur['fontes']:
        fontes[f['chave']].append(f)
    acesso_web = cur['pesquisa']['data_acesso']
    proc_titular = titular_por_processo(ctx)
    ops, sem_titular = operacoes_cfem(ctx, proc_titular)
    carteira, fora = carteira_aba04(ctx)
    port = portfolios(ctx)

    absorvidas = collections.defaultdict(list)
    derivadas = []
    for linha in ops + carteira + port:
        dono = absorvedor(linha, pesquisados)
        if dono:
            absorvidas[dono['chave']].append(linha)
        else:
            derivadas.append(linha)

    ordem = {m: i for i, m in enumerate(HIERARQUIA)}
    pesquisados = sorted(pesquisados, key=lambda p: (ordem[p['maturidade']], sem_acento(p['projeto'])))
    origem_ordem = {'cfem': 0, 'aba04': 1, 'pesquisa': 2}
    derivadas.sort(key=lambda d: (origem_ordem[d['origem']], ordem[d['maturidade']], -d.get('valor', 0), sem_acento(d['mineral']), sem_acento(d['projeto'])))
    total = len(pesquisados) + len(derivadas)
    largura = max(3, len(str(total)))

    projetos, noticias = [], []

    def nova_noticia(pid, proj, f):
        noticias.append({'ID do projeto': pid, 'Projeto': proj['Projeto'], 'Empresa': proj['Empresa'], 'Mineral': proj['Mineral principal'],
                         'Município': proj['Município'], 'Estado': 'GO', 'Data': na(f.get('data')), 'Título': f['titulo'],
                         'Veículo': f['veiculo'], 'Tipo de fonte': f['tipo'], 'Evidência extraída': f['evidencia'],
                         'Relevância': f['relevancia'], 'Link': f['link'], 'Data de acesso': f.get('acesso', acesso_web),
                         'Observações': na(f.get('obs'))})

    n = 0
    for p in pesquisados:
        n += 1
        pid = f'GO-{n:0{largura}d}'
        fs = fontes[p['chave']]
        extra = absorvidas.get(p['chave'], [])
        datas = [f['data'] for f in fs if re.fullmatch(r'\d{4}-\d{2}-\d{2}', f.get('data', ''))] + \
                [nt['data'] for x in extra for nt in (x.get('noticias') or [x['noticia']]) if re.fullmatch(r'\d{4}-\d{2}-\d{2}', nt['data'])]
        linha = {c: na(p.get(CAMPO.get(c))) for c in COLUNAS}
        linha['ID'], linha['Estado'] = pid, 'GO'
        propria = linha['Data da informação mais recente']
        if datas or propria != 'NA':
            linha['Data da informação mais recente'] = max(datas + ([propria] if propria != 'NA' else []))
        outras = [f"{f['veiculo']} — {f['titulo']}" for f in fs if f['link'] != p['link']]
        outras += [f"ANM — {nt['titulo']}" for x in extra for nt in (x.get('noticias') or [x['noticia']])]
        if linha['Outras evidências'] == 'NA' and outras:
            linha['Outras evidências'] = ' | '.join(outras)
        elif outras:
            linha['Outras evidências'] = linha['Outras evidências'] + ' | ' + ' | '.join(outras)
        links = []
        for f in fs:
            if f['link'] != p['link'] and f['link'] not in links:
                links.append(f['link'])
        for x in extra:
            for nt in x.get('noticias') or [x['noticia']]:
                if nt['link'] not in links and nt['link'] != p['link']:
                    links.append(nt['link'])
        linha['Links adicionais'] = '; '.join(links) if links else 'NA'
        if extra:
            linha['Observações'] = (linha['Observações'] if linha['Observações'] != 'NA' else '') + \
                (f" Absorve {len(extra)} registro{'s' if len(extra) > 1 else ''} da ANM do mesmo empreendimento — mesmo titular (ou arranjo "
                 f"produtivo), mineral e município, ou mesmo processo (ver NOTÍCIAS).")
            linha['Observações'] = linha['Observações'].strip()
        projetos.append(linha)
        for f in fs:
            nova_noticia(pid, linha, f)
        for x in extra:
            for nt in x.get('noticias') or [x['noticia']]:
                nova_noticia(pid, linha, nt)

    for d in derivadas:
        n += 1
        pid = f'GO-{n:0{largura}d}'
        linha = {c: na(d.get(CAMPO.get(c))) for c in COLUNAS}
        linha['ID'], linha['Estado'] = pid, 'GO'
        projetos.append(linha)
        for nt in d.get('noticias') or [d['noticia']]:
            nova_noticia(pid, linha, nt)

    for i, x in enumerate(noticias, 1):
        x['ID da notícia'] = f'N-{i:04d}'
    resumo = {'pesquisados': len(pesquisados), 'cfem': sum(d['origem'] == 'cfem' for d in derivadas),
              'aba04': sum(d['origem'] == 'aba04' for d in derivadas), 'portfolios': sum(d['origem'] == 'pesquisa' for d in derivadas),
              'absorvidas': sum(len(v) for v in absorvidas.values()), 'aba04_fora': dict(fora),
              'cfem_sem_titular_processos': len(sem_titular), 'cfem_sem_titular_valor': round(sum(sem_titular.values()))}
    return projetos, noticias, resumo, ctx


# ---------------------------------------------------------------- controle de qualidade
def checar(projetos, noticias, ctx):
    erros = []
    ids = [p['ID'] for p in projetos]
    if len(ids) != len(set(ids)):
        erros.append('ID de projeto repetido')
    data_ok = lambda v: v == 'NA' or re.fullmatch(r'\d{4}-\d{2}-\d{2}', v)
    validos = set(ctx.mun_por_codigo.values())
    vistos_nome = collections.Counter((sem_acento(p['Projeto']), p['Município']) for p in projetos)
    for p in projetos:
        pid = p['ID']
        if p['Estado'] != 'GO':
            erros.append(f'{pid}: fora de Goiás')
        if p['Município'] != 'NA' and p['Município'] not in validos:
            erros.append(f"{pid}: município fora da malha do IBGE para Goiás ({p['Município']!r})")
        if p['Maturidade'] not in HIERARQUIA:
            erros.append(f"{pid}: maturidade fora das sete categorias ({p['Maturidade']!r})")
        if p['Grau de confiança'] not in CONFIANCA:
            erros.append(f"{pid}: confiança inválida ({p['Grau de confiança']!r})")
        for c in ('Data do anúncio', 'Data da informação mais recente'):
            if not data_ok(p[c]):
                erros.append(f'{pid}: {c} fora de AAAA-MM-DD ({p[c]!r})')
        if p['CAPEX'] != 'NA' and p['Moeda CAPEX'] == 'NA':
            erros.append(f'{pid}: CAPEX sem moeda')
        if p['Capacidade anunciada'] != 'NA' and p['Unidade da capacidade'] == 'NA':
            erros.append(f'{pid}: capacidade sem unidade')
        if p['Ano previsto'] != 'NA' and not re.fullmatch(r'\d{4}', p['Ano previsto']):
            erros.append(f"{pid}: ano previsto inválido ({p['Ano previsto']!r})")
        if p['Ano previsto'] != 'NA' and p['Ano previsto'] not in p['Previsão de entrada em operação']:
            erros.append(f'{pid}: previsão de entrada e ano previsto divergem')
        if not p['Link principal'].startswith('http'):
            erros.append(f'{pid}: sem link principal')
        if p['Evidência principal'] == 'NA':
            erros.append(f'{pid}: sem evidência principal')
        if vistos_nome[(sem_acento(p['Projeto']), p['Município'])] > 1:
            erros.append(f"{pid}: projeto com mesmo nome e município de outra linha ({p['Projeto']})")
    por_projeto = collections.Counter(x['ID do projeto'] for x in noticias)
    for pid in ids:
        if not por_projeto[pid]:
            erros.append(f'{pid}: projeto sem nenhuma fonte na aba NOTÍCIAS')
    for x in noticias:
        if x['ID do projeto'] not in set(ids):
            erros.append(f"{x['ID da notícia']}: aponta para projeto inexistente")
        if not data_ok(x['Data']) or not data_ok(x['Data de acesso']):
            erros.append(f"{x['ID da notícia']}: data fora de AAAA-MM-DD")
        if not x['Link'].startswith('http'):
            erros.append(f"{x['ID da notícia']}: link inválido")
    return erros


# ---------------------------------------------------------------- metodologia e escrita
def metodologia(resumo):
    r = resumo
    return [
        ('Objetivo', 'Base consolidada dos projetos minerais de Goiás — da operação ao sinal inicial de investimento — para inteligência de '
                     'mercado, análise de investimentos e acompanhamento do pipeline mineral do estado. É o Radar de Projetos do Squad 1, '
                     'que completa a camada ANM da base consolidada (aba 04 da v17).'),
        ('Abrangência', 'Os 246 municípios de Goiás e todos os minerais com registro na ANM no estado, de grandes mineradoras a cooperativas, '
                        'juniors, empresas estrangeiras, subsidiárias e projetos de governo (SGB, INB). Projetos fora de Goiás ficam fora, '
                        'mesmo quando a empresa também atua no estado (ex.: Itafós Arraias, no Tocantins).'),
        ('Período da pesquisa', 'Buscas na web feitas em 21/10/2026, com status mais recente até essa data. Dados oficiais da ANM: arquivos '
                                'baixados pelo Squad 1 em 10/09/2026 (CFEM de jan/2022 a jul/2026; Cadastro Mineiro e SIGMINE na situação '
                                'daquela data); camadas do P3M baixadas em 21/10/2026.'),
        ('Fontes', 'Prioridade a fontes primárias: releases, relatórios e comunicados das empresas (ASX, TSX, SEC, RNS/FCA, CVM), estudos de '
                   'pré-viabilidade, documentos de licenciamento e de órgãos públicos (ANM, SGB, BNDES, Semad e SIC de Goiás, prefeituras); '
                   'depois imprensa especializada (Mining Weekly, Mining.com, Northern Miner, Brasil Mineral, Engineering News) e imprensa '
                   'geral e regional (Jornal Opção, O Hoje, O Popular, Times Brasil/CNBC). Dados abertos da ANM: CFEM, Cadastro Mineiro, '
                   'SIGMINE.'),
        ('Origem das linhas', f"Quatro origens, nesta prioridade: (1) pesquisa na web — {r['pesquisados']} projetos com fontes; (2) operações "
                              f"com CFEM em 2025 — {r['cfem']} titulares PJ; (3) carteira da ANM da aba 04 da base consolidada v17 — "
                              f"{r['aba04']} projetos que ainda não produzem (os de pessoa física agregados por mineral e município); (4) portfólios de pesquisa em minerais críticos — "
                              f"{r['portfolios']} conjuntos de títulos. A origem aparece em 'Fonte principal' e nas observações."),
        ('Critérios de inclusão', 'Pesquisa na web: qualquer empreendimento em Goiás com ao menos uma evidência identificável (empresa, mineral, '
                                  'município e situação). Operações: titular PJ com CFEM em 2025; agregados para construção civil (areia, '
                                  'brita e rochas britadas, argila, cascalho, saibro) só a partir de R$ 300 mil no ano. Carteira ANM: projetos '
                                  'da aba 04, exceto agregados e água mineral; os de pessoa física entram agregados por mineral e município, '
                                  'sem nome. Portfólios: titular PJ com 5 ou mais títulos de '
                                  'pesquisa (alvará ou requerimento) de um mesmo mineral crítico ou estratégico (terras raras, níquel, cobre, '
                                  'cobalto, lítio, grafita, nióbio, tântalo, titânio, vanádio, manganês, fosfato, potássio, estanho, '
                                  'tungstênio, fluorita, platina, ouro, diamante).'),
        ('Critérios de exclusão', 'Nome de pessoa física, de empresário individual e de espólio (privacidade: o projeto entra, mas o titular '
                                  'aparece como \'Titular individual (nome não publicado)\' e nenhum CPF é publicado); água mineral e termal; agregados abaixo do limiar; '
                                  'centros de pesquisa e fábricas que não processam minério de mina associada (ex.: centro de terras raras de '
                                  'Catalão, fábrica de argamassa de Edealina); anúncios de venda de áreas em classificados; projetos sem '
                                  'evidência localizada. Da planilha anterior do aluno Lucas Maia saíram: Palma/Alvo Minerals (Palmeirópolis '
                                  'fica no Tocantins), reprocessamento de rejeitos da SAMA (nenhuma fonte encontrada) e calcário da Votorantim '
                                  'em Vila Boa (sem processo nem CFEM no município); as duas linhas de Niquelândia (Wave Nickel e CBA) viraram '
                                  f"uma só. Ficaram sem titular identificável {r['cfem_sem_titular_processos']} processos com CFEM em 2025 "
                                  f"(grupamentos mineiros 960.xxx, R$ {fmt_mil(r['cfem_sem_titular_valor'])}), quase todos de projetos já "
                                  'pesquisados (ex.: Serra Grande).'),
        ('Critérios de maturidade', 'Sete categorias, nesta hierarquia: OPERAÇÃO > EXPANSÃO > CONSTRUÇÃO > DEFINIDO > PROVÁVEL > POSSÍVEL > '
                                    'SINAL. OPERAÇÃO: produz comercialmente (inclui toda linha com CFEM recolhida em 2025). EXPANSÃO: '
                                    'operação com projeto formal de aumento de capacidade em execução. CONSTRUÇÃO: obra iniciada. DEFINIDO: '
                                    'viabilidade concluída, decisão de investimento, financiamento, licença de instalação ou projeto aprovado. '
                                    'PROVÁVEL: viabilidade em curso, licenciamento avançado, recurso relevante, CAPEX ou cronograma divulgados, '
                                    'retomada em andamento. POSSÍVEL: estágio inicial com evidência razoável (recurso inicial, sondagem com '
                                    'resultados, ativo público em leilão). SINAL: direitos minerários, pesquisa inicial, anúncio preliminar. '
                                    'Fase e maturidade são colunas diferentes. Nas linhas da carteira ANM vale a regra do Squad 1 (aba 04): '
                                    'título de lavra concedido sem CFEM e com evento recente = PROVÁVEL; pesquisa aprovada com lavra requerida '
                                    'ou a requerer = POSSÍVEL; sem evento há 3 anos ou em disputa = SINAL; o teto é PROVÁVEL.'),
        ('Regras de deduplicação', 'Um empreendimento, uma linha; cada notícia, documento ou registro oficial é uma linha da aba NOTÍCIAS ligada '
                                   'pelo ID do projeto. Foram comparados nome, empresa, CNPJ raiz, município, mineral, processos da ANM, '
                                   'depósito e planta. Registros da ANM do mesmo titular, mineral e município de um projeto pesquisado não '
                                   f"viram linha nova: entram como evidência dele ({r['absorvidas']} registros absorvidos). Ficam separados "
                                   'empreendimentos economicamente distintos da mesma empresa (ex.: operação de Chapada, expansão Saúva e '
                                   'depósito Suruca; Barro Alto e Codemin; operação e expansão da Serra Verde). A planta-piloto da Aclara em '
                                   'Aparecida de Goiânia é a primeira etapa do Projeto Carina e foi tratada como evidência dele.'),
        ('Regras de tratamento de CAPEX', 'Só CAPEX divulgado publicamente, no valor, moeda e ano da fonte (ex.: 680,5 US$ milhões de 2025). Nada '
                                          'é estimado nem convertido; valores de aquisição, financiamento e anúncios políticos de investimento não '
                                          'são CAPEX e ficam nas observações. CAPEX de anos e moedas diferentes não se somam. Ano do CAPEX = NA '
                                          'quando a fonte não traz.'),
        ('Regras de capacidade', 'Só capacidade explicitamente anunciada, na unidade original (t/ano de minério, t/ano de TREO, Mt/ano de '
                                 'cimento). Meta de estabilização, produção estimada em estudo e potencial geológico não são capacidade e ficam '
                                 'nas observações. Produção anual: o último ano fechado publicado pela empresa, com a unidade e o ano. A '
                                 'quantidade comercializada da CFEM não é produção e aparece só nas observações.'),
        ('Regras para previsão de entrada', 'A previsão mais recente encontrada, com a precisão da fonte (ano, semestre, trimestre ou mês); '
                                            'Ano previsto é o ano dessa previsão. Mudanças de previsão ficam nas observações. NA quando não '
                                            'há cronograma.'),
        ('Critérios de confiança', 'ALTO: fonte primária (empresa, regulador, órgão público, dado oficial da ANM/SGB) atribuída ao fato. MÉDIO: '
                                   'imprensa especializada confiável ou várias fontes independentes consistentes. BAIXO: fonte secundária, '
                                   'notícia antiga ou sem data, evidência indireta ou contradita por dado oficial. Linhas de confiança baixa '
                                   'ficaram quando relevantes, marcadas como BAIXO.'),
        ('Fontes conflitantes', 'Prioridade: documento oficial/regulatório, empresa, órgão público, estudo técnico, imprensa especializada, '
                                'imprensa geral, outras; e a informação mais recente. Divergências ficam nas observações (ex.: 6.400 × 6.500 '
                                't de TREO na Serra Verde; 200 × 500 t de argila na planta-piloto da Aclara; retomada da Pilar Gold × ausência '
                                'de CFEM de ouro em Pilar de Goiás).'),
        ('Identificadores', 'Projetos: GO- seguido de número sequencial, com quatro dígitos porque a base passa de 999 projetos (GO-0001); '
                            'os pesquisados na web vêm primeiro, por maturidade, e depois as linhas derivadas da ANM. Notícias: N-0001. '
                            'Cada notícia aponta para o ID do projeto. Grupos com mais de cinco projetos da ANM (garimpos, arranjos '
                            'produtivos) têm uma evidência-resumo com a lista de processos, em vez de uma linha por processo.'),
        ('Significado de NA', 'Informação não disponível nas fontes consultadas. NA nunca é zero nem estimativa.'),
        ('Limitações da pesquisa', 'O ambiente de coleta bloqueia o acesso direto aos sites: as fontes foram localizadas e lidas pelo buscador, '
                                   'e os documentos citados não foram abertos um a um; nenhum número foi conferido no PDF de origem. Algumas '
                                   'páginas não exibem data (Data = NA). A exaustividade é limitada pelo que está publicado: muitos projetos '
                                   'pequenos só existem nos registros da ANM, que não trazem capacidade, CAPEX nem cronograma. Os títulos de '
                                   'pesquisa não comprovam depósito. A situação da ANM é a de 10/09/2026. Os IDs são estáveis para esta '
                                   'versão; nova coleta pode renumerar as linhas derivadas da ANM.'),
        ('Como atualizar', 'Editar Squad 1/Radar de Projetos/curadoria_web.json (projetos e fontes da web) e rodar python '
                           'scripts/build_projetos_minerais_goias.py; o gerador relê a ANM e a aba 04, deduplica, roda o controle de '
                           'qualidade e recusa a planilha se algum projeto ficar sem fonte, com município fora de Goiás, maturidade ou '
                           'confiança fora do vocabulário, data fora de AAAA-MM-DD ou notícia ligada a ID inexistente.'),
    ]


def escrever(caminho, projetos, noticias, resumo):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter
    wb = Workbook()
    fonte = Font(name='Arial', size=9)
    cab_fonte = Font(name='Arial', size=9, bold=True, color='FFFFFF')
    cab_fill = PatternFill('solid', start_color='0F4C81')
    larguras = {'ID': 9, 'Projeto': 42, 'Empresa': 30, 'Empresa controladora': 24, 'Parceiros / JV': 20, 'Mineral principal': 14,
                'Outros minerais': 20, 'Município': 18, 'Estado': 7, 'Fase': 24, 'Maturidade': 12, 'Estágio detalhado': 30,
                'Status atual': 30, 'Evidência principal': 60, 'Fonte principal': 34, 'Link principal': 40, 'Outras evidências': 50,
                'Links adicionais': 40, 'Observações': 60, 'Título': 44, 'Evidência extraída': 60, 'Link': 40, 'Veículo': 26,
                'Tipo de fonte': 20, 'ID da notícia': 10, 'ID do projeto': 10}

    def aba(ws, colunas, linhas):
        ws.append(colunas)
        for c in ws[1]:
            c.font, c.fill = cab_fonte, cab_fill
            c.alignment = Alignment(wrap_text=True, vertical='center')
        for linha in linhas:
            ws.append([linha[c] for c in colunas])
        for row in ws.iter_rows(min_row=2):
            for c in row:
                c.font = fonte
                c.alignment = Alignment(wrap_text=True, vertical='top')
        for i, c in enumerate(colunas, 1):
            ws.column_dimensions[get_column_letter(i)].width = larguras.get(c, 14)
        ws.freeze_panes = 'C2' if colunas[0] == 'ID' else 'B2'
        ws.auto_filter.ref = ws.dimensions
        ws.row_dimensions[1].height = 30

    ws = wb.active
    ws.title = 'PROJETOS'
    aba(ws, COLUNAS, projetos)
    aba(wb.create_sheet('NOTÍCIAS'), COLUNAS_NOT, noticias)
    wm = wb.create_sheet('METODOLOGIA')
    wm.append(['Parâmetro', 'Descrição'])
    for c in wm[1]:
        c.font, c.fill = cab_fonte, cab_fill
    for k, v in metodologia(resumo):
        wm.append([k, v])
    for row in wm.iter_rows(min_row=2):
        row[0].font = Font(name='Arial', size=9, bold=True)
        row[1].font = fonte
        for c in row:
            c.alignment = Alignment(wrap_text=True, vertical='top')
    wm.column_dimensions['A'].width = 28
    wm.column_dimensions['B'].width = 120
    wm.freeze_panes = 'A2'
    caminho.parent.mkdir(parents=True, exist_ok=True)
    wb.save(caminho)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--repo', type=Path, default=RAIZ)
    ap.add_argument('--saida', type=Path)
    ap.add_argument('--checar', action='store_true', help='só controle de qualidade e contagens, sem escrever')
    args = ap.parse_args()
    projetos, noticias, resumo, ctx = montar(args.repo)
    erros = checar(projetos, noticias, ctx)
    cont = collections.Counter(p['Maturidade'] for p in projetos)
    print(json.dumps({**resumo, 'projetos': len(projetos), 'noticias': len(noticias),
                      'por_maturidade': {m: cont[m] for m in HIERARQUIA}}, ensure_ascii=False), file=sys.stderr)
    if erros:
        raise SystemExit('Controle de qualidade recusou a planilha:\n- ' + '\n- '.join(erros[:80]))
    if not args.checar:
        saida = args.saida or args.repo / SAIDA
        escrever(saida, projetos, noticias, resumo)
        print(f'{saida}: {len(projetos)} projetos, {len(noticias)} notícias', file=sys.stderr)


if __name__ == '__main__':
    main()
