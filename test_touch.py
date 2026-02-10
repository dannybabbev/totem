import RPi.GPIO as GPIO
import time

# SETTINGS
TOUCH_PIN = 17  # The pin you connected SIG to

# SETUP
GPIO.setmode(GPIO.BCM)
# TTP223 is "Active High" (Sends 3.3V when touched)
# We add a 'Pull Down' to keep it quiet when NOT touched.
GPIO.setup(TOUCH_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

print(f"👇 Touch Sensor Test Initialized on GPIO {TOUCH_PIN}")
print("   (Press Ctrl+C to exit)")

try:
    while True:
        # Check if the pin is High (1)
        if GPIO.input(TOUCH_PIN) == GPIO.HIGH:
            print("👉 TOUCH DETECTED!")
            
            # Wait until you let go (so it doesn't print 1000 times)
            while GPIO.input(TOUCH_PIN) == GPIO.HIGH:
                time.sleep(0.1)
                
            print("   (Released)")
            
        time.sleep(0.1) # Small delay to save CPU

except KeyboardInterrupt:
    print("\n👋 Exiting...")
    GPIO.cleanup()