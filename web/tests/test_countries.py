import json
import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch, Mock
from starlette.requests import Request
from test_web import WebTests as BaseFixture, signed, module
from server import geo

class CountryTests(unittest.TestCase):
    setUp=BaseFixture.setUp
    tearDown=BaseFixture.tearDown
    # Reuse the isolated account/database fixture, not the base test suite.
    def test_first_login_only_and_failure_does_not_block(self):
        with patch.object(module,'country_for_ip',return_value='RU') as lookup:
            first=self.client.post('/api/auth',json={'init_data':signed(uid=1001)}).json()
            self.client.post('/api/auth',json={'init_data':signed(uid=1001)})
            self.assertEqual(lookup.call_count,1)
            self.assertEqual(first['leaderboard']['country']['code'],'RU')
        with patch.object(module,'country_for_ip',return_value=None) as lookup:
            for _ in range(2):
                response=self.client.post('/api/auth',json={'init_data':signed(uid=1002)})
                self.assertEqual(response.status_code,200)
            self.assertEqual(lookup.call_count,1)
            self.assertIsNone(response.json()['leaderboard']['country']['code'])
            self.assertTrue(response.json()['leaderboard']['country']['can_change'])

    def test_once_only_with_retry_relogin_and_same_country(self):
        with module.db() as con:con.execute("UPDATE users SET country='RU' WHERE id=123")
        def change(code):return self.client.post('/api/country',headers=self.headers,json={'code':code})
        self.assertTrue(change('RU').json()['country']['can_change'])
        self.assertEqual(change('ZZ').status_code,422)
        result=change('DE');self.assertEqual(result.status_code,200)
        self.assertFalse(result.json()['country']['can_change'])
        self.assertEqual(change('DE').status_code,200)
        self.assertEqual(change('RU').status_code,409)
        module.init_db()
        result=self.client.post('/api/auth',json={'init_data':signed()}).json()
        self.assertEqual(result['leaderboard']['country']['code'],'DE')
        self.assertFalse(result['leaderboard']['country']['can_change'])
        self.assertEqual(self.client.post('/api/country',json={'code':'US'}).status_code,401)
        self.assertEqual(change('de').status_code,422)

    def test_concurrent_changes_only_one_wins(self):
        def change(code):return self.client.post('/api/country',headers=self.headers,json={'code':code}).status_code
        with ThreadPoolExecutor(max_workers=2) as pool:statuses=list(pool.map(change,['DE','US']))
        self.assertEqual(sorted(statuses),[200,409])

    def test_separate_country_ranks_top30_and_transfer(self):
        with module.db() as con:
            con.execute("UPDATE users SET country='RU',best=10 WHERE id=123")
            for i in range(35):
                con.execute('INSERT INTO users(id,name,best,best_at,country,country_checked) VALUES(?,?,?,?,?,1)',(2000+i,f'Player{i}',100+i,i,'RU' if i<31 else 'DE'))
        board=self.client.get('/api/leaderboard',headers=self.headers).json()
        self.assertEqual(board['me']['rank'],36)
        self.assertEqual(board['country']['me']['rank'],32)
        self.assertEqual(len(board['top']),30)
        self.assertEqual(len(board['country']['top']),30)
        self.assertTrue(all(row['country']=='RU' for row in board['country']['top']))
        moved=self.client.post('/api/country',headers=self.headers,json={'code':'DE'}).json()
        self.assertEqual(moved['country']['me']['rank'],5)
        self.assertEqual(moved['me']['rank'],36)
        self.assertEqual(moved['me']['score'],10)
        self.assertTrue(all(row['country']=='DE' for row in moved['country']['top']))

del BaseFixture

class GeoTests(unittest.TestCase):
    def request(self,host,headers=()):
        return Request({'type':'http','client':(host,123),'headers':[(k.encode(),v.encode()) for k,v in headers]})
    def test_forwarded_ip_only_from_local_proxy(self):
        self.assertEqual(geo.client_ip(self.request('127.0.0.1',[('x-real-ip','8.8.8.8')])), '8.8.8.8')
        self.assertEqual(geo.client_ip(self.request('1.1.1.1',[('x-real-ip','8.8.8.8'),('x-forwarded-for','8.8.8.8')])), '1.1.1.1')
        self.assertIsNone(geo.client_ip(self.request('127.0.0.1',[('x-forwarded-for','8.8.8.8')])))
        for ip in ['10.0.0.1','invalid','8.8.8.8,1.1.1.1','127.0.0.1']:
            self.assertIsNone(geo.client_ip(self.request('127.0.0.1',[('x-real-ip',ip)])))
        self.assertEqual(geo.client_ip(self.request('::1',[('x-real-ip','2001:4860:4860::8888')])), '2001:4860:4860::8888')
    def test_provider_country_validation_and_timeout(self):
        response=Mock();response.json.return_value={'country_code':'US'}
        with patch.object(geo,'IPINFO_TOKEN','test-only'),patch.object(geo.httpx,'get',return_value=response) as get:
            self.assertEqual(geo.country_for_ip('8.8.8.8'),'US')
            self.assertNotIn('test-only',get.call_args.args[0])
            self.assertEqual(get.call_args.kwargs['timeout'],3)
            response.json.return_value={'country_code':'ZZ'}
            self.assertIsNone(geo.country_for_ip('8.8.8.8'))
        with patch.object(geo,'IPINFO_TOKEN','test-only'),patch.object(geo.httpx,'get',side_effect=geo.httpx.ReadTimeout('timeout')):
            self.assertIsNone(geo.country_for_ip('8.8.8.8'))
    def test_legacy_migration_preserves_scores(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'old.sqlite3'
            con=sqlite3.connect(path)
            con.execute('CREATE TABLE users(id INTEGER PRIMARY KEY,name TEXT NOT NULL,best INTEGER NOT NULL DEFAULT 0,best_at REAL NOT NULL DEFAULT 0)')
            con.execute("INSERT INTO users VALUES(1,'Existing',800,42)");con.commit();con.close()
            with patch.object(module,'DB_PATH',path):
                module.init_db();module.init_db()
                with module.db() as db:
                    row=db.execute('SELECT * FROM users WHERE id=1').fetchone()
                    self.assertEqual(row['best'],800);self.assertEqual(row['best_at'],42)
                    self.assertIsNone(row['country']);self.assertEqual(row['country_checked'],0)
