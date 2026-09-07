import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import time
from contextlib import contextmanager, asynccontextmanager
from pathlib import Path
from urllib.parse import parse_qsl

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, ConfigDict
from .engine import Engine, ACTIONS

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = Path(os.environ.get('GAME_DB', ROOT / 'data/game.sqlite3'))
BOT_TOKEN = os.environ.get('BOT_TOKEN', '')

@contextmanager
def db():
    con=sqlite3.connect(DB_PATH, timeout=10)
    con.row_factory=sqlite3.Row
    con.execute('PRAGMA foreign_keys=ON')
    try:
        with con: yield con
    finally: con.close()

def init_db():
    DB_PATH.parent.mkdir(parents=True,exist_ok=True)
    with db() as con:
        con.execute('PRAGMA journal_mode=WAL')
        con.executescript('''
        CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,name TEXT NOT NULL,best INTEGER NOT NULL DEFAULT 0,best_at REAL NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES users(id),expires REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS games(id TEXT PRIMARY KEY,user_id INTEGER NOT NULL REFERENCES users(id),started REAL NOT NULL,state TEXT NOT NULL,seq INTEGER NOT NULL DEFAULT 0,finished INTEGER NOT NULL DEFAULT 0,last_hash TEXT,last_response TEXT);
        CREATE INDEX IF NOT EXISTS games_user ON games(user_id);
        CREATE INDEX IF NOT EXISTS users_ranking ON users(best DESC,best_at,id);
        ''')

@asynccontextmanager
async def lifespan(app):
    init_db()
    yield

app=FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)

@app.middleware('http')
async def bounds(request: Request, call_next):
    if request.method=='POST':
        try: size=int(request.headers.get('content-length','0'))
        except ValueError: return JSONResponse({'detail':'Invalid length'},400)
        if size>65536: return JSONResponse({'detail':'Request too large'},413)
        # Also bound requests without Content-Length before JSON decoding.
        body=bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body)>65536: return JSONResponse({'detail':'Request too large'},413)
        request._body=bytes(body)
    response=await call_next(request)
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Referrer-Policy']='no-referrer'
    if request.url.path.startswith('/api/'):
        response.headers['Cache-Control']='no-store'
    return response

class Login(BaseModel):
    model_config=ConfigDict(extra='forbid')
    init_data: str=Field(min_length=1,max_length=16384)

class Batch(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True)
    seq: int=Field(ge=1)
    ticks: int=Field(ge=0,le=500)
    actions: list=Field(default_factory=list,max_length=400)
    finish: bool=False


def telegram_user(raw, now=None):
    if not BOT_TOKEN: raise HTTPException(503,'Telegram is not configured yet')
    now=time.time() if now is None else now
    try:
        pairs=parse_qsl(raw,keep_blank_values=True,strict_parsing=True)
        data=dict(pairs)
        if len(data)!=len(pairs): raise ValueError('duplicate')
        supplied=data.pop('hash')
        check='\n'.join(f'{k}={v}' for k,v in sorted(data.items()))
        secret=hmac.new(b'WebAppData',BOT_TOKEN.encode(),hashlib.sha256).digest()
        expected=hmac.new(secret,check.encode(),hashlib.sha256).hexdigest()
        if not hmac.compare_digest(supplied,expected): raise ValueError('signature')
        age=now-int(data['auth_date'])
        if not -30<=age<=300: raise ValueError('expired')
        user=json.loads(data['user'])
        if type(user.get('id')) is not int or not 0<user['id']<2**63: raise ValueError('id')
        first=user.get('first_name');last=user.get('last_name','')
        if not isinstance(first,str) or not first.strip() or not isinstance(last,str): raise ValueError('name')
        name=' '.join((first+' '+last).split())[:256]
        return user['id'],name
    except (ValueError,KeyError,TypeError,AttributeError):
        raise HTTPException(401,'Invalid or expired Telegram launch. Reopen the Mini App.')


def identity(request):
    auth=request.headers.get('authorization','')
    if not auth.startswith('Bearer ') or len(auth)>256: raise HTTPException(401,'Login required')
    hashed=hashlib.sha256(auth[7:].encode()).hexdigest()
    with db() as con:
        row=con.execute('SELECT user_id FROM sessions WHERE token=? AND expires>?',(hashed,time.time())).fetchone()
    if not row: raise HTTPException(401,'Session expired. Reopen the Mini App.')
    return row['user_id']


def ranking(con,uid):
    sql='SELECT id,name,best,ROW_NUMBER() OVER (ORDER BY best DESC,best_at ASC,id ASC) AS rank FROM users'
    rows=con.execute(f'SELECT * FROM ({sql}) WHERE rank<=30 OR id=? ORDER BY rank',(uid,)).fetchall()
    # Public entries have no Telegram IDs; the current-user flag suffices.
    entries=[{'name':r['name'],'score':r['best'],'rank':r['rank'],'me':r['id']==uid} for r in rows]
    return {'top':[r for r in entries if r['rank']<=30],'me':next(r for r in entries if r['me'])}

@app.get('/api/health')
def health(): return {'ok':True,'telegram_ready':bool(BOT_TOKEN)}

@app.post('/api/auth')
def auth(payload: Login):
    uid,name=telegram_user(payload.init_data)
    token=secrets.token_urlsafe(32);now=time.time()
    with db() as con:
        con.execute('INSERT INTO users(id,name,best_at) VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name',(uid,name,now))
        con.execute('DELETE FROM sessions WHERE expires<?',(now,))
        con.execute('INSERT INTO sessions VALUES(?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),uid,now+86400))
        # Keep a small number of live sessions per user, without storing launch data.
        con.execute('DELETE FROM sessions WHERE user_id=? AND token NOT IN (SELECT token FROM sessions WHERE user_id=? ORDER BY expires DESC LIMIT 5)',(uid,uid))
        board=ranking(con,uid)
    return {'token':token,'player':{'name':name},'leaderboard':board}

@app.get('/api/leaderboard')
def leaderboard(request: Request):
    uid=identity(request)
    with db() as con: return ranking(con,uid)

@app.post('/api/games')
def start(request: Request):
    uid=identity(request);now=time.time();seed=secrets.randbelow(2**32-1)+1
    game_id=secrets.token_urlsafe(18);engine=Engine(seed)
    with db() as con:
        con.execute('BEGIN IMMEDIATE')
        previous=con.execute('SELECT MAX(started) FROM games WHERE user_id=?',(uid,)).fetchone()[0]
        if previous and now-previous<2: raise HTTPException(429,'Wait a moment before restarting')
        con.execute('UPDATE games SET finished=1 WHERE user_id=?',(uid,))
        con.execute('DELETE FROM games WHERE started<?',(now-86400*7,))
        con.execute('INSERT INTO games(id,user_id,started,state) VALUES(?,?,?,?)',(game_id,uid,now,json.dumps(engine.export())))
    return {'id':game_id,'state':engine.export()}

@app.post('/api/games/{game_id}/steps')
def steps(game_id: str, payload: Batch, request: Request):
    uid=identity(request)
    grouped={}
    for item in payload.actions:
        if not isinstance(item,list) or len(item)!=2: raise HTTPException(422,'Invalid action')
        tick,key=item
        if type(tick) is not int or not 0<=tick<payload.ticks or not isinstance(key,str) or key not in ACTIONS: raise HTTPException(422,'Invalid action')
        grouped.setdefault(tick,[]).append(key)
        if len(grouped[tick])>8: raise HTTPException(422,'Too many actions')
    digest=hashlib.sha256(payload.model_dump_json().encode()).hexdigest()
    with db() as con:
        con.execute('BEGIN IMMEDIATE')
        row=con.execute('SELECT * FROM games WHERE id=? AND user_id=?',(game_id,uid)).fetchone()
        if not row: raise HTTPException(404,'Game not found')
        if row['seq']==payload.seq:
            if row['last_hash']!=digest: raise HTTPException(409,'Conflicting retry')
            return json.loads(row['last_response'])
        if row['finished']: raise HTTPException(409,'Game finished or replaced')
        if row['seq']+1!=payload.seq: raise HTTPException(409,'Out of order')
        engine=Engine(state=json.loads(row['state']))
        elapsed=time.time()-row['started']
        if elapsed>7200: raise HTTPException(409,'Game expired')
        if engine.ticks+payload.ticks>int(elapsed*50)+50: raise HTTPException(422,'Game is faster than real time')
        before=ranking(con,uid)
        for tick in range(payload.ticks): engine.step(grouped.get(tick,()))
        con.execute('UPDATE users SET best=?,best_at=? WHERE id=? AND best<?',(engine.score,time.time(),uid,engine.score))
        board=ranking(con,uid)
        passed=[r['name'] for r in before['top'] if not r['me'] and board['me']['rank']<=r['rank']<before['me']['rank'] and r['score']<engine.score]
        response={'seq':payload.seq,'state':engine.export(),'leaderboard':board,'passed':passed,'finished':engine.over or payload.finish}
        con.execute('UPDATE games SET state=?,seq=?,finished=?,last_hash=?,last_response=? WHERE id=?',(json.dumps(engine.export()),payload.seq,int(response['finished']),digest,json.dumps(response),game_id))
    return response

@app.get('/')
def index(): return FileResponse(ROOT/'public/index.html',headers={'Cache-Control':'no-cache'})

app.mount('/assets',StaticFiles(directory=ROOT/'assets'),name='assets')
app.mount('/',StaticFiles(directory=ROOT/'public'),name='public')
