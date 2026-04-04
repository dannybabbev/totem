"""
Touch Module - TTP223 Capacitive Touch Sensor
===============================================

Detects touch and release events via GPIO interrupt. Emits events to the
daemon which notifies OpenClaw so the agent can react in real-time.

Hardware: TTP223 capacitive touch sensor (active high)
Wiring:   SIG->GPIO17, VCC->3.3V, GND->GND
Power:    3.3V ONLY -- do NOT connect to the 5V rail.
"""

import time
import threading

from hardware.base import HardwareModule


class TouchModule(HardwareModule):

    TOUCH_PIN = 17       # GPIO pin (BCM numbering)
    DEFAULT_DEBOUNCE = 200  # Debounce in milliseconds

    # --- HardwareModule interface -------------------------------------------

    @property
    def name(self):
        return "touch"

    @property
    def description(self):
        return "TTP223 capacitive touch sensor on GPIO 17 (3.3V, active high)"

    def init(self):
        import lgpio
        self._lgpio = lgpio

        self._chip = lgpio.gpiochip_open(0)
        lgpio.gpio_claim_alert(self._chip, self.TOUCH_PIN, lgpio.BOTH_EDGES, lgpio.SET_PULL_DOWN)
        self._cb = lgpio.callback(self._chip, self.TOUCH_PIN, lgpio.BOTH_EDGES, self._gpio_callback)

        # State tracking
        self._is_touched = False
        self._touch_count = 0
        self._last_touch_time = None
        self._last_release_time = None
        self._debounce_ms = self.DEFAULT_DEBOUNCE
        self._last_edge_time = 0  # software debounce
        self._lock = threading.Lock()

    def cleanup(self):
        try:
            self._cb.cancel()
        except Exception:
            pass
        try:
            self._lgpio.gpiochip_close(self._chip)
        except Exception:
            pass

    def get_state(self):
        return {
            "is_touched": self._is_touched,
            "touch_count": self._touch_count,
            "last_touch_time": self._last_touch_time,
            "last_release_time": self._last_release_time,
            "pin": self.TOUCH_PIN,
            "debounce_ms": self._debounce_ms,
        }

    def get_capabilities(self):
        return [
            {
                "action": "read",
                "description": "Read current touch sensor state",
                "params": {},
            },
            {
                "action": "config",
                "description": "Configure touch sensor settings",
                "params": {
                    "debounce_ms": {
                        "type": "int",
                        "required": False,
                        "description": "Debounce time in milliseconds",
                        "default": self.DEFAULT_DEBOUNCE,
                        "min": 50,
                        "max": 2000,
                    },
                },
            },
            {
                "action": "reset",
                "description": "Reset the touch counter to zero",
                "params": {},
            },
        ]

    def handle_command(self, action, params):
        try:
            if action == "read":
                return self._cmd_read(params)
            elif action == "config":
                return self._cmd_config(params)
            elif action == "reset":
                return self._cmd_reset(params)
            else:
                return self._err(f"Unknown touch action: {action}")
        except Exception as e:
            return self._err(str(e))

    # --- Commands -----------------------------------------------------------

    def _cmd_read(self, _params):
        return self._ok(self.get_state())

    def _cmd_config(self, params):
        debounce = params.get("debounce_ms")
        if debounce is not None:
            debounce = max(50, min(2000, int(debounce)))
            self._debounce_ms = debounce

        return self._ok({"debounce_ms": self._debounce_ms})

    def _cmd_reset(self, _params):
        with self._lock:
            self._touch_count = 0
        return self._ok({"touch_count": 0})

    # --- GPIO interrupt handler ---------------------------------------------

    def _gpio_callback(self, chip, gpio, level, tick):
        """
        Called by lgpio on both rising and falling edges.
        level: 0 = LOW (released), 1 = HIGH (touched), 2 = watchdog timeout.
        """
        now = time.time()

        # Software debounce
        if (now - self._last_edge_time) * 1000 < self._debounce_ms:
            return
        self._last_edge_time = now

        with self._lock:
            if level == 1 and not self._is_touched:
                # Touch detected (rising edge)
                self._is_touched = True
                self._touch_count += 1
                self._last_touch_time = now

                self._emit_event("touched", {
                    "pin": self.TOUCH_PIN,
                    "touch_count": self._touch_count,
                    "timestamp": now,
                })

            elif level == 0 and self._is_touched:
                # Release detected (falling edge)
                self._is_touched = False
                self._last_release_time = now

                duration_ms = None
                if self._last_touch_time is not None:
                    duration_ms = int((now - self._last_touch_time) * 1000)

                self._emit_event("released", {
                    "pin": self.TOUCH_PIN,
                    "touch_count": self._touch_count,
                    "duration_ms": duration_ms,
                    "timestamp": now,
                })
