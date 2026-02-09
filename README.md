# Project Totem

**Giving an AI agent a body for the first time.**

Totem is a Raspberry Pi-based companion robot powered by **[OpenClaw](https://github.com/openclaw/openclaw)**. It starts with an animated 8x8 LED matrix face and a 1602 LCD display — but that's just the beginning. The hardware layer is modular and designed to grow: add a servo for neck movement, a microphone for ears, a speaker for voice, a camera for sight, sensors for touch and awareness. Every new module snaps in and the AI agent can immediately use it.

This isn't a static gadget. It's a body that expands endlessly, giving your AI agent a physical presence in the real world.

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
* [x] **Install OpenClaw:** Install the OpenClaw agent on the Pi.
* [x] **Configure Model:** Connect OpenClaw to a robust LLM (Anthropic recommended).
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

If you have just unboxed your Raspberry Pi kit, follow the official [Raspberry Pi Imager tutorial](https://www.raspberrypi.com/software/) to install the Operating System.

### 1. Flash the SD Card with Raspberry Pi Imager

1. **Download** [Raspberry Pi Imager](https://www.raspberrypi.com/software/) on your computer (Windows, macOS, or Linux).
2. **Insert** your MicroSD card into your computer.
3. **Open** Raspberry Pi Imager and select:
   * **Device:** Your Raspberry Pi model (e.g. Pi 400, Pi 4B).
   * **OS:** **Raspberry Pi OS (64-bit)** — 64-bit is **required** for OpenClaw to run.
   * **Storage:** Your MicroSD card.
4. **Click Next**, then **Edit Settings** to pre-configure your Pi:
   * Set **hostname** (e.g. `totem`).
   * Set **username and password**.
   * Enter your **WiFi network name and password**.
   * Set **locale and timezone**.
   * Under the **Services** tab, enable **SSH** if you want remote access.
5. **Save** and confirm. The Imager will flash and verify the SD card.

### 2. First Boot

1. **Insert SD Card:** Put the flashed MicroSD card into the slot on the back of the Pi.
2. **Connect Monitor:** Plug the Micro-HDMI cable into the port labeled **HDMI0** (closest to the power port). If you use HDMI1, you may not see the boot screen. Connect the other end to your monitor.
3. **Connect Peripherals:** Plug in your Mouse and Keyboard (if not using a Pi 400).
4. **Connect Power:** Plug in the USB-C power supply last. The red LED on the Pi should light up, and the monitor should wake up.
5. **Wait:** The Pi will boot directly into the desktop. WiFi, username, and password are already configured from the Imager — no setup wizard needed.

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

# Set Node 24 as the default for all sessions and processes:
nvm alias default 24

# Symlink node/npm to /usr/local/bin so non-interactive processes (systemd, cron) can find them:
sudo ln -sf "$(which node)" /usr/local/bin/node
sudo ln -sf "$(which npm)" /usr/local/bin/npm
sudo ln -sf "$(which npx)" /usr/local/bin/npx

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
* **Power Rails (The Sides):** Red (+) and Blue (-) rails run along the edges for distributing power.

### 0. Create the Power Bus (Do This First!)

We need to distribute 5V and GND to multiple components. Use the breadboard's side rails:

1. **5V Rail:** Connect a jumper wire from **T-Cobbler 5V** (Pin 2 or 4) to the **Red (+) Rail** on the breadboard edge.
2. **GND Rail:** Connect a jumper wire from **T-Cobbler GND** (Pin 6 or 9) to the **Blue (-) Rail** on the breadboard edge.

Now all components can draw power from these rails instead of fighting for space on the T-Cobbler.

### 1. The Face (MAX7219 Matrix)

*Connects via SPI. Use the **Left** side of the T-Cobbler.*

| Matrix Pin | Connect To | Function |
| --- | --- | --- |
| **VCC** | **Red Rail** (5V) | Power |
| **GND** | **Blue Rail** (GND) | Ground |
| **DIN** | `SPIMOSI` / `GPIO 10` (Pin 19) | Data Input |
| **CS** | `SPICE0` / `GPIO 8` (Pin 24) | Chip Select |
| **CLK** | `SPISCLK` / `GPIO 11` (Pin 23) | Clock |

**Test:** Run `python face.py` (Static) or `python animator.py` (Animated).

### 2. The Display (1602 LCD)

*Connects via I2C. Use the **Top Left** of the T-Cobbler.*

| LCD Pin | Connect To | Function |
| --- | --- | --- |
| **VCC** | **Red Rail** (5V) | Power |
| **GND** | **Blue Rail** (GND) | Ground |
| **SDA** | `SDA1` / `GPIO 2` (Pin 3) | Data |
| **SCL** | `SCL1` / `GPIO 3` (Pin 5) | Clock |

**Test:** Run `python lcd_test.py`.

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

### Setting Up the Daemon as a Service

Run the install script to register the Totem daemon as a systemd user service. This makes it start automatically on boot:

```bash
cd ~/totem
bash install-service.sh
```

The daemon discovers all hardware modules in `hardware/`, initializes them, and listens for commands on `/tmp/totem.sock`.

### Managing the Daemon

```bash
# Restart the daemon (after code changes)
systemctl --user restart totem-daemon.service

# Check status
systemctl --user status totem-daemon.service

# Stop it
systemctl --user stop totem-daemon.service

# Start it
systemctl --user start totem-daemon.service

# View logs
journalctl --user -u totem-daemon.service -f

# Disable auto-start (if needed)
systemctl --user disable totem-daemon.service

# Re-enable auto-start
systemctl --user enable totem-daemon.service
```

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

[OpenClaw](https://github.com/openclaw/openclaw) is an open-source personal AI assistant that runs on your own devices. It connects to messaging channels (Telegram, WhatsApp, Slack, Discord, etc.) and uses LLM providers like Anthropic or OpenAI to power the conversation. In this project, OpenClaw is the brain that controls Totem's hardware.

> **Note:** OpenClaw requires a **64-bit OS**. Make sure you flashed Raspberry Pi OS (64-bit) in Part 0.

### 1. Get an API Key

OpenClaw needs an LLM API key to function. Choose one of the following providers:

* **Anthropic (Recommended):** Go to [console.anthropic.com](https://console.anthropic.com/), create an account, navigate to **API Keys**, and generate a new key.
* **OpenAI:** Go to [platform.openai.com](https://platform.openai.com/), create an account, navigate to **API Keys**, and generate a new key.

> **Note:** Both platforms require a payment method. Keep your API key safe — you will need it during the installation.

### 2. Install OpenClaw

Run the installer on the Raspberry Pi:

```bash
curl -fsSL https://openclaw.ai/install.sh | bash
```

Follow the on-screen prompts. When asked for your API key, paste the key you generated above.

During onboarding, you will be asked to connect a chat channel. **Telegram is the easiest option** — here's how to set it up:

1. Open Telegram and search for **@BotFather**.
2. Send `/newbot` and follow the prompts to name your bot.
3. BotFather will give you a **Bot Token** — copy it.
4. Paste the token when the onboarding wizard asks for your Telegram connection.

This will configure your API provider, connect your Telegram bot, and install the background service.

---

## Part VI: Add the Totem Skill to OpenClaw

### 1. Deploy the Skill

Run the deploy script to copy the Totem skill to OpenClaw and restart the daemon:

```bash
cd ~/totem
bash deploy.sh
```

### 2. Verify the Skill is Loaded

Start a new OpenClaw session and ask the agent to run:

```
totem_ctl capabilities
```

If it returns the list of modules and actions, the skill is working.

### 3. You're Ready!

That's it — your robot is alive. Open your Telegram bot and start chatting. The OpenClaw agent will see the `totem-hardware` skill and can control all hardware via `totem_ctl` commands.

Try sending it a message: *"Show me a happy face and say hello on the LCD."*

---

## Part VII: Understanding OpenClaw

[OpenClaw](https://github.com/openclaw/openclaw) is the AI agent that gives Totem its personality and intelligence. It reads a set of markdown files to know who it is, who you are, and what it can do. Everything lives in the workspace at `~/.openclaw/workspace/`. See the [full documentation](https://github.com/openclaw/openclaw#agent-workspace--skills) for more details.

### Personality & Identity

| File | Purpose |
| --- | --- |
| `SOUL.md` | Core personality, values, and boundaries |
| `IDENTITY.md` | Who the robot is — name, vibe, embodiment |
| `AGENTS.md` | Operational guidelines — how it works, when to speak, how to behave |

Edit these files to change your robot's personality. Want it to be sarcastic? Zen? Formal? Change `SOUL.md`.

### About You

| File | Purpose |
| --- | --- |
| `USER.md` | Info about you — name, timezone, interests, what you're building |

OpenClaw reads this to personalize its responses. Update it any time.

### Memory

| File / Folder | Purpose |
| --- | --- |
| `MEMORY.md` | Long-term curated memories (important moments, milestones) |
| `memory/` | Daily logs in `YYYY-MM-DD.md` format (auto-generated) |

The agent writes daily logs automatically and promotes important memories to `MEMORY.md`.

### Tools & Hardware

| File | Purpose |
| --- | --- |
| `TOOLS.md` | Hardware control notes — Totem commands and usage |
| `skills/totem/SKILL.md` | The Totem skill definition (copied by `deploy.sh`) |

### Other

| File | Purpose |
| --- | --- |
| `HEARTBEAT.md` | Periodic check instructions (scheduled tasks, reminders) |

> **Tip:** You can edit any of these files directly to customize your robot. Changes take effect on the next conversation.

---

## Troubleshooting

* **ModuleNotFoundError: No module named 'PIL'**:
* Re-run the system dependency install step, then `pip install --force-reinstall --no-cache-dir luma.led_matrix`.


* **LCD is Blue but Empty**:
* Rotate the blue potentiometer on the back of the I2C backpack.


* **IOError: [Errno 121]**:
* Check wiring (SDA/SCL swapped).
* Check I2C address (`i2cdetect -y 1`) and update code if it is `0x3f`.