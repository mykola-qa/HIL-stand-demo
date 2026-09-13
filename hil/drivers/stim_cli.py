"""Stimulator ESP CLI — open-drain button emulation toward DUT."""

from __future__ import annotations

import logging
import os
import time

import serial
from serial.tools import list_ports

logger = logging.getLogger(__name__)

BAUD = 115200
DEFAULT_STIM_PORT = os.environ.get("STIM_PORT", "")


class StimCli:
    def __init__(self, port: str):
        self.port = port
        self.ser = serial.Serial(port, BAUD, timeout=0.5)
        time.sleep(0.3)
        self.ser.reset_input_buffer()

    def close(self) -> None:
        self.ser.close()

    def send(self, cmd: str) -> str:
        logger.info("stim TX: %s", cmd)
        self.ser.reset_input_buffer()
        self.ser.write(f"{cmd}\n".encode("ascii"))
        self.ser.flush()
        time.sleep(0.15)
        return self.ser.read(self.ser.in_waiting or 1).decode("utf-8", "replace")

    def press(self, btn: int, ms: int = 120) -> None:
        if btn < 1 or btn > 4:
            raise ValueError("btn must be 1..4")
        logger.info("stim press BTN%d %d ms", btn, ms)
        self.send(f"press {btn} {ms}")


def find_stim_port() -> str:
    if DEFAULT_STIM_PORT:
        return DEFAULT_STIM_PORT
    raise LookupError("Set STIM_PORT to stimulator serial device")


def port_exists(port: str) -> bool:
    if os.path.exists(port):
        return True
    return any(p.device == port for p in list_ports.comports())
