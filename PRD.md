# PRD — ESP32-S3 QA Node (esp32s3-qa)

**Document:** Product Requirements Document (PRD)  
**Product:** ESP32-S3 QA Node (`esp32s3-qa`)  
**Firmware:** PlatformIO Arduino tree in `dut_esp32s3/`  
**HW revision:** Bench rev. B (pins in `dut_esp32s3/include/config.h`)  
**Status:** Active — home HIL (Hardware-in-the-Loop) stand demo  
**Traceability:** [`hil/traceability_matrix.md`](hil/traceability_matrix.md)

---

## 1. Purpose of this document

Defines functional and non-functional requirements (NFR) for the IoT node used as DUT (Device Under Test) on the real HIL stand. Basis for test design and the Traceability Matrix.

---

## 2. Product overview

**ESP32-S3 QA Node** is an environmental and power monitoring IoT node:

- Ultrasonic distance (US-100, GPIO TRIG/ECHO mode)
- Temperature / humidity / pressure (GY-BM BME280 or BMP280)
- Bus voltage / current / power (INA219)
- Local UI: 4 buttons, status LED
- Operator / test CLI over USB CDC, UART0 (GPIO43/44 USB-UART), and optional WiFi TCP port 3333

Used in production-like QA as a HIL DUT powered from a programmable PSU (Power Supply Unit: OWON SPM3051) with automated stimulus and measurement from a Raspberry Pi 5.

---

## 3. Technical stack

| Layer | Choice |
|-------|--------|
| MCU | ESP32-S3 |
| Firmware | C++ / Arduino (PlatformIO) |
| CLI | USB CDC, UART0 GPIO43/44 (USB-UART TX/RX/GND), optional WiFi TCP `:3333` |
| Orchestrator | Raspberry Pi 5, Python pytest |
| PSU / DMM | OWON SPM3051 (SCPI over USB-CDC) |
| Stimulator | ESP32-H2 Super Mini, open-drain to DUT buttons |
| Sensors | BME/BMP280, INA219, US-100 |

### Pin map (DUT)

| Function | GPIO |
|----------|------|
| LED | 2 |
| US-100 TRIG / ECHO | 4 / 5 |
| BTN1–BTN4 | 10–13 |
| I2C SDA / SCL | 17 / 18 |
| UART0 TX / RX (CLI) | 43 / 44 |

Power: **`5Vin`** feeds the MCU board (INA219 shunt in this lane). **3V3** feeds GY-BM, INA219, LED, buttons, US-100. Common GND.

---

## 4. Functional requirements

| ID | Requirement |
|----|-------------|
| FR-01 | On boot, DUT prints banner `esp32s3-qa` then `ready - type help`. |
| FR-02 | CLI `help` lists supported commands including `selftest`, `status`, `bme`, `ina`, and `us100`. |
| FR-03 | CLI `status` reports pin map including `US100=4/5` and button range. |
| FR-04 | CLI `bme` / `bmp` returns one climate sample with `PASS` when GY-BM is present. |
| FR-05 | CLI `ina` returns bus V / I / P with `PASS` when INA219 is present. |
| FR-06 | CLI `us100` returns distance with `PASS` when echo is received. |
| FR-07 | BTN1 (active LOW) triggers `selftest` (same as CLI). |
| FR-08 | BTN2 runs `ina`; BTN3 runs `us100`; BTN4 runs `bme`. |
| FR-09 | `selftest` exercises I2C scan, GY-BM, INA219, and US-100; missing modules FAIL that line only. |
| FR-10 | Optional WiFi CLI accepts the same command set on TCP port 3333. |

---

## 5. Non-functional requirements (NFR)

| ID | Requirement |
|----|-------------|
| NFR-01 | Nominal supply: OWON sets **5.0 V** on `5Vin`; measured voltage within **4.90–5.10 V**. |
| NFR-02 | Characterization: DUT remains responsive (CLI `status` OK) at **5.1 V** and **5.2 V**; sensor PASS asserts allowed at these setpoints. |
| NFR-03 | Idle current on OWON at 5.0 V stays within configured min–max (default **0.020–0.350 A** with peripherals attached; override via env). |
| NFR-04 | Brownout: lowering `5Vin` until CLI is lost, then restoring 5.0 V via OWON, DUT returns to `ready` without manual RST. |
| NFR-05 | Power-cycle reset: automated `OUTP OFF` → wait → `OUTP ON` recovers boot banner without operator action. |
| NFR-06 | During power / brownout tests, DUT must not be powered by Pi USB VBUS (WiFi CLI or TX/RX/GND-only UART). |
| NFR-07 | US-100 ECHO is 3.3 V and is wired direct to GPIO5 (no divider). No 5 V echo into ESP pins. |
| NFR-08 | HIL suite is fully automated from Pi 5 (pytest): DUT CLI, stimulator, OWON SCPI. |

---

## 6. Critical use scenarios

1. **Bring-up:** OWON ON @ 5.0 V → boot → `selftest`.
2. **Telemetry:** periodic `bme` + `ina` while rail within NFR-01.
3. **Proximity:** `us100` with target in range.
4. **Local control:** stimulator presses BTN1 → selftest output on CLI.
5. **Power robustness:** 5.1 / 5.2 V characterization; brownout + auto recovery; cold power-cycle.

---

## 7. Out of scope

- Cloud backend / mobile app
- Relay / mains switching
- SENTRY-C1 auth/alarm firmware
- OWON 5→30 V ramp on a populated DUT
