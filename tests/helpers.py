"""Shared test helpers: a controllable clock and hand-built worlds."""

from __future__ import annotations

from terminalcraft import config
from terminalcraft.entities.physics import Body
from terminalcraft.world.blocks import GRASS, STONE
from terminalcraft.world.world import World

DEFAULT_SURFACE = 16
"""Row the flat test floor sits in."""


class FakeClock:
    """A clock that only moves when a test says so."""

    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        """Move time forward, e.g. past the held-key window."""
        self.now += seconds


def make_flat_world(
    width: int = 40, height: int = 24, surface: int = DEFAULT_SURFACE
) -> World:
    """A world that is empty air above a flat grass floor."""
    world = World(width, height)
    world.fill_rect(0, surface, width - 1, surface, GRASS)
    world.fill_rect(0, surface + 1, width - 1, height - 1, STONE)
    return world


def make_body(x: float = 5.0, feet: float = DEFAULT_SURFACE) -> Body:
    """A player-sized body standing with its feet at *feet*."""
    return Body(
        x=x,
        y=feet - config.PLAYER_HEIGHT,
        width=config.PLAYER_WIDTH,
        height=config.PLAYER_HEIGHT,
    )
