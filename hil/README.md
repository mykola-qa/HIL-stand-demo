# HIL orchestrator (Pi 5)

Preferred DUT (Device Under Test) console: **USB-UART adapter** `ESP32_PORT` (TX/RX/GND, no adapter VCC). Unplug DUT native USB before power tests (no VBUS). WiFi `ESP32_HOST` is optional fallback.

A session fixture turns OWON on at **5.0 V / 0.5 A** if the rail is still off. Hardware tests that use `dut` therefore need `OWON_PORT` even when you are not running `-m power`.

```bash
cd hil
pip install -r requirements.txt

# Functional / buttons / LED (USB-UART + OWON rail)
ESP32_PORT=/dev/ttyUSB1 OWON_PORT=/dev/ttyACM1 pytest -m hardware -v
ESP32_PORT=/dev/ttyUSB1 STIM_PORT=/dev/ttyUSB0 OWON_PORT=/dev/ttyACM1 pytest -m stim -v
ESP32_PORT=/dev/ttyUSB1 OWON_PORT=/dev/ttyACM1 pytest -m la -v

# Power (OWON on 5Vin, DUT USB unplugged, same UART adapter)
ESP32_PORT=/dev/ttyUSB1 OWON_PORT=/dev/ttyACM1 pytest -m power -v

# Optional WiFi CLI fallback
ESP32_HOST=<dut-ip> OWON_PORT=/dev/ttyACM1 pytest -m power -v
```

Native ESP USB CDC (`ttyACM*` Espressif) is rejected for `-m power` so VBUS cannot fake the rail.

## Logs

File logging is enabled in `pytest.ini`:

- **File:** `pytest.log` (in `hil/`; overwritten on each local run)
- **Level:** INFO
- **CLI live log:** off (`log_cli = false`) — keep the terminal for pytest results only

Each test is wrapped with markers written by `conftest.py`:

```text
=== START tests/functional/test_cli.py::test_boot_banner_ready ===
...
=== END tests/functional/test_cli.py::test_boot_banner_ready ===
```

To inspect logs:

```bash
less pytest.log
grep -A80 "START tests/power/test_brownout_recovery.py::test_brownout_then_recover" pytest.log
```

Wiring: [`../WIRING.md`](../WIRING.md). PRD: [`../PRD.md`](../PRD.md). Traceability: [`traceability_matrix.md`](traceability_matrix.md).
