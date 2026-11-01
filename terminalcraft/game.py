"""Main loop and scene stack.

This module is the game's control flow and deliberately never imports
``curses``: it reaches the terminal only through the :class:`Renderer`
(``render/``) and :class:`InputHandler` (``input.py``) it is given, which
keeps the loop itself testable and the backends swappable.
"""

from __future__ import annotations

import math
import time
from typing import Protocol

from . import config
from .entities.player import Player
from .input import Action, InputHandler, windows_key_state
from .interaction import (
    BlockCursor,
    MiningState,
    break_seconds,
    in_reach,
    mine_refusal,
    place_refusal,
)
from .items.inventory import Inventory
from .items.items import item_for
from .render.debug import draw_debug_screen
from .render.hud import HUD_ROWS, draw_hud
from .render.renderer import Camera, Renderer, Screen, init_screen
from .world.blocks import AIR, block_for
from .world.world import World
from .world.worldgen import build_test_world


class Scene(Protocol):
    """One full-screen mode of the game (debug, title, playing, ...).

    Scenes form a stack: only the top scene receives actions, updates and
    draws. ``handle_action`` returns ``True`` when the scene consumed the
    action; otherwise the loop applies its own defaults (e.g. QUIT).
    """

    def handle_action(self, action: Action) -> bool:
        """React to one action; return True if it was consumed."""
        ...

    def update(self, dt: float) -> None:
        """Advance the scene by one fixed tick."""
        ...

    def draw(self, renderer: Renderer) -> None:
        """Draw the scene (the frame has already been erased)."""
        ...


class Game:
    """Fixed-timestep loop driving a stack of scenes."""

    def __init__(self, renderer: Renderer, input_handler: InputHandler) -> None:
        self._renderer = renderer
        self._input = input_handler
        self._scenes: list[Scene] = []
        self._running = False
        self._accumulator = 0.0
        self._last_frame = 0.0
        self._fps_frames = 0
        self._fps_window_start = 0.0
        #: Fixed updates simulated so far (shown by debug screens).
        self.tick_count = 0
        #: Frames per second over the most recent one-second window.
        self.fps = 0.0

    # -- scene stack --------------------------------------------------------

    def push_scene(self, scene: Scene) -> None:
        """Push *scene* on top; it becomes the active scene."""
        self._scenes.append(scene)

    def pop_scene(self) -> Scene | None:
        """Pop the active scene (no-op when the stack is empty)."""
        return self._scenes.pop() if self._scenes else None

    def request_quit(self) -> None:
        """Ask the loop to exit after the current iteration."""
        self._running = False

    # -- loop ---------------------------------------------------------------

    def run(
        self,
        scene: Scene,
        *,
        max_ticks: int | None = None,
        frame_seconds: float | None = None,
    ) -> None:
        """Run the loop until quit.

        ``max_ticks``/``frame_seconds`` are for deterministic headless runs:
        pass a fixed elapsed time per iteration and the loop never sleeps.
        """
        self.push_scene(scene)
        self._running = True
        self._last_frame = time.perf_counter()
        self._fps_window_start = self._last_frame
        while self._running:
            if max_ticks is not None and self.tick_count >= max_ticks:
                break
            frame_start = time.perf_counter()
            elapsed = frame_start - self._last_frame if frame_seconds is None else frame_seconds
            self._last_frame = frame_start
            # Drop absurd stalls (breakpoints, OS hiccups) instead of
            # fast-forwarding the world through them.
            self._accumulator = min(self._accumulator + elapsed, config.MAX_FRAME_SECONDS)
            self._dispatch_input()
            while self._accumulator >= config.TICK_SECONDS:
                self._accumulator -= config.TICK_SECONDS
                self.tick_count += 1
                self._update(config.TICK_SECONDS)
            self._draw()
            self._track_fps(frame_start)
            if frame_seconds is None:
                self._sleep_until_next_tick(frame_start)

    def _dispatch_input(self) -> None:
        """Poll the terminal and route each action to the active scene."""
        for action in self._input.poll(self._renderer.screen):
            self._handle_action(action)

    def _handle_action(self, action: Action) -> None:
        if action is Action.RESIZE:
            self._renderer.handle_resize()
            return
        if self._scenes and self._scenes[-1].handle_action(action):
            return
        if action is Action.QUIT:
            self.request_quit()

    def _update(self, dt: float) -> None:
        if self._scenes:
            self._scenes[-1].update(dt)

    def _draw(self) -> None:
        self._renderer.begin_frame()
        if self._renderer.too_small:
            width, height = self._renderer.size
            self._renderer.draw_centered(
                f"Please enlarge to {config.MIN_TERMINAL_WIDTH}x{config.MIN_TERMINAL_HEIGHT} "
                f"(now {width}x{height})",
                self._renderer.attr("warning"),
            )
        elif self._scenes:
            self._scenes[-1].draw(self._renderer)
        self._renderer.present()

    def _track_fps(self, frame_start: float) -> None:
        self._fps_frames += 1
        window = frame_start - self._fps_window_start
        if window >= 1.0:
            self.fps = self._fps_frames / window
            self._fps_frames = 0
            self._fps_window_start = frame_start

    @staticmethod
    def _sleep_until_next_tick(frame_start: float) -> None:
        """Sleep until roughly the next tick so the loop does not busy-spin."""
        remaining = config.TICK_SECONDS - (time.perf_counter() - frame_start)
        if remaining > 0:
            time.sleep(remaining)


class PlayingScene:
    """Milestone-3 scene: walk, jump, mine and place.

    Walking, mining and one-shot actions read the handler's *held* state, so
    holding a direction walks continuously instead of at the terminal's
    key-repeat rate and a held key cannot repeat a jump or a placement. The
    block cursor is the exception: it steps once per key event, because a tap
    has to land on exactly one tile.

    The mouse buttons are extra bindings for mine and place, not a separate
    mode: a click aims the cursor at the tile it landed on and then travels
    the same held/pressed path a key would, so keyboard and mouse can be used
    interchangeably - even at the same time.
    """

    def __init__(
        self,
        game: Game,
        input_handler: InputHandler,
        world: World,
        renderer: Renderer,
        player: Player,
        inventory: Inventory,
        cursor: BlockCursor,
    ) -> None:
        self._game = game
        self._input = input_handler
        self._world = world
        self._renderer = renderer
        self.player = player
        self.inventory = inventory
        self.cursor = cursor
        self.mining = MiningState()
        #: The player tile the cursor's aim offset was last measured from.
        self._anchor = player.tile
        self._notice = ""
        self._notice_seconds = 0.0

    @property
    def notice(self) -> str:
        """The refusal being shown on the hint line, or ``""``."""
        return self._notice

    @property
    def camera(self) -> Camera:
        """The camera this scene follows the player with."""
        return self._renderer.camera

    @property
    def world(self) -> World:
        """The world this scene edits."""
        return self._world

    # -- input -------------------------------------------------------------

    def handle_action(self, action: Action) -> bool:
        """Select hotbar slots and step the cursor; the rest is polled."""
        slot = _HOTBAR_ACTIONS.get(action)
        if slot is not None:
            self.inventory.select(slot)
            return True
        step = _CURSOR_STEPS.get(action)
        if step is not None:
            self.cursor.move(step[0], step[1], self._world)
            return True
        return action in _POLLED_ACTIONS

    # -- simulation --------------------------------------------------------

    def update(self, dt: float) -> None:
        """One fixed tick: aim, walk, mine, place, then move the camera."""
        self._aim_from_mouse()
        self._walk(dt)
        self._follow()
        self._mine(dt)
        self._place()
        self._fade_notice(dt)
        body = self.player.body
        self._renderer.camera.follow(body.center_x, body.center_y, dt)

    def _follow(self) -> None:
        """Carry the cursor by however many tiles the player has moved.

        The cursor is an aim *offset* from the player, not a free pointer:
        walk twenty tiles away and it walks with you, instead of being left
        behind out of reach and quietly refusing every action.
        """
        tile = self.player.tile
        if tile != self._anchor:
            self.cursor.move(
                tile[0] - self._anchor[0], tile[1] - self._anchor[1], self._world
            )
            self._anchor = tile

    def _tell(self, refusal: str) -> None:
        """Show *refusal* on the hint line for :data:`config.NOTICE_SECONDS`."""
        self._notice = refusal
        self._notice_seconds = config.NOTICE_SECONDS

    def _fade_notice(self, dt: float) -> None:
        """Expire the current refusal once its time is up."""
        if not self._notice:
            return
        self._notice_seconds -= dt
        if self._notice_seconds <= 0.0:
            self._notice = ""

    def _aim_from_mouse(self) -> None:
        """Point the cursor at the tile under each click.

        A mouse button is an additional binding for MINE/PLACE, so without
        this a click would act on wherever the arrow keys happened to leave
        the cursor rather than on the block the player clicked. A click on the
        HUD rows is dropped entirely: it landed on the hotbar, not the world.
        """
        playfield_bottom = self._renderer.size[1] - HUD_ROWS
        for click in self._input.take_mouse_presses():
            if click.row >= playfield_bottom:
                self._input.cancel_mouse_action(click.button)
                continue
            tile = self._renderer.tile_at(self._world, click.column, click.row)
            if tile is not None:
                self.cursor.x, self.cursor.y = tile

    def _walk(self, dt: float) -> None:
        """Walk and jump from the held state of the movement keys."""
        held = self._input.is_held
        direction = int(held(Action.MOVE_RIGHT)) - int(held(Action.MOVE_LEFT))
        self.player.update(
            self._world,
            dt=dt,
            move_dir=direction,
            jump=self._input.take_press(Action.JUMP),
        )

    def _mine(self, dt: float) -> None:
        """Hold-to-mine the block under the cursor."""
        if not self._input.is_held(Action.MINE):
            self.mining.reset()
            return
        x, y = self.cursor.tile
        refusal = mine_refusal(self._world, self.player.body, x, y)
        if refusal is not None:
            self.mining.reset()
            self._tell(refusal)
            return
        block = block_for(self._world.get(x, y))
        if block.drops and not self.inventory.can_add(block.drops):
            # A full inventory blocks breaking, so no drop is ever lost.
            self.mining.reset()
            self._tell("inventory is full")
            return
        if self.mining.advance(self.cursor.tile, dt, break_seconds(block)):
            self._world.set(x, y, AIR)
            if block.drops:
                self.inventory.add(block.drops, 1)
            self.mining.reset()

    def _place(self) -> None:
        """Place the selected block on the cursor tile, once per press."""
        if not self._input.take_press(Action.PLACE):
            return
        stack = self.inventory.selected_stack()
        if stack is None:
            self._tell("that slot is empty")
            return
        x, y = self.cursor.tile
        refusal = place_refusal(self._world, self.player.body, x, y)
        if refusal is not None:
            self._tell(refusal)
            return
        self._world.set(x, y, item_for(stack.item).block)
        self.inventory.remove_selected(1)

    # -- drawing -----------------------------------------------------------

    def draw(self, renderer: Renderer) -> None:
        """Draw the world, the player, the HUD and the debug overlay."""
        renderer.draw_world(self._world)
        x, y = self.cursor.tile
        renderer.draw_highlight(
            self._world,
            x,
            y,
            warning=not in_reach(self.player.body, x, y),
        )
        self._draw_player(renderer)
        mining_block, mining_fraction = self._mining_progress()
        draw_hud(
            renderer,
            self.inventory,
            mining_block=mining_block,
            mining_fraction=mining_fraction,
        )
        draw_debug_screen(
            renderer,
            title="TerminalCraft - milestone 3: walk, mine, place",
            last_key=self._input.last_key,
            last_action=self._input.last_action,
            tick_count=self._game.tick_count,
            fps=self._game.fps,
            camera=renderer.camera,
            glyphs=renderer.glyph_set_name,
            fields=self._debug_fields(),
            hint=self._notice
            or "a/d walk   w jump   arrows aim   j/LMB mine   k/RMB place   1-9 slot   q quit",
        )

    def _draw_player(self, renderer: Renderer) -> None:
        """Draw the sprite so its feet sit at the body's bottom edge."""
        body = self.player.body
        pos = renderer.screen_pos(self._world, body.x, body.bottom)
        if pos is None:
            return
        row, column = pos
        sprite = config.PLAYER_SPRITES[renderer.glyph_set_name]
        attr = renderer.pair_attr(config.PLAYER_FG, config.PLAYER_BG)
        renderer.draw_sprite(row - len(sprite), column, sprite, attr)

    def _mining_progress(self) -> tuple[str | None, float]:
        """Name and completion fraction of the block being mined, if any."""
        if not self.mining.active or self.mining.target is None:
            return None, 0.0
        x, y = self.mining.target
        block = block_for(self._world.get(x, y))
        required = break_seconds(block)
        if not math.isfinite(required) or required <= 0.0:
            return block.name, 0.0
        return block.name, min(self.mining.progress / required, 1.0)

    def _debug_fields(self) -> list[tuple[str, str]]:
        """Scene-specific fields for the debug overlay, two per line."""
        body = self.player.body
        x, y = self.cursor.tile
        fields = [
            ("player", f"{body.x:.2f},{body.y:.2f}"),
            ("velocity", f"{body.vx:.1f},{body.vy:.1f}"),
            ("ground", "yes" if body.on_ground else "no"),
            ("cursor", f"{x},{y} {block_for(self._world.get(x, y)).name}"),
            ("facing", "right" if self.player.facing > 0 else "left"),
        ]
        if self.mining.active:
            fields.append(("mining", f"{self.mining.progress:.2f}s"))
        enabled = self._input.mouse_enabled
        if enabled is None:
            mouse_state = "not asked"
        else:
            mouse_state = "on" if enabled else "off"
        fields.append(("mouse", mouse_state))
        return fields


#: Hotbar actions mapped to the 0-based slot they select.
_HOTBAR_ACTIONS: dict[Action, int] = {
    getattr(Action, f"HOTBAR_{number}"): number - 1 for number in range(1, 10)
}

#: Cursor keys move the target one tile per key event, not per tick: a tap
#: must land on exactly one tile, and the terminal's own key repeat is what
#: makes holding the key scroll.
_CURSOR_STEPS: dict[Action, tuple[int, int]] = {
    Action.CURSOR_LEFT: (-1, 0),
    Action.CURSOR_RIGHT: (1, 0),
    Action.CURSOR_UP: (0, -1),
    Action.CURSOR_DOWN: (0, 1),
}

#: Actions the scene reads from held state during :meth:`PlayingScene.update`.
_POLLED_ACTIONS = frozenset(
    {
        Action.MOVE_LEFT,
        Action.MOVE_RIGHT,
        Action.JUMP,
        Action.MINE,
        Action.PLACE,
    }
)


def build_playing_scene(
    game: Game, input_handler: InputHandler, renderer: Renderer
) -> PlayingScene:
    """Create the playing scene with a player standing at the world centre."""
    world = build_test_world()
    player = Player.spawn(world, world.width // 2)
    inventory = Inventory()
    for name, count in config.STARTER_ITEMS:
        inventory.add(name, count)
    renderer.camera.x = player.body.center_x
    renderer.camera.y = player.body.center_y
    return PlayingScene(
        game,
        input_handler,
        world,
        renderer,
        player,
        inventory,
        BlockCursor(*player.tile),
    )


def run_game(screen: Screen) -> None:
    """Bootstrap the real game; called by ``__main__`` inside curses.wrapper."""
    renderer = init_screen(screen)
    # Reading real key state is what removes the OS repeat delay's stutter:
    # without it a held key's first 250-1000 ms look like a release.
    handler = InputHandler(key_state=windows_key_state)
    # Mouse buttons are extra bindings for mine/place; a terminal that cannot
    # report them still plays fine on the keyboard alone.
    handler.enable_mouse()
    game = Game(renderer, handler)
    try:
        game.run(build_playing_scene(game, handler, renderer))
    finally:
        # Mouse reporting disables the console's QuickEdit mode; put the
        # terminal back the way it was found.
        handler.disable_mouse()
