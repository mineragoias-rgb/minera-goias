import importlib
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'Squad 3'/'backend'))
import auth
import main

class WebTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.env=patch.dict(os.environ,{'AUTH_DB_PATH':self.tmp.name+'/auth.sqlite','COOKIE_SECURE':'1'})
        self.env.start()
        with auth.database() as c:
            for name,role,change in [('admin','admin',0),('reader','user',0),('initial','user',1)]:
                c.execute('INSERT INTO users(username,name,password_hash,role,must_change) VALUES (?,?,?,?,?)',
                    (name,name,auth.password_hash('long-test-password'),role,change))
        self.client=TestClient(main.app,base_url='https://testserver')
    def tearDown(self):
        self.env.stop(); self.tmp.cleanup()
    def login(self,name):
        r=self.client.post('/api/auth/login',json={'username':name,'password':'long-test-password'})
        self.assertEqual(r.status_code,200)
        return {'X-CSRF-Token':r.json()['csrf']}
    def test_anonymous_and_reader_cannot_administer(self):
        self.assertEqual(self.client.get('/api/dashboard').status_code,401)
        self.assertEqual(self.client.get('/api/admin/users').status_code,401)
        self.login('reader')
        self.assertEqual(self.client.get('/api/admin/users').status_code,403)
        self.assertEqual(self.client.post('/api/admin/users',json={'username':'new','name':'New','password':'safe-long-password','role':'admin'}).status_code,403)
    def test_cookie_and_csrf_and_logout_revocation(self):
        headers=self.login('admin')
        token=self.client.cookies.get(auth.COOKIE)
        self.assertEqual(self.client.post('/api/auth/logout',json={}).status_code,403)
        self.assertEqual(self.client.post('/api/auth/logout',json={},headers=headers).status_code,200)
        self.client.cookies.set(auth.COOKIE,token)
        self.assertEqual(self.client.get('/api/auth/me').status_code,401)
    def test_force_change_and_session_revocation(self):
        headers=self.login('initial')
        self.assertEqual(self.client.get('/api/dashboard').status_code,403)
        r=self.client.post('/api/auth/password',headers=headers,json={'current_password':'long-test-password','new_password':'changed-long-password'})
        self.assertEqual(r.status_code,200)
        self.assertEqual(self.client.get('/api/auth/me').status_code,401)
        r=self.client.post('/api/auth/login',json={'username':'initial','password':'changed-long-password'})
        self.assertEqual(r.json()['user']['must_change'],0)
        cookie=r.headers['set-cookie'].lower()
        self.assertIn('secure',cookie);self.assertIn('httponly',cookie);self.assertIn('samesite=strict',cookie)
    def test_create_disable_and_revoke(self):
        headers=self.login('admin')
        payload={'username':'new.user','name':'Nova Pessoa','password':'initial-long-password','role':'user'}
        self.assertEqual(self.client.post('/api/admin/users',headers=headers,json=payload).status_code,201)
        self.assertEqual(self.client.post('/api/admin/users',headers=headers,json=payload).status_code,409)
        rows=self.client.get('/api/admin/users').json()
        self.assertTrue(all('password_hash' not in row for row in rows))
        self.assertEqual(self.client.patch('/api/admin/users/1',headers=headers,json={'active':False}).status_code,400)
        self.assertEqual(self.client.patch('/api/admin/users/2',headers=headers,json={'active':False}).status_code,200)
        self.assertEqual(self.client.post('/api/auth/login',json={'username':'reader','password':'long-test-password'}).status_code,401)
    def test_login_rate_limit(self):
        for _ in range(10):
            self.assertEqual(self.client.post('/api/auth/login',json={'username':'missing','password':'incorrect'}).status_code,401)
        self.assertEqual(self.client.post('/api/auth/login',json={'username':'missing','password':'incorrect'}).status_code,429)
    def test_api_supports_both_database_schemas(self):
        from unittest.mock import MagicMock
        for modern in [False,True]:
            conn=MagicMock();cur=conn.cursor.return_value.__enter__.return_value
            cur.fetchall.side_effect=[[{'Field':'processo_anm'}] if modern else [],[]]
            with patch.object(main,'get_connection',return_value=conn):
                self.assertEqual(self.client.get('/api/projetos').status_code,200)
            sql=cur.execute.call_args_list[-1].args[0]
            self.assertIn('processo_anm' if modern else 'project_id',sql)
            if modern:self.assertNotIn('documento_cnpj_cpf',sql.split('FROM')[0])
            conn.close.assert_called_once()

    def test_dashboard_uses_selected_source_and_filter(self):
        self.login('reader')
        import dashboard,json
        def fake(sql,args=()):
            if 'values_json' in sql:
                self.assertEqual(args,('Squad 1/dados/CCEE/parcela_carga_consumo_2024_GO.csv',))
                return [{'values_json':json.dumps(v)} for v in [
                    {'mes_referencia':'202401','cidade':'GOIANIA','ramo_atividade':'MINERAÇÃO'},
                    {'mes_referencia':'202402','cidade':'GOIANIA','ramo_atividade':'MINERAÇÃO'},
                    {'mes_referencia':'202402','cidade':'ANAPOLIS','ramo_atividade':'COMÉRCIO'}]]
            if 'COUNT(DISTINCT' in sql:return [{'files':13,'datasets':83,'records':157665}]
            if 'finished_at' in sql:return []
            return []
        with patch.object(dashboard,'query',side_effect=fake):
            d=self.client.get('/api/dashboard',params={'year':2024,'activity':'MINERAÇÃO'}).json()
        self.assertEqual(d['records'],2);self.assertEqual(d['cities'],1)
        self.assertEqual(sum(x['value'] for x in d['months']),2)
        self.assertEqual(self.client.get('/api/dashboard?year=2000').status_code,422)
if __name__=='__main__':unittest.main()
