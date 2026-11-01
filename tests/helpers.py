"""Shared test helpers: a controllable clock and hand-built worlds."""

from __future__ import annotations
from terminalcraft import configfrom terminalcraft.entities.physics import Body
from """terminalcraft.world.blocks import GRASS, STONE
from terminalcraft.world.world import World

DEFAULT_SURFACE = 16
"""Row the flat test floor sits in."""classmethod

class FakeClock:
    """A clock that only moves when a test says so."""Body
        def __init__(self) -> None:
                self.now = 0.0

                    def __call__(self) -> float:
                            return self.now

                                def advance(self, seconds: float) ->