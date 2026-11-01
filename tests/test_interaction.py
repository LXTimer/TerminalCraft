"""Tests for reach, mining time and the placement rules."""

from __future__ import annotations

import math

import pytest
from helpers import DEFAULT_SURFACE, make_body, make_flat_world

from terminalcraft import config
from terminalcraft.entities.physics import Body
from terminalcraft.interaction import (
    BlockCursor,
    MiningState,
    break_seconds,
    in_reach,
    mine_refusal,
    place_refusal,
    tile_overlaps_body,
    touches_solid,
)
from terminalcraft.world.blocks import AIR, BEDROCK, GRASS, STONE, block_for


def body_at(x: float = 10.0) -> object:
    """A body standing on the flat test floor."""
    return make_body(x=x)


class TestBreakTime:
    def test_by_hand_is_the_hardness(self) -> None:
        assert break_seconds(block_for(GRASS)) == pytest.approx(
            block_for(GRASS).hardness
        )

    def test_a_tool_speed_divides_the_time(self) -> None:
        assert break_seconds(block_for(STONE), speed=4.0) == pytest.approx(
            block_for(STONE).hardness / 4.0
        )

    def test_air_is_never_breakable(self) -> None:
        assert math.isinf(break_seconds(block_for(AIR)))

    def test_bedrock_is_never_breakable(self) -> None:
        assert math.isinf(break_seconds(block_for(BEDROCK)))


class TestReach:
    def test_the_tile_next_to_the_body_is_in_reach(self) -> None:
        assert in_reach(body_at(), 11, DEFAULT_SURFACE - 1)

    def test_a_distant_tile_is_out_of_reach(self) -> None:
        assert not in_reach(body_at(), 10 + int(config.INTERACTION_REACH) + 1, 10)

    def test_the_boundary_counts_as_in_reach(self) -> None:
        # A body whose centre sits exactly on tile (10, 15)'s centre, so the
        # distance to the next tile's centre is exactly one tile.
        body = Body(x=10.1, y=14.6, width=0.8, height=1.8)
        assert in_reach(body, 11, 15, reach=1.0)
        assert in_reach(body, 12, 15, reach=2.0)

    def test_just_beyond_the_boundary_is_out(self) -> None:
        body = Body(x=10.1, y=14.6, width=0.8, height=1.8)
        assert not in_reach(body, 12, 15, reach=1.99)


class TestBodyOverlap:
    def test_the_tile_the_body_stands_in_overlaps(self) -> None:
        body = body_at()
        assert tile_overlaps_body(body, 10, DEFAULT_SURFACE - 1)

    def test_the_tile_below_the_feet_does_not_overlap(self) -> None:
        body = body_at()
        assert not tile_overlaps_body(body, 10, DEFAULT_SURFACE)

    def test_a_tile_beside_the_body_does_not_overlap(self) -> None:
        body = body_at()
        assert not tile_overlaps_body(body, 11, DEFAULT_SURFACE - 1)


class TestTouchesSolid:
    def test_a_tile_above_the_ground_touches_it(self) -> None:
        world = make_flat_world()
        assert touches_solid(world, 5, DEFAULT_SURFACE - 1)

    def test_a_tile_in_mid_air_touches_nothing(self) -> None:
        world = make_flat_world()
        assert not touches_solid(world, 5, 2)


class TestMineRefusal:
    def test_the_ground_under_the_feet_is_mineable(self) -> None:
        world = make_flat_world()
        assert mine_refusal(world, body_at(), 10, DEFAULT_SURFACE) is None

    def test_air_has_nothing_to_break(self) -> None:
        world = make_flat_world()
        assert mine_refusal(world, body_at(), 10, DEFAULT_SURFACE - 3) == (
            "nothing to break there"
        )

    def test_bedrock_has_nothing_to_break(self) -> None:
        world = make_flat_world()
        world.set(10, DEFAULT_SURFACE, BEDROCK)
        assert mine_refusal(world, body_at(), 10, DEFAULT_SURFACE) == (
            "nothing to break there"
        )

    def test_reach_is_reported_before_anything_else(self) -> None:
        world = make_flat_world()
        far = 10 + int(config.INTERACTION_REACH) + 1
        assert mine_refusal(world, body_at(), far, DEFAULT_SURFACE) == "out of reach"


class TestPlaceRefusal:
    def test_a_supported_air_tile_is_placeable(self) -> None:
        world = make_flat_world()
        assert place_refusal(world, body_at(), 5, DEFAULT_SURFACE - 1) is None

    def test_a_filled_tile_is_occupied(self) -> None:
        world = make_flat_world()
        assert place_refusal(world, body_at(), 5, DEFAULT_SURFACE) == (
            "that tile is occupied"
        )

    def test_unsupported_air_needs_a_neighbour(self) -> None:
        world = make_flat_world()
        assert place_refusal(world, body_at(), 11, DEFAULT_SURFACE - 4) == (
            "needs a block to attach to"
        )

    def test_the_player_blocks_its_own_tile(self) -> None:
        world = make_flat_world()
        assert place_refusal(world, body_at(), 10, DEFAULT_SURFACE - 1) == (
            "you are standing there"
        )

    def test_out_of_reach_is_reported(self) -> None:
        world = make_flat_world()
        far = 10 + int(config.INTERACTION_REACH) + 1
        assert place_refusal(world, body_at(), far, DEFAULT_SURFACE - 1) == "out of reach"

    def test_outside_the_world_is_reported(self) -> None:
        world = make_flat_world(width=20)
        assert place_refusal(world, body_at(), 20, DEFAULT_SURFACE - 1) == "out of bounds"
        assert place_refusal(world, body_at(), -1, DEFAULT_SURFACE - 1) == "out of bounds"


class TestMiningState:
    def test_starts_inactive(self) -> None:
        assert not MiningState().active

    def test_progress_accumulates_below_the_threshold(self) -> None:
        state = MiningState()
        assert not state.advance((1, 2), 0.4, 1.0)
        assert state.progress == pytest.approx(0.4)
        assert state.active

    def test_completes_at_the_threshold(self) -> None:
        state = MiningState()
        state.advance((1, 2), 0.4, 1.0)
        assert state.advance((1, 2), 0.6, 1.0)

    def test_another_tile_starts_over(self) -> None:
        state = MiningState()
        state.advance((1, 2), 0.9, 1.0)
        assert not state.advance((2, 2), 0.2, 1.0)
        assert state.progress == pytest.approx(0.2)

    def test_reset_clears_everything(self) -> None:
        state = MiningState()
        state.advance((1, 2), 0.9, 1.0)
        state.reset()
        assert not state.active
        assert state.progress == 0.0


class TestBlockCursor:
    def test_moves_in_tile_steps(self) -> None:
        world = make_flat_world()
        cursor = BlockCursor(5, 5)
        cursor.move(1, -1, world)
        assert cursor.tile == (6, 4)

    def test_stays_inside_the_world(self) -> None:
        world = make_flat_world(width=10, height=8)
        cursor = BlockCursor(0, 0)
        cursor.move(-5, -5, world)
        assert cursor.tile == (0, 0)
        cursor.move(100, 100, world)
        assert cursor.tile == (9, 7)
