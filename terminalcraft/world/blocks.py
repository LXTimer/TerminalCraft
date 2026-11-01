"""The block registry: one dataclass, one table, no block-specific code.

Every block in the game is an entry in :data:`BLOCKS`. Adding a block means
adding one entry here plus its glyph in every set in ``config.GLYPH_SETS``;
nothing else in the codebase may branch on block identity.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

# Block ids. A tile is stored as one of these bytes, so ids must stay stable
# once a save format exists (milestone 8) and are never reused.
AIR = 0
GRASS = 1
DIRT = 2
STONE = 3
COBBLESTONE = 4
LOG = 5
LEAVES = 6
PLANKS = 7
CRAFTING_TABLE = 8
BEDROCK = 9

# Standard curses colour numbers (``curses.COLOR_*`` are exactly these ints).
# Spelled out here so this module never has to import curses.
BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = range(8)


@dataclass(frozen=True)
class Block:
    """Everything the game knows about one kind of tile."""

    id: int
    name: str
    glyph: str
    """Tile glyph, exactly ``config.TILE_WIDTH`` columns wide."""
    fg: int
    bg: int
    solid: bool
    hardness: float
    """Seconds to break by hand; ``math.inf`` means unbreakable."""
    tool: str | None
    """Tool class that speeds up mining: ``"pickaxe"``, ``"axe"``, ``"shovel"``
    or ``None``."""
    min_tool_tier: int
    """Lowest tool tier that still yields the drop (1 = wooden, 2 = stone)."""
    drops: str
    """Item name dropped when broken; ``""`` drops nothing."""


#: The registry itself. Order defines the ids above; keep them contiguous.
BLOCKS: tuple[Block, ...] = (
    Block(AIR, "air", "  ", BLACK, BLACK, False, 0.0, None, 0, ""),
    Block(GRASS, "grass", "██", GREEN, BLACK, True, 0.6, "shovel", 0, "dirt"),
    Block(DIRT, "dirt", "▒▒", YELLOW, BLACK, True, 0.5, "shovel", 0, "dirt"),
    Block(STONE, "stone", "██", WHITE, BLACK, True, 1.5, "pickaxe", 1, "cobblestone"),
    Block(COBBLESTONE, "cobblestone", "██", CYAN, BLACK, True, 1.5, "pickaxe", 1, "cobblestone"),
    Block(LOG, "log", "██", RED, BLACK, True, 1.0, "axe", 0, "log"),
    Block(LEAVES, "leaves", "██", GREEN, BLACK, True, 0.2, None, 0, ""),
    Block(PLANKS, "planks", "██", YELLOW, BLACK, True, 1.0, "axe", 0, "planks"),
    Block(CRAFTING_TABLE, "crafting_table", "██", YELLOW, BLACK, True, 1.0, "axe", 0, "crafting_table"),
    Block(BEDROCK, "bedrock", "▓▓", WHITE, BLACK, True, math.inf, None, 0, ""),
)

BLOCKS_BY_ID: dict[int, Block] = {block.id: block for block in BLOCKS}
BLOCKS_BY_NAME: dict[str, Block] = {block.name: block for block in BLOCKS}


def block_for(block_id: int) -> Block:
    """The :class:`Block` registered under *block_id*.

    Raises :class:`KeyError` for unknown ids: tile bytes only ever come from
    this registry, so an unknown id means corrupted data, not a lookup miss.
    """
    return BLOCKS_BY_ID[block_id]
