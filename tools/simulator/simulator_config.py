from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .scenarios import SUPPORTED_SCENARIOS


DEFAULT_BASE_URL = "http://localhost:8000"
DEFAULT_SCHEMA_VERSION = "1.0"
DEFAULT_MASTER_MODEL = "esp32_master"
DEFAULT_CAMERA_MODEL = "xiao_esp32s3_camera"
PLACEHOLDER_TOKENS = {
    "replace-with-device-api-token",
    "replace_with_device_api_token",
    "your-device-token",
    "device-token",
}


@dataclass(slots=True)
class SimulatorNodeConfig:
    device_id: int | None
    device_token: str
    hardware_device_id: str
    node_role: str
    firmware_version: str = "1.0.0"
    hardware_model: str = DEFAULT_MASTER_MODEL
    hardware_version: str | None = None
    schema_version: str = DEFAULT_SCHEMA_VERSION
    display_name: str | None = None
    node_index: int | None = None
    heartbeat_interval_seconds: float = 10.0
    sensor_interval_seconds: float = 10.0
    image_interval_seconds: float = 300.0
    diagnostics_interval_seconds: float = 30.0
    command_poll_interval_seconds: float = 4.0
    ota_step_delay_seconds: float = 1.0
    capabilities: list[str] = field(default_factory=list)
    scenarios: list[str] = field(default_factory=list)
    ota_failure_rate: float = 0.0
    command_failure_rate: float = 0.0
    register_node: bool = True
    parent_hardware_device_id: str | None = None

    @property
    def is_master(self) -> bool:
        return self.node_role == "master"

    @property
    def is_camera(self) -> bool:
        return self.node_role == "camera"


@dataclass(slots=True)
class SimulatorConfig:
    base_url: str = DEFAULT_BASE_URL
    nodes: list[SimulatorNodeConfig] = field(default_factory=list)
    run_seconds: float | None = None
    log_level: str = "info"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run lightweight PlantLab simulated hardware nodes.")
    parser.add_argument("--config", help="JSON config file with one or more simulated nodes.")
    parser.add_argument("--base-url", default=os.getenv("PLANTLAB_SIM_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument("--device-id", type=int, default=_optional_int(os.getenv("PLANTLAB_DEVICE_ID")))
    parser.add_argument("--device-token", default=os.getenv("PLANTLAB_DEVICE_TOKEN"))
    parser.add_argument("--devices", type=int, default=1, help="Number of simulated master devices for CLI mode.")
    parser.add_argument("--camera-nodes", type=int, default=1, help="Camera nodes per simulated master in CLI mode.")
    parser.add_argument("--firmware-version", default=os.getenv("PLANTLAB_SIM_FIRMWARE_VERSION", "1.0.0"))
    parser.add_argument("--schema-version", default=DEFAULT_SCHEMA_VERSION)
    parser.add_argument("--heartbeat-interval", type=float, default=10.0)
    parser.add_argument("--sensor-interval", type=float, default=10.0)
    parser.add_argument("--image-interval", type=float, default=300.0)
    parser.add_argument("--diagnostics-interval", type=float, default=30.0)
    parser.add_argument("--command-poll-interval", type=float, default=4.0)
    parser.add_argument("--ota-step-delay", type=float, default=1.0)
    parser.add_argument("--scenario", action="append", default=[], help="Scenario name. Can be repeated.")
    parser.add_argument("--ota-failure-rate", type=float, default=0.0)
    parser.add_argument("--command-failure-rate", type=float, default=0.0)
    parser.add_argument("--skip-register", action="store_true", help="Do not call /api/device-nodes/register at startup.")
    parser.add_argument("--run-seconds", type=float, default=None, help="Stop automatically after this many seconds.")
    parser.add_argument("--duration-seconds", type=float, dest="run_seconds", help="Alias for --run-seconds.")
    parser.add_argument("--log-level", choices=["debug", "info", "warning"], default="info")
    return parser.parse_args(argv)


def load_config_from_args(args: argparse.Namespace) -> SimulatorConfig:
    if args.config:
        config = _load_config_file(Path(args.config), args)
        _validate_tokens(config.nodes)
        return config
    if not args.device_token:
        raise SystemExit("--device-token or PLANTLAB_DEVICE_TOKEN is required.")
    if _is_placeholder_token(args.device_token):
        raise SystemExit(
            "The simulator needs a real device API token. Replace --device-token with the device api_token from the backend, "
            "or set PLANTLAB_DEVICE_TOKEN."
        )
    if args.device_id is None and not args.skip_register:
        raise SystemExit("--device-id or PLANTLAB_DEVICE_ID is required unless --skip-register is set.")

    nodes: list[SimulatorNodeConfig] = []
    base_id = _hardware_suffix(args.device_token)
    for device_number in range(1, max(1, args.devices) + 1):
        master_hardware_id = f"sim-master-{base_id}-{device_number:02d}"
        nodes.append(
            SimulatorNodeConfig(
                device_id=args.device_id,
                device_token=args.device_token,
                hardware_device_id=master_hardware_id,
                node_role="master",
                firmware_version=args.firmware_version,
                hardware_model=DEFAULT_MASTER_MODEL,
                schema_version=args.schema_version,
                display_name=f"Simulator master {device_number}",
                node_index=device_number,
                heartbeat_interval_seconds=args.heartbeat_interval,
                sensor_interval_seconds=args.sensor_interval,
                image_interval_seconds=args.image_interval,
                diagnostics_interval_seconds=args.diagnostics_interval,
                command_poll_interval_seconds=args.command_poll_interval,
                ota_step_delay_seconds=args.ota_step_delay,
                capabilities=["ota", "ambient_led", "camera_gateway", "diagnostics", "contract_polling"],
                scenarios=_normalize_scenarios(args.scenario),
                ota_failure_rate=_clamp_rate(args.ota_failure_rate),
                command_failure_rate=_clamp_rate(args.command_failure_rate),
                register_node=not args.skip_register,
            )
        )
        for camera_index in range(1, max(0, args.camera_nodes) + 1):
            nodes.append(
                SimulatorNodeConfig(
                    device_id=args.device_id,
                    device_token=args.device_token,
                    hardware_device_id=f"sim-camera-{base_id}-{device_number:02d}-{camera_index:02d}",
                    node_role="camera",
                    firmware_version=args.firmware_version,
                    hardware_model=DEFAULT_CAMERA_MODEL,
                    schema_version=args.schema_version,
                    display_name=f"Simulator camera {device_number}.{camera_index}",
                    node_index=camera_index,
                    heartbeat_interval_seconds=args.heartbeat_interval,
                    sensor_interval_seconds=args.sensor_interval,
                    image_interval_seconds=args.image_interval,
                    diagnostics_interval_seconds=args.diagnostics_interval,
                    command_poll_interval_seconds=args.command_poll_interval,
                    ota_step_delay_seconds=args.ota_step_delay,
                    capabilities=["camera", "image_capture", "diagnostics", "contract_polling"],
                    scenarios=_normalize_scenarios(args.scenario),
                    ota_failure_rate=_clamp_rate(args.ota_failure_rate),
                    command_failure_rate=_clamp_rate(args.command_failure_rate),
                    register_node=not args.skip_register,
                    parent_hardware_device_id=master_hardware_id,
                )
            )

    config = SimulatorConfig(
        base_url=_clean_base_url(args.base_url),
        nodes=nodes,
        run_seconds=args.run_seconds,
        log_level=args.log_level,
    )
    _validate_tokens(config.nodes)
    return config


def _load_config_file(path: Path, args: argparse.Namespace) -> SimulatorConfig:
    payload = json.loads(path.read_text(encoding="utf-8"))
    base_url = _clean_base_url(str(payload.get("base_url") or args.base_url or DEFAULT_BASE_URL))
    scenario_defaults = _normalize_scenarios(payload.get("scenarios") or args.scenario or [])
    nodes: list[SimulatorNodeConfig] = []

    raw_nodes = payload.get("nodes")
    if raw_nodes is None:
        raw_nodes = _expand_device_blocks(payload.get("devices") or [])
    if not isinstance(raw_nodes, list):
        raise ValueError("Simulator config must contain a nodes list or devices list.")

    for index, item in enumerate(raw_nodes, start=1):
        if not isinstance(item, dict):
            raise ValueError("Each simulator node must be an object.")
        node_role = str(item.get("node_role") or "master").strip().lower()
        nodes.append(
            SimulatorNodeConfig(
                device_id=_optional_int(item.get("device_id")),
                device_token=str(item.get("device_token") or payload.get("device_token") or args.device_token or "").strip(),
                hardware_device_id=str(item.get("hardware_device_id") or f"sim-{node_role}-{index:02d}").strip(),
                node_role=node_role,
                firmware_version=str(item.get("firmware_version") or args.firmware_version),
                hardware_model=str(item.get("hardware_model") or (DEFAULT_CAMERA_MODEL if node_role == "camera" else DEFAULT_MASTER_MODEL)),
                hardware_version=item.get("hardware_version"),
                schema_version=str(item.get("schema_version") or args.schema_version),
                display_name=item.get("display_name"),
                node_index=_optional_int(item.get("node_index")),
                heartbeat_interval_seconds=float(item.get("heartbeat_interval_seconds") or args.heartbeat_interval),
                sensor_interval_seconds=float(item.get("sensor_interval_seconds") or args.sensor_interval),
                image_interval_seconds=float(item.get("image_interval_seconds") or args.image_interval),
                diagnostics_interval_seconds=float(item.get("diagnostics_interval_seconds") or args.diagnostics_interval),
                command_poll_interval_seconds=float(item.get("command_poll_interval_seconds") or args.command_poll_interval),
                ota_step_delay_seconds=float(item.get("ota_step_delay_seconds") or args.ota_step_delay),
                capabilities=list(item.get("capabilities") or _default_capabilities(node_role)),
                scenarios=_normalize_scenarios(item.get("scenarios") or scenario_defaults),
                ota_failure_rate=_clamp_rate(float(item.get("ota_failure_rate") or args.ota_failure_rate)),
                command_failure_rate=_clamp_rate(float(item.get("command_failure_rate") or args.command_failure_rate)),
                register_node=bool(item.get("register_node", not args.skip_register)),
                parent_hardware_device_id=item.get("parent_hardware_device_id"),
            )
        )

    for node in nodes:
        if not node.device_token:
            raise ValueError(f"Node {node.hardware_device_id} is missing device_token.")
        if node.device_id is None and node.register_node:
            raise ValueError(f"Node {node.hardware_device_id} needs device_id when register_node is true.")

    return SimulatorConfig(
        base_url=base_url,
        nodes=nodes,
        run_seconds=_optional_float(payload.get("run_seconds")) if payload.get("run_seconds") is not None else args.run_seconds,
        log_level=str(payload.get("log_level") or args.log_level),
    )


def _expand_device_blocks(devices: list[dict[str, Any]]) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = []
    for device_index, device in enumerate(devices, start=1):
        token = device.get("device_token")
        device_id = device.get("device_id")
        master_id = device.get("hardware_device_id") or f"sim-master-{device_index:02d}"
        node_defaults = {
            "device_id": device_id,
            "device_token": token,
            "firmware_version": device.get("firmware_version"),
            "sensor_interval_seconds": device.get("sensor_interval_seconds"),
            "image_interval_seconds": device.get("image_interval_seconds"),
            "scenarios": _normalize_scenarios(device.get("scenarios") or []),
        }
        nodes.append(
            {
                **node_defaults,
                "hardware_device_id": master_id,
                "node_role": "master",
                "node_index": device_index,
                "display_name": device.get("display_name") or f"Simulator master {device_index}",
                "capabilities": device.get("capabilities") or _default_capabilities("master"),
            }
        )
        for camera_index in range(1, int(device.get("camera_nodes", 0)) + 1):
            nodes.append(
                {
                    **node_defaults,
                    "hardware_device_id": f"{master_id}-camera-{camera_index:02d}",
                    "node_role": "camera",
                    "node_index": camera_index,
                    "display_name": f"Simulator camera {device_index}.{camera_index}",
                    "parent_hardware_device_id": master_id,
                    "capabilities": _default_capabilities("camera"),
                }
            )
    return nodes


def _default_capabilities(node_role: str) -> list[str]:
    if node_role == "camera":
        return ["camera", "image_capture", "diagnostics", "contract_polling"]
    return ["ota", "ambient_led", "camera_gateway", "diagnostics", "contract_polling"]


def _clean_base_url(value: str) -> str:
    return str(value or DEFAULT_BASE_URL).strip().rstrip("/")


def _hardware_suffix(value: str) -> str:
    cleaned = "".join(char.lower() for char in value if char.isalnum())
    return cleaned[-6:] or "device"


def _optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    return int(value)


def _optional_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    return float(value)


def _clamp_rate(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _normalize_scenarios(values: Any) -> list[str]:
    if values is None:
        return []
    if isinstance(values, str):
        values = [values]
    normalized: list[str] = []
    unknown: list[str] = []
    for value in values:
        scenario = str(value or "").strip().lower()
        if not scenario or scenario == "normal":
            continue
        if scenario not in SUPPORTED_SCENARIOS:
            unknown.append(scenario)
            continue
        normalized.append(scenario)
    if unknown:
        supported = ", ".join(sorted(SUPPORTED_SCENARIOS))
        raise SystemExit(f"Unsupported simulator scenario(s): {', '.join(unknown)}. Supported scenarios: {supported}.")
    return normalized


def _validate_tokens(nodes: list[SimulatorNodeConfig]) -> None:
    for node in nodes:
        if _is_placeholder_token(node.device_token):
            raise SystemExit(
                f"Node {node.hardware_device_id} uses a placeholder device_token. "
                "Replace it with the real device api_token before starting the simulator."
            )


def _is_placeholder_token(value: str | None) -> bool:
    text = str(value or "").strip().lower()
    return text in PLACEHOLDER_TOKENS or text.startswith("replace-") or text.startswith("replace_")
