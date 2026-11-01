"""The debug overlay drawn on top of whatever scene is running.

Milestone 1 shipped the key/action view; every milestone since has added
fields for what it brought. Scenes pass their own fields in, so this function
does not grow a parameter per milestone.

The panel is deliberately short: it is opaque (the world behind it would
otherwise run through the text) and the player sits in the middle of the
screen, so a tall panel would hide the character it is describing.
"""

from __future__ import annotations

from collections.abc import Sequence

from ..input import Action, describe_key
from .renderer import Camera, Renderer

COLUMN_WIDTH = 34
"""Characters per field column; two columns fit the minimum 80-wide terminal."""


def draw_debug_screen(
    renderer: Renderer,
    *,
    title: str,
    last_key: int | None,
    last_action: Action | None,
    tick_count: int,
    fps: float,
    camera: Camera,
    glyphs: str,
    fields: Sequence[tuple[str, str]] = (),
    hint: str = "",
) -> None:
    """Draw the overlay: title, key and loop stats, then the scene's fields.

    Fields are packed two per line, in the order given.
    """
    width, height = renderer.size
    entries = (
        ("last key", describe_key(last_key)),
        ("action", last_action.name if last_action is not None else "(none)"),
        ("ticks", str(tick_count)),
        ("fps", f"{fps:.0f}"),
        ("view", f"{width}x{height}"),
        ("camera", f"{camera.x:.0f},{camera.y:.0f}"),
        ("glyphs", glyphs),
        *fields,
    )
    lines = [
        _field_text(entries[i], COLUMN_WIDTH)
        + (_field_text(entries[i + 1], COLUMN_WIDTH) if i + 1 < len(entries) else "")
        for i in range(0, len(entries), 2)
    ]
    panel_width = min(2 * COLUMN_WIDTH, width)
    panel_rows = 1 + len(lines) + (1 if hint else 0)
    for row in range(min(panel_rows, height)):
        renderer.addstr(row, 0, " " * panel_width)
    renderer.addstr(0, 0, title, renderer.attr("title"))
    for index, line in enumerate(lines):
        renderer.addstr(1 + index, 0, line, renderer.attr("value"))
    if hint:
        renderer.addstr(1 + len(lines), 0, hint, renderer.attr("label"))


def _field_text(field: tuple[str, str], width: int) -> str:
    """One label/value pair padded to a column, never wider than *width*."""
    label, value = field
    return f"{label} {value}"[: width - 1].ljust(width)
