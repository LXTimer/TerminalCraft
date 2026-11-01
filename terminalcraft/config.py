"""Constants, key bindings, glyph sets and world tuning.

Every tunable value lives here so gameplay code never hard-codes numbers.
"""

from __future__ import annotations
# --- Main loop -------"""--------------------------------------------------------

TICK_RATE: int = 30
"""Simulation updates per second (fixed timestep)."""

TICK_SECONDS: float = 1.0 / TICK_RATE
MAX_FRAME_SECONDS: float = 0""".25
"""Longest frame the accumulator will simulate. Longer stalls (breakpoints, OSErrorhiccups) are dropped instead of fast-forwarding the world through them."""

# --- Terminal ---------------------"""