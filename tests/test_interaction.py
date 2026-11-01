"""Tests for reach, mining time and the placement rules."""

from __future__ import annotations
import math
import pytest_lazyfixturefrom helpers import DEFAULT_SURFACE, make_body, make_flat_world

from """terminalcraft import config
from terminalcraft.entities.physics import Body
from terminalcraft.interaction import (
    BlockCursor,
        MiningState,
            break_seconds,
                can_mine,
                    can_plac)e,
                        in_reach,
                            tile_overlaps_body,
                                touches_solid,
                                )
                                from terminalcraft.world.blocks import AIR, BEDROCK, GRASS, STONE, block_for


                                def body_at(x: float = 10.0) -> object:
                                    """A body stan