# Dev Log #3

A fresh dev log! The last build left TerminalCraft as a pretty-but-dead world: you could pan
a camera across it, but you could never touch a single block. So the past few days I finally
gave it a pulse. This round is all about *you* — a character that walks, jumps, digs, and
builds — and, as usual, the bugs that fought back hardest were the ones you can't see.

## New in this build

**The Player.** There's finally someone in the world. A small `@@` figure (or `██` on a
Unicode terminal) stands on the surface and answers to the keys. Walking is continuous, not
one-tile-per-press; a jump launches you about 1.2 tiles up and lands you right where you left.

**Real physics.** Blocks now have weight. Gravity pulls at 30 tiles/s², you cap out at 20
falling, and a one-tile ledge gets climbed without you thinking about it — but a two-tile wall
demands a real jump. Walk into a wall and you stop flush against it; hit the ceiling and the
climb just ends.

**Mining & Placing.** Aim the cursor with the arrows and hold `J` to dig. Every block takes its
own time (grass is quick, stone is slow, bedrock just refuses). Drops go straight into your
pack. `K` puts the selected item back into the world — as long as it's empty space, close
enough, and not inside you.

**A camera that follows you.** No more still shots. It tracks the player sideways and eases
vertically inside a dead zone, so a jump doesn't jolt the whole screen.

**A proper HUD.** A nine-slot hotbar along the bottom, the held item plus a mining progress bar
above it, and a compact debug panel (opaque this time — more on that below).

## Challenges

The camera wouldn't move *at all* in the real terminal. Keys mapped fine in every test, yet the
arrows did nothing on screen. It turned out Windows Terminal and the VS Code integrated terminal
don't send the arrow codes everyone expects — they arrive as keypad codes (`KEY_A2` and friends),
and my mapping simply didn't have them.

The debug panel was a smaller headache: drawn as transparent text, the world showed *through* the
letters; making it opaque fixed that, but then it swallowed the player sprite sitting at the
screen's centre.

And one physics bug bit hard — a body pressed against a ledge cleared its own horizontal speed on
contact, so it never got a second chance to step up. You'd walk into a single step and just... stop.

## Solutions

For the arrows: I added the keypad codes as aliases in the input layer, applied *after* the
explicit bindings so a user's own mapping still wins, and taught the debug overlay to name them
too. Verified end-to-end by injecting the real codes through `getch`.

For the panel: rewrote it as a short, two-column, fully opaque overlay — 8 rows pinned to the
top-left — so it stays readable without covering the player.

For the step-up: the horizontal mover no longer wipes the caller's intended velocity on a blocked
move; it keeps trying each tick, so the ledge gets climbed on the next frame instead of never. A
test now pins that behaviour so it can't quietly come back.

## Next up

World generation gets a real upgrade next: seeded noise terrain, caves, and proper trees instead
of the hand-placed test world we've been using. After that, the full inventory screen, crafting
with actual tools, and finally save/load so your builds survive a restart.
