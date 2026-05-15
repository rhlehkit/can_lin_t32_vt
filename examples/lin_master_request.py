from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vector_lin import VectorLinChannel, VectorLinConfig, format_event


def main() -> int:
    parser = argparse.ArgumentParser(description="Send LIN master header requests through Vector XL Driver Library.")
    add_common_args(parser)
    parser.add_argument("--request-id", type=parse_int, default=0x12, help="LIN ID to request, e.g. 0x12.")
    parser.add_argument("--count", type=int, default=1, help="Number of requests. Use 0 for forever.")
    parser.add_argument("--period-ms", type=float, default=1000.0, help="Delay between requests.")
    parser.add_argument("--listen-ms", type=float, default=100.0, help="Receive window after each request.")
    parser.add_argument("--default-dlc", type=parse_int, default=8, help="Default DLC configured for all LIN IDs.")
    parser.add_argument("--dlc", action="append", default=[], help="Override DLC, e.g. --dlc 0x12=4.")
    parser.add_argument(
        "--checksum",
        choices=["auto", "classic", "enhanced", "undefined"],
        default="auto",
        help="Checksum mode for LIN IDs 0..59.",
    )
    parser.add_argument("--slave-id", type=parse_int, help="Optional slave response ID hosted by this master node.")
    parser.add_argument("--slave-data", default="", help="Optional hosted slave payload bytes, e.g. '01 02 A0'.")
    parser.add_argument("--slave-dlc", type=parse_int, help="Optional hosted slave DLC. Defaults to payload length.")
    parser.add_argument("--slave-checksum", choices=["auto", "classic", "enhanced"], default="auto")

    args = parser.parse_args()

    config = build_config(args)
    dlc_by_id = parse_assignments(args.dlc)

    with VectorLinChannel(config) as lin:
        lin.configure_master(default_dlc=args.default_dlc, dlc_by_id=dlc_by_id, checksum=args.checksum)

        if args.slave_id is not None:
            lin.set_slave_response(
                args.slave_id,
                parse_bytes(args.slave_data),
                dlc=args.slave_dlc,
                checksum=args.slave_checksum,
            )

        lin.activate()
        iteration = 0
        while args.count == 0 or iteration < args.count:
            lin.send_request(args.request_id)
            for event in lin.receive(timeout_s=args.listen_ms / 1000.0, max_events=64):
                print(format_event(event))
            iteration += 1
            if args.count == 0 or iteration < args.count:
                time.sleep(args.period_ms / 1000.0)

    return 0


def add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--app-name", default="PythonLIN", help="Vector Hardware Config application name.")
    parser.add_argument("--app-channel", type=int, default=0, help="Application channel configured in Vector Hardware Config.")
    parser.add_argument("--channel-index", type=int, help="Use raw XL channel index instead of app config.")
    parser.add_argument("--channel-mask", type=parse_int, help="Use raw XL access mask instead of app config.")
    parser.add_argument("--baudrate", type=int, default=19200, help="LIN baudrate.")
    parser.add_argument("--lin-version", choices=["1.3", "2.0", "2.1"], default="2.1")
    parser.add_argument("--dll", help="Full path to vxlapi64.dll or vxlapi.dll if it is not on PATH.")
    parser.add_argument("--allow-shared-init", action="store_true", help="Do not fail if init permission is not granted.")


def build_config(args: argparse.Namespace) -> VectorLinConfig:
    return VectorLinConfig(
        app_name=args.app_name,
        app_channel=args.app_channel,
        baudrate=args.baudrate,
        lin_version=args.lin_version,
        channel_index=args.channel_index,
        channel_mask=args.channel_mask,
        dll_path=args.dll,
        require_init_access=not args.allow_shared_init,
    )


def parse_int(value: str) -> int:
    return int(value, 0)


def parse_assignments(values: list[str]) -> dict[int, int]:
    result: dict[int, int] = {}
    for value in values:
        if "=" not in value:
            raise argparse.ArgumentTypeError(f"Expected ID=DLC assignment, got {value!r}")
        left, right = value.split("=", 1)
        result[parse_int(left)] = parse_int(right)
    return result


def parse_bytes(value: str) -> list[int]:
    if not value.strip():
        return []
    parts = value.replace(",", " ").split()
    data = [parse_int(part) for part in parts]
    for byte in data:
        if byte < 0 or byte > 0xFF:
            raise argparse.ArgumentTypeError("Payload bytes must be in range 0x00..0xFF")
    return data


if __name__ == "__main__":
    raise SystemExit(main())
