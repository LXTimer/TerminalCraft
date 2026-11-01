"""What the player may do to the world, and how long it takes.

Rules live here rather than in the scene so they can be tested against a
hand-built world: reach, "is this block breakable", "may a block go here".
The scene owns the state (what the cursor points at, how far mining has got);
this module owns the answers.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from . import config
from .entities.physics import Body
from .world.blocks import AIR, Block, block_for
from .world.world import World

#: Tile offsets that count as "touching" for placement.
NEIGHBOURS: tuple[tuple[int, int], ...] = ((1, 0), (-1, 0), (0, 1), (0, -1))


@dataclass
class BlockCursor:
    """The tile the arrow keys point at, in world coordinates."""

    x: int
    y: int

    @property
    def tile(self) -> tuple[int, int]:
        """The cursor as a ``(x, y)`` pair."""
        return self.x, self.y

    def move(self, dx: int, dy: int, world: World) -> None:
        """Step the cursor, keeping it inside the world."""
        self.x = min(max(self.x + dx, 0), world.width - 1)
        self.y = min(max(self.y + dy, 0), world.height - 1)


@dataclass
class MiningState:
    """How far the current block has been broken, in seconds."""

    target: tuple[int, int] | None = None
    progress: float = 0.0

    @property
    def active(self) -> bool:
        """True while a block is being mined."""
        return self.target is not None

    def reset(self) -> None:
        """Abandon the current block (cursor moved, key released, done)."""
        self.target = None
        self.progress = 0.0

    def advance(self, target: tuple[int, int], seconds: float, required: float) -> bool:
        """Add mining time for *target*; True when the block finally breaks.

        Progress belongs to one tile: pointing somewhere else starts over,
        which is what stops a player from mining three blocks at once by
        waving the cursor around.
        """
        if self.target != target:
            self.target = target
            self.progress = 0.0
        self.progress += seconds
        return self.progress >= required


def break_seconds(block: Block, speed: float = config.HAND_MINING_SPEED) -> float:
    """Seconds needed to break *block* at *speed*.

    Returns ``math.inf`` for air and for unbreakable blocks (bedrock), which
    callers use as "never"; no separate flag is needed.
    """
    if not block.solid or not math.isfinite(block.hardness):
        return math.inf
    return block.hardness / speed


def in_reach(body: Body, tile_x: int, tile_y: int, reach: float = config.INTERACTION_REACH) -> bool:
    """True when the tile's centre is within *reach* of the body's centre."""
    dx = tile_x + 0.5 - body.center_x
    dy = tile_y + 0.5 - body.center_y
    return dx * dx + dy * dy <= reach * reach


def tile_overlaps_body(body: Body, tile_x: int, tile_y: int) -> bool:
    """True when a block at that tile would intersect the body's hitbox."""
    return (
        tile_x + 1.0 > body.x
        and tile_x < body.right
        and tile_y + 1.0 > body.y
        and tile_y < body.bottom
    )


def touches_solid(world: World, tile_x: int, tile_y: int) -> bool:
    """True when any of the four neighbours is not air.

    Blocks cannot be placed in mid-air: something has to hold them up.
    """
    return any(world.get(tile_x + dx, tile_y + dy) != AIR for dx, dy in NEIGHBOURS)


def mine_refusal(world: World, body: Body, tile_x: int, tile_y: int) -> str | None:
    """Why the player cannot break that tile, or None when they can.

    This used to be a plain bool, which left the scene unable to tell "too far
    away" from "nothing there" - two very different things to tell a player
    who is holding the key and watching nothing happen.
    """
    if not in_reach(body, tile_x, tile_y):
        return "out of reach"
    if not math.isfinite(break_seconds(block_for(world.get(tile_x, tile_y)))):
        return "nothing to break there"
    return None


def place_refusal(world: World, body: Body, tile_x: int, tile_y: int) -> str | None:
    """Why a block may not be placed at that tile, or None when it may."""
    if not world.in_bounds(tile_x, tile_y):
        return "out of bounds"
    if not in_reach(body, tile_x, tile_y):
        return "out of reach"
    if world.get(tile_x, tile_y) != AIR:
        return "that tile is occupied"
    if tile_overlaps_body(body, tile_x, tile_y):
        return "you are standing there"
    if not touches_solid(world, tile_x, tile_y):
        return "needs a block to attach to"
    return None
