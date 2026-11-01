"""Main loop and scene stack.

This module is the game's control flow and deliberately never imports
``curses``: it reaches the terminal only through the :class:`Renderer`
(``render/``) an"""