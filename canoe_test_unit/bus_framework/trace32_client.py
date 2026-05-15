"""Small TRACE32 Remote API wrapper used by the Python Test Unit examples."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional


class Trace32Error(AssertionError):
    """Raised when TRACE32 is unavailable or returns unexpected data."""


@dataclass(frozen=True)
class DebugValue:
    name: str
    value: Any
    kind: str = "variable"
    label: Optional[str] = None

    def format(self) -> str:
        display_name = self.label or self.name
        return f"{self.kind} {display_name}={self.value!r}"


class Trace32Client:
    def __init__(self, config: Dict[str, Any]) -> None:
        self.config = config
        self._dbg = None

    def connect(self):
        if self._dbg is not None:
            return self._dbg

        if not self.config.get("enabled", True):
            raise Trace32Error("TRACE32 integration is disabled in trace32_config.py.")

        try:
            import lauterbach.trace32.rcl as t32
        except ImportError as exc:
            raise Trace32Error(
                "Python package 'lauterbach-trace32-rcl' is not installed. "
                "Install it on the CANoe/vTESTstudio Python runtime, for example: "
                "py -m pip install lauterbach-trace32-rcl~=1.1.0"
            ) from exc

        connection = self.config.get("connection", {})
        protocol = str(connection.get("protocol", "TCP")).upper()
        kwargs = {
            "node": connection.get("node", "localhost"),
            "port": int(connection.get("port", 20000)),
            "protocol": protocol,
            "timeout": float(connection.get("timeout_s", 5.0)),
        }
        if protocol == "UDP":
            kwargs["packlen"] = int(connection.get("packlen", 1024))

        self._dbg = t32.connect(**kwargs)
        return self._dbg

    def command(self, command: str) -> None:
        self.connect().cmd(command)

    def function(self, expression: str) -> str:
        return str(self.connect().fnc(expression))

    def read_variable(self, name: str, label: Optional[str] = None) -> DebugValue:
        variable = self.connect().variable.read(name)
        return DebugValue(name=name, value=getattr(variable, "value", variable), kind="variable", label=label)

    def write_variable(self, name: str, value: Any, verify: bool = True, label: Optional[str] = None) -> DebugValue:
        normalized_value = _format_trace32_value(value)
        command = f"Var.Set {name}={normalized_value}"
        self.command(command)

        if not verify:
            return DebugValue(name=name, value=value, kind="variable", label=label)

        written = self.read_variable(name, label)
        self._assert_value(written, value)
        return written

    def write_variables(self, variables: Iterable[Dict[str, Any]]) -> List[DebugValue]:
        result = []
        for item in variables:
            result.append(
                self.write_variable(
                    name=str(item["name"]),
                    value=item["value"],
                    verify=bool(item.get("verify", True)),
                    label=item.get("label"),
                )
            )
        return result

    def read_variables(self, variables: Iterable[Dict[str, Any]]) -> List[DebugValue]:
        result = []
        for item in variables:
            result.append(self.read_variable(str(item["name"]), item.get("label")))
        return result

    def read_register(self, name: str) -> DebugValue:
        register = self.connect().register.read(name)
        return DebugValue(name=name, value=getattr(register, "value", register), kind="register")

    def read_registers(self, names: Iterable[str]) -> List[DebugValue]:
        return [self.read_register(str(name)) for name in names]

    def snapshot(self) -> List[DebugValue]:
        snapshot_config = self.config.get("snapshot", {})
        halt = bool(snapshot_config.get("halt_before_read", False))
        resume = bool(snapshot_config.get("resume_after_read", False))

        if halt:
            self.command("Break")

        try:
            for command in snapshot_config.get("pre_read_commands", []):
                self.command(str(command))

            values = []
            values.extend(self.read_variables(self.config.get("variables", [])))
            values.extend(self.read_registers(self.config.get("registers", [])))
            return values
        finally:
            if resume:
                self.command("Go")

    def assert_variables(self, checks: Iterable[Dict[str, Any]]) -> List[DebugValue]:
        values = []
        for check in checks:
            name = str(check["name"])
            value = self.read_variable(name, check.get("label"))
            values.append(value)
            self._assert_value(value, check.get("expected"), check.get("tolerance"))
        return values

    def _assert_value(self, actual: DebugValue, expected: Any, tolerance: Any = None) -> None:
        if expected is None:
            return

        actual_value = _normalize_value(actual.value)
        expected_value = _normalize_value(expected)

        if tolerance is not None:
            actual_num = float(actual_value)
            expected_num = float(expected_value)
            tolerance_num = float(tolerance)
            if abs(actual_num - expected_num) > tolerance_num:
                raise Trace32Error(
                    f"TRACE32 variable {actual.name} expected {expected_num} +/- {tolerance_num}, "
                    f"got {actual_num}"
                )
            return

        if actual_value != expected_value:
            raise Trace32Error(f"TRACE32 variable {actual.name} expected {expected_value!r}, got {actual_value!r}")


def _normalize_value(value: Any) -> Any:
    if isinstance(value, str):
        text = value.strip()
        try:
            return int(text, 0)
        except ValueError:
            try:
                return float(text)
            except ValueError:
                return text
    return value


def _format_trace32_value(value: Any) -> str:
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        text = value.strip()
        if text.startswith(("0x", "0X")):
            return text
        try:
            float(text)
            return text
        except ValueError:
            escaped = text.replace("\\", "\\\\").replace('"', '\\"')
            return f'"{escaped}"'
    return str(value)
