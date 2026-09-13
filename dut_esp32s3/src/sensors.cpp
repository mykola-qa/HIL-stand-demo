#include "sensors.h"

#include "cli_out.h"
#include "config.h"
#include <Wire.h>
#include <string.h>

static uint8_t bmeAddr;
static uint8_t bmeChip;
static bool bmeReady;
static int32_t dig_T1, dig_T2, dig_T3;
static int32_t dig_P1, dig_P2, dig_P3, dig_P4, dig_P5, dig_P6, dig_P7, dig_P8, dig_P9;
static int32_t dig_H1, dig_H2, dig_H3, dig_H4, dig_H5, dig_H6;
static int32_t t_fine;

static uint8_t inaAddr;
static bool inaReady;
static const float kCurrentLsb = 0.0001f;

static bool i2cRead(uint8_t addr, uint8_t reg, uint8_t *buf, size_t n) {
  Wire.beginTransmission(addr);
  Wire.write(reg);
  if (Wire.endTransmission(false) != 0) {
    return false;
  }
  const size_t got = Wire.requestFrom(static_cast<int>(addr), static_cast<int>(n));
  if (got != n) {
    return false;
  }
  for (size_t i = 0; i < n; i++) {
    buf[i] = static_cast<uint8_t>(Wire.read());
  }
  return true;
}

static bool i2cWrite(uint8_t addr, uint8_t reg, uint8_t val) {
  Wire.beginTransmission(addr);
  Wire.write(reg);
  Wire.write(val);
  return Wire.endTransmission() == 0;
}

static bool i2cWrite16(uint8_t addr, uint8_t reg, uint16_t val) {
  Wire.beginTransmission(addr);
  Wire.write(reg);
  Wire.write(static_cast<uint8_t>(val >> 8));
  Wire.write(static_cast<uint8_t>(val));
  return Wire.endTransmission() == 0;
}

static bool i2cRead16(uint8_t addr, uint8_t reg, uint16_t *val) {
  uint8_t b[2];
  if (!i2cRead(addr, reg, b, 2)) {
    return false;
  }
  *val = (static_cast<uint16_t>(b[0]) << 8) | b[1];
  return true;
}

static bool i2cProbe(uint8_t addr) {
  Wire.beginTransmission(addr);
  return Wire.endTransmission() == 0;
}

static int32_t compensateT(int32_t adcT) {
  int32_t var1 = ((((adcT >> 3) - (dig_T1 << 1))) * dig_T2) >> 11;
  int32_t var2 =
      (((((adcT >> 4) - dig_T1) * ((adcT >> 4) - dig_T1)) >> 12) * dig_T3) >> 14;
  t_fine = var1 + var2;
  return (t_fine * 5 + 128) >> 8;
}

static uint32_t compensateP(int32_t adcP) {
  int64_t var1 = static_cast<int64_t>(t_fine) - 128000;
  int64_t var2 = var1 * var1 * static_cast<int64_t>(dig_P6);
  var2 = var2 + ((var1 * static_cast<int64_t>(dig_P5)) << 17);
  var2 = var2 + (static_cast<int64_t>(dig_P4) << 35);
  var1 = ((var1 * var1 * static_cast<int64_t>(dig_P3)) >> 8) +
         ((var1 * static_cast<int64_t>(dig_P2)) << 12);
  var1 = (((((int64_t)1) << 47) + var1)) * static_cast<int64_t>(dig_P1) >> 33;
  if (var1 == 0) {
    return 0;
  }
  int64_t p = 1048576 - adcP;
  p = (((p << 31) - var2) * 3125) / var1;
  var1 = (static_cast<int64_t>(dig_P9) * (p >> 13) * (p >> 13)) >> 25;
  var2 = (static_cast<int64_t>(dig_P8) * p) >> 19;
  p = ((p + var1 + var2) >> 8) + (static_cast<int64_t>(dig_P7) << 4);
  return static_cast<uint32_t>(p);
}

static uint32_t compensateH(int32_t adcH) {
  int32_t v = t_fine - 76800;
  v = (((((adcH << 14) - (dig_H4 << 20) - (dig_H5 * v)) + 16384) >> 15) *
       (((((((v * dig_H6) >> 10) * (((v * dig_H3) >> 11) + 32768)) >> 10) +
           2097152) *
              dig_H2 +
          8192) >>
         14));
  v = v - (((((v >> 15) * (v >> 15)) >> 7) * dig_H1) >> 4);
  if (v < 0) {
    v = 0;
  }
  if (v > 419430400) {
    v = 419430400;
  }
  return static_cast<uint32_t>(v >> 12);
}

static bool loadCalib(uint8_t addr, bool humidity) {
  uint8_t c[26];
  if (!i2cRead(addr, 0x88, c, 26)) {
    return false;
  }
  dig_T1 = c[0] | (c[1] << 8);
  dig_T2 = static_cast<int16_t>(c[2] | (c[3] << 8));
  dig_T3 = static_cast<int16_t>(c[4] | (c[5] << 8));
  dig_P1 = c[6] | (c[7] << 8);
  dig_P2 = static_cast<int16_t>(c[8] | (c[9] << 8));
  dig_P3 = static_cast<int16_t>(c[10] | (c[11] << 8));
  dig_P4 = static_cast<int16_t>(c[12] | (c[13] << 8));
  dig_P5 = static_cast<int16_t>(c[14] | (c[15] << 8));
  dig_P6 = static_cast<int16_t>(c[16] | (c[17] << 8));
  dig_P7 = static_cast<int16_t>(c[18] | (c[19] << 8));
  dig_P8 = static_cast<int16_t>(c[20] | (c[21] << 8));
  dig_P9 = static_cast<int16_t>(c[22] | (c[23] << 8));
  dig_H1 = c[25];
  if (!humidity) {
    return true;
  }
  uint8_t h[7];
  if (!i2cRead(addr, 0xE1, h, 7)) {
    return false;
  }
  dig_H2 = static_cast<int16_t>(h[0] | (h[1] << 8));
  dig_H3 = h[2];
  int32_t h4 = (h[3] << 4) | (h[4] & 0x0F);
  int32_t h5 = (h[5] << 4) | (h[4] >> 4);
  if (h4 & 0x800) {
    h4 |= ~0xFFF;
  }
  if (h5 & 0x800) {
    h5 |= ~0xFFF;
  }
  dig_H4 = h4;
  dig_H5 = h5;
  dig_H6 = static_cast<int8_t>(h[6]);
  return true;
}

static bool bmeInit() {
  bmeReady = false;
  bmeAddr = 0;
  const uint8_t addrs[] = {0x76, 0x77};
  for (uint8_t addr : addrs) {
    if (!i2cProbe(addr)) {
      continue;
    }
    uint8_t id = 0;
    if (!i2cRead(addr, 0xD0, &id, 1)) {
      continue;
    }
    if (id != 0x60 && id != 0x58) {
      Cli.printf("gy-bm 0x%02X chip id 0x%02X (not BME/BMP280)\n", addr, id);
      continue;
    }
    if (!i2cWrite(addr, 0xE0, 0xB6)) {
      continue;
    }
    delay(10);
    const bool hum = (id == 0x60);
    if (!loadCalib(addr, hum)) {
      continue;
    }
    bmeAddr = addr;
    bmeChip = id;
    bmeReady = true;
    Cli.printf("gy-bm %s @ 0x%02X\n", hum ? "BME280" : "BMP280", addr);
    return true;
  }
  Cli.println("gy-bm FAIL not found (VCC=3V3 CSB=3V3 SDO=GND)");
  return false;
}

static bool inaInit() {
  inaReady = false;
  inaAddr = 0;
  const uint8_t addrs[] = {0x40, 0x41, 0x44, 0x45};
  for (uint8_t addr : addrs) {
    if (!i2cProbe(addr)) {
      continue;
    }
    if (!i2cWrite16(addr, 0x00, 0x399F)) {
      continue;
    }
    if (!i2cWrite16(addr, 0x05, 4096)) {
      continue;
    }
    inaAddr = addr;
    inaReady = true;
    Cli.printf("ina219 @ 0x%02X cal=4096\n", addr);
    return true;
  }
  Cli.println("ina219 FAIL not found");
  return false;
}

void sensorsBegin() {
  Wire.begin(PIN_I2C_SDA, PIN_I2C_SCL);
  Wire.setClock(I2C_FREQ_HZ);
  Wire.setTimeOut(50);
  bmeInit();
  inaInit();
}

void i2cScan() {
  int found = 0;
  Cli.println("i2c scan 0x03..0x77:");
  for (uint8_t addr = 0x03; addr <= 0x77; addr++) {
    if (i2cProbe(addr)) {
      Cli.printf("  found 0x%02X\n", addr);
      found++;
    }
  }
  if (!found) {
    Cli.println("  none (FAIL if a module should be connected)");
  }
}

void printBme() {
  if (!bmeReady && !bmeInit()) {
    return;
  }
  const bool hum = (bmeChip == 0x60);
  if (hum && !i2cWrite(bmeAddr, 0xF2, 0x01)) {
    bmeReady = false;
    Cli.println("gy-bm FAIL write");
    return;
  }
  if (!i2cWrite(bmeAddr, 0xF4, 0x25)) {
    bmeReady = false;
    Cli.println("gy-bm FAIL write");
    return;
  }
  delay(15);
  uint8_t d[8];
  const size_t n = hum ? 8 : 6;
  if (!i2cRead(bmeAddr, 0xF7, d, n)) {
    bmeReady = false;
    Cli.println("gy-bm FAIL read");
    return;
  }
  const int32_t adcP = (static_cast<int32_t>(d[0]) << 12) |
                       (static_cast<int32_t>(d[1]) << 4) | (d[2] >> 4);
  const int32_t adcT = (static_cast<int32_t>(d[3]) << 12) |
                       (static_cast<int32_t>(d[4]) << 4) | (d[5] >> 4);
  const float tC = compensateT(adcT) / 100.0f;
  const float pPa = compensateP(adcP) / 256.0f;
  if (hum) {
    const int32_t adcH = (static_cast<int32_t>(d[6]) << 8) | d[7];
    const float rh = compensateH(adcH) / 1024.0f;
    Cli.printf("gy-bm PASS BME280 0x%02X T=%.2fC P=%.0fPa H=%.1f%%\n", bmeAddr,
                  tC, pPa, rh);
  } else {
    Cli.printf("gy-bm PASS BMP280 0x%02X T=%.2fC P=%.0fPa\n", bmeAddr, tC, pPa);
  }
}

void printIna() {
  if (!inaReady && !inaInit()) {
    return;
  }
  uint16_t bus = 0, shunt = 0, cur = 0, pwr = 0;
  if (!i2cRead16(inaAddr, 0x02, &bus) || !i2cRead16(inaAddr, 0x01, &shunt) ||
      !i2cRead16(inaAddr, 0x04, &cur) || !i2cRead16(inaAddr, 0x03, &pwr)) {
    inaReady = false;
    Cli.println("ina219 FAIL read");
    return;
  }
  const float busV = (bus >> 3) * 0.004f;
  const float shuntV = static_cast<int16_t>(shunt) * 0.00001f;
  const float amp = static_cast<int16_t>(cur) * kCurrentLsb;
  const float watts = pwr * 20.0f * kCurrentLsb;
  Cli.printf("ina219 PASS 0x%02X Vbus=%.3fV Vshunt=%.5fV I=%.4fA P=%.4fW\n",
                inaAddr, busV, shuntV, amp, watts);
}

void printSensors() {
  printBme();
  printIna();
}
