"""Power tests: nominal 5.0 V rail voltage and idle current."""

from __future__ import annotations

import os
import time

import pytest
from drivers.dut_cli import DutCli
from drivers.owon_psu import OwonSpm3051

I_MIN = float(os.environ.get("OWON_I_MIN", "0.020"))
I_MAX = float(os.environ.get("OWON_I_MAX", "0.350"))
V_MIN = float(os.environ.get("OWON_V_MIN", "4.90"))
V_MAX = float(os.environ.get("OWON_V_MAX", "5.10"))


@pytest.mark.power
@pytest.mark.hardware
def test_rail_5v0_within_limits(owon: OwonSpm3051, power_dut: DutCli) -> None:
    owon.apply(5.0, settle_s=1.0)
    v = owon.meas_voltage()
    assert V_MIN <= v <= V_MAX, (
        f"measured {v} V not in [{V_MIN}, {V_MAX}] "
        f"VOLT?={owon.volt_setpoint()} LIM?={owon.ovp_setpoint()}"
    )
    try:
        power_dut.prove_alive(8)
    except AssertionError:
        power_dut.recover(30)


@pytest.mark.power
@pytest.mark.hardware
def test_idle_current_within_limits(owon: OwonSpm3051, power_dut: DutCli) -> None:
    owon.apply(5.0, settle_s=1.5)
    try:
        power_dut.prove_alive(8)
    except AssertionError:
        power_dut.recover(30)
    time.sleep(0.5)
    i = owon.meas_current()
    assert I_MIN <= i <= I_MAX, f"idle current {i} A not in [{I_MIN}, {I_MAX}]"
