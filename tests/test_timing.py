import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("tetris", ROOT / "tetris.py")
tetris = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tetris)


class PythonGameTests(unittest.TestCase):
    def setUp(self):
        self.clock = patch.object(tetris.time, "monotonic", return_value=100.0)
        self.now = self.clock.start()
        self.addCleanup(self.clock.stop)
        self.game = tetris.Game(None, "test", 0, "Normal", 1.4)

    def test_classic_shapes_and_seven_bag(self):
        self.assertTrue(all(len(set(s)) == 4 for s in tetris.SHAPES.values()))
        names = []
        for _ in range(14):
            names.append(self.game.piece_name)
            next_name = self.game.next_piece_name
            self.game.new_piece()
            self.assertEqual(self.game.piece_name, next_name)
        for start in (0, 7):
            self.assertEqual(set(names[start:start + 7]), set(tetris.SHAPES))

    def test_input_does_not_advance_gravity(self):
        for i in range(100):
            self.now.return_value = 100 + i / 100
            self.game.handle_key(ord("s" if i % 2 else "f"))
            self.game.tick()
        self.assertEqual(self.game.py, 0)
        self.now.return_value = 101.5
        self.game.tick()
        self.assertEqual(self.game.py, 1)

    def test_slow_frame_preserves_deadline(self):
        self.now.return_value = 102.0
        self.game.tick()
        self.assertAlmostEqual(self.game.last_fall, 101.4)
        self.now.return_value = 102.9
        self.game.tick()
        self.assertEqual(self.game.py, 2)

    def test_pause_and_resize_timer_behavior(self):
        self.game.handle_key(ord("p"))
        self.now.return_value = 200
        self.game.tick()
        self.game.handle_key(ord(" "))
        self.assertEqual(self.game.py, 0)
        self.game.handle_key(ord("p"))
        self.game.tick()
        self.assertEqual(self.game.py, 0)
        self.now.return_value = 201.5
        self.game.tick()
        self.assertEqual(self.game.py, 1)

    def test_long_suspension_does_not_fast_forward(self):
        self.now.return_value = 1000
        self.game.tick()
        self.assertLessEqual(self.game.py, 1)

    def test_ghost_matches_hard_drop(self):
        self.game.board[19][3] = "O"
        y = self.game.landing_y()
        cells = {(self.game.px + x, y + dy) for x, dy in self.game.shape}
        next_name = self.game.next_piece_name
        self.game.handle_key(ord(" "))
        self.assertTrue(all(self.game.board[r][c] != "." for c, r in cells))
        self.assertEqual(self.game.piece_name, next_name)

    def test_contact_delay_and_reset_limit(self):
        self.game.py = self.game.landing_y()
        self.game.update_contact()
        self.now.return_value = 100.39
        self.game.tick()
        self.assertFalse(any(c != "." for row in self.game.board for c in row))
        # Moving while grounded extends the delay, at most 15 times.
        for i in range(20):
            self.now.return_value += .01
            self.game.handle_key(ord("s" if i % 2 else "f"))
        self.assertEqual(self.game.lock_resets, 15)
        self.now.return_value = self.game.lock_since + .401
        self.game.tick()
        self.assertEqual(sum(c != "." for row in self.game.board for c in row), 4)

    def test_restart_resets_statistics(self):
        for _ in range(10):
            self.game.new_piece()
        self.game.reset()
        self.assertEqual(sum(self.game.shape_stats.values()), 1)
        self.assertEqual(self.game.score, 0)
        self.assertFalse(self.game.game_over)

    def test_blocked_spawn_and_restart(self):
        self.game.board[0] = ["O"] * 10
        self.game.new_piece()
        self.assertTrue(self.game.game_over)
        self.game.handle_key(ord("r"))
        self.assertFalse(self.game.game_over)

    def test_top_100_all_accessible(self):
        class Screen:
            def __init__(self):
                self.keys = iter([tetris.curses.KEY_RIGHT] * 6 + [10])
                self.text = []
            def getmaxyx(self): return (24, 80)
            def nodelay(self, value): pass
            def erase(self): pass
            def refresh(self): pass
            def getch(self): return next(self.keys)
            def addstr(self, y, x, text, attr=0): self.text.append(text)
        screen = Screen()
        with patch.object(tetris, 'top_players', return_value=[(f'P{i}', i) for i in range(1, 101)]):
            tetris.draw_start(screen)
        self.assertTrue(any('100.' in line for line in screen.text))



if __name__ == '__main__':
    unittest.main()
