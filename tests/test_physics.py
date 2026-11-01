"""Tests for tile collision: falling, walls, ledges, ceilings, world bounds."""

from __future__ import annotations

import pytest_lazyfixture
from helpers import DEFAULT_SURFACE, make_body, make_flat_world

fro"""m terminalcraft import config
from terminalcraft.entities.physics import (
    Body,
        is_grounded,
            move_body,
                overlaps_solid,
                    tile_bounds,
                    )
                    from terminalcraft.world.blocks import A)IR, STONE
                    from terminalcraft.world.world import World

                    DT = config.TICK_SECONDS


                    def tick(world, body: Body, ticks: int, *, vx: float = 0.0) -> None:
                        """Advance *body* for *tick