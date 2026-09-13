"""OWON SPM3051 SCPI driver for HIL power tests (DUT-safe voltage range only)."""

from __future__ import annotations

import logging
import os
import time

import serial
from serial.tools import list_ports

logger = logging.getLogger(__name__)

BAUD = 115200
QUERY_TIMEOUT_S = 1.0
ESP32_PORT = os.environ.get("ESP32_PORT", "/dev/ttyACM0")
DEFAULT_OWON_PORT = os.environ.get("OWON_PORT", "")

_SKIP_HINTS = (
    "espressif",
    "usb jtag",
    "cp210",
    "silicon labs",
    "ch340",
    "ch341",
    "ch343",
    "wch",
)


class OwonSpm3051:
    def __init__(self, port: str):
        self.port = port
        self.ser = serial.Serial(
            port=port,
            baudrate=BAUD,
            timeout=QUERY_TIMEOUT_S,
            dsrdtr=False,
            rtscts=False,
        )
        self.ser.dtr = False
        self.ser.rts = False
        time.sleep(0.2)
        self.ser.reset_input_buffer()

    def close(self) -> None:
        self.ser.close()

    def write(self, cmd: str) -> None:
        self.ser.reset_input_buffer()
        self.ser.write(f"{cmd}\r\n".encode("ascii"))
        self.ser.flush()
        time.sleep(0.05)

    def query(self, cmd: str) -> str:
        self.write(cmd)
        raw = self.ser.readline().decode("ascii", "replace").strip()
        if not raw:
            raise TimeoutError(f"{self.port}: no reply to {cmd}")
        return raw

    def ident(self) -> str:
        idn = self.query("*IDN?")
        logger.info("OWON *IDN? %s", idn)
        return idn

    def remote(self) -> None:
        """SPM3051 ignores OUTP/VOLT until remote (SYST:REM). *IDN? works anyway."""
        self.write("SYST:REM")
        time.sleep(0.15)

    def output(self, on: bool) -> None:
        self.remote()
        self.write(f"OUTP {'ON' if on else 'OFF'}")
        time.sleep(0.1)

    def output_is_on(self) -> bool:
        st = self.query("OUTP?").strip().upper()
        if st in ("1", "ON", "TRUE"):
            return True
        try:
            return float(st) >= 0.5
        except ValueError:
            return False

    def set_current(self, amps: float) -> None:
        self.write(f"CURR {amps:.3f}")

    def set_ovp(self, volts: float) -> None:
        self.write(f"VOLT:LIM {volts:.2f}")

    def set_voltage(self, volts: float) -> None:
        if volts < 0 or volts > 5.5:
            raise ValueError(f"refusing unsafe DUT voltage {volts} V (max 5.5)")
        self.write(f"VOLT {volts:.2f}")

    def meas_voltage(self) -> float:
        return float(self.query("MEAS:VOLT?"))

    def meas_current(self) -> float:
        return float(self.query("MEAS:CURR?"))

    def volt_setpoint(self) -> float:
        return float(self.query("VOLT?"))

    def ovp_setpoint(self) -> float:
        return float(self.query("VOLT:LIM?"))

    def apply(self, volts: float, ilim_a: float = 0.5, settle_s: float = 0.8) -> None:
        """Set CV (constant voltage). Do not cut the rail if it is already on (that hung the DUT)."""
        logger.info(
            "OWON apply %.2f V, Ilim=%.3f A, settle=%.1fs", volts, ilim_a, settle_s
        )
        self.remote()
        try:
            already_on = self.output_is_on()
        except Exception:
            already_on = False
        if not already_on:
            self.output(False)
        self.set_current(ilim_a)
        # Keep OVP at the DUT-safe ceiling. Lowering VOLT:LIM during brownout
        # (volts+1) left ~4.0 V OVP and later 5.0/5.1/5.2 V setpoints folded back.
        self.set_ovp(6.0)
        self.set_voltage(volts)
        self.output(True)
        time.sleep(settle_s)
        if not self.output_is_on():
            raise RuntimeError(
                "OWON OUTP? is not ON after apply (need SYST:REM / USB remote)"
            )
        got = self.volt_setpoint()
        if abs(got - volts) > 0.05:
            raise RuntimeError(
                f"OWON rejected voltage set: wanted {volts:.2f} V, VOLT?={got}"
            )

    def power_cycle(
        self, volts: float = 5.0, off_s: float = 1.0, boot_s: float = 3.0
    ) -> None:
        logger.info("OWON power-cycle off=%.1fs then %.2f V", off_s, volts)
        self.output(False)
        time.sleep(off_s)
        self.apply(volts, settle_s=boot_s)


def _blob(port: object) -> str:
    return " ".join(
        part
        for part in (
            getattr(port, "device", ""),
            getattr(port, "description", ""),
            getattr(port, "hwid", ""),
        )
        if part
    ).lower()


def find_owon_port() -> str:
    if DEFAULT_OWON_PORT:
        return DEFAULT_OWON_PORT
    candidates = []
    for p in list_ports.comports():
        if p.device == ESP32_PORT:
            continue
        if any(h in _blob(p) for h in _SKIP_HINTS):
            continue
        candidates.append(p.device)
    last_err: Exception | None = None
    for dev in candidates:
        psu = None
        try:
            psu = OwonSpm3051(dev)
            idn = psu.ident()
            if "OWON" in idn.upper() or "SPM" in idn.upper():
                psu.close()
                return dev
            psu.close()
        except Exception as exc:
            last_err = exc
            if psu is not None:
                psu.close()
    hint = f" last error: {last_err}" if last_err else ""
    raise LookupError(f"OWON SPM3051 not found. Set OWON_PORT=...{hint}")
