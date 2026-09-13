"""Power tests: brownout and power-cycle recovery of the DUT (Device Under Test)."""

from __future__ import annotations

import time

import pytest
from drivers.dut_cli import DutCli, open_power_dut, wait_dut_up
from drivers.owon_psu import OwonSpm3051


@pytest.mark.power
@pytest.mark.hardware
def test_power_cycle_boot(owon: OwonSpm3051) -> None:
    try:
        probe = open_power_dut()
        probe.close()
    except LookupError as exc:
        pytest.skip(str(exc))
    owon.power_cycle(volts=5.0, off_s=1.2, boot_s=2.0)
    w = wait_dut_up(60)
    try:
        w.prove_alive(8)
    finally:
        w.close()


@pytest.mark.power
@pytest.mark.hardware
def test_brownout_then_recover(owon: OwonSpm3051, power_dut: DutCli) -> None:
    """Lower Vin until CLI fails, then restore 5.0 V and recover.

    Sensor PASS is not asserted mid-brownout (expected FAIL / silence).
    """
    lost = False
    for v in (4.5, 4.0, 3.6, 3.3, 3.0):
        owon.apply(v, ilim_a=0.5, settle_s=0.8)
        try:
            power_dut.prove_alive(3)
        except AssertionError:
            lost = True
            break

    if not lost:
        owon.output(False)
        time.sleep(1.0)
        lost = True

    assert lost, "DUT (Device Under Test) CLI never dropped during brownout sweep"

    owon.apply(5.0, settle_s=2.0)
    power_dut.recover(60)
