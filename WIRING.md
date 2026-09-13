# HIL stand wiring — esp32s3-qa

Single fixed rail. No manual moving of OWON leads between tests.

## 1. Power (OWON → DUT)

| From | To |
|------|-----|
| OWON **+** | INA219 **VIN+** |
| INA219 **VIN−** | DUT **`5Vin`** (board 5 V rail; DUT powered from this rail) |
| OWON **−** | DUT **GND** + all module GNDs + stimulator GND + LA GND |

OWON setpoints used by tests: **5.0 / 5.1 / 5.2 V**. Current limit start at **0.5 A**.

**Power tests:** unplug Pi USB from DUT (or use VBUS-cut cable). Preferred console: **TX/RX/GND-only** USB-UART adapter (`ESP32_PORT`, adapter VCC **not** connected). Optional: WiFi TCP 3333 (`ESP32_HOST`).

**Flash only:** temporary USB to Pi is OK; disconnect before OWON V/I / brownout runs.

## 2. DUT sensors / actuators

Per `dut_esp32s3/include/config.h`:

| Module | Wiring |
|--------|--------|
| GY-BM | VCC=3V3, GND, SCL=18, SDA=17, CSB=3V3, SDO=GND |
| INA219 | VCC=3V3, GND, SCL=18, SDA=17; **VIN+** from OWON **+**; **VIN−** to board **5Vin** |
| US-100 | VCC=DUT 3V3, GND, TRIG=GPIO4, ECHO=GPIO5 **direct** (3.3 V, no divider). GPIO mode: jumper **off**. |
| LED | GPIO2 (board or external to 3V3 logic); LA CH0 for `-m la` |
| Buttons | GPIO10–13 INPUT_PULLUP (or driven only by stimulator) |

## 3. Stimulator ESP32-H2 Super Mini → DUT buttons

Stimulator drives **open-drain / open-collector** style: idle = Hi-Z / input; press = drive **LOW**.

Header GPIOs on this board: **0–5 and 10–14**. Do not use 16–19 (not brought out). Skip Mini **GPIO13** (onboard LED). Do not use GPIO2/3 (strapping).

| Stim GPIO | DUT pin | Action in FW |
|-----------|---------|--------------|
| 10 | BTN1 GPIO10 | selftest |
| 11 | BTN2 GPIO11 | ina |
| 12 | BTN3 GPIO12 | us100 |
| 14 | BTN4 GPIO13 | bme |

Common **GND** mandatory. Do **not** feed 5 V into DUT button pins.

Stimulator is powered from Pi USB (its own USB). It is **not** the DUT UART bridge.

## 4. Logic analyzer (FX2 clone)

Fixed probe for pytest `-m la`. USB into Pi 5 **USB 2.0** (black, not USB 3). **GND first**, then CH0 (D0) → DUT GPIO2 (LED). Other channels in `dut_esp32s3/include/config.h` are optional (manual).

## 5. Pi 5 USB map (typical)

| Device | Port example |
|--------|----------------|
| OWON SPM3051 | `/dev/ttyACM1` → `OWON_PORT` |
| Stimulator ESP32-H2 Super Mini | `/dev/ttyUSB0` or `/dev/ttyACM0` → `STIM_PORT` |
| DUT console | UART adapter `/dev/ttyUSB1` → `ESP32_PORT` (preferred); WiFi `ESP32_HOST` optional |
| FX2 logic analyzer | USB 2.0 → `sigrok-cli -d fx2lafw` |

Never point OWON SCPI at an Espressif/CH340 DUT port.

## 6. Safety

- US-100 ECHO is 3.3 V — no divider, no 5 V echo into ESP pins.
- No OWON into GPIO or **3V3** pin.
- Do not run a 5→30 V PSU ramp on a populated DUT (Device Under Test).
