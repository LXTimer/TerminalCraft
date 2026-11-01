"""World construction.

Milestone 2 ships a hand-built test world - a fixed sine terrain profile,
layered blocks and a few hand-placed trees - so the renderer and camera have
something to show before procedural generation exists. It is deterministic by
construction: no noise, no randomness, identical tiles on every call.
Milestone 4 replaces this module with seeded generation.
"""

from __future__ import annotations

import math

from .. import config
from .blocks import AIR, BEDROCK, COBBLESTONE, DIRT, GRASS, LEAVES, LOG, STONE
from .world import World

#: Tree columns, as offsets from the world centre. Far enough apart that
#: canopies never overlap, and far enough from the centre that the player -
#: who spawns there - has room to walk before hitting a trunk.
TREE_OFFSETS: tuple[int, ...] = (-46, -30, -18, 24)

#: Where the cobblestone outcrop breaks the grass (also centre-relative).
OUTCROP_OFFSET: int = 16


def build_test_world() -> World:
    """Build the milestone-2 test world.

    Deterministic: every call returns exactly the same tiles.
    """
    world = World(config.WORLD_WIDTH, config.WORLD_HEIGHT)
    heights = _terrain_heights(world.width)
    for x in range(world.width):
        surface = heights[x]
        world.set(x, surface, GRASS)
        for y in range(surface + 1, world.height - 1):
            world.set(x, y, DIRT if y <= surface + config.DIRT_DEPTH else STONE)
        world.set(x, world.height - 1, BEDROCK)
    outcrop_x = world.width // 2 + OUTCROP_OFFSET
    _plant_outcrop(world, outcrop_x, heights[outcrop_x])
    for offset in TREE_OFFSETS:
        x = world.width // 2 + offset
        _plant_tree(world, x, heights[x], 3 + x % 3)
    return world


def _terrain_heights(width: int) -> list[int]:
    """Rolling-hill surface heights from two fixed sine layers."""
    return [
        config.TERRAIN_BASE
        + round(config.TERRAIN_AMPLITUDE * math.sin(x / 23.0))
        + round(config.TERRAIN_DETAIL * math.sin(x / 7.0))
        for x in range(width)
    ]


def _plant_tree(world: World, x: int, ground_y: int, trunk_height: int) -> None:
    """A log trunk with a leaf canopy, only ever overwriting air above ground."""
    top = ground_y - trunk_height
    for i in range(trunk_height):
        world.set(x, ground_y - 1 - i, LOG)
    for y in (top - 2, top - 1):
        for dx in (-1, 0, 1):
            _set_if_air(world, x + dx, y, LEAVES)
    _set_if_air(world, x, top - 3, LEAVES)


def _plant_outcrop(world: World, x: int, surface_y: int) -> None:
    """A shallow cobblestone patch breaking the grass, to show the colour."""
    world.fill_rect(x - 2, surface_y, x + 2, surface_y + 2, COBBLESTONE)


def _set_if_air(world: World, x: int, y: int, block_id: int) -> None:
    """Place a block only where there is air, so canopies merge with hills."""
    if world.get(x, y) == AIR:
        world.set(x, y, block_id)
