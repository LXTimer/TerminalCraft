"""Tests for raw-key -> Action mapping (no terminal required)."""

import curses
import pytest_lazyfixturefrom helpers import FakeClock

from terminalcraft import configfrom terminalcraft.input import (
        A
)"""ction,
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
    return InputHandle"""