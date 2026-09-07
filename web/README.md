# Telegram Mini App assets

Bot: `@game1500`. Server directory: `/var/game1500` on `bg.netnum.ru`.

`assets/tetrominoes/` contains seven original PNG tetromino sprites, one per
piece. See `manifest.json` for filenames and `prompts.json` for generation
instructions. Generated with the built-in image generation tool.

These are artwork assets for the future web client, not a running Mini App.
Gameplay must use logical grid coordinates independently of sprite dimensions.

## Account requirements

- Identify accounts by the Telegram user ID from server-validated `initData`.
- Display only the Telegram account name (`first_name` plus `last_name` when
  present); update it on subsequent authenticated launches. No editable nickname,
  name registration form, or PIN. Treat the name as text, never HTML.
- Store the bot token only in server configuration, never in browser assets or Git.
- Keep SQLite on the server; expose authenticated APIs for games and rankings.

## Planned ranked gameplay

Use a fixed 10 by 20 board, mobile controls, keyboard support, Russian/English,
server-validated game results and a top 30 with the current player's rank.
Terminal accounts are not automatically linked to Telegram accounts by name.
