"""Heads-up display: the hotbar and what is being mined.

Two rows at the bottom of the screen: status (held item, mining progress)
above, the nine hotbar slots below.
"""

from __future__ import annotations

from ..items.items import item_for
from ..items.inventory import Inventory
from ..world import blocks
from .renderer import Renderer

SLOT_COLUMNS = 7
"""Screen columns per hotbar slot: bracket, glyph (2), count (2), space,
bracket."""

HUD_ROWS = 2
"""Screen rows the HUD covers at the bottom. Scenes use it to tell a click on
the hotbar from a click on the world."""

PROGRESS_WIDTH = 8
"""Cells in the mining progress bar."""


def draw_hud(
    renderer: Renderer,
    inventory: Inventory,
    *,
    mining_block: str | None = None,
    mining_fraction: float = 0.0,
) -> None:
    """Draw the hotbar and, while mining, the progress toward a break."""
    width, height = renderer.size
    # Blank the two rows first: the world is already drawn underneath and
    # would otherwise show through the gaps between slots.
    for row in range(height - HUD_ROWS, height):
        renderer.addstr(row, 0, " " * width)
    _draw_status(
        renderer,
        inventory,
        row=height - 2,
        mining_block=mining_block,
        mining_fraction=mining_fraction,
    )
    _draw_hotbar(renderer, inventory, row=height - 1)


def _draw_status(
    renderer: Renderer,
    inventory: Inventory,
    *,
    row: int,
    mining_block: str | None,
    mining_fraction: float,
) -> None:
    """Selected item on the left, mining progress on the right."""
    width, _ = renderer.size
    stack = inventory.selected_stack()
    if stack is None:
        label = "empty hand"
    else:
        label = f"{item_for(stack.item).display} x{stack.count}"
    renderer.addstr(row, 0, label, renderer.attr("value"))
    if mining_block is None:
        return
    filled = min(max(round(mining_fraction * PROGRESS_WIDTH), 0), PROGRESS_WIDTH)
    bar = "#" * filled + "-" * (PROGRESS_WIDTH - filled)
    text = f"{mining_block} [{bar}]"
    renderer.addstr(row, width - len(text), text, renderer.attr("label"))


def _draw_hotbar(renderer: Renderer, inventory: Inventory, *, row: int) -> None:
    """One cell per slot; the selected slot is bracketed and bright."""
    bracket_attr = renderer.attr("value")
    dim_attr = renderer.attr("label")
    for index, stack in enumerate(inventory.hotbar()):
        left = index * SLOT_COLUMNS
        selected = index == inventory.selected
        brackets = bracket_attr if selected else dim_attr
        renderer.addstr(row, left, "[" if selected else " ", brackets)
        renderer.addstr(row, left + 6, "]" if selected else " ", brackets)
        if stack is None:
            continue
        item = item_for(stack.item)
        block = blocks.block_for(item.block)
        renderer.addstr(
            row,
            left + 1,
            renderer.glyph_for_block(block.id),
            renderer.pair_attr(block.fg, block.bg),
        )
        renderer.addstr(row, left + 3, f"{stack.count:>3}", renderer.attr("value"))
