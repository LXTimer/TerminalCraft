"""Tests for the tile grid."""

import pytest

from terminalcraft.world.blocks import AIR, GRASS, STONE
from terminalcraft.world.world import World


class TestIndexing:
    def test_index_matches_row_major_layout(self) -> None:
        world = World(4, 3)
        assert world.index(0, 0) == 0
        assert world.index(3, 0) == 3
        assert world.index(0, 1) == 4
        assert world.index(3, 2) == 11

    def test_get_set_round_trip(self) -> None:
        world = World(4, 3)
        world.set(2, 1, GRASS)
        assert world.get(2, 1) == GRASS
        assert world.get(1, 1) == AIR

    def test_set_rejects_unknown_block_ids(self) -> None:
        world = World(4, 3)
        with pytest.raises(ValueError):
            world.set(0, 0, 200)

    def test_constructor_rejects_unknown_fill(self) -> None:
        with pytest.raises(ValueError):
            World(4, 3, fill=200)

    def test_constructor_rejects_degenerate_sizes(self) -> None:
        with pytest.raises(ValueError):
            World(0, 3)
        with pytest.raises(ValueError):
            World(4, -1)


class TestBounds:
    def test_in_bounds_edges(self) -> None:
        world = World(4, 3)
        assert world.in_bounds(0, 0)
        assert world.in_bounds(3, 2)
        assert not world.in_bounds(-1, 0)
        assert not world.in_bounds(4, 0)
        assert not world.in_bounds(0, 3)
        assert not world.in_bounds(0, -1)

    def test_out_of_bounds_reads_are_air(self) -> None:
        world = World(4, 3)
        assert world.get(-1, 0) == AIR
        assert world.get(4, 2) == AIR
        assert world.get(0, 3) == AIR

    def test_out_of_bounds_writes_are_ignored(self) -> None:
        world = World(4, 3)
        world.set(-1, 0, GRASS)
        world.set(4, 2, GRASS)
        assert world.get(-1, 0) == AIR
        assert len(world.tile_bytes()) == 12


class TestBulkOperations:
    def test_fill_rect_covers_inclusive_bounds(self) -> None:
        world = World(5, 5)
        world.fill_rect(1, 1, 3, 2, STONE)
        assert world.get(1, 1) == STONE
        assert world.get(3, 2) == STONE
        assert world.get(0, 1) == AIR
        assert world.get(4, 2) == AIR
        assert world.get(2, 3) == AIR

    def test_fill_rect_clips_to_the_grid(self) -> None:
        world = World(5, 5)
        world.fill_rect(-2, -2, 99, 99, STONE)
        assert world.tile_bytes() == bytes([STONE]) * 25

    def test_surface_y_finds_topmost_solid(self) -> None:
        world = World(3, 6)
        world.set(1, 4, GRASS)
        assert world.surface_y(1) == 4
        assert world.surface_y(0) == 6  # empty column
        assert world.surface_y(-1) == 6  # out of bounds

    def test_tile_bytes_is_row_major(self) -> None:
        world = World(2, 2)
        world.set(1, 0, GRASS)
        world.set(0, 1, STONE)
        assert world.tile_bytes() == bytes([AIR, GRASS, STONE, AIR])
