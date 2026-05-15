"""TRACE32-aware example test cases for CANoe/vTESTstudio."""

from __future__ import annotations

import sys
from pathlib import Path

import vector.canoe
import vector.canoe.tfs

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from bus_test_config import CONFIG
from bus_test_lib import CanoeComCaplBridge, config_int, frame_from_config
from trace32_client import Trace32Client
from trace32_config import TRACE32_CONFIG


_BUS_BRIDGE = None
_TRACE32 = None


def bus_bridge() -> CanoeComCaplBridge:
    global _BUS_BRIDGE
    if _BUS_BRIDGE is None:
        _BUS_BRIDGE = CanoeComCaplBridge()
    return _BUS_BRIDGE


def trace32() -> Trace32Client:
    global _TRACE32
    if _TRACE32 is None:
        _TRACE32 = Trace32Client(TRACE32_CONFIG)
    return _TRACE32


def step(title: str, detail: str) -> None:
    test_step = getattr(vector.canoe.tfs, "test_step", None)
    if callable(test_step):
        try:
            test_step(title, detail)
            return
        except TypeError:
            test_step(f"{title}: {detail}")
            return
    print(f"[{title}] {detail}")


def report_debug_values(title: str, values) -> None:
    if not values:
        step(title, "No TRACE32 variables/registers configured.")
        return
    for value in values:
        step(title, value.format())


@vector.canoe.tfs.export
@vector.canoe.tfs.test_case
def TC_TRACE32_ConnectAndSnapshot():
    """Connect to TRACE32 and report configured variables/registers."""

    trace32().connect()
    step("TRACE32 connect", "Connected to TRACE32 Remote API.")
    report_debug_values("TRACE32 snapshot", trace32().snapshot())


@vector.canoe.tfs.export
@vector.canoe.tfs.test_case
def TC_TRACE32_AssertVariables():
    """Read configured TRACE32 variables and compare against expected values."""

    checks = TRACE32_CONFIG.get("assert_variables", [])
    values = trace32().assert_variables(checks)
    report_debug_values("TRACE32 assert", values)


@vector.canoe.tfs.export
@vector.canoe.tfs.test_case
def TC_TRACE32_WriteVariables():
    """Write configured TRACE32 variables and optionally verify the written values."""

    writes = TRACE32_CONFIG.get("write_variables", [])
    values = trace32().write_variables(writes)
    report_debug_values("TRACE32 write", values)


@vector.canoe.tfs.export
@vector.canoe.tfs.test_case
def TC_CAN_TxThenTrace32Snapshot():
    """Send one CAN frame, then capture TRACE32 variables/registers."""

    can_config = CONFIG["can"]
    channel = config_int(can_config, "channel", 1)
    tx_frame = frame_from_config(can_config["tx_once"])

    bus_bridge().send_can(channel, tx_frame)
    step("CAN TX", tx_frame.format())

    report_debug_values("TRACE32 after CAN TX", trace32().snapshot())


@vector.canoe.tfs.export
@vector.canoe.tfs.test_case
def TC_CAN_RxThenTrace32Snapshot():
    """Wait for a CAN response, then capture TRACE32 variables/registers."""

    can_config = CONFIG["can"]
    rx_config = can_config["rx_expected"]
    channel = config_int(can_config, "channel", 1)
    expected_rx = frame_from_config(rx_config)
    timeout_ms = config_int(rx_config, "timeout_ms", 1000)

    actual_rx = bus_bridge().wait_can(channel, expected_rx, timeout_ms, check_data=bool(rx_config.get("check_data", True)))
    step("CAN RX", actual_rx.format())

    report_debug_values("TRACE32 after CAN RX", trace32().snapshot())


@vector.canoe.tfs.export
@vector.canoe.tfs.test_case
def TC_TRACE32_WriteThenCanTx():
    """Write TRACE32 variables first, then transmit one CAN frame."""

    writes = TRACE32_CONFIG.get("write_variables", [])
    report_debug_values("TRACE32 write", trace32().write_variables(writes))

    can_config = CONFIG["can"]
    channel = config_int(can_config, "channel", 1)
    tx_frame = frame_from_config(can_config["tx_once"])
    bus_bridge().send_can(channel, tx_frame)
    step("CAN TX after TRACE32 write", tx_frame.format())


@vector.canoe.tfs.export
@vector.canoe.tfs.test_case
def TC_LIN_RxThenTrace32Snapshot():
    """Request/wait for LIN response, then capture TRACE32 variables/registers."""

    lin_config = CONFIG["lin"]
    rx_config = lin_config["rx_expected"]
    channel = config_int(lin_config, "channel", 1)
    expected_rx = frame_from_config(rx_config)
    timeout_ms = config_int(rx_config, "timeout_ms", 1000)

    if bool(rx_config.get("request_header_before_wait", False)):
        bus_bridge().request_lin_header(channel, expected_rx.frame_id)
        step("LIN header", f"id=0x{expected_rx.frame_id:X}")

    actual_rx = bus_bridge().wait_lin(channel, expected_rx, timeout_ms, check_data=bool(rx_config.get("check_data", True)))
    step("LIN RX", actual_rx.format())

    report_debug_values("TRACE32 after LIN RX", trace32().snapshot())
