import time,unittest
from unittest.mock import patch
from test_web import WebTests as Fixture, module
class BotTests(unittest.TestCase):
    setUp=Fixture.setUp
    tearDown=Fixture.tearDown
    def update(self,**values):
        return {'update_id':90,'message':{'chat':{'id':100,'type':'private'},'date':int(time.time()),'text':'/start','from':{'language_code':'ru'},**values}}
    def send(self,data,secret='local-test'):
        with patch.object(module,'WEBHOOK_SECRET','local-test'):
            return self.client.post('/api/telegram/webhook',json=data,headers={'X-Telegram-Bot-Api-Secret-Token':secret})
    def test_secret_and_start_reply(self):
        self.assertEqual(self.send(self.update(),'wrong').status_code,403)
        response=self.send(self.update()).json()
        self.assertEqual(response['method'],'sendMessage')
        self.assertIn('меню',response['text'])
        self.assertEqual(response['reply_markup']['inline_keyboard'][0][0]['web_app']['url'],'https://bg.netnum.ru/game1500/')
        self.assertEqual(self.send(self.update()).json(),{'ok':True})
    def test_no_unrequested_replies(self):
        for update in [self.update(text='/help'),self.update(chat={'id':-1,'type':'group'}),self.update(date=int(time.time())-1000)]:
            self.assertEqual(self.send(update).json(),{'ok':True})
    def test_english_start_payload(self):
        update=self.update(text='/start@Game1500_bot hello');update['message']['from']['language_code']='en'
        self.assertIn('bot menu',self.send(update).json()['text'])
del Fixture
