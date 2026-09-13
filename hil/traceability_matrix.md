# Traceability Matrix — esp32s3-qa HIL

Scheme: **PRD requirement → test file → test function**.

PRD: [`../PRD.md`](../PRD.md). Wiring: [`../WIRING.md`](../WIRING.md).

| Req ID | PRD requirement (short) | Test file | Test function |
|--------|-------------------------|-----------|---------------|
| FR-01 | Boot banner + ready | `hil/tests/functional/test_cli.py` | `test_boot_banner_ready` |
| FR-02 | help lists commands | `hil/tests/functional/test_cli.py` | `test_help_lists_selftest` |
| FR-03 | status pin map | `hil/tests/functional/test_cli.py` | `test_status_prints_pins` |
| FR-04 | bme/bmp PASS | `hil/tests/functional/test_sensors.py` | `test_bme_pass` |
| FR-05 | ina PASS | `hil/tests/functional/test_sensors.py` | `test_ina_pass` |
| FR-06 | us100 PASS | `hil/tests/functional/test_sensors.py` | `test_us100_pass` |
| FR-07 | BTN1 → selftest | `hil/tests/stim/test_buttons.py` | `test_btn1_runs_selftest` |
| FR-08 | BTN2 ina | `hil/tests/stim/test_buttons.py` | `test_btn2_runs_ina` |
| FR-08 | BTN3 us100 | `hil/tests/stim/test_buttons.py` | `test_btn3_runs_us100` |
| FR-08 | BTN4 bme | `hil/tests/stim/test_buttons.py` | `test_btn4_runs_bme` |
| FR-09 | selftest multi-line | `hil/tests/functional/test_sensors.py` | `test_selftest_runs` |
| FR-10 | WiFi CLI same commands | `hil/tests/functional/test_cli.py` | `test_status_prints_pins` (via `ESP32_HOST`) |
| NFR-01 | 5.0 V rail window | `hil/tests/power/test_rail_nominal.py` | `test_rail_5v0_within_limits` |
| NFR-02 | 5.1 V characterization | `hil/tests/power/test_rail_characterize.py` | `test_rail_5v1_dut_responsive` |
| NFR-02 | 5.2 V characterization | `hil/tests/power/test_rail_characterize.py` | `test_rail_5v2_dut_responsive` |
| NFR-03 | Idle current min–max | `hil/tests/power/test_rail_nominal.py` | `test_idle_current_within_limits` |
| NFR-04 | Brownout recovery | `hil/tests/power/test_brownout_recovery.py` | `test_brownout_then_recover` |
| NFR-05 | Power-cycle reset | `hil/tests/power/test_brownout_recovery.py` | `test_power_cycle_boot` |
| NFR-06 | No USB VBUS on power tests | `WIRING.md` + `open_power_dut()` rejects Espressif USB CDC | `power_dut` / `open_power_dut` in `conftest.py` / `dut_cli.py` |
| NFR-07 | US-100 3.3 V echo, no divider | Covered by stand rules in `WIRING.md` (process req; no runtime assert) | — |
| NFR-08 | Full automation from Pi 5 | Entire `hil/` pytest package | suite entry via `pytest` |

## Coverage statement

All FR-01…FR-10 and NFR-01…NFR-08 (non-functional requirements) from [PRD.md](../PRD.md) are mapped. NFR-07 is a hardware safety constraint enforced by wiring procedure rather than a pytest assert.
