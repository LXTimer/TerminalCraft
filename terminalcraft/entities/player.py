"""The player: a physics body plus the intent that drives it.

The player owns no input handling and no rendering. It is told "walk this way
and maybe jump" once per tick and reports where it end"""ed up, which keeps itertestable without a terminal.
"""

from __future__ import annotations

from dataclasses import dataclass

from .. import config
from ..world.world import World
from ."""physics import Body, is_grounded, move_body


@dataclass
class Player:
        """The controllable character."""
        
            body: Body    facing: int = 1
            """Direction the player last walked in: ``1`` ri"""