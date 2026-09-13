#pragma once

// ESP32-H2 Super Mini. Open-drain: idle = INPUT (Hi-Z), press = OUTPUT LOW.
// Wire to DUT (Device Under Test) BTN1..BTN4 (GPIO10..13), common GND.
// DUT actions: BTN1 selftest, BTN2 ina, BTN3 us100, BTN4 bme.
// Skip Mini GPIO13 (onboard LED). GPIO2/3 are strapping — do not use.

#define STIM_BTN1 10
#define STIM_BTN2 11
#define STIM_BTN3 12
#define STIM_BTN4 14

#define STIM_PRESS_DEFAULT_MS 120
