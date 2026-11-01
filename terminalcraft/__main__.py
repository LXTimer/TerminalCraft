"""Entry point: ``python -m terminalcraft``."""

from __future__ import annotations

import argparse
import importlib.util


def _require_curses_backend() -> None:
    """Refuse to start with actionable advice when ``_curses`` is missing.

    Windows builds of Python ship the ``curses`` package without its C module;
    the ``windows-curses`` package provides ``_curses``. Probing for the spec
    (rather than importing) keeps this entry point free of a real ``curses``
    import and turns an import-time traceback into a two-line fix.
    """
    if importlib.util.find_spec("_curses") is None:
        raise SystemExit(
            "error: the curses C module (_curses) is not available.\n"
            "  Windows Python needs:  python -m pip install windows-curses\n"
            "  Python 3.15 has no windows-curses wheel yet - use Python 3.11-3.14,\n"
            "  for example:  py -3.11 -m terminalcraft"
        )


def main(argv: list[str] | None = None) -> int:
    """Parse arguments and either run the game or the headless harness."""
    _require_curses_backend()
    # Imported lazily so the backend check above can explain a missing
    # windows-curses before the curses import chain (input.py, render/) runs.
    from .game import run_game
    from .render import headless
    from .render.renderer import run_with_curses

    parser = argparse.ArgumentParser(
        prog="terminalcraft",
        description="TerminalCraft: a 2D side-view sandbox for the terminal.",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="run a scripted, terminal-free smoke test and print the captured screen",
    )
    parser.add_argument(
        "--keys",
        default="",
        help="comma-separated keys to feed in headless mode (e.g. 'a,j,q')",
    )
    parser.add_argument(
        "--ticks",
        type=int,
        default=3,
        help="number of ticks to simulate in headless mode (default: 3)",
    )
    args = parser.parse_args(argv)

    if args.headless:
        print(headless.run_from_symbols(args.keys, ticks=args.ticks))
    else:
        run_with_curses(run_game)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
