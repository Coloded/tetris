import unittest
from test_web import WebTests as Fixture, signed, module

class DeleteTests(unittest.TestCase):
    setUp=Fixture.setUp
    tearDown=Fixture.tearDown
    start=Fixture.start

    def test_delete_owned_account_revoke_all_sessions_and_recreate(self):
        self.start()
        extra=self.client.post('/api/auth',json={'init_data':signed()}).json()['token']
        other=self.client.post('/api/auth',json={'init_data':signed(uid=456)}).json()['token']
        with module.db() as con:
            con.execute("UPDATE users SET best=900,country='RU',country_changed=1,hidden=1 WHERE id=123")
        result=self.client.post('/api/account/delete',headers=self.headers,json={'confirmed':True})
        self.assertEqual(result.json(),{'deleted':True})
        with module.db() as con:
            for table,column in [('users','id'),('sessions','user_id'),('games','user_id')]:
                self.assertEqual(con.execute(f'SELECT COUNT(*) FROM {table} WHERE {column}=123').fetchone()[0],0)
        for token in [self.headers['Authorization'],'Bearer '+extra]:
            self.assertEqual(self.client.get('/api/leaderboard',headers={'Authorization':token}).status_code,401)
        self.assertEqual(self.client.get('/api/leaderboard',headers={'Authorization':'Bearer '+other}).status_code,200)
        new=self.client.post('/api/auth',json={'init_data':signed()}).json()
        self.assertEqual(new['leaderboard']['me']['score'],0)
        self.assertFalse(new['leaderboard']['privacy']['hidden'])
        self.assertTrue(new['leaderboard']['country']['can_change'])
        # Retry the lost deletion acknowledgement after recreation: keep new user.
        self.assertEqual(self.client.post('/api/account/delete',headers=self.headers,json={'confirmed':True}).json(),{'deleted':True})
        self.assertEqual(self.client.get('/api/leaderboard',headers={'Authorization':'Bearer '+new['token']}).status_code,200)

    def test_confirmation_and_auth_required_no_foreign_id_allowed(self):
        self.assertEqual(self.client.post('/api/account/delete',json={'confirmed':True}).status_code,401)
        for body in [{'confirmed':False},{},{'confirmed':'true'},{'confirmed':True,'id':456}]:
            self.assertEqual(self.client.post('/api/account/delete',headers=self.headers,json=body).status_code,422)
        self.assertEqual(self.client.get('/api/leaderboard',headers=self.headers).status_code,200)

del Fixture
