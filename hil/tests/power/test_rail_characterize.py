"""Power tests: DUT (Device Under Test) stays alive at 5.1 V and 5.2 V."""

from __future__ import annotations

import time

import pytest
from drivers.dut_cli import DutCli
from drivers.owon_psu import OwonSpm3051


def _set_and_ping(owon: OwonSpm3051, power_dut: DutCli, volts: float) -> None:
    owon.apply(volts, settle_s=1.0)
    time.sleep(0.3)
    v = owon.meas_voltage()
    assert abs(v - volts) <= 0.15, (
        f"meas V={v} set={volts} VOLT?={owon.volt_setpoint()} LIM?={owon.ovp_setpoint()}"
    )
    try:
        power_dut.prove_alive(8)
    except AssertionError:
        power_dut.recover(30)
    power_dut.send("bme")
    got = power_dut.wait_for(r"gy-bm PASS", 8)
    assert "PASS" in got, f"BME280 failed at {volts} V: {got!r}"


@pytest.mark.power
@pytest.mark.hardware
def test_rail_5v1_dut_responsive(owon: OwonSpm3051, power_dut: DutCli) -> None:
    _set_and_ping(owon, power_dut, 5.1)


@pytest.mark.power
@pytest.mark.hardware
def test_rail_5v2_dut_responsive(owon: OwonSpm3051, power_dut: DutCli) -> None:
    _set_and_ping(owon, power_dut, 5.2)
    owon.apply(5.0, settle_s=0.8)
