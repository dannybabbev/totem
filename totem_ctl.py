#!/usr/bin/env python3
"""
Totem CLI - Hardware Control Client
====================================

Thin CLI client that sends JSON commands to the totem daemon via Unix socket.
Designed for use by both humans and the OpenClaw AI agent (via exec tool).

Usage:
    totem_ctl <module> <action> [args...]
    totem_ctl --json '<raw JSON>'
    totem_ctl ping | status | capabilities
    totem_ctl express <emotion> [--message "..."]
    totem_ctl batch '<JSON array>'

Examples:
    totem_ctl face expression happy
    totem_ctl face pixel 3 4 1
    totem_ctl face line 0 0 7 7
    totem_ctl face animate thinking --duration 5
    totem_ctl face sequence '[{"grid":[[...]], "ms":200}]'

    totem_ctl lcd write "Hello" --line2 "World" --align center
    totem_ctl lcd create_char 0 '[0,10,31,31,14,4,0,0]'
    totem_ctl lcd write_char 0
    totem_ctl lcd cursor_mode blink

    totem_ctl express happy --message "Feeling great!"
    totem_ctl batch '[{"module":"face","action":"expression","params":{"name":"happy"}}]'
"""

import argparse
import json
import os
import socket
import sys

SOCKET_PATH = "/tmp/totem.sock"
BUFFER_SIZE = 65536


def send_command(command_dict):
    """Send a JSON command to the daemon and return the response."""
    if not os.path.exists(SOCKET_PATH):
        print("Error: Totem daemon is not running. Start it with: python totem_daemon.py", file=sys.stderr)
        sys.exit(1)

    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(10.0)
        sock.connect(SOCKET_PATH)
        sock.sendall(json.dumps(command_dict).encode("utf-8"))
        sock.shutdown(socket.SHUT_WR)  # Signal end of message

        # Read response
        data = b""
        while True:
            chunk = sock.recv(BUFFER_SIZE)
            if not chunk:
                break
            data += chunk

        sock.close()
        return json.loads(data.decode("utf-8"))
    except ConnectionRefusedError:
        print("Error: Cannot connect to daemon. Is it running?", file=sys.stderr)
        sys.exit(1)
    except socket.timeout:
        print("Error: Daemon did not respond in time.", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


def print_response(response):
    """Print the daemon response in a readable format."""
    print(json.dumps(response, indent=2))


# ---------------------------------------------------------------------------
# Argument parsing and command building
# ---------------------------------------------------------------------------

def build_face_command(args):
    """Build a face module command from CLI args."""
    action = args.face_action
    params = {}

    if action == "expression":
        params["name"] = args.value
    elif action == "animate":
        params["name"] = args.value
        if args.duration is not None:
            params["duration"] = args.duration
    elif action in ("stop",):
        pass
    elif action == "blink":
        if args.duration_ms is not None:
            params["duration_ms"] = args.duration_ms
    elif action == "custom":
        params["grid"] = json.loads(args.value)
    elif action == "pixel":
        params["x"] = int(args.coords[0])
        params["y"] = int(args.coords[1])
        if len(args.coords) > 2:
            params["on"] = int(args.coords[2])
        if args.no_flush:
            params["flush"] = False
    elif action == "line":
        params["x1"] = int(args.coords[0])
        params["y1"] = int(args.coords[1])
        params["x2"] = int(args.coords[2])
        params["y2"] = int(args.coords[3])
        if args.no_flush:
            params["flush"] = False
    elif action == "rect":
        params["x1"] = int(args.coords[0])
        params["y1"] = int(args.coords[1])
        params["x2"] = int(args.coords[2])
        params["y2"] = int(args.coords[3])
        if args.fill:
            params["fill"] = True
        if args.no_flush:
            params["flush"] = False
    elif action == "ellipse":
        params["x1"] = int(args.coords[0])
        params["y1"] = int(args.coords[1])
        params["x2"] = int(args.coords[2])
        params["y2"] = int(args.coords[3])
        if args.fill:
            params["fill"] = True
        if args.no_flush:
            params["flush"] = False
    elif action == "text":
        params["x"] = int(args.coords[0])
        params["y"] = int(args.coords[1])
        params["char"] = args.char
        if args.no_flush:
            params["flush"] = False
    elif action == "clear":
        if args.no_flush:
            params["flush"] = False
    elif action == "invert":
        if args.no_flush:
            params["flush"] = False
    elif action == "brightness":
        params["value"] = int(args.value)
    elif action == "flush":
        pass
    elif action == "sequence":
        params["frames"] = json.loads(args.value)
        if args.loop:
            params["loop"] = True

    return {"module": "face", "action": action, "params": params}


def build_lcd_command(args):
    """Build an LCD module command from CLI args."""
    action = args.lcd_action
    params = {}

    if action == "write":
        params["line1"] = args.text
        if args.line2 is not None:
            params["line2"] = args.line2
        if args.align is not None:
            params["align"] = args.align
    elif action == "scroll":
        params["text"] = args.text
        if args.row is not None:
            params["row"] = args.row
        if args.delay is not None:
            params["delay"] = args.delay
    elif action == "progress":
        params["percentage"] = int(args.value)
        if args.label is not None:
            params["label"] = args.label
    elif action == "write_at":
        params["row"] = int(args.coords[0])
        params["col"] = int(args.coords[1])
        params["text"] = args.text
    elif action in ("clear", "home", "stop_scroll"):
        pass
    elif action == "cursor":
        params["row"] = int(args.coords[0])
        params["col"] = int(args.coords[1])
    elif action == "cursor_mode":
        params["mode"] = args.value
    elif action == "display":
        params["on"] = args.value.lower() in ("on", "true", "1", "yes")
    elif action == "backlight":
        params["on"] = args.value.lower() in ("on", "true", "1", "yes")
    elif action == "shift":
        params["amount"] = int(args.value)
    elif action == "create_char":
        params["slot"] = int(args.slot)
        params["bitmap"] = json.loads(args.value)
    elif action == "write_char":
        params["slot"] = int(args.value)
    elif action == "raw_command":
        params["value"] = int(args.value, 0)  # Supports 0x prefix
    elif action == "raw_write":
        params["value"] = int(args.value, 0)

    return {"module": "lcd", "action": action, "params": params}


def build_touch_command(args):
    """Build a touch module command from CLI args."""
    action = args.touch_action
    params = {}

    if action == "config":
        if args.debounce is not None:
            params["debounce_ms"] = args.debounce

    return {"module": "touch", "action": action, "params": params}


def main():
    parser = argparse.ArgumentParser(
        prog="totem_ctl",
        description="Totem Hardware Control CLI",
    )
    subparsers = parser.add_subparsers(dest="command", help="Command category")

    # --- Raw JSON mode ---
    parser.add_argument("--json", metavar="JSON", help="Send raw JSON command to daemon")

    # --- System commands ---
    sub_ping = subparsers.add_parser("ping", help="Check if daemon is alive")
    sub_status = subparsers.add_parser("status", help="Get state of all hardware")
    sub_caps = subparsers.add_parser("capabilities", help="List all modules and actions")

    # --- Events ---
    sub_events = subparsers.add_parser("events", help="Poll pending hardware events")
    sub_events.add_argument("--peek", action="store_true", help="Read events without clearing")

    # --- Express (compound) ---
    sub_express = subparsers.add_parser("express", help="Coordinated face + LCD emotion")
    sub_express.add_argument("emotion", help="Emotion name (e.g. happy, sad, thinking)")
    sub_express.add_argument("--message", "-m", default="", help="LCD message")
    sub_express.add_argument("--duration", "-d", type=float, default=0, help="Duration in seconds")

    # --- Batch ---
    sub_batch = subparsers.add_parser("batch", help="Execute multiple commands atomically")
    sub_batch.add_argument("json_array", help="JSON array of commands")

    # --- Face ---
    sub_face = subparsers.add_parser("face", help="LED matrix face control")
    face_sub = sub_face.add_subparsers(dest="face_action", help="Face action")

    # face expression <name>
    fp = face_sub.add_parser("expression", help="Set named expression")
    fp.add_argument("value", help="Expression name")

    # face animate <name> [--duration N]
    fp = face_sub.add_parser("animate", help="Start named animation")
    fp.add_argument("value", help="Animation name")
    fp.add_argument("--duration", "-d", type=float, default=None, help="Duration in seconds")

    # face stop
    face_sub.add_parser("stop", help="Stop animation")

    # face blink [--duration-ms N]
    fp = face_sub.add_parser("blink", help="Single eye blink")
    fp.add_argument("--duration-ms", type=int, default=None, help="Blink duration in ms")

    # face custom '<grid json>'
    fp = face_sub.add_parser("custom", help="Draw custom 8x8 bitmap")
    fp.add_argument("value", help="JSON 8x8 grid")

    # face pixel x y [on] [--no-flush]
    fp = face_sub.add_parser("pixel", help="Set/clear a pixel")
    fp.add_argument("coords", nargs="+", help="x y [on]")
    fp.add_argument("--no-flush", action="store_true", help="Don't flush to display")

    # face line x1 y1 x2 y2 [--no-flush]
    fp = face_sub.add_parser("line", help="Draw a line")
    fp.add_argument("coords", nargs=4, help="x1 y1 x2 y2")
    fp.add_argument("--no-flush", action="store_true")

    # face rect x1 y1 x2 y2 [--fill] [--no-flush]
    fp = face_sub.add_parser("rect", help="Draw a rectangle")
    fp.add_argument("coords", nargs=4, help="x1 y1 x2 y2")
    fp.add_argument("--fill", action="store_true", help="Filled rectangle")
    fp.add_argument("--no-flush", action="store_true")

    # face ellipse x1 y1 x2 y2 [--fill] [--no-flush]
    fp = face_sub.add_parser("ellipse", help="Draw an ellipse")
    fp.add_argument("coords", nargs=4, help="x1 y1 x2 y2")
    fp.add_argument("--fill", action="store_true", help="Filled ellipse")
    fp.add_argument("--no-flush", action="store_true")

    # face text x y <char> [--no-flush]
    fp = face_sub.add_parser("text", help="Draw a character")
    fp.add_argument("coords", nargs=2, help="x y")
    fp.add_argument("char", help="Single character to draw")
    fp.add_argument("--no-flush", action="store_true")

    # face clear [--no-flush]
    fp = face_sub.add_parser("clear", help="Clear display")
    fp.add_argument("--no-flush", action="store_true")

    # face invert [--no-flush]
    fp = face_sub.add_parser("invert", help="Invert all pixels")
    fp.add_argument("--no-flush", action="store_true")

    # face brightness <value>
    fp = face_sub.add_parser("brightness", help="Set brightness (0-255)")
    fp.add_argument("value", help="Brightness value")

    # face flush
    face_sub.add_parser("flush", help="Flush buffer to display")

    # face sequence '<frames json>' [--loop]
    fp = face_sub.add_parser("sequence", help="Play custom animation frames")
    fp.add_argument("value", help="JSON array of frames")
    fp.add_argument("--loop", action="store_true", help="Loop the animation")

    # --- LCD ---
    sub_lcd = subparsers.add_parser("lcd", help="1602 LCD display control")
    lcd_sub = sub_lcd.add_subparsers(dest="lcd_action", help="LCD action")

    # lcd write <text> [--line2 ...] [--align ...]
    lp = lcd_sub.add_parser("write", help="Write text to display")
    lp.add_argument("text", help="Line 1 text")
    lp.add_argument("--line2", default=None, help="Line 2 text")
    lp.add_argument("--align", default=None, choices=["left", "center", "right"])

    # lcd scroll <text> [--row N] [--delay N]
    lp = lcd_sub.add_parser("scroll", help="Scroll text across display")
    lp.add_argument("text", help="Text to scroll")
    lp.add_argument("--row", type=int, default=None)
    lp.add_argument("--delay", type=float, default=None)

    # lcd progress <percentage> [--label ...]
    lp = lcd_sub.add_parser("progress", help="Show progress bar")
    lp.add_argument("value", help="Percentage (0-100)")
    lp.add_argument("--label", default=None)

    # lcd write_at <row> <col> <text>
    lp = lcd_sub.add_parser("write_at", help="Write at specific position")
    lp.add_argument("coords", nargs=2, help="row col")
    lp.add_argument("text", help="Text to write")

    # lcd clear
    lcd_sub.add_parser("clear", help="Clear display")

    # lcd home
    lcd_sub.add_parser("home", help="Reset cursor to home")

    # lcd cursor <row> <col>
    lp = lcd_sub.add_parser("cursor", help="Move cursor")
    lp.add_argument("coords", nargs=2, help="row col")

    # lcd cursor_mode <mode>
    lp = lcd_sub.add_parser("cursor_mode", help="Set cursor mode")
    lp.add_argument("value", choices=["hide", "line", "blink"])

    # lcd display <on|off>
    lp = lcd_sub.add_parser("display", help="Toggle display on/off")
    lp.add_argument("value", help="on or off")

    # lcd backlight <on|off>
    lp = lcd_sub.add_parser("backlight", help="Toggle backlight")
    lp.add_argument("value", help="on or off")

    # lcd shift <amount>
    lp = lcd_sub.add_parser("shift", help="Shift display")
    lp.add_argument("value", help="Amount (positive=right, negative=left)")

    # lcd create_char <slot> <bitmap json>
    lp = lcd_sub.add_parser("create_char", help="Create custom character")
    lp.add_argument("slot", help="CGRAM slot (0-7)")
    lp.add_argument("value", help="JSON array of 8 integers")

    # lcd write_char <slot>
    lp = lcd_sub.add_parser("write_char", help="Write custom character")
    lp.add_argument("value", help="CGRAM slot (0-7)")

    # lcd raw_command <value>
    lp = lcd_sub.add_parser("raw_command", help="Send raw HD44780 command")
    lp.add_argument("value", help="Command byte (supports 0x prefix)")

    # lcd raw_write <value>
    lp = lcd_sub.add_parser("raw_write", help="Write raw byte")
    lp.add_argument("value", help="Data byte (supports 0x prefix)")

    # lcd stop_scroll
    lcd_sub.add_parser("stop_scroll", help="Stop scrolling text")

    # --- Touch ---
    sub_touch = subparsers.add_parser("touch", help="Touch sensor control")
    touch_sub = sub_touch.add_subparsers(dest="touch_action", help="Touch action")

    # touch read
    touch_sub.add_parser("read", help="Read current touch sensor state")

    # touch config [--debounce N]
    tp = touch_sub.add_parser("config", help="Configure touch sensor")
    tp.add_argument("--debounce", type=int, default=None, help="Debounce time in ms (50-2000)")

    # touch reset
    touch_sub.add_parser("reset", help="Reset touch counter to zero")

    # --- Parse and execute ---
    args = parser.parse_args()

    # Raw JSON mode
    if args.json:
        response = send_command(json.loads(args.json))
        print_response(response)
        return

    if not args.command:
        parser.print_help()
        return

    # System commands
    if args.command == "ping":
        response = send_command({"action": "ping"})
        print_response(response)
    elif args.command == "status":
        response = send_command({"action": "status"})
        print_response(response)
    elif args.command == "capabilities":
        response = send_command({"action": "capabilities"})
        print_response(response)
    elif args.command == "events":
        params = {}
        if args.peek:
            params["peek"] = True
        response = send_command({"action": "events", "params": params})
        print_response(response)
    elif args.command == "express":
        cmd = {
            "module": "totem",
            "action": "express",
            "params": {
                "emotion": args.emotion,
                "message": args.message,
                "duration": args.duration,
            },
        }
        response = send_command(cmd)
        print_response(response)
    elif args.command == "batch":
        commands = json.loads(args.json_array)
        response = send_command({"batch": commands})
        print_response(response)
    elif args.command == "face":
        if not args.face_action:
            sub_face.print_help()
            return
        cmd = build_face_command(args)
        response = send_command(cmd)
        print_response(response)
    elif args.command == "lcd":
        if not args.lcd_action:
            sub_lcd.print_help()
            return
        cmd = build_lcd_command(args)
        response = send_command(cmd)
        print_response(response)
    elif args.command == "touch":
        if not args.touch_action:
            sub_touch.print_help()
            return
        cmd = build_touch_command(args)
        response = send_command(cmd)
        print_response(response)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
