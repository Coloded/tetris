"""Consistent SQLite backup (including committed WAL data)."""
import sqlite3
from contextlib import closing
from datetime import datetime,timezone
from pathlib import Path
root=Path('/var/game1500/data');dest=root/'backups';dest.mkdir(exist_ok=True,mode=0o700)
path=dest/(datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')+'.sqlite3')
with closing(sqlite3.connect(root/'game.sqlite3')) as source, closing(sqlite3.connect(path)) as target:source.backup(target)
for old in sorted(dest.glob('*.sqlite3'))[:-14]:old.unlink()
