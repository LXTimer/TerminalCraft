"""Constants, key bindings, glyph sets and world tuning.

Every tunable value lives here so gameplay code never hard-codes numbers.
"""

from __future__ import annotations

# --- Main loop ---------------------------------------------------------------

TICK_RATE: int = 30
"""Simulation updates per second (fixed timestep)."""

TICK_SECONDS: float = 1.0 / TICK_RATE

MAX_FRAME_SECONDS: float = 0.25
"""Longest frame the accumulator will simulate. Longer stalls (breakpoints, OS
hiccups) are dropped instead of fast-forwarding the world through them."""

# --- Terminal ----------------------------------------------------------------

MIN_TERMINAL_WIDTH: int = 80
MIN_TERMINAL_HEIGHT: int = 24

# --- Input -------------------------------------------------------------------

# Symbolic key names -> actions. ``input.py`` resolves each symbol to the raw
# curses key code a terminal sends: single characters map to their ordinal,
# named symbols ("space", "esc", "up", ...) to the matching curses constant.
KEY_BINDINGS: dict[str, tuple[str, ...]] = {
    "move_left": ("a",),
    "move_right": ("d",),
    "jump": ("w", "space"),
    "cursor_up": ("up",),
    "cursor_down": ("down",),
    "cursor_left": ("left",),
    "cursor_right": ("right",),
    "mine": ("j",),
    "place": ("k",),
    "hotbar_1": ("1",),
    "hotbar_2": ("2",),
    "hotbar_3": ("3",),
    "hotbar_4": ("4",),
    "hotbar_5": ("5",),
    "hotbar_6": ("6",),
    "hotbar_7": ("7",),
    "hotbar_8": ("8",),
    "hotbar_9": ("9",),
    "inventory": ("e",),
    "crafting": ("c",),
    "pause": ("esc",),
    # Escape hatch for the milestone-1 debug screen. Milestone 8 adds a pause
    # menu that can also quit to the title screen.
    "quit": ("q",),
}

#: Mouse buttons as *extra* bindings for actions that already have keys.
#: Left mines, right places; the keyboard bindings above keep working
#: unchanged, so both input paths stay live at the same time. Values are
#: ``"left"`` or ``"right"``.
MOUSE_BINDINGS: dict[str, str] = {
    "mine": "left",
    "place": "right",
}

# --- World --------------------------------------------------------------------

WORLD_WIDTH: int = 512
"""World width in tiles (fixed by the spec)."""

WORLD_HEIGHT: int = 128
"""World height in tiles; y=0 is the top row."""

TILE_WIDTH: int = 2
"""Screen columns per tile. Tiles are drawn 2 columns wide x 1 row tall so they
look square in terminal cells, which are about twice as tall as they are wide."""

# --- Glyph sets ---------------------------------------------------------------

#: Tile glyphs per block name, exactly :data:`TILE_WIDTH` columns wide.
#: ``"unicode"`` is the primary set; ``"ascii"`` is the fallback for terminals
#: that cannot show block characters. A block missing from the active set
#: falls back to the glyph in its registry entry.
GLYPH_SETS: dict[str, dict[str, str]] = {
    "unicode": {
        "air": "  ",
        "grass": "██",
        "dirt": "▒▒",
        "stone": "██",
        "cobblestone": "██",
        "log": "██",
        "leaves": "██",
        "planks": "██",
        "crafting_table": "██",
        "bedrock": "▓▓",
    },
    "ascii": {
        "air": "  ",
        "grass": "##",
        "dirt": "..",
        "stone": "##",
        "cobblestone": "%%",
        "log": "||",
        "leaves": "**",
        "planks": "==",
        "crafting_table": "[]",
        "bedrock": "##",
    },
}

GLYPH_SET: str = "auto"
"""Active glyph set: ``"auto"`` probes the terminal at startup; ``"unicode"``
or ``"ascii"`` force one (useful when the probe guesses wrong)."""

# --- Terrain (milestone-2 test world) -----------------------------------------

TERRAIN_BASE: int = 30
"""Mean surface height, in tiles from the top of the world."""

TERRAIN_AMPLITUDE: int = 6
TERRAIN_DETAIL: int = 2
"""Amplitudes of the two sine layers that make up the test-world hills."""

DIRT_DEPTH: int = 4
"""Rows of dirt between the grass surface and the stone below."""

# --- Player physics (milestone 3) ---------------------------------------------

GRAVITY: float = 30.0
"""Downward acceleration, tiles per second squared."""

JUMP_SPEED: float = 9.0
"""Upward speed at the instant of a jump, tiles per second."""

TERMINAL_VELOCITY: float = 20.0
"""Fastest free fall, so a long drop stays readable at 30 ticks per second."""

WALK_SPEED: float = 6.0
"""Horizontal walking speed, tiles per second."""

PLAYER_WIDTH: float = 0.8
"""Hitbox width in tiles: narrower than a tile so one-tile gaps are passable."""

PLAYER_HEIGHT: float = 1.8
"""Hitbox height in tiles: shorter than two so two-tile tunnels are passable."""

STEP_UP_HEIGHT: float = 1.0
"""Tallest ledge the player walks up instead of jumping."""

HOLD_WINDOW_SECONDS: float = 0.12
"""How long after its last key event an action still counts as held.

Curses reports key *events*, not key state, so "held" has to be emulated with
a time window. It is longer than the usual OS key-repeat delay (about 33 ms
here) so repeats keep the window open, and short enough that a tap does not
feel like a stuck key."""

# --- Interaction (milestones 3 and 5) -----------------------------------------

INTERACTION_REACH: float = 6.0
"""Tiles between the player centre and a block it may mine or place."""

HAND_MINING_SPEED: float = 1.0
"""Mining speed with bare hands. Break time is ``hardness / speed``."""

NOTICE_SECONDS: float = 1.5
"""How long a refused mine or placement stays on the hint line.

A refusal has to be visible without lingering: the player holds the key and
nothing happens, so a message that expires is the only feedback they get."""

# --- Inventory (milestone 6 data model, hotbar used from milestone 3) ---------

INVENTORY_SIZE: int = 36
"""Total slots; the first :data:`HOTBAR_SIZE` are the hotbar."""

HOTBAR_SIZE: int = 9

MAX_STACK_SIZE: int = 64

STARTER_ITEMS: tuple[tuple[str, int], ...] = (("dirt", 8), ("planks", 8))
"""What the player starts with. Without this, placing would silently do
nothing until the first block is mined, which reads as a broken key."""

# --- Camera -------------------------------------------------------------------

CAMERA_DEADZONE_Y: float = 2.0
"""Vertical distance the player may drift from the view centre before the
camera follows. Keeps a 1.3-tile jump from shaking the whole screen."""

CAMERA_MAX_SPEED_Y: float = 24.0
"""Fastest vertical camera speed. Must exceed :data:`TERMINAL_VELOCITY`, or a
long fall would leave the player off-screen."""

# --- Player sprite ------------------------------------------------------------

PLAYER_SPRITES: dict[str, tuple[str, str]] = {
    "unicode": ("@@", "██"),
    "ascii": ("@@", "##"),
}
"""One glyph row per line, :data:`TILE_WIDTH` columns wide, keyed by glyph set.
The head is ASCII in both sets because ``@`` is unambiguously narrow."""

PLAYER_FG: int = 7  # white
PLAYER_BG: int = 4  # blue
"""Colours of the player sprite (standard curses colour numbers)."""
