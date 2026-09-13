"""DUT CLI over USB-UART, USB CDC, or WiFi TCP (same esp32s3-qa command set)."""

from __future__ import annotations

import logging
import os
import re
import socket
import time
from collections import deque

import serial
from serial.tools import list_ports

logger = logging.getLogger(__name__)

BAUD = 115200
BOOT_TIMEOUT_S = 45.0
DEFAULT_PORT = os.environ.get("ESP32_PORT", "/dev/ttyACM0")
TCP_HOST = os.environ.get("ESP32_HOST", "")
TCP_PORT = int(os.environ.get("ESP32_TCP", "3333"))

# Espressif USB gadget — native CDC/JTAG, feeds DUT via VBUS.
_ESP_VID = 0x303A


def port_exists(port: str) -> bool:
    if os.path.exists(port):
        return True
    return any(p.device == port for p in list_ports.comports())


def is_native_usb_cdc(port: str) -> bool:
    """True if `port` looks like ESP32-S3 USB CDC (VBUS), not a TX/RX/GND adapter."""
    for p in list_ports.comports():
        if p.device != port:
            continue
        desc = f"{p.description} {p.manufacturer} {p.product}".lower()
        if p.vid == _ESP_VID:
            return True
        if "espressif" in desc or "usb jtag" in desc:
            return True
        return False
    return False


class LineBuf:
    def __init__(self) -> None:
        self.buf = ""
        self.lines: deque[str] = deque(maxlen=400)

    def feed(self, chunk: str) -> None:
        if not chunk:
            return
        self.buf += chunk
        while "\n" in self.buf:
            line, self.buf = self.buf.split("\n", 1)
            line = line.strip("\r")
            if line:
                self.lines.append(line)

    def clear(self) -> None:
        self.buf = ""
        self.lines.clear()

    def wait_for(self, pattern: str, timeout: float, read) -> str:
        rx = re.compile(pattern)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            read()
            for line in reversed(self.lines):
                if rx.search(line):
                    return line
            time.sleep(0.05)
        recent = "\n".join(list(self.lines)[-30:])
        logger.error("timeout %ss waiting for /%s/\n%s", timeout, pattern, recent)
        raise AssertionError(
            f"timeout {timeout}s waiting for /{pattern}/\n--- recent ---\n{recent}"
        )


class DutCli:
    def wait_for(self, pattern: str, timeout: float) -> str:  # pragma: no cover
        raise NotImplementedError

    def send(self, cmd: str) -> None:  # pragma: no cover
        raise NotImplementedError

    def wait_boot_no_dtr(
        self, timeout: float = BOOT_TIMEOUT_S
    ) -> None:  # pragma: no cover
        raise NotImplementedError

    def close(self) -> None:  # pragma: no cover
        raise NotImplementedError

    def _prepare_recover(self) -> None:
        return

    def drain(self, seconds: float = 0.3) -> None:
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            self._read()
            time.sleep(0.05)

    def _read(self) -> None:  # pragma: no cover
        raise NotImplementedError

    def prove_alive(self, timeout: float = 8.0) -> None:
        """Clear RX, send status, require a fresh US100=4/5 (no stale match)."""
        logger.info("prove_alive timeout=%.1fs", timeout)
        self.drain(0.1)
        self._lb.clear()
        self.send("status")
        self.wait_for(r"US100=4/5", timeout)

    def wait_boot(self) -> None:
        try:
            self.prove_alive(5)
        except AssertionError:
            logger.info("status missed; waiting for boot banner")
            self.wait_boot_no_dtr(BOOT_TIMEOUT_S)

    def recover(self, timeout: float = 60.0) -> None:
        """Wait until CLI answers after power loss. Pulse DTR (Data Terminal Ready) → RST if hung."""
        logger.info("recover DUT (Device Under Test) timeout=%.1fs", timeout)
        deadline = time.monotonic() + timeout
        last_err: Exception | None = None
        pulsed = False
        while time.monotonic() < deadline:
            remain = max(1.0, deadline - time.monotonic())
            try:
                self.prove_alive(min(5.0, remain))
                return
            except AssertionError as exc:
                last_err = exc
            try:
                if not pulsed:
                    self._prepare_recover()
                    pulsed = True
                self.wait_boot_no_dtr(min(15.0, max(1.0, deadline - time.monotonic())))
                self.prove_alive(min(8.0, max(1.0, deadline - time.monotonic())))
                return
            except Exception as exc:
                last_err = exc
                self._prepare_recover()
                pulsed = True
                time.sleep(1.0)
        logger.error("DUT (Device Under Test) did not recover: %s", last_err)
        raise AssertionError(f"DUT did not recover: {last_err}")


class DutSerial(DutCli):
    def __init__(self, port: str):
        self.ser = serial.Serial(
            port,
            BAUD,
            timeout=0.2,
            dsrdtr=False,
            rtscts=False,
        )
        self.ser.dtr = False
        self.ser.rts = False
        time.sleep(0.3)
        self.ser.reset_input_buffer()
        self._lb = LineBuf()

    @property
    def lines(self) -> deque[str]:
        return self._lb.lines

    def close(self) -> None:
        self.ser.close()

    def pulse_en(self) -> None:
        """DTR (Data Terminal Ready) → DUT RST (reset) / EN (enable). Assert, then release."""
        logger.info("pulse DTR (Data Terminal Ready) → RST on %s", self.ser.port)
        self.ser.dtr = True
        time.sleep(0.05)
        self.ser.dtr = False
        time.sleep(0.15)
        self.ser.reset_input_buffer()
        self._lb.clear()

    def _prepare_recover(self) -> None:
        self.pulse_en()

    def _read(self) -> None:
        chunk = self.ser.read(self.ser.in_waiting or 1).decode("utf-8", "replace")
        self._lb.feed(chunk)

    def wait_for(self, pattern: str, timeout: float) -> str:
        return self._lb.wait_for(pattern, timeout, self._read)

    def send(self, cmd: str) -> None:
        logger.info("DUT TX: %s", cmd)
        self.ser.write(f"{cmd}\n".encode("ascii"))
        self.ser.flush()

    def wait_boot_no_dtr(self, timeout: float = BOOT_TIMEOUT_S) -> None:
        self._lb.clear()
        self.wait_for(r"esp32s3-qa", timeout)
        self.wait_for(r"ready - type help", timeout)


class DutTcp(DutCli):
    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.sock = socket.create_connection((host, port), timeout=10)
        self.sock.settimeout(0.2)
        self._lb = LineBuf()

    @property
    def lines(self) -> deque[str]:
        return self._lb.lines

    def close(self) -> None:
        try:
            self.sock.close()
        except OSError:
            pass

    def reconnect(self) -> None:
        self.close()
        time.sleep(0.5)
        self._lb.clear()
        self.sock = socket.create_connection((self.host, self.port), timeout=15)
        self.sock.settimeout(0.2)

    def _prepare_recover(self) -> None:
        self.reconnect()

    def _read(self) -> None:
        try:
            chunk = self.sock.recv(256).decode("utf-8", "replace")
        except (TimeoutError, OSError):
            return
        self._lb.feed(chunk)

    def wait_for(self, pattern: str, timeout: float) -> str:
        return self._lb.wait_for(pattern, timeout, self._read)

    def send(self, cmd: str) -> None:
        logger.info("DUT TCP TX: %s", cmd)
        self.sock.sendall(f"{cmd}\n".encode("ascii"))

    def wait_boot_no_dtr(self, timeout: float = BOOT_TIMEOUT_S) -> None:
        self.wait_for(r"esp32s3-qa", timeout)
        self.wait_for(r"ready - type help", timeout)


def open_dut() -> DutCli:
    """Functional CLI: USB-UART / USB CDC first, WiFi if no serial port."""
    if port_exists(DEFAULT_PORT):
        return DutSerial(DEFAULT_PORT)
    if TCP_HOST:
        return DutTcp(TCP_HOST, TCP_PORT)
    raise LookupError(f"no ESP32 on {DEFAULT_PORT} (set ESP32_PORT or ESP32_HOST)")


def open_power_dut() -> DutCli:
    """Power-test CLI: TX/RX/GND adapter or WiFi. Reject native USB CDC (VBUS)."""
    if port_exists(DEFAULT_PORT):
        if is_native_usb_cdc(DEFAULT_PORT):
            raise LookupError(
                f"{DEFAULT_PORT} looks like ESP USB CDC (VBUS). "
                "Unplug DUT USB; set ESP32_PORT to the TX/RX/GND adapter "
                "or set ESP32_HOST"
            )
        return DutSerial(DEFAULT_PORT)
    if TCP_HOST:
        return DutTcp(TCP_HOST, TCP_PORT)
    raise LookupError("power tests need ESP32_PORT (TX/RX/GND USB-UART) or ESP32_HOST")


def wait_dut_up(timeout: float = 60.0) -> DutCli:
    """Open a power-safe console and wait until `status` works."""
    deadline = time.monotonic() + timeout
    last_err: Exception | None = None
    while time.monotonic() < deadline:
        w: DutCli | None = None
        try:
            w = open_power_dut()
            remain = max(5.0, deadline - time.monotonic())
            w.recover(remain)
            return w
        except LookupError:
            raise
        except Exception as exc:
            last_err = exc
            if w is not None:
                w.close()
            time.sleep(1.5)
    raise AssertionError(f"DUT did not come up: {last_err}")
