import uuid
from pathlib import Path


def stable_device_id() -> str:
    """Build a stable, readable device id for the Raspberry Pi."""
    machine_id = _read_first_existing(
        [
            Path("/etc/machine-id"),
            Path("/var/lib/dbus/machine-id"),
        ]
    )
    if machine_id:
        return f"pl-rpi-{machine_id[:12]}"

    return f"pl-rpi-{uuid.getnode():012x}"


def _read_first_existing(paths: list[Path]) -> str | None:
    for path in paths:
        if path.exists():
            value = path.read_text(encoding="utf-8").strip()
            if value:
                return value
    return None
