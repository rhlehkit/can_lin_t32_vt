"""TRACE32 integration settings for CANoe/vTESTstudio Python Test Units.

Edit this file on the PC where TRACE32 PowerView is running.
"""

TRACE32_CONFIG = {
    "enabled": True,
    "connection": {
        "node": "localhost",
        "port": 20000,
        "protocol": "TCP",
        "timeout_s": 5.0,
        "packlen": 1024,
    },
    "snapshot": {
        # Keep these false by default. Halting a target from a test case can
        # disturb timing-sensitive CAN/LIN tests.
        "halt_before_read": False,
        "resume_after_read": False,
        # Optional TRACE32 commands to run before reading variables.
        # Examples: ["Var.Frame /Locals", "Register.view"]
        "pre_read_commands": [],
    },
    "variables": [
        # Edit these names to match the loaded ELF/symbol file in TRACE32.
        # {"name": "gVehicleSpeed", "label": "VehicleSpeed"},
        # {"name": "AppState.currentMode", "label": "CurrentMode", "expected": 3},
    ],
    "registers": [
        # Common examples. Exact names depend on CPU architecture.
        # "PC",
        # "SP",
    ],
    "assert_variables": [
        # Examples:
        # {"name": "gDiagState", "expected": 2},
        # {"name": "gCurrentA", "expected": 12.5, "tolerance": 0.5},
    ],
    "write_variables": [
        # Examples:
        # {"name": "gTestMode", "value": 1, "verify": True},
        # {"name": "AppState.injectedSpeed", "value": 42, "verify": True},
    ],
}
