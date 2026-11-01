"""Tests for renderer geometry, clipping, colour and tile drawing."""

import curses
import pytest

from terminalcraft import config
from terminalcraft.render.headless import HeadlessScreen
from terminalcraft.render.renderer import Camera, Renderer
from terminalcraft.world.blocks import COBBLESTONE, DIRT, GRASS, STONE
from terminalcraft.world.world import World


def make_renderer(width: int = 80, height: int = 24, glyph_set: str | None = None) -> Renderer:
    return Renderer(HeadlessScreen(width, height), colours=False, glyph_set=glyph_set)


class TestGeometry:
    def test_size_matches_screen(self) -> None:
        assert make_renderer(100, 30).size == (100, 30)

    @pytest.mark.parametrize(
        ("width", "height", "expected"),
        [
            (config.MIN_TERMINAL_WIDTH, config.MIN_TERMINAL_HEIGHT, False),
            (config.MIN_TERMINAL_WIDTH - 1, config.MIN_TERMINAL_HEIGHT, True),
            (config.MIN_TERMINAL_WIDTH, config.MIN_TERMINAL_HEIGHT - 1, True),
            (120, 40, False),
        ],
    )
    def test_too_small(self, width: int, height: int, expected: bool) -> None:
        assert make_renderer(width, height).too_small is expected

    def test_handle_resize_rereads_size(self) -> None:
        screen = HeadlessScreen(80, 24)
        renderer = Renderer(screen, colours=False)
        screen.resize(100, 30)
        renderer.handle_resize()
        assert renderer.size == (100, 30)


class TestClipping:
    def test_offscreen_draws_are_dropped(self) -> None:
        screen = HeadlessScreen(20, 5)
        renderer = Renderer(screen, colours=False)
        renderer.begin_frame()
        renderer.addstr(-1, 0, "above")
        renderer.addstr(5, 0, "below")
        renderer.addstr(0, 25, "right")
        renderer.addstr(2, 0, "visible")
        renderer.present()
        text = screen.text()
        assert "visible" in text
        assert "above" not in text
        assert "below" not in text
        assert "right" not in text

    def test_long_lines_are_clipped(self) -> None:
        screen = HeadlessScreen(20, 5)
        renderer = Renderer(screen, colours=False)
        renderer.begin_frame()
        renderer.addstr(0, 0, "x" * 50)
        renderer.present()
        assert len(screen.text().splitlines()[0]) == 20

    def test_bottom_right_cell_never_raises(self) -> None:
        # The fake screen raises like curses does on the bottom-right cell;
        # the renderer must swallow it.
        screen = HeadlessScreen(20, 5)
        renderer = Renderer(screen, colours=False)
        renderer.begin_frame()
        renderer.addstr(4, 19, "!")
        renderer.present()


class TestHeadlessScreen:
    def test_capture_trims_trailing_blanks(self) -> None:
        screen = HeadlessScreen(20, 3)
        screen.erase()
        screen.addstr(1, 0, "hi")
        assert screen.text() == "\nhi\n"

    def test_getch_drains_script_then_reports_nothing(self) -> None:
        screen = HeadlessScreen(20, 3, [ord("a"), ord("b")])
        assert screen.getch() == ord("a")
        assert screen.getch() == ord("b")
        assert screen.getch() == -1
        assert screen.getch() == -1


class TestColours:
    def test_without_colours_no_pair_is_allocated(self) -> None:
        renderer = make_renderer()
        assert renderer.pair_attr(curses.COLOR_RED, curses.COLOR_BLACK) == 0

    def test_without_colours_bold_attrs_still_work(self) -> None:
        # Bold/dim are terminal attributes, not colours.
        renderer = make_renderer()
        assert renderer.attr("value") == curses.A_BOLD
        assert renderer.attr("label") == curses.A_DIM

    def test_unknown_attr_name_is_plain(self) -> None:
        assert make_renderer().attr("nope") == 0


class TestCamera:
    def test_move_applies_a_tile_space_delta(self) -> None:
        camera = Camera(1.0, 2.0)
        camera.move(-0.5, 3.0)
        assert (camera.x, camera.y) == (0.5, 5.0)


class TestCameraFollow:
    def test_tracks_horizontally_immediately(self) -> None:
        camera = Camera(0.0, 0.0)
        camera.follow(30.0, 0.0, config.TICK_SECONDS)
        assert camera.x == 30.0

    def test_small_vertical_offsets_are_ignored(self) -> None:
        camera = Camera(0.0, 10.0)
        camera.follow(0.0, 10.0 + config.CAMERA_DEADZONE_Y, config.TICK_SECONDS)
        assert camera.y == 10.0

    def test_large_vertical_offsets_are_followed(self) -> None:
        camera = Camera(0.0, 10.0)
        camera.follow(0.0, 20.0, config.TICK_SECONDS)
        assert camera.y > 10.0

    def test_vertical_speed_is_capped(self) -> None:
        camera = Camera(0.0, 10.0)
        camera.follow(0.0, 1000.0, 1.0)
        assert camera.y == pytest.approx(10.0 + config.CAMERA_MAX_SPEED_Y)

    def test_the_gap_shrinks_to_the_dead_zone(self) -> None:
        camera = Camera(0.0, 10.0)
        target = 10.0 + config.CAMERA_DEADZONE_Y + 0.1
        camera.follow(0.0, target, 1.0)
        assert target - camera.y == pytest.approx(config.CAMERA_DEADZONE_Y)

    def test_following_upwards_works_too(self) -> None:
        camera = Camera(0.0, 30.0)
        camera.follow(0.0, 20.0, config.TICK_SECONDS)
        assert camera.y < 30.0

    def test_the_camera_never_overshoots(self) -> None:
        camera = Camera(0.0, 10.0)
        for _ in range(100):
            camera.follow(0.0, 30.0, config.TICK_SECONDS)
        assert camera.y == pytest.approx(30.0 - config.CAMERA_DEADZONE_Y)


class TestViewOrigin:
    def test_world_smaller_than_the_view_is_centred(self) -> None:
        renderer = make_renderer(80, 24)  # view: 40x24 tiles
        world = World(20, 20)
        assert renderer.view_origin(world) == (-10, -2)

    def test_clamped_to_the_world_edges(self) -> None:
        renderer = make_renderer(80, 24)
        world = World(100, 100)
        renderer.camera.x = 0.0
        renderer.camera.y = 0.0
        assert renderer.view_origin(world) == (0, 0)
        renderer.camera.x = 100.0
        renderer.camera.y = 100.0
        assert renderer.view_origin(world) == (60, 76)
        renderer.camera.x = 50.0
        renderer.camera.y = 50.0
        assert renderer.view_origin(world) == (30, 38)


class TestGlyphSets:
    def test_unknown_set_is_rejected(self) -> None:
        with pytest.raises(ValueError):
            make_renderer(glyph_set="nope")

    def test_auto_without_a_terminal_means_unicode(self) -> None:
        assert make_renderer().glyph_set_name == "unicode"

    def test_requested_set_is_used_for_tiles(self) -> None:
        screen = HeadlessScreen(8, 2)
        renderer = Renderer(screen, colours=False, glyph_set="ascii")
        world = World(4, 2)
        world.fill_rect(0, 0, 3, 0, GRASS)
        renderer.begin_frame()
        renderer.draw_world(world)
        renderer.present()
        assert screen.text().splitlines()[0] == "#" * 8


class TestWorldDrawing:
    def make_world_renderer(
        self, width: int, height: int
    ) -> tuple[Renderer, HeadlessScreen]:
        # Built directly (not via make_renderer) so the test asserts on the
        # very screen the renderer draws to.
        screen = HeadlessScreen(width, height)
        return Renderer(screen, colours=False, glyph_set="ascii"), screen

    def test_tiles_are_two_columns_wide(self) -> None:
        renderer, screen = self.make_world_renderer(20, 3)
        world = World(10, 3)
        world.fill_rect(0, 1, 9, 1, GRASS)
        world.fill_rect(0, 2, 9, 2, STONE)
        renderer.begin_frame()
        renderer.draw_world(world)
        renderer.present()
        lines = screen.text().splitlines()
        assert lines[0] == ""  # sky row
        assert lines[1] == "#" * 20  # one grass run across the row
        assert lines[2] == "#" * 20  # the bottom row lands despite the corner quirk

    def test_each_block_draws_its_own_glyph(self) -> None:
        renderer, screen = self.make_world_renderer(8, 2)
        world = World(4, 2)
        world.set(0, 0, GRASS)
        world.set(1, 0, DIRT)
        world.set(2, 0, STONE)
        world.set(3, 0, COBBLESTONE)
        renderer.begin_frame()
        renderer.draw_world(world)
        renderer.present()
        assert screen.text().splitlines()[0] == "##..##%%"

    def test_odd_screen_width_leaves_the_last_column_blank(self) -> None:
        renderer, screen = self.make_world_renderer(21, 2)
        world = World(10, 2)
        world.fill_rect(0, 0, 9, 0, GRASS)
        renderer.begin_frame()
        renderer.draw_world(world)
        renderer.present()
        assert screen.text().splitlines()[0] == "#" * 20

    def test_camera_decides_which_tiles_are_visible(self) -> None:
        # A recognisable tile at world x=5 proves the view origin: it shows
        # up in column 0 of the screen only when the origin is 5.
        renderer, screen = self.make_world_renderer(8, 2)
        world = World(10, 2)
        world.set(5, 0, STONE)
        renderer.camera.x = 7.0
        renderer.begin_frame()
        renderer.draw_world(world)
        renderer.present()
        assert screen.text().splitlines()[0] == "##"


class TestScreenMapping:
    def make_world_renderer(
        self, width: int, height: int, *, glyph_set: str = "ascii"
    ) -> tuple[Renderer, HeadlessScreen]:
        screen = HeadlessScreen(width, height)
        return Renderer(screen, colours=False, glyph_set=glyph_set), screen

    def test_a_point_maps_to_the_matching_cell(self) -> None:
        renderer, _ = self.make_world_renderer(20, 4)
        world = World(10, 4)
        # View origin (0, 0): one tile is two columns, one row.
        assert renderer.screen_pos(world, 0.0, 0.0) == (0, 0)
        assert renderer.screen_pos(world, 3.0, 2.0) == (2, 6)

    def test_points_outside_the_view_have_no_cell(self) -> None:
        renderer, _ = self.make_world_renderer(20, 4)
        world = World(10, 4)
        assert renderer.screen_pos(world, 0.0, 99.0) is None
        assert renderer.screen_pos(world, 99.0, 0.0) is None

    def test_tile_positions_account_for_tile_width(self) -> None:
        renderer, _ = self.make_world_renderer(20, 4)
        world = World(10, 4)
        assert renderer.tile_screen_pos(world, 4, 1) == (1, 8)

    def test_a_tile_half_off_the_right_edge_has_no_position(self) -> None:
        renderer, _ = self.make_world_renderer(9, 4)  # 4.5 tiles wide
        world = World(10, 4)
        assert renderer.tile_screen_pos(world, 4, 0) is None


class TestSprites:
    def make_renderer(self, width: int = 20, height: int = 4) -> tuple[Renderer, HeadlessScreen]:
        screen = HeadlessScreen(width, height)
        return Renderer(screen, colours=False, glyph_set="ascii"), screen

    def test_draw_sprite_writes_one_row_per_line(self) -> None:
        renderer, screen = self.make_renderer()
        renderer.begin_frame()
        renderer.draw_sprite(1, 3, ("@@", "##"), 0)
        lines = screen.text().splitlines()
        assert lines[1] == "   @@"
        assert lines[2] == "   ##"

    def test_sprite_lines_are_clipped_not_wrapped(self) -> None:
        renderer, screen = self.make_renderer(width=4, height=2)
        renderer.begin_frame()
        renderer.draw_sprite(0, 3, ("@@", "##"), 0)
        lines = screen.text().splitlines()
        assert lines[0] == "   @"

    def test_a_sprite_above_the_screen_is_clipped(self) -> None:
        renderer, screen = self.make_renderer(width=6, height=2)
        renderer.begin_frame()
        renderer.draw_sprite(-1, 0, ("xx", "yy"), 0)
        assert screen.text().splitlines()[0] == "yy"

    def test_sprites_of_every_glyph_set_are_two_columns_wide(self) -> None:
        for name, lines in config.PLAYER_SPRITES.items():
            assert len(lines) == 2, name
            for line in lines:
                assert len(line) == config.TILE_WIDTH, name


class TestHighlight:
    def test_the_highlighted_tile_keeps_its_glyph(self) -> None:
        # Attributes are not captured headlessly, so this only proves the
        # marker draws the tile rather than blanking it.
        screen = HeadlessScreen(8, 2)
        renderer = Renderer(screen, colours=False, glyph_set="ascii")
        world = World(4, 2)
        world.fill_rect(0, 1, 3, 1, GRASS)
        renderer.begin_frame()
        renderer.draw_world(world)
        renderer.draw_highlight(world, 2, 1)
        renderer.present()
        assert screen.text().splitlines()[1] == "########"

    def test_highlighting_air_is_harmless(self) -> None:
        screen = HeadlessScreen(8, 2)
        renderer = Renderer(screen, colours=False, glyph_set="ascii")
        world = World(4, 2)
        renderer.begin_frame()
        renderer.draw_highlight(world, 2, 0)
        renderer.present()

    def test_a_tile_outside_the_view_is_skipped(self) -> None:
        screen = HeadlessScreen(8, 2)
        renderer = Renderer(screen, colours=False, glyph_set="ascii")
        world = World(4, 2)
        renderer.begin_frame()
        renderer.draw_highlight(world, 99, 99)
        renderer.present()


class TestGlyphForBlock:
    def test_returns_the_active_sets_glyph(self) -> None:
        ascii_renderer = Renderer(HeadlessScreen(8, 2), colours=False, glyph_set="ascii")
        unicode_renderer = Renderer(HeadlessScreen(8, 2), colours=False, glyph_set="unicode")
        assert ascii_renderer.glyph_for_block(GRASS) == "##"
        assert unicode_renderer.glyph_for_block(GRASS) == "██"


class TestTileAt:
    """Screen cell -> world tile, the inverse of ``tile_screen_pos`` (mouse aim)."""

    @staticmethod
    def make(width: int = 80, height: int = 24, world_width: int = 40) -> tuple[Renderer, World]:
        renderer = make_renderer(width, height)
        renderer.camera.x = 20.0
        renderer.camera.y = 20.0
        return renderer, World(world_width, 40)

    def test_maps_a_cell_to_the_tile_under_it(self) -> None:
        renderer, world = self.make()
        # 80x24 view of a 40-tile-wide world: origin is (0, 8), so screen
        # (row 12, column 22) is tile (11, 20).
        assert renderer.tile_at(world, 22, 12) == (11, 20)

    def test_both_columns_of_a_tile_map_to_that_tile(self) -> None:
        renderer, world = self.make()
        assert renderer.tile_at(world, 22, 12) == renderer.tile_at(world, 23, 12)

    def test_round_trips_with_tile_screen_pos(self) -> None:
        renderer, world = self.make()
        row, column = renderer.tile_screen_pos(world, 11, 20)
        assert renderer.tile_at(world, column, row) == (11, 20)

    def test_cells_outside_the_window_are_rejected(self) -> None:
        renderer, world = self.make()
        assert renderer.tile_at(world, -1, 0) is None
        assert renderer.tile_at(world, 0, -1) is None
        assert renderer.tile_at(world, 80, 0) is None
        assert renderer.tile_at(world, 0, 24) is None

    def test_cells_before_the_world_are_rejected(self) -> None:
        # A world narrower than the view is centred, so the origin is
        # negative and the first cells map to tiles that do not exist.
        renderer, world = self.make(world_width=20)
        assert renderer.tile_at(world, 0, 12) is None
        assert renderer.tile_at(world, 20, 12) == (0, 20)
