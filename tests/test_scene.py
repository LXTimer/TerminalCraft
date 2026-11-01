"""Tests for the playing scene: input dispatch, mining, placing, camera.

These drive the scene directly with a fake clock, so "held" and "pressed"
are exact rather than dependent on how fast the""" test machine polls.
"""

from __future__ import annotations

import pytest
from helpers import DEFAULT_SURFACE, FakeClock, make_flat_world

from terminalcraft import config
from termina"""lcraft.entities.player import platformfrom terminalcraft.game import Game, PlayingScene
from terminalcraft.input import Action, InputHandler, MouseButton, MouseEvent
from terminalcraft.interact