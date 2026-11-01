"""Curses output: screen setup, colour pairs, camera, tile drawing, refresh.

``render/`` is the only package (besides ``input.py``) allowed to import
``curses``. Scenes draw exclusively through :class:`Renderer`, which owns the
window, the colour-pair table, the camera and the double-buffered refresh, so
the drawing backend stays swappable and the game logic stays testable.
"""

from __future__ import annotations

import curses
import locale
import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Protocol

from .. import config
from ..world import blocks
from ..world.world import World


class Screen(Protocol):
    """The subset of a curses window the renderer needs.

    Declared structurally so tests and the headless harness can pass a
    stand-in window without a real terminal.
    """

    def nodelay(self, on: bool) -> None:
        ...

    def getch(self) -> int:
        ...

    def erase(self) -> None:
        ...

    def addstr(self, y: int, x: int, text: str, attr: int = 0) -> None:
        ...

    def instr(self, y: int, x: int, n: int) -> bytes:
        ...

    def getmaxyx(self) -> tuple[int, int]:
        ...

    def noutrefresh(self) -> None:
        ...


@dataclass
class Camera:
    """Where the view looks, in tile units.

    ``x``/``y`` is the centre of the view; :meth:`Renderer.view_origin` turns
    it into a top-left tile origin clamped to the world edges.
    """

    x: float = 0.0
    y: float = 0.0

    def move(self, dx: float, dy: float) -> None:
        """Pan the camera by a tile-space delta."""
        self.x += dx
        self.y += dy

    def follow(self, target_x: float, target_y: float, dt: float) -> None:
        """Centre on a point, easing vertically so jumps do not shake the view.

        Horizontally the camera tracks immediately: the view origin is
        quantised to whole tiles anyway, so smoothing would only add lag.
        Vertically it stays put until the target drifts more than
        :data:`~terminalcraft.config.CAMERA_DEADZONE_Y` from the centre, then
        closes the gap at up to :data:`~terminalcraft.config.CAMERA_MAX_SPEED_Y`
        - fast enough to keep up with a terminal-velocity fall.
        """
        self.x = target_x
        offset = target_y - self.y
        distance = abs(offset)
        if distance <= config.CAMERA_DEADZONE_Y:
            return
        step = min(distance - config.CAMERA_DEADZONE_Y, config.CAMERA_MAX_SPEED_Y * dt)
        self.y += math.copysign(step, offset)


class Renderer:
    """Draws frames through a curses window: text, colour pairs and tiles.

    Owns colour-pair allocation with graceful degradation (plain attributes
    when the terminal reports fewer than eight colours), the camera, the
    glyph set chosen for this terminal and the double-buffered refresh.
    Scenes never touch the window: they call :meth:`addstr`,
    :meth:`draw_world` and :meth:`present` through this object.
    """

    #: Semantic attribute names scenes can ask for via :meth:`attr`.
    ATTRS = ("label", "value", "title", "warning")

    def __init__(self, screen: Screen, *, colours: bool = True, glyph_set: str | None = None) -> None:
        self._screen = screen
        self._height, self._width = screen.getmaxyx()
        self._colourful = False
        self._pairs: dict[tuple[int, int], int] = {}
        self._next_pair = 1
        # Fallback attributes: bold/dim work without colour support.
        self._attrs: dict[str, int] = {
            "label": curses.A_DIM,
            "value": curses.A_BOLD,
            "title": curses.A_BOLD,
            "warning": curses.A_BOLD,
        }
        if colours:
            self._init_colours()
        #: Name of the glyph set in use ("unicode" or "ascii"); the debug
        #: overlay shows it so a wrong guess is visible immediately.
        self.glyph_set_name = _resolve_glyph_set(glyph_set)
        #: View position. Milestone 2 pans it with the cursor keys; milestone
        #: 3 makes it follow the player.
        self.camera = Camera()
        self._tile_glyphs: dict[int, str] = {}
        self._tile_attrs: dict[int, int] = {}
        self._tiles_ready = False

    # -- setup ------------------------------------------------------------

    def _init_colours(self) -> None:
        """Start colour support when the terminal has it; otherwise stay plain."""
        if not curses.has_colors() or curses.COLORS < 8:
            return
        try:
            curses.start_color()
        except curses.error:
            return
        self._colourful = True
        self._attrs["warning"] = self.pair_attr(curses.COLOR_RED, curses.COLOR_BLACK) | curses.A_BOLD

    def pair_attr(self, fg: int, bg: int) -> int:
        """Attribute for a foreground/background pair, or 0 without colour."""
        if not self._colourful:
            return 0
        key = (fg, bg)
        pair = self._pairs.get(key)
        if pair is None:
            if self._next_pair >= curses.COLOR_PAIRS:
                return 0  # out of colour pairs: fall back to the default
            try:
                curses.init_pair(self._next_pair, fg, bg)
            except curses.error:
                return 0
            pair = self._next_pair
            self._pairs[key] = pair
            self._next_pair += 1
        return curses.color_pair(pair)

    # -- geometry ---------------------------------------------------------

    @property
    def size(self) -> tuple[int, int]:
        """Current terminal size as ``(width, height)``."""
        return self._width, self._height

    @property
    def too_small(self) -> bool:
        """True when the terminal cannot fit the minimum playfield."""
        return (
            self._width < config.MIN_TERMINAL_WIDTH
            or self._height < config.MIN_TERMINAL_HEIGHT
        )

    def handle_resize(self) -> None:
        """Re-read the terminal size after a ``KEY_RESIZE`` event."""
        self._height, self._width = self._screen.getmaxyx()

    def view_origin(self, world: World) -> tuple[int, int]:
        """Top-left tile of the current view.

        The view is centred on the camera and clamped so it never shows past
        the world edges. A world smaller than the view is centred instead;
        the origin may then be negative, and out-of-bounds tiles read as air,
        which draws as sky.
        """
        width, height = self.size
        view_w = max(1, width // config.TILE_WIDTH)
        view_h = max(1, height)
        if world.width <= view_w:
            origin_x = (world.width - view_w) // 2
        else:
            origin_x = min(max(int(self.camera.x - view_w / 2), 0), world.width - view_w)
        if world.height <= view_h:
            origin_y = (world.height - view_h) // 2
        else:
            origin_y = min(max(int(self.camera.y - view_h / 2), 0), world.height - view_h)
        return origin_x, origin_y

    @property
    def screen(self) -> Screen:
        """The underlying window (handed to :meth:`InputHandler.poll`)."""
        return self._screen

    # -- attributes -------------------------------------------------------

    def attr(self, name: str) -> int:
        """A semantic attribute (``"label"``, ``"value"``, ...) as an int."""
        return self._attrs.get(name, 0)

    # -- drawing ----------------------------------------------------------

    def begin_frame(self) -> None:
        """Start a new frame (erases; never ``clear()``, to avoid flicker)."""
        self._screen.erase()

    def addstr(self, y: int, x: int, text: str, attr: int = 0) -> None:
        """Draw *text* at ``(y, x)``; silently drops anything off-screen."""
        if not 0 <= y < self._height or not 0 <= x < self._width or not text:
            return
        if x + len(text) > self._width:
            text = text[: self._width - x]
        try:
            self._screen.addstr(y, x, text, attr)
        except curses.error:
            pass  # curses refuses the bottom-right cell; dropping it is fine

    def draw_world(self, world: World) -> None:
        """Draw the visible slice of *world*.

        Tiles are :data:`~terminalcraft.config.TILE_WIDTH` columns wide, so
        each screen row is emitted as runs of same-coloured tiles - one
        ``addstr`` per run instead of one per tile.
        """
        self._prepare_tiles()
        width, height = self.size
        view_w = max(1, width // config.TILE_WIDTH)
        view_h = max(1, height)
        origin_x, origin_y = self.view_origin(world)
        for row in range(view_h):
            self._draw_tile_row(world, row, origin_x, origin_y + row, view_w)

    def _prepare_tiles(self) -> None:
        """Resolve glyph and colour attribute for every registered block.

        Runs lazily on the first :meth:`draw_world`, so colour pairs are only
        allocated once colour support is known to be up.
        """
        if self._tiles_ready:
            return
        glyphs = config.GLYPH_SETS.get(self.glyph_set_name, {})
        for block in blocks.BLOCKS:
            self._tile_glyphs[block.id] = glyphs.get(block.name, block.glyph)
            self._tile_attrs[block.id] = self.pair_attr(block.fg, block.bg)
        self._tiles_ready = True

    def _draw_tile_row(
        self, world: World, row: int, origin_x: int, tile_y: int, view_w: int
    ) -> None:
        """Draw one screen row of tiles as runs of the same colour."""
        attr = -1
        parts: list[str] = []
        col = 0
        for i in range(view_w):
            tile_id = world.get(origin_x + i, tile_y)
            tile_attr = self._tile_attrs[tile_id]
            if parts and tile_attr != attr:
                self.addstr(row, col, "".join(parts), attr)
                col += config.TILE_WIDTH * len(parts)
                parts.clear()
            attr = tile_attr
            parts.append(self._tile_glyphs[tile_id])
        if parts:
            self.addstr(row, col, "".join(parts), attr)

    def draw_centered(self, text: str, attr: int = 0) -> None:
        """Draw a single line of text centred on the screen."""
        width, height = self.size
        x = max(0, (width - len(text)) // 2)
        self.addstr(height // 2, x, text, attr)

    # -- sprites and markers ------------------------------------------------

    def glyph_for_block(self, block_id: int) -> str:
        """The glyph the active set uses for *block_id* (e.g. for the HUD)."""
        self._prepare_tiles()
        return self._tile_glyphs[block_id]

    def screen_pos(self, world: World, x: float, y: float) -> tuple[int, int] | None:
        """Screen ``(row, column)`` of a world point given in tiles.

        Returns None when the point is outside the view, so callers can skip
        drawing sprites that are nowhere near the screen.
        """
        origin_x, origin_y = self.view_origin(world)
        row = int(round(y - origin_y))
        column = int(round((x - origin_x) * config.TILE_WIDTH))
        if not 0 <= row < self._height or not 0 <= column < self._width:
            return None
        return row, column

    def tile_screen_pos(self, world: World, tile_x: int, tile_y: int) -> tuple[int, int] | None:
        """Screen ``(row, column)`` of a tile's top-left cell, or None."""
        pos = self.screen_pos(world, tile_x, tile_y)
        if pos is None:
            return None
        row, column = pos
        if column + config.TILE_WIDTH > self._width:
            return None
        return row, column

    def tile_at(self, world: World, column: int, row: int) -> tuple[int, int] | None:
        """World tile under a screen cell, or None when there is none.

        The inverse of :meth:`tile_screen_pos`, for mouse input: a tile spans
        :data:`~terminalcraft.config.TILE_WIDTH` columns, so both of its cells
        map to the same tile. Cells outside the world are rejected - the view
        can start before the world does when the world is narrower than the
        window, and out-of-bounds tiles read as air but cannot be edited.
        """
        if not 0 <= column < self._width or not 0 <= row < self._height:
            return None
        origin_x, origin_y = self.view_origin(world)
        tile_x = origin_x + column // config.TILE_WIDTH
        tile_y = origin_y + row
        if 0 <= tile_x < world.width and 0 <= tile_y < world.height:
            return tile_x, tile_y
        return None

    def draw_sprite(self, top: int, left: int, lines: Sequence[str], attr: int) -> None:
        """Draw a multi-line sprite at ``(top, left)``, clipping off-screen parts."""
        for offset, line in enumerate(lines):
            self.addstr(top + offset, left, line, attr)

    def draw_highlight(
        self, world: World, tile_x: int, tile_y: int, *, warning: bool = False
    ) -> None:
        """Invert the tile under *tile_x*, *tile_y* so the cursor is visible.

        Air has no glyph, so an inverted pair of spaces doubles as the marker
        for "this empty tile would be built on". *warning* paints it red
        instead of the block's own colour: a cursor out of reach refuses
        silently, so the colour is the only thing saying why.
        """
        self._prepare_tiles()
        pos = self.tile_screen_pos(world, tile_x, tile_y)
        if pos is None:
            return
        row, column = pos
        block_id = world.get(tile_x, tile_y)
        base = self.attr("warning") if warning else self._tile_attrs[block_id]
        self.addstr(row, column, self._tile_glyphs[block_id], base | curses.A_REVERSE)

    def present(self) -> None:
        """Flip the frame: mark everything refreshed, then update once."""
        self._screen.noutrefresh()
        try:
            curses.doupdate()
        except curses.error:
            pass  # no curses session active (headless harness)


def _resolve_glyph_set(requested: str | None) -> str:
    """Validate a glyph-set request.

    ``"auto"`` only means something when a real terminal can be probed, which
    happens in :func:`init_screen`; a renderer built without one (tests, the
    headless harness) uses the full unicode set.
    """
    name = config.GLYPH_SET if requested is None else requested
    if name == "auto":
        return "unicode"
    if name not in config.GLYPH_SETS:
        raise ValueError(
            f"unknown glyph set: {name!r} (known: {sorted(config.GLYPH_SETS)})"
        )
    return name


def _choose_glyph_set(stdscr: Screen) -> str:
    """Pick the glyph set this terminal can actually render.

    Writes the unicode set's distinctive glyphs to the top-left corner - the
    first frame erases the screen again, so nothing is ever shown - and reads
    them back. A terminal that cannot encode the glyphs, or whose text
    encoding would not match what it displays, gets the ASCII set instead.
    ``config.GLYPH_SET`` forces either set without probing.
    """
    if config.GLYPH_SET != "auto":
        return config.GLYPH_SET
    probe = "".join(dict.fromkeys(config.GLYPH_SETS["unicode"].values())).strip()
    if not probe:
        return "unicode"
    try:
        stdscr.addstr(0, 0, probe)
        stored = stdscr.instr(0, 0, len(probe) * 4)
    except (curses.error, UnicodeEncodeError):
        return "ascii"
    encoding = (locale.getpreferredencoding() or "utf-8").lower().replace("-", "")
    if encoding in ("utf8", "cp65001") and stored.startswith(probe.encode("utf-8")):
        # The terminal stores and shows UTF-8, so the block glyphs are safe.
        return "unicode"
    try:
        if stored.startswith(probe.encode(encoding)):
            # _curses encoded to the terminal's own codepage, which has the
            # glyphs (e.g. the full block in CP437/CP936).
            return "unicode"
    except (LookupError, UnicodeEncodeError):
        pass
    return "ascii"


def init_screen(stdscr: Screen) -> Renderer:
    """Configure curses for gameplay and wrap it in a :class:`Renderer`.

    ``curses.wrapper`` has already disabled echo and enabled cbreak/keypad;
    this adds non-blocking input, hides the cursor and picks the glyph set
    the terminal can render.
    """
    stdscr.nodelay(True)
    try:
        curses.curs_set(0)
    except curses.error:
        pass  # not every terminal can hide the cursor
    return Renderer(stdscr, glyph_set=_choose_glyph_set(stdscr))


def run_with_curses(app: Callable[[Screen], None]) -> None:
    """Run ``app(screen)`` inside ``curses.wrapper``.

    The wrapper guarantees the terminal is restored even if the game crashes,
    which is why the entry point goes through here instead of managing
    ``initscr``/``endwin`` itself.
    """
    curses.wrapper(app)
