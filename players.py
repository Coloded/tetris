"""Shared local player accounts and independent scores for the two games."""
import curses
import re
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).with_name("tetris_scores.sqlite3")


class UserExit(Exception):
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


def prompt(stdscr, y, x, label, hidden=False):
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
                raise UserExit
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


def login(stdscr):
    name_re = re.compile(r"^[A-Za-z0-9]+$")
    while True:
        stdscr.clear()
        safe_addstr(stdscr, 1, 2, "Player login - Esc: quit")
        name = prompt(stdscr, 3, 2, "Player name (A-Z, a-z, 0-9): ")
        if not name_re.match(name):
            safe_addstr(stdscr, 5, 2, "Use only English letters and digits. Press any key...")
            stdscr.getch()
            continue
        existing = get_player(name)
        if existing:
            pin = prompt(stdscr, 5, 2, f"PIN for {name}: ", hidden=True)
            if pin == existing[0]:
                return name, existing[1]
            safe_addstr(stdscr, 7, 2, "Name taken. Wrong PIN. Press any key to retry.")
            stdscr.getch()
            continue
        pin = prompt(stdscr, 5, 2, f"Create PIN for {name} (A-Z, a-z, 0-9): ", hidden=True)
        if not name_re.match(pin):
            safe_addstr(stdscr, 7, 2, "PIN can contain only English letters and digits. Press any key...")
            stdscr.getch()
            continue
        create_player(name, pin)
        return name, 0



def runner_best(name):
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute("SELECT score FROM runner_scores WHERE name = ?", (name,)).fetchone()
        return row[0] if row else 0


def save_runner_best(name, score):
    with sqlite3.connect(DB_PATH) as conn:
        if conn.execute("SELECT 1 FROM players WHERE name = ?", (name,)).fetchone() is None:
            raise ValueError("Unknown player")
        conn.execute(
            """INSERT INTO runner_scores (name, score) VALUES (?, ?)
            ON CONFLICT(name) DO UPDATE SET
                score = MAX(runner_scores.score, excluded.score),
                updated_at = CURRENT_TIMESTAMP""", (name, score)
        )
