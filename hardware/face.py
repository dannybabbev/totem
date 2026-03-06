"""
Face Module - MAX7219 8x8 LED Matrix
=====================================

Exposes the full Pillow ImageDraw API on an 8x8 pixel canvas, plus
named expressions and background animations.

Hardware: MAX7219 via SPI (port=0, device=0)
Wiring:   DIN->GPIO10(MOSI), CS->GPIO8(CE0), CLK->GPIO11(SCLK), VCC->5V, GND->GND
"""

import time
import random
import threading
from PIL import Image, ImageDraw, ImageFont

from hardware.base import HardwareModule

# Imported at module level so expressions are available without circular deps
import expressions as expr_lib


class FaceModule(HardwareModule):

    # --- HardwareModule interface -------------------------------------------

    @property
    def name(self):
        return "face"

    @property
    def description(self):
        return "MAX7219 8x8 LED matrix face with expressions, drawing, and animations"

    def init(self):
        from luma.core.interface.serial import spi, noop
        from luma.led_matrix.device import max7219

        serial = spi(port=0, device=0, gpio=noop())
        self._device = max7219(serial, cascaded=1, block_orientation=0, rotate=0)
        self._device.contrast(128)

        # Internal pixel buffer (8x8)
        self._buffer = Image.new("1", (8, 8), 0)
        self._draw = ImageDraw.Draw(self._buffer)

        # Animation thread management
        self._anim_stop = threading.Event()
        self._anim_thread = None

        # State tracking
        self._current_expression = None
        self._current_animation = None
        self._brightness = 128

    def cleanup(self):
        self._stop_animation()
        try:
            self._device.hide()
        except Exception:
            pass

    def get_state(self):
        return {
            "current_expression": self._current_expression,
            "current_animation": self._current_animation,
            "brightness": self._brightness,
            "animation_running": self._anim_thread is not None and self._anim_thread.is_alive(),
        }

    def get_capabilities(self):
        return [
            # High-level
            {
                "action": "expression",
                "description": "Set a named facial expression",
                "params": {
                    "name": {
                        "type": "str",
                        "required": True,
                        "description": "Expression name",
                        "options": expr_lib.list_expressions(),
                    }
                },
            },
            {
                "action": "animate",
                "description": "Start a named background animation",
                "params": {
                    "name": {
                        "type": "str",
                        "required": True,
                        "description": "Animation name",
                        "options": ["thinking", "speaking", "listening", "sleeping", "idle_blink"],
                    },
                    "duration": {
                        "type": "float",
                        "required": False,
                        "description": "Duration in seconds (0 = loop forever)",
                        "default": 0,
                    },
                },
            },
            {
                "action": "stop",
                "description": "Stop any running animation",
                "params": {},
            },
            {
                "action": "blink",
                "description": "Single eye blink",
                "params": {
                    "duration_ms": {
                        "type": "int",
                        "required": False,
                        "description": "Blink duration in ms",
                        "default": 150,
                    }
                },
            },
            # Low-level drawing
            {
                "action": "custom",
                "description": "Draw an arbitrary 8x8 bitmap grid",
                "params": {
                    "grid": {
                        "type": "list[list[int]]",
                        "required": True,
                        "description": "8 rows of 8 pixels (0 or 1)",
                    }
                },
            },
            {
                "action": "pixel",
                "description": "Set or clear a single pixel",
                "params": {
                    "x": {"type": "int", "required": True, "description": "X coord (0-7)"},
                    "y": {"type": "int", "required": True, "description": "Y coord (0-7)"},
                    "on": {"type": "int", "required": False, "description": "1=on, 0=off", "default": 1},
                    "flush": {"type": "bool", "required": False, "description": "Flush to display", "default": True},
                },
            },
            {
                "action": "line",
                "description": "Draw a line between two points",
                "params": {
                    "x1": {"type": "int", "required": True},
                    "y1": {"type": "int", "required": True},
                    "x2": {"type": "int", "required": True},
                    "y2": {"type": "int", "required": True},
                    "flush": {"type": "bool", "required": False, "default": True},
                },
            },
            {
                "action": "rect",
                "description": "Draw a rectangle",
                "params": {
                    "x1": {"type": "int", "required": True},
                    "y1": {"type": "int", "required": True},
                    "x2": {"type": "int", "required": True},
                    "y2": {"type": "int", "required": True},
                    "fill": {"type": "bool", "required": False, "default": False},
                    "flush": {"type": "bool", "required": False, "default": True},
                },
            },
            {
                "action": "ellipse",
                "description": "Draw an ellipse / circle",
                "params": {
                    "x1": {"type": "int", "required": True},
                    "y1": {"type": "int", "required": True},
                    "x2": {"type": "int", "required": True},
                    "y2": {"type": "int", "required": True},
                    "fill": {"type": "bool", "required": False, "default": False},
                    "flush": {"type": "bool", "required": False, "default": True},
                },
            },
            {
                "action": "text",
                "description": "Draw a character at a position (tiny pixel font)",
                "params": {
                    "x": {"type": "int", "required": True},
                    "y": {"type": "int", "required": True},
                    "char": {"type": "str", "required": True, "description": "Single character"},
                    "flush": {"type": "bool", "required": False, "default": True},
                },
            },
            {
                "action": "clear",
                "description": "Clear the display (all pixels off)",
                "params": {
                    "flush": {"type": "bool", "required": False, "default": True},
                },
            },
            {
                "action": "invert",
                "description": "Invert all pixels on the display",
                "params": {
                    "flush": {"type": "bool", "required": False, "default": True},
                },
            },
            {
                "action": "brightness",
                "description": "Set LED brightness",
                "params": {
                    "value": {
                        "type": "int",
                        "required": True,
                        "description": "Brightness 0-255",
                        "min": 0,
                        "max": 255,
                    }
                },
            },
            {
                "action": "flush",
                "description": "Flush the internal pixel buffer to the display",
                "params": {},
            },
            # Animation authoring
            {
                "action": "sequence",
                "description": "Play a custom animation (list of frames with timing)",
                "params": {
                    "frames": {
                        "type": "list[dict]",
                        "required": True,
                        "description": 'List of {"grid": [[...]], "ms": 200}',
                    },
                    "loop": {"type": "bool", "required": False, "default": False},
                },
            },
        ]

    def handle_command(self, action, params):
        try:
            if action == "expression":
                return self._cmd_expression(params)
            elif action == "animate":
                return self._cmd_animate(params)
            elif action == "stop":
                return self._cmd_stop(params)
            elif action == "blink":
                return self._cmd_blink(params)
            elif action == "custom":
                return self._cmd_custom(params)
            elif action == "pixel":
                return self._cmd_pixel(params)
            elif action == "line":
                return self._cmd_line(params)
            elif action == "rect":
                return self._cmd_rect(params)
            elif action == "ellipse":
                return self._cmd_ellipse(params)
            elif action == "text":
                return self._cmd_text(params)
            elif action == "clear":
                return self._cmd_clear(params)
            elif action == "invert":
                return self._cmd_invert(params)
            elif action == "brightness":
                return self._cmd_brightness(params)
            elif action == "flush":
                return self._cmd_flush(params)
            elif action == "sequence":
                return self._cmd_sequence(params)
            else:
                return self._err(f"Unknown face action: {action}")
        except Exception as e:
            return self._err(str(e))

    # --- High-level commands ------------------------------------------------

    def _cmd_expression(self, params):
        name = params.get("name", "").lower()
        grid = expr_lib.get_expression(name)
        if grid is None:
            return self._err(
                f"Unknown expression '{name}'. Available: {expr_lib.list_expressions()}"
            )
        self._stop_animation()
        self._draw_grid(grid)
        self._flush()
        self._current_expression = name
        self._current_animation = None
        return self._ok({"expression": name})

    def _cmd_animate(self, params):
        name = params.get("name", "").lower()
        duration = float(params.get("duration", 0))

        animations = {
            "thinking": self._anim_thinking,
            "speaking": self._anim_speaking,
            "listening": self._anim_listening,
            "sleeping": self._anim_sleeping,
            "idle_blink": self._anim_idle_blink,
        }

        if name not in animations:
            return self._err(f"Unknown animation '{name}'. Available: {list(animations.keys())}")

        self._stop_animation()
        self._current_animation = name
        self._current_expression = None
        self._anim_stop.clear()
        self._anim_thread = threading.Thread(
            target=animations[name], args=(duration,), daemon=True
        )
        self._anim_thread.start()
        return self._ok({"animation": name, "duration": duration})

    def _cmd_stop(self, _params):
        was_running = self._current_animation
        self._stop_animation()
        return self._ok({"stopped": was_running})

    def _cmd_blink(self, params):
        duration_ms = int(params.get("duration_ms", 150))
        self._stop_animation()
        # Save current buffer
        saved = self._buffer.copy()
        # Draw blink frame
        self._draw_grid(expr_lib.BLINK)
        self._flush()
        time.sleep(duration_ms / 1000.0)
        # Restore
        self._buffer = saved
        self._draw = ImageDraw.Draw(self._buffer)
        self._flush()
        return self._ok()

    # --- Low-level drawing commands -----------------------------------------

    def _cmd_custom(self, params):
        grid = params.get("grid")
        if not grid or len(grid) != 8:
            return self._err("Grid must be a list of 8 rows, each with 8 values")
        self._stop_animation()
        self._draw_grid(grid)
        self._flush()
        self._current_expression = "custom"
        self._current_animation = None
        return self._ok()

    def _cmd_pixel(self, params):
        x = int(params.get("x", 0))
        y = int(params.get("y", 0))
        on = int(params.get("on", 1))
        flush = params.get("flush", True)
        self._buffer.putpixel((x, y), 1 if on else 0)
        if flush:
            self._flush()
        return self._ok({"x": x, "y": y, "on": on})

    def _cmd_line(self, params):
        coords = (int(params["x1"]), int(params["y1"]), int(params["x2"]), int(params["y2"]))
        flush = params.get("flush", True)
        self._draw.line(coords, fill=1)
        if flush:
            self._flush()
        return self._ok()

    def _cmd_rect(self, params):
        coords = (int(params["x1"]), int(params["y1"]), int(params["x2"]), int(params["y2"]))
        fill_it = params.get("fill", False)
        flush = params.get("flush", True)
        if fill_it:
            self._draw.rectangle(coords, outline=1, fill=1)
        else:
            self._draw.rectangle(coords, outline=1, fill=0)
        if flush:
            self._flush()
        return self._ok()

    def _cmd_ellipse(self, params):
        coords = (int(params["x1"]), int(params["y1"]), int(params["x2"]), int(params["y2"]))
        fill_it = params.get("fill", False)
        flush = params.get("flush", True)
        if fill_it:
            self._draw.ellipse(coords, outline=1, fill=1)
        else:
            self._draw.ellipse(coords, outline=1, fill=0)
        if flush:
            self._flush()
        return self._ok()

    def _cmd_text(self, params):
        x = int(params.get("x", 0))
        y = int(params.get("y", 0))
        char = str(params.get("char", ""))[:1]
        flush = params.get("flush", True)
        # Use default tiny font
        self._draw.text((x, y), char, fill=1)
        if flush:
            self._flush()
        return self._ok()

    def _cmd_clear(self, params):
        flush = params.get("flush", True)
        self._draw.rectangle((0, 0, 7, 7), fill=0)
        if flush:
            self._flush()
        self._current_expression = None
        return self._ok()

    def _cmd_invert(self, params):
        flush = params.get("flush", True)
        for y in range(8):
            for x in range(8):
                val = self._buffer.getpixel((x, y))
                self._buffer.putpixel((x, y), 0 if val else 1)
        if flush:
            self._flush()
        return self._ok()

    def _cmd_brightness(self, params):
        value = int(params.get("value", 128))
        value = max(0, min(255, value))
        self._device.contrast(value)
        self._brightness = value
        return self._ok({"brightness": value})

    def _cmd_flush(self, _params=None):
        self._flush()
        return self._ok()

    def _cmd_sequence(self, params):
        frames = params.get("frames", [])
        loop = params.get("loop", False)
        if not frames:
            return self._err("No frames provided")

        self._stop_animation()
        self._current_animation = "sequence"
        self._anim_stop.clear()
        self._anim_thread = threading.Thread(
            target=self._anim_sequence, args=(frames, loop), daemon=True
        )
        self._anim_thread.start()
        return self._ok({"frames": len(frames), "loop": loop})

    # --- Internal helpers ---------------------------------------------------

    def _draw_grid(self, grid):
        """Draw an 8x8 grid into the internal buffer."""
        for y, row in enumerate(grid):
            for x, pixel in enumerate(row):
                self._buffer.putpixel((x, y), 1 if pixel else 0)

    def _flush(self):
        """Send the internal buffer to the physical device."""
        self._device.display(self._buffer)

    def _stop_animation(self):
        """Signal the animation thread to stop and wait for it."""
        if self._anim_thread and self._anim_thread.is_alive():
            self._anim_stop.set()
            self._anim_thread.join(timeout=2)
        self._anim_thread = None
        self._current_animation = None

    # --- Built-in animations ------------------------------------------------

    def _anim_thinking(self, duration):
        """Spinning line animation."""
        end_time = time.time() + duration if duration > 0 else float("inf")
        frames = [
            [(3, 1, 3, 6), (4, 1, 4, 6)],  # Vertical |
            [(1, 6, 6, 1)],                  # Diagonal /
            [(1, 3, 6, 3), (1, 4, 6, 4)],   # Horizontal -
            [(1, 1, 6, 6)],                  # Diagonal \
        ]
        while time.time() < end_time and not self._anim_stop.is_set():
            for lines in frames:
                if self._anim_stop.is_set():
                    break
                self._draw.rectangle((0, 0, 7, 7), fill=0)
                for line in lines:
                    self._draw.line(line, fill=1)
                self._flush()
                self._anim_stop.wait(0.1)

    def _anim_speaking(self, duration):
        """Mouth flapping between open and closed."""
        end_time = time.time() + duration if duration > 0 else float("inf")
        while time.time() < end_time and not self._anim_stop.is_set():
            self._draw_grid(expr_lib.TALK_OPEN)
            self._flush()
            self._anim_stop.wait(random.uniform(0.1, 0.3))
            if self._anim_stop.is_set():
                break
            self._draw_grid(expr_lib.TALK_CLOSED)
            self._flush()
            self._anim_stop.wait(random.uniform(0.05, 0.2))

    def _anim_listening(self, duration):
        """Subtle pulsing dot pattern indicating listening."""
        end_time = time.time() + duration if duration > 0 else float("inf")
        while time.time() < end_time and not self._anim_stop.is_set():
            # Dots expand
            for size in range(1, 4):
                if self._anim_stop.is_set():
                    break
                self._draw.rectangle((0, 0, 7, 7), fill=0)
                cx, cy = 3, 3
                self._draw.ellipse((cx - size, cy - size, cx + size + 1, cy + size + 1), outline=1)
                self._flush()
                self._anim_stop.wait(0.15)
            # Dots contract
            for size in range(3, 0, -1):
                if self._anim_stop.is_set():
                    break
                self._draw.rectangle((0, 0, 7, 7), fill=0)
                cx, cy = 3, 3
                self._draw.ellipse((cx - size, cy - size, cx + size + 1, cy + size + 1), outline=1)
                self._flush()
                self._anim_stop.wait(0.15)

    def _anim_sleeping(self, duration):
        """Zzz floating up animation."""
        end_time = time.time() + duration if duration > 0 else float("inf")
        z_positions = [(6, 6), (4, 4), (2, 2), (1, 0)]
        while time.time() < end_time and not self._anim_stop.is_set():
            for x, y in z_positions:
                if self._anim_stop.is_set():
                    break
                self._draw.rectangle((0, 0, 7, 7), fill=0)
                self._draw.text((x, y), "z", fill=1)
                self._flush()
                self._anim_stop.wait(0.4)

    def _anim_idle_blink(self, duration):
        """Neutral face with periodic random blinks."""
        end_time = time.time() + duration if duration > 0 else float("inf")
        while time.time() < end_time and not self._anim_stop.is_set():
            # Show neutral
            self._draw_grid(expr_lib.NEUTRAL)
            self._flush()
            # Wait random interval before blinking
            wait = random.uniform(2.0, 5.0)
            self._anim_stop.wait(wait)
            if self._anim_stop.is_set():
                break
            # Blink
            self._draw_grid(expr_lib.BLINK)
            self._flush()
            self._anim_stop.wait(0.15)

    def _anim_sequence(self, frames, loop):
        """Play a custom frame sequence."""
        while not self._anim_stop.is_set():
            for frame in frames:
                if self._anim_stop.is_set():
                    break
                grid = frame.get("grid", [])
                ms = frame.get("ms", 200)
                if grid and len(grid) == 8:
                    self._draw_grid(grid)
                    self._flush()
                self._anim_stop.wait(ms / 1000.0)
            if not loop:
                break
        self._current_animation = None
