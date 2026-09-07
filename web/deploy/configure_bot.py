"""Set and verify the bot's launch menu. Never print token-bearing URLs."""
import json,os,sys,urllib.request
from pathlib import Path
URL='https://bg.netnum.ru/game1500/'
if not os.environ.get('BOT_TOKEN'):
    for line in Path('/var/game1500/.env').read_text().splitlines():
        if line.startswith('BOT_TOKEN='):
            os.environ['BOT_TOKEN']=line.split('=',1)[1].strip().strip('\"\'')
token=os.environ['BOT_TOKEN']
def call(method,payload=None):
    body=json.dumps(payload or {}).encode()
    request=urllib.request.Request('https://api.telegram.org/bot'+token+'/'+method,data=body,headers={'Content-Type':'application/json'})
    data=json.load(urllib.request.urlopen(request,timeout=20))
    if not data.get('ok'):raise RuntimeError('Bot API rejected configuration')
    return data['result']
try:
    me=call('getMe')
    if me['username'].lower()!='game1500_bot':raise RuntimeError('Unexpected bot')
    call('setChatMenuButton',{'menu_button':{'type':'web_app','text':'🎮 Играть / Play','web_app':{'url':URL}}})
    menu=call('getChatMenuButton')
    assert menu.get('web_app',{}).get('url')==URL
    print(json.dumps({'bot':me['username'],'menu':menu},ensure_ascii=False))
except Exception:
    print('Bot configuration failed; token and URLs omitted.',file=sys.stderr)
    sys.exit(1)
