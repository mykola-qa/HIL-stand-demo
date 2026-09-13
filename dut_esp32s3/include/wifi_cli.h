#pragma once

#include <stddef.h>
#include <stdint.h>

class Stream;

void wifiBegin();
void wifiPoll();
Stream *wifiStream();
void wifiNetWrite(const uint8_t *buf, size_t n);
void wifiPrintStatus();
