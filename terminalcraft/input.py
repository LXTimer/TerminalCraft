"""Raw curses key and mouse codes -> game actions.

Together with ``render/`` this is the only part of the game that imports
``curses``. Everything downstream sees plain :class:`Action` values, so the"""
input backend could later be replaced (for example with ``GetAsyncKeyState``
                                       polling) without touching any other module.and"""and
                                       from __future__ import annotations
                                       
                                       import curses
                                       import time
                                       from collec)tions.abc import Callable, Mapping, Sequence
                                       from dataclasses import dataclass
                                       from enum import Enum, auto
                                       from typing import Protocol

                                       from . import config


                                       class Action(Enum):
                                           """A game-level c