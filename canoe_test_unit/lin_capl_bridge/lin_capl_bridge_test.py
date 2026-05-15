"""Python Test Unit sample that calls a CAPL LIN bridge.

This avoids using CANoe system variables as the frame transport. CAPL owns the
LIN bus, RX buffering, and timing-sensitive logic. Python only calls exported
CAPL functions and performs test-level assertions.

The CAPL function names expected by this file are documented in README.md and
sketched in lin_bridge.can.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional, Sequence

import vector.canoe
import vector.canoe.tfs


TIMEOUT_MS = 1000

TX_FRAMES = (
    (0x12, (0x10, 0x22, 0x33, 0x44)),
    (0x13, (0x20, 0x22, 0x33, 0x45)),
)

EXPECTED_RX_FRAMES = (
    (0x22, (0x55, 0xAA, 0x12, 0x34)),
    (0x23, (0x55, 0xAA, 0x13, 0x35)),
)


@dataclass(frozen=True)
class LinFrame:
    frame_id: int
    data: tuple[int, ...]

    @classmethod
    def from_pair(cls, item: tuple[int, Sequence[int]]) -> "LinFrame":
        frame_id, data = item
        return cls(frame_id=frame_id, data=tuple(int(byte) & 0xFF for byte in data))

    @property
    def dlc(self) -> int:
        return len(self.data)

    def padded_data(self) -> tuple[int, int, int, int, int, int, int, int]:
        padded = list(self.data[:8])
        padded.extend([0] * (8 - len(padded)))
        return tuple(padded)  # type: ignore[return-value]

    def format(self) -> str:
        payload = " ".join(f"{byte:02X}" for byte in self.data)
        return f"id=0x{self.frame_id:02X}, dlc={self.dlc}, data=[{payload}]"


class CaplBridge:
    """Calls exported CAPL functions through CANoe COM.

    If your Vector Python Test Unit type libraries expose CAPL functions
    directly, replace this class with those generated calls. The test case
    above it stays the same.
    """

    def __init__(self) -> None:
        self._app = None
        self._functions = {}

    def reset(self) -> None:
        self._call("LinBridge_Reset")

    def send_frame(self, frame: LinFrame) -> None:
        if frame.dlc > 8:
            raise ValueError("LIN classic frame payload must be 8 bytes or fewer.")
        status = self._call("LinBridge_SendFrame", frame.frame_id, frame.dlc, *frame.padded_data())
        if int(status or 0) != 0:
            raise AssertionError(f"CAPL LinBridge_SendFrame failed with status={status}")

    def request_slave_response(self, frame_id: int) -> None:
        status = self._call("LinBridge_RequestSlaveResponse", frame_id)
        if int(status or 0) != 0:
            raise AssertionError(f"CAPL LinBridge_RequestSlaveResponse failed with status={status}")

    def wait_for_frame(self, frame_id: int, timeout_ms: int) -> LinFrame:
        status = self._call("LinBridge_WaitForFrame", frame_id, timeout_ms)
        if int(status or 0) == 0:
            raise AssertionError(f"Timed out waiting for LIN frame 0x{frame_id:02X}")

        dlc = int(self._call("LinBridge_GetLastRxDlc") or 0)
        rx_id = int(self._call("LinBridge_GetLastRxId") or 0)
        data = tuple(int(self._call("LinBridge_GetLastRxByte", index) or 0) & 0xFF for index in range(dlc))
        return LinFrame(rx_id, data)

    def _call(self, name: str, *args):
        function = self._function(name)
        return function.Call(*args)

    def _function(self, name: str):
        function = self._functions.get(name)
        if function is None:
            function = self._canoe_app().CAPL.GetFunction(name)
            self._functions[name] = function
        return function

    def _canoe_app(self):
        if self._app is not None:
            return self._app

        try:
            import pythoncom
            import win32com.client
        except ImportError as exc:
            raise RuntimeError(
                "pywin32 is not available. Install pywin32 in the Python runtime "
                "or replace CaplBridge with Vector's generated Python type-library calls."
            ) from exc

        pythoncom.CoInitialize()
        try:
            self._app = win32com.client.GetActiveObject("CANoe.Application")
        except Exception:
            self._app = win32com.client.Dispatch("CANoe.Application")
        return self._app


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


def _assert_frame_equal(actual: LinFrame, expected: LinFrame) -> None:
    if actual.frame_id != expected.frame_id or actual.data != expected.data:
        raise AssertionError(f"Expected {expected.format()}, got {actual.format()}")


BRIDGE: Optional[CaplBridge] = None


def _bridge() -> CaplBridge:
    global BRIDGE
    if BRIDGE is None:
        BRIDGE = CaplBridge()
    return BRIDGE


@vector.canoe.tfs.export
@vector.canoe.tfs.test_case
def LinTxRx_CaplBridgeTest():
    """Send LIN frames and verify RX frames through a CAPL bridge."""

    bridge = _bridge()
    bridge.reset()

    tx_frames = tuple(LinFrame.from_pair(item) for item in TX_FRAMES)
    expected_rx_frames = tuple(LinFrame.from_pair(item) for item in EXPECTED_RX_FRAMES)

    for frame in tx_frames:
        bridge.send_frame(frame)
        _test_step("LIN TX", frame.format())
        time.sleep(0.02)

    for expected in expected_rx_frames:
        bridge.request_slave_response(expected.frame_id)
        actual = bridge.wait_for_frame(expected.frame_id, TIMEOUT_MS)
        _assert_frame_equal(actual, expected)
        _test_step("LIN RX", actual.format())

