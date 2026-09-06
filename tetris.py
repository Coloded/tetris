#!/usr/bin/env python3

import curses
import random
import time

from players import (
    UserExit, safe_addstr, init_db, top_players, reset_database, login, update_best,
)


ROWS = 20
COLS = 10
CELL = "[]"

SHAPES = {
    "I": [(0, 0), (1, 0), (2, 0), (3, 0)],
    "O": [(0, 0), (1, 0), (0, 1), (1, 1)],
    "T": [(0, 0), (1, 0), (2, 0), (1, 1)],
    "S": [(1, 0), (2, 0), (0, 1), (1, 1)],
    "Z": [(0, 0), (1, 0), (1, 1), (2, 1)],
    "J": [(1, 0), (1, 1), (0, 2), (1, 2)],
    "L": [(0, 0), (0, 1), (0, 2), (1, 2)],
}

SCORES = {1: 1, 2: 3, 3: 6, 4: 24}
LOCK_DELAY = 0.4
MAX_LOCK_RESETS = 15
MIN_HEIGHT, MIN_WIDTH = 24, 52
SPEEDS = {
    "1": ("Easy", 2.4),
    "2": ("Normal", 1.4),
    "3": ("Medium", 0.8),
    "4": ("Hard", 0.4),
}
PIECE_COLORS = {"I": 1, "O": 2, "T": 3, "S": 4, "Z": 5, "J": 6, "L": 7}


def draw_start(stdscr):
    page = 0
    stdscr.nodelay(False)
    try:
        while True:
            stdscr.erase()
            height, width = stdscr.getmaxyx()
            rows = top_players()
            page_size = max(1, height - 7)
            pages = max(1, (len(rows) + page_size - 1) // page_size)
            page = min(page, pages - 1)
            safe_addstr(stdscr, 0, 0, "Tetris - Top 100")
            safe_addstr(stdscr, 1, 0, f"Page {page + 1}/{pages}  Left/Right: pages")
            for i, (name, score) in enumerate(rows[page * page_size:(page + 1) * page_size]):
                rank = page * page_size + i + 1
                safe_addstr(stdscr, 3 + i, 0, f"{rank:3}. {name[:20]:20} {score}"[:width - 1])
            if not rows:
                safe_addstr(stdscr, 3, 0, "No players yet.")
            safe_addstr(stdscr, height - 3, 0, "Enter: play   P: reset database   Q: quit")
            stdscr.refresh()
            ch = stdscr.getch()
            if ch in (10, 13):
                return
            if ch in (ord("q"), ord("Q")):
                raise UserExit
            if ch in (curses.KEY_RIGHT, curses.KEY_NPAGE):
                page = min(page + 1, pages - 1)
            elif ch in (curses.KEY_LEFT, curses.KEY_PPAGE):
                page = max(0, page - 1)
            elif ch in (ord("p"), ord("P")):
                answer = prompt(stdscr, height - 2, 0, "Delete all players/scores? (y/n): ")
                if answer.lower() == "y":
                    reset_database()
                    page = 0
    except KeyboardInterrupt as exc:
        raise UserExit from exc


def choose_speed(stdscr):
    stdscr.nodelay(False)
    try:
        while True:
            stdscr.clear()
            safe_addstr(stdscr, 1, 2, "Select speed:")
            safe_addstr(stdscr, 3, 2, "1) Easy   - very calm")
            safe_addstr(stdscr, 4, 2, "2) Normal - calm")
            safe_addstr(stdscr, 5, 2, "3) Medium - focused")
            safe_addstr(stdscr, 6, 2, "4) Hard   - quick")
            stdscr.refresh()
            ch = stdscr.getch()
            key = chr(ch) if 0 <= ch < 256 else ""
            if key.lower() == "q":
                raise UserExit
            if key in SPEEDS:
                return SPEEDS[key]
    except KeyboardInterrupt as exc:
        raise UserExit from exc




class Game:
    def __init__(self, stdscr, player, best, level, fall_delay):
        self.stdscr = stdscr
        self.player = player
        self.best = best
        self.level = level
        self.fall_delay = fall_delay
        self.board = [["." for _ in range(COLS)] for _ in range(ROWS)]
        self.score = 0
        self.logs = []
        self.paused = False
        self.game_over = False
        self.shape_stats = {name: 0 for name in SHAPES}
        self.last_fall = time.monotonic()
        self.piece_name = ""
        self.shape = []
        self.px = 3
        self.py = 0
        self.bag = []
        self.next_piece_name = self.take_piece()
        self.new_piece()

    def log(self, message):
        self.logs.append(message)
        self.logs = self.logs[-28:]

    def reset(self):
        self.save_best()
        self.board = [["." for _ in range(COLS)] for _ in range(ROWS)]
        self.score = 0
        self.paused = False
        self.logs = ["Game restarted"]
        self.game_over = False
        self.shape_stats = {name: 0 for name in SHAPES}
        self.bag = []
        self.next_piece_name = self.take_piece()
        self.new_piece()

    def save_best(self):
        if self.score > self.best:
            old = self.best
            self.best = self.score
            update_best(self.player, self.best)
            self.log(f"New best score saved: {self.best}")
            return f"New record saved! Previous best: {old}"
        return "Record unchanged."

    def occupied(self):
        return {(self.px + x, self.py + y) for x, y in self.shape}

    def can_place(self, px, py, shape):
        for x, y in shape:
            bx, by = px + x, py + y
            if bx < 0 or bx >= COLS or by < 0 or by >= ROWS:
                return False
            if self.board[by][bx] != ".":
                return False
        return True

    def take_piece(self):
        if not self.bag:
            self.bag = list(SHAPES)
            random.shuffle(self.bag)
        return self.bag.pop()

    def new_piece(self):
        self.piece_name = self.next_piece_name
        self.next_piece_name = self.take_piece()
        self.shape = SHAPES[self.piece_name][:]
        self.px = 3
        self.py = 0
        self.last_fall = time.monotonic()
        self.lock_since = None
        self.lock_resets = 0
        if not self.can_place(self.px, self.py, self.shape):
            self.game_over = True
            self.save_best()
            self.log("Game over")
            return
        self.shape_stats[self.piece_name] += 1
        self.log(f"Figure: {self.piece_name}")

    def landing_y(self):
        y = self.py
        while self.can_place(self.px, y + 1, self.shape):
            y += 1
        return y

    def update_contact(self, moved=False):
        now = time.monotonic()
        if self.can_place(self.px, self.py + 1, self.shape):
            self.lock_since = None
        elif self.lock_since is None:
            self.lock_since = now
        elif moved and self.lock_resets < MAX_LOCK_RESETS:
            self.lock_since = now
            self.lock_resets += 1

    def lock_piece(self):
        for x, y in self.shape:
            self.board[self.py + y][self.px + x] = self.piece_name
        self.clear_lines()
        self.new_piece()

    def rotate(self):
        rotated = [(1 - y, x) for x, y in self.shape]
        min_x = min(x for x, _ in rotated)
        min_y = min(y for _, y in rotated)
        rotated = [(x - min_x, y - min_y) for x, y in rotated]
        for offset in (0, -1, 1, -2, 2, -3, 3):
            if self.can_place(self.px + offset, self.py, rotated):
                self.px += offset
                self.shape = rotated
                self.update_contact(moved=True)
                return

    def advance(self):
        if self.can_place(self.px, self.py + 1, self.shape):
            self.py += 1
        self.update_contact()

    def clear_lines(self):
        new_board = [row for row in self.board if any(cell == "." for cell in row)]
        cleared = ROWS - len(new_board)
        if cleared:
            self.board = [["." for _ in range(COLS)] for _ in range(cleared)] + new_board
            points = SCORES.get(cleared, 0)
            self.score += points
            word = "line" if cleared == 1 else "lines"
            point_word = "point" if points == 1 else "points"
            self.log(f"Cleared {cleared} {word} +{points} {point_word}")
            self.save_best()

    def handle_key(self, ch):
        if self.game_over:
            if ch in (ord("r"), ord("R")):
                self.reset()
                return True
            if ch in (ord("q"), ord("Q")):
                return False
            return True
        if ch in (ord("q"), ord("Q")):
            return False
        if ch in (ord("p"), ord("P")):
            self.paused = not self.paused
            self.last_fall = time.monotonic()
            if self.lock_since is not None:
                self.lock_since = self.last_fall
            self.log("Pause on" if self.paused else "Pause off")
            return True
        if ch in (ord("r"), ord("R")):
            self.reset()
            return True
        if self.paused:
            return True
        if ch == ord(" "):
            self.py = self.landing_y()
            self.lock_piece()
            return True
        if ch in (ord("s"), ord("S"), curses.KEY_LEFT) and self.can_place(self.px - 1, self.py, self.shape):
            self.px -= 1
            self.update_contact(moved=True)
        elif ch in (ord("f"), ord("F"), curses.KEY_RIGHT) and self.can_place(self.px + 1, self.py, self.shape):
            self.px += 1
            self.update_contact(moved=True)
        elif ch == curses.KEY_DOWN and self.can_place(self.px, self.py + 1, self.shape):
            self.py += 1
            self.last_fall = time.monotonic()
            self.update_contact()
        elif ch in (ord("d"), ord("D"), curses.KEY_UP):
            self.rotate()
        return True

    def tick(self):
        if self.game_over or self.paused:
            return
        now = time.monotonic()
        # Preserve the schedule across slow frames, but discard long suspensions.
        if now - self.last_fall > self.fall_delay * 3:
            self.last_fall = now - self.fall_delay
            if self.lock_since is not None:
                self.lock_since = now
        while now - self.last_fall >= self.fall_delay:
            self.last_fall += self.fall_delay
            self.advance()
        self.update_contact()
        if self.lock_since is not None and now - self.lock_since >= LOCK_DELAY:
            self.lock_piece()

    def draw_cell(self, y, x, piece):
        if piece == ".":
            safe_addstr(self.stdscr, y, x, "  ")
            return
        color = curses.color_pair(PIECE_COLORS[piece])
        safe_addstr(self.stdscr, y, x, CELL, color)

    def screen_fits(self):
        height, width = self.stdscr.getmaxyx()
        return height >= MIN_HEIGHT and width >= MIN_WIDTH

    def draw(self):
        s = self.stdscr
        s.erase()
        height, width = s.getmaxyx()
        if not self.screen_fits():
            safe_addstr(s, 0, 0, "Paused: enlarge terminal to 52x24. Q: quit")
            s.refresh()
            return
        state = "GAME OVER" if self.game_over else ("PAUSED" if self.paused else "Playing")
        safe_addstr(s, 0, 0, "+" + "-" * (COLS * 2) + "+")
        active = self.occupied() if not self.game_over else set()
        ghost = {(self.px + x, self.landing_y() + y) for x, y in self.shape} if not self.game_over else set()
        for r in range(ROWS):
            safe_addstr(s, r + 1, 0, "|")
            for c in range(COLS):
                piece = self.piece_name if (c, r) in active else self.board[r][c]
                if piece == "." and (c, r) in ghost:
                    safe_addstr(s, r + 1, 1 + c * 2, "..", curses.A_DIM)
                else:
                    self.draw_cell(r + 1, 1 + c * 2, piece)
            safe_addstr(s, r + 1, 21, "|")
        safe_addstr(s, 21, 0, "+" + "-" * (COLS * 2) + "+")
        safe_addstr(s, 22, 0, f"Score:{self.score} Best:{self.best}"[:22])
        if self.paused or self.game_over:
            safe_addstr(s, 10, 5, state, curses.A_REVERSE)
        panel = [f"{self.level} - {state}", f"Next: {self.next_piece_name}"]
        preview = set(SHAPES[self.next_piece_name])
        panel += ["".join("[]" if (x, y) in preview else "  " for x in range(4)) for y in range(4)]
        panel += ["Left/Right: move", "Up: rotate  Down: soft drop",
                  "Space: hard drop", "P:pause R:restart Q:quit", "Stats:",
                  " ".join(f"{k}:{self.shape_stats[k]}" for k in ("I", "O", "T", "S")),
                  " ".join(f"{k}:{self.shape_stats[k]}" for k in ("Z", "J", "L")), "Events:"]
        panel += self.logs[-max(1, height - len(panel) - 1):]
        for y, text in enumerate(panel):
            safe_addstr(s, y, 24, text[:width - 25])
        s.refresh()


def init_colors():
    curses.start_color()
    curses.use_default_colors()
    pairs = [
        (curses.COLOR_CYAN, -1),
        (curses.COLOR_YELLOW, -1),
        (curses.COLOR_MAGENTA, -1),
        (curses.COLOR_GREEN, -1),
        (curses.COLOR_RED, -1),
        (curses.COLOR_BLUE, -1),
        (curses.COLOR_WHITE, -1),
    ]
    for i, (fg, bg) in enumerate(pairs, start=1):
        curses.init_pair(i, fg, bg)


def run(stdscr):
    try:
        random.seed()
        curses.curs_set(0)
        stdscr.keypad(True)
        stdscr.nodelay(True)
        stdscr.timeout(30)
        init_colors()
        init_db()
        draw_start(stdscr)
        level, delay = choose_speed(stdscr)
        player, best = login(stdscr)
        stdscr.nodelay(True)
        game = Game(stdscr, player, best, level, delay)
    except (KeyboardInterrupt, UserExit):
        return "Interrupted.", 0, "", 0, ""

    result = "Quit."
    try:
        running = True
        while running:
            frame_start = time.monotonic()
            ch = stdscr.getch()
            if not game.screen_fits():
                # Resizing suspends both timers without changing the user's pause.
                game.last_fall = time.monotonic()
                if game.lock_since is not None:
                    game.lock_since = game.last_fall
                running = ch not in (ord("q"), ord("Q"))
            else:
                if ch != -1:
                    running = game.handle_key(ch)
                if running:
                    game.tick()
            game.draw()
            # Bound rendering and CPU usage even when getch() returns instantly.
            time.sleep(max(0.0, 1 / 30 - (time.monotonic() - frame_start)))
    except (KeyboardInterrupt, UserExit):
        result = "Interrupted."

    save_message = game.save_best()
    return result, game.score, player, game.best, save_message


if __name__ == "__main__":
    try:
        result, score, player, best, save_message = curses.wrapper(run)
        print(f"{result} Score: {score}")
        if player:
            print(f"Player: {player}. Best score: {best}")
        if save_message:
            print(save_message)
    except KeyboardInterrupt:
        print("Interrupted.")
