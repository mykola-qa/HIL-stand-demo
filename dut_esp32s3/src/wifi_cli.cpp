#include "wifi_cli.h"

#include "cli_out.h"
#include "config.h"
#include <Arduino.h>
#include <ESPmDNS.h>
#include <WiFi.h>

#if __has_include("wifi_secrets.h")
#include "wifi_secrets.h"
#else
#define WIFI_SSID ""
#define WIFI_PASS ""
#endif

static WiFiServer server(WIFI_TCP_PORT);
static WiFiClient client;
static bool wifiUp;
static bool tcpOpen;

void wifiNetWrite(const uint8_t *buf, size_t n) {
  if (!n || !tcpOpen) {
    return;
  }
  client.write(buf, n);
}

Stream *wifiStream() {
  if (tcpOpen) {
    return &client;
  }
  return nullptr;
}

void wifiPrintStatus() {
  if (!wifiUp) {
    Cli.println("wifi: down");
    return;
  }
  Cli.printf("wifi: %s ip=%s rssi=%d tcp=%u\n", WiFi.SSID().c_str(),
             WiFi.localIP().toString().c_str(), WiFi.RSSI(), WIFI_TCP_PORT);
}

void wifiBegin() {
  if (WIFI_SSID[0] == '\0') {
    Cli.println("wifi: skipped (no wifi_secrets.h)");
    return;
  }
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  const uint32_t t0 = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - t0 < WIFI_CONNECT_MS) {
    delay(200);
  }
  if (WiFi.status() != WL_CONNECTED) {
    Cli.println("wifi FAIL timeout (2.4 GHz SSID? secrets?)");
    return;
  }
  wifiUp = true;
  server.begin();
  server.setNoDelay(true);
  if (MDNS.begin("esp32s3-qa")) {
    MDNS.addService("telnet", "tcp", WIFI_TCP_PORT);
  }
  Cli.printf("wifi PASS %s ip=%s tcp=%u  nc %s %u\n", WiFi.SSID().c_str(),
             WiFi.localIP().toString().c_str(), WIFI_TCP_PORT,
             WiFi.localIP().toString().c_str(), WIFI_TCP_PORT);
}

void wifiPoll() {
  if (!wifiUp) {
    return;
  }
  if (tcpOpen && !client.connected() && !client.available()) {
    client.stop();
    tcpOpen = false;
  }
  if (tcpOpen) {
    return;
  }
  WiFiClient next = server.available();
  if (!next) {
    return;
  }
  client.stop();
  client = next;
  client.setNoDelay(true);
  client.setTimeout(50);
  tcpOpen = true;
  Cli.println("esp32s3-qa");
  Cli.println("ready - type help");
}
