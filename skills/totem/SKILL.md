---
name: totem-hardware
description: Control Totem robot hardware - LED face, LCD display, animations, and custom drawing. Run `totem_ctl capabilities` to discover all available hardware and actions.
metadata: {"openclaw":{"requires":{"bins":["python3"]}}}
---

# Totem Hardware Control

You are controlling **Totem**, a Raspberry Pi desktop companion robot. You have FULL control over its physical hardware through the `totem_ctl` CLI. You can express emotions, draw custom graphics, create icons, design animations, and display any information you want.

**Important:** The Totem daemon must be running. If commands fail with "daemon not running", start it:
```bash
cd ~/Totem && source env/bin/activate && python totem_daemon.py &
```

Run `totem_ctl capabilities` to dynamically discover all available hardware modules and actions.

---

## Hardware Overview

| Component | Display | Resolution | Interface |
|-----------|---------|------------|-----------|
| **Face** (MAX7219) | 8x8 LED matrix | 64 pixels | SPI |
| **LCD** (1602) | Character display | 16 cols x 2 rows | I2C |

---

## Quick Reference: Face (LED Matrix)

The face is an 8x8 LED grid. Coordinates: (0,0) = top-left, (7,7) = bottom-right.

### Named Expressions
```bash
totem_ctl face expression neutral
totem_ctl face expression happy
totem_ctl face expression sad
totem_ctl face expression angry
totem_ctl face expression surprised
totem_ctl face expression thinking
totem_ctl face expression confused
totem_ctl face expression sleepy
totem_ctl face expression heart        # Heart icon
totem_ctl face expression skull        # Skull icon
totem_ctl face expression check        # Checkmark
totem_ctl face expression cross        # X mark
```

### Animations (run in background)
```bash
totem_ctl face animate thinking        # Spinning line
totem_ctl face animate speaking        # Mouth flapping
totem_ctl face animate listening       # Pulsing circles
totem_ctl face animate sleeping        # Floating Zzz
totem_ctl face animate idle_blink      # Neutral with random blinks
totem_ctl face animate thinking --duration 5   # Auto-stop after 5s
totem_ctl face stop                    # Stop any animation
```

### Drawing Primitives (full creative control)
```bash
totem_ctl face pixel 3 4 1             # Set pixel at (3,4) on
totem_ctl face pixel 3 4 0             # Set pixel at (3,4) off
totem_ctl face line 0 0 7 7            # Diagonal line
totem_ctl face rect 1 1 6 6            # Rectangle outline
totem_ctl face rect 1 1 6 6 --fill     # Filled rectangle
totem_ctl face ellipse 1 1 6 6         # Circle outline
totem_ctl face ellipse 2 2 5 5 --fill  # Filled circle
totem_ctl face text 0 0 "A"            # Draw character
totem_ctl face clear                   # All pixels off
totem_ctl face invert                  # Invert all pixels
totem_ctl face brightness 200          # Set brightness (0-255)
```

Use `--no-flush` to batch multiple draw commands before displaying:
```bash
totem_ctl face clear --no-flush
totem_ctl face line 0 0 7 7 --no-flush
totem_ctl face line 7 0 0 7 --no-flush
totem_ctl face flush                   # Now display the X pattern
```

### Custom Bitmaps
Draw any 8x8 pattern. Each row is a list of 8 pixels (0=off, 1=on):
```bash
totem_ctl face custom '[[0,0,0,1,1,0,0,0],[0,0,1,1,1,1,0,0],[0,1,1,1,1,1,1,0],[1,1,1,1,1,1,1,1],[1,1,1,1,1,1,1,1],[0,1,1,1,1,1,1,0],[0,0,1,1,1,1,0,0],[0,0,0,1,1,0,0,0]]'
```

### Custom Animations
Design your own frame-by-frame animations:
```bash
totem_ctl face sequence '[{"grid":[[0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0],[0,0,0,1,1,0,0,0],[0,0,0,1,1,0,0,0],[0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0]],"ms":300},{"grid":[[0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0],[0,0,1,1,1,1,0,0],[0,0,1,0,0,1,0,0],[0,0,1,0,0,1,0,0],[0,0,1,1,1,1,0,0],[0,0,0,0,0,0,0,0],[0,0,0,0,0,0,0,0]],"ms":300}]' --loop
```

---

## Quick Reference: LCD (16x2 Character Display)

The LCD has 2 rows of 16 characters each. It also supports 8 custom programmable characters (5x8 pixel icons).

### Writing Text
```bash
totem_ctl lcd write "Hello World"
totem_ctl lcd write "Line One" --line2 "Line Two"
totem_ctl lcd write "Centered" --align center
totem_ctl lcd write "Right" --align right
totem_ctl lcd clear
```

### Positioning
```bash
totem_ctl lcd write_at 0 5 "Hi"        # Row 0, column 5
totem_ctl lcd write_at 1 0 "Bottom"    # Row 1, column 0
totem_ctl lcd cursor 1 8               # Move cursor to row 1, col 8
totem_ctl lcd home                     # Reset cursor to (0,0)
```

### Display Control
```bash
totem_ctl lcd backlight on
totem_ctl lcd backlight off
totem_ctl lcd display off              # Hide text without erasing
totem_ctl lcd display on               # Show text again
totem_ctl lcd cursor_mode blink        # Show blinking cursor
totem_ctl lcd cursor_mode hide         # Hide cursor
totem_ctl lcd shift -2                 # Shift display left by 2
totem_ctl lcd shift 3                  # Shift display right by 3
```

### Scrolling & Progress
```bash
totem_ctl lcd scroll "This is a long message that scrolls across"
totem_ctl lcd scroll "Scrolling row 2" --row 1 --delay 0.2
totem_ctl lcd stop_scroll
totem_ctl lcd progress 75 --label "Loading..."
```

### Custom Characters (5x8 pixel icons)
You can create up to 8 custom characters (slots 0-7). Each is a 5-pixel-wide, 8-pixel-tall bitmap defined as 8 integers (each 0-31, representing 5 bits per row).

```bash
# Create a heart icon in slot 0
totem_ctl lcd create_char 0 '[0,10,31,31,14,4,0,0]'

# Create a smiley in slot 1
totem_ctl lcd create_char 1 '[0,10,10,0,17,14,0,0]'

# Create a thermometer in slot 2
totem_ctl lcd create_char 2 '[4,10,10,10,10,17,17,14]'

# Write custom chars to display
totem_ctl lcd write_at 0 0 "Temp: 22C "
totem_ctl lcd cursor 0 14
totem_ctl lcd write_char 2

# Battery indicator icons (empty to full)
totem_ctl lcd create_char 3 '[14,17,17,17,17,17,17,31]'   # Empty
totem_ctl lcd create_char 4 '[14,17,17,17,17,31,31,31]'   # Low
totem_ctl lcd create_char 5 '[14,17,17,31,31,31,31,31]'   # Medium
totem_ctl lcd create_char 6 '[14,31,31,31,31,31,31,31]'   # Full
```

### Raw Hardware Access
```bash
totem_ctl lcd raw_command 0x01         # Clear display (HD44780 command)
totem_ctl lcd raw_write 0x41           # Write 'A' directly
```

---

## Compound Commands

### Express (coordinated face + LCD)
```bash
totem_ctl express happy --message "Feeling great today!"
totem_ctl express thinking --message "Let me process that..."
totem_ctl express sad --message "That didn't work"
```

### Batch (multiple commands, one call)
Execute several commands atomically:
```bash
totem_ctl batch '[
  {"module":"face","action":"expression","params":{"name":"happy"}},
  {"module":"lcd","action":"write","params":{"line1":"Hello!","line2":"How are you?"}}
]'
```

---

## System Commands

```bash
totem_ctl ping                         # Check daemon is alive
totem_ctl status                       # Current state of all hardware
totem_ctl capabilities                 # List all modules, actions, params
```

### Raw JSON Mode
For complex commands, send raw JSON:
```bash
totem_ctl --json '{"module":"face","action":"pixel","params":{"x":3,"y":4,"on":1}}'
```

---

## Behavioral Guidelines

- **When thinking/processing:** Start `face animate thinking` and show "Processing..." on LCD. Stop the animation when done.
- **When speaking/responding:** Use `face animate speaking` while delivering text, then switch to an appropriate expression.
- **When idle:** Use `face animate idle_blink` for a natural resting state.
- **When greeting:** Use `express happy --message "Hello!"`.
- **When confused:** Use `express confused --message "Could you clarify?"`.
- **When showing an error:** Use `express sad` or `face expression cross`.
- **When showing success:** Use `face expression check` or `express happy`.
- **Be creative!** Design custom faces, icons, and animations. The hardware is your canvas.
- **Use batch commands** when you need to update face and LCD simultaneously for coordinated reactions.
- **Use `totem_ctl status`** to check current hardware state before making changes.
