import json,unittest
from test_web import WebTests as Fixture,signed,module
from server.engine import Engine
class PrivacyTests(unittest.TestCase):
    setUp=Fixture.setUp
    tearDown=Fixture.tearDown
    start=Fixture.start
    def account(self,uid):
        data=self.client.post('/api/auth',json={'init_data':signed(uid=uid,name=f'Name{uid}')}).json()
        return {'Authorization':'Bearer '+data['token']}
    def toggle(self,hidden):return self.client.post('/api/privacy',headers=self.headers,json={'hidden':hidden})
    def test_owner_only_world_and_country_and_unhide(self):
        other=self.account(200);third=self.account(201);secret=self.account(202)
        with module.db() as con:
            for uid,score,hidden in [(123,500,0),(200,900,0),(201,200,0),(202,1000,1)]:
                con.execute("UPDATE users SET best=?,hidden=?,country='RU' WHERE id=?",(score,hidden,uid))
        own=self.toggle(True).json()
        self.assertTrue(own['privacy']['hidden']);self.assertEqual(own['me']['rank'],2)
        self.assertEqual(own['country']['me']['rank'],2)
        self.assertEqual(len(own['top']),3)
        self.assertNotIn('Name202',json.dumps(own))
        public=self.client.get('/api/leaderboard',headers=third).json()
        self.assertEqual(public['me']['rank'],2)
        self.assertEqual(len(public['top']),2)
        self.assertEqual(len(public['country']['top']),2)
        self.assertFalse(any(r['name']=='Анна Тест' for r in public['top']))
        self.toggle(False)
        self.assertEqual(self.client.get('/api/leaderboard',headers=third).json()['me']['rank'],3)
    def test_persistence_idempotence_and_authorization(self):
        first=self.toggle(True).json()['privacy']
        self.assertEqual(self.toggle(True).json()['privacy'],first)
        module.init_db()
        login=self.client.post('/api/auth',json={'init_data':signed()}).json()
        self.assertEqual(login['leaderboard']['privacy'],first)
        self.assertEqual(self.client.post('/api/privacy',json={'hidden':True}).status_code,401)
        for payload in [{'hidden':'true'},{'hidden':1},{'hidden':True,'id':200}]:
            self.assertEqual(self.client.post('/api/privacy',headers=self.headers,json=payload).status_code,422)
        self.assertGreater(self.toggle(False).json()['privacy']['version'],first['version'])
    def test_hidden_player_still_saves_scores(self):
        other=self.account(200);self.toggle(True);game=self.start();e=Engine(1)
        e.piece='I';e.shape=[[0,0],[1,0],[2,0],[3,0]];e.x=3;e.board[19]=['J']*3+[None]*4+['J']*3
        with module.db() as con:con.execute('UPDATE games SET state=? WHERE id=?',(json.dumps(e.export()),game))
        result=self.client.post(f'/api/games/{game}/steps',headers=self.headers,json={'seq':1,'ticks':1,'actions':[[0,'drop']]}).json()
        self.assertEqual(result['leaderboard']['me']['score'],100)
        self.assertTrue(result['leaderboard']['privacy']['hidden'])
        self.assertEqual(len(self.client.get('/api/leaderboard',headers=other).json()['top']),1)
    def test_replayed_response_does_not_leak_now_hidden_names(self):
        other=self.account(200)
        game=self.start();body={'seq':1,'ticks':1,'actions':[]};url=f'/api/games/{game}/steps'
        response=self.client.post(url,headers=self.headers,json=body).json()
        response['passed']=['Name200 Тест'];response['passed_country']=['Name200 Тест']
        with module.db() as con:
            con.execute('UPDATE games SET last_response=? WHERE id=?',(json.dumps(response),game))
        self.client.post('/api/privacy',headers=other,json={'hidden':True})
        retry=self.client.post(url,headers=self.headers,json=body).json()
        self.assertNotIn('Name200',json.dumps(retry))
        self.assertEqual(retry['passed'],[]);self.assertEqual(retry['passed_country'],[])
    def test_hidden_rows_do_not_reduce_public_top30(self):
        with module.db() as con:
            for i in range(70):
                con.execute('INSERT INTO users(id,name,best,best_at,hidden) VALUES(?,?,?,?,?)',(1000+i,f'P{i}',1000-i,0,int(i<35)))
        result=self.client.get('/api/leaderboard',headers=self.headers).json()
        self.assertEqual(len(result['top']),30)
        self.assertEqual(result['top'][0]['name'],'P35')
        self.assertEqual(result['me']['rank'],36)
del Fixture
