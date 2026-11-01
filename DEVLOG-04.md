# Dev Log #4

The mouse landed, and then I finally did something I had been putting off: I ran the
game in a real terminal and *looked* at what the renderer is actually painting. The
answer, it turns out, is a lot of rectangles that all look the same.

## Mouse, from the drawing side

Left button mines, right button places — extra bindings, not a new mode. The renderer
had to learn to answer the opposite question: not "where does this tile go on screen",
but "what tile is this click on". `tile_at()` is that inverse, and a click now aims the
block cursor at the tile it landed on. Clicks on the two HUD rows are dropped — they hit
the hotbar, not the world. Whether a physical click actually reaches a console app inside
Windows Terminal is still an open question, so the debug panel shows `mouse on/off` and
the keyboard path stays fully live either way.

## The audit, measured rather than guessed

- Three seconds of real-time play: 89 ticks, 29.7 fps. The run-based tile drawing (one
  `addstr` per colour run instead of one per tile) is earning its keep.
- The glyph probe picked `unicode` on the real terminal. The write-the-glyphs-then-read-
  them-back trick works.
- And the uncomfortable part: **seven of the ten blocks share the same `██` glyph.**
  Stone, log, leaves, planks — one solid wall. Grass and leaves are even the same green.
  The world doesn't read, it blurs.
- The debug panel is nine opaque rows. On the minimum 80x24 terminal that is 37% of the
  screen, the HUD takes two more, and the world gets the leftovers.
- Walk twenty tiles away from the cursor and press `J`: nothing. Correctly nothing — the
  block is out of reach — but *silently* nothing. Right rule, mute feedback.

One favourite detail from the probes: PDCurses happily *draws* the bottom-right cell and
reports the error only afterwards. So the renderer's swallow-the-error policy loses
nothing, and the fake screen in the tests now mimics the quirk faithfully: write first,
raise after.

## Next

Not new features — eyesight. Distinct glyphs per block, a debug panel that can be turned
off, and a cursor that tells you *why* mining refused. Then the world generator gets real
terrain, because "every column is ninety rows of identical stone" is a geology lesson,
not a landscape.
