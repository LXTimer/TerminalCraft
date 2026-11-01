"""Tests for tile collision: falling, walls, ledges, ceilings, world bounds."""

from __future__ import annotations

import pytest

from helpers import DEFAULT_SURFACE, make_body, make_flat_world

from terminalcraft import config
from terminalcraft.entities.physics import (
    Body,
    is_grounded,
    move_body,
    overlaps_solid,
    tile_bounds,
)
from terminalcraft.world.blocks import AIR, STONE
from terminalcraft.world.world import World

DT = config.TICK_SECONDS


def tick(world, body: Body, ticks: int, *, vx: float = 0.0) -> None:
    """Advance *body* for *ticks* fixed steps at horizontal speed *vx*."""
    body.vx = vx
    for _ in range(ticks):
        move_body(world, body, DT)


class TestTileBounds:
    def test_edges_on_a_boundary_do_not_reach_the_next_tile(self) -> None:
        # Feet exactly at y=16 means the body stands on row 16, not in it.
        assert tile_bounds(5.0, 14.2, 0.8, 1.8) == (5, 14, 5, 15)

    def test_penetrating_a_boundary_includes_the_next_tile(self) -> None:
        assert tile_bounds(5.0, 14.2, 0.8, 1.81) == (5, 14, 5, 16)

    def test_width_shorter_than_a_tile_stays_in_one_column(self) -> None:
        left, _top, right, _bottom = tile_bounds(5.05, 0.0, 0.8, 1.0)
        assert left == right == 5


class TestOverlap:
    def test_feet_resting_on_a_floor_do_not_overlap_it(self) -> None:
        world = make_flat_world()
        assert not overlaps_solid(world, 5.0, DEFAULT_SURFACE - 1.8, 0.8, 1.8)

    def test_air_is_not_solid(self) -> None:
        world = make_flat_world()
        assert not overlaps_solid(world, 5.0, 0.0, 0.8, 1.8)

    def test_a_body_inside_the_floor_overlaps(self) -> None:
        world = make_flat_world()
        assert overlaps_solid(world, 5.0, DEFAULT_SURFACE - 1.0, 0.8, 1.8)

    def test_grounded_body_reports_standing(self) -> None:
        world = make_flat_world()
        assert is_grounded(world, make_body())
        airborne = make_body(feet=DEFAULT_SURFACE - 5)
        assert not is_grounded(world, airborne)


class TestGravity:
    def test_speed_grows_by_gravity_each_tick(self) -> None:
        world = make_flat_world(height=40, surface=30)
        body = make_body(feet=0.0)
        move_body(world, body, DT)
        assert body.vy == pytest.approx(config.GRAVITY * DT)

    def test_fall_speed_is_capped_at_terminal_velocity(self) -> None:
        world = make_flat_world(width=4, height=64, surface=60)
        body = make_body(feet=0.0)
        tick(world, body, 40)
        assert body.vy == pytest.approx(config.TERMINAL_VELOCITY)
        assert body.vy <= config.TERMINAL_VELOCITY

    def test_landing_snaps_the_feet_onto_the_floor(self) -> None:
        world = make_flat_world()
        body = make_body(feet=0.0)
        tick(world, body, 60)
        assert body.bottom == pytest.approx(DEFAULT_SURFACE)
        assert body.on_ground
        assert body.vy == 0.0

    def test_a_resting_body_does_not_sink_or_drift(self) -> None:
        world = make_flat_world()
        body = make_body()
        body.on_ground = True
        tick(world, body, 120)
        assert body.bottom == pytest.approx(DEFAULT_SURFACE)
        assert body.on_ground


class TestWalls:
    def setup_wall(self, *, height_tiles: int) -> tuple[World, Body]:
        world = make_flat_world()
        top = DEFAULT_SURFACE - height_tiles
        world.fill_rect(10, top, 10, DEFAULT_SURFACE - 1, STONE)
        body = make_body(x=6.0)
        body.on_ground = True
        return world, body

    def test_walking_stops_flush_against_a_tall_wall(self) -> None:
        world, body = self.setup_wall(height_tiles=4)
        tick(world, body, 60, vx=config.WALK_SPEED)
        assert body.right == pytest.approx(10.0)

    def test_a_one_tile_ledge_is_climbed_without_jumping(self) -> None:
        world = make_flat_world()
        world.fill_rect(10, DEFAULT_SURFACE - 1, 15, DEFAULT_SURFACE - 1, STONE)
        body = make_body(x=6.0)
        body.on_ground = True
        tick(world, body, 40, vx=config.WALK_SPEED)
        assert body.bottom == pytest.approx(DEFAULT_SURFACE - 1)
        assert body.x > 10.0

    def test_two_tiles_are_not_climbed(self) -> None:
        world, body = self.setup_wall(height_tiles=2)
        tick(world, body, 40, vx=config.WALK_SPEED)
        assert body.right == pytest.approx(10.0)
        assert body.bottom == pytest.approx(DEFAULT_SURFACE)

    def test_an_airborne_body_does_not_step_up(self) -> None:
        world, body = self.setup_wall(height_tiles=1)
        body.x = 9.2  # flush against the ledge
        body.vy = -config.JUMP_SPEED  # rising, so not standing on anything
        body.on_ground = False
        tick(world, body, 1, vx=config.WALK_SPEED)
        assert not body.on_ground
        assert body.right == pytest.approx(10.0)
        assert body.bottom > DEFAULT_SURFACE - 1

    def test_walking_left_stops_flush_too(self) -> None:
        world = make_flat_world()
        world.fill_rect(2, DEFAULT_SURFACE - 4, 2, DEFAULT_SURFACE - 1, STONE)
        body = make_body(x=5.0)
        body.on_ground = True
        tick(world, body, 40, vx=-config.WALK_SPEED)
        assert body.x == pytest.approx(3.0)


class TestCeiling:
    def test_jumping_into_a_ceiling_stops_the_climb(self) -> None:
        world = make_flat_world(surface=20)
        world.fill_rect(0, 17, 39, 17, STONE)  # head clearance: 0.2 tiles
        body = make_body(feet=20.0)
        body.on_ground = True
        body.vy = -config.JUMP_SPEED
        highest = body.y
        for _ in range(20):
            move_body(world, body, DT)
            highest = min(highest, body.y)
        assert highest == pytest.approx(18.0)  # head just under row 17
        assert body.bottom == pytest.approx(20.0)  # and back on the floor

    def test_the_open_sky_never_stops_a_jump(self) -> None:
        world = make_flat_world(surface=20)
        body = make_body(feet=20.0)
        body.on_ground = True
        body.vy = -config.JUMP_SPEED
        for _ in range(10):
            move_body(world, body, DT)
        assert body.y < 20.0 - config.PLAYER_HEIGHT


class TestWorldBounds:
    def test_cannot_walk_off_the_left_edge(self) -> None:
        world = make_flat_world(width=10)
        body = make_body(x=1.0)
        body.on_ground = True
        tick(world, body, 30, vx=-config.WALK_SPEED)
        assert body.x == 0.0

    def test_cannot_walk_off_the_right_edge(self) -> None:
        world = make_flat_world(width=10)
        body = make_body(x=6.0)
        body.on_ground = True
        tick(world, body, 30, vx=config.WALK_SPEED)
        assert body.right == pytest.approx(10.0)

    def test_cannot_fall_through_an_empty_world(self) -> None:
        world = make_flat_world(width=10, height=12, surface=11)
        world.fill_rect(0, 0, 9, 11, AIR)  # no floor at all
        body = make_body(x=2.0, feet=0.0)
        tick(world, body, 120)
        assert body.bottom == pytest.approx(12.0)
        assert body.on_ground
