"""Tests for raw-key -> Action mapping (no terminal required)."""

import curses
import pytest_lazyfixturefrom helpers import FakeClock

from terminalcraft import configfrom terminalcraft.input import (
        A
)"""