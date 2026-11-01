"""The item registry.

Items are identified by name, and the inventory stores those names rather
than objects, so a save file (milestone 8) only ever holds plain strings.

Every item in this milestone is a block item: it places the block it came
from. Tools (milestone 7) are the first items that do not place anything, and
this dataclass grows a "what it does" field then.
"""

from __future__ import annotations

from dataclasses import dataclass

from .. import config
from ..world import blocks


@dataclass(frozen=True)
class Item:
    """Everything the game knows about one kind of carried thing."""

    name: str
    """Registry key, also the name blocks drop and saves store."""

    display: str
    """Name shown in the HUD."""

    block: int
    """Block id placed when this item is used."""

    max_stack: int = config.MAX_STACK_SIZE


#: The registry. Insertion order is the order the HUD and inventory list them.
ITEMS: tuple[Item, ...] = (
    Item("dirt", "Dirt", blocks.DIRT),
    Item("cobblestone", "Cobblestone", blocks.COBBLESTONE),
    Item("log", "Log", blocks.LOG),
    Item("planks", "Planks", blocks.PLANKS),
    Item("crafting_table", "Crafting Table", blocks.CRAFTING_TABLE),
)

ITEMS_BY_NAME: dict[str, Item] = {item.name: item for item in ITEMS}


def item_for(name: str) -> Item:
    """The :class:`Item` registered under *name*.

    Raises :class:`KeyError` for unknown names: item names only ever come from
    this registry or from block drops, so a miss means a broken data table
    rather than bad input.
    """
    return ITEMS_BY_NAME[name]
