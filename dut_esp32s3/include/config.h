#pragma once

// ESP32-S3 QA pin table. Do not change without explicit user approve.
// Flash/HIL from Raspberry Pi 5 (PlatformIO), same flow as esp32d-watchdog.
//
// Power: 5Vin = MCU board (INA219 shunt in this lane).
//        3V3 = GY-BM, INA219, LED, buttons, US-100 (GPIO mode, jumper off).
// Common GND everywhere, including logic analyzer GND.
//
// USB-UART CLI: GPIO43 TX, GPIO44 RX (3.3 V adapter, VCC not connected).
// US-100 ECHO is 3.3 V — wire direct to GPIO5, no divider.
// GY-BM ME/PM 280 6-pin I2C: VCC=3V3, GND, SCL, SDA, CSB=3V3, SDO=GND (addr 0x76).
//
// Logic analyzer (probe only):
//   CH0 GPIO2 LED
//   CH2 GPIO18 SCL
//   CH3 GPIO17 SDA
//   CH4 GPIO4  US-100 TRIG
//   CH5 GPIO5  US-100 ECHO
//   CH7 GPIO10 BTN1

#define PIN_LED 2

#define PIN_US100_TRIG 4
#define PIN_US100_ECHO 5

#define PIN_BTN1 10
#define PIN_BTN2 11
#define PIN_BTN3 12
#define PIN_BTN4 13

#define PIN_I2C_SDA 17
#define PIN_I2C_SCL 18
#define I2C_FREQ_HZ 100000

// UART0 CLI (USB-UART adapter: DUT TX→adapter RX, DUT RX→adapter TX, GND only)
#define PIN_UART0_TX 43
#define PIN_UART0_RX 44
#define UART0_BAUD 115200

#define ECHO_TIMEOUT_US 25000
#define ECHO_MIN_US 116  // ~2 cm; below this is noise on a floating/unplugged ECHO
#define LED_BLINK_MS 500
#define BTN_DEBOUNCE_MS 50

#define WIFI_TCP_PORT 3333
#define WIFI_CONNECT_MS 20000
