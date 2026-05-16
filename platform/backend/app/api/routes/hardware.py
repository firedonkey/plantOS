from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.api.deps import get_device_from_token
from app.db.session import get_session
from app.schemas.commands import CommandRead
from app.schemas.hardware import (
    HardwareCommandResultCreate,
    HardwareHeartbeatCreate,
    HardwareHeartbeatRead,
    HardwareReadingCreate,
)
from app.schemas.readings import SensorReadingCreate, SensorReadingRead
from app.services.commands import claim_pending_commands, get_command_for_device, report_command_result
from app.services.device_diagnostics import snapshot_read, upsert_diagnostic_snapshot
from app.services.device_nodes import get_node_by_hardware_id, update_node_heartbeat
from app.services.readings import create_sensor_reading
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
            light_on=payload.light_on,
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


@router.post("/commands/{command_id}/result", response_model=CommandRead)
def report_hardware_command_result(
    command_id: int,
    payload: HardwareCommandResultCreate,
    request: Request,
    session: Session = Depends(get_session),
):
    device = _require_device(request, session)
    command = get_command_for_device(session, device.id, command_id)
    if command is None:
        raise HTTPException(status_code=404, detail="Command not found.")
    return report_command_result(
        session,
        command,
        status=payload.status,
        message=payload.final_message,
        light_on=payload.light_on,
        pump_on=payload.pump_on,
    )


@router.post("/heartbeat", response_model=HardwareHeartbeatRead)
def hardware_heartbeat(
    payload: HardwareHeartbeatCreate,
    request: Request,
    session: Session = Depends(get_session),
):
    device = _require_device(request, session)
    last_seen_at = None
    node_role = payload.node_role
    diagnostics_snapshot = None
    updated_node = None

    if payload.hardware_device_id:
        node = get_node_by_hardware_id(session, payload.hardware_device_id)
        if node is None or node.device_id != device.id:
            raise HTTPException(status_code=404, detail="Device node not found.")
        if payload.node_role and node.node_role != payload.node_role:
            raise HTTPException(status_code=409, detail="Device node role does not match registration.")
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
            pump_on=payload.pump_on,
            message=payload.message or payload.status,
        ),
    )
    return HardwareHeartbeatRead(
        device_id=device.id,
        status=payload.status,
        hardware_device_id=payload.hardware_device_id,
        node_role=node_role,
        software_version=updated_node.software_version if payload.hardware_device_id and updated_node is not None else None,
        light_on=status_read.light_on,
        pump_on=status_read.pump_on,
        message=status_read.message,
        updated_at=status_read.updated_at,
        last_seen_at=last_seen_at,
        diagnostics=snapshot_read(diagnostics_snapshot),
    )
