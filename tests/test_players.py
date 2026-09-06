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


class SelectionScreen(Screen):
    def __init__(self, keys):
        super().__init__()
        self.keys = iter(keys)
    def getmaxyx(self): return (24, 52)
    def nodelay(self, value): pass
    def erase(self): pass
    def refresh(self): pass
    def getch(self): return next(self.keys)


class SelectionTests(unittest.TestCase):
    setUp = PlayerTests.setUp
    def test_enter_means_new_account(self):
        screen = SelectionScreen([10])
        self.assertIsNone(players.choose_player(screen, rows=[('Alice', 10)]))

    def test_multidigit_number_and_invalid_number(self):
        rows = [(f'Player{i}', 0) for i in range(1, 121)]
        screen = SelectionScreen([ord('9'), ord('9'), ord('9'), 10, ord('1'), ord('0'), ord('0'), 10])
        self.assertEqual(players.choose_player(screen, rows=rows), 'Player100')
        self.assertTrue(any('No such number' in s for s in screen.messages))

    def test_selected_player_only_asks_pin_and_retries(self):
        players.create_player('Alice', '1234')
        with patch.object(players, 'prompt', side_effect=['9999', '1234']) as prompt:
            self.assertEqual(players.login(Screen(), selected_name='Alice'), ('Alice', 0))
        self.assertEqual(prompt.call_count, 2)
        self.assertTrue(all('PIN for Alice' in call.args[3] for call in prompt.call_args_list))

    def test_registration_rejects_occupied_name(self):
        players.create_player('Alice', '1234')
        with patch.object(players, 'prompt', side_effect=['Alice', 'Bob', '5678']) as prompt:
            self.assertEqual(players.login(Screen(), new_only=True), ('Bob', 0))
        self.assertFalse(any('PIN for Alice' in call.args[3] for call in prompt.call_args_list))
        self.assertEqual(players.get_player('Alice')[0], '1234')

    def test_escape_returns_to_list_then_new_account(self):
        players.create_player('Alice', '1234')
        with patch.object(players, 'choose_player', side_effect=['Alice', None]) as choose:
            with patch.object(players, 'prompt', side_effect=[players.LoginBack(), 'Bob', '5678']):
                self.assertEqual(players.authenticate(Screen()), ('Bob', 0))
        self.assertEqual(choose.call_count, 2)

    def test_runner_list_uses_runner_scores(self):
        players.create_player('Alice', '1234')
        players.create_player('Bob', '5678')
        players.update_best('Alice', 100)
        players.save_runner_best('Bob', 20)
        self.assertEqual(players.account_rows('runner'), [('Bob', 20), ('Alice', 0)])
