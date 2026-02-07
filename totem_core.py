import time
import random
from luma.core.interface.serial import spi, noop
from luma.core.render import canvas
from luma.led_matrix.device import max7219
from RPLCD.i2c import CharLCD

# --- CONFIGURATION ---
LCD_ADDRESS = 0x27  # Change to 0x3f if 0x27 doesn't work

# --- 1. HARDWARE SETUP ---

# Setup Matrix (SPI)
print("Initializing Matrix...")
serial = spi(port=0, device=0, gpio=noop())
matrix = max7219(serial, cascaded=1, block_orientation=0, rotate=0)

# Setup LCD (I2C)
print("Initializing LCD...")
try:
    lcd = CharLCD(i2c_expander='PCF8574', address=LCD_ADDRESS, port=1,
                  cols=16, rows=2, dotsize=8,
                  charmap='A02',
                  auto_linebreaks=True,
                  backlight_enabled=True)
except Exception as e:
    print(f"LCD Error: {e}")
    print("Check your I2C address!")
    lcd = None # Continue without LCD if it fails

# --- 2. FACIAL EXPRESSIONS (Bitmaps) ---
FACE_SMILE = [
    [0, 0, 1, 1, 1, 1, 0, 0],
    [0, 1, 0, 0, 0, 0, 1, 0],
    [1, 0, 1, 0, 0, 1, 0, 1],
    [1, 0, 0, 0, 0, 0, 0, 1],
    [1, 0, 1, 0, 0, 1, 0, 1],
    [1, 0, 0, 1, 1, 0, 0, 1],
    [0, 1, 0, 0, 0, 0, 1, 0],
    [0, 0, 1, 1, 1, 1, 0, 0]
]

FACE_TALK_OPEN = [
    [0, 0, 1, 1, 1, 1, 0, 0],
    [0, 1, 0, 0, 0, 0, 1, 0],
    [1, 0, 1, 0, 0, 1, 0, 1],
    [1, 0, 0, 0, 0, 0, 0, 1],
    [1, 0, 0, 1, 1, 0, 0, 1],
    [1, 0, 0, 1, 1, 0, 0, 1],
    [0, 1, 0, 0, 0, 0, 1, 0],
    [0, 0, 1, 1, 1, 1, 0, 0]
]

FACE_TALK_CLOSED = [
    [0, 0, 1, 1, 1, 1, 0, 0],
    [0, 1, 0, 0, 0, 0, 1, 0],
    [1, 0, 1, 0, 0, 1, 0, 1],
    [1, 0, 0, 0, 0, 0, 0, 1],
    [1, 0, 0, 0, 0, 0, 0, 1],
    [1, 0, 1, 1, 1, 1, 0, 1],
    [0, 1, 0, 0, 0, 0, 1, 0],
    [0, 0, 1, 1, 1, 1, 0, 0]
]

# --- 3. SYNC FUNCTIONS ---

def set_status(text_line1, text_line2=""):
    """Updates the LCD Text immediately"""
    if lcd:
        lcd.clear()
        lcd.write_string(text_line1)
        if text_line2:
            lcd.cursor_pos = (1, 0)
            lcd.write_string(text_line2)
    print(f"[STATUS] {text_line1} | {text_line2}")

def draw_static_face(face_grid):
    """Draws a single frame on the matrix"""
    with canvas(matrix) as draw:
        for y, row in enumerate(face_grid):
            for x, pixel in enumerate(row):
                if pixel == 1:
                    draw.point((x, y), fill="white")

def animate_thinking(duration=3):
    """Spinning animation + LCD 'Thinking...'"""
    set_status("Processing...", "Please wait")
    
    end_time = time.time() + duration
    while time.time() < end_time:
        # Rotating line animation
        frames = [
            [(3,1,3,6), (4,1,4,6)], # Vertical
            [(1,6,6,1)],            # Diagonal /
            [(1,3,6,3), (1,4,6,4)], # Horizontal
            [(1,1,6,6)]             # Diagonal \
        ]
        
        for lines in frames:
            with canvas(matrix) as draw:
                for line in lines:
                    draw.line(line, fill="white")
            time.sleep(0.1)

def animate_speaking(text_to_display, duration=4):
    """Mouth flapping + LCD shows the text"""
    # Split text into two lines for the LCD
    line1 = text_to_display[:16]
    line2 = text_to_display[16:32]
    
    set_status(line1, line2)
    
    end_time = time.time() + duration
    while time.time() < end_time:
        draw_static_face(FACE_TALK_OPEN)
        time.sleep(random.uniform(0.1, 0.3))
        
        draw_static_face(FACE_TALK_CLOSED)
        time.sleep(random.uniform(0.05, 0.2))

# --- 4. MAIN LOOP ---
try:
    print("💀 Totem Core Active")
    
    while True:
        # 1. IDLE STATE
        set_status("Totem v1.0", "Ready for Input")
        draw_static_face(FACE_SMILE)
        time.sleep(3) # Wait for user (simulated)
        
        # 2. LISTENING STATE (Simulated)
        set_status("Listening...", "Say something")
        # (Here we would blink the eyes or show a question mark)
        time.sleep(2)

        # 3. THINKING STATE
        animate_thinking(duration=3)
        
        # 4. SPEAKING STATE
        # Simulate a response from the AI
        responses = [
            "I checked email.",
            "Systems nominal.",
            "Humans are odd.",
            "Need more coffee"
        ]
        chosen_response = random.choice(responses)
        animate_speaking(chosen_response, duration=3)
        
        # Pause before looping
        time.sleep(1)

except KeyboardInterrupt:
    if lcd: lcd.clear()
    print("Shutting down...")