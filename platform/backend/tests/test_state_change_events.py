from __future__ import annotations

from copy import deepcopy

from app.api.deps import get_current_user, get_optional_current_user
from app.main import app
from app.models import DeviceDiagnosticEvent, DeviceNode
from tests.test_hardware_api import build_client_with_devices, teardown_overrides


def test_actuator_state_change_emits_once_for_meaningful_change():
    client, device_id, _ = build_client_with_devices()
    try:
        _add_node(client, device_id)
        _use_device_token_auth()

        _post_heartbeat(client, _heartbeat(device_id=device_id, light_enabled=False, brightness=0))
        _post_heartbeat(client, _heartbeat(device_id=device_id, light_enabled=True, brightness=65))
        _post_heartbeat(client, _heartbeat(device_id=device_id, light_enabled=True, brightness=65))

        events = _events(client, "ACTUATOR_STATE_CHANGED")
        assert len(events) == 1
        data = events[0].metadata_json["data"]
        assert data["actuator"] == "grow_light"
        assert data["previous"] == {"enabled": False, "brightness_percent": 0}
        assert data["current"] == {"enabled": True, "brightness_percent": 65}
    finally:
        teardown_overrides()


def test_camera_node_connection_state_changes_are_emitted():
    client, device_id, _ = build_client_with_devices()
    try:
        _add_node(client, device_id)
        _use_device_token_auth()

        _post_heartbeat(client, _heartbeat(device_id=device_id, camera_node_status="online"))
        _post_heartbeat(client, _heartbeat(device_id=device_id, camera_node_status="offline"))
        _post_heartbeat(client, _heartbeat(device_id=device_id, camera_node_status="online"))

        assert [event.event_type for event in _events(client, "CAMERA_NODE_DISCONNECTED")] == ["CAMERA_NODE_DISCONNECTED"]
        assert [event.event_type for event in _events(client, "CAMERA_NODE_CONNECTED")] == ["CAMERA_NODE_CONNECTED"]
    finally:
        teardown_overrides()


def test_wifi_signal_uses_hysteresis_and_does_not_spam():
    client, device_id, _ = build_client_with_devices()
    try:
        _add_node(client, device_id)
        _use_device_token_auth()

        _post_heartbeat(client, _heartbeat(device_id=device_id, wifi_rssi_dbm=-58))
        _post_heartbeat(client, _heartbeat(device_id=device_id, wifi_rssi_dbm=-82))
        _post_heartbeat(client, _heartbeat(device_id=device_id, wifi_rssi_dbm=-85))
        _post_heartbeat(client, _heartbeat(device_id=device_id, wifi_rssi_dbm=-75))
        _post_heartbeat(client, _heartbeat(device_id=device_id, wifi_rssi_dbm=-60))

        degraded = _events(client, "WIFI_SIGNAL_DEGRADED")
        recovered = _events(client, "WIFI_SIGNAL_RECOVERED")
        assert len(degraded) == 1
        assert degraded[0].metadata_json["data"]["previous"] == -58
        assert degraded[0].metadata_json["data"]["current"] == -82
        assert len(recovered) == 1
        assert recovered[0].metadata_json["data"]["previous"] == -75
        assert recovered[0].metadata_json["data"]["current"] == -60
    finally:
        teardown_overrides()


def test_heartbeat_node_status_change_emits_device_health_changed():
    client, device_id, _ = build_client_with_devices()
    try:
        _add_node(client, device_id)
        _use_device_token_auth()

        _post_heartbeat(client, _heartbeat(device_id=device_id, node_status="online"))
        _post_heartbeat(client, _heartbeat(device_id=device_id, node_status="degraded"))

        events = _events(client, "DEVICE_HEALTH_CHANGED")
        assert len(events) == 1
        assert events[0].severity == "warning"
        assert events[0].metadata_json["data"]["previous"] == "online"
        assert events[0].metadata_json["data"]["current"] == "degraded"
    finally:
        teardown_overrides()


def test_command_poll_stale_emits_once_when_threshold_crossed():
    client, device_id, _ = build_client_with_devices()
    try:
        _add_node(client, device_id)
        _use_device_token_auth()

        _post_heartbeat(client, _heartbeat(device_id=device_id, command_poll_stale_seconds=60))
        _post_heartbeat(
            client,
            _heartbeat(
                device_id=device_id,
                command_poll_stale_seconds=305,
                last_command_poll_status="error",
                last_command_poll_error="connection timed out",
                last_command_poll_latency_ms=5000,
            ),
        )
        _post_heartbeat(
            client,
            _heartbeat(
                device_id=device_id,
                command_poll_stale_seconds=420,
                last_command_poll_status="error",
                last_command_poll_error="connection timed out",
                last_command_poll_latency_ms=5000,
            ),
        )

        events = _events(client, "COMMAND_POLL_STALE")
        assert len(events) == 1
        assert events[0].severity == "warning"
        data = events[0].metadata_json["data"]
        assert data["threshold_seconds"] == 300
        assert data["previous_stale_seconds"] == 60
        assert data["current_stale_seconds"] == 305
        assert data["last_command_poll_status"] == "error"
        assert data["last_command_poll_error"] == "connection timed out"
        assert data["last_command_poll_latency_ms"] == 5000
    finally:
        teardown_overrides()


def test_diagnostics_status_and_severity_change_emits_device_health_changed():
    client, device_id, _ = build_client_with_devices()
    try:
        _add_node(client, device_id)
        _use_device_token_auth()

        _post_diagnostics(client, _diagnostics(device_id=device_id, status="online", severity="info"))
        _post_diagnostics(client, _diagnostics(device_id=device_id, status="degraded", severity="warning"))

        events = _events(client, "DEVICE_HEALTH_CHANGED")
        assert len(events) == 1
        assert events[0].severity == "warning"
        assert events[0].metadata_json["data"]["source"] == "diagnostics"
        assert events[0].metadata_json["data"]["previous"] == {"status": "online", "severity": "info"}
        assert events[0].metadata_json["data"]["current"] == {"status": "degraded", "severity": "warning"}
    finally:
        teardown_overrides()


def test_ota_status_change_emits_once_and_progress_only_does_not_spam():
    client, device_id, _ = build_client_with_devices()
    try:
        _add_node(client, device_id)
        _use_device_token_auth()

        first = client.post(
            "/api/hardware/ota/status",
            json={
                "hardware_device_id": "master-01",
                "status": "downloading",
                "target_version": "1.2.0",
                "progress": 10,
            },
            headers={"X-Device-Token": "token-owner"},
        )
        assert first.status_code == 200
        progress = client.post(
            "/api/hardware/ota/status",
            json={
                "hardware_device_id": "master-01",
                "status": "downloading",
                "target_version": "1.2.0",
                "progress": 42,
            },
            headers={"X-Device-Token": "token-owner"},
        )
        assert progress.status_code == 200

        events = _events(client, "OTA_STATE_CHANGED")
        assert len(events) == 1
        assert events[0].metadata_json["data"]["previous"] == "idle"
        assert events[0].metadata_json["data"]["current"] == "downloading"
    finally:
        teardown_overrides()


def test_timeline_summaries_handle_state_change_events():
    client, device_id, _ = build_client_with_devices()
    try:
        with client.testing_session_local() as session:
            session.add_all(
                [
                    DeviceDiagnosticEvent(
                        device_id=device_id,
                        hardware_device_id="master-01",
                        event_type="ACTUATOR_STATE_CHANGED",
                        severity="info",
                        metadata_json={
                            "node_role": "master",
                            "data": {
                                "actuator": "grow_light",
                                "previous": {"enabled": False, "brightness_percent": 0},
                                "current": {"enabled": True, "brightness_percent": 65},
                            },
                        },
                    ),
                    DeviceDiagnosticEvent(
                        device_id=device_id,
                        hardware_device_id="master-01",
                        event_type="WIFI_SIGNAL_DEGRADED",
                        severity="warning",
                        metadata_json={
                            "node_role": "master",
                            "data": {"previous": -58, "current": -82},
                        },
                    ),
                    DeviceDiagnosticEvent(
                        device_id=device_id,
                        hardware_device_id="master-01",
                        event_type="COMMAND_POLL_STALE",
                        severity="warning",
                        metadata_json={
                            "node_role": "master",
                            "data": {"current_stale_seconds": 305},
                        },
                    ),
                ]
            )
            session.commit()

        response = client.get(f"/api/devices/{device_id}/timeline")

        assert response.status_code == 200
        summaries = [event["summary"] for event in response.json()["events"]]
        assert "Grow light changed: off -> 65%" in summaries
        assert "Wi-Fi signal degraded: -58 -> -82 dBm" in summaries
        assert "Command polling stale for 305s" in summaries
    finally:
        teardown_overrides()


def _add_node(client, device_id: int) -> None:
    with client.testing_session_local() as session:
        session.add(
            DeviceNode(
                device_id=device_id,
                hardware_device_id="master-01",
                node_role="master",
                display_name="Master",
                status="offline",
                software_version="1.0.0",
            )
        )
        session.commit()


def _use_device_token_auth() -> None:
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_optional_current_user, None)


def _post_heartbeat(client, payload: dict) -> None:
    response = client.post("/api/hardware/heartbeat", json=payload, headers={"X-Device-Token": "token-owner"})
    assert response.status_code == 200


def _post_diagnostics(client, payload: dict) -> None:
    response = client.post("/api/hardware/diagnostics", json=payload, headers={"X-Device-Token": "token-owner"})
    assert response.status_code == 200


def _events(client, event_type: str) -> list[DeviceDiagnosticEvent]:
    with client.testing_session_local() as session:
        return list(
            session.query(DeviceDiagnosticEvent)
            .filter(DeviceDiagnosticEvent.event_type == event_type)
            .order_by(DeviceDiagnosticEvent.id)
            .all()
        )


def _heartbeat(
    *,
    device_id: int,
    node_status: str = "online",
    wifi_rssi_dbm: int = -58,
    light_enabled: bool = False,
    brightness: int = 0,
    camera_node_status: str = "online",
    ota_status: str = "idle",
    command_poll_stale_seconds: int | None = None,
    last_command_poll_status: str | None = None,
    last_command_poll_error: str | None = None,
    last_command_poll_latency_ms: int | None = None,
) -> dict:
    payload = {
        "schema_version": "1.0",
        "message_id": "evt_test_heartbeat",
        "device_id": device_id,
        "hardware_device_id": "master-01",
        "node_role": "master",
        "message_type": "HEARTBEAT",
        "sent_at": "2026-05-27T12:00:00Z",
        "payload": {
            "uptime_seconds": 123,
            "wifi_rssi_dbm": wifi_rssi_dbm,
            "free_heap_bytes": 180000,
            "node_status": node_status,
            "firmware_version": "1.0.0",
            "hardware_model": "esp32_master",
            "capabilities": ["ota", "grow_light", "camera_gateway"],
            "actuators": {
                "grow_light": {
                    "enabled": light_enabled,
                    "brightness_percent": brightness,
                }
            },
            "runtime": {
                "capture_interval_seconds": 3600,
                "ota_status": ota_status,
                "provisioning_status": "provisioned",
                "camera_node_status": camera_node_status,
            },
        },
    }
    payload = deepcopy(payload)
    runtime = payload["payload"]["runtime"]
    if command_poll_stale_seconds is not None:
        runtime["command_poll_stale_seconds"] = command_poll_stale_seconds
    if last_command_poll_status is not None:
        runtime["last_command_poll_status"] = last_command_poll_status
    if last_command_poll_error is not None:
        runtime["last_command_poll_error"] = last_command_poll_error
    if last_command_poll_latency_ms is not None:
        runtime["last_command_poll_latency_ms"] = last_command_poll_latency_ms
    return payload


def _diagnostics(*, device_id: int, status: str, severity: str) -> dict:
    return {
        "schema_version": "1.0",
        "message_id": "evt_test_diagnostics",
        "device_id": device_id,
        "hardware_device_id": "master-01",
        "node_role": "master",
        "message_type": "DIAGNOSTICS",
        "sent_at": "2026-05-27T12:00:00Z",
        "payload": {
            "status": status,
            "severity": severity,
            "error_counters": {},
            "subsystem_statuses": {
                "wifi": status,
            },
        },
    }
