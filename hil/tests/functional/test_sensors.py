"""Functional tests: on-board sensor CLI commands."""

from __future__ import annotations

import pytest
from drivers.dut_cli import DutCli


@pytest.mark.hardware
def test_bme_pass(dut: DutCli) -> None:
    dut.send("bme")
    got = dut.wait_for(r"gy-bm PASS", 8)
    assert "PASS" in got, f"BME280 self-check failed: {got!r}"


@pytest.mark.hardware
def test_ina_pass(dut: DutCli) -> None:
    dut.send("ina")
    got = dut.wait_for(r"ina219 PASS", 8)
    assert "PASS" in got, f"INA219 self-check failed: {got!r}"


@pytest.mark.hardware
def test_us100_pass(dut: DutCli) -> None:
    dut.send("us100")
    got = dut.wait_for(r"us100 PASS", 8)
    assert "PASS" in got, f"US-100 self-check failed: {got!r}"


@pytest.mark.hardware
def test_selftest_runs(dut: DutCli) -> None:
    dut.send("selftest")
    got = dut.wait_for(r"selftest done", 20)
    assert "selftest done" in got, f"selftest did not finish: {got!r}"
