"""Stimulator button presses mapped to DUT (Device Under Test) CLI actions."""

from __future__ import annotations

import pytest
from drivers.dut_cli import DutCli
from drivers.stim_cli import StimCli


@pytest.mark.hardware
@pytest.mark.stim
def test_btn1_runs_selftest(dut: DutCli, stim: StimCli) -> None:
    dut.drain(0.2)
    stim.press(1, 150)
    pressed = dut.wait_for(r"BTN1 pressed", 5)
    done = dut.wait_for(r"selftest done", 20)
    assert "BTN1" in pressed, f"BTN1 press not seen: {pressed!r}"
    assert "selftest done" in done, f"BTN1 did not finish selftest: {done!r}"


@pytest.mark.hardware
@pytest.mark.stim
def test_btn2_runs_ina(dut: DutCli, stim: StimCli) -> None:
    dut.drain(0.2)
    stim.press(2, 150)
    pressed = dut.wait_for(r"BTN2 pressed", 5)
    got = dut.wait_for(r"ina219 PASS", 8)
    assert "BTN2" in pressed, f"BTN2 press not seen: {pressed!r}"
    assert "PASS" in got, f"BTN2 INA219 check failed: {got!r}"


@pytest.mark.hardware
@pytest.mark.stim
def test_btn3_runs_us100(dut: DutCli, stim: StimCli) -> None:
    dut.drain(0.2)
    stim.press(3, 150)
    pressed = dut.wait_for(r"BTN3 pressed", 5)
    got = dut.wait_for(r"us100 PASS", 8)
    assert "BTN3" in pressed, f"BTN3 press not seen: {pressed!r}"
    assert "PASS" in got, f"BTN3 US-100 check failed: {got!r}"


@pytest.mark.hardware
@pytest.mark.stim
def test_btn4_runs_bme(dut: DutCli, stim: StimCli) -> None:
    dut.drain(0.2)
    stim.press(4, 150)
    pressed = dut.wait_for(r"BTN4 pressed", 5)
    got = dut.wait_for(r"gy-bm PASS", 8)
    assert "BTN4" in pressed, f"BTN4 press not seen: {pressed!r}"
    assert "PASS" in got, f"BTN4 BME280 check failed: {got!r}"
