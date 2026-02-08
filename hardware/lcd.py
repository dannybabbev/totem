"""
LCD Module - 1602 LCD Display with I2C Backpack
================================================

Exposes the full RPLCD / HD44780 API surface so the AI has complete
control over every character cell and can create custom icons.

Hardware: 1602 LCD via PCF8574 I2C backpack
Wiring:   SDA->GPIO2(SDA1), SCL->GPIO3(SCL1), VCC->5V, GND->GND
Default I2C address: 0x27 (some boards use 0x3f)
"""

import time
import threading

from hardware.base import HardwareModule


class LCDModule(HardwareModule):

    LCD_COLS = 16
    LCD_ROWS = 2
    I2C_ADDRESS = 0x27  # Override via params if needed

    # --- HardwareModule interface -------------------------------------------

    @property
    def name(self):
        return "lcd"

    @property
    def description(self):
        return "1602 LCD display (16x2 characters) with I2C backpack, custom chars, and full cursor control"

    def init(self):
        from RPLCD.i2c import CharLCD

        self._lcd = CharLCD(
            i2c_expander="PCF8574",
            address=self.I2C_ADDRESS,
            port=1,
            cols=self.LCD_COLS,
            rows=self.LCD_ROWS,
            dotsize=8,
            charmap="A02",
            auto_linebreaks=True,
            backlight_enabled=True,
        )

        # State tracking
        self._backlight = True
        self._display_on = True
        self._cursor_mode = "hide"
        self._line1 = ""
        self._line2 = ""
        self._custom_chars = {}  # slot -> bitmap

        # Scroll thread management
        self._scroll_stop = threading.Event()
        self._scroll_thread = None

    def cleanup(self):
        self._stop_scroll()
        try:
            self._lcd.close(clear=True)
        except Exception:
            pass

    def get_state(self):
        return {
            "line1": self._line1,
            "line2": self._line2,
            "backlight": self._backlight,
            "display_on": self._display_on,
            "cursor_mode": self._cursor_mode,
            "custom_chars": list(self._custom_chars.keys()),
        }

    def get_capabilities(self):
        return [
            # High-level convenience
            {
                "action": "write",
                "description": "Write text to LCD (convenience: handles both lines and alignment)",
                "params": {
                    "line1": {"type": "str", "required": True, "description": "Text for row 1 (max 16 chars)"},
                    "line2": {"type": "str", "required": False, "description": "Text for row 2 (max 16 chars)", "default": ""},
                    "align": {"type": "str", "required": False, "description": "Text alignment", "options": ["left", "center", "right"], "default": "left"},
                },
            },
            {
                "action": "scroll",
                "description": "Scroll long text across the display (background thread)",
                "params": {
                    "text": {"type": "str", "required": True, "description": "Text to scroll"},
                    "row": {"type": "int", "required": False, "description": "Row to scroll on (0 or 1)", "default": 0},
                    "delay": {"type": "float", "required": False, "description": "Delay between shifts in seconds", "default": 0.3},
                },
            },
            {
                "action": "progress",
                "description": "Display a progress bar on line 2 with optional label on line 1",
                "params": {
                    "percentage": {"type": "int", "required": True, "description": "Progress 0-100", "min": 0, "max": 100},
                    "label": {"type": "str", "required": False, "description": "Label for line 1", "default": ""},
                },
            },
            # Low-level control
            {
                "action": "write_at",
                "description": "Write a string starting at any (row, col) position",
                "params": {
                    "row": {"type": "int", "required": True, "description": "Row (0 or 1)"},
                    "col": {"type": "int", "required": True, "description": "Column (0-15)"},
                    "text": {"type": "str", "required": True, "description": "Text to write"},
                },
            },
            {
                "action": "clear",
                "description": "Clear the display and reset cursor",
                "params": {},
            },
            {
                "action": "home",
                "description": "Reset cursor to (0,0) without clearing",
                "params": {},
            },
            {
                "action": "cursor",
                "description": "Move cursor to a specific position",
                "params": {
                    "row": {"type": "int", "required": True, "description": "Row (0 or 1)"},
                    "col": {"type": "int", "required": True, "description": "Column (0-15)"},
                },
            },
            {
                "action": "cursor_mode",
                "description": "Set cursor display mode",
                "params": {
                    "mode": {"type": "str", "required": True, "description": "Cursor mode", "options": ["hide", "line", "blink"]},
                },
            },
            {
                "action": "display",
                "description": "Toggle character display on/off (hides text without erasing)",
                "params": {
                    "on": {"type": "bool", "required": True, "description": "True=show, False=hide"},
                },
            },
            {
                "action": "backlight",
                "description": "Toggle LCD backlight on/off",
                "params": {
                    "on": {"type": "bool", "required": True, "description": "True=on, False=off"},
                },
            },
            {
                "action": "shift",
                "description": "Shift entire display content left or right",
                "params": {
                    "amount": {"type": "int", "required": True, "description": "Positive=right, negative=left"},
                },
            },
            {
                "action": "create_char",
                "description": "Define a custom 5x8 character in CGRAM (8 slots: 0-7)",
                "params": {
                    "slot": {"type": "int", "required": True, "description": "CGRAM slot (0-7)", "min": 0, "max": 7},
                    "bitmap": {
                        "type": "list[int]",
                        "required": True,
                        "description": "8 integers, each representing a 5-pixel row (0-31)",
                    },
                },
            },
            {
                "action": "write_char",
                "description": "Write a custom character from a CGRAM slot at current cursor position",
                "params": {
                    "slot": {"type": "int", "required": True, "description": "CGRAM slot (0-7)", "min": 0, "max": 7},
                },
            },
            {
                "action": "raw_command",
                "description": "Send a raw HD44780 command byte",
                "params": {
                    "value": {"type": "int", "required": True, "description": "Command byte (0-255)"},
                },
            },
            {
                "action": "raw_write",
                "description": "Write a raw byte to the display data register",
                "params": {
                    "value": {"type": "int", "required": True, "description": "Data byte (0-255)"},
                },
            },
            {
                "action": "stop_scroll",
                "description": "Stop any running scroll animation",
                "params": {},
            },
        ]

    def handle_command(self, action, params):
        try:
            if action == "write":
                return self._cmd_write(params)
            elif action == "scroll":
                return self._cmd_scroll(params)
            elif action == "progress":
                return self._cmd_progress(params)
            elif action == "write_at":
                return self._cmd_write_at(params)
            elif action == "clear":
                return self._cmd_clear(params)
            elif action == "home":
                return self._cmd_home(params)
            elif action == "cursor":
                return self._cmd_cursor(params)
            elif action == "cursor_mode":
                return self._cmd_cursor_mode(params)
            elif action == "display":
                return self._cmd_display(params)
            elif action == "backlight":
                return self._cmd_backlight(params)
            elif action == "shift":
                return self._cmd_shift(params)
            elif action == "create_char":
                return self._cmd_create_char(params)
            elif action == "write_char":
                return self._cmd_write_char(params)
            elif action == "raw_command":
                return self._cmd_raw_command(params)
            elif action == "raw_write":
                return self._cmd_raw_write(params)
            elif action == "stop_scroll":
                return self._cmd_stop_scroll(params)
            else:
                return self._err(f"Unknown lcd action: {action}")
        except Exception as e:
            return self._err(str(e))

    # --- High-level commands ------------------------------------------------

    def _cmd_write(self, params):
        line1 = str(params.get("line1", ""))
        line2 = str(params.get("line2", ""))
        align = str(params.get("align", "left")).lower()

        line1 = self._align_text(line1, align)
        line2 = self._align_text(line2, align)

        self._stop_scroll()
        self._lcd.clear()
        self._lcd.write_string(line1[:self.LCD_COLS])
        if line2:
            self._lcd.cursor_pos = (1, 0)
            self._lcd.write_string(line2[:self.LCD_COLS])

        self._line1 = line1[:self.LCD_COLS]
        self._line2 = line2[:self.LCD_COLS]
        return self._ok({"line1": self._line1, "line2": self._line2})

    def _cmd_scroll(self, params):
        text = str(params.get("text", ""))
        row = int(params.get("row", 0))
        delay = float(params.get("delay", 0.3))

        self._stop_scroll()
        self._scroll_stop.clear()
        self._scroll_thread = threading.Thread(
            target=self._scroll_worker, args=(text, row, delay), daemon=True
        )
        self._scroll_thread.start()
        return self._ok({"scrolling": text, "row": row})

    def _cmd_progress(self, params):
        percentage = max(0, min(100, int(params.get("percentage", 0))))
        label = str(params.get("label", ""))

        self._stop_scroll()

        # Build progress bar (16 chars wide)
        bar_width = self.LCD_COLS - 2  # [ and ]
        filled = int(bar_width * percentage / 100)
        bar = "[" + "#" * filled + "-" * (bar_width - filled) + "]"

        self._lcd.clear()
        if label:
            label_text = self._align_text(label[:self.LCD_COLS], "center")
            self._lcd.write_string(label_text)
        self._lcd.cursor_pos = (1, 0)
        self._lcd.write_string(bar)

        self._line1 = label[:self.LCD_COLS]
        self._line2 = bar
        return self._ok({"percentage": percentage, "bar": bar})

    # --- Low-level commands -------------------------------------------------

    def _cmd_write_at(self, params):
        row = int(params.get("row", 0))
        col = int(params.get("col", 0))
        text = str(params.get("text", ""))
        self._lcd.cursor_pos = (row, col)
        self._lcd.write_string(text)
        return self._ok({"row": row, "col": col, "text": text})

    def _cmd_clear(self, _params):
        self._stop_scroll()
        self._lcd.clear()
        self._line1 = ""
        self._line2 = ""
        return self._ok()

    def _cmd_home(self, _params):
        self._lcd.home()
        return self._ok()

    def _cmd_cursor(self, params):
        row = int(params.get("row", 0))
        col = int(params.get("col", 0))
        self._lcd.cursor_pos = (row, col)
        return self._ok({"row": row, "col": col})

    def _cmd_cursor_mode(self, params):
        mode = str(params.get("mode", "hide")).lower()
        if mode not in ("hide", "line", "blink"):
            return self._err(f"Invalid cursor mode '{mode}'. Use: hide, line, blink")
        self._lcd.cursor_mode = mode
        self._cursor_mode = mode
        return self._ok({"cursor_mode": mode})

    def _cmd_display(self, params):
        on = self._parse_bool(params.get("on", True))
        self._lcd.display_enabled = on
        self._display_on = on
        return self._ok({"display_on": on})

    def _cmd_backlight(self, params):
        on = self._parse_bool(params.get("on", True))
        self._lcd.backlight_enabled = on
        self._backlight = on
        return self._ok({"backlight": on})

    def _cmd_shift(self, params):
        amount = int(params.get("amount", 0))
        self._lcd.shift_display(amount)
        return self._ok({"shifted": amount})

    def _cmd_create_char(self, params):
        slot = int(params.get("slot", 0))
        bitmap = params.get("bitmap", [])

        if slot < 0 or slot > 7:
            return self._err("Slot must be 0-7")
        if not isinstance(bitmap, list) or len(bitmap) != 8:
            return self._err("Bitmap must be a list of 8 integers (each 0-31)")

        bitmap_tuple = tuple(int(v) for v in bitmap)
        self._lcd.create_char(slot, bitmap_tuple)
        self._custom_chars[slot] = bitmap_tuple
        return self._ok({"slot": slot, "bitmap": list(bitmap_tuple)})

    def _cmd_write_char(self, params):
        slot = int(params.get("slot", 0))
        if slot < 0 or slot > 7:
            return self._err("Slot must be 0-7")
        self._lcd.write_string(chr(slot))
        return self._ok({"slot": slot})

    def _cmd_raw_command(self, params):
        value = int(params.get("value", 0))
        self._lcd.command(value)
        return self._ok({"command": value})

    def _cmd_raw_write(self, params):
        value = int(params.get("value", 0))
        self._lcd.write(value)
        return self._ok({"wrote": value})

    def _cmd_stop_scroll(self, _params=None):
        self._stop_scroll()
        return self._ok()

    # --- Internal helpers ---------------------------------------------------

    def _align_text(self, text, align):
        """Pad text for alignment within LCD_COLS."""
        text = text[:self.LCD_COLS]
        if align == "center":
            return text.center(self.LCD_COLS)
        elif align == "right":
            return text.rjust(self.LCD_COLS)
        return text.ljust(self.LCD_COLS)

    def _parse_bool(self, value):
        """Parse various boolean representations."""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes", "on")
        return bool(value)

    def _stop_scroll(self):
        """Stop the scroll thread if running."""
        if self._scroll_thread and self._scroll_thread.is_alive():
            self._scroll_stop.set()
            self._scroll_thread.join(timeout=2)
        self._scroll_thread = None

    def _scroll_worker(self, text, row, delay):
        """Background scroll: slides text across one row."""
        padded = " " * self.LCD_COLS + text + " " * self.LCD_COLS
        for i in range(len(padded) - self.LCD_COLS + 1):
            if self._scroll_stop.is_set():
                break
            window = padded[i : i + self.LCD_COLS]
            self._lcd.cursor_pos = (row, 0)
            self._lcd.write_string(window)
            self._scroll_stop.wait(delay)
