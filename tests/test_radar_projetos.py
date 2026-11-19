"""Radar de Projetos de Goiás (Squad 1/Radar de Projetos): a planilha tem de manter o formato pedido e o que o gerador promete."""
import collections
import importlib.util
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PASTA = ROOT / 'Squad 1' / 'Radar de Projetos'
PLANILHA = PASTA / 'projetos_minerais_goias.xlsx'
CURADORIA = PASTA / 'curadoria_web.json'
sys.path.insert(0, str(ROOT / 'scripts'))
from build_projetos_go import ler_xlsx, registros  # noqa: E402  leitor de xlsx só com a biblioteca padrão
import build_projetos_minerais_goias as gerador  # noqa: E402

DATA = re.compile(r'\d{4}-\d{2}-\d{2}')


class RadarDeProjetosTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        abas = ler_xlsx(PLANILHA)
        cls.abas = abas
        cls.projetos = registros(abas['PROJETOS'])
        cls.noticias = registros(abas['NOTÍCIAS'])
        atlas = json.loads((ROOT / 'data' / 'atlas' / 'atlas.json').read_text(encoding='utf-8'))
        cls.municipios = {m['name'] for m in atlas['municipalities']}

    def test_tres_abas_com_as_colunas_pedidas(self):
        self.assertEqual(list(self.abas), ['PROJETOS', 'NOTÍCIAS', 'METODOLOGIA'])
        self.assertEqual([h.strip() for h in self.abas['PROJETOS'][0]], gerador.COLUNAS)
        self.assertEqual([h.strip() for h in self.abas['NOTÍCIAS'][0]], gerador.COLUNAS_NOT)
        parametros = {r['Parâmetro'] for r in registros(self.abas['METODOLOGIA'])}
        for tema in ('Objetivo', 'Abrangência', 'Período da pesquisa', 'Fontes', 'Critérios de inclusão', 'Critérios de exclusão',
                     'Critérios de maturidade', 'Regras de deduplicação', 'Regras de tratamento de CAPEX', 'Regras de capacidade',
                     'Regras para previsão de entrada', 'Critérios de confiança', 'Significado de NA', 'Limitações da pesquisa'):
            self.assertIn(tema, parametros)

    def test_vocabulario_e_ids(self):
        ids = [p['ID'] for p in self.projetos]
        self.assertEqual(len(ids), len(set(ids)))
        largura = len(ids[0]) - 3
        for p in self.projetos:
            self.assertRegex(p['ID'], rf'^GO-\d{{{largura}}}$')
            self.assertEqual(p['Estado'], 'GO')
            self.assertIn(p['Maturidade'], gerador.HIERARQUIA, p['ID'])
            self.assertIn(p['Grau de confiança'], gerador.CONFIANCA, p['ID'])
            self.assertTrue(p['Município'] == 'NA' or p['Município'] in self.municipios, p['ID'])
            for c in ('Data do anúncio', 'Data da informação mais recente'):
                self.assertTrue(p[c] == 'NA' or DATA.fullmatch(p[c]), (p['ID'], c))
            self.assertTrue(p['Link principal'].startswith('http'), p['ID'])

    def test_ausencia_e_na_e_nunca_celula_vazia(self):
        for aba in ('PROJETOS', 'NOTÍCIAS'):
            for linha in self.abas[aba][1:]:
                self.assertTrue(all(str(v).strip() for v in linha), linha[:2])

    def test_cada_projeto_tem_fonte_e_cada_noticia_aponta_para_projeto(self):
        ids = {p['ID'] for p in self.projetos}
        por_projeto = collections.Counter(n['ID do projeto'] for n in self.noticias)
        self.assertEqual(set(por_projeto), ids)
        for n in self.noticias:
            self.assertTrue(n['Link'].startswith('http'), n['ID da notícia'])
            self.assertTrue(n['Data'] == 'NA' or DATA.fullmatch(n['Data']), n['ID da notícia'])
            self.assertTrue(DATA.fullmatch(n['Data de acesso']), n['ID da notícia'])

    def test_capex_e_capacidade_com_unidade_e_previsao_coerente(self):
        for p in self.projetos:
            if p['CAPEX'] != 'NA':
                self.assertNotEqual(p['Moeda CAPEX'], 'NA', p['ID'])
            if p['Capacidade anunciada'] != 'NA':
                self.assertNotEqual(p['Unidade da capacidade'], 'NA', p['ID'])
            if p['Ano previsto'] != 'NA':
                self.assertIn(p['Ano previsto'], p['Previsão de entrada em operação'], p['ID'])

    def test_sem_dado_pessoal(self):
        texto = json.dumps(self.abas, ensure_ascii=False)
        self.assertIsNone(re.search(r'\d{3}\.\d{3}\.\d{3}-\d{2}', texto), 'CPF na planilha')
        for p in self.projetos:
            if p['Empresa'] not in (gerador.TITULAR_INDIVIDUAL, gerador.TITULARES_INDIVIDUAIS) and 'Linha derivada da ANM' in p['Observações']:
                self.assertRegex(p['Empresa'], gerador.MARCA_EMPRESA, p['ID'])

    def test_sem_projeto_duplicado(self):
        vistos = collections.Counter((gerador.sem_acento(p['Projeto']), p['Município']) for p in self.projetos)
        self.assertEqual([k for k, n in vistos.items() if n > 1], [])

    def test_curadoria_toda_com_fonte(self):
        cur = json.loads(CURADORIA.read_text(encoding='utf-8'))
        chaves = [p['chave'] for p in cur['projetos']]
        self.assertEqual(len(chaves), len(set(chaves)))
        com_fonte = {f['chave'] for f in cur['fontes']}
        self.assertEqual(set(chaves), com_fonte)
        for p in cur['projetos']:
            self.assertIn(p['maturidade'], gerador.HIERARQUIA, p['chave'])

    @unittest.skipUnless(importlib.util.find_spec('openpyxl') and importlib.util.find_spec('shapefile'),
                         'o gerador precisa de openpyxl e pyshp')
    def test_planilha_bate_com_o_gerador(self):
        projetos, noticias, _, ctx = gerador.montar(ROOT)
        self.assertEqual(gerador.checar(projetos, noticias, ctx), [])
        self.assertEqual([[p[c] for c in gerador.COLUNAS] for p in projetos],
                         [[p[c] for c in gerador.COLUNAS] for p in self.projetos])
        self.assertEqual(len(noticias), len(self.noticias))


if __name__ == '__main__':
    unittest.main()
