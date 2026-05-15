from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lin_master_request import add_common_args, build_config, parse_assignments, parse_int
from vector_lin import VectorLinChannel, format_event


def main() -> int:
    parser = argparse.ArgumentParser(description="Listen to LIN events through Vector XL Driver Library.")
    add_common_args(parser)
    parser.add_argument("--default-dlc", type=parse_int, default=0xFF, help="Default receive DLC; 0xFF means undefined.")
    parser.add_argument("--dlc-map", action="append", default=[], help="Override receive DLC, e.g. --dlc-map 0x12=3.")
    parser.add_argument("--listen-ms", type=float, default=100.0, help="Polling interval while listening.")

    args = parser.parse_args()

    with VectorLinChannel(build_config(args)) as lin:
        lin.configure_slave(default_dlc=args.default_dlc, dlc_by_id=parse_assignments(args.dlc_map))
        lin.activate()
        print("LIN monitor is active. Press Ctrl+C to stop.")
        try:
            while True:
                for event in lin.receive(timeout_s=args.listen_ms / 1000.0, max_events=64):
                    print(format_event(event))
        except KeyboardInterrupt:
            print("Stopping.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
