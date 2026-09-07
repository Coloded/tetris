"""Install the isolated service and its Nginx location (run as root)."""
import datetime,os,pwd,re,shutil,subprocess
from pathlib import Path
root=Path('/var/game1500')
try:pwd.getpwnam('game1500')
except KeyError:subprocess.run(['useradd','--system','--home-dir',str(root),'--shell','/usr/sbin/nologin','game1500'],check=True)
user=pwd.getpwnam('game1500');data=root/'data';data.mkdir(exist_ok=True,mode=0o700)
os.chown(data,user.pw_uid,user.pw_gid)
os.chmod(root/'.env',0o600)
for name in ('game1500.service','game1500-backup.service','game1500-backup.timer'):
    shutil.copy2(root/'deploy'/name,Path('/etc/systemd/system')/name)
conf=Path('/etc/nginx/sites-enabled/bg.netnum.ru').resolve()
original=conf.read_text();snippet=(root/'deploy/nginx-location.conf').read_text().rstrip()
marker='    location ^~ /game1500/ {'
if marker in original:
    pattern=r'    location = /game1500 \{[^\n]*\}\n    location \^~ /game1500/ \{.*?\n    \}'
    matches=list(re.finditer(pattern,original,re.S))
    assert len(matches)==1,'Unexpected Game1500 Nginx layout'
    match=matches[0];updated=original[:match.start()]+snippet+original[match.end():]
else:
    needle='    server_name bg.netnum.ru;'
    assert needle in original
    updated=original.replace(needle,needle+'\n\n'+snippet+'\n',1)
if updated!=original:
    backup_dir=Path('/var/backups/game1500-nginx');backup_dir.mkdir(parents=True,exist_ok=True,mode=0o700)
    backup=backup_dir/(conf.name+'-'+datetime.datetime.now().strftime('%Y%m%d%H%M%S')+'.bak')
    shutil.copy2(conf,backup);conf.write_text(updated)
    try:subprocess.run(['nginx','-t'],check=True)
    except Exception:
        conf.write_text(original)
        raise
subprocess.run(['nginx','-t'],check=True)
# Install trusted IP forwarding before the new geolocation code starts.
subprocess.run(['systemctl','reload','nginx'],check=True)
subprocess.run(['systemctl','daemon-reload'],check=True)
subprocess.run(['systemctl','enable','--now','game1500.service','game1500-backup.timer'],check=True)
subprocess.run(['systemctl','restart','game1500.service'],check=True)
print('Installed Game1500 at https://bg.netnum.ru/game1500/')
