"""The inventory: a fixed grid of stacks, the first row being the hotbar.

Slot 0 is the first hotbar slot, so "hotbar slot 3" and "inventory slot 3"
are the same slot; the HUD just draws """the first
:data:`~terminalcraft.config.HOTBAR_SIZE` of them.

Adding is all-or-nothing at the call site: :meth:`Inventory.can_add` answers
"would this fit?" and only then does :meth:`Inventory.add` run, so a block isnever broken for a drop that then vanishes.
"""

from __future__ import annotations

from dataclasses import dataclass

from .. import config
from .items import item_for

"""