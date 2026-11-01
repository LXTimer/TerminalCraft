"""End-to-end tests: loop, playing scene and report, driven headlessly."""

from __future__ import annotations

import curses

import pytest

from terminalcraft import config
from terminalcraft.game import Game, PlayingScene, build_playing_scene
from terminalcraft.input import InputHandler
from terminalcraft.render.headless import HeadlessScreen, codes_from_symbols, run_headless
from terminalcraft.render.renderer import Renderer
from terminalcraft.world.blocks import AIR

SPAWN_COLUMN = config.WORLD_WIDTH // 2


def build(
    width: int = 80, height: int = 24, keys: list[int] | None = None
) -> tuple[Game, PlayingScene, HeadlessScreen]:
    screen = HeadlessScreen(width, height, keys or [])
    renderer = Renderer(screen, colours=False)
    handler = InputHandler()
    game = Game(renderer, handler)
    return game, build_playing_scene(game, handler, renderer), screen


def run_ticks(game: Game, scene: PlayingScene, ticks: int) -> None:
    game.run(scene, max_ticks=ticks, frame_seconds=config.TICK_SECONDS)


class TestLoop:
    def test_runs_exactly_max_ticks(self) -> None:
        game, scene, _ = build()
        run_ticks(game, scene, 5)
        assert game.tick_count == 5

    def test_quit_stops_the_loop_after_one_final_frame(self) -> None:
        game, scene, _ = build(keys=[ord("q")])
        run_ticks(game, scene, 5)
        assert game.tick_count == 1

    def test_accumulator_merges_two_half_tick_frames(self) -> None:
        # Frames shorter than a tick advance the accumulator only; the second
        # half-tick completes tick 1.
        game, scene, _ = build()
        game.run(scene, max_ticks=1, frame_seconds=config.TICK_SECONDS / 2)
        assert game.tick_count == 1

    def test_resize_key_is_handled_without_crashing(self) -> None:
        game, scene, _ = build(keys=[curses.KEY_RESIZE])
        run_ticks(game, scene, 3)
        assert game.tick_count == 3

    def test_actions_reach_the_active_scene(self) -> None:
        received: list[str] = []

        class SpyScene:
            def handle_action(self, action: object) -> bool:
                received.append(action.name)  # type: ignore[attr-defined]
                return action.name == "MOVE_LEFT"  # consume movement only

            def update(self, dt: float) -> None:
                pass

            def draw(self, renderer: Renderer) -> None:
                pass

        screen = HeadlessScreen(80, 24, [ord("a"), ord("j"), ord("q")])
        renderer = Renderer(screen, colours=False)
        game = Game(renderer, InputHandler())
        game.run(SpyScene(), max_ticks=1, frame_seconds=config.TICK_SECONDS)
        # MINE is not consumed by the scene (and is not QUIT), so the loop
        # ignores it; QUIT falls through to the loop and stops it.
        assert received == ["MOVE_LEFT", "MINE", "QUIT"]


class TestDebugScreen:
    def test_names_the_milestone(self) -> None:
        game, scene, screen = build()
        run_ticks(game, scene, 2)
        assert "milestone 3" in screen.text()

    def test_shows_last_key_and_action(self) -> None:
        game, scene, screen = build(keys=[ord("j")])
        run_ticks(game, scene, 2)
        text = screen.text()
        assert "last key" in text
        assert "j (106)" in text
        assert "MINE" in text

    def test_shows_tick_count(self) -> None:
        game, scene, screen = build()
        run_ticks(game, scene, 7)
        assert "ticks 7" in screen.text()

    def test_shows_player_physics(self) -> None:
        game, scene, screen = build()
        run_ticks(game, scene, 2)
        text = screen.text()
        assert "player " in text
        assert "velocity " in text
        assert "ground " in text
        assert "cursor " in text

    def test_too_small_terminal_shows_warning(self) -> None:
        game, scene, screen = build(width=40, height=10)
        run_ticks(game, scene, 2)
        text = screen.text()
        assert "Please enlarge" in text
        assert "80x24" in text
        assert "TerminalCraft" not in text


class TestPlayingView:
    def test_world_is_drawn_behind_the_overlay(self) -> None:
        game, scene, screen = build()
        run_ticks(game, scene, 2)
        text = screen.text()
        assert "\u2588" in text  # tile glyphs are on screen
        assert "TerminalCraft" in text  # the overlay stays on top

    def test_player_sprite_is_drawn(self) -> None:
        game, scene, screen = build()
        run_ticks(game, scene, 2)
        assert "@@" in screen.text()

    def test_hotbar_shows_the_starter_stack(self) -> None:
        game, scene, screen = build()
        run_ticks(game, scene, 2)
        text = screen.text()
        assert "[▒▒  8]" in text  # selected slot: dirt glyph and count
        assert "Dirt x8" in text  # status row names the held item

    def test_player_starts_standing_on_the_surface(self) -> None:
        game, scene, _ = build()
        run_ticks(game, scene, 2)
        assert scene.player.body.on_ground
        surface = scene.world.surface_y(SPAWN_COLUMN)
        assert scene.player.body.bottom == pytest.approx(surface)

    def test_camera_is_centred_on_the_player(self) -> None:
        game, scene, _ = build()
        run_ticks(game, scene, 2)
        assert scene.camera.x == pytest.approx(scene.player.body.center_x)

    def test_walking_moves_the_player_and_the_camera(self) -> None:
        game, scene, _ = build(keys=[ord("d")])
        start = scene.player.body.x
        run_ticks(game, scene, 4)
        assert scene.player.body.x > start
        assert scene.camera.x == pytest.approx(scene.player.body.center_x)

    def test_keypad_arrows_step_the_cursor(self) -> None:
        # Regression test for the ConPTY delivery path: in Windows Terminal
        # and the VS Code integrated terminal the arrows arrive as keypad
        # codes, and the cursor must still move.
        game, scene, screen = build(keys=[curses.KEY_B1])
        start = scene.cursor.x
        run_ticks(game, scene, 2)
        assert scene.cursor.x == start - 1
        assert "CURSOR_LEFT" in screen.text()

    def test_hotbar_digit_changes_the_selection(self) -> None:
        game, scene, _ = build(keys=[ord("2")])
        run_ticks(game, scene, 2)
        assert scene.inventory.selected == 1


class TestMouseThroughTheLoop:
    """A click has to survive the real path: getch -> poll -> action -> aim."""

    class _ScriptedMouse:
        """Mouse backend that hands out queued (column, row, bstate) tuples."""

        def __init__(self) -> None:
            self.events: list[tuple[int, int, int]] = []

        def __call__(self) -> tuple[int, int, int] | None:
            return self.events.pop(0) if self.events else None

    def test_a_click_mines_the_tile_it_landed_on(self) -> None:
        mouse = self._ScriptedMouse()
        screen = HeadlessScreen(80, 24, [curses.KEY_MOUSE])
        renderer = Renderer(screen, colours=False)
        handler = InputHandler(mouse_reader=mouse)
        game = Game(renderer, handler)
        scene = build_playing_scene(game, handler, renderer)

        column = int(scene.player.body.center_x) + 2
        row = scene.world.surface_y(column)
        screen_row, screen_column = renderer.tile_screen_pos(scene.world, column, row)
        mouse.events.append((screen_column, screen_row, curses.BUTTON1_PRESSED))

        run_ticks(game, scene, 25)

        assert scene.cursor.tile == (column, row)
        assert scene.world.get(column, row) == AIR
        assert scene.inventory.count("dirt") == 9
        assert f"mouse ({curses.KEY_MOUSE})" in screen.text()


class TestReport:
    def test_report_lists_keys_and_state(self) -> None:
        report = run_headless([ord("a"), ord("j"), ord("q")], ticks=3)
        assert "a (97) -> MOVE_LEFT" in report
        assert "j (106) -> MINE" in report
        assert "q (113) -> QUIT" in report
        assert "--- state ---" in report
        assert "player: x=" in report
        assert "hotbar slot 1: dirt x8" in report
        assert "TerminalCraft" in report

    def test_report_without_keys(self) -> None:
        report = run_headless(ticks=2)
        assert "(no keys fed)" in report

    def test_codes_from_symbols(self) -> None:
        assert codes_from_symbols("a,j,left,q") == [
            ord("a"),
            ord("j"),
            curses.KEY_LEFT,
            ord("q"),
        ]
        assert codes_from_symbols("") == []
        assert codes_from_symbols("  ") == []

    def test_codes_from_symbols_rejects_typos(self) -> None:
        with pytest.raises(ValueError):
            codes_from_symbols("a,hyper")
