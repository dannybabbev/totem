# Project Totem

A Raspberry Pi-based desktop companion robot featuring an animated 8x8 LED matrix face, a 1602 LCD status display, and an **OpenClaw** AI brain.

## Project Roadmap (Status)

### Phase 1: The Body (Hardware & Drivers)

* [x] **Setup Raspberry Pi:** OS installed, SPI/I2C enabled, System dependencies fixed.
* [x] **The Face:** Connect MAX7219 Matrix and run `animator.py`.
* [x] **The Voice (Text):** Connect 1602 LCD and run `lcd_test.py`.
* [x] **Core Integration:** Run `totem_core.py` to sync Face and LCD.
* [ ] **Connect Servo Motor:** Wire SG90 servo for neck movement (Nod/Shake).
* [ ] **Connect Audio:** Setup USB Microphone (Ears) and Speaker (Mouth).
* [ ] **Connect Camera:** Give the robot sight.

Note: If using Raspberry Pi 400, you must use a USB Webcam. The SunFounder CSI ribbon-cable camera will not fit inside the keyboard unit.

Note: If using Pi 4B, use the CSI port between the HDMI and Audio jack.

### Phase 2: The Brain (OpenClaw)

* [x] **Hardware Abstraction Layer:** Built `hardware/` package with `HardwareModule` interface.
* [x] **Totem Daemon:** Built `totem_daemon.py` — background service for persistent hardware state.
* [x] **Totem CLI:** Built `totem_ctl.py` — CLI for controlling hardware via daemon.
* [x] **OpenClaw Skill:** Created `skills/totem/SKILL.md` — teaches agent to control hardware.
* [ ] **Install OpenClaw:** Install the OpenClaw agent on the Pi.
* [ ] **Configure Model:** Connect OpenClaw to a robust LLM (Anthropic recommended).
* [ ] **Voice Mode:** Enable OpenClaw's TTS/STT features.

### Phase 3: Expansion (Planned)

* [ ] **Servo Motor:** SG90 servo for head nod/shake (`hardware/servo.py`).
* [ ] **Audio:** USB Microphone + Speaker (`hardware/microphone.py`, `hardware/speaker.py`).
* [ ] **Camera:** USB Webcam for vision (`hardware/camera.py`).
* [ ] **Sensors:** HC-SR04 distance, DHT11 temperature (`hardware/distance.py`, `hardware/temperature.py`).
* [ ] **Touch:** Capacitive touch sensor (`hardware/touch.py`).
* [ ] **Lighting:** WS2812B NeoPixel LED strip (`hardware/neopixel.py`).

---

## Hardware Requirements

* **Raspberry Pi** (400 or 4B recommended)
* **Monitor** (HDMI input) & Micro-HDMI Cable
* **GPIO Extension Board** (T-Cobbler) + Breadboard
* **MAX7219 8x8 LED Matrix** (SPI interface)
* **1602 LCD Display** (I2C interface)
* **Jumper Wires** (Male-to-Male, Female-to-Male)

---

## Part 0: First Time Setup

> **Note:** Do not use NOOBS. Instead, follow the official [Raspberry Pi Imager guide](https://www.raspberrypi.com/software/) to flash a **64-bit Raspberry Pi OS** to your SD card before first boot. This ensures better performance and compatibility with modern software.

If you have just unboxed your Raspberry Pi kit, follow these steps to install the Operating System.

### 1. Hardware Connections

1. **Insert SD Card:** Ensure the MicroSD card (with NOOBS pre-installed) is inserted into the slot on the back of the Pi.
2. **Connect Monitor:** Plug the Micro-HDMI cable into the port labeled **HDMI0** (closest to the power port). If you use HDMI1, you may not see the boot screen. Connect the other end to your monitor.
3. **Connect Peripherals:** Plug in your Mouse and Keyboard (if not using a Pi 400).
4. **Connect Power:** Plug in the USB-C power supply last. The red LED on the Pi should light up, and the monitor should wake up.

### 2. Install Raspberry Pi OS

> **Recommended:** Use [Raspberry Pi Imager](https://www.raspberrypi.com/software/) to flash **Raspberry Pi OS (64-bit)** to your SD card before powering on your Pi. This method is faster and more reliable than NOOBS.

If you are using a pre-installed NOOBS SD card:

1. **The Installer:** Upon first boot, you will see the NOOBS / Raspberry Pi Recovery window.
2. **Select OS:** Check the box next to **Raspberry Pi OS (64-bit)** if available.
3. **Install:** Click the **Install** button (or press `i`).
4. **Wait:** The system will install. This takes 10-20 minutes.
5. **Reboot:** Click **OK** when finished. The Pi will restart into the desktop.

### 3. Initial Configuration

1. **Welcome Wizard:** Follow the on-screen prompts.
* Set **Country/Language**.
* Set **Password** (Default user is usually `pi` or you create a new one).
* **Connect to WiFi.**
* **Update Software:** Allow it to download updates if asked.


2. **Restart:** Reboot one last time to apply updates.

---

## Part I: System Configuration

Now that the OS is running, open the **Terminal** (black icon on the taskbar) to prepare the software environment.

### 1. Update & Install Dependencies

Run these commands to fix common library issues before they happen.

```bash
sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get install -y python3-pip python3-venv python3-dev libjpeg-dev zlib1g-dev libfreetype6-dev liblcms2-dev libopenjp2-7-dev libtiff5-dev i2c-tools

```

### 2. Clone the Project Repository

Clone the Totem project from GitHub to your home directory.

```bash
cd ~
git clone https://github.com/dannybabbev/totem.git
cd totem

```

### 3. Enable Hardware Interfaces

1. Run `sudo raspi-config`
2. Navigate to **Interface Options**.
3. **SPI** -> Select **Yes** to enable.
4. **I2C** -> Select **Yes** to enable.
5. **Finish** and **Reboot** the Pi.

### 4. Verify Hardware

* **Check SPI:** `ls /dev/spi*` (Should show `/dev/spidev0.0`)
* **Check I2C:** `sudo i2cdetect -y 1` (Should show a number like `27` or `3f`)

### 5. Python Environment Setup

Create a virtual environment in the cloned project directory.

```bash
# You should already be in ~/totem from step 2
python3 -m venv env
source env/bin/activate

```

*(Always run `source env/bin/activate` before working)*

### 6. Install Python Libraries

Install all dependencies from the `requirements.txt` file.

```bash
pip install --upgrade pip
pip install -r requirements.txt

```

### 7. Install Node.js (via nvm)

Install Node.js to support JavaScript-based tools and OpenClaw integration.

```bash
# Download and install nvm:
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash

# in lieu of restarting the shell
\. "$HOME/.nvm/nvm.sh"

# Download and install Node.js:
nvm install 24

# Verify the Node.js version:
node -v # Should print "v24.13.0".

# Verify npm version:
npm -v # Should print "11.6.2".

```

---

## Part II: Wiring & Testing

### Understanding the Breadboard

* **Terminal Rows (The Middle):** Rows 1-60 are connected horizontally (A-E are linked, F-J are linked).
* **The Divider:** The middle gap separates the Left side from the Right side.
* **The T-Cobbler:** Bridges the Pi pins to the breadboard rows.

### 1. The Face (MAX7219 Matrix)

*Connects via SPI. Use the **Left** side of the T-Cobbler.*

| Matrix Pin | T-Cobbler Label | Physical Pin | Function |
| --- | --- | --- | --- |
| **VCC** | `5V` / `5V0` | Pin 2/4 | Power |
| **GND** | `GND` | Pin 6/9 | Ground |
| **DIN** | `SPIMOSI` / `GPIO 10` | Pin 19 | Data Input |
| **CS** | `SPICE0` / `GPIO 8` | Pin 24 | Chip Select |
| **CLK** | `SPISCLK` / `GPIO 11` | Pin 23 | Clock |

**Test:** Run `python face.py` (Static) or `python animator.py` (Animated).

### 2. The Voice (1602 LCD)

*Connects via I2C. Use the **Top Left** of the T-Cobbler.*

| LCD Pin | T-Cobbler Label | Physical Pin | Function |
| --- | --- | --- | --- |
| **VCC** | `5V` / `5V0` | Pin 2/4 | Power |
| **GND** | `GND` | Pin 6/9 | Ground |
| **SDA** | `SDA1` / `GPIO 2` | Pin 3 | Data |
| **SCL** | `SCL1` / `GPIO 3` | Pin 5 | Clock |

**Test:** Run `python lcd_test.py`.

---

## Part III: The Core (Combined)

Run `python totem_core.py` to synchronize both the Face and LCD.

## Part IV: Software Architecture

Totem uses a **daemon + CLI** architecture so that hardware stays initialized between commands and animations can run in the background.

```
OpenClaw Agent (AI)
    │  exec tool (shell command)
    ▼
totem_ctl.py (CLI client)
    │  JSON over Unix socket
    ▼
totem_daemon.py (background service)
    │  Hardware Registry (auto-discovers modules)
    ▼
hardware/ package
    ├── face.py    → MAX7219 LED Matrix (SPI)
    ├── lcd.py     → 1602 LCD Display (I2C)
    └── (future)   → servo.py, mic.py, distance.py, ...
```

### Project File Structure

```
totem/
├── hardware/                  # Modular hardware abstraction layer
│   ├── __init__.py
│   ├── base.py                # HardwareModule abstract base class
│   ├── face.py                # MAX7219 face (expressions, drawing, animations)
│   └── lcd.py                 # 1602 LCD (text, custom chars, full HD44780 API)
├── expressions.py             # Face bitmap library (all 8x8 grids)
├── totem_daemon.py            # Background daemon (Unix socket server)
├── totem_ctl.py               # CLI client (sends JSON commands to daemon)
├── skills/
│   └── totem/
│       └── SKILL.md           # OpenClaw skill definition
├── face.py                    # Original face test script
├── lcd_test.py                # Original LCD test script
├── totem_core.py              # Original combined demo script
├── requirements.txt           # Python dependencies
├── CONTRIBUTING.md            # Guide for adding new hardware modules
└── README.md                  # This file
```

### Starting the Daemon

```bash
cd ~/totem
source env/bin/activate
python totem_daemon.py
```

The daemon discovers all hardware modules in `hardware/`, initializes them, and listens for commands on `/tmp/totem.sock`.

### Testing with the CLI

```bash
# Check daemon is alive
python totem_ctl.py ping

# Set a happy face
python totem_ctl.py face expression happy

# Write to LCD
python totem_ctl.py lcd write "Hello!" --line2 "I am Totem"

# Coordinated emotion (face + LCD together)
python totem_ctl.py express thinking --message "Processing..."

# See all available hardware and actions
python totem_ctl.py capabilities
```

### Adding New Hardware

New hardware components are added as modules in the `hardware/` package. Each module implements the `HardwareModule` interface. The daemon auto-discovers new modules on restart. See [CONTRIBUTING.md](CONTRIBUTING.md) for a complete guide with a worked example.

---

## Part V: Install OpenClaw

Install OpenClaw on the Raspberry Pi using the official installer:

```bash
curl -fsSL https://openclaw.ai/install.sh | bash
```

Follow the on-screen prompts to complete the setup. Once installed, run the onboarding wizard:

```bash
openclaw onboard --install-daemon
```

This will configure your API key, pair a chat channel (WhatsApp, Telegram, etc.), and install the background service.

---

## Part VI: Add the Totem Skill to OpenClaw

### 1. Copy the Skill

Create the OpenClaw skills directory and copy the Totem skill:

```bash
mkdir -p ~/.openclaw/skills && cp -r ~/totem/skills/totem ~/.openclaw/skills/totem
```

### 2. Verify the Skill is Loaded

Start a new OpenClaw session and ask the agent to run:

```
totem_ctl capabilities
```

If it returns the list of modules and actions, the skill is working.

### 3. Start Totem + OpenClaw

Make sure the Totem daemon is running before (or alongside) OpenClaw:

```bash
# Terminal 1: Start the Totem daemon
cd ~/totem && source env/bin/activate && python totem_daemon.py

# Terminal 2: Start the OpenClaw gateway
openclaw gateway --port 18789
```

The OpenClaw agent will see the `totem-hardware` skill and can control all hardware via `totem_ctl` commands. Try messaging it: *"Show me a happy face and say hello on the LCD."*

---

## Troubleshooting

* **ModuleNotFoundError: No module named 'PIL'**:
* Re-run the system dependency install step, then `pip install --force-reinstall --no-cache-dir luma.led_matrix`.


* **LCD is Blue but Empty**:
* Rotate the blue potentiometer on the back of the I2C backpack.


* **IOError: [Errno 121]**:
* Check wiring (SDA/SCL swapped).
* Check I2C address (`i2cdetect -y 1`) and update code if it is `0x3f`.