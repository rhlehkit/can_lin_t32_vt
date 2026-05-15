"""Exported CAN/LIN test cases for CANoe/vTESTstudio.

These test cases are intentionally scenario-style. Edit bus_test_config.py for
IDs, payloads, channels, periods, and tolerances.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict

import vector.canoe
import vector.canoe.tfs

THIS_DIR = Path(__file__).resolve().parent
if str(THIS_DIR) not in sys.path:
    sys.path.insert(0, str(THIS_DIR))

from bus_test_config import CONFIG
from bus_test_lib import CanoeComCaplBridge, config_int, frame_from_config, parse_int


_BRIDGE = None


def _bridge() -> CanoeComCaplBridge:
    global _BRIDGE
    if _BRIDGE is None:
        _BRIDGE = CanoeComCaplBridge()
    return _BRIDGE


def _defaults() -> Dict[str, Any]:
    return CONFIG.get("defaults", {})


def _timeout(config: Dict[str, Any]) -> int:
    return config_int(config, "timeout_ms", config_int(_defaults(), "timeout_ms", 1000))


def _test_step(title: str, detail: str) -> None:
    step = getattr(vector.canoe.tfs, "test_step", None)
    if callable(step):
        try:
            step(title, detail)
            return
        except TypeError:
            try:
                step(f"{title}: {detail}")
                return
            except TypeError:
                pass
    print(f"[{title}] {detail}")


def _can_channel() -> int:
    return config_int(CONFIG["can"], "channel", 1)


def _lin_channel() -> int:
    return config_int(CONFIG["lin"], "channel", 1)


def _start_can_periodic_from_config():
    config = CONFIG["can"]["periodic_tx"]
    frame = frame_from_config(config)
    task_id = config_int(config, "task_id")
    period_ms = config_int(config, "period_ms")

    _bridge().start_can_periodic(task_id, _can_channel(), frame, period_ms)
    _test_step("CAN periodic TX start", f"task={task_id}, period={period_ms}ms, {frame.format()}")
    return task_id


def _start_lin_periodic_from_config():
    config = CONFIG["lin"]["periodic_tx"]
    frame = frame_from_config(config)
    task_id = config_int(config, "task_id")
    period_ms = config_int(config, "period_ms")
    send_data = bool(config.get("send_data", False))

    _bridge().start_lin_periodic(task_id, _lin_channel(), frame, period_ms, send_data)
    mode = "frame" if send_data else "header"
    _test_step("LIN periodic TX start", f"task={task_id}, mode={mode}, period={period_ms}ms, {frame.format()}")
    return task_id


@vector.canoe.tfs.export
@vector.canoe.tfs.test_case
def TC_CAN_TxOnce():
    """Transmit one CAN frame through the CAPL bridge."""

    config = CONFIG["can"]["tx_once"]
    frame = frame_from_config(config)
    _bridge().send_can(_can_channel(), frame)
    _test_step("CAN TX", frame.format())


@vector.canoe.tfs.export
@vector.canoe.tfs.test_case
def TC_CAN_RxExpect():
    """Wait for one CAN frame and optionally check its payload."""

    config = CONFIG["can"]["rx_expected"]
    expected = frame_from_config(config)
    check_data = bool(config.get("check_data", True))
    actual = _bridge().wait_can(_can_channel(), expected, _timeout(config), check_data)
    _test_step("CAN RX", actual.format())


@vector.canoe.tfs.export
@vector.canoe.tfs.test_case
def TC_CAN_PeriodicTx():
    """Start a periodic CAN TX task for the configured duration."""

    config = CONFIG["can"]["periodic_tx"]
    duration_ms = config_int(config, "duration_ms")

    bridge = _bridge()
    task_id = _start_can_periodic_from_config()
    try:
        bridge.sleep_ms(duration_ms)
    finally:
        bridge.stop_periodic(task_id)
    _test_step("CAN periodic TX stop", f"task={task_id}, duration={duration_ms}ms")


@vector.canoe.tfs.export
@vector.canoe.tfs.test_case
def TC_CAN_PeriodicTx_Start():
    """Start periodic CAN TX and leave it running for later test cases."""

    task_id = _start_can_periodic_from_config()
    _test_step("CAN periodic TX running", f"task={task_id}")


@vector.canoe.tfs.export
@vector.canoe.tfs.test_case
def TC_CAN_PeriodicTx_Stop():
    """Stop the configured periodic CAN TX task."""

    task_id = config_int(CONFIG["can"]["periodic_tx"], "task_id")
    _bridge().stop_periodic(task_id)
    _test_step("CAN periodic TX stop", f"task={task_id}")


@vector.canoe.tfs.export
@vector.canoe.tfs.test_case
def TC_CAN_PeriodCheck():
    """Measure and verify the period of a received CAN frame."""

    config = CONFIG["can"]["period_check"]
    frame_id = parse_int(config["id"])
    extended = bool(config.get("extended", False))
    expected_ms = config_int(config, "expected_period_ms")
    tolerance_ms = config_int(config, "tolerance_ms", config_int(_defaults(), "period_tolerance_ms", 5))
    sample_count = config_int(config, "sample_count", config_int(_defaults(), "period_sample_count", 20))
    timeout_ms = _timeout(config)

    stats = _bridge().check_can_period(
        _can_channel(),
        frame_id,
        extended,
        expected_ms,
        tolerance_ms,
        sample_count,
        timeout_ms,
    )
    _test_step("CAN period check", stats.format())


@vector.canoe.tfs.export
@vector.canoe.tfs.test_case
def TC_LIN_TxOnce():
    """Transmit or publish one LIN frame through the CAPL bridge."""

    config = CONFIG["lin"]["tx_once"]
    frame = frame_from_config(config)
    _bridge().send_lin(_lin_channel(), frame)
    _test_step("LIN TX", frame.format())


@vector.canoe.tfs.export
@vector.canoe.tfs.test_case
def TC_LIN_RxExpect():
    """Wait for one LIN frame and optionally check its payload."""

    config = CONFIG["lin"]["rx_expected"]
    expected = frame_from_config(config)
    check_data = bool(config.get("check_data", True))
    bridge = _bridge()

    if bool(config.get("request_header_before_wait", False)):
        bridge.request_lin_header(_lin_channel(), expected.frame_id)
        _test_step("LIN header request", f"id=0x{expected.frame_id:X}")

    actual = bridge.wait_lin(_lin_channel(), expected, _timeout(config), check_data)
    _test_step("LIN RX", actual.format())


@vector.canoe.tfs.export
@vector.canoe.tfs.test_case
def TC_LIN_PeriodicTx():
    """Start a periodic LIN header/data task for the configured duration."""

    config = CONFIG["lin"]["periodic_tx"]
    duration_ms = config_int(config, "duration_ms")

    bridge = _bridge()
    task_id = _start_lin_periodic_from_config()
    try:
        bridge.sleep_ms(duration_ms)
    finally:
        bridge.stop_periodic(task_id)
    _test_step("LIN periodic TX stop", f"task={task_id}, duration={duration_ms}ms")


@vector.canoe.tfs.export
@vector.canoe.tfs.test_case
def TC_LIN_PeriodicTx_Start():
    """Start periodic LIN header/data TX and leave it running for later test cases."""

    task_id = _start_lin_periodic_from_config()
    _test_step("LIN periodic TX running", f"task={task_id}")


@vector.canoe.tfs.export
@vector.canoe.tfs.test_case
def TC_LIN_PeriodicTx_Stop():
    """Stop the configured periodic LIN TX task."""

    task_id = config_int(CONFIG["lin"]["periodic_tx"], "task_id")
    _bridge().stop_periodic(task_id)
    _test_step("LIN periodic TX stop", f"task={task_id}")


@vector.canoe.tfs.export
@vector.canoe.tfs.test_case
def TC_LIN_PeriodCheck():
    """Measure and verify the period of a received LIN frame."""

    config = CONFIG["lin"]["period_check"]
    frame_id = parse_int(config["id"])
    expected_ms = config_int(config, "expected_period_ms")
    tolerance_ms = config_int(config, "tolerance_ms", config_int(_defaults(), "period_tolerance_ms", 5))
    sample_count = config_int(config, "sample_count", config_int(_defaults(), "period_sample_count", 20))
    timeout_ms = _timeout(config)

    stats = _bridge().check_lin_period(
        _lin_channel(),
        frame_id,
        expected_ms,
        tolerance_ms,
        sample_count,
        timeout_ms,
    )
    _test_step("LIN period check", stats.format())
