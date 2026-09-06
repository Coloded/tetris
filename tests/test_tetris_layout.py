import curses
import unittest
from unittest.mock import patch

import i18n
import tetris


class Screen:
    def __init__(self, height=30, width=120):
        self.height, self.width = height, width
        self.calls = []

    def getmaxyx(self): return self.height, self.width
    def erase(self): self.calls.clear()
    def refresh(self): pass
    def addstr(self, y, x, text, attr=0):
        assert 0 <= y < self.height and 0 <= x and x + len(text) < self.width, (y, x, text)
        self.calls.append((y, x, text, attr))


class LayoutTests(unittest.TestCase):
    def tearDown(self):
        i18n.set_language('en')

    def game(self, screen=None, player='Me', best=0, leaderboard=None):
        return tetris.Game(screen, player, best, 'Normal', 1.4, leaderboard=leaderboard)

    def test_height_floor_and_line_clear(self):
        for height in (24, 30, 40):
            game = self.game(Screen(height))
            self.assertEqual(game.rows, height - 3)
            game.shape = [(0, 0)]
            self.assertEqual(game.landing_y(), height - 4)
            self.assertFalse(game.can_place(0, game.rows, game.shape))
            game.board[-1] = ['I'] * 10
            with patch.object(tetris, 'update_best'):
                game.clear_lines()
            self.assertEqual(len(game.board), height - 3)
            self.assertEqual(game.score, 1)
            with patch.object(tetris.curses, 'color_pair', return_value=0):
                game.draw()
            self.assertTrue(any(y == height - 1 and 'Score:' in text for y, _, text, _ in game.stdscr.calls))

    def test_resize_preserves_round_until_explicit_restart(self):
        screen = Screen()
        game = self.game(screen)
        game.board[-1][0] = 'T'
        screen.height = 24
        self.assertFalse(game.screen_fits())
        game.draw()
        self.assertEqual(game.board[-1][0], 'T')
        game.reset()
        self.assertTrue(game.screen_fits())
        self.assertEqual(game.rows, 21)
        screen.height = 40
        game.reset()
        self.assertEqual(game.rows, 37)

    def test_top30_visible_and_highlighted_in_both_languages(self):
        entries = [(f'Player{i:02}', 100 - i) for i in range(35)]
        for lang in ('en', 'ru'):
            i18n.set_language(lang)
            screen = Screen()
            game = self.game(screen, 'Player20', 80, entries)
            with patch.object(tetris.curses, 'color_pair', return_value=0):
                game.draw()
            texts = [text for _, _, text, _ in screen.calls]
            for i in range(30):
                self.assertTrue(any(f'Player{i:02}' in text for text in texts))
            self.assertFalse(any('Player30' in text for text in texts))
            self.assertTrue(any('Player20' in text and attr == curses.A_REVERSE
                                for _, _, text, attr in screen.calls))

    def test_narrow_pagination_and_outside_top30(self):
        entries = [(f'P{i:02}', 100 - i) for i in range(40)]
        for width in (52, 80):
            screen = Screen(24, width)
            game = self.game(screen, 'P39', 61, entries)
            seen = set()
            with patch.object(tetris.curses, 'color_pair', return_value=0):
                for _ in range(8):
                    game.draw()
                    for _, _, text, _ in screen.calls:
                        seen.update(name for name, _ in entries if name in text)
                    game.handle_key(9)
            self.assertTrue(all(name in seen for name, _ in entries[:30]))
            self.assertIn('P39', seen)

    def test_overtake_ties_multiple_and_restart(self):
        game = self.game(player='Me', best=5, leaderboard=[('Alice', 10), ('Bob', 8), ('Me', 5)])
        with patch.object(tetris, 'update_best'):
            game.score = 8
            game.save_best()
            self.assertEqual(game.rank_notice, '')
            game.score = 11
            game.save_best()
            self.assertIn('Alice, Bob', game.rank_notice)
            self.assertIn('#1', game.rank_notice)
            self.assertEqual(game.ranked_players()[0], ('Me', 11))
            notice_count = sum('Well done!' in text for text in game.logs)
            game.save_best()
            self.assertEqual(sum('Well done!' in text for text in game.logs), notice_count)
            game.reset()
            self.assertEqual(game.ranked_players()[0], ('Me', 11))
            self.assertEqual(game.notice_until, 0)

    def test_entering_top30(self):
        game = self.game(leaderboard=[(f'P{i}', 100 - i) for i in range(35)])
        with patch.object(tetris, 'update_best'):
            game.score = 75
            game.save_best()
        self.assertEqual(game.ranked_players()[26], ('Me', 75))
        self.assertIn('#27', game.rank_notice)
