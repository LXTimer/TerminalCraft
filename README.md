# TerminalCraft

A 2D side-view Minecraft-like sandbox game that runs in the terminal. 

## Install and run

Requires **Python 3.11–3.14** and the `windows-curses` package (the `curses`
C module is not bundled with Windows Python):

```powershell
pip install windows-curses
python -m terminalcraft
```

### If your `python` is 3.15

`windows-curses` has no wheel for CPython 3.15 yet, so `import curses` fails
with `ModuleNotFoundError: _curses`. Either run with an older interpreter:

```powershell
py -3.11 -m terminalcraft
```

…or install the dependencies into 3.15 once a matching wheel exists. The
game itself detects the missing module and prints this hint instead of a
traceback.

## Controls

| Keys          | Action                                    |
| ------------- | ----------------------------------------- |
| `A` / `D`     | walk left / right (hold to keep walking)  |
| `W` / `Space` | jump                                      |
| arrow keys    | move the block cursor one tile            |
| `J` (hold)    | mine the block under the cursor           |
| `K`           | place the selected block                  |
| left mouse    | aim at the clicked tile and mine it       |
| right mouse   | aim at the clicked tile and place there   |
| `1`–`9`       | select a hotbar slot                      |
| `E`           | inventory (milestone 6)                   |
| `C`           | crafting (milestone 7)                    |
| `Esc`         | pause (milestone 8)                       |
| `Q`           | quit                                      |

All bindings live in `terminalcraft/config.py` (`KEY_BINDINGS` for the
keyboard, `MOUSE_BINDINGS` for the mouse).

The mouse buttons are **additional** bindings for the same mine and place
actions — nothing is remapped, and keyboard and mouse can be used at the same
time. A click aims the cursor at the tile it landed on before acting, so
clicking a block three tiles away mines that block rather than whatever the
arrow keys last selected. Clicks on the hotbar rows are ignored.

Mouse reporting needs a console that forwards mouse events: it works in
`conhost.exe`, and in Windows Terminal when the host passes events through to
the console app. If clicks do nothing, the keyboard is unaffected — the debug
panel's `mouse` field (`on`/`off`) shows whether the terminal accepted the
request.

## Game rules as implemented

- **Walking** is 6 tiles/s with gravity 30 tiles/s², a 9 tiles/s jump (about
  1.2 tiles of height), terminal fall speed 20 tiles/s, and a hitbox of
  0.8 × 1.8 tiles. Ledges up to one tile are stepped up automatically;
  taller ones need a jump.
- **Mining** takes `hardness / speed` seconds by hand (grass 0.6 s, stone
  1.5 s, bedrock never). Progress belongs to one tile: moving the cursor or
  releasing `J` starts over. A full inventory blocks breaking, so no drop is
  ever lost.
- **Placing** needs the selected slot to hold a block, the target tile to be
  air within 6 tiles of the player, not inside the player, and next to
  something solid.
- The player starts with 8 dirt and 8 planks, so `K` works before the first
  block is mined.
- The camera tracks the player horizontally and eases vertically with a
  2-tile dead zone, which keeps jumps from shaking the whole screen.

## Tiles and glyphs

Each tile is drawn 2 columns wide x 1 row tall. The renderer probes the
terminal at startup and picks the `unicode` glyph set (`██▒▓`) when it can,
falling back to `ascii` (`##..%%`) otherwise; the debug overlay shows which
set is active. Force one with `GLYPH_SET` in `terminalcraft/config.py`.
The player is `@@` over `██` (or `##` in the ASCII set) in white on blue.

## Tests and headless mode

```powershell
pip install pytest
python -m pytest                                   # 329 tests
python -m terminalcraft --headless --keys a,j,left,5,esc,q
```

Headless mode drives the real loop against a fake screen and prints the
key→action mapping, the resulting player/inventory state and the final frame,
so the whole path can be checked without a terminal.

## Layout

```
terminalcraft/
  config.py        tunables: physics, reach, inventory size, glyph sets
  input.py         raw key codes and mouse events -> actions, held-state emulation
  game.py          fixed-timestep loop, scene stack, playing scene
  interaction.py   reach, break time, placement rules, mining progress
  entities/        body physics (axis-separated collision) and the player
  items/           item registry and the 36-slot inventory
  render/          curses output, HUD, debug panel, headless harness
  world/           tile grid, block registry, test-world generation
```

`entities/`, `items/`, `interaction.py` and `world/` never import `curses`;
only `input.py` and `render/` do. `tests/test_architecture.py` enforces it.
