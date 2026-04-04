"""
Temperature Module - DHT11 Temperature & Humidity Sensor
========================================================

Reads temperature and humidity from a DHT11 sensor via GPIO.
Supports one-shot reads and background monitoring with threshold alerts.

Hardware: DHT11 3-pin breakout board (built-in pull-up resistor)
Wiring:   +->3.3V, out->GPIO4, -->GND
Power:    3.3V recommended (keeps data line safe for Pi GPIO)
"""

import time
import threading

from hardware.base import HardwareModule


class TemperatureModule(HardwareModule):

    DATA_PIN = 4            # GPIO pin (BCM numbering)
    MIN_READ_INTERVAL = 2   # DHT11 hardware minimum (seconds)
    DEFAULT_INTERVAL = 3    # Default polling interval (seconds)

    # --- HardwareModule interface -------------------------------------------

    @property
    def name(self):
        return "temperature"

    @property
    def description(self):
        return "DHT11 temperature & humidity sensor on GPIO 4 (3.3V)"

    def init(self):
        import board
        import adafruit_dht

        self._sensor = adafruit_dht.DHT11(board.D4)

        # Latest readings
        self._temperature_c = None
        self._humidity = None
        self._last_read_time = None

        # Watch mode
        self._watching = False
        self._watch_thread = None
        self._stop_event = threading.Event()
        self._interval = self.DEFAULT_INTERVAL
        self._thresholds = {}
        self._lock = threading.Lock()

        # Track which thresholds have been crossed (to emit only on transition)
        self._alert_state = {}

    def cleanup(self):
        self._stop_watching()
        try:
            self._sensor.exit()
        except Exception:
            pass

    def get_state(self):
        temperature_f = None
        if self._temperature_c is not None:
            temperature_f = round(self._temperature_c * 9.0 / 5.0 + 32.0, 1)
        return {
            "temperature_c": self._temperature_c,
            "temperature_f": temperature_f,
            "humidity": self._humidity,
            "last_read_time": self._last_read_time,
            "pin": self.DATA_PIN,
            "watching": self._watching,
            "interval": self._interval,
            "thresholds": self._thresholds,
        }

    def get_capabilities(self):
        return [
            {
                "action": "read",
                "description": "Read current temperature and humidity",
                "params": {
                    "unit": {
                        "type": "str",
                        "required": False,
                        "description": "Temperature unit",
                        "options": ["C", "F"],
                        "default": "C",
                    },
                },
            },
            {
                "action": "watch",
                "description": "Start background monitoring with optional threshold alerts",
                "params": {
                    "temp_min": {
                        "type": "float",
                        "required": False,
                        "description": "Alert when temperature drops below this (Celsius)",
                    },
                    "temp_max": {
                        "type": "float",
                        "required": False,
                        "description": "Alert when temperature rises above this (Celsius)",
                    },
                    "humidity_min": {
                        "type": "float",
                        "required": False,
                        "description": "Alert when humidity drops below this (%)",
                    },
                    "humidity_max": {
                        "type": "float",
                        "required": False,
                        "description": "Alert when humidity rises above this (%)",
                    },
                    "interval": {
                        "type": "float",
                        "required": False,
                        "description": "Polling interval in seconds (minimum 2)",
                        "default": self.DEFAULT_INTERVAL,
                        "min": self.MIN_READ_INTERVAL,
                    },
                },
            },
            {
                "action": "stop",
                "description": "Stop background monitoring",
                "params": {},
            },
            {
                "action": "config",
                "description": "Configure polling interval",
                "params": {
                    "interval": {
                        "type": "float",
                        "required": False,
                        "description": "Polling interval in seconds (minimum 2)",
                        "default": self.DEFAULT_INTERVAL,
                        "min": self.MIN_READ_INTERVAL,
                    },
                },
            },
        ]

    def handle_command(self, action, params):
        try:
            if action == "read":
                return self._cmd_read(params)
            elif action == "watch":
                return self._cmd_watch(params)
            elif action == "stop":
                return self._cmd_stop(params)
            elif action == "config":
                return self._cmd_config(params)
            else:
                return self._err(f"Unknown temperature action: {action}")
        except Exception as e:
            return self._err(str(e))

    # --- Commands -----------------------------------------------------------

    def _cmd_read(self, params):
        unit = params.get("unit", "C").upper()
        if unit not in ("C", "F"):
            return self._err(f"Invalid unit: {unit}. Use 'C' or 'F'.")

        self._do_read()

        if self._temperature_c is None:
            return self._err("Failed to read sensor. Try again in a few seconds.")

        temperature_f = round(self._temperature_c * 9.0 / 5.0 + 32.0, 1)
        data = {
            "temperature_c": self._temperature_c,
            "temperature_f": temperature_f,
            "humidity": self._humidity,
            "unit": unit,
            "timestamp": self._last_read_time,
        }
        return self._ok(data)

    def _cmd_watch(self, params):
        # Stop any existing watch
        self._stop_watching()

        # Set thresholds
        self._thresholds = {}
        for key in ("temp_min", "temp_max", "humidity_min", "humidity_max"):
            val = params.get(key)
            if val is not None:
                self._thresholds[key] = float(val)

        # Set interval
        interval = params.get("interval")
        if interval is not None:
            self._interval = max(self.MIN_READ_INTERVAL, float(interval))

        # Reset alert state
        self._alert_state = {}

        # Start background thread
        self._stop_event.clear()
        self._watching = True
        self._watch_thread = threading.Thread(
            target=self._watch_loop, daemon=True
        )
        self._watch_thread.start()

        return self._ok({
            "watching": True,
            "interval": self._interval,
            "thresholds": self._thresholds,
        })

    def _cmd_stop(self, _params):
        was_watching = self._watching
        self._stop_watching()
        return self._ok({"watching": False, "was_watching": was_watching})

    def _cmd_config(self, params):
        interval = params.get("interval")
        if interval is not None:
            self._interval = max(self.MIN_READ_INTERVAL, float(interval))
        return self._ok({"interval": self._interval})

    # --- Sensor reading -----------------------------------------------------

    def _do_read(self):
        """Read the sensor, updating cached values. Retries once on failure."""
        for attempt in range(2):
            try:
                temp = self._sensor.temperature
                hum = self._sensor.humidity
                if temp is not None and hum is not None:
                    with self._lock:
                        self._temperature_c = round(float(temp), 1)
                        self._humidity = round(float(hum), 1)
                        self._last_read_time = time.time()
                    return True
            except RuntimeError:
                # DHT sensors intermittently fail — retry after short delay
                time.sleep(self.MIN_READ_INTERVAL)
        return False

    # --- Background watch ---------------------------------------------------

    def _watch_loop(self):
        """Background polling loop. Reads sensor and checks thresholds."""
        while not self._stop_event.is_set():
            if self._do_read():
                self._check_thresholds()
            self._stop_event.wait(self._interval)

    def _check_thresholds(self):
        """Emit events when thresholds are crossed (only on transition)."""
        with self._lock:
            temp = self._temperature_c
            hum = self._humidity
            timestamp = self._last_read_time

        if temp is None or hum is None:
            return

        # Temperature thresholds
        if "temp_max" in self._thresholds:
            key = "temp_above"
            crossed = temp > self._thresholds["temp_max"]
            if crossed and not self._alert_state.get(key):
                self._alert_state[key] = True
                self._emit_event("temperature_alert", {
                    "temperature_c": temp,
                    "direction": "above",
                    "threshold": self._thresholds["temp_max"],
                    "timestamp": timestamp,
                })
            elif not crossed:
                self._alert_state[key] = False

        if "temp_min" in self._thresholds:
            key = "temp_below"
            crossed = temp < self._thresholds["temp_min"]
            if crossed and not self._alert_state.get(key):
                self._alert_state[key] = True
                self._emit_event("temperature_alert", {
                    "temperature_c": temp,
                    "direction": "below",
                    "threshold": self._thresholds["temp_min"],
                    "timestamp": timestamp,
                })
            elif not crossed:
                self._alert_state[key] = False

        # Humidity thresholds
        if "humidity_max" in self._thresholds:
            key = "hum_above"
            crossed = hum > self._thresholds["humidity_max"]
            if crossed and not self._alert_state.get(key):
                self._alert_state[key] = True
                self._emit_event("humidity_alert", {
                    "humidity": hum,
                    "direction": "above",
                    "threshold": self._thresholds["humidity_max"],
                    "timestamp": timestamp,
                })
            elif not crossed:
                self._alert_state[key] = False

        if "humidity_min" in self._thresholds:
            key = "hum_below"
            crossed = hum < self._thresholds["humidity_min"]
            if crossed and not self._alert_state.get(key):
                self._alert_state[key] = True
                self._emit_event("humidity_alert", {
                    "humidity": hum,
                    "direction": "below",
                    "threshold": self._thresholds["humidity_min"],
                    "timestamp": timestamp,
                })
            elif not crossed:
                self._alert_state[key] = False

    def _stop_watching(self):
        """Stop the background watch thread cleanly."""
        if self._watching:
            self._stop_event.set()
            if self._watch_thread and self._watch_thread.is_alive():
                self._watch_thread.join(timeout=5)
            self._watching = False
            self._watch_thread = None
