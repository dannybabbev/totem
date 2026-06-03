#!/usr/bin/env python3
"""
Totem Daemon
============

Long-running background service that manages all hardware modules.
Listens on a Unix socket for JSON commands from totem_ctl.

Usage:
    python totem_daemon.py              # Start the daemon
    python totem_daemon.py --status     # Check if daemon is running
    python totem_daemon.py --stop       # Stop a running daemon

Socket: /tmp/totem.sock
PID file: /tmp/totem.pid

Protocol:
    Client sends JSON:  {"module": "face", "action": "expression", "params": {"name": "happy"}}
    Server responds:    {"ok": true, "data": {"expression": "happy"}}

    Batch:   {"batch": [cmd1, cmd2, ...]}
    System:  {"action": "capabilities"} | {"action": "status"} | {"action": "ping"}
"""

import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import time
import threading
import importlib
import inspect
import traceback

from hardware.base import HardwareModule

SOCKET_PATH = "/tmp/totem.sock"
PID_FILE = "/tmp/totem.pid"
BUFFER_SIZE = 65536

# Per-module OpenClaw dispatch defaults.
# Set a module to False to disable push notifications at startup.
# Can also be toggled at runtime: totem_ctl notify <module> on|off
NOTIFY_DEFAULTS = {
    "touch":    True,
    "distance": True,
}


class TotemDaemon:
    """Main daemon that discovers, initializes, and routes commands to hardware modules."""

    def __init__(self):
        self._modules = {}  # name -> HardwareModule instance
        self._server = None
        self._running = False
        self._lock = threading.Lock()

        # Event system
        self._events = []  # timestamped event log
        self._events_lock = threading.Lock()
        self._notify_enabled = os.environ.get("TOTEM_NOTIFY_ENABLED", "true").lower() != "false"
        self._module_notify = dict(NOTIFY_DEFAULTS)  # per-module toggle, see NOTIFY_DEFAULTS
        self._openclaw_bin = shutil.which("openclaw")
        self._last_notify_time = 0  # timestamp of last OpenClaw notification
        self._notify_cooldown = 5   # minimum seconds between notifications

    # --- Module discovery and initialization --------------------------------

    def discover_modules(self):
        """
        Auto-discover HardwareModule subclasses from the hardware package.
        Scans all .py files in hardware/ for classes that extend HardwareModule.
        """
        import hardware
        hardware_dir = os.path.dirname(hardware.__file__)

        for filename in os.listdir(hardware_dir):
            if filename.startswith("_") or not filename.endswith(".py"):
                continue
            module_name = filename[:-3]  # strip .py
            try:
                mod = importlib.import_module(f"hardware.{module_name}")
                for attr_name in dir(mod):
                    attr = getattr(mod, attr_name)
                    if (
                        inspect.isclass(attr)
                        and issubclass(attr, HardwareModule)
                        and attr is not HardwareModule
                    ):
                        instance = attr()
                        self._modules[instance.name] = instance
                        print(f"  [OK] Discovered module: {instance.name} ({instance.description})")
            except Exception as e:
                print(f"  [WARN] Failed to load hardware.{module_name}: {e}")

    def init_modules(self):
        """Initialize all discovered hardware modules."""
        for name, module in list(self._modules.items()):
            try:
                module.init()
                # Wire up event callback so sensor modules can emit events
                module.set_event_callback(self._on_event)
                print(f"  [OK] Initialized: {name}")
            except Exception as e:
                print(f"  [FAIL] Could not init {name}: {e}")
                del self._modules[name]

    def cleanup_modules(self):
        """Cleanup all modules safely."""
        for name, module in self._modules.items():
            try:
                module.cleanup()
                print(f"  [OK] Cleaned up: {name}")
            except Exception as e:
                print(f"  [WARN] Cleanup failed for {name}: {e}")

    # --- Event system -------------------------------------------------------

    def _on_event(self, module_name, event_type, data):
        """
        Called by hardware modules via _emit_event().
        Stores the event, fires non-blocking physical reactions, and optionally
        dispatches to OpenClaw (respects per-module notify toggle).
        """
        event = {
            "module": module_name,
            "event": event_type,
            "data": data,
            "timestamp": time.time(),
            "timestamp_iso": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }

        # Store in event queue
        with self._events_lock:
            self._events.append(event)
            if len(self._events) > 100:
                self._events = self._events[-100:]

        print(f"  [EVENT] {module_name}: {event_type} {data}")

        def _dispatch_if_allowed():
            if self._notify_enabled and self._module_notify.get(module_name, True) and self._openclaw_bin:
                threading.Thread(
                    target=self._dispatch_openclaw_event,
                    args=(event,),
                    daemon=True,
                ).start()

        if event_type == "touched":
            now = time.time()
            if now - self._last_notify_time >= self._notify_cooldown:
                self._last_notify_time = now
                threading.Thread(
                    target=self._react_and_restore,
                    args=("surprised", "I felt that!", "Thinking..."),
                    daemon=True,
                ).start()
                _dispatch_if_allowed()
            else:
                print(f"  [SKIP] Touch cooldown ({self._notify_cooldown}s)")

        elif event_type == "wave_detected":
            now = time.time()
            if now - self._last_notify_time >= self._notify_cooldown:
                self._last_notify_time = now
                wave_num = data.get("wave_count", "?")
                threading.Thread(
                    target=self._react_and_restore,
                    args=("happy", "Hey, I saw that!", f"Wave #{wave_num} :)"),
                    daemon=True,
                ).start()
                _dispatch_if_allowed()
            else:
                print(f"  [SKIP] Wave cooldown ({self._notify_cooldown}s)")

        elif event_type in ("temperature_alert", "humidity_alert"):
            now = time.time()
            if now - self._last_notify_time >= self._notify_cooldown:
                self._last_notify_time = now
                d = event["data"]
                if event_type == "temperature_alert":
                    line1 = f"Temp {d.get('direction', '?')}"
                    line2 = f"{d.get('temperature_c')}C > {d.get('threshold')}C"
                else:
                    line1 = f"Humidity {d.get('direction', '?')}"
                    line2 = f"{d.get('humidity')}% > {d.get('threshold')}%"
                with self._lock:
                    if "lcd" in self._modules:
                        self._modules["lcd"].handle_command("write", {
                            "line1": line1, "line2": line2, "align": "center",
                        })
                _dispatch_if_allowed()
            else:
                print(f"  [SKIP] Alert cooldown ({self._notify_cooldown}s)")

    def _react_and_restore(self, face_expr, lcd_line1, lcd_line2, hold_sec=1.5):
        """
        Apply a physical reaction on face + LCD, hold for hold_sec, then restore
        the previous state. Runs in a background thread — never blocks the caller.
        The lock is released during the sleep so CLI commands remain responsive.
        """
        # Step 1: snapshot current state and apply reaction
        with self._lock:
            face_state = self._modules["face"].get_state() if "face" in self._modules else None
            lcd_state  = self._modules["lcd"].get_state()  if "lcd"  in self._modules else None
            if face_state is not None:
                self._modules["face"].handle_command("expression", {"name": face_expr})
            if lcd_state is not None:
                self._modules["lcd"].handle_command("write", {
                    "line1": lcd_line1, "line2": lcd_line2, "align": "center",
                })

        # Step 2: hold (lock released so other commands go through)
        time.sleep(hold_sec)

        # Step 3: restore previous state
        with self._lock:
            if face_state is not None and "face" in self._modules:
                prev_expr = face_state.get("current_expression") or "neutral"
                self._modules["face"].handle_command("expression", {"name": prev_expr})
            if lcd_state is not None and "lcd" in self._modules:
                self._modules["lcd"].handle_command("write", {
                    "line1": lcd_state.get("line1", ""),
                    "line2": lcd_state.get("line2", ""),
                })

    # https://docs.openclaw.ai/cli/system
    def _dispatch_openclaw_event(self, event):
        """
        Notify OpenClaw by running: openclaw system event --text "..." --mode now
        Runs in a background thread so it never blocks GPIO callbacks.
        """
        module = event["module"]
        event_type = event["event"]
        data = event["data"]
        ts = event["timestamp_iso"]

        # Build a descriptive text for the agent
        parts = [f"{module} sensor: {event_type} at {ts}."]
        if "touch_count" in data:
            parts.append(f"Touch count: {data['touch_count']}.")
        if "duration_ms" in data:
            parts.append(f"Duration: {data['duration_ms']}ms.")
        if "wave_count" in data:
            parts.append(f"Wave count: {data['wave_count']}. Distance: {data.get('distance_cm')}cm.")
        if "temperature_c" in data:
            parts.append(f"Temperature: {data['temperature_c']}°C, direction: {data.get('direction')}, threshold: {data.get('threshold')}°C.")
        if "humidity" in data:
            parts.append(f"Humidity: {data['humidity']}%, direction: {data.get('direction')}, threshold: {data.get('threshold')}%.")
        parts.append(
            "A physical reaction has already been shown on the face and LCD. "
            "You may respond verbally or trigger additional actions."
        )
        text = " ".join(parts)

        try:
            subprocess.Popen(
                [self._openclaw_bin, "system", "event", "--text", text, "--mode", "now"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except FileNotFoundError:
            print("  [WARN] openclaw binary not found, cannot dispatch event")
        except Exception as e:
            print(f"  [WARN] Failed to dispatch event to OpenClaw: {e}")

    def _get_events(self, peek=False):
        """Return pending events. If peek=False, clears the queue."""
        with self._events_lock:
            events = list(self._events)
            if not peek:
                self._events.clear()
        return events

    # --- Command routing ----------------------------------------------------

    def handle_message(self, raw):
        """Parse and route a JSON command. Returns a JSON response dict."""
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError as e:
            return {"ok": False, "error": f"Invalid JSON: {e}"}

        # Batch command
        if "batch" in msg:
            return self._handle_batch(msg["batch"])

        # System commands (no module specified)
        action = msg.get("action", "")
        module_name = msg.get("module", "")

        if not module_name:
            return self._handle_system(action, msg.get("params", {}))

        # Compound "totem" module for coordinated actions
        if module_name == "totem":
            return self._handle_compound(action, msg.get("params", {}))

        # Module-specific command
        if module_name not in self._modules:
            return {
                "ok": False,
                "error": f"Unknown module '{module_name}'. Available: {list(self._modules.keys())}",
            }

        module = self._modules[module_name]
        params = msg.get("params", {})
        with self._lock:
            return module.handle_command(action, params)

    def _handle_batch(self, commands):
        """Execute a list of commands and return all results."""
        results = []
        for cmd in commands:
            result = self.handle_message(json.dumps(cmd))
            results.append(result)
        all_ok = all(r.get("ok", False) for r in results)
        return {"ok": all_ok, "results": results}

    def _handle_system(self, action, params):
        """Handle system-level commands."""
        if action == "ping":
            return {"ok": True, "data": {"pong": True}}

        if action == "status":
            state = {}
            for name, module in self._modules.items():
                try:
                    state[name] = module.get_state()
                except Exception as e:
                    state[name] = {"error": str(e)}
            return {"ok": True, "data": state}

        if action == "capabilities":
            caps = {}
            for name, module in self._modules.items():
                try:
                    caps[name] = {
                        "description": module.description,
                        "actions": module.get_capabilities(),
                    }
                except Exception as e:
                    caps[name] = {"error": str(e)}
            return {"ok": True, "data": caps}

        if action == "events":
            peek = params.get("peek", False)
            events = self._get_events(peek=peek)
            return {"ok": True, "data": {"events": events, "count": len(events)}}

        if action == "notify":
            module  = params.get("module")
            enabled = params.get("enabled")
            if module is None or enabled is None:
                return {"ok": True, "data": {"module_notify": self._module_notify}}
            self._module_notify[module] = bool(enabled)
            return {"ok": True, "data": {"module": module, "enabled": bool(enabled)}}

        return {"ok": False, "error": f"Unknown system action '{action}'"}

    def _handle_compound(self, action, params):
        """Handle compound totem-level actions that coordinate multiple modules."""
        if action == "express":
            # Coordinated emotion: face expression + LCD message
            emotion = params.get("emotion", "neutral")
            message = params.get("message", "")
            duration = float(params.get("duration", 0))

            results = []

            # Set face expression
            if "face" in self._modules:
                with self._lock:
                    r = self._modules["face"].handle_command("expression", {"name": emotion})
                    results.append(r)

            # Set LCD text
            if "lcd" in self._modules and message:
                line1 = message[:16]
                line2 = message[16:32] if len(message) > 16 else ""
                with self._lock:
                    r = self._modules["lcd"].handle_command(
                        "write", {"line1": line1, "line2": line2}
                    )
                    results.append(r)

            all_ok = all(r.get("ok", False) for r in results)
            return {"ok": all_ok, "data": {"emotion": emotion, "message": message}}

        return {"ok": False, "error": f"Unknown compound action '{action}'"}

    # --- Socket server ------------------------------------------------------

    def start(self):
        """Start the daemon: discover modules, init hardware, listen on socket."""
        print("=" * 50)
        print("  TOTEM DAEMON")
        print("=" * 50)

        # Clean up stale socket
        if os.path.exists(SOCKET_PATH):
            os.unlink(SOCKET_PATH)

        # Write PID file
        with open(PID_FILE, "w") as f:
            f.write(str(os.getpid()))

        # Discover and init hardware
        print("\n[1/3] Discovering hardware modules...")
        self.discover_modules()

        if not self._modules:
            print("\n  [WARN] No hardware modules found! Running in headless mode.")
        else:
            print(f"\n[2/3] Initializing {len(self._modules)} module(s)...")
            self.init_modules()

        # Start socket server
        print(f"\n[3/3] Starting socket server at {SOCKET_PATH}")
        self._server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._server.bind(SOCKET_PATH)
        self._server.listen(5)
        self._server.settimeout(1.0)  # Allow periodic interrupt check
        self._running = True

        # Handle signals
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)

        modules_str = ", ".join(self._modules.keys()) if self._modules else "none"
        notify_str = "enabled" if (self._notify_enabled and self._openclaw_bin) else "disabled"
        if self._notify_enabled and not self._openclaw_bin:
            notify_str = "disabled (openclaw binary not found)"
        print(f"\n  Daemon ready. Modules: [{modules_str}]")
        print(f"  PID: {os.getpid()}")
        print(f"  Socket: {SOCKET_PATH}")
        print(f"  OpenClaw notify: {notify_str}")
        print("  Press Ctrl+C to stop.\n")

        # Main loop
        while self._running:
            try:
                conn, _ = self._server.accept()
                thread = threading.Thread(target=self._handle_client, args=(conn,), daemon=True)
                thread.start()
            except socket.timeout:
                continue
            except OSError:
                if self._running:
                    raise
                break

        self._shutdown()

    def _handle_client(self, conn):
        """Handle a single client connection."""
        try:
            data = b""
            while True:
                chunk = conn.recv(BUFFER_SIZE)
                if not chunk:
                    break
                data += chunk
                # Try to parse -- simple protocol: one JSON message per connection
                try:
                    json.loads(data)
                    break  # Valid JSON received
                except json.JSONDecodeError:
                    continue  # Keep reading

            if data:
                response = self.handle_message(data.decode("utf-8"))
                conn.sendall(json.dumps(response).encode("utf-8"))
        except Exception as e:
            error_response = {"ok": False, "error": str(e)}
            try:
                conn.sendall(json.dumps(error_response).encode("utf-8"))
            except Exception:
                pass
        finally:
            conn.close()

    def _handle_signal(self, signum, frame):
        """Handle SIGTERM/SIGINT for graceful shutdown."""
        print(f"\n  Received signal {signum}, shutting down...")
        self._running = False

    def _shutdown(self):
        """Clean shutdown: cleanup modules, close socket, remove files."""
        print("\n  Shutting down...")

        # Cleanup hardware
        self.cleanup_modules()

        # Close socket
        if self._server:
            try:
                self._server.close()
            except Exception:
                pass

        # Remove socket and pid files
        for path in (SOCKET_PATH, PID_FILE):
            try:
                os.unlink(path)
            except OSError:
                pass

        print("  Daemon stopped.")


# ---------------------------------------------------------------------------
# CLI entry points
# ---------------------------------------------------------------------------

def check_status():
    """Check if a daemon is already running."""
    if not os.path.exists(PID_FILE):
        print("Totem daemon is not running.")
        return False

    with open(PID_FILE) as f:
        pid = int(f.read().strip())

    # Check if process is alive
    try:
        os.kill(pid, 0)
        print(f"Totem daemon is running (PID {pid}).")
        return True
    except OSError:
        print("Totem daemon is not running (stale PID file).")
        # Clean up stale files
        for path in (PID_FILE, SOCKET_PATH):
            try:
                os.unlink(path)
            except OSError:
                pass
        return False


def stop_daemon():
    """Send SIGTERM to a running daemon."""
    if not os.path.exists(PID_FILE):
        print("Totem daemon is not running.")
        return

    with open(PID_FILE) as f:
        pid = int(f.read().strip())

    try:
        os.kill(pid, signal.SIGTERM)
        print(f"Sent stop signal to daemon (PID {pid}).")
    except OSError as e:
        print(f"Could not stop daemon: {e}")


if __name__ == "__main__":
    if "--status" in sys.argv:
        check_status()
    elif "--stop" in sys.argv:
        stop_daemon()
    else:
        daemon = TotemDaemon()
        daemon.start()
