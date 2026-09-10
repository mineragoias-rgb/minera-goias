"""Server-side accounts and revocable sessions; persistent storage outside Git."""
import hashlib
import hmac
import os
import re
import secrets
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from fastapi import APIRouter, HTTPException, Request, Response, Depends
from pydantic import BaseModel, Field

router = APIRouter(prefix='/api')
COOKIE = 'minera_session'
TTL = 8 * 3600

@contextmanager
def database():
    path = Path(os.getenv('AUTH_DB_PATH', '/srv/minera-goias/shared/auth.sqlite'))
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=15)
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript('''
        CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL, password_hash TEXT NOT NULL, role TEXT NOT NULL CHECK(role IN ('admin','user')),
        active INTEGER NOT NULL DEFAULT 1, must_change INTEGER NOT NULL DEFAULT 1);
        CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY, user_id INTEGER NOT NULL,
        csrf TEXT NOT NULL, expires REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS attempts(key TEXT PRIMARY KEY, count INTEGER NOT NULL, started REAL NOT NULL);
        ''')
        yield conn
        conn.commit()
    finally:
        conn.close()

def password_hash(password):
    salt = secrets.token_hex(16)
    value = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1).hex()
    return salt + ':' + value

def verify(password, stored):
    salt, expected = stored.split(':')
    value = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1).hex()
    return hmac.compare_digest(value, expected)

DUMMY = password_hash('dummy-not-a-real-account')

def public_user(u):
    return {k: u[k] for k in ('id','username','name','role','active','must_change')}

def current_user(request: Request):
    token = request.cookies.get(COOKIE, '')
    with database() as conn:
        u = conn.execute('''SELECT u.*, s.csrf FROM sessions s JOIN users u ON u.id=s.user_id
        WHERE s.token=? AND s.expires>? AND u.active=1''',
        (hashlib.sha256(token.encode()).hexdigest(), time.time())).fetchone()
    if not u:
        raise HTTPException(401, 'Entre na sua conta para continuar.')
    if request.method not in ('GET','HEAD','OPTIONS'):
        if not hmac.compare_digest(request.headers.get('x-csrf-token',''), u['csrf']):
            raise HTTPException(403, 'Sessão inválida. Atualize a página.')
    return dict(u)

def reader(u=Depends(current_user)):
    if u['must_change']:
        raise HTTPException(403, 'Defina uma nova senha antes de continuar.')
    return u

def admin(u=Depends(reader)):
    if u['role'] != 'admin':
        raise HTTPException(403, 'Acesso reservado ao administrador.')
    return u

class Login(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=256)

@router.post('/auth/login')
def login(data: Login, request: Request, response: Response):
    # The proxy trusts only loopback; the socket client is supplied by Uvicorn.
    ip = request.client.host if request.client else 'unknown'
    key = hashlib.sha256(ip.encode()).hexdigest()
    now = time.time()
    with database() as conn:
        conn.execute('DELETE FROM attempts WHERE started<?', (now-900,))
        conn.execute('DELETE FROM sessions WHERE expires<?', (now,))
        attempt = conn.execute('SELECT count FROM attempts WHERE key=?',(key,)).fetchone()
        if attempt and attempt['count'] >= 10:
            raise HTTPException(429, 'Muitas tentativas. Aguarde 15 minutos.')
        conn.execute('INSERT INTO attempts VALUES (?,1,?) ON CONFLICT(key) DO UPDATE SET count=count+1',(key,now))
        conn.commit()
        u = conn.execute('SELECT * FROM users WHERE username=?',(data.username.strip().lower(),)).fetchone()
        valid = verify(data.password, u['password_hash'] if u else DUMMY)
        if not u or not valid or not u['active']:
            raise HTTPException(401, 'Usuário ou senha incorretos.')
        conn.execute('DELETE FROM attempts WHERE key=?',(key,))
        token, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        conn.execute('INSERT INTO sessions VALUES (?,?,?,?)',
                     (hashlib.sha256(token.encode()).hexdigest(),u['id'],csrf,now+TTL))
    response.set_cookie(COOKIE, token, max_age=TTL, secure=os.getenv('COOKIE_SECURE','1')=='1',
                        httponly=True, samesite='strict', path='/api')
    response.headers['Cache-Control'] = 'no-store'
    return {'user':public_user(u),'csrf':csrf}

@router.get('/auth/me')
def me(u=Depends(current_user)):
    return {'user':public_user(u),'csrf':u['csrf']}

@router.post('/auth/logout')
def logout(request: Request, response: Response, u=Depends(current_user)):
    with database() as conn:
        conn.execute('DELETE FROM sessions WHERE token=?',
        (hashlib.sha256(request.cookies.get(COOKIE,'').encode()).hexdigest(),))
    response.delete_cookie(COOKIE,path='/api')
    return {'ok':True}

class Password(BaseModel):
    current_password: str = Field(min_length=1,max_length=256)
    new_password: str = Field(min_length=12,max_length=256)

@router.post('/auth/password')
def change_password(data: Password, u=Depends(current_user)):
    if not verify(data.current_password,u['password_hash']):
        raise HTTPException(400,'A senha atual não confere.')
    if data.new_password == data.current_password:
        raise HTTPException(400,'Escolha uma senha diferente da inicial.')
    with database() as conn:
        conn.execute('UPDATE users SET password_hash=?,must_change=0 WHERE id=?',
                     (password_hash(data.new_password),u['id']))
        conn.execute('DELETE FROM sessions WHERE user_id=?',(u['id'],))
    return {'ok':True}

class NewUser(BaseModel):
    username: str = Field(min_length=3,max_length=80,pattern=r'^[a-z0-9._-]+$')
    name: str = Field(min_length=2,max_length=100)
    password: str = Field(min_length=12,max_length=256)
    role: str = Field(pattern=r'^(admin|user)$')

@router.get('/admin/users')
def users(u=Depends(admin)):
    with database() as conn:
        return [public_user(row) for row in conn.execute('SELECT * FROM users ORDER BY id')]

@router.post('/admin/users',status_code=201)
def create_user(data: NewUser, u=Depends(admin)):
    with database() as conn:
        try:
            conn.execute('INSERT INTO users(username,name,password_hash,role) VALUES (?,?,?,?)',
                         (data.username,data.name,password_hash(data.password),data.role))
        except sqlite3.IntegrityError:
            raise HTTPException(409,'Esse usuário já existe.')
    return {'ok':True}

class UserState(BaseModel):
    active: bool

@router.patch('/admin/users/{user_id}')
def set_active(user_id: int,data: UserState,u=Depends(admin)):
    if user_id == u['id']:
        raise HTTPException(400,'Você não pode desativar a própria conta.')
    with database() as conn:
        result=conn.execute('UPDATE users SET active=? WHERE id=?',(int(data.active),user_id))
        if not result.rowcount:
            raise HTTPException(404,'Usuário não encontrado.')
        conn.execute('DELETE FROM sessions WHERE user_id=?',(user_id,))
    return {'ok':True}
