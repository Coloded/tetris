"""Install the isolated service and add a single Nginx location (run as root)."""
import datetime,os,pwd,shutil,subprocess
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
original=conf.read_text()
marker='    location ^~ /game1500/ {'
if marker not in original:
    backup_dir=Path('/var/backups/game1500-nginx')
    backup_dir.mkdir(parents=True,exist_ok=True,mode=0o700)
    backup=backup_dir/(conf.name+'-'+datetime.datetime.now().strftime('%Y%m%d%H%M%S')+'.bak')
    shutil.copy2(conf,backup)
    needle='    server_name bg.netnum.ru;'
    assert needle in original
    replacement=needle+'\n\n'+(root/'deploy/nginx-location.conf').read_text()
    conf.write_text(original.replace(needle,replacement,1))
    try:subprocess.run(['nginx','-t'],check=True)
    except Exception:
        conf.write_text(original)
        raise
subprocess.run(['systemctl','daemon-reload'],check=True)
subprocess.run(['systemctl','enable','--now','game1500.service','game1500-backup.timer'],check=True)
subprocess.run(['systemctl','restart','game1500.service'],check=True)
subprocess.run(['nginx','-t'],check=True)
subprocess.run(['systemctl','reload','nginx'],check=True)
print('Installed Game1500 at https://bg.netnum.ru/game1500/')
