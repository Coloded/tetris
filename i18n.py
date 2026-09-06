"""Shared English/Russian interface text and startup language picker."""
import curses

_language = 'en'
RU = {
    'TOP 30 — personal bests': 'ТОП-30 — личные рекорды',
    'You: #{rank} {name} — {score}': 'Вы: №{rank} {name} — {score}',
    'Tab: top page {page}/{pages}': 'Tab: топ {page}/{pages}',
    'Well done! Passed {names}. Rank #{rank}!': 'Поздравляем! Вы обошли {names}. Место №{rank}!',
    'Enlarge to {width}x{height}. R: restart, Q: quit': 'Окно {width}x{height}. R: заново, Q: выход',

    'Player login - Esc: back': 'Вход игрока — Esc: к списку',
    'Name taken. Choose another or Esc for the list.': 'Имя занято. Другое имя или Esc: к списку.',
    'Players - choose a number or press Enter': 'Игроки — выберите номер или нажмите Enter',
    'Number + Enter: PIN | Enter: new player': 'Номер + Enter: PIN | Enter: новый игрок',
    'P: reset database | Q/Esc: quit': 'P: очистить базу | Q/Esc: выход',
    'Q/Esc: quit': 'Q/Esc: выход',
    'Player number: {number}': 'Номер игрока: {number}',
    'No such number. Enter a number from the list.': 'Нет такого номера. Введите номер из списка.',

    'Player login - Esc: quit': 'Вход игрока — Esc: выход',
    'Player name (A-Z, a-z, 0-9): ': 'Имя (латиница и цифры): ',
    'Use only English letters and digits. Press any key...': 'Только латиница и цифры. Нажмите клавишу...',
    'PIN for {name}: ': 'PIN игрока {name}: ',
    'Name taken. Wrong PIN. Press any key to retry.': 'Имя занято. Неверный PIN. Нажмите клавишу.',
    'Create PIN for {name} (A-Z, a-z, 0-9): ': 'Создайте PIN для {name} (латиница, цифры): ',
    'PIN can contain only English letters and digits. Press any key...': 'PIN: только латиница и цифры. Нажмите клавишу...',
    'Unknown player': 'Неизвестный игрок',
    'Tetris - Top 100': 'Тетрис — 100 лучших игроков',
    'Page {page}/{pages}  Left/Right: pages': 'Страница {page}/{pages}  ←/→: листать',
    'No players yet.': 'Пока нет игроков.',
    'Enter: play   P: reset database   Q: quit': 'Enter: играть  P: очистить базу  Q: выход',
    'Delete all players/scores? (y/n): ': 'Удалить игроков и рекорды? (y/n): ',
    'Select speed:': 'Выберите скорость:',
    '1) Easy   - very calm': '1) Легко — очень спокойно',
    '2) Normal - calm': '2) Обычно — спокойно',
    '3) Medium - focused': '3) Средне — быстрее',
    '4) Hard   - quick': '4) Сложно — быстро',
    'Easy': 'Легко', 'Normal': 'Обычно', 'Medium': 'Средне', 'Hard': 'Сложно',
    'Game restarted': 'Игра начата заново',
    'New best score saved: {best}': 'Новый рекорд: {best}',
    'New record saved! Previous best: {old}': 'Рекорд сохранён! Предыдущий: {old}',
    'Record unchanged.': 'Рекорд не изменился.',
    'Game over': 'Игра окончена',
    'Figure: {piece}': 'Фигура: {piece}',
    'Cleared {cleared} {word} +{points} {point_word}': 'Линий: {cleared}, очков: +{points}',
    'Pause on': 'Пауза включена', 'Pause off': 'Пауза выключена',
    'Paused: enlarge terminal to 52x24. Q: quit': 'Пауза: увеличьте окно до 52×24. Q: выход',
    'GAME OVER': 'ИГРА ОКОНЧЕНА', 'PAUSED': 'ПАУЗА', 'Playing': 'Играем',
    'Score:{score} Best:{best}': 'Очки:{score} Рек:{best}',
    'Next: {piece}': 'Далее: {piece}',
    'Left/Right: move': '←/→: движение',
    'Up: rotate  Down: soft drop': '↑: поворот  ↓: вниз',
    'Space: hard drop': 'Пробел: сбросить',
    'P:pause R:restart Q:quit': 'P:пауза R:заново Q:выход',
    'Stats:': 'Статистика:', 'Events:': 'События:',
    'Interrupted.': 'Прервано.', 'Quit.': 'Выход.',
    '{result} Score: {score}': '{result} Очки: {score}',
    'Player: {player}. Best score: {best}': 'Игрок: {player}. Рекорд: {best}',
    'Ready - good luck!': 'Готово — удачи!',
    'High jump!': 'Высокий прыжок!',
    'Paused': 'Пауза', 'Resumed': 'Игра продолжена',
    'Game over - R to retry': 'Игра окончена — R: заново',
    'Bird passed': 'Птица пройдена', 'Cactus passed': 'Кактус пройден',
    'RUNNER / Choose your character': 'РАННЕР / Выберите персонажа',
    'Human': 'Человек', 'Dog': 'Собака', 'Cockroach': 'Таракан',
    'Player: {player}': 'Игрок: {player}',
    'Same size, speed and jump for every character.': 'Размер, скорость и прыжок у всех одинаковые.',
    'Up/Space twice: high jump': '↑/Пробел дважды: высокий прыжок',
    '1-3: choose   Q: quit': '1–3: выбрать   Q: выход',
    'Paused: enlarge terminal to 52x16. Q: quit': 'Пауза: увеличьте окно до 52×16. Q: выход',
    'RUNNER': 'РАННЕР', ' PAUSED ': ' ПАУЗА ', ' GAME OVER ': ' ИГРА ОКОНЧЕНА ',
    'Cactus - jump': 'Кактус — прыгайте',
    'Tall cactus - jump': 'Большой кактус — прыжок',
    'Bird - duck': 'Птица — пригнитесь',
    'Score: {score}': 'Очки: {score}', 'Best:  {best}': 'Рекорд: {best}',
    'Speed: {speed:.1f} cells/s': 'Скорость: {speed:.1f} кл/с',
    'Passed: {passed}  Jumps: {jumps}': 'Пройдено:{passed} Прыжки:{jumps}',
    'Next:': 'Далее:', 'Clear ahead': 'Путь свободен', 'Controls': 'Управление',
    'Up/Space x2: high jump': '↑/Пробел ×2: выше',
    'Space/Up: jump  Down: duck': '↑: прыжок  ↓: пригнуться',
    'P: pause / resume': 'P: пауза / продолжить',
    'R: restart   Q: quit': 'R: заново   Q: выход',
    'R: retry   Q: quit': 'R: повторить   Q: выход',
    'Up/Space x2: high | Down: duck | P: pause': '↑/Пробел ×2: выше | ↓: вниз | P: пауза',
    '{name} S:{score} Best:{best} {state}': '{name} Очки:{score} Рек:{best} {state}',
    'Up/Space x2:high Down:duck P:pause R/Q': '↑/Пробел ×2:выше ↓:вниз P:пауза R/Q',
    'Runner stopped. Score: {score} Best: {best}': 'Раннер закрыт. Очки: {score} Рекорд: {best}',
}


def set_language(language):
    global _language
    if language not in ('ru', 'en'):
        raise ValueError('Unsupported language')
    _language = language


def tr(text, **values):
    translated = RU.get(text, text) if _language == 'ru' else text
    return translated.format(**values) if values else translated


def choose_language(screen):
    screen.nodelay(False)
    while True:
        screen.erase()
        rows, cols = screen.getmaxyx()
        lines = ('Язык / Language', '', '1 — Русский', '2 — English', '', 'Q / Esc — Выход / Quit')
        for y, line in enumerate(lines):
            if y < rows:
                try:
                    screen.addstr(y, 0, line[:max(0, cols - 1)])
                except curses.error:
                    pass
        screen.refresh()
        key = screen.getch()
        if key in (ord('1'), ord('2')):
            set_language('ru' if key == ord('1') else 'en')
            return True
        if key in (27, ord('q'), ord('Q')):
            return False
