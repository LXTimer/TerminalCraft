"""Guards the architecture rule: game logic must never import curses."""

import pathlib
import re

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
CURSES_IMPORT = re.compile(r"^\s*(?:import curses|from curses\b)", re.MULTILINE)

#: Modules the spec allows to touch curses.
ALLOWED = {"input.py", "renderer.py", "debug.py", "headless.py"}


def _sources() -> list[pathlib.Path]:
    package = PROJECT_ROOT / "terminalcraft"
    return sorted(package.rglob("*.py"))


def test_no_module_outside_render_and_input_imports_curses() -> None:
    offenders = [
        path.name
        for path in _sources()
        if path.name not in ALLOWED and CURSES_IMPORT.search(path.read_text(encoding="utf-8"))
    ]
    assert offenders == []


def test_render_and_input_do_import_curses() -> None:
    # The rule is two-sided: the allowed modules really do own curses.
    for name in ("input.py", "render/renderer.py"):
        source = (PROJECT_ROOT / "terminalcraft" / name).read_text(encoding="utf-8")
        assert CURSES_IMPORT.search(source), f"{name} should import curses"
