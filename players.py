"""Shared local player accounts and independent scores for the two games."""
import curses
from i18n import tr
import re
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).with_name("tetris_scores.sqlite3")


class UserExit(Exception):
    pass


class LoginBack(Exception):
    pass


def safe_addstr(stdscr, y, x, text, attr=0):
    try:
        stdscr.addstr(y, x, text, attr)
    except curses.error:
        pass


def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS players (
                name TEXT PRIMARY KEY,
                pin TEXT NOT NULL,
                score INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """CREATE TABLE IF NOT EXISTS runner_scores (
                name TEXT PRIMARY KEY REFERENCES players(name),
                score INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )"""
        )


def top_players(limit=100):
    with sqlite3.connect(DB_PATH) as conn:
        return conn.execute(
            """
            SELECT name, score
            FROM players
            ORDER BY score DESC, updated_at ASC, name ASC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()


def get_player(name):
    with sqlite3.connect(DB_PATH) as conn:
        return conn.execute("SELECT pin, score FROM players WHERE name = ?", (name,)).fetchone()


def create_player(name, pin):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("INSERT INTO players (name, pin, score) VALUES (?, ?, 0)", (name, pin))


def update_best(name, score):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "UPDATE players SET score = ?, updated_at = CURRENT_TIMESTAMP WHERE name = ?",
            (score, name),
        )


def reset_database():
    DB_PATH.unlink(missing_ok=True)
    init_db()


def prompt(stdscr, y, x, label, hidden=False, back=False):
    chars = []
    try:
        curses.curs_set(1)
        stdscr.nodelay(False)
        while True:
            height, width = stdscr.getmaxyx()
            row = min(y, height - 1)
            col = min(x, max(0, width - 2))
            value = "*" * len(chars) if hidden else "".join(chars)
            visible = (label + value)[-max(1, width - col - 2):]
            stdscr.move(row, col)
            stdscr.clrtoeol()
            safe_addstr(stdscr, row, col, visible)
            stdscr.move(row, min(width - 1, col + len(visible)))
            stdscr.refresh()
            ch = stdscr.getch()
            if ch in (10, 13):
                return "".join(chars)
            if ch == 27:
                raise LoginBack if back else UserExit
            if ch in (curses.KEY_BACKSPACE, 127, 8):
                if chars:
                    chars.pop()
            elif 32 <= ch <= 126 and len(chars) < 128:
                chars.append(chr(ch))
    except KeyboardInterrupt as exc:
        raise UserExit from exc
    finally:
        curses.noecho()
        try:
            curses.curs_set(0)
        except curses.error:
            pass
        stdscr.nodelay(False)


def login(stdscr, selected_name=None, new_only=False):
    name_re = re.compile(r"^[A-Za-z0-9]+$")
    while True:
        stdscr.clear()
        safe_addstr(stdscr, 1, 2, tr('Player login - Esc: back'))
        name = selected_name or prompt(stdscr, 3, 2, tr('Player name (A-Z, a-z, 0-9): '), back=True)
        if not name_re.match(name):
            safe_addstr(stdscr, 5, 2, tr('Use only English letters and digits. Press any key...'))
            stdscr.getch()
            continue
        existing = get_player(name)
        if existing and new_only:
            safe_addstr(stdscr, 5, 2, tr('Name taken. Choose another or Esc for the list.'))
            stdscr.getch()
            continue
        if selected_name and not existing:
            raise LoginBack
        if existing:
            safe_addstr(stdscr, 3, 2, tr('Player: {player}', player=name))
            pin = prompt(stdscr, 5, 2, tr("PIN for {name}: ", name=name), hidden=True, back=True)
            if pin == existing[0]:
                return name, existing[1]
            safe_addstr(stdscr, 7, 2, tr('Name taken. Wrong PIN. Press any key to retry.'))
            stdscr.getch()
            continue
        pin = prompt(stdscr, 5, 2, tr("Create PIN for {name} (A-Z, a-z, 0-9): ", name=name), hidden=True, back=True)
        if not name_re.match(pin):
            safe_addstr(stdscr, 7, 2, tr('PIN can contain only English letters and digits. Press any key...'))
            stdscr.getch()
            continue
        try:
            create_player(name, pin)
        except sqlite3.IntegrityError:
            safe_addstr(stdscr, 7, 2, tr('Name taken. Choose another or Esc for the list.'))
            stdscr.getch()
            continue
        return name, 0



def runner_best(name):
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute("SELECT score FROM runner_scores WHERE name = ?", (name,)).fetchone()
        return row[0] if row else 0


def save_runner_best(name, score):
    with sqlite3.connect(DB_PATH) as conn:
        if conn.execute("SELECT 1 FROM players WHERE name = ?", (name,)).fetchone() is None:
            raise ValueError(tr('Unknown player'))
        conn.execute(
            """INSERT INTO runner_scores (name, score) VALUES (?, ?)
            ON CONFLICT(name) DO UPDATE SET
                score = MAX(runner_scores.score, excluded.score),
                updated_at = CURRENT_TIMESTAMP""", (name, score)
        )


def account_rows(game):
    if game == 'tetris':
        return top_players(limit=-1)
    with sqlite3.connect(DB_PATH) as conn:
        return conn.execute(
            """SELECT players.name, COALESCE(runner_scores.score, 0)
            FROM players LEFT JOIN runner_scores USING(name)
            ORDER BY COALESCE(runner_scores.score, 0) DESC, players.name ASC"""
        ).fetchall()


def choose_player(screen, game='tetris', rows=None):
    rows = account_rows(game) if rows is None else rows
    page = 0
    digits = ''
    error = ''
    screen.nodelay(False)
    while True:
        screen.erase()
        height, width = screen.getmaxyx()
        page_size = max(1, height - 8)
        pages = max(1, (len(rows) + page_size - 1) // page_size)
        page = min(page, pages - 1)
        def line(y, text):
            if 0 <= y < height:
                safe_addstr(screen, y, 0, text[:max(0, width - 1)])
        line(0, tr('Players - choose a number or press Enter'))
        line(1, tr('Page {page}/{pages}  Left/Right: pages', page=page+1, pages=pages))
        for i, (name, score) in enumerate(rows[page*page_size:(page+1)*page_size]):
            line(3+i, f'{page*page_size+i+1:3}. {name[:20]:20} {score}')
        if not rows:
            line(3, tr('No players yet.'))
        line(height-4, tr('Number + Enter: PIN | Enter: new player'))
        line(height-3, tr('P: reset database | Q/Esc: quit') if game == 'tetris' else tr('Q/Esc: quit'))
        line(height-2, tr('Player number: {number}', number=digits))
        line(height-1, error)
        screen.refresh()
        key = screen.getch()
        if key in (ord('q'), ord('Q'), 27):
            raise UserExit
        if key in (10, 13):
            if not digits:
                return None
            number = int(digits)
            if 1 <= number <= len(rows):
                return rows[number-1][0]
            error = tr('No such number. Enter a number from the list.')
            digits = ''
        elif ord('0') <= key <= ord('9'):
            if len(digits) < max(3, len(str(len(rows)))):
                digits += chr(key)
            error = ''
        elif key in (curses.KEY_BACKSPACE, 127, 8):
            digits = digits[:-1]
        elif key in (curses.KEY_RIGHT, curses.KEY_NPAGE):
            page = min(page+1, pages-1)
        elif key in (curses.KEY_LEFT, curses.KEY_PPAGE):
            page = max(0, page-1)
        elif key in (ord('p'), ord('P')) and game == 'tetris':
            answer = prompt(screen, height-2, 0, tr('Delete all players/scores? (y/n): '))
            if answer.lower() == 'y':
                reset_database()
                rows = account_rows(game)
                page = 0
                digits = ''


def authenticate(screen, game='tetris', selector=None):
    while True:
        selected = selector(screen) if selector else choose_player(screen, game)
        try:
            return login(screen, selected_name=selected, new_only=selected is None)
        except LoginBack:
            continue
