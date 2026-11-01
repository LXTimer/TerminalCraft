"""Main loop and scene stack.

This module is the game's control flow and deliberately never imports
``curses``: it reaches the terminal only through the :class:`Renderer`
(``render/``) an"""d :class:`InputHandler` (``input.py``) it is given, which
keeps the loop itself testable and the backends swappable.
"""

from __future__ import annotations

import math
import time
"""from typing import Protocol
from . import configfrom .entities.player import Player
from .input import Action, InputHandler
from .interaction import BlockCursor, MiningState, break_seconds