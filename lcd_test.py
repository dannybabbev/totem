import time
from RPLCD.i2c import CharLCD

# --- CONFIGURATION ---
# Change this to the number you found in 'i2cdetect' (usually 0x27 or 0x3f)
lcd_address = 0x27 

try:
    # Initialize the LCD
    # cols=16, rows=2 (Standard 1602 display)
    lcd = CharLCD(i2c_expander='PCF8574', address=lcd_address, port=1,
                  cols=16, rows=2, dotsize=8,
                  charmap='A02',
                  auto_linebreaks=True,
                  backlight_enabled=True)

    print("Writing to LCD...")

    # 1. Clear the screen
    lcd.clear()
    
    # 2. Write Text
    lcd.write_string("Totem Online!")
    
    # 3. Move to second line (Cursor position: Row 1, Col 0)
    lcd.cursor_pos = (1, 0) 
    lcd.write_string("System: Ready")
    
    time.sleep(5)
    
    # 4. Blink Effect
    for i in range(3):
        lcd.backlight_enabled = False
        time.sleep(0.5)
        lcd.backlight_enabled = True
        time.sleep(0.5)
        
    lcd.clear()
    lcd.write_string("Sleeping...")
    time.sleep(2)
    lcd.backlight_enabled = False
    
except Exception as e:
    print(f"Error: {e}")
    print("Check your I2C Address (0x27 vs 0x3f)!")

finally:
    # Close nicely
    try:
        lcd.close(clear=True)
    except:
        pass