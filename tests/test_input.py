"""Tests for raw-key -> Action mapping (no terminal required)."""

import curses

import pytest
from helpers import FakeClock

from terminalcraft import config
from terminalcraft.input import (
    Action,
    InputHandler,
    MouseButton,
    MouseEvent,
    describe_key,
    symbol_to_code,
)


@pytest.fixture
def handler() -> InputHandler:
    return InputHandler()


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def timed(clock: FakeClock) -> InputHandler:
    """A handler whose sense of time the test controls."""
    return InputHandler(clock=clock)


class TestDefaultBindings:
    @pytest.mark.parametrize(
        ("key", "expected"),
        [
            (ord("a"), Action.MOVE_LEFT),
            (ord("d"), Action.MOVE_RIGHT),
            (ord("w"), Action.JUMP),
            (ord(" "), Action.JUMP),
            (curses.KEY_UP, Action.CURSOR_UP),
            (curses.KEY_DOWN, Action.CURSOR_DOWN),
            (curses.KEY_LEFT, Action.CURSOR_LEFT),
            (curses.KEY_RIGHT, Action.CURSOR_RIGHT),
            (ord("j"), Action.MINE),
            (ord("k"), Action.PLACE),
            (ord("1"), Action.HOTBAR_1),
            (ord("5"), Action.HOTBAR_5),
            (ord("9"), Action.HOTBAR_9),
            (ord("e"), Action.INVENTORY),
            (ord("c"), Action.CRAFTING),
            (27, Action.PAUSE),
            (ord("q"), Action.QUIT),
            (curses.KEY_RESIZE, Action.RESIZE),
        ],
    )
    def test_default_binding(self, handler: InputHandler, key: int, expected: Action) -> None:
        assert handler.dispatch(key) is expected

    def test_unbound_key_maps_to_nothing(self, handler: InputHandler) -> None:
        assert handler.dispatch(ord("z")) is None

    def test_last_key_and_action_are_recorded(self, handler: InputHandler) -> None:
        assert handler.last_key is None
        assert handler.last_action is None
        handler.dispatch(ord("a"))
        assert handler.last_key == ord("a")
        assert handler.last_action is Action.MOVE_LEFT

    def test_last_key_records_unbound_keys_too(self, handler: InputHandler) -> None:
        handler.dispatch(ord("z"))
        assert handler.last_key == ord("z")
        assert handler.last_action is None


class TestSymbolToCode:
    @pytest.mark.parametrize(
        ("symbol", "expected"),
        [
            ("a", ord("a")),
            ("Z", ord("Z")),
            ("1", ord("1")),
            ("space", ord(" ")),
            ("esc", 27),
            ("up", curses.KEY_UP),
            ("down", curses.KEY_DOWN),
            ("left", curses.KEY_LEFT),
            ("right", curses.KEY_RIGHT),
        ],
    )
    def test_known_symbols(self, symbol: str, expected: int) -> None:
        assert symbol_to_code(symbol) == expected

    def test_unknown_symbol_raises(self) -> None:
        with pytest.raises(ValueError):
            symbol_to_code("hyper")


class TestCustomBindings:
    def test_rebinding_replaces_defaults(self) -> None:
        handler = InputHandler({"move_left": ("left",)})
        assert handler.dispatch(curses.KEY_LEFT) is Action.MOVE_LEFT
        assert handler.dispatch(ord("a")) is None

    def test_duplicate_binding_is_rejected(self) -> None:
        with pytest.raises(ValueError):
            InputHandler({"move_left": ("a",), "move_right": ("a",)})

    def test_unknown_action_name_is_rejected(self) -> None:
        with pytest.raises(ValueError):
            InputHandler({"fly": ("f",)})


class TestKeypadArrowAliases:
    """Pseudo-console terminals deliver arrows as keypad codes.

    Windows Terminal and the VS Code integrated terminal host console
    processes in ConPTY, where PDCurses reports the arrow keys as the
    numeric-keypad codes (microsoft/vscode#112405). The aliases must map
    them onto the same actions as the real arrow keys.
    """

    @pytest.mark.parametrize(
        ("key", "expected"),
        [
            (curses.KEY_A2, Action.CURSOR_UP),
            (curses.KEY_C2, Action.CURSOR_DOWN),
            (curses.KEY_B1, Action.CURSOR_LEFT),
            (curses.KEY_B3, Action.CURSOR_RIGHT),
        ],
    )
    def test_keypad_codes_map_to_cursor_actions(
        self, handler: InputHandler, key: int, expected: Action
    ) -> None:
        assert handler.dispatch(key) is expected

    def test_keypad_codes_are_recorded_as_last_key(self, handler: InputHandler) -> None:
        handler.dispatch(curses.KEY_B1)
        assert handler.last_key == curses.KEY_B1
        assert handler.last_action is Action.CURSOR_LEFT

    def test_real_arrow_codes_are_not_displaced(self, handler: InputHandler) -> None:
        # Both delivery paths must work side by side.
        assert handler.dispatch(curses.KEY_LEFT) is Action.CURSOR_LEFT
        assert handler.dispatch(curses.KEY_B1) is Action.CURSOR_LEFT
        assert handler.dispatch(curses.KEY_UP) is Action.CURSOR_UP
        assert handler.dispatch(curses.KEY_A2) is Action.CURSOR_UP

    def test_describe_key_names_the_keypad_codes(self) -> None:
        assert describe_key(curses.KEY_A2) == f"up (keypad) ({curses.KEY_A2})"
        assert describe_key(curses.KEY_B1) == f"left (keypad) ({curses.KEY_B1})"


class TestHeldKeys:
    """Curses reports key events, not key state, so "held" is emulated.

    An action counts as held for a short window after its last key event;
    the OS key repeat keeps refreshing that window while the key is down.
    """

    def test_an_action_is_held_right_after_a_press(self, timed: InputHandler) -> None:
        timed.dispatch(ord("d"))
        assert timed.is_held(Action.MOVE_RIGHT)

    def test_the_window_lasts_exactly_its_length(self, timed: InputHandler, clock: FakeClock) -> None:
        timed.dispatch(ord("d"))
        clock.advance(config.HOLD_WINDOW_SECONDS)
        assert timed.is_held(Action.MOVE_RIGHT)

    def test_the_window_expires(self, timed: InputHandler, clock: FakeClock) -> None:
        timed.dispatch(ord("d"))
        clock.advance(config.HOLD_WINDOW_SECONDS + 0.001)
        assert not timed.is_held(Action.MOVE_RIGHT)

    def test_key_repeat_extends_the_window(self, timed: InputHandler, clock: FakeClock) -> None:
        timed.dispatch(ord("d"))
        clock.advance(config.HOLD_WINDOW_SECONDS * 0.9)
        timed.dispatch(ord("d"))  # the terminal's repeat
        clock.advance(config.HOLD_WINDOW_SECONDS * 0.9)
        assert timed.is_held(Action.MOVE_RIGHT)

    def test_other_actions_are_not_held(self, timed: InputHandler) -> None:
        timed.dispatch(ord("d"))
        assert not timed.is_held(Action.MOVE_LEFT)

    def test_nothing_is_held_before_any_input(self, handler: InputHandler) -> None:
        assert not handler.is_held(Action.MOVE_RIGHT)

    def test_held_actions_lists_only_the_live_ones(
        self, timed: InputHandler, clock: FakeClock
    ) -> None:
        timed.dispatch(ord("a"))
        timed.dispatch(ord("d"))
        clock.advance(config.HOLD_WINDOW_SECONDS + 0.001)
        timed.dispatch(ord("d"))
        assert timed.held_actions() == [Action.MOVE_RIGHT]

    def test_the_default_clock_is_real_time(self, handler: InputHandler) -> None:
        handler.dispatch(ord("d"))
        assert handler.is_held(Action.MOVE_RIGHT)


class TestPressEdge:
    """One-shot actions fire once per press, not once per tick."""

    def test_a_press_is_reported_once(self, timed: InputHandler) -> None:
        timed.dispatch(ord("k"))
        assert timed.take_press(Action.PLACE)
        assert not timed.take_press(Action.PLACE)

    def test_a_held_key_does_not_press_again(self, timed: InputHandler) -> None:
        timed.dispatch(ord("k"))
        assert timed.take_press(Action.PLACE)
        timed.dispatch(ord("k"))  # the terminal's repeat, still one press
        assert not timed.take_press(Action.PLACE)

    def test_releasing_and_pressing_again_presses_again(
        self, timed: InputHandler, clock: FakeClock
    ) -> None:
        timed.dispatch(ord("k"))
        assert timed.take_press(Action.PLACE)
        clock.advance(config.HOLD_WINDOW_SECONDS + 0.001)
        timed.dispatch(ord("k"))
        assert timed.take_press(Action.PLACE)

    def test_an_expired_press_is_not_reported(self, timed: InputHandler, clock: FakeClock) -> None:
        timed.dispatch(ord("k"))
        clock.advance(config.HOLD_WINDOW_SECONDS + 0.001)
        assert not timed.take_press(Action.PLACE)

    def test_nothing_to_take_before_any_input(self, handler: InputHandler) -> None:
        assert not handler.take_press(Action.PLACE)


class TestRealKeyState:
    """The keyboard itself bridges the OS repeat delay.

    Windows waits 250-1000 ms before the first repeat event, which a pure
    event window reads as a release - so a held key stutters to a stop and
    then resumes. A real key-state probe keeps the window open through that
    gap. It may only *extend* a press an event started, never start one.
    """

    @staticmethod
    def handler(down: set[str], clock: FakeClock) -> InputHandler:
        return InputHandler(clock=clock, key_state=lambda symbol: symbol in down)

    def test_a_held_key_survives_the_repeat_gap(self, clock: FakeClock) -> None:
        handler = self.handler({"d"}, clock)
        handler.dispatch(ord("d"))
        clock.advance(1.0)  # past the window, before the first repeat arrives
        assert handler.is_held(Action.MOVE_RIGHT)

    def test_the_hold_ends_when_the_key_comes_up(self, clock: FakeClock) -> None:
        down = {"d"}
        handler = self.handler(down, clock)
        handler.dispatch(ord("d"))
        down.clear()
        clock.advance(config.HOLD_WINDOW_SECONDS + 0.001)
        assert not handler.is_held(Action.MOVE_RIGHT)

    def test_key_state_cannot_start_a_press_on_its_own(self, clock: FakeClock) -> None:
        handler = self.handler({"d", "k"}, clock)
        assert not handler.is_held(Action.MOVE_RIGHT)
        assert not handler.take_press(Action.PLACE)

    def test_the_press_edge_still_comes_from_the_event(self, clock: FakeClock) -> None:
        handler = self.handler({"w"}, clock)
        handler.dispatch(ord("w"))
        assert handler.take_press(Action.JUMP)

    def test_a_repeat_after_the_gap_is_not_a_second_place(self, clock: FakeClock) -> None:
        handler = self.handler({"k"}, clock)
        handler.dispatch(ord("k"))
        assert handler.take_press(Action.PLACE)
        clock.advance(1.0)
        assert handler.is_held(Action.PLACE)  # kept alive by real key state
        handler.dispatch(ord("k"))  # the first repeat event
        assert not handler.take_press(Action.PLACE)


class TestMouseBindings:
    """The mouse buttons are *extra* bindings for mine and place.

    Nothing is remapped: the keyboard bindings keep working exactly as
    before, and both devices drive the same action state.
    """

    @staticmethod
    def click(
        column: int = 10,
        row: int = 5,
        button: MouseButton = MouseButton.LEFT,
        pressed: bool = True,
    ) -> MouseEvent:
        return MouseEvent(column, row, button, pressed)

    def test_left_button_mines(self, handler: InputHandler) -> None:
        assert handler.dispatch_mouse(self.click(button=MouseButton.LEFT)) is Action.MINE

    def test_right_button_places(self, handler: InputHandler) -> None:
        assert handler.dispatch_mouse(self.click(button=MouseButton.RIGHT)) is Action.PLACE

    def test_the_keyboard_bindings_are_untouched(self, handler: InputHandler) -> None:
        assert handler.dispatch(ord("j")) is Action.MINE
        assert handler.dispatch(ord("k")) is Action.PLACE

    def test_a_button_holds_the_same_action_a_key_does(
        self, timed: InputHandler, clock: FakeClock
    ) -> None:
        timed.dispatch_mouse(self.click(pressed=True))
        # Unlike a key, a button needs no repeat to stay held: its release is
        # a real event, so the hold must outlive the key window.
        clock.advance(config.HOLD_WINDOW_SECONDS * 10)
        assert timed.is_held(Action.MINE)

    def test_releasing_the_button_ends_the_hold_immediately(
        self, timed: InputHandler
    ) -> None:
        timed.dispatch_mouse(self.click(pressed=True))
        timed.dispatch_mouse(self.click(pressed=False))
        assert not timed.is_held(Action.MINE)

    def test_a_released_button_does_not_resurrect_from_the_key_window(
        self, timed: InputHandler
    ) -> None:
        timed.dispatch_mouse(self.click(pressed=True))
        timed.dispatch_mouse(self.click(pressed=False))
        assert not timed.is_held(Action.MINE)
        assert timed.held_actions() == []

    def test_one_place_per_click(self, timed: InputHandler) -> None:
        timed.dispatch_mouse(self.click(button=MouseButton.RIGHT, pressed=True))
        assert timed.take_press(Action.PLACE)
        assert not timed.take_press(Action.PLACE)
        timed.dispatch_mouse(self.click(button=MouseButton.RIGHT, pressed=False))
        assert not timed.take_press(Action.PLACE)

    def test_a_press_is_queued_with_the_cell_it_landed_on(self, handler: InputHandler) -> None:
        handler.dispatch_mouse(self.click(column=42, row=7))
        presses = handler.take_mouse_presses()
        assert [(press.column, press.row) for press in presses] == [(42, 7)]
        assert handler.take_mouse_presses() == []

    def test_a_release_is_not_queued(self, handler: InputHandler) -> None:
        handler.dispatch_mouse(self.click(column=42, row=7, pressed=False))
        assert handler.take_mouse_presses() == []

    def test_the_mouse_is_recorded_as_the_last_input(self, handler: InputHandler) -> None:
        handler.dispatch_mouse(self.click())
        assert handler.last_key == curses.KEY_MOUSE
        assert handler.last_action is Action.MINE

    def test_an_unbound_button_does_nothing(self) -> None:
        handler = InputHandler(mouse_bindings={"mine": "left"})
        assert handler.dispatch_mouse(self.click(button=MouseButton.RIGHT)) is None

    def test_an_unknown_button_is_rejected(self) -> None:
        with pytest.raises(ValueError):
            InputHandler(mouse_bindings={"mine": "thumb"})

    def test_an_unknown_action_is_rejected(self) -> None:
        with pytest.raises(ValueError):
            InputHandler(mouse_bindings={"fly": "left"})

    def test_two_actions_cannot_share_a_button(self) -> None:
        with pytest.raises(ValueError):
            InputHandler(mouse_bindings={"mine": "left", "place": "left"})


class _Keys:
    """Minimal KeySource: yields scripted codes, then ERR forever."""

    def __init__(self, keys: list[int]) -> None:
        self._keys = list(keys)

    def getch(self) -> int:
        return self._keys.pop(0) if self._keys else -1


class TestMousePolling:
    """``poll`` has to turn KEY_MOUSE plus a queued event into an action."""

    @staticmethod
    def handler_with(events: list[tuple[int, int, int]]) -> InputHandler:
        return InputHandler(
            mouse_reader=lambda: events.pop(0) if events else None,
        )

    def test_a_queued_click_becomes_an_action(self) -> None:
        handler = self.handler_with([(12, 7, curses.BUTTON1_PRESSED)])
        assert handler.poll(_Keys([curses.KEY_MOUSE])) == [Action.MINE]

    def test_a_right_click_becomes_a_place(self) -> None:
        handler = self.handler_with([(12, 7, curses.BUTTON3_PRESSED)])
        assert handler.poll(_Keys([curses.KEY_MOUSE])) == [Action.PLACE]

    def test_a_move_without_a_button_is_ignored(self) -> None:
        handler = self.handler_with([(12, 7, curses.REPORT_MOUSE_POSITION)])
        assert handler.poll(_Keys([curses.KEY_MOUSE])) == []

    def test_an_empty_queue_does_not_crash(self) -> None:
        handler = self.handler_with([])
        assert handler.poll(_Keys([curses.KEY_MOUSE])) == []

    def test_a_click_that_only_reports_clicked_counts_as_a_press(self) -> None:
        handler = self.handler_with([(12, 7, curses.BUTTON1_CLICKED)])
        assert handler.poll(_Keys([curses.KEY_MOUSE])) == [Action.MINE]

    def test_keys_and_clicks_can_be_polled_together(self) -> None:
        handler = self.handler_with([(12, 7, curses.BUTTON1_PRESSED)])
        actions = handler.poll(_Keys([ord("d"), curses.KEY_MOUSE, ord("k")]))
        assert actions == [Action.MOVE_RIGHT, Action.MINE, Action.PLACE]

    def test_describe_key_names_the_mouse(self) -> None:
        assert describe_key(curses.KEY_MOUSE) == f"mouse ({curses.KEY_MOUSE})"


class TestMouseEnabling:
    """What the terminal reports back decides whether the mouse is usable."""

    @staticmethod
    def patch(monkeypatch: pytest.MonkeyPatch, available: int) -> list[int]:
        calls: list[int] = []

        def fake_mousemask(mask: int) -> tuple[int, int]:
            calls.append(mask)
            return available, 0

        monkeypatch.setattr(curses, "mousemask", fake_mousemask)
        monkeypatch.setattr(curses, "def_prog_mode", lambda: None)
        monkeypatch.setattr(curses, "mouseinterval", lambda value: None)
        return calls

    def test_enable_reports_what_the_terminal_offers(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self.patch(monkeypatch, curses.ALL_MOUSE_EVENTS)
        handler = InputHandler()
        assert handler.enable_mouse() is True
        assert handler.mouse_enabled is True

    def test_a_terminal_that_offers_nothing_reports_off(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self.patch(monkeypatch, 0)
        handler = InputHandler()
        assert handler.enable_mouse() is False
        assert handler.mouse_enabled is False

    def test_disable_switches_mouse_reporting_off(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls = self.patch(monkeypatch, curses.ALL_MOUSE_EVENTS)
        handler = InputHandler()
        handler.enable_mouse()
        handler.disable_mouse()
        assert calls == [curses.ALL_MOUSE_EVENTS, 0]
        assert handler.mouse_enabled is False

    def test_disable_before_enable_touches_nothing(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        calls = self.patch(monkeypatch, curses.ALL_MOUSE_EVENTS)
        InputHandler().disable_mouse()
        assert calls == []


class TestConfigConsistency:
    def test_every_bound_action_exists(self) -> None:
        for name in config.KEY_BINDINGS:
            assert name.upper() in Action.__members__

    def test_every_bindable_action_is_bound(self) -> None:
        # RESIZE comes from the terminal itself, not from a key binding.
        bound = {name.upper() for name in config.KEY_BINDINGS}
        unbound = {
            action.name
            for action in Action
            if action is not Action.RESIZE and action.name not in bound
        }
        assert unbound == set()

    def test_default_bindings_build_without_conflicts(self) -> None:
        # Building the lookup raises on duplicates; this asserts it builds.
        InputHandler(config.KEY_BINDINGS)

    def test_every_mouse_bound_action_exists(self) -> None:
        for name in config.MOUSE_BINDINGS:
            assert name.upper() in Action.__members__

    def test_mouse_bindings_use_known_buttons(self) -> None:
        known = {button.value for button in MouseButton}
        for button in config.MOUSE_BINDINGS.values():
            assert button in known

    def test_mouse_bindings_only_ever_extend_keyboard_actions(self) -> None:
        # The mouse is an extra way to trigger an action, never a new one.
        for name in config.MOUSE_BINDINGS:
            assert name in config.KEY_BINDINGS


class TestDescribeKey:
    def test_none(self) -> None:
        assert describe_key(None) == "(none)"

    def test_printable(self) -> None:
        assert describe_key(ord("a")) == "a (97)"

    def test_space(self) -> None:
        assert describe_key(ord(" ")) == "space (32)"

    def test_special(self) -> None:
        assert describe_key(curses.KEY_LEFT) == "left (260)"
        assert describe_key(curses.KEY_RESIZE) == f"KEY_RESIZE ({curses.KEY_RESIZE})"

    def test_unknown_code(self) -> None:
        assert describe_key(9999) == "key 9999"
