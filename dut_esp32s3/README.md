# DUT (Device Under Test) ESP32-S3 — esp32s3-qa

PlatformIO Arduino firmware for the HIL (Hardware-in-the-Loop) DUT (Device Under Test). USB CDC (Communications Device Class), UART0 on GPIO43/44, and optional WiFi TCP `:3333` share the same CLI.

Pin map: `include/config.h`. Wiring: `../WIRING.md`. Pytest: `../hil/`.

## Flash (Pi 5)

```bash
cd ~/embedded-robot-qa/HIL_stand_project/dut_esp32s3   # or scp this folder
pio run -e esp32s3 -t upload --upload-port /dev/ttyACM0
```

Unplug DUT USB after flash. Console for the stand is the **USB-UART adapter** (TX/RX/GND only, adapter VCC off):

```bash
pio device monitor --port /dev/ttyUSB1 -b 115200 --echo
```

DTR (Data Terminal Ready) / RTS off (`monitor_dtr = 0` in `platformio.ini`). Expected banner:

```text
esp32s3-qa
ready - type help
```

`status` must show `uart0: TX=43 RX=44`. Native USB CDC still works if that cable is plugged (bring-up / re-flash only).

Disconnect Pi USB VBUS from the DUT (Device Under Test) before OWON V/I / brownout tests. Flash-only USB is OK.

## WiFi CLI (optional, 2.4 GHz)

Copy `include/wifi_secrets.h.example` to `include/wifi_secrets.h` (gitignored). After boot, CLI prints `wifi PASS ... ip=... tcp=3333`. Use `ESP32_HOST` only if the USB-UART adapter is not available.

## Safety

- USB-UART: 3.3 V logic, **VCC not connected**, TX/RX crossed, common GND.
- US-100 ECHO is 3.3 V — wire direct (no divider). No 5 V echo into ESP pins.
- No OWON into GPIO or **3V3**.
