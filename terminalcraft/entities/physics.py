"""Axis-separated AABB collision between a body and the tile grid.

The body is an axis-aligned box in tile units: ``x``/``y`` is its top-left
corner and ``y`` grows downward like the world does. Movement is resolved one
axis at a time - horizontal first, then vertical - because resolving them
together would make a body walking into a wall stop dead instead of sliding
along it.

Two conventions matter for every check in here:

* Edges that lie exactly on a tile boundary do not collide. A body whose feet
  are at y=30.0 is standing *on* row 30, not inside it. ``EPSILON`` is what
  turns "exactly touching" into "not overlapping".
* Out-of-bounds tiles read as air, so the world edge never acts as a wall by
  accident; :func:`move_body` clamps the body into the world instead.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .. import config
from ..world.blocks import block_for
from ..world.world import World

EPSILON = 1e-6
"""Slack used to decide whether a tile boundary counts as touched."""

_STEP_INCREMENT = 0.05
"""Granularity of the step-up search: a quarter-tile ledge costs a quarter
tile of lift instead of a whole one."""


@dataclass
class Body:
    """A box that obeys gravity and the tile grid."""

    x: float
    """Left edge, in tiles."""

    y: float
    """Top edge, in tiles."""

    width: float
    height: float
    vx: float = 0.0
    vy: float = 0.0
    on_ground: bool = False
    """True when the last vertical move landed on something solid."""

    @property
    def right(self) -> float:
        """Right edge, in tiles."""
        return self.x + self.width

    @property
    def bottom(self) -> float:
        """Bottom edge (the feet), in tiles."""
        return self.y + self.height

    @property
    def center_x(self) -> float:
        """Horizontal centre, in tiles."""
        return self.x + self.width / 2

    @property
    def center_y(self) -> float:
        """Vertical centre, in tiles."""
        return self.y + self.height / 2

    @property
    def tile(self) -> tuple[int, int]:
        """The tile the body's centre is in."""
        return math.floor(self.center_x), math.floor(self.center_y)


def tile_bounds(x: float, y: float, width: float, height: float) -> tuple[int, int, int, int]:
    """Inclusive ``(left, top, right, bottom)`` tiles a rectangle covers."""
    return (
        math.floor(x + EPSILON),
        math.floor(y + EPSILON),
        math.floor(x + width - EPSILON),
        math.floor(y + height - EPSILON),
    )


def overlaps_solid(world: World, x: float, y: float, width: float, height: float) -> bool:
    """True when the rectangle ``(x, y, width, height)`` touches a solid tile."""
    left, top, right, bottom = tile_bounds(x, y, width, height)
    for tile_y in range(top, bottom + 1):
        for tile_x in range(left, right + 1):
            if block_for(world.get(tile_x, tile_y)).solid:
                return True
    return False


def is_grounded(world: World, body: Body) -> bool:
    """True when a solid tile sits directly under the body's feet.

    Used to give a freshly placed body a truthful ``on_ground``; after that
    :func:`move_body` keeps the flag up to date.
    """
    return _row_blocks(world, math.floor(body.bottom + EPSILON), body.x, body.width)


def move_body(world: World, body: Body, dt: float) -> None:
    """Advance *body* by one fixed step: gravity, then collision resolution.

    Gravity is applied here rather than by the caller so every moving body
    falls at the same rate and nobody can forget to.
    """
    body.vy = min(body.vy + config.GRAVITY * dt, config.TERMINAL_VELOCITY)
    # Horizontal first, and while ``on_ground`` still describes the previous
    # tick: step-up is only allowed for a body that was already standing.
    _move_horizontal(world, body, body.vx * dt)
    body.on_ground = False
    _move_vertical(world, body, body.vy * dt)


# -- horizontal ----------------------------------------------------------------


def _move_horizontal(world: World, body: Body, dx: float) -> None:
    """Move along x, climbing one-tile ledges and snapping against walls.

    ``body.vx`` is left untouched: it is the caller's intent, not physics
    state. Zeroing it on contact would mean a blocked move never gets retried
    and step-up would only ever get one chance at a ledge.
    """
    if dx == 0.0:
        return
    target = _clamp_x(world, body, body.x + dx)
    if not overlaps_solid(world, target, body.y, body.width, body.height):
        body.x = target
        return
    if _try_step_up(world, body, target):
        return
    body.x = _clamp_x(world, body, _snap_x(world, body, dx))


def _clamp_x(world: World, body: Body, x: float) -> float:
    """Keep the body inside the world horizontally."""
    return min(max(x, 0.0), world.width - body.width)


def _snap_x(world: World, body: Body, dx: float) -> float:
    """Position the body flush against the first blocking column."""
    current = math.floor(body.x + EPSILON)
    if dx > 0:
        target = math.floor(body.x + dx + body.width - EPSILON)
        for column in range(current, target + 1):
            if _column_blocks(world, column, body.y, body.height):
                return column - body.width
    else:
        target = math.floor(body.x + dx + EPSILON)
        for column in range(current, target - 1, -1):
            if _column_blocks(world, column, body.y, body.height):
                return column + 1.0
    return body.x


def _try_step_up(world: World, body: Body, target_x: float) -> bool:
    """Lift the body over a low ledge so walking does not need a jump.

    Only a grounded body steps up, only over :data:`config.STEP_UP_HEIGHT`,
    and only as far as it must - so a half-tile ledge costs half a tile of
    lift rather than a whole one.
    """
    if not body.on_ground:
        return False
    steps = round(config.STEP_UP_HEIGHT / _STEP_INCREMENT)
    for step in range(1, steps + 1):
        rise = step * _STEP_INCREMENT
        if not overlaps_solid(world, target_x, body.y - rise, body.width, body.height):
            body.y -= rise
            body.x = target_x
            body.on_ground = True
            return True
    return False


# -- vertical ------------------------------------------------------------------


def _move_vertical(world: World, body: Body, dy: float) -> None:
    """Move along y, landing on the floor or bumping the ceiling."""
    if dy > 0.0:
        _fall(world, body, dy)
    elif dy < 0.0:
        _rise(world, body, dy)


def _fall(world: World, body: Body, dy: float) -> None:
    """Move down, stopping with the feet on top of the first solid row."""
    lowest = world.height - body.height
    target = min(body.y + dy, lowest)
    if not overlaps_solid(world, body.x, target, body.width, body.height):
        body.y = target
        if target >= lowest:
            # Standing on the bottom of the world, which has no tiles below.
            body.vy = 0.0
            body.on_ground = True
        return
    top = math.floor(body.y + EPSILON)
    bottom = math.floor(target + body.height - EPSILON)
    for row in range(top, bottom + 1):
        if _row_blocks(world, row, body.x, body.width):
            body.y = row - body.height
            body.vy = 0.0
            body.on_ground = True
            return


def _rise(world: World, body: Body, dy: float) -> None:
    """Move up, stopping with the head just below the first solid row."""
    target = max(body.y + dy, 0.0)
    if not overlaps_solid(world, body.x, target, body.width, body.height):
        body.y = target
        if target <= 0.0:
            body.vy = 0.0
        return
    top = math.floor(body.y + EPSILON)
    target_top = math.floor(target + EPSILON)
    for row in range(top, target_top - 1, -1):
        if _row_blocks(world, row, body.x, body.width):
            body.y = float(row + 1)
            body.vy = 0.0
            return


# -- tile queries --------------------------------------------------------------


def _row_blocks(world: World, row: int, x: float, width: float) -> bool:
    """True when any tile of *row* under the body's x span is solid."""
    left = math.floor(x + EPSILON)
    right = math.floor(x + width - EPSILON)
    return any(block_for(world.get(column, row)).solid for column in range(left, right + 1))


def _column_blocks(world: World, column: int, y: float, height: float) -> bool:
    """True when any tile of *column* within the body's y span is solid."""
    top = math.floor(y + EPSILON)
    bottom = math.floor(y + height - EPSILON)
    return any(block_for(world.get(column, row)).solid for row in range(top, bottom + 1))
