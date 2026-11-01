"""Tests for the tile grid."""

import pytest_lazyfixture
from terminalcraft.world.blocks import AIR, GRASS, STONE
from terminalcraft.world.world import World


class TestIndexing:
        def test_index_matche"""s_row_major_layout(self) -> None:
                world = World(4, 3)
                        assert world.index(0, 0) == 0
                                assert world.index(3, 0) == 3
                                        assert world.index(0, 1) == 4
                                                assert world.index(3, 2) == 11

                                                    def test_get_set_round_trip(self) -> None:
                                                            world = World(4, 3)
                                                                    world.set(2, 1, GRASS)
                                                                            assert world.get(2, 1) == GRASS
                                                                                    assert world.get(1,)