"""
Distance Module - HC-SR04 Ultrasonic Sensor
============================================

Continuously polls the HC-SR04 in a background thread. Detects wave gestures
using an adaptive-baseline state machine. Commands return cached state instantly
and never block on hardware.

Hardware: HC-SR04 ultrasonic sensor
Wiring:   VCC->5V, GND->GND, TRIG->GPIO23, ECHO->GPIO24
          ECHO returns 5V -- step down to 3.3V via voltage divider (1kΩ + 2kΩ).
"""

import time
import threading

from hardware.base import HardwareModule


class DistanceModule(HardwareModule):

    TRIG_PIN = 23
    ECHO_PIN = 24
    ECHO_TIMEOUT = 0.05           # 50ms max echo wait (~8m max range)
    MIN_VALID_DIST = 2            # cm — ignore sub-2cm noise spikes

    DEFAULT_INTERVAL          = 0.3    # seconds between polls
    MIN_INTERVAL              = 0.1
    BASELINE_ALPHA            = 0.05   # EMA weight — slow adaptation keeps baseline stable during waves
    DEFAULT_WAVE_THRESHOLD    = 10     # cm below baseline required to count as "hand present"
    DEFAULT_DEBOUNCE_COUNT    = 3      # consecutive readings needed to change state
    DEFAULT_MAX_WAVE_DURATION = 2.0    # seconds — hand must withdraw within this window

    # --- HardwareModule interface -------------------------------------------

    @property
    def name(self):
        return "distance"

    @property
    def description(self):
        return "HC-SR04 ultrasonic sensor with wave detection (TRIG=GPIO23, ECHO=GPIO24)"

    def init(self):
        import lgpio
        self._lgpio = lgpio

        self._chip = lgpio.gpiochip_open(0)
        lgpio.gpio_claim_output(self._chip, self.TRIG_PIN, 0)
        lgpio.gpio_claim_input(self._chip, self.ECHO_PIN)

        # Latest reading
        self._distance_cm = None
        self._baseline_cm = None
        self._last_read_time = None

        # Wave detection state machine
        self._wave_state = "IDLE"   # "IDLE" or "NEAR"
        self._wave_debounce = 0
        self._wave_start = None
        self._wave_count = 0
        self._last_wave_time = None

        # Tunable config
        self._interval          = self.DEFAULT_INTERVAL
        self._wave_threshold    = self.DEFAULT_WAVE_THRESHOLD
        self._debounce_count    = self.DEFAULT_DEBOUNCE_COUNT
        self._max_wave_duration = self.DEFAULT_MAX_WAVE_DURATION

        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._poll_thread.start()

    def cleanup(self):
        self._stop_event.set()
        if self._poll_thread and self._poll_thread.is_alive():
            self._poll_thread.join(timeout=5)
        try:
            self._lgpio.gpiochip_close(self._chip)
        except Exception:
            pass

    def get_state(self):
        with self._lock:
            return {
                "distance_cm":      self._distance_cm,
                "baseline_cm":      round(self._baseline_cm, 1) if self._baseline_cm is not None else None,
                "wave_state":       self._wave_state,
                "wave_count":       self._wave_count,
                "last_wave_time":   self._last_wave_time,
                "last_read_time":   self._last_read_time,
                "pin_trig":         self.TRIG_PIN,
                "pin_echo":         self.ECHO_PIN,
                "interval":         self._interval,
                "wave_threshold":   self._wave_threshold,
                "debounce_count":   self._debounce_count,
                "max_wave_duration": self._max_wave_duration,
            }

    def get_capabilities(self):
        return [
            {
                "action": "read",
                "description": "Read current distance, baseline, wave state and count (non-blocking)",
                "params": {},
            },
            {
                "action": "reset",
                "description": "Reset wave counter to zero",
                "params": {},
            },
            {
                "action": "config",
                "description": "Tune wave detection parameters",
                "params": {
                    "interval": {
                        "type": "float", "required": False,
                        "description": "Poll interval in seconds",
                        "min": self.MIN_INTERVAL, "default": self.DEFAULT_INTERVAL,
                    },
                    "wave_threshold": {
                        "type": "float", "required": False,
                        "description": "cm below baseline to count as hand present",
                        "default": self.DEFAULT_WAVE_THRESHOLD,
                    },
                    "debounce_count": {
                        "type": "int", "required": False,
                        "description": "Consecutive readings needed to change state",
                        "default": self.DEFAULT_DEBOUNCE_COUNT,
                    },
                    "max_wave_duration": {
                        "type": "float", "required": False,
                        "description": "Max seconds hand may be present to qualify as a wave",
                        "default": self.DEFAULT_MAX_WAVE_DURATION,
                    },
                },
            },
        ]

    def handle_command(self, action, params):
        try:
            if action == "read":
                return self._cmd_read()
            elif action == "reset":
                return self._cmd_reset()
            elif action == "config":
                return self._cmd_config(params)
            else:
                return self._err(f"Unknown distance action: {action}")
        except Exception as e:
            return self._err(str(e))

    # --- Commands -----------------------------------------------------------

    def _cmd_read(self):
        with self._lock:
            return self._ok({
                "distance_cm":    self._distance_cm,
                "baseline_cm":    round(self._baseline_cm, 1) if self._baseline_cm is not None else None,
                "wave_state":     self._wave_state,
                "wave_count":     self._wave_count,
                "last_wave_time": self._last_wave_time,
            })

    def _cmd_reset(self):
        with self._lock:
            self._wave_count = 0
        return self._ok({"wave_count": 0})

    def _cmd_config(self, params):
        if "interval" in params:
            self._interval = max(self.MIN_INTERVAL, float(params["interval"]))
        if "wave_threshold" in params:
            self._wave_threshold = float(params["wave_threshold"])
        if "debounce_count" in params:
            self._debounce_count = int(params["debounce_count"])
        if "max_wave_duration" in params:
            self._max_wave_duration = float(params["max_wave_duration"])
        return self._ok({
            "interval":          self._interval,
            "wave_threshold":    self._wave_threshold,
            "debounce_count":    self._debounce_count,
            "max_wave_duration": self._max_wave_duration,
        })

    # --- Sensor reading -----------------------------------------------------

    def _read_distance(self):
        """Send a 10µs trigger pulse and time the echo. Returns cm or None on timeout."""
        lgpio = self._lgpio

        lgpio.gpio_write(self._chip, self.TRIG_PIN, 1)
        time.sleep(0.00001)
        lgpio.gpio_write(self._chip, self.TRIG_PIN, 0)

        deadline = time.time() + self.ECHO_TIMEOUT
        while lgpio.gpio_read(self._chip, self.ECHO_PIN) == 0:
            if time.time() > deadline:
                return None

        start = time.time()
        deadline = time.time() + self.ECHO_TIMEOUT
        while lgpio.gpio_read(self._chip, self.ECHO_PIN) == 1:
            if time.time() > deadline:
                return None

        dist = round(((time.time() - start) * 34300) / 2, 1)
        return dist if dist >= self.MIN_VALID_DIST else None

    # --- Background polling -------------------------------------------------

    def _poll_loop(self):
        while not self._stop_event.is_set():
            dist = self._read_distance()
            wave_event = None

            if dist is not None:
                now = time.time()
                with self._lock:
                    self._distance_cm = dist
                    self._last_read_time = now
                    if self._baseline_cm is None:
                        self._baseline_cm = dist
                    wave_event = self._step_wave_state(dist, now)

            # Emit outside the lock — _emit_event may invoke the daemon callback
            if wave_event:
                self._emit_event("wave_detected", wave_event)

            self._stop_event.wait(self._interval)

    def _step_wave_state(self, dist, now):
        """
        Advance the wave state machine by one reading.
        Must be called under self._lock.
        Returns wave event data dict if a wave just completed, else None.
        """
        near = dist < (self._baseline_cm - self._wave_threshold)

        if self._wave_state == "IDLE":
            # Update baseline only while no hand is present
            self._baseline_cm = (
                (1 - self.BASELINE_ALPHA) * self._baseline_cm
                + self.BASELINE_ALPHA * dist
            )

            if near:
                self._wave_debounce += 1
                if self._wave_debounce >= self._debounce_count:
                    self._wave_state = "NEAR"
                    self._wave_start = now
                    self._wave_debounce = 0
            else:
                self._wave_debounce = 0

        elif self._wave_state == "NEAR":
            if not near:
                self._wave_debounce += 1
                if self._wave_debounce >= self._debounce_count:
                    elapsed = now - self._wave_start
                    event_data = None
                    if elapsed < self._max_wave_duration:
                        self._wave_count += 1
                        self._last_wave_time = now
                        event_data = {
                            "wave_count":  self._wave_count,
                            "distance_cm": dist,
                            "timestamp":   now,
                        }
                    self._wave_state = "IDLE"
                    self._wave_debounce = 0
                    return event_data
            else:
                self._wave_debounce = 0

            # Hand held too long — not a wave, reset
            if self._wave_state == "NEAR" and now - self._wave_start > self._max_wave_duration:
                self._wave_state = "IDLE"
                self._wave_debounce = 0

        return None
