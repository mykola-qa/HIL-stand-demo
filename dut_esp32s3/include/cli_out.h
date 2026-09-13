#pragma once

#include <Print.h>

class CliTee : public Print {
public:
  size_t write(uint8_t b) override;
  size_t write(const uint8_t *buf, size_t n) override;
};

extern CliTee Cli;
