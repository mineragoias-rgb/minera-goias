import importlib.util
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'ingestion' / 'import_repository.py'
spec = importlib.util.spec_from_file_location('ingest', SCRIPT)
ingest = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ingest)


class IngestionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name) / 'repo'
        self.root.mkdir()
        self.db = ingest.Database(sqlite3.connect(':memory:'))
        self.db.initialize()
        self.policy = json.loads(SCRIPT.with_name('policy.json').read_text())

    def tearDown(self):
        self.db.connection.close()
        self.temp.cleanup()

    def scan(self, commit='abc'):
        return ingest.scan(self.db, self.root, 'example/repo', commit, self.policy)

    def test_locale_identifiers_multiline_and_idempotency(self):
        path = self.root / 'dados.csv'
        path.write_bytes('CNPJ;Valor;Descrição\n001234;1.234,56;"Água\nmineral"\n002345;0;Outra\n'.encode('cp1252'))
        first = self.scan()
        self.assertEqual(first['errors'], 0)
        row = self.db.one("SELECT source_row, values_json FROM ingest_current_rows WHERE row_role='data' ORDER BY source_row")
        self.assertEqual(json.loads(row[1]), {'cnpj': '001234', 'valor': '1.234,56', 'descricao': 'Água\nmineral'})
        self.assertEqual(self.db.one('SELECT MAX(source_row) FROM ingest_rows')[0], 4)
        self.scan('new-commit-with-same-data')
        self.assertEqual(self.db.one('SELECT COUNT(*) FROM ingest_versions')[0], 1)
        self.assertEqual(self.db.one('SELECT COUNT(*) FROM ingest_rows')[0], 3)

    def test_updates_and_removed_sources_keep_history(self):
        path = self.root / 'data.csv'
        path.write_text('ano,valor\n2024,1\n')
        self.scan('one')
        path.write_text('ano,valor\n2024,2\n2025,3\n')
        self.scan('two')
        self.assertEqual(self.db.one('SELECT COUNT(*) FROM ingest_versions')[0], 2)
        self.assertEqual(self.db.one("SELECT COUNT(*) FROM ingest_current_rows WHERE row_role='data'")[0], 2)
        path.unlink()
        self.scan('three')
        self.assertEqual(self.db.one('SELECT COUNT(*) FROM ingest_current_rows')[0], 0)
        self.assertEqual(self.db.one('SELECT COUNT(*) FROM ingest_rows')[0], 5)

    def test_invalid_update_retains_previous_and_reports_failure(self):
        path = self.root / 'data.csv'
        path.write_text('name,value\na,1\n')
        self.scan()
        path.write_text('name,value\n"unterminated')
        result = self.scan('bad')
        self.assertEqual(result['errors'], 1)
        self.assertEqual(self.db.one('SELECT COUNT(*) FROM ingest_versions')[0], 1)
        self.assertEqual(self.db.one("SELECT COUNT(*) FROM ingest_current_rows WHERE row_role='data'")[0], 1)
        self.assertEqual(self.db.one('SELECT status FROM ingest_files')[0], 'error')

    def test_demo_symlinks_and_hidden_files(self):
        (self.root / 'projects_demo.csv').write_text('x,y\n1,2\n')
        (self.root / '.env').write_text('secret')
        outside = Path(self.temp.name) / 'outside.csv'
        outside.write_text('x,y\n1,2\n')
        (self.root / 'linked.csv').symlink_to(outside)
        result = self.scan()
        self.assertEqual(len(result['files']), 1)
        self.assertEqual(result['files'][0]['status'], 'demo_excluded')
        self.assertEqual(self.db.one('SELECT COUNT(*) FROM ingest_rows')[0], 0)

    def test_duplicate_headers_and_extra_columns(self):
        (self.root / 'data.csv').write_text('Nome,Nome,\nA,B,C,D\n')
        self.scan()
        row = json.loads(self.db.one("SELECT values_json FROM ingest_rows WHERE row_role='data'")[0])
        self.assertEqual(row, {'nome': 'A', 'nome_2': 'B', 'col_3': 'C', 'col_4': 'D'})

    def test_missing_formula_cache_is_not_zero(self):
        rows = iter([(1, ['Value', 'ID'], {}), (2, [None, '001'], {0: '=1+1'})])
        result = ingest.import_sheet(self.db, Path('new.xlsx'), 'v', 'Sheet', rows, {}, self.policy)
        row = self.db.one("SELECT values_json,formulas_json FROM ingest_rows WHERE row_role='data'")
        self.assertIsNone(json.loads(row[0])['value'])
        self.assertEqual(json.loads(row[1])['value'], '=1+1')
        self.assertEqual(result['warnings']['missing_formula_cache'], 1)


if __name__ == '__main__':
    unittest.main()
