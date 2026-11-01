"""The inventory: a fixed grid of stacks, the first row being the hotbar.

Slot 0 is the first hotbar slot, so "hotbar slot 3" and "inventory slot 3"
are the same slot; the HUD just draws the first
:data:`~terminalcraft.config.HOTBAR_SIZE` of them.

Adding is all-or-nothing at the call site: :meth:`Inventory.can_add` answers
"would this fit?" and only then does :meth:`Inventory.add` run, so a block is
never broken for a drop that then vanishes.
"""

from __future__ import annotations

from dataclasses import dataclass

from .. import config
from .items import item_for


@dataclass
class ItemStack:
    """A run of identical items in one slot."""

    item: str
    count: int


class Inventory:
    """36 slots, 9 of them the hotbar, plus which hotbar slot is selected."""

    def __init__(self) -> None:
        self._slots: list[ItemStack | None] = [None] * config.INVENTORY_SIZE
        self.selected = 0
        """Index of the selected hotbar slot, 0-based."""

    # -- reading -----------------------------------------------------------

    def slot(self, index: int) -> ItemStack | None:
        """The stack in *index*, or None when the slot is empty."""
        return self._slots[index]

    def hotbar(self) -> list[ItemStack | None]:
        """The first :data:`~terminalcraft.config.HOTBAR_SIZE` slots."""
        return self._slots[: config.HOTBAR_SIZE]

    def selected_stack(self) -> ItemStack | None:
        """The stack the player is holding, if any."""
        return self._slots[self.selected]

    def count(self, item: str) -> int:
        """How many of *item* the inventory holds, across all slots."""
        return sum(stack.count for stack in self._slots if stack and stack.item == item)

    # -- selection ---------------------------------------------------------

    def select(self, index: int) -> None:
        """Select hotbar slot *index*; out-of-range indices are ignored."""
        if 0 <= index < config.HOTBAR_SIZE:
            self.selected = index

    # -- writing -----------------------------------------------------------

    def free_space(self, item: str) -> int:
        """How many more of *item* would fit, counting partial stacks."""
        capacity = item_for(item).max_stack
        free = 0
        for stack in self._slots:
            if stack is None:
                free += capacity
            elif stack.item == item:
                free += capacity - stack.count
        return free

    def can_add(self, item: str, count: int = 1) -> bool:
        """True when *count* of *item* would fit completely."""
        return self.free_space(item) >= count

    def add(self, item: str, count: int) -> int:
        """Add *count* of *item*; return how many did not fit.

        Existing stacks are topped up before empty slots are used, which is
        what players expect and what keeps the hotbar tidy.
        """
        capacity = item_for(item).max_stack
        remaining = count
        for stack in self._slots:
            if remaining == 0:
                return 0
            if stack is not None and stack.item == item and stack.count < capacity:
                moved = min(capacity - stack.count, remaining)
                stack.count += moved
                remaining -= moved
        for index, stack in enumerate(self._slots):
            if remaining == 0:
                return 0
            if stack is None:
                moved = min(capacity, remaining)
                self._slots[index] = ItemStack(item, moved)
                remaining -= moved
        return remaining

    def remove_selected(self, count: int = 1) -> bool:
        """Take *count* out of the selected slot; False when it is short."""
        stack = self._slots[self.selected]
        if stack is None or stack.count < count:
            return False
        stack.count -= count
        if stack.count == 0:
            self._slots[self.selected] = None
        return True
