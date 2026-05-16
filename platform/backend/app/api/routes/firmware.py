from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.api.deps import get_device_from_token
from app.core.settings import get_settings
from app.db.session import get_session
from app.schemas.firmware import FirmwareManifestRead, FirmwareOtaStatusCreate, FirmwareOtaStatusRead
from app.services.device_nodes import get_node_by_hardware_id
from app.services.firmware import (
    build_manifest_for_node,
    firmware_artifact_response,
    get_published_release,
    update_ota_status,
)


router = APIRouter(prefix="/api/hardware/ota", tags=["firmware"])


def _require_device(request: Request, session: Session):
    device = get_device_from_token(request, session)
    if device is None:
        raise HTTPException(status_code=401, detail="Valid device token required.")
    return device


def _require_node(session: Session, device_id: int, hardware_device_id: str):
    node = get_node_by_hardware_id(session, hardware_device_id)
    if node is None or node.device_id != device_id:
        raise HTTPException(status_code=404, detail="Device node not found.")
    return node


@router.get("/manifest", response_model=FirmwareManifestRead)
def ota_manifest(
    request: Request,
    hardware_device_id: str = Query(min_length=3, max_length=120),
    node_role: str = Query(min_length=3, max_length=40),
    current_version: str | None = Query(default=None, max_length=120),
    session: Session = Depends(get_session),
):
    device = _require_device(request, session)
    node = _require_node(session, device.id, hardware_device_id)
    if node.node_role != node_role:
        raise HTTPException(status_code=409, detail="Device node role does not match registration.")
    return build_manifest_for_node(
        session,
        node=node,
        node_role=node_role,
        current_version=current_version,
    )


@router.post("/status", response_model=FirmwareOtaStatusRead)
def ota_status(
    payload: FirmwareOtaStatusCreate,
    request: Request,
    session: Session = Depends(get_session),
):
    device = _require_device(request, session)
    node = _require_node(session, device.id, payload.hardware_device_id)
    return update_ota_status(session, node=node, payload=payload)


@router.get("/artifacts/{release_id}")
def ota_artifact(
    release_id: str,
    request: Request,
    session: Session = Depends(get_session),
):
    _require_device(request, session)
    release = get_published_release(session, release_id)
    if release is None:
        raise HTTPException(status_code=404, detail="Firmware release not found.")
    try:
        return firmware_artifact_response(release, get_settings())
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=404, detail="Firmware artifact not found.") from exc
