"""Tests for the player: spawn placement, walking, jumping."""

from __future__ import annotations

import pytest
from helpers import DEFAULT_SURFACE, make_flat_world

from terminalcraft import config
from terminalcraft.entities.physics import overlaps_solid
from terminalcraft.entities.player import Player
from terminalcraft.world.blocks import STONE
from terminalcraft.world.world import World

DT = config.TICK_SECONDS
JUMP_RISE = 1.2
"""Tiles a jump gains with this integrator: the launch speed loses one
gravity step before the first move, so the sum is (8+7+...+1)/30."""


def spawn(column: int = 10) -> tuple[World, Player]:
    world = make_flat_world()
    return world, Player.spawn(world, column)


class TestSpawn:
    def test_feet_rest_on_the_surface(self) -> None:
        _, player = spawn()
        assert player.body.bottom == pytest.approx(DEFAULT_SURFACE)

    def test_centred_on_the_column(self) -> None:
        _, player = spawn(column=10)
        assert player.body.center_x == pytest.approx(10.5)

    def test_is_player_sized(self) -> None:
        _, player = spawn()
        assert player.body.width == config.PLAYER_WIDTH
        assert player.body.height == config.PLAYER_HEIGHT

    def test_knows_it_is_standing_so_the_first_jump_works(self) -> None:
        _, player = spawn()
        assert player.body.on_ground

    def test_does_not_start_inside_a_block(self) -> None:
        world, player = spawn()
        body = player.body
        assert not overlaps_solid(world, body.x, body.y, body.width, body.height)

    def test_faces_right_by_default(self) -> None:
        _, player = spawn()
        assert player.facing == 1


class TestWalking:
    def test_moves_right_at_walk_speed(self) -> None:
        world, player = spawn()
        start = player.body.x
        player.update(world, dt=DT, move_dir=1, jump=False)
        assert player.body.x == pytest.approx(start + config.WALK_SPEED * DT)

    def test_moves_left_at_walk_speed(self) -> None:
        world, player = spawn()
        start = player.body.x
        player.update(world, dt=DT, move_dir=-1, jump=False)
        assert player.body.x == pytest.approx(start - config.WALK_SPEED * DT)

    def test_facing_follows_the_direction(self) -> None:
        world, player = spawn()
        player.update(world, dt=DT, move_dir=-1, jump=False)
        assert player.facing == -1
        player.update(world, dt=DT, move_dir=1, jump=False)
        assert player.facing == 1

    def test_standing_still_reports_no_velocity(self) -> None:
        world, player = spawn()
        player.update(world, dt=DT, move_dir=0, jump=False)
        assert player.body.vx == 0.0

    def test_walking_does_not_sink_into_the_floor(self) -> None:
        world, player = spawn()
        for _ in range(20):
            player.update(world, dt=DT, move_dir=1, jump=False)
        assert player.body.bottom == pytest.approx(DEFAULT_SURFACE)


class TestJumping:
    def test_jump_leaves_the_ground(self) -> None:
        world, player = spawn()
        start = player.body.y
        player.update(world, dt=DT, move_dir=0, jump=True)
        assert player.body.y < start
        assert not player.body.on_ground

    def test_jump_rises_about_one_point_two_tiles(self) -> None:
        world, player = spawn()
        start = player.body.y
        player.update(world, dt=DT, move_dir=0, jump=True)
        highest = player.body.y
        for _ in range(20):
            player.update(world, dt=DT, move_dir=0, jump=False)
            highest = min(highest, player.body.y)
        assert start - highest == pytest.approx(JUMP_RISE, abs=0.05)

    def test_lands_again_on_the_same_spot(self) -> None:
        world, player = spawn()
        for _ in range(40):
            player.update(world, dt=DT, move_dir=0, jump=False)
            if player.body.on_ground:
                break
        assert player.body.on_ground
        assert player.body.bottom == pytest.approx(DEFAULT_SURFACE)

    def test_cannot_jump_again_while_airborne(self) -> None:
        world, player = spawn()
        player.update(world, dt=DT, move_dir=0, jump=True)
        rising = player.body.vy
        player.update(world, dt=DT, move_dir=0, jump=True)
        # Only gravity changed the speed; a second launch would be -9 again.
        assert player.body.vy == pytest.approx(rising + config.GRAVITY * DT)

    def test_a_jump_does_not_also_climb_a_ledge(self) -> None:
        # The jump tick must not be both airborne and grounded, or the player
        # would clear a ledge it should have hit.
        world = make_flat_world()
        world.fill_rect(11, DEFAULT_SURFACE - 1, 12, DEFAULT_SURFACE - 1, STONE)
        player = Player.spawn(world, 10)
        player.update(world, dt=DT, move_dir=1, jump=True)
        assert player.body.bottom > DEFAULT_SURFACE - 1
