"""Diagnostic test case for identifying the Python runtime used by CANoe/vTESTstudio."""

from __future__ import annotations

import site
import sys
from pathlib import Path

import vector.canoe
import vector.canoe.tfs


def step(title: str, detail: str) -> None:
    test_step = getattr(vector.canoe.tfs, "test_step", None)
    if callable(test_step):
        try:
            test_step(title, detail)
            return
        except TypeError:
            test_step(f"{title}: {detail}")
            return
    print(f"[{title}] {detail}")


@vector.canoe.tfs.export
@vector.canoe.tfs.test_case
def TC_PYTHON_RuntimeInfo():
    """Print the Python executable and package search paths used by the test run."""

    step("Python executable", sys.executable)
    step("Python version", sys.version.replace("\n", " "))
    step("Python prefix", sys.prefix)
    step("Python base_prefix", getattr(sys, "base_prefix", ""))
    step("Current file", str(Path(__file__).resolve()))

    try:
        site_packages = site.getsitepackages()
    except Exception as exc:
        site_packages = [f"site.getsitepackages failed: {exc}"]

    for index, path in enumerate(site_packages):
        step(f"site-packages {index}", path)

    for index, path in enumerate(sys.path[:20]):
        step(f"sys.path {index}", path)

