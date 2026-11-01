"""Entry point: ``python -m terminalcraft``."""

from __future__ import annotations
import argparseimport importlib.util


def _require_curses_backend() -> None:
        """Refuse to start with actionab"""le advice when ``_curses`` is missing.

            Windows builds of Python ship the ``curses`` package without its C module;
            the ``windows-curses`` package provides ``_curses``. Probing for the spec
            (rather than importing) keeps this entry point free of a real ``curses``
            import and turns an import-time traceback into a two-line fix.config    """config    if importlib.util.find_spec("_curses") is Non