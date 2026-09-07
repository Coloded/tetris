# Game1500 Telegram Tetris

Live: https://bg.netnum.ru/game1500/
Bot: https://t.me/Game1500_bot — launch with its **Играть / Play** menu button.

A Python/FastAPI backend with a plain JavaScript Canvas client. No frontend
build step. Uses the seven original PNG assets in `assets/tetrominoes/`.
The browser samples individual cells from these originals at runtime; source
PNGs are preserved. `prompts.json` records the original imagegen prompts.

## Play

- Fixed 10 × 20 board for every player; seven-bag randomizer, next piece, ghost.
- Arrow keys: move, rotate, soft drop. Space: hard drop. P: pause.
- Touch buttons support press-and-hold movement. Switching away pauses play.
- A 400 ms contact delay allows adjustment; at most 15 movement resets.
- Lines score 100 / 300 / 500 / 800 × level. Level rises every ten lines.
- Russian/English selector; initial language follows Telegram/browser settings.
- Ordinary browser launches offer practice with no identity or saved records.
- Top 30, current rank even outside the top, and overtaking congratulations.

## Identity and records

Only Telegram ID and the Telegram first/last name from server-validated
`initData` establish the account. There is no PIN, editable nickname or name
registration. Names refresh on login and are rendered as text. Telegram IDs
are not returned in leaderboard entries. Terminal accounts remain separate.

The backend checks Telegram's HMAC and a five-minute launch age, then creates
a 24-hour bearer session (only its hash is stored). Bot tokens never enter
browser assets. Starting a new ranked game closes the user's previous one.

The client runs deterministic 50 Hz simulation for responsive input and sends
ordered batches about once per second. The server replays moves using its own
state/seed, computes scores, bounds simulation speed against elapsed real time,
and saves records transactionally in SQLite. Retries are idempotent. This
prevents arbitrary submitted scores; it is not protection against automated
players. Network failure pauses play and retries unsent moves. Closing the app
before an upload finishes can lose the last unsent moves, not saved records.
Games expire after two hours. Ranking refreshes on uploads and every 15 seconds.

## Development

```sh
cd web
python3 -m venv .venv
.venv/bin/pip install -r requirements.lock
.venv/bin/python -m uvicorn server.app:app --host 127.0.0.1 --port 8765
```

Without `BOT_TOKEN`, practice works and Telegram login returns 503. Set the token
through the environment for authenticated launches; never commit `.env`.
`GAME_DB` overrides the default `web/data/game.sqlite3`.

```sh
.venv/bin/python -m unittest discover -s tests -v
node --test tests/engine.test.js
```

Tests use isolated temporary databases and synthetic signed launch data. They
cover authentication, account ownership, repeat uploads, invalid moves, score
injection, elapsed-time bounds, persisted scores and Python/JavaScript parity.

## Deployment

Files live in `/var/game1500`. `.env` contains `BOT_TOKEN=...` and is root-only.
The `game1500` service runs as the dedicated unprivileged `game1500` user on
127.0.0.1:8765. SQLite is in `data/`; Nginx strips the `/game1500/` URL prefix.
Only `public/` and `assets/` are served, never the project root or database.

`deploy/install.py` installs service units and the isolated Nginx location.
It backs up changed Nginx configuration under `/var/backups/game1500-nginx`.
`deploy/configure_bot.py` sets and verifies the bot launch menu without printing
credentials. The optional main profile launch button can also be configured in
BotFather with the same HTTPS URL.

`game1500-backup.timer` runs daily at 04:15 server time. It uses SQLite's backup
API, stores consistent snapshots in `data/backups/`, and retains 14 copies.
Game session rows older than seven days are pruned when new games start.

For an update, copy `public/`, `server/`, `assets/`, `deploy/` and the dependency
files, preserving `.env` and `data/`; install requirements into `.venv` and run
`systemctl restart game1500`. Diagnose with `journalctl -u game1500` and verify
`/game1500/api/health`. Never deploy local test launch pages or development tokens.

## World and country rankings

The leaderboard has **All World Top** and a top 30 for the player's stored
country, with independent ranks and overtaking notices. Existing records and
scores are preserved. Flags appear beside names; region labels use the selected
interface language. `public/countries.json` contains the 249 ISO alpha-2 codes
from the public-domain IANA tzdata country table; the server validates choices
against the same list.

On the first authenticated launch (or first launch after this feature was
installed), the server claims a one-time country lookup in SQLite and calls
IPinfo Lite using `IPINFO_TOKEN` from the root-only `.env`. Nginx overwrites
`X-Real-IP` from its connection address; Uvicorn disables automatic proxy-header
interpretation, and only the loopback Nginx peer is trusted. Client-supplied
forwarding headers cannot choose the lookup IP. The profile stores the country
code, not the IP or provider response. VPNs/proxies can affect the initial result.

The lookup is attempted once, even on provider failure, with a three-second
network timeout. A missing country does not block playing or world ranking.
The player may select a country manually **once**, with a clear notice that the
choice is final. Saving the same country is a no-op; retrying a successful save
is idempotent. Atomic database updates prevent concurrent requests bypassing the
limit. Changing country moves the existing record into that country's ranking
without changing the world score/rank. Login and server restarts never reset the
one-change allowance.
