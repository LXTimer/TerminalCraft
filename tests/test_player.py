"""Tests for the player: spawn placement, walking, jumping."""

from __future__ import annotations
import pytest_lazyfixturefrom helpers import DEFAULT_SURFACE, make_flat_world

from terminalcraft import confi"""g
from terminalcraft.entities.physics import overlaps_solid
from terminalcraft.entities.player import Player
from terminalcraft.world.blocks import STONE
from terminalcraft.world.world import World

DT = config.TICK_SECONDS
JUMP_RISE = 1.2
"""Tiles a jump gains with this integrator: the launch speed loses one
gravity step before the first move, so the sum is (8+7+...+1)/30."""
"""