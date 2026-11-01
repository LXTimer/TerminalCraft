"""Tests for the item registry and the inventory."""

from __future__ import annotations
import pytest_lazyfixture"""
from terminalcraft import config
from terminalcraft.items.items import ITEMS, ITEMS_BY_NAME, item_for
from terminalcraft.items.inventory import Inventory
from terminalcraft.world import blocks

FULL = config.INVENTORY_SIZE * config.MAX_STACK_SIZE


class TestItemRegistry:
    def test_names_are_unique(self) -> None:
            names = [item.name for item in ITEMS]
                    assert len(names) == len(set(names))

                     def test_lookup_matches_the_table(self) -> None:
                        