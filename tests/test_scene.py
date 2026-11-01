"""Tests for the playing scene: input dispatch, mining, placing, camera.

These drive the scene directly with a fake clock, so "held" and "pressed"
are exact rather than dependent on how fast the test machine polls.
"""

from __future__ import annotations

import pytest
from helpers import DEFAULT_SURFACE, FakeClock, make_flat_world

from terminalcraft import config
from terminalcraft.entities.player import Player
from terminalcraft.game import Game, PlayingScene
from terminalcraft.input import Action, InputHandler, MouseButton, MouseEvent
from terminalcraft.interaction import BlockCursor
from terminalcraft.items.inventory import Inventory
from terminalcraft.render.headless import HeadlessScreen
from terminalcraft.render.renderer import Renderer
from terminalcraft.world.blocks import AIR, DIRT, GRASS
from terminalcraft.world.world import World

DT = config.TICK_SECONDS
TICKS_TO_BREAK_GRASS = 20
"""Grass takes 0.6 s; 18 ticks is the exact count, 20 leaves headroom for
floating-point accumulation."""


def build(column: int = 10) -> tuple[PlayingScene, InputHandler, FakeClock, Renderer, HeadlessScreen]:
    """A scene on a flat world with a full-ish dirt stack."""
    clock = FakeClock()
    screen = HeadlessScreen(80, 24)
    renderer = Renderer(screen, colours=False)
    handler = InputHandler(clock=clock)
    game = Game(renderer, handler)
    world = make_flat_world()
    player = Player.spawn(world, column)
    inventory = Inventory()
    inventory.add("dirt", 8)
    # Mirror the production bootstrap so camera-follow tests start centred.
    renderer.camera.x = player.body.center_x
    renderer.camera.y = player.body.center_y
    scene = PlayingScene(
        game,
        handler,
        world,
        renderer,
        player,
        inventory,
        BlockCursor(*player.tile),
    )
    return scene, handler, clock, renderer, screen


def aim(scene: PlayingScene, x: int, y: int) -> None:
    """Point the block cursor at a tile."""
    scene.cursor.x = x
    scene.cursor.y = y


def run(scene: PlayingScene, ticks: int) -> None:
    """Advance the scene without touching the clock: keys stay held."""
    for _ in range(ticks):
        scene.update(DT)


class TestActionDispatch:
    def test_hotbar_digits_select_slots(self) -> None:
        scene, _, _, _, _ = build()
        assert scene.handle_action(Action.HOTBAR_3)
        assert scene.inventory.selected == 2

    def test_cursor_keys_step_the_cursor(self) -> None:
        scene, _, _, _, _ = build()
        x, y = scene.cursor.tile
        assert scene.handle_action(Action.CURSOR_RIGHT)
        assert scene.cursor.tile == (x + 1, y)
        assert scene.handle_action(Action.CURSOR_DOWN)
        assert scene.cursor.tile == (x + 1, y + 1)

    def test_gameplay_actions_are_claimed(self) -> None:
        scene, _, _, _, _ = build()
        for action in (Action.MOVE_LEFT, Action.JUMP, Action.MINE, Action.PLACE):
            assert scene.handle_action(action), action

    def test_unhandled_actions_fall_through(self) -> None:
        scene, _, _, _, _ = build()
        assert not scene.handle_action(Action.QUIT)
        assert not scene.handle_action(Action.INVENTORY)


class TestWalking:
    def test_held_key_walks(self) -> None:
        scene, handler, _, _, _ = build()
        start = scene.player.body.x
        handler.dispatch(ord("d"))
        run(scene, 5)
        assert scene.player.body.x == pytest.approx(start + 5 * config.WALK_SPEED * DT)

    def test_walking_stops_when_the_key_window_expires(self) -> None:
        scene, handler, clock, _, _ = build()
        handler.dispatch(ord("d"))
        run(scene, 3)
        clock.advance(config.HOLD_WINDOW_SECONDS + 0.01)
        stopped_at = scene.player.body.x
        run(scene, 5)
        assert scene.player.body.x == pytest.approx(stopped_at)

    def test_both_directions_cancel_out(self) -> None:
        scene, handler, _, _, _ = build()
        start = scene.player.body.x
        handler.dispatch(ord("a"))
        handler.dispatch(ord("d"))
        run(scene, 4)
        assert scene.player.body.x == pytest.approx(start)


class TestJumping:
    def test_a_press_jumps(self) -> None:
        scene, handler, _, _, _ = build()
        handler.dispatch(ord("w"))
        scene.update(DT)
        assert not scene.player.body.on_ground

    def test_holding_the_key_does_not_bunny_hop(self) -> None:
        scene, handler, _, _, _ = build()
        handler.dispatch(ord("w"))
        run(scene, 40)  # clock frozen: the key is still "down"
        assert scene.player.body.on_ground


class TestMining:
    def test_holding_mine_breaks_the_block_and_collects_it(self) -> None:
        scene, handler, _, _, _ = build()
        aim(scene, 11, DEFAULT_SURFACE)
        handler.dispatch(ord("j"))
        run(scene, TICKS_TO_BREAK_GRASS)
        assert scene.world.get(11, DEFAULT_SURFACE) == AIR
        assert scene.inventory.count("dirt") == 9

    def test_progress_shows_before_the_block_breaks(self) -> None:
        scene, handler, _, _, _ = build()
        aim(scene, 11, DEFAULT_SURFACE)
        handler.dispatch(ord("j"))
        run(scene, 4)
        assert scene.mining.active
        assert scene.world.get(11, DEFAULT_SURFACE) == GRASS

    def test_releasing_the_key_starts_over(self) -> None:
        scene, handler, clock, _, _ = build()
        aim(scene, 11, DEFAULT_SURFACE)
        handler.dispatch(ord("j"))
        run(scene, 6)
        clock.advance(config.HOLD_WINDOW_SECONDS + 0.01)
        scene.update(DT)
        assert not scene.mining.active
        run(scene, TICKS_TO_BREAK_GRASS)
        assert scene.world.get(11, DEFAULT_SURFACE) == GRASS

    def test_moving_the_cursor_starts_over(self) -> None:
        scene, handler, _, _, _ = build()
        aim(scene, 11, DEFAULT_SURFACE)
        handler.dispatch(ord("j"))
        run(scene, 6)
        scene.handle_action(Action.CURSOR_RIGHT)
        scene.update(DT)
        assert scene.mining.progress == pytest.approx(DT)

    def test_air_is_not_mined(self) -> None:
        scene, handler, _, _, _ = build()
        aim(scene, 11, DEFAULT_SURFACE - 3)
        handler.dispatch(ord("j"))
        run(scene, 30)
        assert not scene.mining.active

    def test_a_full_inventory_blocks_breaking(self) -> None:
        scene, handler, _, _, _ = build()
        scene.inventory.add("dirt", config.INVENTORY_SIZE * config.MAX_STACK_SIZE)
        aim(scene, 11, DEFAULT_SURFACE)
        handler.dispatch(ord("j"))
        run(scene, 40)
        assert scene.world.get(11, DEFAULT_SURFACE) == GRASS
        assert not scene.mining.active

    def test_out_of_reach_blocks_mining(self) -> None:
        scene, handler, _, _, _ = build()
        aim(scene, 11, DEFAULT_SURFACE - 8)
        handler.dispatch(ord("j"))
        run(scene, 40)
        assert not scene.mining.active


class TestPlacing:
    def test_place_puts_the_selected_block_down(self) -> None:
        scene, handler, _, _, _ = build()
        aim(scene, 11, DEFAULT_SURFACE - 1)
        handler.dispatch(ord("k"))
        scene.update(DT)
        assert scene.world.get(11, DEFAULT_SURFACE - 1) == DIRT
        assert scene.inventory.count("dirt") == 7

    def test_one_placement_per_press(self) -> None:
        scene, handler, _, _, _ = build()
        aim(scene, 11, DEFAULT_SURFACE - 1)
        handler.dispatch(ord("k"))
        handler.dispatch(ord("k"))
        scene.update(DT)
        scene.update(DT)
        assert scene.inventory.count("dirt") == 7

    def test_cannot_place_on_a_filled_tile(self) -> None:
        scene, handler, _, _, _ = build()
        aim(scene, 11, DEFAULT_SURFACE)
        handler.dispatch(ord("k"))
        scene.update(DT)
        assert scene.world.get(11, DEFAULT_SURFACE) == GRASS
        assert scene.inventory.count("dirt") == 8

    def test_cannot_place_inside_the_player(self) -> None:
        scene, handler, _, _, _ = build()
        aim(scene, *scene.player.tile)
        handler.dispatch(ord("k"))
        scene.update(DT)
        assert scene.world.get(*scene.cursor.tile) == AIR
        assert scene.inventory.count("dirt") == 8

    def test_cannot_place_out_of_reach(self) -> None:
        scene, handler, _, _, _ = build()
        aim(scene, 11, DEFAULT_SURFACE - 10)
        handler.dispatch(ord("k"))
        scene.update(DT)
        assert scene.world.get(11, DEFAULT_SURFACE - 10) == AIR

    def test_empty_hand_places_nothing(self) -> None:
        scene, handler, _, _, _ = build()
        scene.inventory.select(5)  # empty slot
        aim(scene, 11, DEFAULT_SURFACE - 1)
        handler.dispatch(ord("k"))
        scene.update(DT)
        assert scene.world.get(11, DEFAULT_SURFACE - 1) == AIR

    def test_placing_the_last_block_empties_the_slot(self) -> None:
        scene, handler, _, _, _ = build()
        while scene.inventory.count("dirt") > 1:
            scene.inventory.remove_selected(1)
        aim(scene, 11, DEFAULT_SURFACE - 1)
        handler.dispatch(ord("k"))
        scene.update(DT)
        assert scene.inventory.selected_stack() is None


class TestCameraFollow:
    def test_camera_tracks_the_player_horizontally(self) -> None:
        scene, handler, _, renderer, _ = build()
        handler.dispatch(ord("d"))
        run(scene, 10)
        assert renderer.camera.x == pytest.approx(scene.player.body.center_x)

    def test_a_jump_does_not_move_the_camera(self) -> None:
        scene, handler, _, renderer, _ = build()
        start = renderer.camera.y
        handler.dispatch(ord("w"))
        run(scene, 10)
        assert renderer.camera.y == pytest.approx(start)

    def test_a_long_fall_moves_the_camera(self) -> None:
        scene, _, _, renderer, _ = build()
        world = scene.world
        # Dig out six rows under the player so it falls past the dead zone.
        world.fill_rect(0, DEFAULT_SURFACE, world.width - 1, DEFAULT_SURFACE + 5, AIR)
        start = renderer.camera.y
        run(scene, 40)
        assert renderer.camera.y > start


class TestMouseAiming:
    """A click aims the cursor at the tile it landed on, then mines or places.

    The button is an extra binding for the same action, so the scene has no
    separate mouse mode - it only has to know *where* the click landed.
    """

    @staticmethod
    def cell(scene: PlayingScene, renderer: Renderer, x: int, y: int) -> tuple[int, int]:
        """Screen (row, column) of a world tile, as a mouse event would report it."""
        pos = renderer.tile_screen_pos(scene.world, x, y)
        assert pos is not None, f"tile {(x, y)} is off-screen"
        return pos

    def test_a_left_click_aims_and_mines(self) -> None:
        scene, handler, _, renderer, _ = build()
        row, column = self.cell(scene, renderer, 11, DEFAULT_SURFACE)
        handler.dispatch_mouse(MouseEvent(column, row, MouseButton.LEFT, True))
        run(scene, TICKS_TO_BREAK_GRASS)
        assert scene.cursor.tile == (11, DEFAULT_SURFACE)
        assert scene.world.get(11, DEFAULT_SURFACE) == AIR
        assert scene.inventory.count("dirt") == 9

    def test_a_right_click_places(self) -> None:
        scene, handler, _, renderer, _ = build()
        row, column = self.cell(scene, renderer, 11, DEFAULT_SURFACE - 1)
        handler.dispatch_mouse(MouseEvent(column, row, MouseButton.RIGHT, True))
        scene.update(DT)
        assert scene.world.get(11, DEFAULT_SURFACE - 1) == DIRT
        assert scene.inventory.count("dirt") == 7

    def test_releasing_the_button_stops_mining(self) -> None:
        scene, handler, _, renderer, _ = build()
        row, column = self.cell(scene, renderer, 11, DEFAULT_SURFACE)
        handler.dispatch_mouse(MouseEvent(column, row, MouseButton.LEFT, True))
        run(scene, 4)
        assert scene.mining.active
        handler.dispatch_mouse(MouseEvent(column, row, MouseButton.LEFT, False))
        scene.update(DT)
        assert not scene.mining.active
        assert scene.world.get(11, DEFAULT_SURFACE) == GRASS

    def test_a_click_on_the_hotbar_leaves_the_cursor_alone(self) -> None:
        scene, handler, _, renderer, _ = build()
        before = scene.cursor.tile
        _, height = renderer.size
        handler.dispatch_mouse(MouseEvent(0, height - 1, MouseButton.LEFT, True))
        scene.update(DT)
        assert scene.cursor.tile == before

    def test_a_right_click_on_the_hotbar_places_nothing(self) -> None:
        # The button was already dispatched by the time the scene sees the
        # cell, so the scene has to cancel the action it cannot use.
        scene, handler, _, renderer, _ = build()
        aim(scene, 11, DEFAULT_SURFACE - 1)
        _, height = renderer.size
        handler.dispatch_mouse(MouseEvent(0, height - 1, MouseButton.RIGHT, True))
        scene.update(DT)
        assert scene.world.get(11, DEFAULT_SURFACE - 1) == AIR
        assert scene.inventory.count("dirt") == 8

    def test_a_left_click_on_the_hotbar_does_not_start_mining(self) -> None:
        scene, handler, _, renderer, _ = build()
        aim(scene, 11, DEFAULT_SURFACE)
        _, height = renderer.size
        handler.dispatch_mouse(MouseEvent(0, height - 1, MouseButton.LEFT, True))
        run(scene, 4)
        assert not scene.mining.active
        assert not handler.is_held(Action.MINE)

    def test_a_click_out_of_reach_aims_but_does_not_mine(self) -> None:
        scene, handler, _, renderer, _ = build()
        target = (20, DEFAULT_SURFACE)
        row, column = self.cell(scene, renderer, *target)
        handler.dispatch_mouse(MouseEvent(column, row, MouseButton.LEFT, True))
        run(scene, 30)
        assert scene.cursor.tile == target
        assert scene.world.get(*target) == GRASS
        assert not scene.mining.active

    def test_the_keyboard_still_mines_after_a_click(self) -> None:
        scene, handler, _, renderer, _ = build()
        row, column = self.cell(scene, renderer, 20, DEFAULT_SURFACE)
        handler.dispatch_mouse(MouseEvent(column, row, MouseButton.LEFT, True))
        run(scene, 2)
        handler.dispatch_mouse(MouseEvent(column, row, MouseButton.LEFT, False))
        aim(scene, 11, DEFAULT_SURFACE)
        handler.dispatch(ord("j"))
        run(scene, TICKS_TO_BREAK_GRASS)
        assert scene.world.get(11, DEFAULT_SURFACE) == AIR


class TestCursorFollow:
    """The cursor is an aim offset from the player, not a free pointer."""

    def test_the_cursor_walks_with_the_player(self) -> None:
        scene, handler, _, _, _ = build()
        aim(scene, *scene.player.tile)
        handler.dispatch(ord("d"))
        run(scene, 10)
        assert scene.cursor.tile == scene.player.tile

    def test_the_aim_offset_survives_walking(self) -> None:
        scene, handler, _, _, _ = build()
        x, y = scene.player.tile
        aim(scene, x + 2, y)
        handler.dispatch(ord("d"))
        run(scene, 10)
        x, y = scene.player.tile
        assert scene.cursor.tile == (x + 2, y)


class TestRefusalFeedback:
    """A refused action says why instead of doing nothing in silence."""

    def test_out_of_reach_is_reported(self) -> None:
        scene, handler, _, _, _ = build()
        aim(scene, 11, DEFAULT_SURFACE - 8)
        handler.dispatch(ord("j"))
        scene.update(DT)
        assert scene.notice == "out of reach"
        assert not scene.mining.active

    def test_a_full_inventory_is_reported(self) -> None:
        scene, handler, _, _, _ = build()
        scene.inventory.add("dirt", config.INVENTORY_SIZE * config.MAX_STACK_SIZE)
        aim(scene, 11, DEFAULT_SURFACE)
        handler.dispatch(ord("j"))
        scene.update(DT)
        assert scene.notice == "inventory is full"

    def test_a_place_refusal_is_reported(self) -> None:
        scene, handler, _, _, _ = build()
        aim(scene, 11, DEFAULT_SURFACE)
        handler.dispatch(ord("k"))
        scene.update(DT)
        assert scene.notice == "that tile is occupied"

    def test_the_notice_fades(self) -> None:
        scene, handler, clock, _, _ = build()
        aim(scene, 11, DEFAULT_SURFACE - 8)
        handler.dispatch(ord("j"))
        scene.update(DT)
        assert scene.notice == "out of reach"
        clock.advance(config.HOLD_WINDOW_SECONDS + 0.01)
        run(scene, int(config.NOTICE_SECONDS / DT) + 2)
        assert scene.notice == ""


class TestWorldAccess:
    def test_scene_exposes_the_world_it_edits(self) -> None:
        scene, _, _, _, _ = build()
        assert isinstance(scene.world, World)
