from __future__ import annotations

import platform
from pathlib import Path


RASPBERRY_PI_TEST_ROOT = Path("device") / "raspberry_pi"


def _is_raspberry_pi_host() -> bool:
    if platform.system() != "Linux":
        return False

    model_paths = (
        Path("/proc/device-tree/model"),
        Path("/sys/firmware/devicetree/base/model"),
    )
    for model_path in model_paths:
        try:
            model = model_path.read_text(errors="ignore").lower()
        except OSError:
            continue
        if "raspberry pi" in model:
            return True

    try:
        cpuinfo = Path("/proc/cpuinfo").read_text(errors="ignore").lower()
    except OSError:
        return False

    return "raspberry pi" in cpuinfo or "bcm270" in cpuinfo or "bcm271" in cpuinfo


def pytest_ignore_collect(collection_path: Path, config) -> bool | None:
    if _is_raspberry_pi_host():
        return None

    try:
        relative_path = Path(collection_path).resolve().relative_to(config.rootpath)
    except ValueError:
        return None

    if (
        relative_path == RASPBERRY_PI_TEST_ROOT
        or RASPBERRY_PI_TEST_ROOT in relative_path.parents
    ):
        return True

    return None
