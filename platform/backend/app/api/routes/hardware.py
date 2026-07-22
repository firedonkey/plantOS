from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.api.deps import get_device_from_token
from app.api.errors import api_error
from app.contracts import (
    CommandProtocolStatus,
    DiagnosticSeverity,
    EventType,
    HeartbeatPayload,
    ProtocolValidationError,
    diagnostics_snapshot_payload,
    is_device_message_envelope,
    parse_command_result_message,
    parse_diagnostics_message,
    parse_heartbeat_message,
)
from app.db.session import get_session
from app.models import CommandStatus
from app.schemas.commands import CommandRead
from app.schemas.diagnostics import DeviceDiagnosticSnapshotRead, HardwareDiagnosticsCreate
from app.schemas.hardware import (
    HardwareCommandResultCreate,
    HardwareHeartbeatCreate,
    HardwareHeartbeatRead,
    HardwareReadingCreate,
)
from app.schemas.readings import SensorReadingCreate, SensorReadingRead
from app.services.command_events import build_command_payload, event_type_for_result_status, parse_contract_command_id
from app.services.commands import claim_pending_commands, get_command_for_device, report_command_result
from app.services.contract_commands import poll_contract_commands
from app.services.device_diagnostics import snapshot_read, upsert_diagnostic_snapshot
from app.services.device_nodes import get_node_by_hardware_id, update_node_heartbeat
from app.services.events import write_canonical_event
from app.services.readings import create_sensor_reading
from app.services.state_changes import emit_diagnostics_state_changes, emit_heartbeat_state_changes
from app.services.status import update_device_status
from app.api.routes.readings import _validate_reading_origin
from app.schemas.status import DeviceStatusCreate


router = APIRouter(prefix="/api/hardware", tags=["hardware"])


def _require_device(request: Request, session: Session):
    device = get_device_from_token(request, session)
    if device is None:
        raise HTTPException(status_code=401, detail="Valid device token required.")
    return device


@router.post("/readings", response_model=SensorReadingRead, status_code=201)
def upload_hardware_reading(
    payload: HardwareReadingCreate,
    request: Request,
    session: Session = Depends(get_session),
):
    device = _require_device(request, session)
    _validate_reading_origin(session, device.id, payload.hardware_device_id)
    return create_sensor_reading(
        session,
        SensorReadingCreate(
            device_id=device.id,
            hardware_device_id=payload.hardware_device_id,
            moisture=payload.moisture,
            temperature=payload.temperature,
            humidity=payload.humidity,
            water_temperature_c=payload.water_temperature_c,
            water_level_raw=payload.water_level_raw,
            water_level_state=payload.water_level_state,
            light_on=payload.light_on,
            light_intensity_percent=payload.light_intensity_percent,
            pump_on=payload.pump_on,
            pump_status=payload.pump_status,
            timestamp=payload.timestamp,
        ),
    )


@router.get("/commands/pending", response_model=list[CommandRead])
def poll_hardware_commands(
    request: Request,
    limit: int = Query(default=10, ge=1, le=50),
    session: Session = Depends(get_session),
):
    device = _require_device(request, session)
    return claim_pending_commands(session, device.id, limit=limit)


@router.get("/commands/poll")
def poll_contract_hardware_commands(
    request: Request,
    hardware_device_id: str = Query(min_length=3, max_length=120),
    node_role: str = Query(min_length=3, max_length=40),
    firmware_version: str | None = Query(default=None, max_length=120),
    schema_version: str = Query(default="1.0", min_length=3, max_length=16),
    hardware_model: str | None = Query(default=None, max_length=120),
    limit: int = Query(default=10, ge=1, le=50),
    session: Session = Depends(get_session),
):
    device = _require_device(request, session)
    node = get_node_by_hardware_id(session, hardware_device_id)
    if node is None or node.device_id != device.id:
        raise HTTPException(status_code=404, detail="Device node not found.")
    if not _node_role_matches(node.node_role, node_role):
        raise HTTPException(status_code=409, detail="Device node role does not match registration.")
    if hardware_model and node.hardware_model and hardware_model != node.hardware_model:
        raise api_error(
            409,
            "hardware_model_mismatch",
            "Reported hardware_model does not match registration.",
            details={"registered": node.hardware_model, "reported": hardware_model},
        )
    try:
        response = poll_contract_commands(
            session,
            device_id=device.id,
            poller_node=node,
            schema_version=schema_version,
            firmware_version=firmware_version,
            hardware_model=hardware_model,
            limit=limit,
        )
    except ProtocolValidationError as exc:
        _raise_protocol_error(exc)
    return response.model_dump(mode="json")


@router.post("/commands/{command_id}/result", response_model=CommandRead)
def report_hardware_command_result(
    command_id: int,
    request: Request,
    raw_payload: dict[str, Any] = Body(...),
    session: Session = Depends(get_session),
):
    device = _require_device(request, session)
    command = get_command_for_device(session, device.id, command_id)
    if command is None:
        raise HTTPException(status_code=404, detail="Command not found.")
    result_payload = _normalize_command_result_payload(
        raw_payload,
        command=command,
        command_id=command_id,
        device_id=device.id,
        session=session,
    )
    return report_command_result(
        session,
        command,
        status=result_payload["status"],
        message=result_payload["message"],
        light_on=result_payload["light_on"],
        light_intensity_percent=result_payload["light_intensity_percent"],
        pump_on=result_payload["pump_on"],
        event_type=result_payload["event_type"],
        event_status=result_payload["event_status"],
        error_code=result_payload["error_code"],
        result=result_payload["result"],
    )


@router.post("/heartbeat", response_model=HardwareHeartbeatRead)
def hardware_heartbeat(
    request: Request,
    raw_payload: dict[str, Any] = Body(...),
    session: Session = Depends(get_session),
):
    device = _require_device(request, session)
    payload, correlation_id, contract_data, diagnostics_event_source = _normalize_heartbeat_payload(
        raw_payload,
        device_id=device.id,
    )
    last_seen_at = None
    node_role = payload.node_role
    diagnostics_snapshot = None
    updated_node = None
    previous_node_status = None

    if payload.hardware_device_id:
        node = get_node_by_hardware_id(session, payload.hardware_device_id)
        if node is None or node.device_id != device.id:
            raise HTTPException(status_code=404, detail="Device node not found.")
        if payload.node_role and node.node_role != payload.node_role:
            raise HTTPException(status_code=409, detail="Device node role does not match registration.")
        previous_node_status = node.status
        updated_node = update_node_heartbeat(
            session,
            payload.hardware_device_id,
            status=payload.status,
            software_version=payload.software_version,
        )
        if updated_node is None:
            raise HTTPException(status_code=404, detail="Device node not found.")
        last_seen_at = updated_node.last_seen_at
        node_role = updated_node.node_role
        if payload.diagnostics is not None:
            diagnostics_snapshot = upsert_diagnostic_snapshot(
                session,
                device_id=device.id,
                node=updated_node,
                status=payload.status,
                diagnostics=payload.diagnostics,
                reported_at=last_seen_at,
            )

    status_read = update_device_status(
        session,
        device,
        DeviceStatusCreate(
            light_on=payload.light_on,
            light_intensity_percent=payload.light_intensity_percent,
            pump_on=payload.pump_on,
            message=payload.message or payload.status,
        ),
    )
    if payload.hardware_device_id and updated_node is not None:
        emit_heartbeat_state_changes(
            session,
            device_id=device.id,
            hardware_device_id=updated_node.hardware_device_id,
            node_role=updated_node.node_role,
            current=contract_data,
            correlation_id=correlation_id,
            occurred_at=last_seen_at,
        )
        write_canonical_event(
            session,
            event_type=EventType.HEARTBEAT_RECEIVED,
            severity=DiagnosticSeverity.INFO,
            device_id=device.id,
            hardware_device_id=updated_node.hardware_device_id,
            node_role=updated_node.node_role,
            correlation_id=correlation_id,
            data=contract_data,
            occurred_at=last_seen_at,
        )
        if payload.status == "online" and previous_node_status != "online":
            write_canonical_event(
                session,
                event_type=EventType.DEVICE_ONLINE,
                severity=DiagnosticSeverity.INFO,
                device_id=device.id,
                hardware_device_id=updated_node.hardware_device_id,
                node_role=updated_node.node_role,
                correlation_id=correlation_id,
                data={"source": "heartbeat"},
                occurred_at=last_seen_at,
            )
        if payload.status == "offline" and previous_node_status != "offline":
            write_canonical_event(
                session,
                event_type=EventType.DEVICE_OFFLINE,
                severity=DiagnosticSeverity.WARNING,
                device_id=device.id,
                hardware_device_id=updated_node.hardware_device_id,
                node_role=updated_node.node_role,
                correlation_id=correlation_id,
                data={"source": "heartbeat"},
                occurred_at=last_seen_at,
            )
        if diagnostics_snapshot is not None and diagnostics_event_source is not None:
            write_canonical_event(
                session,
                event_type=EventType.DIAGNOSTICS_RECEIVED,
                severity=DiagnosticSeverity.WARNING if diagnostics_snapshot.last_error_code else DiagnosticSeverity.INFO,
                device_id=device.id,
                hardware_device_id=updated_node.hardware_device_id,
                node_role=updated_node.node_role,
                correlation_id=correlation_id,
                data={
                    "source": diagnostics_event_source,
                    "schema_version": diagnostics_snapshot.schema_version,
                },
                occurred_at=last_seen_at,
            )
    return HardwareHeartbeatRead(
        device_id=device.id,
        status=payload.status,
        hardware_device_id=payload.hardware_device_id,
        node_role=node_role,
        software_version=updated_node.software_version if payload.hardware_device_id and updated_node is not None else None,
        light_on=status_read.light_on,
        light_intensity_percent=status_read.light_intensity_percent,
        pump_on=status_read.pump_on,
        message=status_read.message,
        updated_at=status_read.updated_at,
        last_seen_at=last_seen_at,
        diagnostics=snapshot_read(diagnostics_snapshot),
    )


@router.post("/diagnostics", response_model=DeviceDiagnosticSnapshotRead)
def hardware_diagnostics(
    request: Request,
    raw_payload: dict[str, Any] = Body(...),
    session: Session = Depends(get_session),
):
    device = _require_device(request, session)
    if not is_device_message_envelope(raw_payload):
        raise api_error(
            422,
            "contract_envelope_required",
            "Diagnostics must use the PlantLab device message envelope.",
        )
    try:
        message = parse_diagnostics_message(raw_payload)
    except ProtocolValidationError as exc:
        _raise_protocol_error(exc)

    _validate_contract_device_id(message.device_id, device.id)
    node = get_node_by_hardware_id(session, message.hardware_device_id)
    if node is None or node.device_id != device.id:
        raise HTTPException(status_code=404, detail="Device node not found.")
    if node.node_role != message.node_role.value:
        raise HTTPException(status_code=409, detail="Device node role does not match registration.")

    updated_node = update_node_heartbeat(
        session,
        message.hardware_device_id,
        status=message.payload.status.value,
    )
    if updated_node is None:
        raise HTTPException(status_code=404, detail="Device node not found.")
    snapshot = upsert_diagnostic_snapshot(
        session,
        device_id=device.id,
        node=updated_node,
        status=message.payload.status.value,
        diagnostics=diagnostics_snapshot_payload(message.payload),
        reported_at=updated_node.last_seen_at,
    )
    diagnostic_data = message.payload.model_dump(mode="json", exclude_none=True)
    emit_diagnostics_state_changes(
        session,
        device_id=device.id,
        hardware_device_id=updated_node.hardware_device_id,
        node_role=updated_node.node_role,
        current=diagnostic_data,
        correlation_id=message.message_id,
        occurred_at=updated_node.last_seen_at,
    )
    write_canonical_event(
        session,
        event_type=EventType.DIAGNOSTICS_RECEIVED,
        severity=message.payload.severity,
        device_id=device.id,
        hardware_device_id=updated_node.hardware_device_id,
        node_role=updated_node.node_role,
        correlation_id=message.message_id,
        data=diagnostic_data,
        occurred_at=updated_node.last_seen_at,
    )
    return snapshot_read(snapshot)


def _normalize_heartbeat_payload(
    raw_payload: dict[str, Any],
    *,
    device_id: int,
) -> tuple[HardwareHeartbeatCreate, str | None, dict[str, Any], str | None]:
    if is_device_message_envelope(raw_payload):
        try:
            message = parse_heartbeat_message(raw_payload)
        except ProtocolValidationError as exc:
            _raise_protocol_error(exc)
        _validate_contract_device_id(message.device_id, device_id)
        heartbeat = message.payload
        grow_light = None
        if heartbeat.actuators:
            grow_light = heartbeat.actuators.grow_light or heartbeat.actuators.ambient_light
        return (
            HardwareHeartbeatCreate(
                hardware_device_id=message.hardware_device_id,
                node_role=message.node_role.value,
                status=heartbeat.node_status.value,
                software_version=heartbeat.firmware_version,
                light_on=grow_light.enabled if grow_light else None,
                light_intensity_percent=grow_light.brightness_percent if grow_light else None,
                message=heartbeat.node_status.value,
                diagnostics=_diagnostics_from_heartbeat_payload(heartbeat),
            ),
            message.message_id,
            heartbeat.model_dump(mode="json", exclude_none=True),
            None,
        )

    try:
        payload = HardwareHeartbeatCreate.model_validate(raw_payload)
    except ValidationError as exc:
        raise api_error(
            422,
            "validation_error",
            "Request validation failed.",
            details=_validation_error_details(exc),
        ) from exc
    return (
        payload,
        None,
        {"source": "legacy"},
        "legacy_heartbeat_diagnostics" if payload.diagnostics is not None else None,
    )


def _diagnostics_from_heartbeat_payload(heartbeat: HeartbeatPayload) -> HardwareDiagnosticsCreate:
    runtime = heartbeat.runtime
    last_command = None
    if runtime is not None and (runtime.last_command_id or runtime.last_command_status):
        last_command = {
            "id": parse_contract_command_id(runtime.last_command_id),
            "status": runtime.last_command_status,
        }
    return HardwareDiagnosticsCreate(
        schema_version=1,
        uptime_seconds=heartbeat.uptime_seconds,
        wifi_rssi_dbm=heartbeat.wifi_rssi_dbm,
        provisioning_state=runtime.provisioning_status if runtime is not None else None,
        last_command=last_command,
        error_counters={},
    )


def _normalize_command_result_payload(
    raw_payload: dict[str, Any],
    *,
    command,
    command_id: int,
    device_id: int,
    session: Session,
) -> dict[str, Any]:
    if is_device_message_envelope(raw_payload):
        try:
            message = parse_command_result_message(raw_payload)
        except ProtocolValidationError as exc:
            _raise_protocol_error(exc)
        _validate_contract_device_id(message.device_id, device_id)
        payload_command_id = parse_contract_command_id(message.payload.command_id)
        if payload_command_id != command_id:
            raise api_error(
                409,
                "command_id_mismatch",
                "Command result command_id does not match the route command_id.",
                details={"command_id": message.payload.command_id},
            )
        expected_payload = build_command_payload(session, command)
        if expected_payload is not None and expected_payload.command_type != message.payload.command_type:
            raise api_error(
                409,
                "command_type_mismatch",
                "Command result command_type does not match the queued command.",
                details={
                    "expected": expected_payload.command_type.value,
                    "actual": message.payload.command_type.value,
                },
            )
        result = dict(message.payload.result or {})
        return {
            "status": _db_command_status(message.payload.status),
            "message": message.payload.message or (message.payload.error_code.value if message.payload.error_code else None),
            "light_on": _optional_bool(result.get("light_on")),
            "light_intensity_percent": _optional_int_percent(result.get("light_intensity_percent")),
            "pump_on": _optional_bool(result.get("pump_on")),
            "event_type": event_type_for_result_status(message.payload.status.value),
            "event_status": message.payload.status.value,
            "error_code": message.payload.error_code.value if message.payload.error_code else None,
            "result": result,
        }

    try:
        payload = HardwareCommandResultCreate.model_validate(raw_payload)
    except ValidationError as exc:
        raise api_error(
            422,
            "validation_error",
            "Request validation failed.",
            details=_validation_error_details(exc),
        ) from exc
    return {
        "status": payload.status,
        "message": payload.final_message,
        "light_on": payload.light_on,
        "light_intensity_percent": payload.light_intensity_percent,
        "pump_on": payload.pump_on,
        "event_type": None,
        "event_status": None,
        "error_code": None,
        "result": {},
    }


def _db_command_status(status: CommandProtocolStatus) -> CommandStatus:
    if status == CommandProtocolStatus.COMPLETED:
        return CommandStatus.COMPLETED
    if status in {CommandProtocolStatus.FAILED, CommandProtocolStatus.REJECTED}:
        return CommandStatus.FAILED
    if status == CommandProtocolStatus.TIMED_OUT:
        return CommandStatus.TIMED_OUT
    return CommandStatus.IN_PROGRESS


def _optional_bool(value: Any) -> bool | None:
    return value if isinstance(value, bool) else None


def _optional_int_percent(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int) and 0 <= value <= 100:
        return value
    return None


def _validate_contract_device_id(contract_device_id: int | None, token_device_id: int) -> None:
    if contract_device_id is not None and contract_device_id != token_device_id:
        raise api_error(
            409,
            "device_id_mismatch",
            "Device message device_id does not match the device token.",
            details={"device_id": contract_device_id},
        )


def _node_role_matches(registered_role: str | None, requested_role: str) -> bool:
    registered = str(registered_role or "").strip().lower()
    requested = str(requested_role or "").strip().lower()
    return registered == requested or (registered == "single_board" and requested == "master")


def _raise_protocol_error(exc: ProtocolValidationError) -> None:
    raise api_error(
        422,
        exc.code,
        exc.message,
        details=exc.details,
    )


def _validation_error_details(error: ValidationError) -> dict[str, Any]:
    errors = []
    for item in error.errors():
        errors.append(
            {
                "loc": list(item.get("loc") or []),
                "msg": str(item.get("msg") or ""),
                "type": str(item.get("type") or ""),
            }
        )
    return {"errors": errors}
