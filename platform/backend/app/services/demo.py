from __future__ import annotations

import math
import struct
import zlib
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from threading import Lock

from fastapi import Request
from fastapi.responses import Response

from app.models import CommandAction, CommandStatus, CommandTarget
from app.schemas.commands import CommandCreate, CommandRead, DeviceCommandEnvelopeRead, LightCommandRequest
from app.schemas.devices import (
    DeviceHardwareHealthRead,
    DeviceHealthCommandRead,
    DeviceHealthNodeRead,
    DeviceRead,
    DeviceSummaryImageRead,
    DeviceSummaryRead,
    DeviceSummaryReadingRead,
    DeviceTimelapseFrameRead,
    DeviceTimelapseRead,
)
from app.schemas.diagnostics import (
    DeviceDiagnosticEventRead,
    DeviceDiagnosticSnapshotRead,
    DeviceDiagnosticsRead,
    DeviceTimelineEventRead,
    DeviceTimelineRead,
)
from app.schemas.readings import SensorReadingRead


DEMO_DEVICE_ID = 600001
DEMO_MASTER_ID = "demo-master-64e0"
DEMO_CAMERA_ID = "demo-camera-1c1d"
DEMO_IMAGE_ID_BASE = 610000
DEMO_COMMAND_ID_BASE = 620000
DEMO_EVENT_ID_BASE = 630000
DEMO_READING_ID_BASE = 640000
DEMO_PLANT_TYPE = "Genovese basil"
DEMO_DEVICE_NAME = "PlantLab Demo Garden"
DEMO_LOCATION = "Sunny kitchen shelf"
DEMO_AGE_DAYS = 60


@dataclass
class DemoCommand:
    id: int
    target: str
    action: str
    value: str | None
    message: str
    created_at: datetime


@dataclass
class DemoTimelineEvent:
    id: int
    event_type: str
    severity: str
    occurred_at: datetime
    summary: str
    hardware_device_id: str | None = None
    node_role: str | None = None
    correlation_id: str | None = None
    code: str | None = None
    message: str | None = None
    data: dict = field(default_factory=dict)


@dataclass
class DemoState:
    light_on: bool = True
    light_intensity_percent: int = 72
    next_command_id: int = DEMO_COMMAND_ID_BASE
    next_event_id: int = DEMO_EVENT_ID_BASE
    extra_images: list[tuple[int, datetime]] = field(default_factory=list)
    commands: list[DemoCommand] = field(default_factory=list)
    events: list[DemoTimelineEvent] = field(default_factory=list)


_states: dict[int, DemoState] = {}
_state_lock = Lock()
_capture_day_offsets = [-60, -54, -48, -42, -36, -30, -24, -18, -14, -10, -7, -6, -5, -4, -3, -2, -1, 0]


def is_demo_user(user: object) -> bool:
    return bool(getattr(user, "is_demo_user", False))


def is_demo_device_id(device_id: int) -> bool:
    return device_id == DEMO_DEVICE_ID


def demo_state_for_user(user_id: int | None) -> DemoState:
    key = int(user_id or 0)
    with _state_lock:
        state = _states.get(key)
        if state is None:
            state = DemoState()
            _seed_state(state)
            _states[key] = state
        return state


def reset_demo_states_for_tests() -> None:
    with _state_lock:
        _states.clear()


def demo_device_read(request: Request, user_id: int | None) -> DeviceRead:
    state = demo_state_for_user(user_id)
    latest_reading = _latest_reading(state)
    latest_image = _image_read(request, _image_specs(state)[-1])
    hardware_health = _hardware_health(state)
    return DeviceRead(
        id=DEMO_DEVICE_ID,
        name=DEMO_DEVICE_NAME,
        location=DEMO_LOCATION,
        plant_type=DEMO_PLANT_TYPE,
        api_token=None,
        created_at=_started_at(),
        status="online",
        current_light_on=state.light_on,
        current_light_intensity_percent=state.light_intensity_percent,
        current_pump_on=False,
        latest_reading=latest_reading,
        latest_image=latest_image,
        node_summary=_node_summary(state),
        hardware_health=hardware_health,
    )


def demo_device_summary(request: Request, user_id: int | None) -> DeviceSummaryRead:
    state = demo_state_for_user(user_id)
    latest_image = _image_read(request, _image_specs(state)[-1])
    return DeviceSummaryRead(
        id=DEMO_DEVICE_ID,
        name=DEMO_DEVICE_NAME,
        location=DEMO_LOCATION,
        plant_type=DEMO_PLANT_TYPE,
        current_light_on=state.light_on,
        current_light_intensity_percent=state.light_intensity_percent,
        current_pump_on=False,
        latest_reading=_latest_reading(state),
        latest_image=latest_image,
        node_summary=_node_summary(state),
        hardware_health=_hardware_health(state),
    )


def demo_readings(
    user_id: int | None,
    *,
    limit: int,
    since: datetime | None,
    until: datetime | None,
    order: str,
) -> list[SensorReadingRead]:
    state = demo_state_for_user(user_id)
    end = _as_utc(until) if until is not None else _now()
    start = _as_utc(since) if since is not None else end - timedelta(days=1)
    if start >= end:
        start = end - timedelta(hours=1)

    window_seconds = max(1, int((end - start).total_seconds()))
    target_count = min(max(limit, 1), max(2, min(limit, 240)))
    step = max(1, window_seconds // max(target_count - 1, 1))
    rows: list[SensorReadingRead] = []
    current = start
    index = 0
    while current <= end and len(rows) < target_count:
        rows.append(_reading_at(state, current, DEMO_READING_ID_BASE + index))
        current += timedelta(seconds=step)
        index += 1
    if rows and rows[-1].timestamp < end and len(rows) < limit:
        rows.append(_reading_at(state, end, DEMO_READING_ID_BASE + index))
    if order == "newest":
        rows.reverse()
    return rows[:limit]


def demo_images(request: Request, user_id: int | None, *, limit: int) -> list[DeviceSummaryImageRead]:
    state = demo_state_for_user(user_id)
    specs = list(reversed(_image_specs(state)))[:limit]
    return [_image_read(request, spec) for spec in specs]


def demo_latest_image(request: Request, user_id: int | None) -> DeviceSummaryImageRead:
    state = demo_state_for_user(user_id)
    return _image_read(request, _image_specs(state)[-1])


def demo_timelapse(
    request: Request,
    user_id: int | None,
    *,
    days: int,
    interval_minutes: int,
    max_frames: int,
    target_duration_seconds: int,
    playback_frame_ms: int | None = None,
) -> DeviceTimelapseRead:
    state = demo_state_for_user(user_id)
    now = _now()
    window_start = now - timedelta(days=days)
    specs = [spec for spec in _image_specs(state) if spec[1] >= window_start]
    if not specs:
        specs = _image_specs(state)[-1:]
    selected = specs[-max_frames:]
    frames = [
        DeviceTimelapseFrameRead(
            id=spec[0],
            content_url=_image_url(request, spec[0]),
            timestamp=spec[1],
            source_hardware_device_id=DEMO_CAMERA_ID,
        )
        for spec in selected
    ]
    return DeviceTimelapseRead(
        device_id=DEMO_DEVICE_ID,
        window_start=window_start,
        window_end=now,
        interval_minutes=interval_minutes,
        target_duration_seconds=target_duration_seconds,
        playback_frame_ms=playback_frame_ms or 450,
        total_image_count=len(specs),
        frame_count=len(frames),
        frames=frames,
    )


def demo_diagnostics(user_id: int | None, *, events_limit: int) -> DeviceDiagnosticsRead:
    state = demo_state_for_user(user_id)
    return DeviceDiagnosticsRead(
        snapshots=[_master_snapshot(), _camera_snapshot()],
        recent_events=_diagnostic_events(state, events_limit),
    )


def demo_timeline(
    user_id: int | None,
    *,
    limit: int,
    before: datetime | None,
    after: datetime | None,
    event_types: list[str] | None,
    severities: list[str] | None,
    node_role: str | None,
    correlation_id: str | None,
) -> DeviceTimelineRead:
    state = demo_state_for_user(user_id)
    events = _timeline_events(state)
    before_utc = _as_utc(before) if before is not None else None
    after_utc = _as_utc(after) if after is not None else None
    event_type_set = {item.upper() for item in event_types or []}
    severity_set = {item.lower() for item in severities or []}
    rows = []
    for event in events:
        if before_utc is not None and event.occurred_at >= before_utc:
            continue
        if after_utc is not None and event.occurred_at < after_utc:
            continue
        if event_type_set and event.event_type.upper() not in event_type_set:
            continue
        if severity_set and event.severity.lower() not in severity_set:
            continue
        if node_role and event.node_role != node_role:
            continue
        if correlation_id and event.correlation_id != correlation_id:
            continue
        rows.append(_timeline_read(event))
    limited = rows[:limit]
    return DeviceTimelineRead(
        events=limited,
        next_before=limited[-1].occurred_at if len(limited) == limit else None,
    )


def demo_commands(user_id: int | None, *, limit: int = 20) -> list[CommandRead]:
    state = demo_state_for_user(user_id)
    return [_command_read(command) for command in state.commands[:limit]]


def demo_light_command(user_id: int | None, payload: LightCommandRequest) -> DeviceCommandEnvelopeRead:
    state = demo_state_for_user(user_id)
    if payload.intensity_percent is not None:
        state.light_on = payload.intensity_percent > 0
        state.light_intensity_percent = payload.intensity_percent
        action = CommandAction.SET_INTENSITY
        value = str(payload.intensity_percent)
        message = f"Demo grow-light brightness set to {payload.intensity_percent}%."
        summary = f"SET_GROW_LIGHT_BRIGHTNESS completed at {payload.intensity_percent}%"
    else:
        state.light_on = payload.state == "on"
        action = CommandAction.ON if state.light_on else CommandAction.OFF
        value = None
        message = f"Demo grow light turned {'on' if state.light_on else 'off'}."
        summary = f"Grow light turned {'on' if state.light_on else 'off'}"
    return _record_simulated_command(
        state,
        target=CommandTarget.GROW_LIGHT,
        action=action,
        value=value,
        command_name="grow_light",
        message=message,
        event_summary=summary,
        hardware_device_id=DEMO_MASTER_ID,
        node_role="master",
        data={
            "demo": True,
            "light_on": state.light_on,
            "light_intensity_percent": state.light_intensity_percent,
        },
    )


def demo_capture_command(user_id: int | None) -> DeviceCommandEnvelopeRead:
    state = demo_state_for_user(user_id)
    next_image_id = DEMO_IMAGE_ID_BASE + 1000 + len(state.extra_images)
    state.extra_images.append((next_image_id, _now()))
    return _record_simulated_command(
        state,
        target=CommandTarget.CAMERA,
        action=CommandAction.CAPTURE,
        value=None,
        command_name="capture",
        message="Demo capture completed and added to the image gallery.",
        event_summary="Demo image captured and uploaded",
        hardware_device_id=DEMO_CAMERA_ID,
        node_role="camera",
        data={"demo": True, "image_id": next_image_id, "upload_reason": "manual"},
    )


def demo_diagnostics_command(user_id: int | None, payload: CommandCreate) -> CommandRead:
    state = demo_state_for_user(user_id)
    now = _now()
    command_id = state.next_command_id
    state.next_command_id += 1
    command = DemoCommand(
        id=command_id,
        target=CommandTarget.DIAGNOSTICS.value,
        action=CommandAction.REQUEST.value,
        value=payload.value,
        message="Demo diagnostics refreshed.",
        created_at=now,
    )
    state.commands.insert(0, command)
    event_id = state.next_event_id
    state.next_event_id += 1
    state.events.insert(
        0,
        DemoTimelineEvent(
            id=event_id,
            event_type="DIAGNOSTICS_RECEIVED",
            severity="info",
            occurred_at=now,
            summary="Diagnostics refreshed",
            hardware_device_id=DEMO_MASTER_ID,
            node_role="master",
            correlation_id=f"demo_cmd_{command_id}",
            data={"demo": True, "status": "healthy", "command_id": f"demo_cmd_{command_id}"},
        ),
    )
    return _command_read(command)


def demo_image_response(image_id: int) -> Response:
    return Response(
        content=_png_for_image(image_id),
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=86400"},
    )


def demo_forbidden_message(action: str) -> str:
    return f"Demo accounts cannot {action} real PlantLab devices or account data."


def _seed_state(state: DemoState) -> None:
    now = _now()
    state.commands = [
        DemoCommand(
            id=DEMO_COMMAND_ID_BASE - 1,
            target=CommandTarget.GROW_LIGHT.value,
            action=CommandAction.SET_INTENSITY.value,
            value="72",
            message="Demo grow-light schedule applied.",
            created_at=now - timedelta(minutes=18),
        )
    ]
    state.events = [
        DemoTimelineEvent(
            id=DEMO_EVENT_ID_BASE - 1,
            event_type="LIGHT_SCHEDULE_APPLIED",
            severity="info",
            occurred_at=now - timedelta(hours=2),
            summary="Morning grow-light schedule started",
            hardware_device_id=DEMO_MASTER_ID,
            node_role="master",
            data={"schedule": "07:00-21:00", "brightness_percent": 72},
        ),
        DemoTimelineEvent(
            id=DEMO_EVENT_ID_BASE - 2,
            event_type="WATERING_EVENT",
            severity="info",
            occurred_at=now - timedelta(days=1, hours=3),
            summary="Water reservoir topped off",
            hardware_device_id=DEMO_MASTER_ID,
            node_role="master",
            data={"water_level_state": "ok", "volume_ml": 420},
        ),
        DemoTimelineEvent(
            id=DEMO_EVENT_ID_BASE - 3,
            event_type="GROWTH_MILESTONE",
            severity="info",
            occurred_at=_started_at() + timedelta(days=44),
            summary="New leaf cluster detected",
            hardware_device_id=DEMO_CAMERA_ID,
            node_role="camera",
            data={"plant_age_days": 44, "observation": "canopy filled the planter opening"},
        ),
    ]


def _record_simulated_command(
    state: DemoState,
    *,
    target: CommandTarget,
    action: CommandAction,
    value: str | None,
    command_name: str,
    message: str,
    event_summary: str,
    hardware_device_id: str,
    node_role: str,
    data: dict,
) -> DeviceCommandEnvelopeRead:
    now = _now()
    command_id = state.next_command_id
    state.next_command_id += 1
    command = DemoCommand(
        id=command_id,
        target=target.value,
        action=action.value,
        value=value,
        message=message,
        created_at=now,
    )
    state.commands.insert(0, command)
    event_id = state.next_event_id
    state.next_event_id += 1
    state.events.insert(
        0,
        DemoTimelineEvent(
            id=event_id,
            event_type="COMMAND_COMPLETED",
            severity="info",
            occurred_at=now,
            summary=event_summary,
            hardware_device_id=hardware_device_id,
            node_role=node_role,
            correlation_id=f"demo_cmd_{command_id}",
            data={"command_id": f"demo_cmd_{command_id}", "target": target.value, "action": action.value, **data},
        ),
    )
    return DeviceCommandEnvelopeRead(
        status="accepted",
        device_id=DEMO_DEVICE_ID,
        command=command_name,
        action=action.value,
        queued=False,
        message=message,
        command_id=command_id,
        command_status=CommandStatus.COMPLETED,
        created_at=now,
        value=value,
    )


def _latest_reading(state: DemoState) -> DeviceSummaryReadingRead:
    reading = _reading_at(state, _now(), DEMO_READING_ID_BASE)
    return DeviceSummaryReadingRead(
        timestamp=reading.timestamp,
        moisture=reading.moisture,
        temperature=reading.temperature,
        humidity=reading.humidity,
        water_temperature_c=reading.water_temperature_c,
        water_level_raw=reading.water_level_raw,
        water_level_state=reading.water_level_state,
        light_on=reading.light_on,
        light_intensity_percent=reading.light_intensity_percent,
        pump_on=reading.pump_on,
        pump_status=reading.pump_status,
    )


def _reading_at(state: DemoState, timestamp: datetime, reading_id: int) -> SensorReadingRead:
    timestamp = _as_utc(timestamp)
    hours = timestamp.timestamp() / 3600
    day_age = max(0.0, (timestamp - _started_at()).total_seconds() / 86400)
    water_raw = int(36600 - (day_age % 4.5) * 360 + math.sin(hours / 3.1) * 95)
    return SensorReadingRead(
        id=reading_id,
        device_id=DEMO_DEVICE_ID,
        timestamp=timestamp,
        moisture=64.0 + math.sin(hours / 7.5) * 2.4,
        temperature=23.4 + math.sin(hours / 2.6) * 0.7,
        humidity=58.0 + math.cos(hours / 3.4) * 2.8,
        water_temperature_c=21.2 + math.sin(hours / 5.2) * 0.4,
        water_level_raw=water_raw,
        water_level_state="ok" if water_raw >= 34200 else "low",
        light_on=state.light_on,
        light_intensity_percent=state.light_intensity_percent if state.light_on else 0,
        pump_on=False,
        pump_status="idle",
    )


def _hardware_health(state: DemoState) -> DeviceHardwareHealthRead:
    now = _now()
    last_command = _command_read(state.commands[0]) if state.commands else None
    health_command = None
    if last_command is not None:
        health_command = DeviceHealthCommandRead(
            id=last_command.id,
            target=last_command.target,
            action=last_command.action,
            status=last_command.status,
            message=last_command.message,
            created_at=last_command.created_at,
            completed_at=last_command.completed_at,
            sent_at=last_command.sent_at,
            timestamp=last_command.completed_at or last_command.created_at,
        )
    return DeviceHardwareHealthRead(
        overall_status="online",
        master_status="online",
        master_online=True,
        primary=_health_node(
            hardware_device_id=DEMO_MASTER_ID,
            node_role="master",
            display_name="Demo master",
            firmware_version="0.1.6",
            model="PlantLab ESP32-S3",
            last_seen_at=now - timedelta(seconds=22),
            diagnostics=_master_snapshot(),
            capabilities={"light_intensity_control": True, "light_control_modes": ["on_off", "intensity"], "diagnostics": True},
        ),
        cameras=[
            _health_node(
                hardware_device_id=DEMO_CAMERA_ID,
                node_role="camera",
                display_name="Demo camera",
                firmware_version="0.1.8",
                model="XIAO ESP32S3 Sense",
                last_seen_at=now - timedelta(seconds=34),
                diagnostics=_camera_snapshot(),
                capabilities={"capture_image": True, "timelapse": True},
            )
        ],
        last_heartbeat_at=now - timedelta(seconds=22),
        heartbeat_status="online",
        last_reading_at=now,
        reading_status="online",
        last_image_at=_image_specs(state)[-1][1],
        image_status="online",
        camera_status="online",
        last_command=health_command,
        last_successful_command_at=health_command.timestamp if health_command else None,
        friendly_status="online",
        attention_reasons=[],
        recent_events=_diagnostic_events(state, 6),
    )


def _health_node(
    *,
    hardware_device_id: str,
    node_role: str,
    display_name: str,
    firmware_version: str,
    model: str,
    last_seen_at: datetime,
    diagnostics: DeviceDiagnosticSnapshotRead,
    capabilities: dict,
) -> DeviceHealthNodeRead:
    return DeviceHealthNodeRead(
        hardware_device_id=hardware_device_id,
        node_role=node_role,
        node_index=0 if node_role == "master" else 1,
        display_name=display_name,
        status="online",
        hardware_model=model,
        hardware_version="demo-rev-a",
        software_version=firmware_version,
        ota_status="idle",
        capabilities=capabilities,
        last_seen_at=last_seen_at,
        health_status="online",
        diagnostics=diagnostics,
    )


def _node_summary(state: DemoState) -> dict:
    health = _hardware_health(state)
    return {
        "overall_status": "online",
        "primary": health.primary.model_dump(mode="json") if health.primary else None,
        "cameras": [camera.model_dump(mode="json") for camera in health.cameras],
    }


def _master_snapshot() -> DeviceDiagnosticSnapshotRead:
    now = _now()
    return DeviceDiagnosticSnapshotRead(
        hardware_device_id=DEMO_MASTER_ID,
        device_id=DEMO_DEVICE_ID,
        node_role="master",
        schema_version=1,
        reported_status="online",
        firmware_version="0.1.6",
        uptime_seconds=int((now - _started_at()).total_seconds()),
        wifi_rssi_dbm=-48,
        reboot_reason="power_on",
        provisioning_state="configured",
        last_sensor_reading_at=now - timedelta(seconds=18),
        last_camera_image_upload_at=now - timedelta(minutes=14),
        last_command_status=CommandStatus.COMPLETED.value,
        last_command_code="completed",
        last_command_message="Demo command completed",
        last_command_at=now - timedelta(minutes=18),
        error_counters={},
        reported_at=now - timedelta(seconds=24),
        updated_at=now - timedelta(seconds=24),
    )


def _camera_snapshot() -> DeviceDiagnosticSnapshotRead:
    now = _now()
    return DeviceDiagnosticSnapshotRead(
        hardware_device_id=DEMO_CAMERA_ID,
        device_id=DEMO_DEVICE_ID,
        node_role="camera",
        schema_version=1,
        reported_status="online",
        firmware_version="0.1.8",
        uptime_seconds=int((now - _started_at()).total_seconds()) - 14,
        wifi_rssi_dbm=-51,
        reboot_reason="power_on",
        provisioning_state="configured",
        last_camera_image_upload_at=now - timedelta(minutes=14),
        error_counters={},
        reported_at=now - timedelta(seconds=40),
        updated_at=now - timedelta(seconds=40),
    )


def _diagnostic_events(state: DemoState, limit: int) -> list[DeviceDiagnosticEventRead]:
    now = _now()
    rows = [
        DeviceDiagnosticEventRead(
            id=DEMO_EVENT_ID_BASE - 20,
            device_id=DEMO_DEVICE_ID,
            hardware_device_id=DEMO_MASTER_ID,
            event_type="DIAGNOSTICS_RECEIVED",
            severity="info",
            code="healthy",
            message="Demo master diagnostics healthy",
            metadata={"demo": True, "uptime_days": DEMO_AGE_DAYS},
            occurred_at=now - timedelta(minutes=8),
            created_at=now - timedelta(minutes=8),
        ),
        DeviceDiagnosticEventRead(
            id=DEMO_EVENT_ID_BASE - 21,
            device_id=DEMO_DEVICE_ID,
            hardware_device_id=DEMO_CAMERA_ID,
            event_type="IMAGE_UPLOAD_COMPLETED",
            severity="info",
            code="image_uploaded",
            message="Demo camera image uploaded",
            metadata={"demo": True},
            occurred_at=_image_specs(state)[-1][1],
            created_at=_image_specs(state)[-1][1],
        ),
        DeviceDiagnosticEventRead(
            id=DEMO_EVENT_ID_BASE - 22,
            device_id=DEMO_DEVICE_ID,
            hardware_device_id=DEMO_MASTER_ID,
            event_type="WATER_LEVEL_OK",
            severity="info",
            code="reservoir_ok",
            message="Water reservoir level is healthy",
            metadata={"demo": True},
            occurred_at=now - timedelta(hours=6),
            created_at=now - timedelta(hours=6),
        ),
    ]
    for event in state.events[:3]:
        rows.append(
            DeviceDiagnosticEventRead(
                id=event.id,
                device_id=DEMO_DEVICE_ID,
                hardware_device_id=event.hardware_device_id,
                event_type=event.event_type,
                severity=event.severity,
                code=event.code,
                message=event.summary,
                metadata=event.data,
                occurred_at=event.occurred_at,
                created_at=event.occurred_at,
            )
        )
    return sorted(rows, key=lambda item: item.occurred_at, reverse=True)[:limit]


def _timeline_events(state: DemoState) -> list[DemoTimelineEvent]:
    now = _now()
    baseline = [
        DemoTimelineEvent(
            id=DEMO_EVENT_ID_BASE - 30,
            event_type="HEARTBEAT_RECEIVED",
            severity="info",
            occurred_at=now - timedelta(minutes=4),
            summary="Heartbeat received from demo master",
            hardware_device_id=DEMO_MASTER_ID,
            node_role="master",
            correlation_id="demo_heartbeat",
            data={"wifi_rssi_dbm": -48, "firmware_version": "0.1.6"},
        ),
        DemoTimelineEvent(
            id=DEMO_EVENT_ID_BASE - 31,
            event_type="IMAGE_UPLOAD_COMPLETED",
            severity="info",
            occurred_at=_image_specs(state)[-1][1],
            summary="Latest growth image uploaded",
            hardware_device_id=DEMO_CAMERA_ID,
            node_role="camera",
            correlation_id="demo_image_upload",
            data={"plant_age_days": DEMO_AGE_DAYS, "source_hardware_device_id": DEMO_CAMERA_ID},
        ),
        DemoTimelineEvent(
            id=DEMO_EVENT_ID_BASE - 32,
            event_type="ALERT_RESOLVED",
            severity="info",
            occurred_at=now - timedelta(days=3, hours=2),
            summary="Water refill reminder resolved",
            hardware_device_id=DEMO_MASTER_ID,
            node_role="master",
            data={"alert": "water_refill", "resolved_by": "demo fixture"},
        ),
    ]
    return sorted([*state.events, *baseline], key=lambda event: event.occurred_at, reverse=True)


def _timeline_read(event: DemoTimelineEvent) -> DeviceTimelineEventRead:
    return DeviceTimelineEventRead(
        id=event.id,
        event_type=event.event_type,
        severity=event.severity,
        occurred_at=event.occurred_at,
        hardware_device_id=event.hardware_device_id,
        node_role=event.node_role,
        correlation_id=event.correlation_id,
        summary=event.summary,
        code=event.code,
        message=event.message,
        data=event.data,
        created_at=event.occurred_at,
    )


def _command_read(command: DemoCommand) -> CommandRead:
    return CommandRead(
        id=command.id,
        device_id=DEMO_DEVICE_ID,
        target=command.target,
        action=command.action,
        value=command.value,
        status=CommandStatus.COMPLETED,
        message=command.message,
        light_on=None,
        light_intensity_percent=None,
        pump_on=False,
        created_at=command.created_at,
        sent_at=command.created_at,
        completed_at=command.created_at + timedelta(milliseconds=350),
    )


def _image_specs(state: DemoState) -> list[tuple[int, datetime]]:
    start = _started_at()
    latest_allowed = _now() - timedelta(minutes=14)
    specs = [
        (DEMO_IMAGE_ID_BASE + index, min(start + timedelta(days=DEMO_AGE_DAYS + offset, minutes=15), latest_allowed))
        for index, offset in enumerate(_capture_day_offsets)
    ]
    specs.extend(state.extra_images)
    return sorted(specs, key=lambda item: item[1])


def _image_read(request: Request, spec: tuple[int, datetime]) -> DeviceSummaryImageRead:
    return DeviceSummaryImageRead(
        id=spec[0],
        content_url=_image_url(request, spec[0]),
        timestamp=spec[1],
        source_hardware_device_id=DEMO_CAMERA_ID,
    )


def _image_url(request: Request, image_id: int) -> str:
    return str(request.url_for("demo_image", image_id=image_id))


def _png_for_image(image_id: int) -> bytes:
    width = 640
    height = 480
    stage = max(0, min(17, image_id - DEMO_IMAGE_ID_BASE))
    if image_id >= DEMO_IMAGE_ID_BASE + 1000:
        stage = 17
    growth = 0.25 + min(stage, 17) / 24
    rows = []
    for y in range(height):
        row = bytearray([0])
        for x in range(width):
            nx = (x - width / 2) / (width / 2)
            ny = (y - height / 2) / (height / 2)
            table = 118 + int(18 * math.sin((x + image_id) / 50))
            r, g, b = table, 111 + int(18 * (1 - y / height)), 91
            pot = y > height * 0.68 and abs(nx) < 0.55
            if pot:
                r, g, b = 88, 96, 88
            stem = abs(nx) < 0.025 and -0.45 < ny < 0.4
            leaf_left = ((nx + 0.18) / (0.18 + growth * 0.18)) ** 2 + ((ny + 0.05) / (0.12 + growth * 0.14)) ** 2 < 1
            leaf_right = ((nx - 0.2) / (0.18 + growth * 0.16)) ** 2 + ((ny + 0.14) / (0.12 + growth * 0.13)) ** 2 < 1
            leaf_top = (nx / (0.14 + growth * 0.18)) ** 2 + ((ny + 0.35) / (0.11 + growth * 0.12)) ** 2 < 1
            if stem or leaf_left or leaf_right or leaf_top:
                r = 34 + int(20 * growth)
                g = 105 + int(80 * growth)
                b = 58 + int(16 * math.sin((x + y) / 31))
            light = max(0.0, 1.0 - ((x - width * 0.18) ** 2 + (y - height * 0.1) ** 2) / (width * height * 0.55))
            r = min(255, int(r + light * 38))
            g = min(255, int(g + light * 34))
            b = min(255, int(b + light * 26))
            row.extend([r, g, b])
        rows.append(bytes(row))
    raw = b"".join(rows)
    return _png_encode(width, height, raw)


def _png_encode(width: int, height: int, raw_scanlines: bytes) -> bytes:
    def chunk(kind: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + kind
            + data
            + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
        )

    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(raw_scanlines, 6)) + chunk(b"IEND", b"")


def _started_at() -> datetime:
    now = _now()
    return (now - timedelta(days=DEMO_AGE_DAYS)).replace(hour=9, minute=0, second=0, microsecond=0)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
