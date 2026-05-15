from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

from . import constants as c
from .vxlapi import VectorXLApi, XLevent


@dataclass(frozen=True)
class VectorLinConfig:
    app_name: str = "PythonLIN"
    app_channel: int = 0
    baudrate: int = 19200
    lin_version: str = "2.1"
    channel_index: Optional[int] = None
    channel_mask: Optional[int] = None
    dll_path: Optional[str] = None
    rx_queue_size: int = 256
    require_init_access: bool = True


@dataclass(frozen=True)
class LinEvent:
    tag: int
    tag_name: str
    timestamp_ns: int
    channel_index: int
    lin_id: Optional[int] = None
    dlc: Optional[int] = None
    data: tuple[int, ...] = ()
    crc: Optional[int] = None
    flags: Optional[int] = None
    direction: Optional[str] = None
    description: str = ""


class VectorLinChannel:
    """High-level LIN channel helper around VectorXLApi.

    The object opens the driver and port, lets callers configure master/slave
    behavior, then activates the channel when ready.
    """

    def __init__(self, config: VectorLinConfig) -> None:
        self.config = config
        self.api = VectorXLApi(config.dll_path)
        self.port_handle: Optional[int] = None
        self.access_mask: Optional[int] = None
        self.permission_mask: Optional[int] = None
        self.activated = False
        self.driver_open = False
        self.lin_version_value = _lin_version_value(config.lin_version)

    def __enter__(self) -> "VectorLinChannel":
        try:
            self.open()
            return self
        except Exception:
            self.close()
            raise

    def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[no-untyped-def]
        self.close()

    def open(self) -> None:
        self.api.open_driver()
        self.driver_open = True
        self.access_mask = self._resolve_access_mask()
        self.port_handle, self.permission_mask = self.api.open_port(
            self.config.app_name,
            self.access_mask,
            self.config.rx_queue_size,
        )
        if self.config.require_init_access and (self.permission_mask & self.access_mask) != self.access_mask:
            raise RuntimeError(
                "This process did not get init access to the LIN channel. "
                "Close CANoe/CANalyzer or another app using the channel, or set require_init_access=False."
            )

    def close(self) -> None:
        try:
            if self.activated and self.port_handle is not None and self.access_mask is not None:
                self.api.deactivate_channel(self.port_handle, self.access_mask)
        finally:
            self.activated = False
            try:
                if self.port_handle is not None:
                    self.api.close_port(self.port_handle)
            finally:
                self.port_handle = None
                if self.driver_open:
                    self.api.close_driver()
                    self.driver_open = False

    def configure_master(
        self,
        default_dlc: int = 8,
        dlc_by_id: Optional[dict[int, int]] = None,
        checksum: str = "auto",
        checksum_by_id: Optional[dict[int, str]] = None,
    ) -> None:
        self._require_open()
        self.api.lin_set_channel_params(
            self.port_handle,
            self.access_mask,
            c.XL_LIN_MASTER,
            self.config.baudrate,
            self.lin_version_value,
        )
        self.api.lin_set_dlc(self.port_handle, self.access_mask, _make_dlc_map(default_dlc, dlc_by_id))
        self.api.lin_set_checksum(
            self.port_handle,
            self.access_mask,
            _make_checksum_map(self.lin_version_value, checksum, checksum_by_id),
        )

    def configure_slave(
        self,
        default_dlc: int = c.XL_LIN_UNDEFINED_DLC,
        dlc_by_id: Optional[dict[int, int]] = None,
    ) -> None:
        self._require_open()
        self.api.lin_set_channel_params(
            self.port_handle,
            self.access_mask,
            c.XL_LIN_SLAVE,
            self.config.baudrate,
            self.lin_version_value,
        )
        self.api.lin_set_dlc(self.port_handle, self.access_mask, _make_dlc_map(default_dlc, dlc_by_id))

    def set_slave_response(
        self,
        lin_id: int,
        data: list[int] | tuple[int, ...],
        dlc: Optional[int] = None,
        checksum: str = "auto",
    ) -> None:
        self._require_open()
        _validate_lin_id(lin_id)
        payload = list(data)
        selected_dlc = len(payload) if dlc is None else dlc
        _validate_dlc(selected_dlc)
        checksum_value = _slave_checksum_value(self.lin_version_value, lin_id, checksum)
        self.api.lin_set_slave(
            self.port_handle,
            self.access_mask,
            lin_id,
            payload,
            selected_dlc,
            checksum_value,
        )

    def activate(self, reset_clock: bool = True, flush_rx_queue: bool = True) -> None:
        self._require_open()
        if flush_rx_queue:
            self.api.flush_receive_queue(self.port_handle)
        self.api.activate_channel(self.port_handle, self.access_mask, reset_clock=reset_clock)
        self.activated = True

    def send_request(self, lin_id: int) -> None:
        self._require_open()
        _validate_lin_id(lin_id)
        self.api.lin_send_request(self.port_handle, self.access_mask, lin_id, flags=0)

    def wakeup(self) -> None:
        self._require_open()
        self.api.lin_wakeup(self.port_handle, self.access_mask)

    def receive(self, timeout_s: float = 0.0, max_events: int = 1) -> list[LinEvent]:
        self._require_open()
        deadline = time.monotonic() + max(timeout_s, 0.0)
        events: list[LinEvent] = []

        while len(events) < max_events:
            event = self.api.receive_one(self.port_handle)
            if event is not None:
                events.append(_lin_event_from_xl_event(event, self.api.event_string(event)))
                continue

            if timeout_s <= 0.0 or time.monotonic() >= deadline:
                break
            time.sleep(0.001)

        return events

    def _resolve_access_mask(self) -> int:
        if self.config.channel_mask is not None:
            return self.config.channel_mask
        if self.config.channel_index is not None:
            if self.config.channel_index < 0 or self.config.channel_index > 63:
                raise ValueError("channel_index must be in range 0..63")
            return 1 << self.config.channel_index
        return self.api.get_application_channel_mask(self.config.app_name, self.config.app_channel)

    def _require_open(self) -> None:
        if self.port_handle is None or self.access_mask is None:
            raise RuntimeError("Vector LIN channel is not open")


def format_event(event: LinEvent) -> str:
    if event.tag == c.XL_LIN_MSG:
        data = " ".join(f"{byte:02X}" for byte in event.data)
        return (
            f"{event.timestamp_ns:>12} ns CH{event.channel_index} {event.direction or '?':>2} "
            f"ID=0x{event.lin_id:02X} DLC={event.dlc} DATA=[{data}] CRC=0x{event.crc:02X} "
            f"FLAGS=0x{event.flags:04X}"
        )
    if event.lin_id is not None:
        return f"{event.timestamp_ns:>12} ns CH{event.channel_index} {event.tag_name} ID=0x{event.lin_id:02X}"
    if event.description:
        return f"{event.timestamp_ns:>12} ns CH{event.channel_index} {event.tag_name} {event.description}"
    return f"{event.timestamp_ns:>12} ns CH{event.channel_index} {event.tag_name}"


def _lin_event_from_xl_event(event: XLevent, fallback_description: str = "") -> LinEvent:
    tag_name = c.EVENT_NAMES.get(event.tag, f"XL_EVENT_{event.tag}")

    if event.tag in (c.XL_LIN_MSG, c.XL_LIN_ERRMSG):
        lin_msg = event.tagData.linMsgApi.linMsg
        dlc = min(int(lin_msg.dlc), 8)
        flags = int(lin_msg.flags)
        direction = "TX" if flags & c.XL_LIN_MSGFLAG_TX else "RX"
        if event.tag == c.XL_LIN_ERRMSG:
            direction = "ERR"
        return LinEvent(
            tag=event.tag,
            tag_name=tag_name,
            timestamp_ns=int(event.timeStamp),
            channel_index=int(event.chanIndex),
            lin_id=int(lin_msg.id),
            dlc=int(lin_msg.dlc),
            data=tuple(int(lin_msg.data[index]) for index in range(dlc)),
            crc=int(lin_msg.crc),
            flags=flags,
            direction=direction,
            description=fallback_description,
        )

    if event.tag in (c.XL_LIN_NOANS, c.XL_LIN_SYNCERR):
        no_ans = event.tagData.linMsgApi.linNoAns
        return LinEvent(
            tag=event.tag,
            tag_name=tag_name,
            timestamp_ns=int(event.timeStamp),
            channel_index=int(event.chanIndex),
            lin_id=int(no_ans.id),
            description=fallback_description,
        )

    if event.tag == c.XL_LIN_CRCINFO:
        crc_info = event.tagData.linMsgApi.linCRCinfo
        return LinEvent(
            tag=event.tag,
            tag_name=tag_name,
            timestamp_ns=int(event.timeStamp),
            channel_index=int(event.chanIndex),
            lin_id=int(crc_info.id),
            flags=int(crc_info.flags),
            description=f"FLAGS=0x{int(crc_info.flags):02X}",
        )

    return LinEvent(
        tag=event.tag,
        tag_name=tag_name,
        timestamp_ns=int(event.timeStamp),
        channel_index=int(event.chanIndex),
        description=fallback_description,
    )


def _lin_version_value(version: str) -> int:
    try:
        return c.LIN_VERSION_BY_NAME[version]
    except KeyError as exc:
        valid = ", ".join(c.LIN_VERSION_BY_NAME)
        raise ValueError(f"Unsupported LIN version {version!r}. Use one of: {valid}") from exc


def _make_dlc_map(default_dlc: int, overrides: Optional[dict[int, int]]) -> list[int]:
    _validate_dlc(default_dlc, allow_undefined=True)
    dlc = [default_dlc] * 64
    for lin_id, value in (overrides or {}).items():
        _validate_lin_id(lin_id)
        _validate_dlc(value, allow_undefined=True)
        dlc[lin_id] = value
    return dlc


def _make_checksum_map(version: int, default: str, overrides: Optional[dict[int, str]]) -> list[int]:
    checksum = [_checksum_value(version, default)] * 60
    for lin_id, value in (overrides or {}).items():
        if lin_id < 0 or lin_id > 59:
            raise ValueError("xlLinSetChecksum only accepts LIN IDs 0..59")
        checksum[lin_id] = _checksum_value(version, value)
    return checksum


def _checksum_value(version: int, name: str) -> int:
    if name == "auto":
        return c.XL_LIN_CHECKSUM_CLASSIC if version == c.XL_LIN_VERSION_1_3 else c.XL_LIN_CHECKSUM_ENHANCED
    try:
        return c.CHECKSUM_BY_NAME[name]
    except KeyError as exc:
        raise ValueError("checksum must be one of: auto, classic, enhanced, undefined") from exc


def _slave_checksum_value(version: int, lin_id: int, name: str) -> int:
    if name == "auto":
        if version == c.XL_LIN_VERSION_1_3 or lin_id >= 60:
            return c.XL_LIN_CALC_CHECKSUM
        return c.XL_LIN_CALC_CHECKSUM_ENHANCED
    if name == "classic":
        return c.XL_LIN_CALC_CHECKSUM
    if name == "enhanced":
        return c.XL_LIN_CALC_CHECKSUM_ENHANCED
    raise ValueError("slave checksum must be one of: auto, classic, enhanced")


def _validate_lin_id(lin_id: int) -> None:
    if lin_id < 0 or lin_id > 63:
        raise ValueError("LIN ID must be in range 0x00..0x3F")


def _validate_dlc(dlc: int, allow_undefined: bool = False) -> None:
    if allow_undefined and dlc == c.XL_LIN_UNDEFINED_DLC:
        return
    if dlc < 0 or dlc > 8:
        raise ValueError("LIN DLC must be in range 0..8")
