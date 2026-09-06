import string
import unittest
from unittest.mock import patch

import i18n
import dino
import tetris
import players


class Screen:
    def __init__(self, rows=24, cols=80, keys=()):
        self.rows, self.cols = rows, cols
        self.keys = iter(keys)
        self.messages = []
    def getmaxyx(self): return self.rows, self.cols
    def nodelay(self, value): pass
    def erase(self): pass
    def clear(self): pass
    def refresh(self): pass
    def getch(self): return next(self.keys)
    def addstr(self, y, x, text, attr=0):
        assert 0 <= y < self.rows and x + len(text) < self.cols, (y, x, text)
        self.messages.append(text)


class LanguageTests(unittest.TestCase):
    def tearDown(self):
        i18n.set_language('en')

    def test_language_selection_and_cancel(self):
        for key, expected in ((ord('1'), 'Пауза'), (ord('2'), 'Paused')):
            self.assertTrue(i18n.choose_language(Screen(keys=[key])))
            self.assertEqual(i18n.tr('Paused'), expected)
        self.assertFalse(i18n.choose_language(Screen(keys=[27])))

    def test_translation_placeholders_are_valid(self):
        formatter = string.Formatter()
        for english, russian in i18n.RU.items():
            source = {field for _, field, _, _ in formatter.parse(english) if field}
            target = {field for _, field, _, _ in formatter.parse(russian) if field}
            self.assertLessEqual(target, source, english)
        i18n.set_language('ru')
        self.assertEqual(i18n.tr('Score: {score}', score=12), 'Очки: 12')

    def test_russian_game_panels_fit(self):
        i18n.set_language('ru')
        for rows, cols in ((24, 52), (24, 80), (40, 120)):
            screen = Screen(rows, cols)
            with patch.object(tetris.curses, 'color_pair', return_value=0):
                game = tetris.Game(screen, 'Player', 0, 'Normal', 1.4)
                game.draw()
            self.assertIn('События:', screen.messages)
            self.assertFalse(any('Playing' in text or 'Score:' in text for text in screen.messages))
            screen = Screen(rows, cols)
            game = dino.Runner(player='Player')
            dino.draw_game(screen, game)
            self.assertTrue(any('пауза' in text for text in screen.messages))
            if cols >= 80:
                self.assertIn('Управление', screen.messages)

    def test_russian_login_uses_same_credentials(self):
        i18n.set_language('ru')
        screen = Screen()
        with patch.object(players, 'prompt', side_effect=['Alice', '1234']) as prompt:
            with patch.object(players, 'get_player', return_value=('1234', 10)):
                self.assertEqual(players.login(screen), ('Alice', 10))
        self.assertIn('Вход игрока — Esc: к списку', screen.messages)
        self.assertEqual(prompt.call_args.args[3], 'PIN игрока Alice: ')

    def test_reset_confirmation_available_after_shared_login_refactor(self):
        with patch.object(tetris, 'top_players', return_value=[]):
            with patch.object(players, 'prompt', return_value='n'):
                with patch.object(players, 'reset_database') as reset:
                    tetris.draw_start(Screen(keys=[ord('p'), 10]))
                    reset.assert_not_called()
