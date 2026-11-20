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

    def test_publicado_comparavel_tem_diferenca(self):
        comparaveis = [r for r in self.emp if r['publicado_comparavel'] == 'sim']
        self.assertTrue(comparaveis)
        for r in comparaveis:
            self.assertNotEqual(r['diferenca_base_vs_publicado'], '', r)


if __name__ == '__main__':
    unittest.main()
