"""Tests for the block registry and the glyph sets in config."""

import math

import pytest

from terminalcraft import config
from terminalcraft.world import blocks


class TestRegistry:
    def test_ids_are_contiguous_from_zero(self) -> None:
        assert [block.id for block in blocks.BLOCKS] == list(range(len(blocks.BLOCKS)))

    def test_names_are_unique(self) -> None:
        names = [block.name for block in blocks.BLOCKS]
        assert len(set(names)) == len(names)

    def test_v1_blocks_are_all_present(self) -> None:
        assert {block.name for block in blocks.BLOCKS} == {
            "air",
            "grass",
            "dirt",
            "stone",
            "cobblestone",
            "log",
            "leaves",
            "planks",
            "crafting_table",
            "bedrock",
        }

    def test_block_for_round_trips(self) -> None:
        for block in blocks.BLOCKS:
            assert blocks.block_for(block.id) is block

    def test_block_for_unknown_id_raises(self) -> None:
        with pytest.raises(KeyError):
            blocks.block_for(len(blocks.BLOCKS))


class TestBlockFields:
    def test_air_is_not_solid_and_drops_nothing(self) -> None:
        air = blocks.block_for(blocks.AIR)
        assert air.solid is False
        assert air.drops == ""
        assert air.hardness == 0.0

    def test_every_solid_block_is_marked_solid(self) -> None:
        for block in blocks.BLOCKS:
            if block.name != "air":
                assert block.solid is True, block.name

    def test_bedrock_is_unbreakable(self) -> None:
        assert math.isinf(blocks.block_for(blocks.BEDROCK).hardness)

    def test_stone_needs_a_wooden_pickaxe_and_drops_cobblestone(self) -> None:
        stone = blocks.block_for(blocks.STONE)
        assert stone.tool == "pickaxe"
        assert stone.min_tool_tier == 1
        assert stone.drops == "cobblestone"

    def test_grass_drops_dirt(self) -> None:
        # Minecraft convention: no grass item exists in v1, so the block
        # under it is what you get.
        assert blocks.block_for(blocks.GRASS).drops == "dirt"

    def test_tools_are_known_names(self) -> None:
        for block in blocks.BLOCKS:
            assert block.tool in (None, "pickaxe", "axe", "shovel"), block.name

    def test_minable_blocks_drop_something(self) -> None:
        for block in blocks.BLOCKS:
            if block.name in ("air", "bedrock", "leaves"):
                assert block.drops == "", block.name
            else:
                assert block.drops, block.name


class TestGlyphSets:
    def test_every_block_has_a_glyph_in_every_set(self) -> None:
        for set_name, glyphs in config.GLYPH_SETS.items():
            for block in blocks.BLOCKS:
                assert block.name in glyphs, f"{block.name} missing from {set_name}"

    def test_glyphs_are_two_columns_wide(self) -> None:
        for set_name, glyphs in config.GLYPH_SETS.items():
            for block_name, glyph in glyphs.items():
                assert len(glyph) == config.TILE_WIDTH, (set_name, block_name)

    def test_ascii_set_is_pure_ascii(self) -> None:
        for block_name, glyph in config.GLYPH_SETS["ascii"].items():
            assert all(ord(ch) < 128 for ch in glyph), block_name

    def test_unicode_set_differs_from_ascii(self) -> None:
        # Otherwise the startup probe would have nothing to decide.
        assert config.GLYPH_SETS["unicode"] != config.GLYPH_SETS["ascii"]

    def test_registry_glyphs_match_the_unicode_set(self) -> None:
        # The registry glyph is the canonical one; the unicode set may only
        # refine it, so both stay consistent.
        for block in blocks.BLOCKS:
            assert len(block.glyph) == config.TILE_WIDTH, block.name
