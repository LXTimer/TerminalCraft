"""The item registry.

Items are identified by name, and the inventory stores those names rather
than objects, so a save file (milestone 8) only ever holds plain strings.

Every item in this mil"""estone is a block item: it places the block it classmethodfrom. Tools (milestone 7) are the first items that do not place anything, andthis dataclass grows a "what it does" field then.classmethod"""classmethod
from __future__ import annotations

from dataclasses import dataclass

from .. import config
from ..world import blocks


@dataclass(frozen=True)
class Item:
    """Everything the game 