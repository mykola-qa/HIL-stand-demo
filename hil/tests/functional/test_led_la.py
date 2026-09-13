"""LED burst on GPIO2 captured with the FX2 logic analyzer."""

from __future__ import annotations

import pytest
from drivers.dut_cli import DutCli
from drivers.logic_analyzer import (
    Capture,
    LogicAnalyzer,
    parse_ch0_csv,
    parse_logic_csv,
)


def test_parse_ch0_csv_skips_header() -> None:
    text = "; comment\nD0\n0\n1\n0\n"
    actual = parse_ch0_csv(text)
    expected = [0, 1, 0]
    assert actual == expected, f"CH0 parse mismatch: {actual} != {expected}"


def test_parse_logic_csv_multi_channel() -> None:
    actual = parse_logic_csv("; h\nD0,D1\n0,1\n1,0\n")
    expected = [[0, 1], [1, 0]]
    assert actual == expected, f"multi-channel parse mismatch: {actual} != {expected}"


def test_ch0_square_stats_synthetic_1khz() -> None:
    fs = 100_000
    bits: list[int] = [0] * 50
    for _ in range(20):
        bits.extend([1] * 50)
        bits.extend([0] * 50)
    freq, dur, n = Capture(bits, fs).ch0_square_stats(800, 1200)
    assert n == 19, f"period count {n} != 19 (freq={freq:.1f} Hz, dur={dur:.3f}s)"
    assert 990.0 <= freq <= 1010.0, f"synthetic freq {freq:.1f} Hz not ~1 kHz"
    assert 0.018 <= dur <= 0.020, f"synthetic burst {dur:.3f} s not ~19 ms"


@pytest.mark.hardware
@pytest.mark.la
def test_la_led_1khz(dut: DutCli, la: LogicAnalyzer) -> None:
    def kick() -> None:
        dut.send("la")
        dut.wait_for(r"la done", 5)

    cap = la.capture_around(kick, duration_s=4.0, arm_s=1.2)
    freq, dur, n = cap.ch0_square_stats(800, 1200)
    assert n >= 800, (
        f"too few 1 kHz periods on CH0: {n} (freq={freq:.1f} Hz, dur={dur:.3f}s)"
    )
    assert 800.0 <= freq <= 1200.0, f"LED freq {freq:.1f} Hz not in 0.8–1.2 kHz"
    assert 1.5 <= dur <= 2.4, f"burst {dur:.3f} s not ~2 s"
