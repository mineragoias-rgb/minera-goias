# -*- coding: utf-8 -*-
"""Carteira de projetos minerais de Goiás para a aba Mercado (public/data/mercado/projetos_go_v1.json).

    python scripts/build_projetos_go.py                  # usa a raiz do repositório onde está este script
    python scripts/build_projetos_go.py --saida <arquivo>

Lê a planilha levantada pelo aluno Lucas Maia (Squad 1) em `Squad 1/Dados brutos/Aluno Lucas Maia/projetos_minerais_goias.xlsx`,
com três abas — PROJETOS, NOTÍCIAS e METODOLOGIA — e publica as três sem reescrever nada: o texto de cada célula sai como está, e `NA`
vira ausência (`null`), que é o que a própria metodologia da planilha diz que `NA` significa.

O que o gerador faz além de copiar é **recusar** a planilha quando ela sai do próprio vocabulário: ID fora do padrão `GO-000` ou repetido,
maturidade fora das sete etiquetas da hierarquia, confiança fora de ALTO/MÉDIO/BAIXO, data que não é AAAA-MM-DD, projeto fora de Goiás,
notícia que aponta para projeto inexistente, ou "Previsão de entrada" diferente de "Ano previsto".

A capacidade e a produção ficam em texto com a unidade original (t/ano, oz/ano, t/ano de TREO…): unidades diferentes não se somam nem viram
barra na mesma escala. O CAPEX sai em número só porque a planilha declara a moeda e o ano de cada valor; valores de anos diferentes continuam
não somáveis, e a aba não os soma.

Lê o .xlsx com a biblioteca padrão (zip + XML), sem openpyxl, para que o teste de reprodutibilidade rode no CI.
"""
import argparse
import hashlib
import json
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
ORIGEM = Path('Squad 1') / 'Dados brutos' / 'Aluno Lucas Maia' / 'projetos_minerais_goias.xlsx'
SAIDA = Path('public') / 'data' / 'mercado' / 'projetos_go_v1.json'

# A ordem é a da metodologia da planilha: do mais firme ao mais incerto.
HIERARQUIA = ['OPERAÇÃO', 'EXPANSÃO', 'CONSTRUÇÃO', 'DEFINIDO', 'PROVÁVEL', 'POSSÍVEL', 'SINAL']
CONFIANCA = ['ALTO', 'MÉDIO', 'BAIXO']

NS = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main',
      'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
      'rel': 'http://schemas.openxmlformats.org/package/2006/relationships'}


def _texto(no):
    return ''.join(t.text or '' for t in no.iter('{%s}t' % NS['m']))


def _coluna(ref):
    letras = re.match(r'[A-Z]+', ref).group(0)
    n = 0
    for letra in letras:
        n = n * 26 + ord(letra) - 64
    return n - 1


def ler_xlsx(caminho):
    """{nome da aba: [linhas como listas de texto]} — só o que este tipo de planilha usa: texto e número."""
    with zipfile.ZipFile(caminho) as z:
        compartilhadas = []
        if 'xl/sharedStrings.xml' in z.namelist():
            raiz = ET.fromstring(z.read('xl/sharedStrings.xml'))
            compartilhadas = [_texto(si) for si in raiz.findall('m:si', NS)]
        rels = {r.get('Id'): r.get('Target') for r in ET.fromstring(z.read('xl/_rels/workbook.xml.rels')).findall('rel:Relationship', NS)}
        abas = {}
        for aba in ET.fromstring(z.read('xl/workbook.xml')).find('m:sheets', NS):
            alvo = rels[aba.get('{%s}id' % NS['r'])].lstrip('/')
            alvo = alvo if alvo.startswith('xl/') else 'xl/' + alvo
            linhas = []
            for linha in ET.fromstring(z.read(alvo)).iter('{%s}row' % NS['m']):
                valores = {}
                for c in linha.findall('m:c', NS):
                    tipo, v = c.get('t'), c.find('m:v', NS)
                    if tipo == 'inlineStr':
                        valor = _texto(c.find('m:is', NS))
                    elif tipo == 's':
                        valor = compartilhadas[int(v.text)]
                    elif v is not None:
                        valor = v.text
                    else:
                        valor = ''
                    valores[_coluna(c.get('r'))] = valor
                if valores:
                    linhas.append([valores.get(i, '') for i in range(max(valores) + 1)])
            abas[aba.get('name')] = linhas
    return abas


def registros(linhas):
    cabecalho = [h.strip() for h in linhas[0]]
    saida = []
    for linha in linhas[1:]:
        if not any(str(v).strip() for v in linha):
            continue
        linha = list(linha) + [''] * (len(cabecalho) - len(linha))
        saida.append({h: str(v).strip() for h, v in zip(cabecalho, linha)})
    return saida


def na(v):
    return None if v in ('', 'NA') else v


def data_iso(v, campo, ident, erros):
    v = na(v)
    if v is not None and not re.fullmatch(r'\d{4}-\d{2}-\d{2}', v):
        erros.append(f'{ident}: {campo} fora do formato AAAA-MM-DD ({v!r})')
    return v


def numero_br(v):
    """'1.234,5' -> 1234.5. Só para o CAPEX, cuja moeda e ano a planilha declara."""
    n = float(v.replace('.', '').replace(',', '.'))
    return int(n) if n.is_integer() else n


def montar(raiz):
    caminho = raiz / ORIGEM
    abas = ler_xlsx(caminho)
    erros = []
    for nome in ('PROJETOS', 'NOTÍCIAS', 'METODOLOGIA'):
        if nome not in abas:
            erros.append(f'aba {nome} ausente')
    if erros:
        raise SystemExit('\n'.join(erros))

    projetos, vistos = [], set()
    for r in registros(abas['PROJETOS']):
        ident = r['ID']
        if not re.fullmatch(r'GO-\d{3}', ident):
            erros.append(f'{ident!r}: ID fora do padrão GO-000')
        if ident in vistos:
            erros.append(f'{ident}: ID repetido')
        vistos.add(ident)
        if r['Estado'] != 'GO':
            erros.append(f'{ident}: projeto fora de Goiás ({r["Estado"]})')
        if r['Maturidade'] not in HIERARQUIA:
            erros.append(f'{ident}: maturidade fora da hierarquia ({r["Maturidade"]!r})')
        if r['Grau de confiança'] not in CONFIANCA:
            erros.append(f'{ident}: confiança fora de ALTO/MÉDIO/BAIXO ({r["Grau de confiança"]!r})')
        if na(r['Previsão de entrada em operação']) != na(r['Ano previsto']):
            erros.append(f'{ident}: previsão de entrada e ano previsto divergem')
        ano = na(r['Ano previsto'])
        capex = None
        if na(r['CAPEX']):
            if not (na(r['Moeda CAPEX']) and na(r['Ano do CAPEX'])):
                erros.append(f'{ident}: CAPEX sem moeda ou sem ano')
            else:
                capex = {'valor': numero_br(r['CAPEX']), 'moeda': r['Moeda CAPEX'], 'ano': int(r['Ano do CAPEX'])}
        links = [l for l in (na(r['Link principal']), *(na(r['Links adicionais']) or '').split(';')) if l and l.strip()]
        for link in links:
            if not link.strip().startswith('https://'):
                erros.append(f'{ident}: link sem https ({link})')
        projetos.append({
            'id': ident,
            'projeto': r['Projeto'],
            'empresa': r['Empresa'],
            'controladora': na(r['Empresa controladora']),
            'parceiros': na(r['Parceiros / JV']),
            'mineral': r['Mineral principal'],
            'outros_minerais': na(r['Outros minerais']),
            'municipio': r['Município'],
            'fase': r['Fase'],
            'maturidade': r['Maturidade'],
            'estagio': na(r['Estágio detalhado']),
            'status': na(r['Status atual']),
            'capacidade': {'valor': r['Capacidade anunciada'], 'unidade': na(r['Unidade da capacidade'])}
                          if na(r['Capacidade anunciada']) else None,
            'producao': {'valor': r['Produção anual'], 'unidade': na(r['Unidade da produção'])}
                        if na(r['Produção anual']) else None,
            'capex': capex,
            'ano_previsto': int(ano) if ano else None,
            'data_anuncio': data_iso(r['Data do anúncio'], 'data do anúncio', ident, erros),
            'data_informacao': data_iso(r['Data da informação mais recente'], 'data da informação', ident, erros),
            'confianca': r['Grau de confiança'],
            'evidencia': r['Evidência principal'],
            'fonte': r['Fonte principal'],
            'link': na(r['Link principal']),
            'outras_evidencias': na(r['Outras evidências']),
            'links_adicionais': [l.strip() for l in links[1:]],
            'observacoes': na(r['Observações']),
        })

    noticias = []
    for r in registros(abas['NOTÍCIAS']):
        ident = r['ID da notícia']
        if r['ID do projeto'] not in vistos:
            erros.append(f'{ident}: aponta para projeto inexistente ({r["ID do projeto"]})')
        link = na(r['Link'])
        if link and not link.startswith('https://'):
            erros.append(f'{ident}: link sem https ({link})')
        noticias.append({
            'id': ident,
            'projeto_id': r['ID do projeto'],
            'data': data_iso(r['Data'], 'data', ident, erros),
            'titulo': r['Título'],
            'veiculo': r['Veículo'],
            'tipo_fonte': na(r['Tipo de fonte']),
            'evidencia': na(r['Evidência extraída']),
            'relevancia': na(r['Relevância']),
            'link': link,
            'data_acesso': data_iso(r['Data de acesso'], 'data de acesso', ident, erros),
            'observacoes': na(r['Observações']),
        })

    metodologia = [{'parametro': r['Parâmetro'], 'descricao': r['Descrição']} for r in registros(abas['METODOLOGIA'])]
    if erros:
        raise SystemExit('A planilha saiu do próprio vocabulário:\n- ' + '\n- '.join(erros))

    acessos = sorted({n['data_acesso'] for n in noticias if n['data_acesso']})
    return {
        'versao': 'v1',
        'meta': {
            'origem': ORIGEM.as_posix(),
            'sha256_origem': hashlib.sha256(caminho.read_bytes()).hexdigest(),
            'autoria': {'pt': 'Squad 1 · aluno Lucas Maia', 'en': 'Squad 1 · student Lucas Maia'},
            'consultado_ate': acessos[-1] if acessos else None,
            'hierarquia': HIERARQUIA,
            'confianca': CONFIANCA,
            'gerado_por': 'scripts/build_projetos_go.py',
        },
        'metodologia': metodologia,
        'projetos': projetos,
        'noticias': noticias,
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    ap.add_argument('--repo', type=Path, default=RAIZ)
    ap.add_argument('--saida', type=Path)
    args = ap.parse_args()
    pacote = montar(args.repo)
    saida = args.saida or args.repo / SAIDA
    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text(json.dumps(pacote, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(f'{saida}: {len(pacote["projetos"])} projetos, {len(pacote["noticias"])} notícias', file=sys.stderr)


if __name__ == '__main__':
    main()
