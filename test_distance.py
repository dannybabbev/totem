import RPi.GPIO as GPIO
import time

# SETTINGS
TRIG_PIN = 23       # GPIO 23 (BCM) — Pin 16
ECHO_PIN = 24       # GPIO 24 (BCM) — Pin 18 (via voltage divider: 1kΩ + 2kΩ)
READ_INTERVAL = 0.5  # seconds between readings

# SETUP
GPIO.setmode(GPIO.BCM)
GPIO.setup(TRIG_PIN, GPIO.OUT)
GPIO.setup(ECHO_PIN, GPIO.IN)
GPIO.output(TRIG_PIN, GPIO.LOW)
time.sleep(0.5)  # let sensor settle after power-on


def read_distance():
    # Send 10µs trigger pulse
    GPIO.output(TRIG_PIN, GPIO.HIGH)
    time.sleep(0.00001)
    GPIO.output(TRIG_PIN, GPIO.LOW)

    # Wait for echo to go high (start of pulse)
    timeout = time.time() + 0.05
    while GPIO.input(ECHO_PIN) == GPIO.LOW:
        if time.time() > timeout:
            return None

    start = time.time()

    # Wait for echo to go low (end of pulse)
    timeout = time.time() + 0.05
    while GPIO.input(ECHO_PIN) == GPIO.HIGH:
        if time.time() > timeout:
            return None

    duration = time.time() - start
    distance_cm = (duration * 34300) / 2
    return round(distance_cm, 1)


print(f"HC-SR04 Ultrasonic Distance Test  (TRIG=GPIO{TRIG_PIN}, ECHO=GPIO{ECHO_PIN})")
print(f"Reading every {READ_INTERVAL}s  (Press Ctrl+C to exit)\n")

try:
    while True:
        dist = read_distance()
        if dist is None:
            print("   Timeout — check wiring or move object within range")
        else:
            print(f"   Distance: {dist} cm")
        time.sleep(READ_INTERVAL)

except KeyboardInterrupt:
    print("\nExiting...")
finally:
    GPIO.cleanup()
