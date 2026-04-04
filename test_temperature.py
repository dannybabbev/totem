import time
import board
import adafruit_dht

# SETTINGS
DATA_PIN = board.D4  # GPIO 4 (BCM) — change if wired differently
READ_INTERVAL = 3    # Seconds between reads (DHT-11 min is ~2s)

# SETUP
sensor = adafruit_dht.DHT11(DATA_PIN)

print(f"🌡️  DHT-11 Temperature & Humidity Test on GPIO 4")
print(f"   Reading every {READ_INTERVAL} seconds (Press Ctrl+C to exit)\n")

try:
    while True:
        try:
            temperature_c = sensor.temperature
            humidity = sensor.humidity
            temperature_f = temperature_c * 9.0 / 5.0 + 32.0

            print(f"   Temp: {temperature_c:.1f}°C ({temperature_f:.1f}°F)  |  Humidity: {humidity:.1f}%")

        except RuntimeError as e:
            # DHT sensors occasionally fail to read — this is normal
            print(f"   ⚠ Read error (retrying): {e}")

        time.sleep(READ_INTERVAL)

except KeyboardInterrupt:
    print("\n👋 Exiting...")
    sensor.exit()
