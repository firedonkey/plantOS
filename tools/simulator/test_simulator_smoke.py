from __future__ import annotations

import asyncio
import time
from typing import Any

import pytest

from tools.simulator.simulator import _friendly_api_error
from tools.simulator.simulator_config import SimulatorConfig, SimulatorNodeConfig, load_config_from_args, parse_args
from tools.simulator.simulator_events import SimulatorApiError
from tools.simulator.simulator_fake_media import make_plant_png
from tools.simulator.simulator_runtime import SimulatorRuntime


class FakeApiClient:
    def __init__(self, commands: list[dict[str, Any]]) -> None:
        self.commands = commands
        self.posts: list[tuple[str, dict[str, Any], str]] = []
        self.gets: list[tuple[str, dict[str, Any], str]] = []
        self.uploads: list[tuple[str, dict[str, Any], list[Any], str]] = []

    def post_json(self, path: str, payload: dict[str, Any], *, token: str) -> dict[str, Any]:
        self.posts.append((path, payload, token))
        return {"ok": True}

    def get_json(self, path: str, *, token: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self.gets.append((path, params or {}, token))
        if path == "/api/hardware/commands/poll":
            commands = self.commands
            self.commands = []
            return {"schema_version": "1.0", "commands": commands}
        return {}

    def post_multipart(self, path: str, *, token: str, fields: dict[str, Any], files: list[Any]) -> dict[str, Any]:
        self.uploads.append((path, fields, files, token))
        return {"id": 9001}


class FakeLegacyApiClient(FakeApiClient):
    def post_json(self, path: str, payload: dict[str, Any], *, token: str) -> dict[str, Any]:
        if path == "/api/hardware/diagnostics":
            raise SimulatorApiError("POST", path, 404, '{"detail":"Not Found"}')
        return super().post_json(path, payload, token=token)

    def get_json(self, path: str, *, token: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        if path == "/api/hardware/commands/poll":
            self.gets.append((path, params or {}, token))
            raise SimulatorApiError("GET", path, 404, '{"detail":"Not Found"}')
        if path == "/api/hardware/commands/pending":
            self.gets.append((path, params or {}, token))
            commands = self.commands
            self.commands = []
            return {"value": commands}
        return super().get_json(path, token=token, params=params)


def test_simulator_smoke_sends_heartbeat_polls_commands_reports_results_and_ota_statuses():
    fake = FakeApiClient(
        [
            _command("cmd_101", "SET_LIGHT_BRIGHTNESS", {"brightness_percent": 65}),
            _command(
                "cmd_102",
                "START_OTA",
                {
                    "target_version": "1.2.3",
                    "firmware_channel": "local",
                    "download_url": "https://example.test/firmware.bin",
                    "hardware_model": "esp32_master",
                },
            ),
        ]
    )
    runtime = SimulatorRuntime(
        SimulatorConfig(
            base_url="http://testserver",
            nodes=[
                SimulatorNodeConfig(
                    device_id=33,
                    device_token="token-owner",
                    hardware_device_id="sim-master-test",
                    node_role="master",
                    hardware_model="esp32_master",
                    capabilities=["ota", "ambient_led", "camera_gateway", "diagnostics", "contract_polling"],
                    ota_step_delay_seconds=0,
                )
            ],
        ),
        api=fake,
    )

    asyncio.run(runtime.run_once())

    post_paths = [path for path, _, _ in fake.posts]
    assert "/api/device-nodes/register" in post_paths
    assert "/api/hardware/heartbeat" in post_paths
    assert "/api/hardware/readings" in post_paths
    assert "/api/hardware/diagnostics" in post_paths
    assert "/api/hardware/ota/status" in post_paths
    assert any(path == "/api/hardware/commands/poll" for path, _, _ in fake.gets)

    command_results = [
        payload["payload"]
        for path, payload, _ in fake.posts
        if path.startswith("/api/hardware/commands/") and path.endswith("/result")
    ]
    assert ("cmd_101", "acked") in [(item["command_id"], item["status"]) for item in command_results]
    assert ("cmd_101", "completed") in [(item["command_id"], item["status"]) for item in command_results]
    assert ("cmd_102", "acked") in [(item["command_id"], item["status"]) for item in command_results]
    assert ("cmd_102", "completed") in [(item["command_id"], item["status"]) for item in command_results]

    ota_statuses = [
        payload["payload"]["status"]
        for path, payload, _ in fake.posts
        if path == "/api/hardware/ota/status"
    ]
    assert ota_statuses == [
        "preparing",
        "downloading",
        "downloading",
        "validating",
        "installing",
        "rebooting",
        "success",
    ]

    heartbeat = next(payload for path, payload, _ in fake.posts if path == "/api/hardware/heartbeat")
    assert heartbeat["message_type"] == "HEARTBEAT"
    assert heartbeat["payload"]["actuators"]["ambient_light"]["brightness_percent"] == 0

    reading = next(payload for path, payload, _ in fake.posts if path == "/api/hardware/readings")
    assert reading["hardware_device_id"] == "sim-master-test"
    assert isinstance(reading["temperature"], float)
    assert isinstance(reading["humidity"], float)
    assert reading["water_level_state"] == "ok"


def test_simulator_camera_uploads_fake_image():
    fake = FakeApiClient([])
    runtime = SimulatorRuntime(
        SimulatorConfig(
            base_url="http://testserver",
            nodes=[
                SimulatorNodeConfig(
                    device_id=33,
                    device_token="token-owner",
                    hardware_device_id="sim-camera-test",
                    node_role="camera",
                    hardware_model="xiao_esp32s3_camera",
                    capabilities=["camera", "image_capture", "diagnostics", "contract_polling"],
                )
            ],
        ),
        api=fake,
    )

    asyncio.run(runtime.run_once())

    assert len(fake.uploads) == 1
    path, fields, files, token = fake.uploads[0]
    assert path == "/api/image"
    assert token == "token-owner"
    assert fields == {"device_id": 33, "source_hardware_device_id": "sim-camera-test"}
    assert files[0].content_type == "image/png"
    assert files[0].data.startswith(b"\x89PNG\r\n\x1a\n")


def test_capture_command_uploads_fake_image_and_reports_image_id():
    fake = FakeApiClient([_command("cmd_201", "CAPTURE_IMAGE", {"reason": "manual"})])
    runtime = SimulatorRuntime(
        SimulatorConfig(
            base_url="http://testserver",
            nodes=[
                SimulatorNodeConfig(
                    device_id=33,
                    device_token="token-owner",
                    hardware_device_id="sim-master-test",
                    node_role="master",
                    hardware_model="esp32_master",
                    capabilities=["ota", "ambient_led", "camera_gateway", "diagnostics", "contract_polling"],
                )
            ],
        ),
        api=fake,
    )

    asyncio.run(runtime.run_once())

    assert len(fake.uploads) == 1
    command_results = [
        payload["payload"]
        for path, payload, _ in fake.posts
        if path == "/api/hardware/commands/201/result"
    ]
    completed = next(item for item in command_results if item["status"] == "completed")
    assert completed["result"]["image_id"] == 9001


def test_fake_images_have_visible_per_capture_variation():
    first = make_plant_png(seed=123, frame_index=1)
    second = make_plant_png(seed=123, frame_index=2)

    assert first.startswith(b"\x89PNG\r\n\x1a\n")
    assert second.startswith(b"\x89PNG\r\n\x1a\n")
    assert first != second


def test_missing_and_placeholder_tokens_fail_fast(monkeypatch):
    monkeypatch.delenv("PLANTLAB_DEVICE_TOKEN", raising=False)
    monkeypatch.delenv("PLANTLAB_DEVICE_ID", raising=False)

    with pytest.raises(SystemExit, match="--device-token"):
        load_config_from_args(parse_args([]))

    with pytest.raises(SystemExit, match="real device API token"):
        load_config_from_args(parse_args(["--device-id", "1", "--device-token", "replace-with-device-api-token"]))


def test_low_memory_scenario_reports_critical_diagnostics():
    runtime = SimulatorRuntime(
        SimulatorConfig(
            nodes=[
                SimulatorNodeConfig(
                    device_id=33,
                    device_token="token-owner",
                    hardware_device_id="sim-master-test",
                    node_role="master",
                    scenarios=["low_memory"],
                )
            ]
        )
    )
    node = runtime.nodes[0]

    diagnostics = node.diagnostics_payload()

    assert diagnostics["status"] == "degraded"
    assert diagnostics["severity"] == "critical"
    assert diagnostics["last_error_code"] == "LOW_MEMORY"
    assert diagnostics["subsystem_statuses"]["memory"] == "error"


def test_camera_flapping_scenario_suppresses_camera_heartbeat_when_offline():
    runtime = SimulatorRuntime(
        SimulatorConfig(
            nodes=[
                SimulatorNodeConfig(
                    device_id=33,
                    device_token="token-owner",
                    hardware_device_id="sim-camera-test",
                    node_role="camera",
                    scenarios=["camera_flapping"],
                )
            ]
        )
    )
    node = runtime.nodes[0]
    node.boot_time_monotonic = time.monotonic() - 13

    assert node.node_status() == "offline"
    assert node.should_transmit_now("heartbeat") is False


def test_friendly_backend_errors_are_actionable():
    auth_message = _friendly_api_error(SimulatorApiError("POST", "/api/hardware/heartbeat", 401, "nope"))
    network_message = _friendly_api_error(SimulatorApiError("POST", "/api/hardware/heartbeat", None, "Connection refused"))

    assert "device api_token" in auth_message
    assert "docker exec" in auth_message
    assert "Could not reach" in network_message
    assert "docker compose" in network_message


def test_simulator_continues_when_optional_contract_endpoints_are_missing():
    fake = FakeLegacyApiClient([])
    runtime = SimulatorRuntime(
        SimulatorConfig(
            base_url="http://testserver",
            nodes=[
                SimulatorNodeConfig(
                    device_id=33,
                    device_token="token-owner",
                    hardware_device_id="sim-master-test",
                    node_role="master",
                    hardware_model="esp32_master",
                    capabilities=["ota", "ambient_led", "camera_gateway", "diagnostics", "contract_polling"],
                )
            ],
        ),
        api=fake,
    )

    asyncio.run(runtime.run_once())

    post_paths = [path for path, _, _ in fake.posts]
    assert "/api/device-nodes/register" in post_paths
    assert "/api/hardware/heartbeat" in post_paths
    assert "/api/hardware/diagnostics" not in post_paths


def test_simulator_uses_legacy_pending_commands_when_contract_poll_is_missing():
    fake = FakeLegacyApiClient(
        [
            {
                "id": 77,
                "device_id": 33,
                "target": "light",
                "action": "set_intensity",
                "value": "65",
                "status": "in_progress",
                "message": None,
                "light_on": None,
                "light_intensity_percent": None,
                "pump_on": None,
                "created_at": "2026-05-27T12:00:00Z",
                "sent_at": "2026-05-27T12:00:01Z",
                "completed_at": None,
            }
        ]
    )
    runtime = SimulatorRuntime(
        SimulatorConfig(
            base_url="http://testserver",
            nodes=[
                SimulatorNodeConfig(
                    device_id=33,
                    device_token="token-owner",
                    hardware_device_id="sim-master-test",
                    node_role="master",
                    hardware_model="esp32_master",
                    capabilities=["ota", "ambient_led", "camera_gateway", "diagnostics", "contract_polling"],
                )
            ],
        ),
        api=fake,
    )

    asyncio.run(runtime.run_once())

    assert any(path == "/api/hardware/commands/pending" for path, _, _ in fake.gets)
    command_results = [
        payload
        for path, payload, _ in fake.posts
        if path == "/api/hardware/commands/77/result"
    ]
    assert command_results == [
        {
            "status": "completed",
            "message": "Light brightness set to 65%.",
            "light_on": True,
            "light_intensity_percent": 65,
        }
    ]


def _command(command_id: str, command_type: str, params: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "message_id": f"cmdmsg_{command_id}",
        "device_id": 33,
        "hardware_device_id": "sim-master-test",
        "node_role": "master",
        "message_type": "COMMAND",
        "sent_at": "2026-05-27T12:00:00Z",
        "payload": {
            "command_id": command_id,
            "command_type": command_type,
            "target": {
                "node_role": "master",
                "hardware_device_id": "sim-master-test",
            },
            "params": params,
            "timeout_ms": 120000,
            "priority": "normal",
        },
    }
