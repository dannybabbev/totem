# Contributing to Totem: Adding Hardware Modules

This guide explains how to add new hardware components to Totem. The system is designed so that new sensors, actuators, and peripherals can be added without modifying the daemon, CLI, or existing modules.

---

## Architecture Overview

```
totem_daemon.py  ──discovers──>  hardware/*.py  ──controls──>  Physical Hardware
     │
     │ Unix socket (JSON protocol)
     │
totem_ctl.py  <──used by──  OpenClaw Agent (via exec tool)
```

Every hardware component is a **module** -- a Python class in the `hardware/` package that implements the `HardwareModule` abstract base class. The daemon auto-discovers all modules on startup by scanning `hardware/` for `HardwareModule` subclasses.

---

## The HardwareModule Interface

All modules must extend `hardware.base.HardwareModule` and implement these:

### Required Properties

| Property | Type | Description |
|----------|------|-------------|
| `name` | `str` | Short identifier used in CLI commands (e.g., `"face"`, `"lcd"`, `"servo"`) |
| `description` | `str` | Human-readable summary for capabilities discovery |

### Required Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `init()` | `() -> None` | Initialize hardware (SPI/I2C/GPIO setup). Called once at daemon startup. Raise on failure. |
| `cleanup()` | `() -> None` | Release hardware safely. Called at daemon shutdown. Must not raise. |
| `handle_command()` | `(action: str, params: dict) -> dict` | Execute a command. Return success/error dict (see below). |
| `get_state()` | `() -> dict` | Return current module state as a dictionary. |
| `get_capabilities()` | `() -> list` | Return list of supported actions with parameter schemas. |

### Helper Methods (inherited)

| Method | Usage |
|--------|-------|
| `self._ok(data=None)` | Build `{"ok": True, "data": {...}}` response |
| `self._err(message)` | Build `{"ok": False, "error": "..."}` response |

### Response Format

`handle_command` must always return one of:

```python
# Success
{"ok": True}
{"ok": True, "data": {"angle": 90}}

# Error
{"ok": False, "error": "Servo not responding"}
```

### Capabilities Format

`get_capabilities` returns a list describing each action:

```python
[
    {
        "action": "angle",
        "description": "Set servo angle in degrees",
        "params": {
            "degrees": {
                "type": "int",
                "required": True,
                "description": "Angle in degrees",
                "min": 0,
                "max": 180,
            }
        },
    },
    {
        "action": "center",
        "description": "Return to center position (90 degrees)",
        "params": {},
    },
]
```

---

## Step-by-Step: Adding a New Module

We'll walk through adding a **servo motor** as a complete example.

### Step 1: Document the Wiring

Before writing code, document the wiring. Use this template:

| Component Pin | T-Cobbler Label | Physical Pin | Function |
|---------------|-----------------|--------------|----------|
| Signal | `GPIO 18` | Pin 12 | PWM control |
| VCC | `5V` / `5V0` | Pin 2/4 | Power |
| GND | `GND` | Pin 6/9 | Ground |

**Interface type:** GPIO (PWM)
**Required packages:** `RPi.GPIO` (already in requirements.txt)

### Step 2: Create the Module File

Create `hardware/servo.py`:

```python
"""
Servo Module - SG90 Micro Servo
================================

Controls an SG90 servo motor via GPIO PWM for head/neck movement.

Hardware: SG90 servo motor
Wiring:   Signal->GPIO18(PWM0), VCC->5V, GND->GND
"""

import time
import threading

from hardware.base import HardwareModule


class ServoModule(HardwareModule):

    SERVO_PIN = 18      # GPIO pin (BCM numbering)
    FREQ = 50           # 50Hz PWM frequency for servo
    MIN_DUTY = 2.5      # Duty cycle for 0 degrees
    MAX_DUTY = 12.5     # Duty cycle for 180 degrees

    @property
    def name(self):
        return "servo"

    @property
    def description(self):
        return "SG90 servo motor for head/neck movement (0-180 degrees)"

    def init(self):
        import RPi.GPIO as GPIO
        self._GPIO = GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.SERVO_PIN, GPIO.OUT)
        self._pwm = GPIO.PWM(self.SERVO_PIN, self.FREQ)
        self._pwm.start(0)
        self._current_angle = 90
        self._anim_stop = threading.Event()
        self._anim_thread = None

    def cleanup(self):
        self._stop_animation()
        try:
            self._pwm.stop()
            self._GPIO.cleanup(self.SERVO_PIN)
        except Exception:
            pass

    def get_state(self):
        return {
            "angle": self._current_angle,
            "animation_running": self._anim_thread is not None
                                 and self._anim_thread.is_alive(),
        }

    def get_capabilities(self):
        return [
            {
                "action": "angle",
                "description": "Set servo angle",
                "params": {
                    "degrees": {
                        "type": "int",
                        "required": True,
                        "description": "Angle in degrees",
                        "min": 0,
                        "max": 180,
                    }
                },
            },
            {
                "action": "center",
                "description": "Return to center (90 degrees)",
                "params": {},
            },
            {
                "action": "nod",
                "description": "Nod motion (look down then up)",
                "params": {
                    "times": {
                        "type": "int",
                        "required": False,
                        "default": 2,
                        "description": "Number of nods",
                    },
                    "speed": {
                        "type": "float",
                        "required": False,
                        "default": 0.3,
                        "description": "Seconds per movement",
                    },
                },
            },
            {
                "action": "shake",
                "description": "Shake motion (look left then right)",
                "params": {
                    "times": {
                        "type": "int",
                        "required": False,
                        "default": 2,
                    },
                    "speed": {
                        "type": "float",
                        "required": False,
                        "default": 0.3,
                    },
                },
            },
            {
                "action": "stop",
                "description": "Stop any running servo animation",
                "params": {},
            },
        ]

    def handle_command(self, action, params):
        try:
            if action == "angle":
                degrees = int(params.get("degrees", 90))
                degrees = max(0, min(180, degrees))
                self._set_angle(degrees)
                return self._ok({"angle": degrees})

            elif action == "center":
                self._set_angle(90)
                return self._ok({"angle": 90})

            elif action == "nod":
                times = int(params.get("times", 2))
                speed = float(params.get("speed", 0.3))
                self._stop_animation()
                self._anim_stop.clear()
                self._anim_thread = threading.Thread(
                    target=self._anim_nod,
                    args=(times, speed),
                    daemon=True,
                )
                self._anim_thread.start()
                return self._ok({"animation": "nod", "times": times})

            elif action == "shake":
                times = int(params.get("times", 2))
                speed = float(params.get("speed", 0.3))
                self._stop_animation()
                self._anim_stop.clear()
                self._anim_thread = threading.Thread(
                    target=self._anim_shake,
                    args=(times, speed),
                    daemon=True,
                )
                self._anim_thread.start()
                return self._ok({"animation": "shake", "times": times})

            elif action == "stop":
                self._stop_animation()
                return self._ok()

            else:
                return self._err(f"Unknown servo action: {action}")

        except Exception as e:
            return self._err(str(e))

    # --- Internal helpers ---

    def _set_angle(self, degrees):
        duty = self.MIN_DUTY + (degrees / 180.0) * (self.MAX_DUTY - self.MIN_DUTY)
        self._pwm.ChangeDutyCycle(duty)
        time.sleep(0.3)
        self._pwm.ChangeDutyCycle(0)  # Stop jitter
        self._current_angle = degrees

    def _stop_animation(self):
        if self._anim_thread and self._anim_thread.is_alive():
            self._anim_stop.set()
            self._anim_thread.join(timeout=2)
        self._anim_thread = None

    def _anim_nod(self, times, speed):
        for _ in range(times):
            if self._anim_stop.is_set():
                break
            self._set_angle(60)
            self._anim_stop.wait(speed)
            self._set_angle(120)
            self._anim_stop.wait(speed)
        self._set_angle(90)

    def _anim_shake(self, times, speed):
        for _ in range(times):
            if self._anim_stop.is_set():
                break
            self._set_angle(45)
            self._anim_stop.wait(speed)
            self._set_angle(135)
            self._anim_stop.wait(speed)
        self._set_angle(90)
```

### Step 3: Test the Module

Restart the daemon -- it will auto-discover the new module:

```bash
# Stop daemon if running
python totem_daemon.py --stop

# Start again
python totem_daemon.py
# Output should show:
#   [OK] Discovered module: servo (SG90 servo motor for head/neck movement)
#   [OK] Initialized: servo
```

Test via CLI:

```bash
python totem_ctl.py servo angle 90
python totem_ctl.py servo nod
python totem_ctl.py servo shake
python totem_ctl.py capabilities   # Should now include servo
```

### Step 4: Update the OpenClaw Skill

Add the new commands to `skills/totem/SKILL.md` so the AI knows about them:

```markdown
## Servo (Head/Neck Movement)

\`\`\`bash
totem_ctl servo angle 90               # Set angle (0-180)
totem_ctl servo center                 # Return to center
totem_ctl servo nod                    # Nod yes
totem_ctl servo nod --times 3          # Nod 3 times
totem_ctl servo shake                  # Shake no
totem_ctl servo stop                   # Stop animation
\`\`\`
```

### Step 5: Update Documentation

1. Add the wiring table to `README.md` under Part II
2. Add the pip dependency to `requirements.txt` (if any new packages needed)
3. Check the Phase 3 checkbox in `README.md`

### Step 6: Commit

```bash
git add hardware/servo.py skills/totem/SKILL.md README.md
git commit -m "Add servo motor hardware module"
```

---

## Planned Hardware Modules

Reference list for future development. Each module follows the same pattern above.

| Module | Component | Interface | GPIO/Bus | Key Actions |
|--------|-----------|-----------|----------|-------------|
| `hardware/servo.py` | SG90 servo | GPIO PWM | Pin 18 | angle, nod, shake, center |
| `hardware/distance.py` | HC-SR04 ultrasonic | GPIO | Trigger + Echo pins | read, watch (threshold events) |
| `hardware/temperature.py` | DHT11 sensor | GPIO | Data pin | read (temp + humidity) |
| `hardware/microphone.py` | USB mic / ReSpeaker | USB / I2S | USB port | level, record, detect_speech |
| `hardware/speaker.py` | 3.5mm / USB speaker | ALSA | Audio jack / USB | play, say (TTS), volume, stop |
| `hardware/camera.py` | USB webcam | USB | USB port | capture, stream, detect_motion |
| `hardware/touch.py` | Capacitive touch (TTP223) | GPIO | Pin 17 | read, config, reset + emits events via `_emit_event()` |
| `hardware/neopixel.py` | WS2812B LED strip | GPIO PWM | Pin 18* | color, rainbow, pulse, off |

*Note: NeoPixel and Servo both use PWM. If using both, assign them to different PWM channels or use a PCA9685 PWM driver board over I2C.

---

## Wiring Documentation Template

When adding a new module, document the wiring using this template:

```markdown
### Component Name (e.g., HC-SR04 Ultrasonic Sensor)

*Connects via [interface type]. Use [location on breadboard].*

| Component Pin | T-Cobbler Label | Physical Pin | Function |
|---------------|-----------------|--------------|----------|
| VCC           | `5V`            | Pin 2/4      | Power    |
| GND           | `GND`           | Pin 6/9      | Ground   |
| TRIG          | `GPIO 23`       | Pin 16       | Trigger  |
| ECHO          | `GPIO 24`*      | Pin 18       | Echo     |

*Note: ECHO returns 5V signal. Use a voltage divider (1kΩ + 2kΩ) to bring it
down to 3.3V for the Pi's GPIO input.*

**Required packages:** `RPi.GPIO` (already installed)
**Test:** `python totem_ctl.py distance read`
```

---

## Design Guidelines

1. **Two tiers of control.** Every module should expose both high-level convenience actions (named presets, common operations) and low-level primitives (direct hardware access). This gives the AI maximum creative freedom.

2. **Thread safety.** The daemon routes commands through a lock. If your module runs background threads (animations, continuous readings), use `threading.Event` for clean stop signaling.

3. **Graceful degradation.** If hardware init fails, the daemon skips the module and continues. The `cleanup()` method must not raise exceptions.

4. **Capabilities are self-documenting.** The `get_capabilities()` return value is what the AI sees when it runs `totem_ctl capabilities`. Include clear descriptions, type info, valid ranges, and defaults.

5. **State tracking.** The `get_state()` method should return enough information for the AI to understand what the hardware is currently doing before issuing new commands.

6. **No changes to daemon or CLI.** The daemon auto-discovers modules. The CLI sends raw JSON via `--json` mode for any module. You only need to add argparse subcommands to `totem_ctl.py` if you want named CLI shortcuts (optional but recommended).

7. **Update the skill.** After adding a module, add its commands to `skills/totem/SKILL.md` so the OpenClaw agent knows about the new hardware.

8. **Sensor event pattern (for modules that detect things).** Sensors like touch, distance, and microphone need to notify the AI agent when something happens (touched, speech detected, object nearby). Use the built-in event system:

   **How it works:**
   - Call `self._emit_event(event_type, data)` from your module when something is detected.
   - The daemon receives the event via the callback set during init.
   - The daemon runs `openclaw system event --text "..." --mode now` to inject a `System:` line into the agent's main conversation session and trigger an immediate heartbeat.
   - The agent sees the event in context of the ongoing conversation and can react (e.g., change face expression, write to LCD, respond in chat).

   **Example (from `hardware/touch.py`):**
   ```python
   def _on_touch(self, channel):
       self._touch_count += 1
       self._is_touched = True
       self._last_touch_time = time.time()
       self._emit_event("touched", {
           "pin": self.TOUCH_PIN,
           "touch_count": self._touch_count,
           "timestamp": self._last_touch_time,
       })
   ```

   **For a microphone module**, the same pattern applies:
   ```python
   # In hardware/microphone.py
   def _on_speech_detected(self):
       self._emit_event("speech_detected", {
           "timestamp": time.time(),
           "duration_ms": self._speech_duration,
           "level": self._peak_level,
       })
   ```

   **Key rules for sensor events:**
   - Always debounce noisy sensors to avoid flooding the agent with events.
   - Include a `timestamp` in every event payload.
   - Use descriptive `event_type` strings: `"touched"`, `"released"`, `"speech_detected"`, `"object_nearby"`, `"temperature_alert"`.
   - The `_emit_event()` call is non-blocking -- the daemon dispatches the notification in a background thread.
   - Events are also stored in the daemon's internal event queue, accessible via `totem_ctl events`.

---

## Event Notification Workflow

When a sensor module detects something noteworthy (touch, temperature spike, speech, etc.), the event flows through this pipeline to reach the AI agent:

```
Hardware Module                Daemon (_on_event)              OpenClaw Agent
     │                              │                              │
     │  _emit_event("type", data)   │                              │
     │ ──────────────────────────>   │                              │
     │                              │  1. Store in event queue      │
     │                              │  2. Physical reaction         │
     │                              │     (face/LCD, instant)       │
     │                              │  3. Dispatch to OpenClaw      │
     │                              │     (background thread)       │
     │                              │                              │
     │                              │  openclaw system event        │
     │                              │  --text "..." --mode now      │
     │                              │ ──────────────────────────>   │
     │                              │                              │  Sees "System:" line
     │                              │                              │  in conversation,
     │                              │                              │  reacts with totem_ctl
```

### Step-by-step

1. **Module emits event.** The hardware module calls `self._emit_event("event_type", {"key": "value", "timestamp": time.time()})`. This is non-blocking — the daemon's callback runs in the module's thread context.

2. **Daemon stores it.** `_on_event()` in `totem_daemon.py` appends the event to an internal queue (capped at 100 entries). Events are readable via `totem_ctl events` or `totem_ctl events --peek`.

3. **Daemon reacts physically (optional).** Before the AI agent even knows, the daemon can trigger an instant hardware reaction — change the face expression, write to the LCD, etc. This gives the robot sub-second physical responsiveness. Each event type has its own reaction block in `_on_event()`.

4. **Daemon dispatches to OpenClaw.** In a background thread, the daemon runs:
   ```bash
   openclaw system event --text "<descriptive message>" --mode now
   ```
   This injects a `System:` line into the agent's active conversation and triggers an immediate heartbeat, so the agent processes it right away (no waiting for the next poll). See [OpenClaw CLI: system event](https://docs.openclaw.ai/cli/system) for full documentation.

5. **Agent reacts.** The OpenClaw agent sees the `System:` line in context and can run `totem_ctl` commands to react — change the face, write to LCD, respond in chat, etc.

### Cooldown

The daemon enforces a **5-second cooldown** (`self._notify_cooldown`) between OpenClaw notifications. If multiple events fire within 5 seconds, only the first one dispatches — the rest are logged but skipped. This prevents flooding the agent with rapid-fire events (e.g., a sensor bouncing around a threshold).

The cooldown is shared across all event types. Physical reactions still happen even during cooldown — only the OpenClaw dispatch is suppressed.

### Adding a new event type to the daemon

When you add a new sensor module that emits events, you need to add a handler in `_on_event()` in `totem_daemon.py`:

1. **Add an `elif` block** for your event type(s) after the existing handlers:

   ```python
   # In _on_event():
   elif event_type == "your_event_type":
       now = time.time()
       if now - self._last_notify_time >= self._notify_cooldown:
           self._last_notify_time = now

           # Optional: instant physical reaction
           with self._lock:
               if "face" in self._modules:
                   self._modules["face"].handle_command("expression", {"name": "surprised"})
               if "lcd" in self._modules:
                   self._modules["lcd"].handle_command("write", {
                       "line1": "Alert!", "line2": "Details here", "align": "center",
                   })

           # Dispatch to OpenClaw
           if self._notify_enabled and self._openclaw_bin:
               thread = threading.Thread(
                   target=self._dispatch_openclaw_event,
                   args=(event,),
                   daemon=True,
               )
               thread.start()
   ```

2. **Add data formatting** in `_dispatch_openclaw_event()` so your event's payload is included in the text message sent to OpenClaw:

   ```python
   # In _dispatch_openclaw_event():
   if "your_data_key" in data:
       parts.append(f"Your value: {data['your_data_key']}.")
   ```

   The text message is built as a list of `parts` joined by spaces. The first part is always `"<module> sensor: <event_type> at <timestamp>."` and the last part is always `"React to this physically -- use totem_ctl to show a reaction on the face and LCD."`
