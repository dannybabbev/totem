import time
import random
from luma.core.interface.serial import spi, noop
from luma.core.render import canvas
from luma.led_matrix.device import max7219

# --- 1. HARDWARE SETUP ---
serial = spi(port=0, device=0, gpio=noop())
device = max7219(serial, cascaded=1, block_orientation=0, rotate=0)

# --- 2. THE FACE LIBRARY (0=Off, 1=On) ---

# Standard Smiley
FACE_NEUTRAL = [
    [0, 0, 1, 1, 1, 1, 0, 0],
    [0, 1, 0, 0, 0, 0, 1, 0],
    [1, 0, 1, 0, 0, 1, 0, 1], # Eyes Open
    [1, 0, 0, 0, 0, 0, 0, 1],
    [1, 0, 1, 0, 0, 1, 0, 1], # Smile Corners
    [1, 0, 0, 1, 1, 0, 0, 1], # Smile Bottom
    [0, 1, 0, 0, 0, 0, 1, 0],
    [0, 0, 1, 1, 1, 1, 0, 0]
]

# Mouth is a flat line
FACE_TALK_CLOSED = [
    [0, 0, 1, 1, 1, 1, 0, 0],
    [0, 1, 0, 0, 0, 0, 1, 0],
    [1, 0, 1, 0, 0, 1, 0, 1],
    [1, 0, 0, 0, 0, 0, 0, 1],
    [1, 0, 0, 0, 0, 0, 0, 1], # <--- Flat
    [1, 0, 1, 1, 1, 1, 0, 1], # <--- Flat
    [0, 1, 0, 0, 0, 0, 1, 0],
    [0, 0, 1, 1, 1, 1, 0, 0]
]

# Mouth is a big O
FACE_TALK_OPEN = [
    [0, 0, 1, 1, 1, 1, 0, 0],
    [0, 1, 0, 0, 0, 0, 1, 0],
    [1, 0, 1, 0, 0, 1, 0, 1],
    [1, 0, 0, 0, 0, 0, 0, 1],
    [1, 0, 0, 1, 1, 0, 0, 1], # <--- Open Top
    [1, 0, 0, 1, 1, 0, 0, 1], # <--- Open Bottom
    [0, 1, 0, 0, 0, 0, 1, 0],
    [0, 0, 1, 1, 1, 1, 0, 0]
]

# --- 3. HELPER FUNCTIONS ---

def draw_face(face_grid):
    """Takes a list of 8 lists and draws it on the matrix"""
    with canvas(device) as draw:
        for y, row in enumerate(face_grid):
            for x, pixel in enumerate(row):
                if pixel == 1:
                    draw.point((x, y), fill="white")

def animate_thinking(duration_seconds):
    """Shows a spinning loading animation"""
    print("Thinking...")
    end_time = time.time() + duration_seconds
    
    # A simple spinner animation frames
    # (Just a line rotating)
    while time.time() < end_time:
        # Frame 1: Vertical |
        with canvas(device) as draw:
            draw.line((3, 1, 3, 6), fill="white")
            draw.line((4, 1, 4, 6), fill="white")
        time.sleep(0.1)
        
        # Frame 2: Diagonal /
        with canvas(device) as draw:
            draw.line((1, 6, 6, 1), fill="white")
        time.sleep(0.1)
        
        # Frame 3: Horizontal -
        with canvas(device) as draw:
            draw.line((1, 3, 6, 3), fill="white")
            draw.line((1, 4, 6, 4), fill="white")
        time.sleep(0.1)

        # Frame 4: Diagonal \
        with canvas(device) as draw:
            draw.line((1, 1, 6, 6), fill="white")
        time.sleep(0.1)

def animate_speaking(duration_seconds):
    """Flaps the mouth open and closed randomly"""
    print("Speaking...")
    end_time = time.time() + duration_seconds
    
    while time.time() < end_time:
        draw_face(FACE_TALK_OPEN)
        time.sleep(random.uniform(0.1, 0.3)) # Random speed looks more natural
        
        draw_face(FACE_TALK_CLOSED)
        time.sleep(random.uniform(0.05, 0.2))

# --- 4. MAIN DEMO LOOP ---
print("💀 Totem Animator Started")

try:
    while True:
        # 1. Idle (Neutral Face)
        print("State: Idle")
        draw_face(FACE_NEUTRAL)
        time.sleep(2)
        
        # 2. Think (Loading Spinner)
        print("State: Thinking")
        animate_thinking(3) # Think for 3 seconds
        
        # 3. Speak (Mouth Flapping)
        print("State: Speaking")
        animate_speaking(4) # Talk for 4 seconds

except KeyboardInterrupt:
    device.cleanup()
    print("Exiting...")