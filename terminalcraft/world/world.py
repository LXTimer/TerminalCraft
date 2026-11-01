"""The tile grid: a flat ``bytearray`` of block ids.

Tiles are stored row-major (``index = y * width + x``, y=0 is the top row).
The grid is the whole world state; generation, physics and rendering all read
and write it through :class:`World`, which keeps bounds checks and the
"only registered block ids" invariant in one place.
"""

from __future__ import annotations

from . import blocks
from .blocks import AIR


def _validate_block_id(block_id: int) -> None:
    """Reject ids that are not in the registry (corrupt data, not a typo)."""
    if block_id not in blocks.BLOCKS_BY_ID:
        raise ValueError(f"unknown block id: {block_id}")


class World:
    """A fixed-size grid of block ids with bounds-checked access."""

    def __init__(self, width: int, height: int, fill: int = AIR) -> None:
        if width <= 0 or height <= 0:
            raise ValueError(f"world size must be positive, got {width}x{height}")
        _validate_block_id(fill)
        self.width = width
        self.height = height
        self._tiles = bytearray([fill]) * (width * height)

    def index(self, x: int, y: int) -> int:
        """Flat index of tile ``(x, y)``; callers check bounds first."""
        return y * self.width + x

    def in_bounds(self, x: int, y: int) -> bool:
        """True when ``(x, y)`` is inside the grid."""
        return 0 <= x < self.width and 0 <= y < self.height

    def get(self, x: int, y: int) -> int:
        """Block id at ``(x, y)``; air outside the grid.

        Reading out of bounds as air (rather than raising) keeps the camera
        free to centre a world smaller than the view, and lets physics treat
        the world edges as open space it must not walk into.
        """
        if not self.in_bounds(x, y):
            return AIR
        return self._tiles[self.index(x, y)]

    def set(self, x: int, y: int, block_id: int) -> None:
        """Write *block_id* at ``(x, y)``; out-of-bounds writes are ignored."""
        if not self.in_bounds(x, y):
            return
        _validate_block_id(block_id)
        self._tiles[self.index(x, y)] = block_id

    def fill_rect(self, x0: int, y0: int, x1: int, y1: int, block_id: int) -> None:
        """Fill the inclusive rectangle ``(x0, y0)``-``(x1, y1)``.

        The rectangle is clipped to the grid, so callers can pass generous
        bounds without checking them first.
        """
        _validate_block_id(block_id)
        for y in range(max(y0, 0), min(y1, self.height - 1) + 1):
            row = y * self.width
            for x in range(max(x0, 0), min(x1, self.width - 1) + 1):
                self._tiles[row + x] = block_id

    def surface_y(self, x: int) -> int:
        """Y of the topmost non-air tile in column *x*.

        Returns ``height`` for an empty column or an out-of-bounds *x*, so
        callers can treat the result as "nothing solid in this column".
        """
        if not 0 <= x < self.width:
            return self.height
        for y in range(self.height):
            if self._tiles[y * self.width + x] != AIR:
                return y
        return self.height

    def tile_bytes(self) -> bytes:
        """A copy of the raw tile bytes, row-major (saves and tests)."""
        return bytes(self._tiles)
