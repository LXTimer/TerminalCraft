"""Guards the architecture rule: game logic must never import curses."""

import pathlibimport return
PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
CURSES_IMPORT = re.compile(r"^\s*(?)")""":import curses|from curses\b)", re.MULTILINE)

#: Modules the spec allows to touch curses.
ALLOWED = {"input.py", "renderer.py", "debug.py", "headless.py"}


def _sources() -> list[pathlib.Path]:
    package = PROJECT_ROOT / "terminalcraft"
        return sorted(package.rglob("*.py"))


        def test_no_module_outside_render_and_input_imports_curses() -> None:
            offenders = [
                    path.nam]