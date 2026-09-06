import sqlite3
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

import players
from dino import Runner


class Screen:
    def __init__(self): self.messages = []
    def clear(self): pass
    def addstr(self, y, x, text, attr=0): self.messages.append(text)
    def getch(self): return 10


class PlayerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.db = patch.object(players, 'DB_PATH', Path(self.tmp.name) / 'scores.sqlite3')
        self.db.start()
        self.addCleanup(self.db.stop)
        players.init_db()

    def test_register_and_return_with_correct_pin(self):
        with patch.object(players, 'prompt', side_effect=['Alice', '1234']):
            self.assertEqual(players.login(Screen()), ('Alice', 0))
        players.update_best('Alice', 24)
        with patch.object(players, 'prompt', side_effect=['Alice', '1234']):
            self.assertEqual(players.login(Screen()), ('Alice', 24))

    def test_wrong_pin_cannot_enter_or_replace_account(self):
        players.create_player('Alice', '1234')
        screen = Screen()
        with patch.object(players, 'prompt', side_effect=['Alice', '9999', players.UserExit()]):
            with self.assertRaises(players.UserExit):
                players.login(screen)
        self.assertEqual(players.get_player('Alice'), ('1234', 0))
        self.assertTrue(any('Wrong PIN' in s for s in screen.messages))

    def test_wrong_pin_can_choose_a_new_name(self):
        players.create_player('Alice', '1234')
        with patch.object(players, 'prompt', side_effect=['Alice', '9999', 'Bob', '5678']):
            self.assertEqual(players.login(Screen()), ('Bob', 0))
        self.assertEqual(players.get_player('Alice'), ('1234', 0))
        self.assertEqual(players.get_player('Bob'), ('5678', 0))

    def test_duplicate_name_never_overwrites_pin(self):
        players.create_player('Alice', '1234')
        with self.assertRaises(sqlite3.IntegrityError):
            players.create_player('Alice', '9999')
        self.assertEqual(players.get_player('Alice')[0], '1234')

    def test_runner_best_persists_separately(self):
        players.create_player('Alice', '1234')
        players.update_best('Alice', 24)
        game = Runner(player='Alice')
        game.to_spawn = 10**9
        for _ in range(50):
            game.step()
        self.assertEqual(players.runner_best('Alice'), 10)
        game.best = 15
        game.reset()
        self.assertEqual(players.runner_best('Alice'), 15)
        players.save_runner_best('Alice', 2)
        self.assertEqual(players.runner_best('Alice'), 15)
        self.assertEqual(players.get_player('Alice'), ('1234', 24))
        players.init_db()
        self.assertEqual(players.runner_best('Alice'), 15)

    def test_record_requires_existing_name(self):
        with self.assertRaises(ValueError):
            players.save_runner_best('Unknown', 100)
