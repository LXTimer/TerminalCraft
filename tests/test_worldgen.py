"""Tests for the milestone-2 test world (determinism and structure)."""

from terminalcraft import config
from terminalcraft.world.blocks import AIR, BEDROCK, COBBLESTONE, DIRT, GRASS, LEAVES, LOG, STONE
from terminalcraft.world.worldgen import OUTCROP_OFFSET, TREE_OFFSETS, build_test_world


class TestDeterminism:
    def test_every_call_returns_identical_tiles(self) -> None:
        assert build_test_world().tile_bytes() == build_test_world().tile_bytes()


class TestTerrain:
    def test_dimensions(self) -> None:
        world = build_test_world()
        assert (world.width, world.height) == (config.WORLD_WIDTH, config.WORLD_HEIGHT)

    def test_bottom_row_is_bedrock(self) -> None:
        world = build_test_world()
        for x in range(world.width):
            assert world.get(x, world.height - 1) == BEDROCK

    def test_surface_is_grass_over_dirt_over_stone(self) -> None:
        world = build_test_world()
        outcrop_x = world.width // 2 + OUTCROP_OFFSET
        for x in range(0, world.width, 37):
            if abs(x - outcrop_x) <= 2:
                continue  # the outcrop replaces the surface there
            surface = world.surface_y(x)
            assert world.get(x, surface) == GRASS, x
            for dy in range(1, config.DIRT_DEPTH + 1):
                assert world.get(x, surface + dy) == DIRT, (x, dy)
            assert world.get(x, surface + config.DIRT_DEPTH + 1) == STONE, x

    def test_no_air_below_the_surface(self) -> None:
        world = build_test_world()
        for x in range(0, world.width, 53):
            surface = world.surface_y(x)
            for y in range(surface, world.height):
                assert world.get(x, y) != AIR, (x, y)

    def test_terrain_stays_within_the_expected_band(self) -> None:
        world = build_test_world()
        # Tree columns are excluded: their canopies reach up to 8 tiles above
        # the terrain, so surface_y there measures the tree, not the hill.
        tree_columns = {world.width // 2 + offset for offset in TREE_OFFSETS}
        heights = [
            world.surface_y(x)
            for x in range(world.width)
            if all(abs(x - column) > 2 for column in tree_columns)
        ]
        low = config.TERRAIN_BASE - config.TERRAIN_AMPLITUDE - config.TERRAIN_DETAIL - 1
        high = config.TERRAIN_BASE + config.TERRAIN_AMPLITUDE + config.TERRAIN_DETAIL + 1
        assert min(heights) >= low
        assert max(heights) <= high

    def test_outcrop_is_cobblestone_at_the_surface(self) -> None:
        world = build_test_world()
        x = world.width // 2 + OUTCROP_OFFSET
        surface = world.surface_y(x)
        for dx in range(-2, 3):
            assert world.get(x + dx, surface) == COBBLESTONE, dx
            assert world.get(x + dx, surface + 2) == COBBLESTONE, dx


class TestTrees:
    def test_every_tree_has_a_trunk_and_canopy(self) -> None:
        world = build_test_world()
        for offset in TREE_OFFSETS:
            x = world.width // 2 + offset
            logs = [y for y in range(world.height) if world.get(x, y) == LOG]
            assert logs, f"no trunk at x={x}"
            assert 3 <= len(logs) <= 5, (x, len(logs))
            top_log = min(logs)
            canopy = [y for y in range(top_log - 3, top_log) if world.get(x, y) == LEAVES]
            assert canopy, f"no canopy above the trunk at x={x}"

    def test_trunk_stands_on_the_surface(self) -> None:
        world = build_test_world()
        for offset in TREE_OFFSETS:
            x = world.width // 2 + offset
            logs = [y for y in range(world.height) if world.get(x, y) == LOG]
            ground = max(logs) + 1
            assert world.get(x, ground) == GRASS, x

    def test_canopies_do_not_overlap(self) -> None:
        world = build_test_world()
        columns = sorted(world.width // 2 + offset for offset in TREE_OFFSETS)
        gaps = [b - a for a, b in zip(columns, columns[1:])]
        assert min(gaps) > 3  # canopy radius is 1
