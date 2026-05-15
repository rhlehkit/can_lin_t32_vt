"""Small examples showing how to write your own CAN/LIN test cases.

Copy one of these functions and edit IDs/data in bus_test_config.py first.
For project-specific behavior, keep CAN/LIN bus access inside the CAPL bridge
and keep this Python file focused on scenario steps and assertions.
"""

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


_BRIDGE = None


def bridge() -> CanoeComCaplBridge:
    global _BRIDGE
    if _BRIDGE is None:
        _BRIDGE = CanoeComCaplBridge()
    return _BRIDGE


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


@vector.canoe.tfs.export
@vector.canoe.tfs.test_case
def TC_EXAMPLE_CAN_SendAndExpectResponse():
    """Example: send one CAN message and wait for one expected CAN response."""

    can_config = CONFIG["can"]
    channel = config_int(can_config, "channel", 1)
    tx_frame = frame_from_config(can_config["tx_once"])
    expected_rx = frame_from_config(can_config["rx_expected"])
    timeout_ms = config_int(can_config["rx_expected"], "timeout_ms", 1000)

    bridge().send_can(channel, tx_frame)
    step("CAN TX", tx_frame.format())

    actual_rx = bridge().wait_can(channel, expected_rx, timeout_ms, check_data=True)
    step("CAN RX", actual_rx.format())


@vector.canoe.tfs.export
@vector.canoe.tfs.test_case
def TC_EXAMPLE_LIN_RequestAndExpectResponse():
    """Example: request a LIN response header and wait for the expected payload."""

    lin_config = CONFIG["lin"]
    channel = config_int(lin_config, "channel", 1)
    expected_rx = frame_from_config(lin_config["rx_expected"])
    timeout_ms = config_int(lin_config["rx_expected"], "timeout_ms", 1000)

    bridge().request_lin_header(channel, expected_rx.frame_id)
    step("LIN header", f"id=0x{expected_rx.frame_id:X}")

    actual_rx = bridge().wait_lin(channel, expected_rx, timeout_ms, check_data=True)
    step("LIN RX", actual_rx.format())


@vector.canoe.tfs.export
@vector.canoe.tfs.test_case
def TC_EXAMPLE_CAN_PeriodicWhileCheckingResponse():
    """Example: keep periodic CAN TX running while another CAN RX is checked."""

    can_config = CONFIG["can"]
    channel = config_int(can_config, "channel", 1)
    periodic_config = can_config["periodic_tx"]
    rx_config = can_config["rx_expected"]

    task_id = config_int(periodic_config, "task_id")
    period_ms = config_int(periodic_config, "period_ms")
    periodic_frame = frame_from_config(periodic_config)
    expected_rx = frame_from_config(rx_config)
    timeout_ms = config_int(rx_config, "timeout_ms", 1000)

    bridge().start_can_periodic(task_id, channel, periodic_frame, period_ms)
    step("CAN periodic start", f"task={task_id}, period={period_ms}ms, {periodic_frame.format()}")

    try:
        actual_rx = bridge().wait_can(channel, expected_rx, timeout_ms, check_data=True)
        step("CAN RX while periodic TX", actual_rx.format())
    finally:
        bridge().stop_periodic(task_id)
        step("CAN periodic stop", f"task={task_id}")

