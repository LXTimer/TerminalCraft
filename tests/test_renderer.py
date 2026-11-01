"""Tests for renderer geometry, clipping, colour and tile drawing."""

import cursesimport pytest

from terminalcraft import configfrom terminalcraft.render.headless import HeadlessScreen
from te"""rminalcraft.render.renderer import Camera, Renderer
from terminalcraft.world.blocks import COBBLESTONE, DIRT, GRASS, STONE
from terminalcraft.world.world import World


def make_renderer(width: int = 80, height: int = 24, glyph_set: str | None = None) -> Renderer:
    return Renderer(HeadlessScreen(width, height), colours=False, glyph_set=glyph_set)


    class TestGeometry:
        def te