import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('dino', Path(__file__).resolve().parents[1] / 'dino.py')
dino = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dino)


class RunnerTests(unittest.TestCase):
    def game(self, hero='1'):
        game = dino.Runner(hero)
        game.to_spawn = 10**9
        return game

    def test_jump_arc_and_balance(self):
        for hero in dino.HEROES:
            game = self.game(hero)
            game.jump()
            peak = 0
            for _ in range(50):
                game.step()
                peak = max(peak, game.altitude)
            self.assertEqual((peak, game.altitude), (5000, 0))

    def test_double_up_jumps_higher_without_leaving_small_field(self):
        for hero in dino.HEROES:
            for delay in (0, 5, 15):
                game = self.game(hero)
                game.resize(16, 52)
                game.handle_key(dino.curses.KEY_UP)
                for _ in range(delay):
                    game.step()
                game.handle_key(dino.curses.KEY_UP)
                self.assertIn('High jump!', game.logs)
                peak = 0
                for _ in range(100):
                    game.step()
                    peak = max(peak, game.altitude)
                    self.assertGreaterEqual(game.feet - 2, 0)
                self.assertEqual(peak, 7000)
                self.assertEqual(game.altitude, 0)

    def test_boost_only_once_and_only_double_up(self):
        game = self.game()
        game.handle_key(dino.curses.KEY_UP)
        game.step()
        game.handle_key(dino.curses.KEY_UP)
        game.step()
        velocity = game.velocity
        game.handle_key(dino.curses.KEY_UP)
        self.assertEqual(game.velocity, velocity)
        self.assertEqual(game.logs.count('High jump!'), 1)
        game = self.game()
        game.handle_key(ord(' '))
        game.step()
        game.handle_key(dino.curses.KEY_UP)
        self.assertNotIn('High jump!', game.logs)
        game = self.game()
        game.handle_key(dino.curses.KEY_UP)
        for _ in range(20):
            game.step()
        game.handle_key(dino.curses.KEY_UP)
        self.assertNotIn('High jump!', game.logs)

    def test_block_render_and_collision_width_agree(self):
        game = self.game()
        game.obstacles = [dino.Obstacle(20000, 2)]
        rows = game.render_rows()
        self.assertEqual(rows[game.ground][20:24], '[][]')
        game.obstacles[0].x = 5000
        self.assertTrue(game.collision())  # rightmost bracket touches x=8
        self.assertFalse(any('#' in row for row in rows))

    def test_birds_require_duck(self):
        for hero in dino.HEROES:
            game = self.game(hero)
            game.obstacles = [dino.Obstacle(8000, 3)]
            self.assertTrue(game.collision())
            game.handle_key(dino.curses.KEY_DOWN)
            self.assertFalse(game.collision())

    def test_spawn_spacing(self):
        game = self.game()
        for _ in range(100):
            game.spawn()
        for left, right in zip(game.obstacles, game.obstacles[1:]):
            self.assertGreaterEqual(right.x - left.x, dino.MIN_GAP)

    def test_cacti_clearance(self):
        for speed in (12000, 16000, 20000):
            for kind in (1, 2):
                success = False
                for trigger in range(15, 29):
                    game = self.game()
                    game.steps = (speed - 12000) * 3000 // 8000
                    game.obstacles = [dino.Obstacle(38000, kind)]
                    jumped = False
                    for _ in range(180):
                        if not jumped and game.obstacles[0].x <= trigger * 1000:
                            game.jump()
                            jumped = True
                        game.step()
                        if game.game_over:
                            break
                        if game.obstacles[0].x < 4000:
                            success = True
                            break
                    if success:
                        break
                self.assertTrue(success, (speed, kind))

    def test_restart_preserves_best_and_hero(self):
        game = self.game('3')
        for _ in range(50):
            game.step()
        game.handle_key(ord('r'))
        self.assertEqual((game.score, game.best, game.hero), (0, 10, '3'))
        self.assertFalse(game.game_over)
        self.assertEqual(game.obstacles, [])

    def test_input_does_not_change_elapsed_simulation(self):
        for spam in (False, True):
            with patch.object(dino.time, 'monotonic', return_value=100):
                game = self.game()
            for i in range(1, 101):
                if spam:
                    game.handle_key(ord('x'))
                game.tick(100 + i / 100)
            self.assertEqual(game.sim_ms, 1000)

    def test_resize_and_render(self):
        game = self.game()
        self.assertFalse(game.resize(10, 35))
        self.assertTrue(game.resize(16, 52))
        rows = game.render_rows()
        self.assertEqual(len(rows), 11)
        self.assertTrue(all(len(row) == 49 for row in rows))

    def test_long_suspension_discards_backlog(self):
        game = self.game()
        game.tick(game.next_step + 100)
        self.assertEqual(game.sim_ms, 20)

    def test_pause_stops_physics_and_jump(self):
        game = self.game()
        game.handle_key(ord('p'))
        game.handle_key(ord(' '))
        game.tick(game.next_step + 100)
        self.assertEqual((game.sim_ms, game.jumps), (0, 0))
        with patch.object(dino.time, 'monotonic', return_value=200):
            game.handle_key(ord('p'))
        game.tick(200)
        self.assertEqual(game.sim_ms, 0)
        game.tick(200.02)
        self.assertEqual(game.sim_ms, 20)

    def test_passed_obstacle_counted_once(self):
        game = self.game()
        game.obstacles = [dino.Obstacle(7000, 1)]
        for _ in range(5):
            game.step()
        self.assertEqual(game.passed, 1)
        self.assertIn('Cactus passed', game.logs)

    def test_sidebar_and_compact_layout_fit(self):
        class Screen:
            def __init__(self, rows, cols):
                self.rows, self.cols = rows, cols
                self.text = []
            def getmaxyx(self): return self.rows, self.cols
            def erase(self): pass
            def refresh(self): pass
            def addstr(self, y, x, text, attr=0):
                assert 0 <= y < self.rows and x + len(text) < self.cols
                self.text.append(text)
        for rows, cols in ((24, 80), (16, 52), (40, 120)):
            screen = Screen(rows, cols)
            game = self.game()
            dino.draw_game(screen, game)
            self.assertEqual(game.sidebar, cols >= 80)
            self.assertTrue(any('pause' in text for text in screen.text))
            if game.sidebar:
                self.assertIn('Events:', screen.text)
                self.assertIn('Controls', screen.text)
