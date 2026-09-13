"""FX2 logic analyzer via sigrok-cli (headless, pytest)."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

logger = logging.getLogger(__name__)

SIGROK_BIN = os.environ.get("SIGROK_BIN", "sigrok-cli")
DRIVER = "fx2lafw"
SAMPLERATE = os.environ.get("LA_SAMPLERATE", "100kHz")
SAMPLERATE_HZ = int(os.environ.get("LA_SAMPLERATE_HZ", "100000"))
CHANNELS = os.environ.get("LA_CHANNELS", "D0")


def _have_bin(path: str) -> bool:
    return shutil.which(path) is not None or os.path.isfile(path)


def _logic_row(line: str) -> list[int] | None:
    s = line.strip().strip("\r")
    if not s or s[0] in ";#":
        return None
    parts = [p.strip() for p in s.split(",")]
    if not parts:
        return None
    if any(c.isalpha() for c in parts[0]):
        return None
    start = 0
    if parts[0] not in ("0", "1"):
        try:
            float(parts[0])
        except ValueError:
            return None
        start = 1
    bits: list[int] = []
    for p in parts[start:]:
        if p not in ("0", "1"):
            break
        bits.append(int(p))
    return bits or None


def parse_logic_csv(text: str) -> list[list[int]]:
    rows: list[list[int]] = []
    width = 0
    for line in text.splitlines():
        bits = _logic_row(line)
        if bits is None:
            continue
        rows.append(bits)
        width = max(width, len(bits))
    if not rows or width == 0:
        return []
    chans: list[list[int]] = [[] for _ in range(width)]
    for row in rows:
        for i in range(width):
            chans[i].append(row[i] if i < len(row) else 0)
    return chans


def parse_ch0_csv(text: str) -> list[int]:
    chans = parse_logic_csv(text)
    return chans[0] if chans else []


def square_stats(
    bits: list[int], samplerate_hz: int, fmin: float, fmax: float
) -> tuple[float, float, int]:
    """Mean freq, burst length, period count from rising edges in [fmin, fmax]."""
    t_rise: list[float] = []
    prev: int | None = None
    fs = float(samplerate_hz)
    for i, bit in enumerate(bits):
        b = 1 if bit else 0
        if prev == 0 and b == 1:
            t_rise.append(i / fs)
        prev = b
    tmin = 1.0 / fmax
    tmax = 1.0 / fmin
    periods: list[float] = []
    t0: float | None = None
    t1: float | None = None
    for a, b in zip(t_rise, t_rise[1:]):
        dt = b - a
        if tmin <= dt <= tmax:
            periods.append(dt)
            if t0 is None:
                t0 = a
            t1 = b
    if not periods:
        raise AssertionError(
            "no 1 kHz-band periods (probe off, wrong channel, or LED idle)"
        )
    mean = sum(periods) / len(periods)
    dur = (t1 - t0) if t0 is not None and t1 is not None else 0.0
    return 1.0 / mean, dur, len(periods)


class Capture:
    def __init__(self, ch0: list[int] | list[list[int]], samplerate_hz: int):
        if not ch0:
            self.channels: list[list[int]] = []
        elif isinstance(ch0[0], list):
            self.channels = list(ch0)  # type: ignore[arg-type]
        else:
            self.channels = [list(ch0)]  # type: ignore[arg-type]
        self.ch0 = self.channels[0] if self.channels else []
        self.samplerate_hz = samplerate_hz

    def channel_square_stats(
        self, idx: int, fmin: float, fmax: float
    ) -> tuple[float, float, int]:
        if idx < 0 or idx >= len(self.channels):
            raise AssertionError(f"no samples on D{idx}")
        return square_stats(self.channels[idx], self.samplerate_hz, fmin, fmax)

    def ch0_square_stats(self, fmin: float, fmax: float) -> tuple[float, float, int]:
        return self.channel_square_stats(0, fmin, fmax)

    def band_hits(self, fmin: float, fmax: float) -> str:
        parts: list[str] = []
        for i in range(len(self.channels)):
            try:
                freq, dur, n = self.channel_square_stats(i, fmin, fmax)
            except AssertionError:
                continue
            parts.append(f"D{i} {freq:.1f}Hz n={n} dur={dur:.3f}s")
        return ", ".join(parts) if parts else "none"


class LogicAnalyzer:
    def __init__(self, binary: str = SIGROK_BIN):
        self.binary = binary

    def scan(self) -> bool:
        try:
            proc = subprocess.run(
                [self.binary, "--scan"],
                capture_output=True,
                text=True,
                timeout=20,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            return False
        blob = (proc.stdout or "") + (proc.stderr or "")
        return DRIVER in blob.lower()

    def capture_around(
        self,
        fn,
        duration_s: float = 4.0,
        arm_s: float = 1.2,
        samplerate: str = SAMPLERATE,
        samplerate_hz: int = SAMPLERATE_HZ,
        channels: str = CHANNELS,
    ) -> Capture:
        tmp = tempfile.NamedTemporaryFile(prefix="la_", suffix=".csv", delete=False)
        tmp.close()
        path = tmp.name
        cmd = [
            self.binary,
            "-d",
            DRIVER,
            "--config",
            f"samplerate={samplerate}",
            "--channels",
            channels,
            "--time",
            f"{int(round(duration_s))}s",
            "-O",
            "csv",
            "-o",
            path,
        ]
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
            )
            try:
                time.sleep(arm_s)
                fn()
                _, stderr = proc.communicate(timeout=duration_s + 15)
            except Exception:
                proc.kill()
                proc.communicate(timeout=5)
                raise
            if proc.returncode != 0:
                raise RuntimeError(
                    f"sigrok-cli failed ({proc.returncode}): {(stderr or '').strip()}"
                )
            text = Path(path).read_text(encoding="utf-8", errors="replace")
            chans = parse_logic_csv(text)
            n0 = len(chans[0]) if chans else 0
            logger.info("LA capture CH0 samples=%d fs=%d", n0, samplerate_hz)
            if n0 < samplerate_hz // 10:
                raise AssertionError(
                    f"too few CH0 samples ({n0}); stderr={(stderr or '').strip()}"
                )
            return Capture(chans, samplerate_hz)
        finally:
            try:
                os.unlink(path)
            except OSError:
                pass


def find_logic_analyzer() -> LogicAnalyzer:
    if not _have_bin(SIGROK_BIN):
        raise LookupError(
            "sigrok-cli not found (install sigrok-cli and sigrok-firmware-fx2lafw)"
        )
    la = LogicAnalyzer(SIGROK_BIN)
    if not la.scan():
        raise LookupError("no fx2lafw logic analyzer (use a USB 2.0 port on the Pi 5)")
    return la
