import hashlib,hmac,json,random,subprocess,tempfile,time,unittest,sys
from pathlib import Path
from urllib.parse import urlencode
from unittest.mock import patch
from fastapi.testclient import TestClient
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from server import app as module
from server.engine import Engine
ROOT=Path(__file__).resolve().parents[1]
TOKEN='test-token-only'
def signed(uid=123,name='Анна',age=0):
    data={'auth_date':str(int(time.time())-age),'user':json.dumps({'id':uid,'first_name':name,'last_name':'Тест'},ensure_ascii=False)}
    secret=hmac.new(b'WebAppData',TOKEN.encode(),hashlib.sha256).digest()
    data['hash']=hmac.new(secret,'\n'.join(f'{k}={v}' for k,v in sorted(data.items())).encode(),hashlib.sha256).hexdigest()
    return urlencode(data)
class WebTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.patch=patch.multiple(module,DB_PATH=Path(self.tmp.name)/'db.sqlite3',BOT_TOKEN=TOKEN)
        self.patch.start();self.client=TestClient(module.app);self.client.__enter__()
        data=self.client.post('/api/auth',json={'init_data':signed()}).json()
        self.headers={'Authorization':'Bearer '+data['token']}
    def tearDown(self):
        self.client.__exit__(None,None,None);self.patch.stop();self.tmp.cleanup()
    def start(self):return self.client.post('/api/games',headers=self.headers,json={}).json()['id']
    def test_auth_rejects_forgery_expiry_duplicates_and_custom_name(self):
        for raw in [signed()+'x',signed(age=1000),signed()+'&auth_date=1']:
            self.assertEqual(self.client.post('/api/auth',json={'init_data':raw}).status_code,401)
        self.assertEqual(self.client.post('/api/auth',json={'init_data':signed(),'name':'Fake'}).status_code,422)
        self.assertEqual(self.client.get('/api/leaderboard').status_code,401)
        self.assertEqual(self.client.post('/api/games',json={}).status_code,401)
    def test_name_updates_by_id(self):
        data=self.client.post('/api/auth',json={'init_data':signed(name='Новое имя')}).json()
        self.assertEqual(data['player']['name'],'Новое имя Тест');self.assertEqual(len(data['leaderboard']['top']),1)
        self.assertNotIn('id',data['leaderboard']['top'][0])
    def test_batch_retry_score_injection_and_speed(self):
        game=self.start();url=f'/api/games/{game}/steps';body={'seq':1,'ticks':20,'actions':[[0,'left'],[1,'drop']]}
        first=self.client.post(url,headers=self.headers,json=body);self.assertEqual(first.status_code,200,first.text)
        self.assertEqual(first.json(),self.client.post(url,headers=self.headers,json=body).json())
        self.assertEqual(self.client.post(url,headers=self.headers,json={**body,'score':999999}).status_code,422)
        self.assertEqual(self.client.post(url,headers=self.headers,json={**body,'ticks':21}).status_code,409)
        self.assertEqual(self.client.post(url,headers=self.headers,json={**body,'seq':3}).status_code,409)
        self.assertEqual(self.client.post(url,headers=self.headers,json={'seq':2,'ticks':500,'actions':[]}).status_code,422)
    def test_ownership_actions_and_finish(self):
        game=self.start();url=f'/api/games/{game}/steps'
        other=self.client.post('/api/auth',json={'init_data':signed(uid=456)}).json()['token']
        self.assertEqual(self.client.post(url,headers={'Authorization':'Bearer '+other},json={'seq':1,'ticks':1}).status_code,404)
        for actions in [[[0,'cheat']],[[5,'left']],[[False,'drop']],[[0,{}]],[[0,'left']]*9]:
            self.assertEqual(self.client.post(url,headers=self.headers,json={'seq':1,'ticks':1,'actions':actions}).status_code,422)
        self.assertEqual(self.client.post(url,headers=self.headers,json={'seq':1,'ticks':0,'finish':True}).status_code,200)
        self.assertEqual(self.client.post(url,headers=self.headers,json={'seq':2,'ticks':0}).status_code,409)
    def test_server_scores_and_persists_record(self):
        game=self.start();e=Engine(1);e.piece='I';e.shape=[[0,0],[1,0],[2,0],[3,0]];e.x=3;e.y=0;e.board[19]=['J']*3+[None]*4+['J']*3
        with module.db() as con:con.execute('UPDATE games SET state=? WHERE id=?',(json.dumps(e.export()),game))
        body={'seq':1,'ticks':1,'actions':[[0,'drop']]};url=f'/api/games/{game}/steps'
        result=self.client.post(url,headers=self.headers,json=body).json()
        self.assertEqual(result['state']['score'],100);self.assertEqual(result['leaderboard']['me']['score'],100)
        self.client.post(url,headers=self.headers,json=body)
        self.assertEqual(self.client.get('/api/leaderboard',headers=self.headers).json()['me']['score'],100)
    def test_bounds_static_and_missing_token(self):
        self.assertEqual(self.client.post('/api/auth',content='x'*70000).status_code,413)
        self.assertEqual(self.client.get('/').status_code,200)
        self.assertEqual(self.client.get('/.env').status_code,404)
        self.assertEqual(self.client.get('/server/app.py').status_code,404)
        with patch.object(module,'BOT_TOKEN',''):
            self.assertEqual(self.client.post('/api/auth',json={'init_data':signed()}).status_code,503)
    def test_engine_parity(self):
        rng=random.Random(42);cases=[];expected=[]
        for seed in [1,2,9,100,12345,2**32-1]:
            steps=[];e=Engine(seed)
            for tick in range(2000):
                actions=[rng.choice(['left','right','down','rotate','drop'])] if rng.random()<.2 else []
                steps.append(actions);e.step(actions)
            cases.append({'seed':seed,'steps':steps});expected.append(e.export())
        result=subprocess.run(['node',str(ROOT/'tests/replay.mjs')],input=json.dumps(cases),text=True,capture_output=True,check=True)
        self.assertEqual(json.loads(result.stdout),expected)
if __name__=='__main__':unittest.main()
