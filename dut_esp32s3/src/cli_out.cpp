#include "cli_out.h"

#include "wifi_cli.h"
#include <Arduino.h>
#include <HardwareSerial.h>
#include <stdio.h>

CliTee Cli;

static bool atBol = true;

static void rawOut(const uint8_t *p, size_t n) {
  Serial.write(p, n);
  Serial0.write(p, n);
  wifiNetWrite(p, n);
}

static void stamp() {
  const unsigned long ms = millis();
  char ts[16];
  const int n = snprintf(ts, sizeof(ts), "%lu.%03lu ", ms / 1000UL, ms % 1000UL);
  if (n > 0) {
    rawOut(reinterpret_cast<const uint8_t *>(ts), static_cast<size_t>(n));
  }
}

size_t CliTee::write(uint8_t b) {
  if (atBol) {
    stamp();
    atBol = false;
  }
  rawOut(&b, 1);
  if (b == '\n') {
    atBol = true;
  }
  return 1;
}

size_t CliTee::write(const uint8_t *buf, size_t n) {
  for (size_t i = 0; i < n; i++) {
    write(buf[i]);
  }
  return n;
}
