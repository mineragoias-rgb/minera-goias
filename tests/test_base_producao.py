"""Base de produção por empresa: soma igual à aba 12, sem pessoa física identificada e com o publicado ao lado."""
import csv
from collections import defaultdict
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / 'Squad 1' / 'Bases consolidadas' / 'documentacao'


def ler(caminho, sep):
    with open(caminho, encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f, delimiter=sep))


class BaseProducaoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.emp = ler(DOC / 'base_producao' / 'base_producao_empresa_ano.csv', ';')
        cls.est = ler(DOC / 'base_producao' / 'base_producao_estado_ano.csv', ';')
        cls.aba12 = ler(DOC / 'pacote_squad2' / 'interface_squad1_squad2.csv', ',')

    def test_empresas_somam_a_aba_12(self):
        soma, op = defaultdict(float), defaultdict(float)
        for r in self.emp:
            soma[(r['ano'], r['mineral'], r['base'])] += float(r['producao_t'])
        for r in self.aba12:
            if r['nivel_agregacao'] == 'operacao':
                op[(r['year'], r['mineral_name'], r['production_basis'])] += float(r['production_t'] or 0)
        self.assertEqual(set(soma), set(op))
        for k in op:
            self.assertAlmostEqual(soma[k], op[k], delta=max(0.01, 1e-6 * op[k]), msg=k)

    def test_divisao_nao_passa_do_estado(self):
        for r in self.est:
            self.assertLessEqual(float(r['dividida_por_empresa_t']), float(r['producao_estado_t']) * (1 + 1e-6), r)

    def test_minerio_associado_nao_e_dividido(self):
        for r in self.est:
            if r['situacao'].startswith('minério de outro'):
                self.assertEqual(float(r['dividida_por_empresa_t']), 0.0, r)

    def test_pessoa_fisica_sem_nome_nem_cpf(self):
        cpf = re.compile(r'\d{3}\.?\d{3}\.?\d{3}-\d{2}')
        for r in self.emp:
            self.assertNotRegex(';'.join(r.values()), cpf)
            if r['company_id'].startswith('COM_NOME_') or r['empresa'].startswith('pessoa física'):
                self.assertEqual(r['cnpj_raiz'], '', r['company_id'])
            # só CNPJ tem nome: titular sem CNPJ (COM_NOME_) e razão social com CPF mascarado (MEI) aparecem sem nome
            self.assertNotIn('*', r['empresa'], r['company_id'])
            if not r['company_id'].startswith('COM_CNPJ_') and r['company_id'] != 'COM_NAO_IDENTIFICADO':
                self.assertEqual(r['empresa'], 'pessoa física (nome não publicado)', r['company_id'])

    def test_energia_estimada_usa_a_media_do_mineral(self):
        # Sem carga na CCEE, a energia é produção × média dos coeficientes do mineral: o coeficiente é o mesmo em todas essas linhas.
        coef = defaultdict(set)
        for r in self.emp:
            if r['energia_origem'] == 'estimada_media_mineral':
                self.assertIn(r['ano'], ('2024', '2025'), r)
                coef[(r['ano'], r['mineral'], r['base'])].add(round(float(r['coeficiente_mwh_t']), 9))
        self.assertTrue(coef)
        # a energia sai da base de referência do mineral (beneficiada quando existe): nela o coeficiente é um só; na outra base varia
        for ano, mineral in {k[:2] for k in coef}:
            self.assertTrue(any(len(v) == 1 for k, v in coef.items() if k[:2] == (ano, mineral)), (ano, mineral))

    def test_energia_observada_fecha_com_a_carga_da_empresa(self):
        # A carga observada da empresa, repartida entre os minerais, soma a carga inteira (uma base por mineral; o coproduto publicado,
        # como o ouro da Chapada, fica com a diferença).
        por_emp, carga, coprod = defaultdict(dict), {}, defaultdict(float)
        for r in self.emp:
            if r['energia_origem'].startswith('observada'):
                por_emp[(r['ano'], r['company_id'])][r['mineral']] = float(r['energia_mwh'])
                carga[(r['ano'], r['company_id'])] = float(r['energia_ccee_empresa_mwh'])
                m = re.search(r'no concentrado \([^)]*\): ([\d.]+) MWh', r['energia_nota'])
                if m:
                    coprod[(r['ano'], r['company_id'])] = float(m.group(1).replace('.', ''))
        self.assertTrue(carga)
        for k, ms in por_emp.items():
            self.assertAlmostEqual(sum(ms.values()) + coprod[k], carga[k], delta=max(1.0, 1e-3 * carga[k]), msg=k)

    def test_publicado_comparavel_tem_diferenca(self):
        comparaveis = [r for r in self.emp if r['publicado_comparavel'] == 'sim']
        self.assertTrue(comparaveis)
        for r in comparaveis:
            self.assertNotEqual(r['diferenca_base_vs_publicado'], '', r)


if __name__ == '__main__':
    unittest.main()
