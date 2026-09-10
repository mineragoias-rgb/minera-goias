#!/usr/bin/env python3
"""Run on VPS as minera-goias. Prints generated credentials only when creating accounts.
Never redirect output into the repository. Existing accounts are never overwritten.
"""
import argparse
import json
import secrets
import sys
from pathlib import Path
p=argparse.ArgumentParser()
p.add_argument('--backend',default='/srv/minera-goias/current/Squad 3/backend')
p.add_argument('--bootstrap',action='store_true')
p.add_argument('--reset',metavar='USERNAME')
a=p.parse_args()
sys.path.insert(0,str(Path(a.backend).resolve()))
import auth
credentials=[]
with auth.database() as c:
    if a.bootstrap:
        for username,name,role in [('admin','Administrador Minera Goiás','admin'),('usuario','Usuário Minera Goiás','user')]:
            if c.execute('SELECT id FROM users WHERE username=?',(username,)).fetchone():continue
            password=secrets.token_urlsafe(18)
            c.execute('INSERT INTO users(username,name,password_hash,role) VALUES (?,?,?,?)',
                      (username,name,auth.password_hash(password),role))
            credentials.append({'username':username,'password':password,'role':role})
    elif a.reset:
        user=c.execute('SELECT id FROM users WHERE username=?',(a.reset,)).fetchone()
        if not user:raise SystemExit('Usuário não encontrado')
        password=secrets.token_urlsafe(18)
        c.execute('UPDATE users SET password_hash=?,must_change=1 WHERE id=?',(auth.password_hash(password),user['id']))
        c.execute('DELETE FROM sessions WHERE user_id=?',(user['id'],))
        credentials.append({'username':a.reset,'password':password})
    else:p.error('Use --bootstrap ou --reset USERNAME')
print(json.dumps({'url':'https://labfgv.com.br/login.html','accounts':credentials},ensure_ascii=False,indent=2))
