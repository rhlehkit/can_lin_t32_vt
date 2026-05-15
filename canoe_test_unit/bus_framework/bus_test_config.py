"""Edit this file for your CANoe/vTESTstudio project.

IDs may be integers or strings accepted by int(value, 0), for example
"0x123" or "291".
"""

CONFIG = {
    "defaults": {
        "timeout_ms": 1000,
        "period_tolerance_ms": 5,
        "period_sample_count": 20,
    },
    "can": {
        "channel": 1,
        "tx_once": {
            "id": "0x123",
            "extended": False,
            "data": ["0x10", "0x22", "0x33", "0x44", "0x55", "0x66", "0x77", "0x88"],
        },
        "rx_expected": {
            "id": "0x321",
            "extended": False,
            "data": ["0x01", "0x02", "0x03", "0x04"],
            "check_data": True,
            "timeout_ms": 1000,
        },
        "periodic_tx": {
            "task_id": 101,
            "id": "0x555",
            "extended": False,
            "period_ms": 100,
            "duration_ms": 1000,
            "data": ["0xAA", "0xBB", "0xCC", "0xDD"],
        },
        "period_check": {
            "id": "0x100",
            "extended": False,
            "expected_period_ms": 10,
            "tolerance_ms": 2,
            "sample_count": 30,
            "timeout_ms": 2000,
        },
    },
    "lin": {
        "channel": 1,
        "tx_once": {
            "id": "0x12",
            "data": ["0x10", "0x22", "0x33", "0x44"],
        },
        "rx_expected": {
            "id": "0x22",
            "data": ["0x55", "0xAA", "0x12", "0x34"],
            "request_header_before_wait": True,
            "check_data": True,
            "timeout_ms": 1000,
        },
        "periodic_tx": {
            "task_id": 201,
            "id": "0x15",
            "send_data": False,
            "period_ms": 100,
            "duration_ms": 1000,
            "data": [],
        },
        "period_check": {
            "id": "0x22",
            "expected_period_ms": 100,
            "tolerance_ms": 10,
            "sample_count": 10,
            "timeout_ms": 3000,
        },
    },
}

