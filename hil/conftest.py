"""pytest fixtures for the HIL (Hardware-In-the-Loop) suite."""

from __future__ import annotations

import logging
from collections.abc import Iterator

import pytest
from drivers.dut_cli import DutCli, open_dut, open_power_dut
from drivers.logic_analyzer import LogicAnalyzer, find_logic_analyzer
from drivers.owon_psu import OwonSpm3051, find_owon_port
from drivers.stim_cli import StimCli, find_stim_port, port_exists

logger = logging.getLogger(__name__)


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item: pytest.Item) -> None:
    logger.info("=== START %s ===", item.nodeid)


@pytest.hookimpl(trylast=True)
def pytest_runtest_teardown(item: pytest.Item) -> None:
    logger.info("=== END %s ===", item.nodeid)


def _hw_test(request: pytest.FixtureRequest) -> bool:
    node = request.node
    return (
        node.get_closest_marker("hardware") is not None
        or node.get_closest_marker("power") is not None
    )


def _open_console() -> DutCli | None:
    try:
        return open_dut()
    except LookupError:
        try:
            return open_power_dut()
        except LookupError:
            return None


@pytest.fixture(scope="session")
def owon_session() -> Iterator[OwonSpm3051]:
    """Bring up OWON at 5.0 V / 0.5 A once if the rail is still off."""
    try:
        port = find_owon_port()
    except LookupError as exc:
        pytest.skip(str(exc))
    psu = OwonSpm3051(port)
    try:
        logger.info("OWON session %s IDN=%s", port, psu.ident())
        psu.apply(5.0, ilim_a=0.5, settle_s=2.0)
        yield psu
    finally:
        try:
            psu.apply(5.0, ilim_a=0.5, settle_s=0.5)
        except (OSError, RuntimeError, TimeoutError):
            logger.exception("OWON session restore failed; cutting output")
            psu.output(False)
        psu.close()


@pytest.fixture
def owon(owon_session: OwonSpm3051) -> Iterator[OwonSpm3051]:
    """Per-test PSU (Power Supply Unit) handle; restore 5.0 V after power tests."""
    yield owon_session
    try:
        owon_session.apply(5.0, ilim_a=0.5, settle_s=0.5)
    except (OSError, RuntimeError, TimeoutError):
        logger.exception("failed to restore 5.0 V after test")


@pytest.fixture
def dut(owon_session: OwonSpm3051) -> Iterator[DutCli]:
    logger.info("DUT (Device Under Test) rail ready via OWON %s", owon_session.port)
    try:
        w = open_dut()
    except LookupError as exc:
        pytest.skip(str(exc))
    try:
        w.wait_boot()
        yield w
    finally:
        w.close()


@pytest.fixture
def la() -> LogicAnalyzer:
    try:
        return find_logic_analyzer()
    except LookupError as exc:
        pytest.skip(str(exc))


@pytest.fixture
def stim() -> Iterator[StimCli]:
    try:
        port = find_stim_port()
    except LookupError as exc:
        pytest.skip(str(exc))
    if not port_exists(port):
        pytest.skip(f"stimulator not on {port}")
    s = StimCli(port)
    try:
        s.send("help")
        yield s
    finally:
        s.close()


@pytest.fixture
def power_dut(owon: OwonSpm3051) -> Iterator[DutCli]:
    """DUT (Device Under Test) console for power tests: USB-UART TX/RX/GND or WiFi (no USB VBUS)."""
    try:
        w = open_power_dut()
    except LookupError as exc:
        pytest.skip(str(exc))
    owon.apply(5.0, ilim_a=0.5, settle_s=2.0)
    try:
        w.recover(60)
        yield w
    finally:
        w.close()


@pytest.fixture(autouse=True)
def recover_frozen_dut(request: pytest.FixtureRequest) -> Iterator[None]:
    """After hardware tests: prove alive, else DTR (Data Terminal Ready) pulse, else OWON cut."""
    yield
    if not _hw_test(request):
        return
    w = _open_console()
    if w is None:
        logger.info("recovery skipped: no DUT (Device Under Test) console")
        return
    try:
        try:
            w.prove_alive(5)
            logger.info("DUT (Device Under Test) alive after %s", request.node.nodeid)
            return
        except AssertionError:
            logger.warning(
                "DUT (Device Under Test) frozen after %s; "
                "DTR (Data Terminal Ready) recover",
                request.node.nodeid,
            )
            try:
                w.recover(20)
                w.prove_alive(8)
                logger.info(
                    "DUT (Device Under Test) recovered via DTR (Data Terminal Ready)"
                )
                return
            except (AssertionError, OSError, RuntimeError, TimeoutError) as exc:
                logger.warning("DTR (Data Terminal Ready) recover failed: %s", exc)

        psu: OwonSpm3051 | None = None
        for name in ("owon", "owon_session"):
            if name not in request.fixturenames:
                continue
            try:
                psu = request.getfixturevalue(name)
                break
            except (LookupError, OSError, pytest.FixtureLookupError) as exc:
                logger.info("OWON fixture %s unavailable: %s", name, exc)
                continue
            except pytest.skip.Exception as exc:
                logger.info("OWON fixture %s skipped: %s", name, exc)
                continue
        if psu is None:
            logger.warning(
                "no OWON handle; cannot power-cycle after %s",
                request.node.nodeid,
            )
            return
        logger.warning(
            "power-cycling DUT (Device Under Test) for %s", request.node.nodeid
        )
        psu.power_cycle(volts=5.0, off_s=2.0, boot_s=2.0)
        w.recover(30)
    except (AssertionError, OSError, RuntimeError, TimeoutError):
        logger.exception("recovery failed after %s", request.node.nodeid)
    finally:
        w.close()
