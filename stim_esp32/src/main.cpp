#include <Arduino.h>
#include <string.h>
#include <stdlib.h>

#include "config.h"

static const uint8_t kPins[4] = {STIM_BTN1, STIM_BTN2, STIM_BTN3, STIM_BTN4};

static void releaseAll() {
  for (uint8_t p : kPins) {
    pinMode(p, INPUT);
  }
}

static void pressBtn(uint8_t idx, uint16_t ms) {
  if (idx > 3) {
    return;
  }
  pinMode(kPins[idx], OUTPUT);
  digitalWrite(kPins[idx], LOW);
  delay(ms);
  pinMode(kPins[idx], INPUT);
  Serial.printf("ok press %u %u\n", idx + 1, ms);
}

static void help() {
  Serial.print(
      "stim-esp32h2 ready (GPIO 10,11,12,14)\n"
      "  help\n"
      "  press <1-4> [ms]   open-drain LOW pulse (default 120)\n"
      "    1 GPIO10 → DUT BTN1 selftest\n"
      "    2 GPIO11 → DUT BTN2 ina\n"
      "    3 GPIO12 → DUT BTN3 us100\n"
      "    4 GPIO14 → DUT BTN4 bme\n"
      "  release            all lines Hi-Z\n");
}

static char line[64];
static uint8_t len = 0;

static void handleLine() {
  while (len && (line[len - 1] == '\r' || line[len - 1] == '\n')) {
    line[--len] = 0;
  }
  if (!len) {
    return;
  }
  char *cmd = strtok(line, " \t");
  char *a1 = strtok(nullptr, " \t");
  char *a2 = strtok(nullptr, " \t");
  if (!cmd) {
    return;
  }
  if (!strcasecmp(cmd, "help") || !strcasecmp(cmd, "?")) {
    help();
  } else if (!strcasecmp(cmd, "release")) {
    releaseAll();
    Serial.println("ok release");
  } else if (!strcasecmp(cmd, "press")) {
    int btn = a1 ? atoi(a1) : 0;
    int ms = a2 ? atoi(a2) : STIM_PRESS_DEFAULT_MS;
    if (btn < 1 || btn > 4 || ms < 10 || ms > 2000) {
      Serial.println("err usage: press <1-4> [ms]");
    } else {
      pressBtn((uint8_t)(btn - 1), (uint16_t)ms);
    }
  } else {
    Serial.printf("unknown '%s' - type help\n", cmd);
  }
  len = 0;
  line[0] = 0;
}

void setup() {
  Serial.begin(115200);
  delay(500);
  releaseAll();
  help();
}

void loop() {
  while (Serial.available()) {
    char c = (char)Serial.read();
    if (c == '\n' || c == '\r') {
      handleLine();
    } else if (len + 1 < sizeof(line)) {
      line[len++] = c;
      line[len] = 0;
    }
  }
}
