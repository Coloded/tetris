#!/usr/bin/env python3
"""Terminal runner; only Python's standard library is required."""

import curses
from dataclasses import dataclass
import random
import time

STEP_MS = 20
MAX_SPEED = 20000
MIN_GAP = 40000
HEROES = {
    '1': ('Human', (' oo ', '/||\\', '/  \\'), '_oo_'),
    '2': ('Dog', ('/\\/\\', ' oo>', '/__\\'), '_o_>'),
    '3': ('Cockroach', ('\\  /', '(oo)', '/||\\'), '_oo_'),
}


@dataclass
class Obstacle:
    x: int  # thousandths of a cell
    kind: int
    passed: bool = False


class Runner:
    def __init__(self, hero='1'):
        self.hero = hero
        self.best = 0
        self.width, self.height = 77, 19
        self.reset()

    def reset(self):
        self.score = self.sim_ms = self.steps = 0
        self.game_over = self.ducking = self.jump_locked = self.paused = False
        self.jumps = self.passed = 0
        self.logs = ["Ready - good luck!"]
        self.duck_until = 0
        self.last_jump = -1000
        self.altitude = self.velocity = 0
        self.speed = 12000
        self.obstacles = []
        self.to_spawn = 15000
        self.next_step = time.monotonic() + STEP_MS / 1000

    def log(self, message):
        self.logs.append(message)
        self.logs = self.logs[-8:]

    @property
    def ground(self):
        return self.height - 2

    @property
    def feet(self):
        return self.ground - (self.altitude + 500) // 1000

    def jump(self):
        if self.altitude == 0 and not self.jump_locked:
            self.velocity = -20000
            self.ducking = False
            self.duck_until = 0
            self.jump_locked = True
            self.jumps += 1
        self.last_jump = self.sim_ms

    def handle_key(self, key):
        if key in (ord('q'), ord('Q')):
            return False
        if key in (ord('r'), ord('R')):
            self.reset()
            self.log("Game restarted")
        elif key in (ord("p"), ord("P")) and not self.game_over:
            self.paused = not self.paused
            self.next_step = time.monotonic() + STEP_MS / 1000
            self.log("Paused" if self.paused else "Resumed")
        elif not self.game_over and not self.paused:
            if key in (ord(' '), curses.KEY_UP):
                self.jump()
            elif key == curses.KEY_DOWN and self.altitude == 0:
                self.duck_until = self.sim_ms + 700
                self.ducking = True
        return True

    def spawn(self):
        if self.score >= 150 and random.randrange(5) == 0:
            kind = 3
        else:
            kind = 2 if random.randrange(3) == 0 else 1
        x = (self.width + 3) * 1000
        if self.obstacles:
            x = max(x, self.obstacles[-1].x + MIN_GAP)
        self.obstacles.append(Obstacle(x, kind))
        # One-second flight + recovery and collision-box widths at max speed.
        self.to_spawn = MIN_GAP + random.randrange(12001)

    def collision(self):
        top = self.feet if self.ducking and self.altitude == 0 else self.feet - 2
        for obstacle in self.obstacles:
            x = obstacle.x // 1000
            right = x + (0 if obstacle.kind == 1 else 1 if obstacle.kind == 2 else 2)
            ob_top = self.ground - (1 if obstacle.kind == 1 else 2)
            bottom = self.ground - (1 if obstacle.kind == 3 else 0)
            if 8 <= right and 11 >= x and top <= bottom and self.feet >= ob_top:
                return True
        return False

    def step(self):
        self.sim_ms += STEP_MS
        if self.altitude > 0 or self.velocity < 0:
            self.altitude -= self.velocity * STEP_MS // 1000 + 40000 * STEP_MS**2 // 2000000
            self.velocity += 40000 * STEP_MS // 1000
            if self.altitude <= 0:
                self.altitude = self.velocity = 0
        self.ducking = self.altitude == 0 and self.sim_ms < self.duck_until
        if self.altitude == 0 and self.sim_ms - self.last_jump >= 200:
            self.jump_locked = False
        self.speed = min(MAX_SPEED, 12000 + self.steps * 8000 // 3000)
        distance = self.speed * STEP_MS // 1000
        for obstacle in self.obstacles:
            obstacle.x -= distance
        self.obstacles = [o for o in self.obstacles if o.x > -5000]
        self.to_spawn -= distance
        if self.to_spawn <= 0:
            self.spawn()
        self.steps += 1
        self.score = self.sim_ms // 100
        self.best = max(self.best, self.score)
        self.game_over = self.collision()
        if self.game_over:
            self.log("Game over - R to retry")
        else:
            for obstacle in self.obstacles:
                right = obstacle.x // 1000 + obstacle.kind - 1
                if not obstacle.passed and right < 8:
                    obstacle.passed = True
                    self.passed += 1
                    self.log("Bird passed" if obstacle.kind == 3 else "Cactus passed")

    def tick(self, now):
        if self.paused:
            return
        if now - self.next_step > .25:
            self.next_step = now
        while not self.game_over and now + 1e-9 >= self.next_step:
            self.step()
            self.next_step += STEP_MS / 1000

    def resize(self, rows, cols):
        self.sidebar = cols >= 80
        self.width = min(100, cols - 30 if self.sidebar else cols - 3)
        self.height = min(20, rows - 5)
        return rows >= 16 and cols >= 52

    def render_rows(self):
        rows = [[' '] * self.width for _ in range(self.height)]

        def put(y, x, text):
            if 0 <= y < self.height:
                for offset, char in enumerate(text):
                    if 0 <= x + offset < self.width:
                        rows[y][x + offset] = char

        put(self.ground + 1, 0, '_' * self.width)
        for obstacle in self.obstacles:
            x = obstacle.x // 1000
            if obstacle.kind == 3:
                put(self.ground - 2, x, '<=>')
                put(self.ground - 1, x, ' v ')
            else:
                for y in range(self.ground - obstacle.kind, self.ground + 1):
                    put(y, x, '#' * obstacle.kind)
        _, sprite, duck = HEROES[self.hero]
        if self.ducking and self.altitude == 0:
            put(self.ground, 8, duck)
        else:
            for offset, line in enumerate(sprite):
                put(self.feet - 2 + offset, 8, line)
        return [''.join(row) for row in rows]


def write(screen, y, x, text, attr=0):
    rows, cols = screen.getmaxyx()
    if not (0 <= y < rows and 0 <= x < cols):
        return
    try:
        screen.addstr(y, x, text[:max(0, cols - x - 1)], attr)
    except curses.error:
        pass


COLORS = False


def color(pair):
    return curses.color_pair(pair) if COLORS else 0


def init_colors():
    global COLORS
    COLORS = False
    if not curses.has_colors():
        return
    try:
        curses.start_color()
        curses.use_default_colors()
        for pair, fg in enumerate((curses.COLOR_CYAN, curses.COLOR_GREEN,
                                   curses.COLOR_MAGENTA, curses.COLOR_YELLOW), 1):
            curses.init_pair(pair, fg, -1)
        COLORS = True
    except curses.error:
        pass


def draw_menu(screen):
    screen.erase()
    rows, cols = screen.getmaxyx()
    write(screen, 0, 2, "RUNNER / Choose your character", color(1) | curses.A_BOLD)
    card_width = min(22, max(1, (cols - 4) // 3))
    for i, (key, (name, sprite, _)) in enumerate(HEROES.items()):
        x = 2 + i * card_width
        write(screen, 2, x, f"[{key}] {name}", color(i + 1) | curses.A_BOLD)
        for y, line in enumerate(sprite, 4):
            write(screen, y, x + 3, line, color(i + 1) | curses.A_BOLD)
    write(screen, 9, 2, "Same size, speed and jump for every character.")
    write(screen, 11, 2, "Space/Up: jump   Down: duck   P: pause")
    write(screen, 13, 2, "1-3: choose   Q: quit", color(4))
    screen.refresh()


def draw_game(screen, game):
    screen.erase()
    rows, cols = screen.getmaxyx()
    if not game.resize(rows, cols):
        write(screen, 0, 0, "Paused: enlarge terminal to 52x16. Q: quit")
        screen.refresh()
        return
    state = "GAME OVER" if game.game_over else "PAUSED" if game.paused else "Playing"
    write(screen, 0, 0, "RUNNER", color(1) | curses.A_BOLD)
    write(screen, 0, 8, f"{HEROES[game.hero][0]} - {state}", color(4))
    border = '+' + '-' * game.width + '+'
    write(screen, 1, 0, border, color(1))
    for y, row in enumerate(game.render_rows(), 2):
        write(screen, y, 0, '|', color(1))
        write(screen, y, 1, row)
        write(screen, y, game.width + 1, '|', color(1))
    write(screen, game.height + 2, 0, border, color(1))
    # Color visible actors over the fixed-width field without changing geometry.
    def actor(y, x, text, attr):
        if not 0 <= y < game.height:
            return
        if x < 0:
            text, x = text[-x:], 0
        if x < game.width:
            write(screen, y + 2, x + 1, text[:game.width - x], attr)
    actor(game.ground + 1, 0, '_' * game.width, curses.A_DIM)
    for obstacle in game.obstacles:
        x = obstacle.x // 1000
        if obstacle.kind == 3:
            actor(game.ground - 2, x, '<=>', color(3) | curses.A_BOLD)
            actor(game.ground - 1, x, ' v ', color(3))
        else:
            for y in range(game.ground - obstacle.kind, game.ground + 1):
                actor(y, x, '#' * obstacle.kind, color(2) | curses.A_BOLD)
    _, sprite, duck = HEROES[game.hero]
    if game.ducking and game.altitude == 0:
        actor(game.ground, 8, duck, color(1) | curses.A_BOLD)
    else:
        for y, line in enumerate(sprite, game.feet - 2):
            actor(y, 8, line, color(1) | curses.A_BOLD)
    if game.paused or game.game_over:
        label = ' PAUSED ' if game.paused else ' GAME OVER '
        x = max(1, (game.width - len(label)) // 2 + 1)
        write(screen, game.height // 2 + 1, x, label, curses.A_REVERSE | curses.A_BOLD)
    if game.sidebar:
        x = game.width + 4
        next_obstacle = next((o for o in game.obstacles if not o.passed), None)
        upcoming = {1: 'Cactus - jump', 2: 'Tall cactus - jump', 3: 'Bird - duck'}
        panel = [f"Score: {game.score}", f"Best:  {game.best}",
                 f"Time:  {game.sim_ms / 1000:.1f}s", f"Speed: {game.speed / 1000:.1f} cells/s",
                 f"Passed: {game.passed}  Jumps: {game.jumps}", '',
                 'Next:', upcoming[next_obstacle.kind] if next_obstacle else 'Clear ahead', '',
                 'Controls', 'Space / Up: jump', 'Down: duck', 'P: pause / resume',
                 'R: restart   Q: quit', '', 'Events:']
        panel += game.logs[-max(1, rows - len(panel) - 1):]
        for y, line in enumerate(panel):
            attr = color(4) | curses.A_BOLD if y < 2 else color(1) if line in ('Next:', 'Controls', 'Events:') else 0
            write(screen, y, x, line, attr)
        footer = 'R: retry   Q: quit' if game.game_over else 'Space: jump | Down: duck | P: pause'
        write(screen, game.height + 3, 0, footer, curses.A_DIM)
    else:
        write(screen, 0, 0, f"{HEROES[game.hero][0]} S:{game.score} Best:{game.best} {state}", color(4))
        write(screen, game.height + 3, 0, 'Space/Up:jump Down:duck P:pause R:restart Q:quit')
    screen.refresh()


def run(screen):
    curses.curs_set(0)
    init_colors()
    screen.keypad(True)
    screen.timeout(100)
    while True:
        draw_menu(screen)
        key = screen.getch()
        if key in (ord('q'), ord('Q')):
            return 0, 0
        if key in (ord('1'), ord('2'), ord('3')):
            game = Runner(chr(key))
            break
    screen.nodelay(True)
    while True:
        start = time.monotonic()
        key = screen.getch()
        fits = game.resize(*screen.getmaxyx())
        if key in (ord('q'), ord('Q')):
            break
        if fits:
            game.handle_key(key)
            game.tick(time.monotonic())
        else:
            game.next_step = time.monotonic() + STEP_MS / 1000
        draw_game(screen, game)
        time.sleep(max(0, 1 / 50 - (time.monotonic() - start)))
    return game.score, game.best


if __name__ == '__main__':
    try:
        score, best = curses.wrapper(run)
        print(f'Runner stopped. Score: {score} Best: {best}')
    except KeyboardInterrupt:
        print('Interrupted.')
