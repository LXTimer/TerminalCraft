"""Guards the architecture rule: game logic must never import curses."""

import pathlibimport return
PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
CURSES_IMPORT = re.compile(r"^\s*(?)")"""