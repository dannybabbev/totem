"""
Totem Mouth Bitmap Library
==========================

Centralized collection of 8x8 mouth grids for the MAX7219 LED matrix.
Each grid is a list of 8 rows, each row a list of 8 pixels (0=off, 1=on).

The full 8x8 canvas IS the mouth — no face outline.
The physical face is a 3D-printed body; the eyes are the ultrasonic sensor.
Designs should fill the canvas and be readable from a distance.

Coordinate system:
  - (0,0) is top-left
  - x increases rightward (columns 0-7)
  - y increases downward (rows 0-7)
"""

# ---------------------------------------------------------------------------
# Mouth Expressions  (full 8x8 canvas, no border — scale up and fill it)
# ---------------------------------------------------------------------------

NEUTRAL = [
    [0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0],
    [0, 1, 1, 1, 1, 1, 1, 0],  # Flat lip — double-thick bar
    [0, 1, 1, 1, 1, 1, 1, 0],
    [0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0],
]

HAPPY = [
    [0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0],
    [1, 0, 0, 0, 0, 0, 0, 1],  # Smile corners up at full width
    [0, 1, 0, 0, 0, 0, 1, 0],  # Curve sides
    [0, 0, 1, 1, 1, 1, 0, 0],  # Smile arc
    [0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0],
]

SAD = [
    [0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 1, 1, 1, 1, 0, 0],  # Frown arc (high in middle)
    [0, 1, 0, 0, 0, 0, 1, 0],  # Curve sides
    [1, 0, 0, 0, 0, 0, 0, 1],  # Corners drop to full width
    [0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0],
]

ANGRY = [
    [0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0],
    [1, 1, 1, 1, 1, 1, 1, 1],  # Full-width pressed lip (tense)
    [1, 0, 0, 0, 0, 0, 0, 1],  # Jaw corners forced down
    [0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0],
]

SURPRISED = [
    [0, 0, 1, 1, 1, 1, 0, 0],  # Top lip
    [0, 1, 0, 0, 0, 0, 1, 0],  # Upper sides
    [1, 0, 0, 0, 0, 0, 0, 1],  # Wide open
    [1, 0, 0, 0, 0, 0, 0, 1],  # Wide open
    [0, 1, 0, 0, 0, 0, 1, 0],  # Lower sides
    [0, 0, 1, 1, 1, 1, 0, 0],  # Bottom lip
    [0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0],
]

THINKING = [
    [0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 1, 1, 1, 0],  # Small mouth tucked to the right
    [0, 0, 0, 0, 1, 1, 1, 0],
    [0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0],
]

CONFUSED = [
    [0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0],
    [1, 0, 0, 1, 0, 0, 1, 0],  # Zigzag peaks (full-width W shape)
    [0, 1, 1, 0, 1, 1, 0, 1],  # Zigzag valleys
    [0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0],
]

SLEEPY = [
    [0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 1, 1, 1, 1, 0, 0],  # Top of drowsy yawn
    [0, 1, 0, 0, 0, 0, 1, 0],  # Sides open
    [0, 0, 1, 1, 1, 1, 0, 0],  # Bottom (smaller oval than SURPRISED)
    [0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0],
]

EXCITED = [
    [1, 0, 0, 0, 0, 0, 0, 1],  # Corners reach row 0 — massive grin
    [0, 1, 0, 0, 0, 0, 1, 0],  # Curve up
    [0, 0, 1, 0, 0, 1, 0, 0],  # Almost at arc
    [0, 0, 0, 1, 1, 0, 0, 0],  # Bottom of huge smile
    [0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0],
]

# Asymmetric right-side smirk — used for idle "wink" animation
SMIRK = [
    [0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 1, 0],  # Right corner lifted
    [0, 0, 0, 0, 0, 1, 0, 0],  # Angled line down-left
    [0, 0, 0, 0, 1, 1, 0, 0],  # Small left portion of lip
    [0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0],
]

# Backward-compat alias
BLINK = SMIRK

# ---------------------------------------------------------------------------
# Animation Frames
# ---------------------------------------------------------------------------

TALK_OPEN = [
    [0, 0, 1, 1, 1, 1, 0, 0],  # Top lip (same oval as SURPRISED)
    [0, 1, 0, 0, 0, 0, 1, 0],
    [1, 0, 0, 0, 0, 0, 0, 1],
    [1, 0, 0, 0, 0, 0, 0, 1],
    [0, 1, 0, 0, 0, 0, 1, 0],
    [0, 0, 1, 1, 1, 1, 0, 0],  # Bottom lip
    [0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0],
]

TALK_CLOSED = [
    [0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0],
    [0, 1, 1, 1, 1, 1, 1, 0],  # Lips pressed flat
    [0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0],
]

# ---------------------------------------------------------------------------
# Fun Extras / Icons
# ---------------------------------------------------------------------------

HEART = [
    [0, 0, 0, 0, 0, 0, 0, 0],
    [0, 1, 1, 0, 0, 1, 1, 0],
    [1, 1, 1, 1, 1, 1, 1, 1],
    [1, 1, 1, 1, 1, 1, 1, 1],
    [0, 1, 1, 1, 1, 1, 1, 0],
    [0, 0, 1, 1, 1, 1, 0, 0],
    [0, 0, 0, 1, 1, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0],
]

SKULL = [
    [0, 0, 1, 1, 1, 1, 0, 0],
    [0, 1, 1, 1, 1, 1, 1, 0],
    [1, 1, 0, 1, 1, 0, 1, 1],
    [1, 1, 1, 1, 1, 1, 1, 1],
    [0, 1, 1, 1, 1, 1, 1, 0],
    [0, 0, 1, 0, 0, 1, 0, 0],
    [0, 0, 1, 1, 1, 1, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0],
]

ARROW_UP = [
    [0, 0, 0, 1, 1, 0, 0, 0],
    [0, 0, 1, 1, 1, 1, 0, 0],
    [0, 1, 0, 1, 1, 0, 1, 0],
    [1, 0, 0, 1, 1, 0, 0, 1],
    [0, 0, 0, 1, 1, 0, 0, 0],
    [0, 0, 0, 1, 1, 0, 0, 0],
    [0, 0, 0, 1, 1, 0, 0, 0],
    [0, 0, 0, 1, 1, 0, 0, 0],
]

CHECK = [
    [0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 1],
    [0, 0, 0, 0, 0, 0, 1, 0],
    [0, 0, 0, 0, 0, 1, 0, 0],
    [1, 0, 0, 0, 1, 0, 0, 0],
    [0, 1, 0, 1, 0, 0, 0, 0],
    [0, 0, 1, 0, 0, 0, 0, 0],
    [0, 0, 0, 0, 0, 0, 0, 0],
]

CROSS = [
    [0, 0, 0, 0, 0, 0, 0, 0],
    [0, 1, 0, 0, 0, 0, 1, 0],
    [0, 0, 1, 0, 0, 1, 0, 0],
    [0, 0, 0, 1, 1, 0, 0, 0],
    [0, 0, 0, 1, 1, 0, 0, 0],
    [0, 0, 1, 0, 0, 1, 0, 0],
    [0, 1, 0, 0, 0, 0, 1, 0],
    [0, 0, 0, 0, 0, 0, 0, 0],
]

# ---------------------------------------------------------------------------
# Lookup Table (name -> grid)
# ---------------------------------------------------------------------------

EXPRESSIONS = {
    "neutral": NEUTRAL,
    "happy": HAPPY,
    "sad": SAD,
    "angry": ANGRY,
    "surprised": SURPRISED,
    "thinking": THINKING,
    "confused": CONFUSED,
    "sleepy": SLEEPY,
    "excited": EXCITED,
    "smirk": SMIRK,
    "talk_open": TALK_OPEN,
    "talk_closed": TALK_CLOSED,
    "blink": BLINK,
    "heart": HEART,
    "skull": SKULL,
    "arrow_up": ARROW_UP,
    "check": CHECK,
    "cross": CROSS,
}


def get_expression(name):
    """Get a mouth grid by name. Returns None if not found."""
    return EXPRESSIONS.get(name.lower())


def list_expressions():
    """Return a list of all available expression names."""
    return sorted(EXPRESSIONS.keys())
