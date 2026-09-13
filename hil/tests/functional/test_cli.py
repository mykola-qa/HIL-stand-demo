"""Functional tests: DUT (Device Under Test) CLI liveness."""

from __future__ import annotations

import pytest
from drivers.dut_cli import DutCli


@pytest.mark.hardware
def test_boot_banner_ready(dut: DutCli) -> None:
    dut.send("status")
    got = dut.wait_for(r"US100=4/5", 5)
    assert "US100=4/5" in got, f"status did not report US-100 pins after boot: {got!r}"


@pytest.mark.hardware
def test_help_lists_selftest(dut: DutCli) -> None:
    dut.send("help")
    selftest = dut.wait_for(r"selftest", 5)
    us100 = dut.wait_for(r"us100", 5)
    assert "selftest" in selftest, f"help missing selftest: {selftest!r}"
    assert "us100" in us100, f"help missing us100: {us100!r}"


@pytest.mark.hardware
def test_status_prints_pins(dut: DutCli) -> None:
    dut.send("status")
    us100 = dut.wait_for(r"US100=4/5", 5)
    btn = dut.wait_for(r"BTN=", 5)
    assert "US100=4/5" in us100, f"status missing US-100 pins: {us100!r}"
    assert "BTN=" in btn, f"status missing BTN= line: {btn!r}"
