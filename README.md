# TerminalCraft

Welcome to TerminalCraft, a fun 2D, side-view sandbox game that brings a Minecraft-like experience right into your Windows terminal!

## Install and run

To get started, you'll need **Python 3.11–3.14** along with `windows-curses`. Here’s how to set it up:

```powershell
pip install windows-curses
python -m terminalcraft
```

### If you're using `python` 3.15

Currently, `windows-curses` doesn’t have a wheel for CPython 3.15, which means trying to `import curses` will throw a `ModuleNotFoundError: _curses`. If you also have Python 3.11 installed, you can run this one-liner:

```powershell
py -3.11 -m terminalcraft
```

The game checks for the missing module and will show a helpful hint as well.

## Controls

| Keys          | Action                                        |
| ------------- | --------------------------------------------- |
| `A` / `D`     | walk — hold to keep moving without any stutter |
| `W` / `Space` | jump (about 1.2 tiles high)                   |
| arrow keys    | aim the block cursor, one tile per press      |
| `J` (hold)    | mine the block directly beneath the cursor     |
| `K`           | place the selected block (once per press)     |
| left mouse    | aim at the clicked tile and mine it           |
| right mouse   | aim at the clicked tile and place there       |
| `1`–`9`       | select a hotbar slot                          |
| `Q`           | quit                                          |

## Mechanics

- **Physics**: 6 tiles/s walk speed, gravity 30 tiles/s², jump 9 tiles/s,
  terminal velocity 20 tiles/s, hitbox 0.8 × 1.8.
- **Mining** takes `hardness / speed` seconds by hand, some examples: grass 0.6 s, stone
  1.5 s, bedrock never.
- **Placing**: To place a block, you need to have a block in your selected slot, an air tile within 6 tiles of your position, and it can’t overlap with your own hitbox.


## Tests

```powershell
pip install pytest
python -m pytest                                   # 342 tests
python -m terminalcraft --headless --keys a,j,left,5,esc,q
```

## Structure

```
terminalcraft/
  config.py        tunables: physics, reach, bindings, glyph sets
  input.py         raw key/mouse events -> actions, held-state emulation
  game.py          fixed-timestep loop, scene stack, playing scene
  interaction.py   reach, break time, placement rules, mining progress
  entities/        body physics (axis-separated collision) and the player
  items/           item registry and the 36-slot inventory
  render/          curses output, HUD, debug panel, headless harness
  world/           tile grid, block registry, test-world generation
```


## Future plans

Currently, there is no noise terrain, caves, or ore veins. These will be added at some point in the future.
