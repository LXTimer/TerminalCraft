"""Tests for the item registry and the inventory."""

from __future__ import annotations

import pytest

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
        assert ITEMS_BY_NAME["dirt"] is ITEMS[0]

    def test_every_item_places_a_registered_block(self) -> None:
        for item in ITEMS:
            assert item.block in blocks.BLOCKS_BY_ID
            assert blocks.block_for(item.block).name == item.name

    def test_every_block_drop_is_an_item(self) -> None:
        # A block whose drop is not an item would vanish when broken.
        for block in blocks.BLOCKS:
            if block.drops:
                assert block.drops in ITEMS_BY_NAME, block.name

    def test_displays_are_not_empty(self) -> None:
        for item in ITEMS:
            assert item.display.strip()

    def test_stacks_fit_the_inventory_maximum(self) -> None:
        for item in ITEMS:
            assert 1 <= item.max_stack <= config.MAX_STACK_SIZE

    def test_unknown_name_raises(self) -> None:
        with pytest.raises(KeyError):
            item_for("diamond")


class TestAdding:
    def test_add_to_an_empty_inventory(self) -> None:
        inventory = Inventory()
        assert inventory.add("dirt", 5) == 0
        assert inventory.slot(0) is not None
        assert inventory.slot(0).item == "dirt"
        assert inventory.slot(0).count == 5

    def test_overflow_starts_a_new_slot(self) -> None:
        inventory = Inventory()
        inventory.add("dirt", 70)
        assert inventory.slot(0).count == config.MAX_STACK_SIZE
        assert inventory.slot(1).count == 70 - config.MAX_STACK_SIZE

    def test_existing_stacks_are_topped_up_first(self) -> None:
        inventory = Inventory()
        inventory.add("dirt", 10)
        inventory.add("dirt", 60)
        assert inventory.slot(0).count == config.MAX_STACK_SIZE
        assert inventory.slot(1).count == 6

    def test_different_items_get_their_own_slots(self) -> None:
        inventory = Inventory()
        inventory.add("dirt", 1)
        inventory.add("log", 1)
        assert inventory.slot(0).item == "dirt"
        assert inventory.slot(1).item == "log"

    def test_leftover_is_returned_when_the_inventory_is_full(self) -> None:
        inventory = Inventory()
        assert inventory.add("dirt", FULL) == 0
        assert inventory.add("dirt", 3) == 3

    def test_can_add_agrees_with_add(self) -> None:
        inventory = Inventory()
        inventory.add("dirt", FULL - 1)
        assert inventory.can_add("dirt", 1)
        assert not inventory.can_add("dirt", 2)
        assert inventory.add("dirt", 2) == 1

    def test_a_second_item_cannot_use_another_items_slot(self) -> None:
        inventory = Inventory()
        inventory.add("dirt", FULL)
        assert not inventory.can_add("log", 1)
        assert inventory.add("log", 1) == 1

    def test_free_space_counts_partial_stacks(self) -> None:
        inventory = Inventory()
        inventory.add("dirt", 60)
        assert inventory.free_space("dirt") == FULL - 60


class TestSelection:
    def test_starts_on_the_first_slot(self) -> None:
        assert Inventory().selected == 0

    def test_select_changes_the_slot(self) -> None:
        inventory = Inventory()
        inventory.select(4)
        assert inventory.selected == 4

    def test_select_ignores_out_of_range_indices(self) -> None:
        inventory = Inventory()
        inventory.select(config.HOTBAR_SIZE)
        assert inventory.selected == 0
        inventory.select(-1)
        assert inventory.selected == 0

    def test_hotbar_is_the_first_slots(self) -> None:
        inventory = Inventory()
        inventory.add("dirt", 1)
        hotbar = inventory.hotbar()
        assert len(hotbar) == config.HOTBAR_SIZE
        assert hotbar[0].item == "dirt"

    def test_selected_stack_follows_the_selection(self) -> None:
        inventory = Inventory()
        inventory.add("dirt", 1)
        inventory.add("log", 1)
        inventory.select(1)
        assert inventory.selected_stack().item == "log"

    def test_selected_stack_is_none_when_empty(self) -> None:
        assert Inventory().selected_stack() is None


class TestRemoving:
    def test_remove_selected_decrements_the_stack(self) -> None:
        inventory = Inventory()
        inventory.add("dirt", 2)
        assert inventory.remove_selected(1)
        assert inventory.selected_stack().count == 1

    def test_remove_selected_clears_an_exhausted_slot(self) -> None:
        inventory = Inventory()
        inventory.add("dirt", 1)
        assert inventory.remove_selected(1)
        assert inventory.selected_stack() is None

    def test_remove_selected_from_an_empty_slot_fails(self) -> None:
        assert not Inventory().remove_selected(1)

    def test_remove_selected_beyond_the_count_fails(self) -> None:
        inventory = Inventory()
        inventory.add("dirt", 1)
        assert not inventory.remove_selected(2)
        assert inventory.selected_stack().count == 1


class TestCounting:
    def test_counts_across_slots(self) -> None:
        inventory = Inventory()
        inventory.add("dirt", config.MAX_STACK_SIZE + 5)
        assert inventory.count("dirt") == config.MAX_STACK_SIZE + 5

    def test_counts_nothing_for_a_missing_item(self) -> None:
        assert Inventory().count("dirt") == 0
