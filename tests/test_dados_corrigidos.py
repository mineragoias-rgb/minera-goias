"""Bases corrigidas da ANM: o bruto fica intacto e toda diferença entre bruto e corrigido está no registro."""
import csv
import hashlib
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
BRUTOS = ROOT / 'Squad 1' / 'Dados brutos'
CORRIGIDOS = ROOT / 'Squad 1' / 'Dados corrigidos'
ARQUIVOS = ['ANM - Anuário Mineral Brasileiro (AMB)/Producao_Bruta.csv', 'ANM - Anuário Mineral Brasileiro (AMB)/Producao_Beneficiada.csv',
            'ANM - CFEM/CFEM_Arrecadacao_2022_2026_GO.csv']


def linhas(caminho):
    return caminho.read_bytes().decode('cp1252').split('\r\n')  # read_text troca CRLF por LF


def campos(arquivo, linha):
    return next(csv.reader([linha], delimiter=';' if 'CFEM' in arquivo else ','))


class DadosCorrigidosTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(CORRIGIDOS / 'registro_alteracoes.csv', encoding='utf-8-sig', newline='') as f:
            cls.registro = list(csv.DictReader(f, delimiter=';'))

    def test_toda_diferenca_esta_no_registro(self):
        for arq in ARQUIVOS:
            bruto, corr = linhas(BRUTOS / arq), linhas(CORRIGIDOS / arq)
            self.assertEqual(len(bruto), len(corr), arq)
            cab = campos(arq, bruto[0])
            esperado = {(int(r['linha']), r['coluna']) for r in self.registro if r['arquivo'] == arq}
            achado = set()
            for n, (b, c) in enumerate(zip(bruto, corr), start=1):
                if b == c:
                    continue
                fb, fc = campos(arq, b), campos(arq, c)
                self.assertEqual(len(fb), len(fc), (arq, n))
                for col, x, y in zip(cab, fb, fc):
                    if x != y:
                        achado.add((n, col))
            self.assertEqual(achado, esperado, arq)

    def test_registro_md_lista_cada_celula(self):
        md = (CORRIGIDOS / 'REGISTRO_DE_ALTERACOES.md').read_text(encoding='utf-8')
        for r in self.registro:
            self.assertIn(f"| {r['linha']} | {r['chave']} |", md)
        for arq in ARQUIVOS:  # o registro foi gerado a partir do bruto que está no repositório
            sha = hashlib.sha256((BRUTOS / arq).read_bytes()).hexdigest()
            self.assertIn(sha[:16], md, arq)

    def test_cfem_so_esvazia_quantidade(self):
        for r in self.registro:
            if r['regra'].startswith('CFEM'):
                self.assertEqual(r['coluna'], 'QuantidadeComercializada')
                self.assertEqual(r['depois'], '(vazia)')


if __name__ == '__main__':
    unittest.main()
