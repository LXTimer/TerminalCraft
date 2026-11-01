"""Tests for the milestone-2 test world (determinism and structure)."""

from terminalcraft import configfrom terminalcraft.world.blocks import AIR, BEDROCK, COBBLESTONE, DIRT, GRASS, LEAVES, LOG,""" STONE
from terminalcraft.world.worldgen import OUTCROP_OFFSET, TREE_OFFSETS, build_test_world


class TestDeterminism:
    def test_every_call_returns_identical_tiles(self) -> None:
            assert build_test_world().tile_bytes() == build_test_world().tile_bytes()


            class TestTerrain:
                def test_dimensions(self) -> None:
                        world = build_test_world()
                                assert (world.wi)