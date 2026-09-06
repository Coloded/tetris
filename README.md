# Tetris

Two terminal games written entirely in Python, using only the standard library:

- `tetris.py`: Tetris with a curses interface and a local SQLite player database.
- `dino.py`: runner with three selectable characters and a curses interface.

![Current Tetris gameplay](screenshots/gameplay.png)

## Requirements and launch

Python 3.8+ with `curses` support on macOS or Ubuntu. No pip packages, shell
helpers or separate SQLite command are needed.

On Ubuntu, if Python is not installed:

```bash
sudo apt install python3
```

Clone the project and enter its directory:

```bash
git clone https://github.com/Coloded/tetris.git
cd tetris
```

Launch Tetris:

```bash
python3 tetris.py
```

Or launch the runner:

```bash
python3 dino.py
```

Tetris needs at least **52 columns × 24 rows**; the runner needs **52 × 16**.
Both work in a standard 80 × 24 window. A smaller window automatically suspends
play until enlarged; `Q` still quits.

## Tetris rules

The board is 10 × 20. All seven classic pieces contain exactly four cells:

```text
I: [][][][]    O: [][]    T: [][][]
                 [][]        []

S:   [][]     Z: [][]
   [][]           [][]

J:   []       L: []
     []          []
   [][]          [][]
```

Each piece keeps its color after landing. Pieces come from a shuffled bag of
seven: every bag contains I, O, T, S, Z, J and L once. All difficulty levels use
this rule. Easy no longer substitutes a piece based on the board.

The side panel previews the next piece, controls, piece counts and recent events.
Dim `..` cells show where the active piece would land. The preview is part of the
same queue as the active piece.

### Controls

| Key | Action |
| --- | --- |
| Left / Right | Move |
| Up | Rotate clockwise |
| Down | Move down one cell |
| Space | Drop to the shadow and lock immediately |
| P | Pause / resume |
| R | Restart with the same player and speed |
| Q | Quit |

`S`, `F`, `D` remain aliases for left, right and rotation. Letter keys are
case-insensitive. **Space is now hard drop; pause has moved to P.**

After touching the floor or a block, a piece remains movable for **0.4 seconds**.
A successful shift or rotation while grounded can restart that delay up to
15 times per piece. Falling off an edge starts a fresh contact when it lands.
Rotations near a wall try small horizontal offsets. Hard drop locks immediately.

Restart clears the board, current score, statistics and piece queue. It keeps
the player, difficulty and saved record, and checks the current record first.
`R` and `Q` also work after game over.

### Difficulty and timing

| Level | Fall interval |
| --- | --- |
| Easy | 2.4 seconds |
| Normal | 1.4 seconds |
| Medium | 0.8 seconds |
| Hard | 0.4 seconds |

Gravity follows monotonic time, independently of key repeat and rendering.
Tetris renders at up to 30 FPS. Pause and automatic
resize suspension do not consume the contact delay. Long system suspensions
discard overdue steps instead of making the piece suddenly fall many rows.
Extremely slow terminals can still reduce visual smoothness.

### Scores and players

Points are awarded only for completed rows:

| Lines | Points |
| --- | --- |
| 1 | 1 |
| 2 | 3 |
| 3 | 6 |
| 4 | 24 |

Tetris stores `tetris_scores.sqlite3` beside its script. The database contains
each player's name, PIN,
best score and timestamps. Names and new PINs use English letters and digits.
PINs are stored as plain text for this local game. Beaten records are saved when
lines are cleared, with a final check on restart or exit.

Existing players and records are preserved. Old records may have been earned
with the previous larger pieces and five-line scoring rule.

The start screen lists the top 100 players across pages:

- Left/Right or Page Up/Page Down moves between pages.
- Enter continues to speed selection and player login.
- `P` resets the local database **only after confirmation** on the start screen.
  During gameplay `P` only pauses; it cannot erase the database.

Database files and Python cache files are excluded by `.gitignore`.

## Runner

The runner uses the same visual style as Tetris: colored characters and obstacles,
a framed field, and a character selection screen with sprite previews. At 80
columns and wider, a side panel shows score, best score, elapsed time, speed,
jumps, cleared obstacles, the next obstacle, controls and recent events.
Narrower windows use a compact layout. `P` pauses with an overlay on the field.

Choose Human, Dog or Cockroach. Their appearance differs, but all have the same
4 × 3 standing collision box, one-row ducking height, jump arc and world speed.
All three must duck under low birds or jump over obstacles.

| Key | Action |
| --- | --- |
| Up / Space | Jump |
| Up twice quickly | High jump; press again within 0.35 seconds |
| Down | Duck; a tap lasts 1 second, key repeat extends it |
| P | Pause / resume |
| R | Restart |
| Q | Quit |

Physics advances in fixed 20 ms steps with sub-cell position and velocity.
The curses display renders at up to 50 FPS.
A jump reaches five cells in half a second and returns to the ground after
one second. Press Up twice within 0.35 seconds to boost the jump to seven cells.
Only one boost is available per jump, and Space always starts an ordinary jump.
The seven-cell ceiling keeps the entire character visible even in the smallest
supported window. The terminal displays the nearest character row. Held jump
does not immediately trigger a new jump on landing; a repeated Up event inside
the double-tap window counts as a second press.

World speed rises gradually from 12 to 20 cells per second over approximately
one minute. Score increases by ten points per second survived. The best score
is kept for the current process only, without SQLite.

Cacti and birds are drawn from colored `[]` blocks, like the Tetris pieces.
Cacti are two or four character columns wide and at most three rows tall;
birds span six columns. Their collision boxes match these widths. Low birds
require ducking. Obstacle spacing reserves boosted flight, recovery
and collision widths: at least 48 columns between spawn positions, with random
extra space. New obstacles enter from beyond the right edge, including after
resizing. Collision is checked on every physics step.

## Checks

```bash
python3 -m unittest discover -s tests -v
```

Tests cover the seven-piece queue, previews, landing shadows, hard drop,
contact delay, pause, restart, timing, leaderboard pagination, runner jump
physics, character collision balance, spacing and cactus clearance at several
speeds.

## Historical screenshots

The screenshots below show the older interface and larger pieces; the current
compact interface and controls are described above.

![Start screen](screenshots/screenshot-01.png)
![Speed selection](screenshots/screenshot-02.png)
![Player login](screenshots/screenshot-03.png)
![Previous gameplay](screenshots/screenshot-04.png)
![Previous event log](screenshots/screenshot-06.png)
