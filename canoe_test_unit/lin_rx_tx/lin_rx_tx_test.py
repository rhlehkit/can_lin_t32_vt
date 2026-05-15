"""CANoe/vTESTstudio Python Test Unit sample for LIN TX/RX.

This test is intended to run inside the CANoe/vTESTstudio Test Unit runtime.
CANoe should own the VN16xx LIN channel and VT System configuration.

The Python test talks to CANoe through system variables in namespace
``LinTest``. A CANoe simulation node, CAPL helper, or existing test setup
should translate those variables to real LIN bus actions.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Optional

import vector.canoe
import vector.canoe.tfs


SYSVAR_NAMESPACE = "LinTest"

TX_FRAME_ID = 0x12
TX_FRAME_DATA = (0x10, 0x22, 0x33, 0x44)

EXPECTED_RX_FRAME_ID = 0x22
EXPECTED_RX_FRAME_DATA = (0x55, 0xAA, 0x12, 0x34)

TIMEOUT_S = 2.0
POLL_S = 0.01


@dataclass(frozen=True)
class LinFrame:
    frame_id: int
    data: tuple[int, ...]

    @property
    def dlc(self) -> int:
        return len(self.data)

    def format(self) -> str:
        payload = " ".join(f"{byte:02X}" for byte in self.data)
        return f"id=0x{self.frame_id:02X}, dlc={self.dlc}, data=[{payload}]"


class SystemVariables:
    """Small CANoe system-variable adapter.

    The COM fallback is useful for a first bring-up. In a production CANoe
    Python Test Unit, replace this adapter with the generated Vector Python
    type-library access if your CANoe version provides one for system vars.
    """

    def __init__(self, namespace: str) -> None:
        self.namespace = namespace
        self._app = None

    def read(self, name: str) -> int:
        return self._variable(name).Value

    def write(self, name: str, value: int) -> None:
        self._variable(name).Value = value

    def _variable(self, name: str):
        return self._canoe_app().System.Namespaces(self.namespace).Variables(name)

    def _canoe_app(self):
        if self._app is not None:
            return self._app

        try:
            import pythoncom
            import win32com.client
        except ImportError as exc:
            raise RuntimeError(
                "pywin32가 현재 CANoe Python 런타임에 없습니다. "
                "임시로는 pywin32를 설치하거나, 이 SystemVariables 클래스를 "
                "CANoe가 생성한 vector.canoe type-library 방식으로 교체하세요."
            ) from exc

        pythoncom.CoInitialize()
        try:
            self._app = win32com.client.GetActiveObject("CANoe.Application")
        except Exception:
            self._app = win32com.client.Dispatch("CANoe.Application")
        return self._app


SYS = SystemVariables(SYSVAR_NAMESPACE)


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


def _wait_until(description: str, predicate: Callable[[], bool], timeout_s: float) -> None:
    deadline = time.monotonic() + timeout_s
    last_error: Optional[Exception] = None

    while time.monotonic() < deadline:
        try:
            if predicate():
                return
        except Exception as exc:
            last_error = exc
        time.sleep(POLL_S)

    if last_error is not None:
        raise AssertionError(f"{description} timed out. Last error: {last_error}") from last_error
    raise AssertionError(f"{description} timed out.")


def _counter(name: str) -> int:
    return int(SYS.read(name))


def _read_rx_frame() -> LinFrame:
    frame_id = int(SYS.read("RxId"))
    dlc = int(SYS.read("RxDlc"))
    data = tuple(int(SYS.read(f"RxData{index}")) & 0xFF for index in range(dlc))
    return LinFrame(frame_id=frame_id, data=data)


def _write_tx_frame(frame: LinFrame) -> None:
    if frame.dlc > 8:
        raise ValueError("LIN classic frame payload must be 8 bytes or fewer.")

    SYS.write("TxId", frame.frame_id)
    SYS.write("TxDlc", frame.dlc)
    for index in range(8):
        value = frame.data[index] if index < frame.dlc else 0
        SYS.write(f"TxData{index}", value)


def _request_tx(frame: LinFrame) -> None:
    before = _counter("TxRequestCounter")
    _write_tx_frame(frame)
    SYS.write("TxRequestCounter", before + 1)

    def tx_done() -> bool:
        done = _counter("TxDoneCounter") >= before + 1
        status_ok = int(SYS.read("TxStatus")) == 0
        return done and status_ok

    _wait_until(f"TX completion for {frame.format()}", tx_done, TIMEOUT_S)


def _wait_for_rx_after(counter_before: int, expected: LinFrame) -> LinFrame:
    received: LinFrame | None = None

    def rx_matches() -> bool:
        nonlocal received
        if _counter("RxCounter") <= counter_before:
            return False

        received = _read_rx_frame()
        return received.frame_id == expected.frame_id and received.data == expected.data

    _wait_until(f"RX expected frame {expected.format()}", rx_matches, TIMEOUT_S)
    assert received is not None
    return received


@vector.canoe.tfs.export
@vector.canoe.tfs.test_case
def LinTxRx_SmokeTest():
    """Send one LIN frame and verify one expected LIN frame was observed."""

    tx_frame = LinFrame(TX_FRAME_ID, TX_FRAME_DATA)
    expected_rx = LinFrame(EXPECTED_RX_FRAME_ID, EXPECTED_RX_FRAME_DATA)

    _test_step("Prepare", f"TX {tx_frame.format()}, expect RX {expected_rx.format()}")
    rx_counter_before = _counter("RxCounter")

    _request_tx(tx_frame)
    _test_step("LIN TX", f"CANoe bridge accepted TX {tx_frame.format()}")

    received = _wait_for_rx_after(rx_counter_before, expected_rx)
    _test_step("LIN RX", f"Observed expected frame {received.format()}")
