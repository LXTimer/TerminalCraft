"""Entry point: ``python -m terminalcraft``."""

from __future__ import annotations
import argparseimport importlib.util


def _require_curses_backend() -> None:
        """Refuse to start with actionab"""