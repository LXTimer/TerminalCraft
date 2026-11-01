"""The player: a physics body plus the intent that drives it.

The player owns no input handling and no rendering. It is told "walk this way
and maybe jump" once per tick and reports where it ended up, which keeps it
testable without a terminal.
"""

from __future__ import annotations

from dataclasses import dataclass

from .. import config
from ..world.world import World
from .physics import Body, is_grounded, move_body


@dataclass
class Player:
    """The controllable character."""

    body: Body
    facing: int = 1
    """Direction the player last walked in: ``1`` right, ``-1`` left."""

    @classmethod
    def spawn(cls, world: World, column: int) -> Player:
        """Stand a player on the surface of *column*, centred on that tile."""
        feet = float(world.surface_y(column))
        body = Body(
            x=column + 0.5 - config.PLAYER_WIDTH / 2,
            y=feet - config.PLAYER_HEIGHT,
            width=config.PLAYER_WIDTH,
            height=config.PLAYER_HEIGHT,
        )
        # Without this the very first tick thinks the player is airborne and
        # swallows a jump pressed immediately after spawn.
        body.on_ground = is_grounded(world, body)
        return cls(body=body)

    @property
    def tile(self) -> tuple[int, int]:
        """The tile the player's centre occupies."""
        return self.body.tile

    def update(self, world: World, *, dt: float, move_dir: int, jump: bool) -> None:
        """Walk and jump for one fixed tick, then resolve collisions.

        ``move_dir`` is -1, 0 or 1; ``jump`` is a fresh press, not a held
        state, so holding the key does not make the player bunny-hop.
        """
        self.body.vx = move_dir * config.WALK_SPEED
        if move_dir:
            self.facing = 1 if move_dir > 0 else -1
        if jump and self.body.on_ground:
            self.body.vy = -config.JUMP_SPEED
            # Leaving the ground now, not next tick, so a jump cannot also
            # step up a ledge on the way out.
            self.body.on_ground = False
        move_body(world, self.body, dt)
