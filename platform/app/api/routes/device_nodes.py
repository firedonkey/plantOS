from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.deps import get_device_from_token
from app.db.session import get_session
from app.schemas.device_nodes import (
    DeviceNodeHeartbeatCreate,
    DeviceNodeHeartbeatRead,
    DeviceNodeRegisterCreate,
    DeviceNodeRegisterRead,
)
from app.services.device_nodes import (
    get_node_by_hardware_id,
    update_node_heartbeat,
    upsert_device_node,
)


router = APIRouter(prefix="/api/device-nodes", tags=["device-nodes"])


@router.post("/register", response_model=DeviceNodeRegisterRead, status_code=201)
def register_device_node(
    payload: DeviceNodeRegisterCreate,
    request: Request,
    session: Session = Depends(get_session),
):
    device = get_device_from_token(request, session)
    if device is None:
        raise HTTPException(status_code=401, detail="Valid device token required.")
    if device.id != payload.device_id:
        raise HTTPException(status_code=403, detail="Device token does not match device_id.")

    allowed_roles = {"camera", "master", "single_board"}
    if payload.node_role not in allowed_roles:
        raise HTTPException(status_code=400, detail="Unsupported node role.")

    existing = get_node_by_hardware_id(session, payload.hardware_device_id)
    if existing is not None and existing.device_id != device.id:
        raise HTTPException(status_code=409, detail="Device node is attached to another device.")

    node = upsert_device_node(
        session,
        device_id=device.id,
        hardware_device_id=payload.hardware_device_id,
        node_role=payload.node_role,
        node_index=payload.node_index,
        display_name=payload.display_name,
        hardware_model=payload.hardware_model,
        hardware_version=payload.hardware_version,
        software_version=payload.software_version,
        capabilities=payload.capabilities,
        status=payload.status,
    )

    return DeviceNodeRegisterRead(
        device_id=node.device_id,
        hardware_device_id=node.hardware_device_id,
        node_role=node.node_role,
        node_index=node.node_index,
        display_name=node.display_name,
        hardware_model=node.hardware_model,
        hardware_version=node.hardware_version,
        software_version=node.software_version,
        status=node.status,
        last_seen_at=node.last_seen_at,
    )


@router.post("/heartbeat", response_model=DeviceNodeHeartbeatRead)
def heartbeat(
    payload: DeviceNodeHeartbeatCreate,
    request: Request,
    session: Session = Depends(get_session),
):
    device = get_device_from_token(request, session)
    if device is None:
        raise HTTPException(status_code=401, detail="Valid device token required.")
    if device.id != payload.device_id:
        raise HTTPException(status_code=403, detail="Device token does not match device_id.")

    node = get_node_by_hardware_id(session, payload.hardware_device_id)
    if node is None or node.device_id != device.id:
        raise HTTPException(status_code=404, detail="Device node not found.")
    if node.node_role != payload.node_role:
        raise HTTPException(status_code=409, detail="Device node role does not match registration.")

    updated = update_node_heartbeat(session, payload.hardware_device_id, status=payload.status)
    if updated is None:
        raise HTTPException(status_code=404, detail="Device node not found.")

    return DeviceNodeHeartbeatRead(
        device_id=updated.device_id,
        hardware_device_id=updated.hardware_device_id,
        node_role=updated.node_role,
        status=updated.status,
        last_seen_at=updated.last_seen_at,
    )
