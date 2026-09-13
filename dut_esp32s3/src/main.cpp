#include <Arduino.h>
#include <string.h>

#include "cli_out.h"
#include "config.h"
#include "sensors.h"
#include "sonar.h"
#include "wifi_cli.h"

static char serBuf[96];
static uint8_t serLen = 0;
static char uartBuf[96];
static uint8_t uartLen = 0;
static char tcpBuf[96];
static uint8_t tcpLen = 0;

static const uint8_t kBtns[4] = {PIN_BTN1, PIN_BTN2, PIN_BTN3, PIN_BTN4};
static bool btnLast[4] = {true, true, true, true};
static uint32_t btnAt[4] = {0, 0, 0, 0};

static void printHelp() {
  Cli.print(
      "commands:\n"
      "  help              this text\n"
      "  status            pin map + wifi\n"
      "  selftest          all checks (missing devices FAIL only that line)\n"
      "  i2c               scan bus\n"
      "  bme               GY-BM ME/PM 280 once\n"
      "  ina               INA219 once\n"
      "  us100             US-100 once\n"
      "  la                1 kHz on LED for 2 s (logic analyzer)\n"
      "buttons: BTN1 selftest  BTN2 ina  BTN3 us100  BTN4 bme\n");
}

static void printStatus() {
  Cli.printf("pins: LED=%d US100=%d/%d BTN=%d-%d I2C=%d/%d\n", PIN_LED,
             PIN_US100_TRIG, PIN_US100_ECHO, PIN_BTN1, PIN_BTN4, PIN_I2C_SDA,
             PIN_I2C_SCL);
  Cli.printf("uart0: TX=%d RX=%d %u baud (USB-UART TX/RX/GND)\n", PIN_UART0_TX,
             PIN_UART0_RX, static_cast<unsigned>(UART0_BAUD));
  wifiPrintStatus();
}

static void selftest() {
  Cli.println("selftest");
  Cli.println("  led        GPIO2 toggling (no electrical check; look at the external LED)");
  i2cScan();
  printSensors();
  pingUs100();
  Cli.println(
      "selftest done (FAIL on missing modules is expected during 1-by-1 "
      "bring-up)");
}

static void laSquare() {
  Cli.println("LED 1 kHz for 2 s");
  const uint32_t end = millis() + 2000;
  while (millis() < end) {
    digitalWrite(PIN_LED, HIGH);
    delayMicroseconds(500);
    digitalWrite(PIN_LED, LOW);
    delayMicroseconds(500);
  }
  Cli.println("la done");
}

static void handleLine(char *line) {
  char *cmd = strtok(line, " \t\r\n");
  if (!cmd) {
    return;
  }

  if (!strcasecmp(cmd, "help") || !strcasecmp(cmd, "?")) {
    printHelp();
  } else if (!strcasecmp(cmd, "status")) {
    printStatus();
  } else if (!strcasecmp(cmd, "selftest")) {
    selftest();
  } else if (!strcasecmp(cmd, "i2c")) {
    i2cScan();
  } else if (!strcasecmp(cmd, "bme") || !strcasecmp(cmd, "bmp")) {
    printBme();
  } else if (!strcasecmp(cmd, "ina")) {
    printIna();
  } else if (!strcasecmp(cmd, "us100")) {
    pingUs100();
  } else if (!strcasecmp(cmd, "la")) {
    laSquare();
  } else {
    Cli.printf("unknown '%s' - type help\n", cmd);
  }
}

static void pollStream(Stream &s, char *buf, uint8_t &len) {
  while (s.available()) {
    const char c = static_cast<char>(s.read());
    if (c == '\r') {
      continue;
    }
    if (c == '\n') {
      buf[len] = 0;
      if (len > 0) {
        handleLine(buf);
      }
      len = 0;
      continue;
    }
    if (len + 1 < 96) {
      buf[len++] = c;
    }
  }
}

static void pollButtons() {
  const uint32_t now = millis();
  for (int i = 0; i < 4; i++) {
    const bool up = digitalRead(kBtns[i]) == HIGH;
    if (up == btnLast[i]) {
      continue;
    }
    if (now - btnAt[i] < BTN_DEBOUNCE_MS) {
      continue;
    }
    btnAt[i] = now;
    btnLast[i] = up;
    if (up) {
      continue;
    }
    Cli.printf("BTN%d pressed\n", i + 1);
    switch (i) {
    case 0:
      selftest();
      break;
    case 1:
      printIna();
      break;
    case 2:
      pingUs100();
      break;
    case 3:
      printBme();
      break;
    }
  }
}

void setup() {
  Serial0.begin(UART0_BAUD, SERIAL_8N1, PIN_UART0_RX, PIN_UART0_TX);
  Serial.begin(115200);
  Serial.setTxTimeoutMs(0);
  delay(1500);
  Cli.println("esp32s3-qa");
  pinMode(PIN_LED, OUTPUT);
  digitalWrite(PIN_LED, HIGH);
  for (uint8_t p : kBtns) {
    pinMode(p, INPUT_PULLUP);
  }
  sonarBegin();
  sensorsBegin();
  wifiBegin();
  Cli.println("ready - type help");
  printHelp();
}

void loop() {
  digitalWrite(PIN_LED, (millis() / LED_BLINK_MS) % 2 ? HIGH : LOW);
  wifiPoll();
  pollStream(Serial, serBuf, serLen);
  pollStream(Serial0, uartBuf, uartLen);
  Stream *tcp = wifiStream();
  if (tcp) {
    pollStream(*tcp, tcpBuf, tcpLen);
  }
  pollButtons();
}
