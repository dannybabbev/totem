import RPi.GPIO as GPIO
import time

# SETTINGS
TRIG_PIN = 23
ECHO_PIN = 24

# Wave detection tuning
BASELINE_ALPHA   = 0.05   # how fast baseline adapts (lower = slower/smoother)
WAVE_THRESHOLD   = 10     # cm below baseline required to count as "hand present"
DEBOUNCE_COUNT   = 3      # consecutive readings needed to change state
MAX_WAVE_DURATION = 2.0   # seconds — hand must withdraw within this window
MIN_VALID_DIST   = 2      # cm — ignore spurious near-zero spikes

# SETUP
GPIO.setmode(GPIO.BCM)
GPIO.setup(TRIG_PIN, GPIO.OUT)
GPIO.setup(ECHO_PIN, GPIO.IN)
GPIO.output(TRIG_PIN, GPIO.LOW)
time.sleep(0.5)  # let sensor settle after power-on


def read_distance():
    GPIO.output(TRIG_PIN, GPIO.HIGH)
    time.sleep(0.00001)
    GPIO.output(TRIG_PIN, GPIO.LOW)

    timeout = time.time() + 0.05
    while GPIO.input(ECHO_PIN) == GPIO.LOW:
        if time.time() > timeout:
            return None

    start = time.time()

    timeout = time.time() + 0.05
    while GPIO.input(ECHO_PIN) == GPIO.HIGH:
        if time.time() > timeout:
            return None

    duration = time.time() - start
    distance_cm = (duration * 34300) / 2
    return round(distance_cm, 1)


def read_median(samples=5):
    readings = []
    for _ in range(samples):
        d = read_distance()
        if d is not None and d >= MIN_VALID_DIST:
            readings.append(d)
        time.sleep(0.06)
    if not readings:
        return None
    readings.sort()
    return readings[len(readings) // 2]


def calibrate(n=10):
    print("Calibrating baseline — keep area clear...")
    readings = []
    while len(readings) < n:
        d = read_median()
        if d is not None:
            readings.append(d)
            print(f"  {d} cm")
    baseline = sum(readings) / len(readings)
    print(f"Baseline set: {baseline:.1f} cm\n")
    return baseline


print(f"HC-SR04 Wave Detection Test  (TRIG=GPIO{TRIG_PIN}, ECHO=GPIO{ECHO_PIN})")

baseline = calibrate()

state    = "IDLE"
debounce = 0
wave_start = None

print("Ready — wave your hand in front of the sensor\n")

try:
    while True:
        dist = read_median()
        if dist is None:
            continue

        near = dist < (baseline - WAVE_THRESHOLD)

        if state == "IDLE":
            # Update baseline only when no hand is present
            baseline = (1 - BASELINE_ALPHA) * baseline + BASELINE_ALPHA * dist
            print(f"  {dist:.1f} cm  (baseline {baseline:.1f} cm)")

            if near:
                debounce += 1
                if debounce >= DEBOUNCE_COUNT:
                    state = "NEAR"
                    wave_start = time.time()
                    debounce = 0
                    print("  >> Hand detected")
            else:
                debounce = 0

        elif state == "NEAR":
            print(f"  {dist:.1f} cm  [hand]")

            if not near:
                debounce += 1
                if debounce >= DEBOUNCE_COUNT:
                    elapsed = time.time() - wave_start
                    if elapsed < MAX_WAVE_DURATION:
                        print("  ** WAVE DETECTED **\n")
                    else:
                        print("  (hand removed — too slow for wave)")
                    state = "IDLE"
                    debounce = 0
            else:
                debounce = 0

            # Hand held too long — not a wave, reset
            if time.time() - wave_start > MAX_WAVE_DURATION:
                print("  (hand held too long — ignored)")
                state = "IDLE"
                debounce = 0

except KeyboardInterrupt:
    print("\nExiting...")
finally:
    GPIO.cleanup()
