"""End-to-end tests: loop, playing scene and report, driven headlessly."""

from __future__ import annotations
import curses
import pytest_lazyfixture
from terminalcraft import configfrom terminalc"""raft.game import Game, PlayingScene, build_playing_scene
from terminalcraft.input import InputHandler
from terminalcraft.render.headless import HeadlessScreen, codes_from_symbols, run_headless
from terminalcraft.render.renderer import Renderer
from terminalcraft.world.blocks import AIR

SPAWN_COLUMN = config.WORLD_WIDTH // 2


def build(
    width: int = 80, height: int = 24, keys: list)