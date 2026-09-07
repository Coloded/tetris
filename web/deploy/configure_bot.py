"""Configure launch menu, /start webhook and bot avatar without exposing tokens."""
import json,os,secrets,subprocess,sys,time
from pathlib import Path
import httpx
ROOT=Path('/var/game1500');URL='https://bg.netnum.ru/game1500/'
config={}
for line in (ROOT/'.env').read_text().splitlines():
    if '=' in line and not line.lstrip().startswith('#'):
        key,value=line.split('=',1);config[key.strip()]=value.strip().strip('\"\'')
token=config['BOT_TOKEN']
def call(method,payload=None,**kwargs):
    result=httpx.post('https://api.telegram.org/bot'+token+'/'+method,json=payload,timeout=20,**kwargs).json()
    if not result.get('ok'):raise RuntimeError('Telegram rejected configuration')
    return result['result']
try:
    me=call('getMe')
    if me['username'].lower()!='game1500_bot':raise RuntimeError('Unexpected bot')
    hook=call('getWebhookInfo')
    if hook.get('url') not in ('',URL+'api/telegram/webhook'):raise RuntimeError('Unexpected existing webhook')
    secret=config.get('WEBHOOK_SECRET')
    if not secret:
        secret=secrets.token_urlsafe(32)
        with (ROOT/'.env').open('a') as file:file.write('\nWEBHOOK_SECRET='+secret+'\n')
        os.chmod(ROOT/'.env',0o600)
    subprocess.run(['systemctl','restart','game1500'],check=True,stdout=subprocess.DEVNULL)
    for attempt in range(20):
        try:
            if httpx.get('http://127.0.0.1:8765/api/health',timeout=1).status_code==200:break
        except httpx.HTTPError:pass
        time.sleep(.25)
    else:raise RuntimeError('Service not ready')
    call('setChatMenuButton',{'menu_button':{'type':'web_app','text':'🎮 Играть / Play','web_app':{'url':URL}}})
    call('setWebhook',{'url':URL+'api/telegram/webhook','secret_token':secret,'allowed_updates':['message'],'max_connections':4})
    call('setMyCommands',{'commands':[{'command':'start','description':'Launch the game'}]})
    call('setMyCommands',{'language_code':'ru','commands':[{'command':'start','description':'Запустить игру'}]})
    with (ROOT/'assets/branding/bot-icon.jpg').open('rb') as image:
        call('setMyProfilePhoto',data={'photo':json.dumps({'type':'static','photo':'attach://avatar'})},files={'avatar':('bot-icon.jpg',image,'image/jpeg')})
    photos=call('getUserProfilePhotos',{'user_id':me['id'],'limit':1})
    hook=call('getWebhookInfo');menu=call('getChatMenuButton')
    assert photos['total_count']>0 and hook['url']==URL+'api/telegram/webhook'
    assert menu['web_app']['url']==URL
    print(json.dumps({'bot':me['username'],'avatar_set':True,'webhook':hook['url'],'menu_url':menu['web_app']['url']},ensure_ascii=False))
except Exception:
    print('Bot configuration failed; credentials and private details omitted.',file=sys.stderr)
    sys.exit(1)
