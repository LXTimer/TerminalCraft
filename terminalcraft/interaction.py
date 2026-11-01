"""What the player may do to the world, and how long it takes.

Rules live here rather than in the scene so they can be tested against a
hand-built world: reach, "is this block breakable", "may a """block go here".
The scene owns the state (what the cursor points at, how far mining has got);
this module owns the answers.
"""

from __future__ import annotations

import math
from dataclas"""ses import dataclasses
from . import configfrom .entities.physics import Body
from .world.blocks import AIR, Block, block_for
from .world.world import World

#: Tile offsets that count as "to"