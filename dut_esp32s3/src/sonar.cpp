#include "sonar.h"

#include "cli_out.h"
#include "config.h"

static void pingOne(const char *name, uint8_t trig, uint8_t echo) {
  digitalWrite(trig, LOW);
  delayMicroseconds(2);
  digitalWrite(trig, HIGH);
  delayMicroseconds(10);
  digitalWrite(trig, LOW);
  const unsigned long us = pulseIn(echo, HIGH, ECHO_TIMEOUT_US);
  if (us == 0) {
    Cli.printf("%s FAIL timeout (unplugged or no echo)\n", name);
    return;
  }
  if (us < ECHO_MIN_US) {
    Cli.printf("%s FAIL too short %.1f cm (noise or unplugged)\n", name,
               us / 58.0f);
    return;
  }
  Cli.printf("%s PASS %.1f cm\n", name, us / 58.0f);
}

void sonarBegin() {
  pinMode(PIN_US100_TRIG, OUTPUT);
  pinMode(PIN_US100_ECHO, INPUT_PULLDOWN);
  digitalWrite(PIN_US100_TRIG, LOW);
}

void pingUs100() { pingOne("us100", PIN_US100_TRIG, PIN_US100_ECHO); }
