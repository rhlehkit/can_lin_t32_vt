from __future__ import annotations

import ctypes
import os
import platform
import sys
from pathlib import Path
from typing import Iterable, Optional

from . import constants as c


XLstatus = ctypes.c_int16
XLaccess = ctypes.c_uint64
XLportHandle = ctypes.c_int32
XLhandle = ctypes.c_void_p


class XLlinStatPar(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("LINMode", ctypes.c_uint32),
        ("baudrate", ctypes.c_int32),
        ("LINVersion", ctypes.c_uint32),
        ("reserved", ctypes.c_uint32),
    ]


class XLcanMsg(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("id", ctypes.c_uint32),
        ("flags", ctypes.c_uint16),
        ("dlc", ctypes.c_uint16),
        ("res1", ctypes.c_uint64),
        ("data", ctypes.c_uint8 * 8),
        ("res2", ctypes.c_uint64),
    ]


class XLchipState(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("busStatus", ctypes.c_uint8),
        ("txErrorCounter", ctypes.c_uint8),
        ("rxErrorCounter", ctypes.c_uint8),
    ]


class XLsyncPulse(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("pulseCode", ctypes.c_uint8),
        ("time", ctypes.c_uint64),
    ]


class XLtransceiver(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("event_reason", ctypes.c_uint8),
        ("is_present", ctypes.c_uint8),
    ]


class XLdaioData(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("flags", ctypes.c_uint16),
        ("timestamp_correction", ctypes.c_uint32),
        ("mask_digital", ctypes.c_uint8),
        ("value_digital", ctypes.c_uint8),
        ("mask_analog", ctypes.c_uint8),
        ("reserved0", ctypes.c_uint8),
        ("value_analog", ctypes.c_uint16 * 4),
        ("pwm_frequency", ctypes.c_uint32),
        ("pwm_value", ctypes.c_uint16),
        ("reserved1", ctypes.c_uint32),
        ("reserved2", ctypes.c_uint32),
    ]


class XLlinMsg(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("id", ctypes.c_uint8),
        ("dlc", ctypes.c_uint8),
        ("flags", ctypes.c_uint16),
        ("data", ctypes.c_uint8 * 8),
        ("crc", ctypes.c_uint8),
    ]


class XLlinNoAns(ctypes.Structure):
    _pack_ = 1
    _fields_ = [("id", ctypes.c_uint8)]


class XLlinWakeUp(ctypes.Structure):
    _pack_ = 1
    _fields_ = [("flag", ctypes.c_uint8)]


class XLlinSleep(ctypes.Structure):
    _pack_ = 1
    _fields_ = [("flag", ctypes.c_uint8)]


class XLlinCrcInfo(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("id", ctypes.c_uint8),
        ("flags", ctypes.c_uint8),
    ]


class XLlinMsgApi(ctypes.Union):
    _pack_ = 1
    _fields_ = [
        ("linMsg", XLlinMsg),
        ("linNoAns", XLlinNoAns),
        ("linWakeUp", XLlinWakeUp),
        ("linSleep", XLlinSleep),
        ("linCRCinfo", XLlinCrcInfo),
    ]


class XLtagData(ctypes.Union):
    _pack_ = 1
    _fields_ = [
        ("msg", XLcanMsg),
        ("chipState", XLchipState),
        ("linMsgApi", XLlinMsgApi),
        ("syncPulse", XLsyncPulse),
        ("daioData", XLdaioData),
        ("transceiver", XLtransceiver),
        ("raw", ctypes.c_uint8 * 32),
    ]


class XLevent(ctypes.Structure):
    _pack_ = 1
    _fields_ = [
        ("tag", ctypes.c_uint8),
        ("chanIndex", ctypes.c_uint8),
        ("transId", ctypes.c_uint16),
        ("portHandle", ctypes.c_uint16),
        ("reserved", ctypes.c_uint16),
        ("timeStamp", ctypes.c_uint64),
        ("tagData", XLtagData),
    ]


assert ctypes.sizeof(XLevent) == 48, ctypes.sizeof(XLevent)


class VectorXLError(RuntimeError):
    """Raised when the XL Driver Library reports an error."""

    def __init__(self, function: str, status: int, detail: Optional[str] = None) -> None:
        self.function = function
        self.status = int(status)
        suffix = f": {detail}" if detail else ""
        super().__init__(f"{function} failed with XL status {self.status}{suffix}")


class VectorXLApi:
    """Thin ctypes binding for the small part of vxlapi needed by the examples."""

    def __init__(self, dll_path: Optional[str] = None) -> None:
        self.dll_path = dll_path
        self.dll = self._load_library(dll_path)
        self._bind_functions()

    def _load_library(self, dll_path: Optional[str]) -> ctypes.CDLL:
        if os.name != "nt":
            raise OSError("Vector XL Driver Library is a Windows DLL; run this on Windows.")

        candidates: Iterable[str]
        if dll_path:
            path = Path(dll_path).expanduser().resolve()
            if hasattr(os, "add_dll_directory"):
                os.add_dll_directory(str(path.parent))
            candidates = [str(path)]
        else:
            candidates = ["vxlapi64.dll" if platform.architecture()[0] == "64bit" else "vxlapi.dll"]

        errors: list[str] = []
        for candidate in candidates:
            try:
                return ctypes.WinDLL(candidate)  # type: ignore[attr-defined]
            except OSError as exc:
                errors.append(f"{candidate}: {exc}")

        bitness = "64-bit" if sys.maxsize > 2**32 else "32-bit"
        raise OSError(
            "Could not load Vector XL Driver Library. Install Vector Driver Setup / "
            f"XL Driver Library matching your {bitness} Python, or pass --dll. "
            + " | ".join(errors)
        )

    def _bind_functions(self) -> None:
        self.dll.xlOpenDriver.restype = XLstatus
        self.dll.xlOpenDriver.argtypes = []

        self.dll.xlCloseDriver.restype = XLstatus
        self.dll.xlCloseDriver.argtypes = []

        self.dll.xlGetApplConfig.restype = XLstatus
        self.dll.xlGetApplConfig.argtypes = [
            ctypes.c_char_p,
            ctypes.c_uint32,
            ctypes.POINTER(ctypes.c_uint32),
            ctypes.POINTER(ctypes.c_uint32),
            ctypes.POINTER(ctypes.c_uint32),
            ctypes.c_uint32,
        ]

        self.dll.xlGetChannelMask.restype = XLaccess
        self.dll.xlGetChannelMask.argtypes = [ctypes.c_int32, ctypes.c_int32, ctypes.c_int32]

        self.dll.xlOpenPort.restype = XLstatus
        self.dll.xlOpenPort.argtypes = [
            ctypes.POINTER(XLportHandle),
            ctypes.c_char_p,
            XLaccess,
            ctypes.POINTER(XLaccess),
            ctypes.c_uint32,
            ctypes.c_uint32,
            ctypes.c_uint32,
        ]

        self.dll.xlClosePort.restype = XLstatus
        self.dll.xlClosePort.argtypes = [XLportHandle]

        self.dll.xlActivateChannel.restype = XLstatus
        self.dll.xlActivateChannel.argtypes = [XLportHandle, XLaccess, ctypes.c_uint32, ctypes.c_uint32]

        self.dll.xlDeactivateChannel.restype = XLstatus
        self.dll.xlDeactivateChannel.argtypes = [XLportHandle, XLaccess]

        self.dll.xlFlushReceiveQueue.restype = XLstatus
        self.dll.xlFlushReceiveQueue.argtypes = [XLportHandle]

        self.dll.xlReceive.restype = XLstatus
        self.dll.xlReceive.argtypes = [XLportHandle, ctypes.POINTER(ctypes.c_uint32), ctypes.POINTER(XLevent)]

        self.dll.xlGetErrorString.restype = ctypes.c_char_p
        self.dll.xlGetErrorString.argtypes = [XLstatus]

        self.dll.xlGetEventString.restype = ctypes.c_char_p
        self.dll.xlGetEventString.argtypes = [ctypes.POINTER(XLevent)]

        self.dll.xlLinSetChannelParams.restype = XLstatus
        self.dll.xlLinSetChannelParams.argtypes = [XLportHandle, XLaccess, XLlinStatPar]

        self.dll.xlLinSetDLC.restype = XLstatus
        self.dll.xlLinSetDLC.argtypes = [XLportHandle, XLaccess, ctypes.POINTER(ctypes.c_uint8)]

        self.dll.xlLinSetChecksum.restype = XLstatus
        self.dll.xlLinSetChecksum.argtypes = [XLportHandle, XLaccess, ctypes.POINTER(ctypes.c_uint8)]

        self.dll.xlLinSetSlave.restype = XLstatus
        self.dll.xlLinSetSlave.argtypes = [
            XLportHandle,
            XLaccess,
            ctypes.c_uint8,
            ctypes.POINTER(ctypes.c_uint8),
            ctypes.c_uint8,
            ctypes.c_uint16,
        ]

        self.dll.xlLinSendRequest.restype = XLstatus
        self.dll.xlLinSendRequest.argtypes = [XLportHandle, XLaccess, ctypes.c_uint8, ctypes.c_uint32]

        self.dll.xlLinWakeUp.restype = XLstatus
        self.dll.xlLinWakeUp.argtypes = [XLportHandle, XLaccess]

    def check(self, status: int, function: str, ok: tuple[int, ...] = (c.XL_SUCCESS,)) -> int:
        status = int(status)
        if status not in ok:
            raise VectorXLError(function, status, self.error_string(status))
        return status

    def error_string(self, status: int) -> str:
        try:
            raw = self.dll.xlGetErrorString(XLstatus(status))
        except Exception:
            raw = None
        return _decode(raw) or "no error string available"

    def event_string(self, event: XLevent) -> str:
        try:
            raw = self.dll.xlGetEventString(ctypes.byref(event))
        except Exception:
            raw = None
        return _decode(raw) or ""

    def open_driver(self) -> None:
        self.check(self.dll.xlOpenDriver(), "xlOpenDriver")

    def close_driver(self) -> None:
        self.check(self.dll.xlCloseDriver(), "xlCloseDriver")

    def get_application_channel_mask(self, app_name: str, app_channel: int) -> int:
        hw_type = ctypes.c_uint32()
        hw_index = ctypes.c_uint32()
        hw_channel = ctypes.c_uint32()
        self.check(
            self.dll.xlGetApplConfig(
                _bytes(app_name),
                app_channel,
                ctypes.byref(hw_type),
                ctypes.byref(hw_index),
                ctypes.byref(hw_channel),
                c.XL_BUS_TYPE_LIN,
            ),
            "xlGetApplConfig",
        )
        mask = int(self.dll.xlGetChannelMask(hw_type.value, hw_index.value, hw_channel.value))
        if mask == 0:
            raise VectorXLError("xlGetChannelMask", 0, "no channel mask found for application config")
        return mask

    def open_port(
        self,
        user_name: str,
        access_mask: int,
        rx_queue_size: int = 256,
    ) -> tuple[int, int]:
        port_handle = XLportHandle(c.XL_INVALID_PORTHANDLE)
        permission_mask = XLaccess(access_mask)
        self.check(
            self.dll.xlOpenPort(
                ctypes.byref(port_handle),
                _bytes(user_name),
                XLaccess(access_mask),
                ctypes.byref(permission_mask),
                rx_queue_size,
                c.XL_INTERFACE_VERSION,
                c.XL_BUS_TYPE_LIN,
            ),
            "xlOpenPort",
        )
        return int(port_handle.value), int(permission_mask.value)

    def close_port(self, port_handle: int) -> None:
        self.check(self.dll.xlClosePort(XLportHandle(port_handle)), "xlClosePort")

    def activate_channel(self, port_handle: int, access_mask: int, reset_clock: bool = True) -> None:
        flags = c.XL_ACTIVATE_RESET_CLOCK if reset_clock else c.XL_ACTIVATE_NONE
        self.check(
            self.dll.xlActivateChannel(
                XLportHandle(port_handle),
                XLaccess(access_mask),
                c.XL_BUS_TYPE_LIN,
                flags,
            ),
            "xlActivateChannel",
        )

    def deactivate_channel(self, port_handle: int, access_mask: int) -> None:
        self.check(
            self.dll.xlDeactivateChannel(XLportHandle(port_handle), XLaccess(access_mask)),
            "xlDeactivateChannel",
        )

    def flush_receive_queue(self, port_handle: int) -> None:
        self.check(self.dll.xlFlushReceiveQueue(XLportHandle(port_handle)), "xlFlushReceiveQueue")

    def lin_set_channel_params(self, port_handle: int, access_mask: int, lin_mode: int, baudrate: int, lin_version: int) -> None:
        params = XLlinStatPar(lin_mode, baudrate, lin_version, 0)
        self.check(
            self.dll.xlLinSetChannelParams(XLportHandle(port_handle), XLaccess(access_mask), params),
            "xlLinSetChannelParams",
        )

    def lin_set_dlc(self, port_handle: int, access_mask: int, dlc: Iterable[int]) -> None:
        values = list(dlc)
        if len(values) != 64:
            raise ValueError("DLC array must contain exactly 64 entries")
        array_type = ctypes.c_uint8 * 64
        self.check(
            self.dll.xlLinSetDLC(XLportHandle(port_handle), XLaccess(access_mask), array_type(*values)),
            "xlLinSetDLC",
        )

    def lin_set_checksum(self, port_handle: int, access_mask: int, checksum: Iterable[int]) -> None:
        values = list(checksum)
        if len(values) != 60:
            raise ValueError("checksum array must contain exactly 60 entries for LIN IDs 0..59")
        array_type = ctypes.c_uint8 * 60
        self.check(
            self.dll.xlLinSetChecksum(XLportHandle(port_handle), XLaccess(access_mask), array_type(*values)),
            "xlLinSetChecksum",
        )

    def lin_set_slave(
        self,
        port_handle: int,
        access_mask: int,
        lin_id: int,
        data: Iterable[int],
        dlc: int,
        checksum: int,
    ) -> None:
        payload = list(data)
        if len(payload) > 8:
            raise ValueError("LIN payload can contain at most 8 bytes")
        payload = payload + [0] * (8 - len(payload))
        array_type = ctypes.c_uint8 * 8
        self.check(
            self.dll.xlLinSetSlave(
                XLportHandle(port_handle),
                XLaccess(access_mask),
                ctypes.c_uint8(lin_id),
                array_type(*payload),
                ctypes.c_uint8(dlc),
                ctypes.c_uint16(checksum),
            ),
            "xlLinSetSlave",
        )

    def lin_send_request(self, port_handle: int, access_mask: int, lin_id: int, flags: int = 0) -> None:
        self.check(
            self.dll.xlLinSendRequest(
                XLportHandle(port_handle),
                XLaccess(access_mask),
                ctypes.c_uint8(lin_id),
                ctypes.c_uint32(flags),
            ),
            "xlLinSendRequest",
        )

    def lin_wakeup(self, port_handle: int, access_mask: int) -> None:
        self.check(
            self.dll.xlLinWakeUp(XLportHandle(port_handle), XLaccess(access_mask)),
            "xlLinWakeUp",
        )

    def receive_one(self, port_handle: int) -> Optional[XLevent]:
        count = ctypes.c_uint32(1)
        event = XLevent()
        status = int(self.dll.xlReceive(XLportHandle(port_handle), ctypes.byref(count), ctypes.byref(event)))
        if status == c.XL_ERR_QUEUE_IS_EMPTY:
            return None
        self.check(status, "xlReceive")
        if count.value == 0:
            return None
        return event


def _bytes(value: str) -> bytes:
    return value.encode("ascii")


def _decode(value: Optional[bytes]) -> str:
    if not value:
        return ""
    return value.decode("mbcs", errors="replace")
