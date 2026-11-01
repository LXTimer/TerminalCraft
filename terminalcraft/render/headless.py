"""Headless harness: drive the real loop against a fake screen.

The game needs a Windows console to run for real. This module provides a
stand-in window that records what the renderer draws, so the same scenes can
be exercised from tests and from ``python -m terminalcraft --headless`` with a
scripted key sequence, producing plain text that can be eyeballed or
snapshot-tested.
"""

from __future__ import annotations

import curses
from collections.abc import Iterable, Sequence

from .. import config
from ..game import Game, PlayingScene, build_playing_scene
from ..input import Action, InputHandler, describe_key, symbol_to_code
from .renderer import Renderer


class HeadlessScreen:
    """A stand-in for a curses window that records drawn text.

    Implements just enough of the window API for :class:`Renderer` and
    :meth:`InputHandler.poll` to run unchanged. Attributes are not captured:
    the output is plain text (colour handling is covered by the real terminal
    and by the colour-pair unit tests).
    """

    def __init__(self, width: int, height: int, keys: Sequence[int] = ()) -> None:
        self._width = width
        self._height = height
        self._keys = list(keys)
        self._lines: list[list[str]] = [[" "] * width for _ in range(height)]

    # -- window API --------------------------------------------------------

    def nodelay(self, on: bool) -> None:
        """Accepted for interface compatibility; input never blocks here."""

    def getch(self) -> int:
        """Return the next scripted key, then -1 forever."""
        return self._keys.pop(0) if self._keys else -1

    def erase(self) -> None:
        self._lines = [[" "] * self._width for _ in range(self._height)]

    def addstr(self, y: int, x: int, text: str, attr: int = 0) -> None:
        # Mimic curses, bottom-right quirk included: PDCurses draws the text
        # and *then* reports ERR when the write touches the last cell of the
        # last row (measured on windows-curses 2.4.2), so the fake screen
        # writes first and raises the same way for the renderer to swallow.
        if 0 <= y < self._height:
            for offset, char in enumerate(text):
                if 0 <= x + offset < self._width:
                    self._lines[y][x + offset] = char
        if y == self._height - 1 and x + len(text) >= self._width:
            raise curses.error("write to bottom-right cell")

    def instr(self, y: int, x: int, n: int) -> bytes:
        """Read back *n* characters of row *y* as UTF-8 bytes (probe support)."""
        if not 0 <= y < self._height:
            return b""
        return "".join(self._lines[y][x : x + n]).encode("utf-8")

    def getmaxyx(self) -> tuple[int, int]:
        return self._height, self._width

    def noutrefresh(self) -> None:
        """Nothing to mark; :meth:`text` reads the buffer directly."""

    def resize(self, width: int, height: int) -> None:
        """Pretend the terminal was resized."""
        self._width = width
        self._height = height
        self.erase()

    # -- capture -----------------------------------------------------------

    def text(self) -> str:
        """The last frame drawn, as plain text with trailing blanks trimmed."""
        return "\n".join("".join(line).rstrip() for line in self._lines)


class _LoggingInputHandler(InputHandler):
    """InputHandler that records every dispatch, for the headless report."""

    def __init__(self) -> None:
        super().__init__()
        self.log: list[str] = []

    def dispatch(self, key: int) -> Action | None:
        action = super().dispatch(key)
        target = action.name if action is not None else "(unbound)"
        self.log.append(f"{describe_key(key)} -> {target}")
        return action


def codes_from_symbols(text: str) -> list[int]:
    """Parse a comma-separated key script ("a,j,left") into raw key codes."""
    codes: list[int] = []
    for symbol in text.split(","):
        symbol = symbol.strip()
        if symbol:
            codes.append(symbol_to_code(symbol))
    return codes


def run_headless(
    keys: Iterable[int] = (),
    *,
    ticks: int = 3,
    width: int = config.MIN_TERMINAL_WIDTH,
    height: int = config.MIN_TERMINAL_HEIGHT,
) -> str:
    """Run the playing scene for *ticks* frames and return a text report.

    The report lists every key the script fed in (and the action it mapped
    to), the resulting player/inventory state, and the final rendered screen,
    so the whole path - input mapping, physics, loop, drawing - can be checked
    without a terminal.
    """
    screen = HeadlessScreen(width, height, list(keys))
    renderer = Renderer(screen, colours=False)
    handler = _LoggingInputHandler()
    game = Game(renderer, handler)
    scene = build_playing_scene(game, handler, renderer)
    game.run(scene, max_ticks=ticks, frame_seconds=config.TICK_SECONDS)
    header = f"headless: {width}x{height}, {game.tick_count} tick(s) simulated"
    log = "\n".join(handler.log) if handler.log else "(no keys fed)"
    return (
        f"{header}\n{log}\n--- state ---\n{describe_state(scene)}\n"
        f"--- screen ---\n{screen.text()}"
    )


def describe_state(scene: PlayingScene) -> str:
    """One line each for the player, the cursor and the held item."""
    body = scene.player.body
    stack = scene.inventory.selected_stack()
    held = f"{stack.item} x{stack.count}" if stack is not None else "(empty)"
    return "\n".join(
        (
            f"player: x={body.x:.2f} y={body.y:.2f} v=({body.vx:.1f},{body.vy:.1f}) "
            f"ground={'yes' if body.on_ground else 'no'}",
            f"cursor: {scene.cursor.x},{scene.cursor.y}",
            f"hotbar slot {scene.inventory.selected + 1}: {held}",
        )
    )


def run_from_symbols(
    keys: str,
    *,
    ticks: int = 3,
    width: int = config.MIN_TERMINAL_WIDTH,
    height: int = config.MIN_TERMINAL_HEIGHT,
) -> str:
    """Like :func:`run_headless` but takes a comma-separated key script."""
    return run_headless(codes_from_symbols(keys), ticks=ticks, width=width, height=height)
