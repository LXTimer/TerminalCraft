"""Raw curses key and mouse codes -> game actions.

Together with ``render/`` this is the only part of the game that imports
``curses``. Everything downstream sees plain :class:`Action` values, so the
input backend could later be replaced (for example with ``GetAsyncKeyState``
polling) without touching any other module.
"""

from __future__ import annotations

import ctypes
import curses
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from enum import Enum, auto
from typing import Protocol

from . import config


class Action(Enum):
    """A game-level command, independent of the physical key that triggered it."""

    MOVE_LEFT = auto()
    MOVE_RIGHT = auto()
    JUMP = auto()
    CURSOR_UP = auto()
    CURSOR_DOWN = auto()
    CURSOR_LEFT = auto()
    CURSOR_RIGHT = auto()
    MINE = auto()
    PLACE = auto()
    HOTBAR_1 = auto()
    HOTBAR_2 = auto()
    HOTBAR_3 = auto()
    HOTBAR_4 = auto()
    HOTBAR_5 = auto()
    HOTBAR_6 = auto()
    HOTBAR_7 = auto()
    HOTBAR_8 = auto()
    HOTBAR_9 = auto()
    INVENTORY = auto()
    CRAFTING = auto()
    PAUSE = auto()
    RESIZE = auto()
    QUIT = auto()


class MouseButton(Enum):
    """A mouse button that can be bound to an action.

    Only the two the game uses are listed; an unlisted button cannot be
    bound, which is what keeps ``config.MOUSE_BINDINGS`` honest.
    """

    LEFT = "left"
    RIGHT = "right"


@dataclass(frozen=True)
class MouseEvent:
    """One decoded mouse event.

    ``column``/``row`` are *screen cells*, not world tiles: only the renderer
    knows where the view is, so translation happens at the scene.
    """

    column: int
    row: int
    button: MouseButton
    pressed: bool


#: Button-state bits PDCurses uses, per button: (pressed, released, clicked).
#: A backend that cannot report the press and release separately reports the
#: whole click instead, which is treated as a press.
_BUTTON_MASKS: dict[MouseButton, tuple[int, int, int]] = {
    MouseButton.LEFT: (
        curses.BUTTON1_PRESSED,
        curses.BUTTON1_RELEASED,
        curses.BUTTON1_CLICKED,
    ),
    MouseButton.RIGHT: (
        curses.BUTTON3_PRESSED,
        curses.BUTTON3_RELEASED,
        curses.BUTTON3_CLICKED,
    ),
}


def _read_curses_mouse() -> tuple[int, int, int] | None:
    """Pop one queued mouse event from curses as ``(column, row, bstate)``.

    Only called after ``getch`` reported ``KEY_MOUSE``. Returns None when the
    backend has nothing queued, and swallows ``curses.error`` so a handler
    polled outside a curses session (headless, tests) stays harmless.
    """
    try:
        _mid, column, row, _z, bstate = curses.getmouse()
    except curses.error:
        return None
    return column, row, bstate


# Binding symbols that are not their own ordinal.
_SPECIAL_SYMBOLS: dict[str, int] = {
    "space": ord(" "),
    "esc": 27,  # ESC
    "up": curses.KEY_UP,
    "down": curses.KEY_DOWN,
    "left": curses.KEY_LEFT,
    "right": curses.KEY_RIGHT,
}

# Reverse map for debug output. Kept as plain data (rather than using
# ``curses.keyname``) so key names can be shown without initialising curses,
# which also keeps the naming deterministic in tests.
_CODE_NAMES: dict[int, str] = {
    ord(" "): "space",
    27: "esc",
    curses.KEY_UP: "up",
    curses.KEY_DOWN: "down",
    curses.KEY_LEFT: "left",
    curses.KEY_RIGHT: "right",
    curses.KEY_RESIZE: "KEY_RESIZE",
    curses.KEY_MOUSE: "mouse",
    curses.KEY_A2: "up (keypad)",
    curses.KEY_C2: "down (keypad)",
    curses.KEY_B1: "left (keypad)",
    curses.KEY_B3: "right (keypad)",
}

#: Arrow keys as delivered by PDCurses inside a pseudo-console.
#:
#: Windows Terminal and the VS Code integrated terminal host console
#: processes in ConPTY, and there PDCurses reports the arrow keys as the
#: matching numeric-keypad codes instead of the ``KEY_UP``/``KEY_LEFT``/...
#: constants: up arrives as ``KEY_A2`` (keypad 8), down as ``KEY_C2``
#: (keypad 2), left as ``KEY_B1`` (keypad 4) and right as ``KEY_B3``
#: (keypad 6). Without these aliases the cursor keys silently do nothing in
#: those terminals. See microsoft/vscode#112405 for the original report.
_KEYPAD_ARROWS: dict[int, Action] = {
    curses.KEY_A2: Action.CURSOR_UP,
    curses.KEY_C2: Action.CURSOR_DOWN,
    curses.KEY_B1: Action.CURSOR_LEFT,
    curses.KEY_B3: Action.CURSOR_RIGHT,
}


def symbol_to_code(symbol: str) -> int:
    """Resolve a key-binding symbol to the raw key code a terminal sends.

    Single characters map to their ordinal (``"a"`` -> ``97``); named symbols
    (``"space"``, ``"esc"``, ``"up"``, ...) map to the matching curses key
    constant. Raises :class:`ValueError` for unknown symbols so a typo in
    ``config.KEY_BINDINGS`` fails loudly at startup.
    """
    special = _SPECIAL_SYMBOLS.get(symbol)
    if special is not None:
        return special
    if len(symbol) == 1:
        return ord(symbol)
    raise ValueError(f"unknown key symbol: {symbol!r}")


def describe_key(key: int | None) -> str:
    """Human-readable name for a raw key code, used by debug screens.

    Printable ASCII shows as the character, known special keys as their
    binding symbol, anything else as ``key <code>``.
    """
    if key is None:
        return "(none)"
    name = _CODE_NAMES.get(key)
    if name is None and 33 <= key <= 126:
        name = chr(key)
    if name is None:
        return f"key {key}"
    return f"{name} ({key})"


#: Virtual-key codes for the named symbols. Letters and digits are their
#: uppercase ordinal, which happens to be the VK code for that key.
_VK_SYMBOLS: dict[str, int] = {
    "space": 0x20,
    "esc": 0x1B,
    "up": 0x26,
    "down": 0x28,
    "left": 0x25,
    "right": 0x27,
}


def windows_key_state(symbol: str) -> bool:
    """Whether the physical key for *symbol* is down right now.

    ``GetAsyncKeyState`` reads the keyboard itself instead of the console's
    key events, so it keeps reporting "down" through the OS repeat delay -
    the 250-1000 ms between pressing a key and its first repeat event, which
    an event window alone reads as a release. False off Windows, and for any
    symbol without a virtual-key code.
    """
    if sys.platform != "win32" or not hasattr(ctypes, "windll"):
        return False
    code = ord(symbol.upper()) if len(symbol) == 1 else _VK_SYMBOLS.get(symbol)
    if code is None:
        return False
    return bool(ctypes.windll.user32.GetAsyncKeyState(code) & 0x8000)


class KeySource(Protocol):
    """The only window method :class:`InputHandler` needs."""

    def getch(self) -> int:
        ...


class InputHandler:
    """Maps raw key codes and mouse buttons to actions, remembering the last one.

    The handler is deliberately passive: :meth:`dispatch` translates one key
    code, :meth:`dispatch_mouse` one mouse event, and :meth:`poll` drains
    whatever the terminal currently has queued. Keeping the mapping here means
    the game loop never sees a key code, and a future polling-based backend
    only has to reimplement these methods.

    Curses reports key *events*, never key state, so "is this key held?" is
    reconstructed from the time of the last event for that action: an action
    stays held for :data:`~terminalcraft.config.HOLD_WINDOW_SECONDS` after it
    was last seen, which the OS key-repeat keeps refreshing while the key is
    down. A mouse button needs no such guess - the release is a real event -
    so a held button is tracked as state instead. :meth:`is_held` answers for
    continuous input (walking, mining) and :meth:`take_press` for the press
    edge (jumping, placing), which fires once per press no matter how often
    the scene asks.
    """

    def __init__(
        self,
        bindings: Mapping[str, Sequence[str]] | None = None,
        *,
        mouse_bindings: Mapping[str, str] | None = None,
        clock: Callable[[], float] | None = None,
        mouse_reader: Callable[[], tuple[int, int, int] | None] | None = None,
        key_state: Callable[[str], bool] | None = None,
    ) -> None:
        self._code_to_action, self._action_symbols = self._build_lookup(
            config.KEY_BINDINGS if bindings is None else bindings
        )
        self._button_to_action = self._build_mouse_lookup(
            config.MOUSE_BINDINGS if mouse_bindings is None else mouse_bindings
        )
        self._clock = clock if clock is not None else time.monotonic
        self._mouse_reader = _read_curses_mouse if mouse_reader is None else mouse_reader
        #: Real key state, or None to trust the event window alone. The
        #: application passes :func:`windows_key_state`; tests and the
        #: headless harness leave it off so a held key on the developer's
        #: keyboard can never leak into a run.
        self._key_state = key_state
        self._held: dict[Action, float] = {}
        self._fresh: set[Action] = set()
        self._mouse_down: set[Action] = set()
        self._mouse_presses: list[MouseEvent] = []
        #: ``None`` until :meth:`enable_mouse` is called, then whether the
        #: terminal agreed to report mouse events (shown by debug screens).
        self.mouse_enabled: bool | None = None
        self.last_key: int | None = None
        self.last_action: Action | None = None

    @staticmethod
    def _build_lookup(
        bindings: Mapping[str, Sequence[str]],
    ) -> tuple[dict[int, Action], dict[Action, tuple[str, ...]]]:
        """Build the key-code -> action table, plus each action's symbols.

        The symbols are kept per action so a real key-state probe can ask
        "is any key bound to this action down?" without re-reading config.
        """
        lookup: dict[int, Action] = {curses.KEY_RESIZE: Action.RESIZE}
        symbols: dict[Action, tuple[str, ...]] = {}
        for action_name, bound_symbols in bindings.items():
            try:
                action = Action[action_name.upper()]
            except KeyError:
                raise ValueError(f"key binding for unknown action: {action_name!r}") from None
            symbols[action] = tuple(bound_symbols)
            for symbol in bound_symbols:
                code = symbol_to_code(symbol)
                if code in lookup:
                    raise ValueError(
                        f"key {symbol!r} ({code}) is bound to both "
                        f"{lookup[code].name} and {action_name}"
                    )
                lookup[code] = action
        # Keypad arrow aliases go in last (setdefault, not assignment) so an
        # explicit binding on one of those codes always wins.
        for code, action in _KEYPAD_ARROWS.items():
            lookup.setdefault(code, action)
        return lookup, symbols

    @staticmethod
    def _build_mouse_lookup(bindings: Mapping[str, str]) -> dict[MouseButton, Action]:
        """Build a button -> action table, rejecting unknown names."""
        lookup: dict[MouseButton, Action] = {}
        for action_name, button_name in bindings.items():
            try:
                action = Action[action_name.upper()]
            except KeyError:
                raise ValueError(
                    f"mouse binding for unknown action: {action_name!r}"
                ) from None
            try:
                button = MouseButton(button_name)
            except ValueError:
                raise ValueError(
                    f"mouse binding for unknown button: {button_name!r}"
                ) from None
            if button in lookup:
                raise ValueError(
                    f"mouse button {button_name!r} is bound to both "
                    f"{lookup[button].name} and {action_name}"
                )
            lookup[button] = action
        return lookup

    def dispatch(self, key: int) -> Action | None:
        """Translate one raw key code, recording it as the last key seen."""
        action = self._code_to_action.get(key)
        self.last_key = key
        self.last_action = action
        if action is not None:
            self._note(action)
        return action

    def dispatch_mouse(self, event: MouseEvent) -> Action | None:
        """Translate one decoded mouse event, recording it as the last input.

        A press starts the action exactly like a key press does, so the scene
        cannot tell the two apart; a release ends it. Unbound buttons are
        still recorded, mirroring how unbound keys behave.
        """
        action = self._button_to_action.get(event.button)
        self.last_key = curses.KEY_MOUSE
        self.last_action = action
        if action is None:
            return None
        if event.pressed:
            self._note(action)
            self._mouse_down.add(action)
            self._mouse_presses.append(event)
        else:
            self._release(action)
        return action

    def poll(self, source: KeySource) -> list[Action]:
        """Drain all queued input from *source* and return its actions.

        Unmapped keys are still recorded (``last_key``/``last_action``) but
        produce no action.
        """
        actions: list[Action] = []
        while True:
            key = source.getch()
            if key == -1:  # curses.ERR: nothing queued
                return actions
            if key == curses.KEY_MOUSE:
                event = self.read_mouse_event()
                if event is not None:
                    action = self.dispatch_mouse(event)
                    if action is not None:
                        actions.append(action)
                continue
            action = self.dispatch(key)
            if action is not None:
                actions.append(action)

    def read_mouse_event(self) -> MouseEvent | None:
        """Pop one mouse event from the backend and decode its button."""
        raw = self._mouse_reader()
        if raw is None:
            return None
        column, row, bstate = raw
        for button, (pressed, released, clicked) in _BUTTON_MASKS.items():
            if bstate & pressed or bstate & clicked:
                return MouseEvent(column, row, button, True)
            if bstate & released:
                return MouseEvent(column, row, button, False)
        return None

    def take_mouse_presses(self) -> list[MouseEvent]:
        """Button presses since the last call, oldest first.

        The scene needs the cell a press landed on to aim the cursor, which
        an :class:`Action` cannot carry. Only presses are queued: a release
        has nothing to aim at.
        """
        presses, self._mouse_presses = self._mouse_presses, []
        return presses

    def cancel_mouse_action(self, button: MouseButton) -> None:
        """Forget a press the scene decided not to use.

        Used when a click misses the world (it landed on the HUD): the action
        was already dispatched by the time the scene could judge the cell, so
        dropping the hold and the press edge here is what keeps such a click
        from mining or placing at the old cursor. A key held at the same time
        re-arms on its next repeat.
        """
        action = self._button_to_action.get(button)
        if action is not None and action in self._mouse_down:
            self._release(action)

    def enable_mouse(self) -> bool:
        """Ask the terminal to report mouse events; False when it will not.

        ``windows-curses`` 2.4.x replays the console input mode captured at
        ``initscr`` whenever ``reset_prog_mode`` runs, which silently drops
        the mouse mode again; ``def_prog_mode`` re-captures it here so the
        setting survives. ``mouseinterval(0)`` skips the click-versus-double-
        click delay, so a press reaches the game immediately.
        """
        try:
            available, _old = curses.mousemask(curses.ALL_MOUSE_EVENTS)
            curses.def_prog_mode()
            curses.mouseinterval(0)
        except curses.error:
            self.mouse_enabled = False
            return False
        self.mouse_enabled = bool(available)
        return self.mouse_enabled

    def disable_mouse(self) -> None:
        """Stop mouse reporting again.

        Enabling mouse input also turns off the console's QuickEdit mode, so
        leaving it on after the game exits would break text selection in the
        user's terminal. Re-capturing the program mode makes the cleanup
        survive the restore ``curses`` performs on the way out.
        """
        if self.mouse_enabled is None:
            return
        try:
            curses.mousemask(0)
            curses.def_prog_mode()
        except curses.error:
            return
        self.mouse_enabled = False

    # -- held-state emulation ----------------------------------------------

    def _note(self, action: Action) -> None:
        """Record an input event for *action* and detect the press edge."""
        now = self._clock()
        if not self._held_at(action, now):
            self._fresh.add(action)
        self._held[action] = now

    def _release(self, action: Action) -> None:
        """End the held state a mouse release ends.

        The time window is dropped too: it exists to stand in for key state
        the terminal never reports, while a mouse button *does* report its
        release, so keeping the window open would make mining run on for
        another :data:`~terminalcraft.config.HOLD_WINDOW_SECONDS` after the
        button came back up.
        """
        self._mouse_down.discard(action)
        self._fresh.discard(action)
        self._held.pop(action, None)

    def _held_at(self, action: Action, now: float) -> bool:
        last_seen = self._held.get(action)
        if last_seen is None or now - last_seen > config.HOLD_WINDOW_SECONDS:
            # The window is over, so the key is up: forget the press. Dropping
            # it keeps a stale entry from being re-armed by real key state
            # before the next press event arrives.
            self._held.pop(action, None)
            return False
        return True

    def _key_down(self, action: Action) -> bool:
        """Whether any physical key bound to *action* is down right now."""
        if self._key_state is None:
            return False
        return any(self._key_state(symbol) for symbol in self._action_symbols.get(action, ()))

    def _is_held_at(self, action: Action, now: float) -> bool:
        """Held by either input path: a live key window or a pressed button."""
        return action in self._mouse_down or self._held_at(action, now)

    def is_held(self, action: Action) -> bool:
        """True while *action* is considered held down.

        Real key state only *extends* a press that a key event already
        started: the OS waits 250-1000 ms before its first repeat, and an
        event window alone reads that gap as a release. The event still owns
        the press edge, so probing the keyboard can never invent a press.
        """
        now = self._clock()
        if action in self._held and self._key_down(action):
            self._held[action] = now
        return self._is_held_at(action, now)

    def take_press(self, action: Action) -> bool:
        """True once per press: consuming it makes later calls return False.

        A scene calls this every tick for one-shot actions, so the press has
        to be consumed rather than merely observed.
        """
        if not self.is_held(action) or action not in self._fresh:
            return False
        self._fresh.discard(action)
        return True

    def held_actions(self) -> list[Action]:
        """Every action currently held, in a stable order (debug output)."""
        now = self._clock()
        return [action for action in Action if self._is_held_at(action, now)]
