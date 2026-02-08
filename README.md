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

* [ ] **Install OpenClaw:** Install the OpenClaw agent on the Pi.
* [ ] **Configure Model:** Connect OpenClaw to a robust LLM.
* [ ] **Create "Totem" Skill:** Write a custom Skill to control the face via Python scripts.
* [ ] **Voice Mode:** Enable OpenClaw's TTS/STT features.

---

## Hardware Requirements

* **Raspberry Pi** (400 or 4B recommended)
* **Monitor** (HDMI input) & Micro-HDMI Cable
* **GPIO Extension Board** (T-Cobbler) + Breadboard
* **MAX7219 8x8 LED Matrix** (SPI interface)
* **1602 LCD Display** (I2C interface)
* **Jumper Wires** (Male-to-Male, Female-to-Male)

---

## Part 0: First Time Setup (NOOBS)

If you have just unboxed your Raspberry Pi kit, follow these steps to install the Operating System.

### 1. Hardware Connections

1. **Insert SD Card:** Ensure the MicroSD card (with NOOBS pre-installed) is inserted into the slot on the back of the Pi.
2. **Connect Monitor:** Plug the Micro-HDMI cable into the port labeled **HDMI0** (closest to the power port). If you use HDMI1, you may not see the boot screen. Connect the other end to your monitor.
3. **Connect Peripherals:** Plug in your Mouse and Keyboard (if not using a Pi 400).
4. **Connect Power:** Plug in the USB-C power supply last. The red LED on the Pi should light up, and the monitor should wake up.

### 2. Install Raspberry Pi OS

1. **The Installer:** Upon first boot, you will see the NOOBS / Raspberry Pi Recovery window.
2. **Select OS:** Check the box next to **Raspberry Pi OS (32-bit)** (Recommended).
* *Note:* You can choose 64-bit if you prefer, but 32-bit is often more compatible with older hardware libraries.


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

### 2. Enable Hardware Interfaces

1. Run `sudo raspi-config`
2. Navigate to **Interface Options**.
3. **SPI** -> Select **Yes** to enable.
4. **I2C** -> Select **Yes** to enable.
5. **Finish** and **Reboot** the Pi.

### 3. Verify Hardware

* **Check SPI:** `ls /dev/spi*` (Should show `/dev/spidev0.0`)
* **Check I2C:** `sudo i2cdetect -y 1` (Should show a number like `27` or `3f`)

### 4. Python Environment Setup

Create a virtual environment to keep the project isolated.

```bash
mkdir ~/Totem
cd ~/Totem
python3 -m venv env
source env/bin/activate

```

*(Always run `source env/bin/activate` before working)*

### 5. Install Python Libraries

Install all dependencies from the `requirements.txt` file.

```bash
pip install --upgrade pip
pip install -r requirements.txt

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

## Troubleshooting

* **ModuleNotFoundError: No module named 'PIL'**:
* Re-run the system dependency install step, then `pip install --force-reinstall --no-cache-dir luma.led_matrix`.


* **LCD is Blue but Empty**:
* Rotate the blue potentiometer on the back of the I2C backpack.


* **IOError: [Errno 121]**:
* Check wiring (SDA/SCL swapped).
* Check I2C address (`i2cdetect -y 1`) and update code if it is `0x3f`.