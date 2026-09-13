# Stimulator ESP32-H2 Super Mini

Emulates DUT (Device Under Test) button presses via open-drain LOW pulses.

Board GPIOs in use: **10, 11, 12, 14**. GPIO13 is skipped (onboard LED). GPIO2/3 are strapping pins.

## Flash (Pi 5)

```bash
cd ~/embedded-robot-qa/HIL_stand_project/stim_esp32   # or scp this folder
pio run -e stim -t upload --upload-port /dev/ttyUSB0
pio device monitor -b 115200 --port /dev/ttyUSB0
```

Native USB may appear as `/dev/ttyACM*` instead of `ttyUSB0`.

## CLI

```text
press 1 150
press 2
press 3
press 4
release
```

`press <1-4> [ms]` — default 120 ms, range 10–2000.

| CLI | Stim GPIO | DUT pin | Action |
|-----|-----------|---------|--------|
| `press 1` | 10 | GPIO10 | selftest |
| `press 2` | 11 | GPIO11 | ina |
| `press 3` | 12 | GPIO12 | us100 |
| `press 4` | 14 | GPIO13 | bme |

Wiring: see `../WIRING.md`.
