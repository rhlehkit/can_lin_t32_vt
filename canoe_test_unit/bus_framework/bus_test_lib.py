"""Reusable helpers for CANoe/vTESTstudio Python bus test units.

The Python layer intentionally does not touch VN hardware directly. It calls a
CAPL bridge that owns CAN/LIN bus access inside CANoe/vTESTstudio.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, Sequence, Tuple


MAX_CLASSIC_PAYLOAD = 8


class BridgeError(AssertionError):
    """Raised when the CAPL bridge reports a test failure or infrastructure error."""


@dataclass(frozen=True)
class BusFrame:
    frame_id: int
    data: Tuple[int, ...]
    extended: bool = False

    @property
    def dlc(self) -> int:
        return len(self.data)

    def padded_data(self) -> Tuple[int, int, int, int, int, int, int, int]:
        if self.dlc > MAX_CLASSIC_PAYLOAD:
            raise ValueError("Only classic CAN/LIN payloads up to 8 bytes are supported by this template.")
        padded = list(self.data)
        padded.extend([0] * (MAX_CLASSIC_PAYLOAD - len(padded)))
        return tuple(padded)  # type: ignore[return-value]

    def format(self) -> str:
        payload = " ".join(f"{byte:02X}" for byte in self.data)
        ext = ", ext" if self.extended else ""
        return f"id=0x{self.frame_id:X}{ext}, dlc={self.dlc}, data=[{payload}]"


@dataclass(frozen=True)
class PeriodStats:
    samples: int
    average_us: int
    minimum_us: int
    maximum_us: int

    def format(self) -> str:
        return (
            f"samples={self.samples}, "
            f"avg={self.average_us / 1000.0:.3f}ms, "
            f"min={self.minimum_us / 1000.0:.3f}ms, "
            f"max={self.maximum_us / 1000.0:.3f}ms"
        )


def parse_int(value: Any) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return int(value, 0)
    raise TypeError(f"Expected int or string integer, got {type(value).__name__}: {value!r}")


def parse_data(values: Sequence[Any]) -> Tuple[int, ...]:
    data = tuple(parse_int(value) & 0xFF for value in values)
    if len(data) > MAX_CLASSIC_PAYLOAD:
        raise ValueError(f"Payload is too long for this template: {len(data)} bytes")
    return data


def frame_from_config(config: Dict[str, Any]) -> BusFrame:
    return BusFrame(
        frame_id=parse_int(config["id"]),
        data=parse_data(config.get("data", [])),
        extended=bool(config.get("extended", False)),
    )


def config_int(config: Dict[str, Any], name: str, default: Optional[int] = None) -> int:
    if name not in config:
        if default is None:
            raise KeyError(name)
        return default
    return parse_int(config[name])


class CanoeComCaplBridge:
    """Thin adapter around CANoe.Application.CAPL.GetFunction(...).Call(...).

    This is good for bring-up because it works without knowing the generated
    Python type-library module names. For long-term use, you can replace this
    adapter with Vector-generated Python type-library calls while preserving
    the public methods below.
    """

    def __init__(self) -> None:
        self._app = None
        self._functions: Dict[str, Any] = {}

    def reset(self) -> None:
        self._status_call("BusBridge_Reset")

    def send_can(self, channel: int, frame: BusFrame) -> None:
        self._status_call(
            "BusBridge_SendCan",
            channel,
            frame.frame_id,
            int(frame.extended),
            frame.dlc,
            *frame.padded_data(),
        )

    def wait_can(self, channel: int, expected: BusFrame, timeout_ms: int, check_data: bool = True) -> BusFrame:
        self._status_call("BusBridge_WaitCan", channel, expected.frame_id, int(expected.extended), timeout_ms)
        actual = self._read_last_frame()
        self._assert_expected("CAN RX", actual, expected, check_data)
        return actual

    def start_can_periodic(self, task_id: int, channel: int, frame: BusFrame, period_ms: int) -> None:
        self._status_call(
            "BusBridge_StartCanPeriodic",
            task_id,
            channel,
            frame.frame_id,
            int(frame.extended),
            period_ms,
            frame.dlc,
            *frame.padded_data(),
        )

    def check_can_period(
        self,
        channel: int,
        frame_id: int,
        extended: bool,
        expected_period_ms: int,
        tolerance_ms: int,
        sample_count: int,
        timeout_ms: int,
    ) -> PeriodStats:
        self._status_call(
            "BusBridge_CheckCanPeriod",
            channel,
            frame_id,
            int(extended),
            expected_period_ms,
            tolerance_ms,
            sample_count,
            timeout_ms,
        )
        return self._read_period_stats()

    def send_lin(self, channel: int, frame: BusFrame) -> None:
        self._status_call("BusBridge_SendLin", channel, frame.frame_id, frame.dlc, *frame.padded_data())

    def request_lin_header(self, channel: int, frame_id: int) -> None:
        self._status_call("BusBridge_RequestLinHeader", channel, frame_id)

    def wait_lin(self, channel: int, expected: BusFrame, timeout_ms: int, check_data: bool = True) -> BusFrame:
        self._status_call("BusBridge_WaitLin", channel, expected.frame_id, timeout_ms)
        actual = self._read_last_frame()
        self._assert_expected("LIN RX", actual, expected, check_data)
        return actual

    def start_lin_periodic(
        self,
        task_id: int,
        channel: int,
        frame: BusFrame,
        period_ms: int,
        send_data: bool,
    ) -> None:
        self._status_call(
            "BusBridge_StartLinPeriodic",
            task_id,
            channel,
            frame.frame_id,
            int(send_data),
            period_ms,
            frame.dlc,
            *frame.padded_data(),
        )

    def check_lin_period(
        self,
        channel: int,
        frame_id: int,
        expected_period_ms: int,
        tolerance_ms: int,
        sample_count: int,
        timeout_ms: int,
    ) -> PeriodStats:
        self._status_call(
            "BusBridge_CheckLinPeriod",
            channel,
            frame_id,
            expected_period_ms,
            tolerance_ms,
            sample_count,
            timeout_ms,
        )
        return self._read_period_stats()

    def stop_periodic(self, task_id: int) -> None:
        self._status_call("BusBridge_StopPeriodic", task_id)

    def sleep_ms(self, duration_ms: int) -> None:
        time.sleep(duration_ms / 1000.0)

    def _read_last_frame(self) -> BusFrame:
        dlc = int(self._call("BusBridge_GetLastRxDlc") or 0)
        frame_id = int(self._call("BusBridge_GetLastRxId") or 0)
        extended = bool(int(self._call("BusBridge_GetLastRxExtended") or 0))
        data = tuple(int(self._call("BusBridge_GetLastRxByte", index) or 0) & 0xFF for index in range(dlc))
        return BusFrame(frame_id=frame_id, data=data, extended=extended)

    def _read_period_stats(self) -> PeriodStats:
        return PeriodStats(
            samples=int(self._call("BusBridge_GetPeriodSampleCount") or 0),
            average_us=int(self._call("BusBridge_GetPeriodAverageUs") or 0),
            minimum_us=int(self._call("BusBridge_GetPeriodMinimumUs") or 0),
            maximum_us=int(self._call("BusBridge_GetPeriodMaximumUs") or 0),
        )

    def _assert_expected(self, label: str, actual: BusFrame, expected: BusFrame, check_data: bool) -> None:
        id_ok = actual.frame_id == expected.frame_id and actual.extended == expected.extended
        data_ok = (not check_data) or actual.data == expected.data
        if not id_ok or not data_ok:
            raise BridgeError(f"{label} mismatch. expected {expected.format()}, got {actual.format()}")

    def _status_call(self, name: str, *args: Any) -> None:
        status = self._call(name, *args)
        status_int = int(status or 0)
        if status_int != 0:
            detail = self._last_error()
            raise BridgeError(f"{name} failed with status={status_int}. {detail}")

    def _last_error(self) -> str:
        try:
            code = int(self._call("BusBridge_GetLastError") or 0)
        except Exception:
            return "No bridge error detail available."
        return f"BusBridge_GetLastError={code}"

    def _call(self, name: str, *args: Any) -> Any:
        return self._function(name).Call(*args)

    def _function(self, name: str) -> Any:
        function = self._functions.get(name)
        if function is None:
            function = self._canoe_app().CAPL.GetFunction(name)
            self._functions[name] = function
        return function

    def _canoe_app(self) -> Any:
        if self._app is not None:
            return self._app

        try:
            import pythoncom
            import win32com.client
        except ImportError as exc:
            raise RuntimeError(
                "pywin32 is not available in this Python runtime. Install pywin32 "
                "or replace CanoeComCaplBridge with Vector-generated Python "
                "type-library calls."
            ) from exc

        pythoncom.CoInitialize()
        try:
            self._app = win32com.client.GetActiveObject("CANoe.Application")
        except Exception:
            self._app = win32com.client.Dispatch("CANoe.Application")
        return self._app

