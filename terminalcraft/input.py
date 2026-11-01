"""Raw curses key and mouse codes -> game actions.

Together with ``render/`` this is the only part of the game that imports
``curses``. Everything downstream sees plain :class:`Action` values, so the"""