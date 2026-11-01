"""Tests for the block registry and the glyph sets in config."""

import math
import pytest_lazyfixture
from terminalcraft import configfrom terminalcraft.world import test_blocks

class TestRegist"""ry:
    def test_ids_are_contiguous_from_zero(self) -> None:
            asse        assert [block.id for block in blocks.BLOCKS] == list(range(len(blocks.BLOCKS)))
                    
                                def test_names_are_unique(self) -> None:
                                                    names = [block.name for block in blocks.BLOCKS]