import logging
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_device_from_token
from app.core.settings import get_settings
from app.db.session import get_session
from app.models import User
from app.schemas.commands import CommandCreate, CommandRead, LightCommandRequest, PumpCommandRequest
from app.schemas.devices import (
    DeviceCreate,
    DeviceRead,
    DeviceSummaryImageRead,
    DeviceSummaryRead,
    DeviceSummaryReadingRead,
)
from app.schemas.readings import SensorReadingRead
from app.services.commands import create_command
from app.services.device_nodes import build_node_summary, list_nodes_for_device
from app.services.devices import (
    create_device_for_user,
    factory_reset_device,
    get_device_for_user,
    list_devices_for_user,
)
from app.services.images import list_recent_images_for_device
from app.services.readings import get_latest_reading_for_device, list_recent_readings_for_device


router = APIRouter(prefix="/api/devices", tags=["devices"])
logger = logging.getLogger(__name__)


@router.get("", response_model=list[DeviceRead])
def list_devices(
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return list_devices_for_user(session, current_user)


@router.post("", response_model=DeviceRead, status_code=201)
def create_device(
    payload: DeviceCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    return create_device_for_user(session, current_user, payload)


@router.get("/{device_id}", response_model=DeviceRead)
def get_device(
    device_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    device = get_device_for_user(session, current_user, device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found.")
    return device


@router.get("/{device_id}/summary", response_model=DeviceSummaryRead)
def get_device_summary(
    device_id: int,
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    device = get_device_for_user(session, current_user, device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found.")

    latest_reading = get_latest_reading_for_device(session, device.id)
    latest_images = list_recent_images_for_device(session, device.id, limit=1)
    latest_image = latest_images[0] if latest_images else None
    nodes = list_nodes_for_device(session, device.id)

    return DeviceSummaryRead(
        id=device.id,
        name=device.name,
        location=device.location,
        plant_type=device.plant_type,
        latest_reading=(
            DeviceSummaryReadingRead.model_validate(latest_reading, from_attributes=True)
            if latest_reading is not None
            else None
        ),
        latest_image=(
            DeviceSummaryImageRead(
                id=latest_image.id,
                content_url=str(request.url_for("image_content", image_id=latest_image.id)),
                timestamp=latest_image.timestamp,
                source_hardware_device_id=latest_image.source_hardware_device_id,
            )
            if latest_image is not None
            else None
        ),
        node_summary=build_node_summary(nodes),
    )


@router.get("/{device_id}/readings", response_model=list[SensorReadingRead])
def get_device_readings(
    device_id: int,
    limit: int = Query(default=50, ge=1, le=500),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    device = get_device_for_user(session, current_user, device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found.")
    return list_recent_readings_for_device(session, device.id, limit=limit)


@router.get("/{device_id}/images/latest", response_model=DeviceSummaryImageRead | None)
def get_device_latest_image(
    device_id: int,
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    device = get_device_for_user(session, current_user, device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found.")

    latest_images = list_recent_images_for_device(session, device.id, limit=1)
    latest_image = latest_images[0] if latest_images else None
    if latest_image is None:
        return None

    return DeviceSummaryImageRead(
        id=latest_image.id,
        content_url=str(request.url_for("image_content", image_id=latest_image.id)),
        timestamp=latest_image.timestamp,
        source_hardware_device_id=latest_image.source_hardware_device_id,
    )


@router.post("/{device_id}/commands/light", response_model=CommandRead, status_code=201)
def create_light_command(
    device_id: int,
    payload: LightCommandRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    device = get_device_for_user(session, current_user, device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found.")

    return create_command(
        session,
        device.id,
        CommandCreate(target="light", action=payload.state),
    )


@router.post("/{device_id}/commands/pump", response_model=CommandRead, status_code=201)
def create_pump_command(
    device_id: int,
    payload: PumpCommandRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    device = get_device_for_user(session, current_user, device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found.")

    return create_command(
        session,
        device.id,
        CommandCreate(
            target="pump",
            action=payload.action,
            value=str(payload.seconds) if payload.action == "run" and payload.seconds is not None else None,
        ),
    )


@router.post("/{device_id}/commands/capture", status_code=501)
def create_capture_command(
    device_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    device = get_device_for_user(session, current_user, device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found.")
    raise HTTPException(
        status_code=501,
        detail="Capture commands are not yet supported through the shared backend command queue.",
    )


@router.post("/{device_id}/factory-reset")
def factory_reset_device_route(
    device_id: int,
    request: Request,
    session: Session = Depends(get_session),
):
    device = get_device_from_token(request, session)
    if device is None:
        raise HTTPException(status_code=401, detail="Valid device token required.")
    if device.id != device_id:
        raise HTTPException(status_code=403, detail="Device token does not match device_id.")

    factory_reset_device(session, device)
    return {"ok": True, "device_id": device_id, "status": "factory_reset"}


@router.post("/register-provisioned")
async def register_provisioned_device_proxy(request: Request):
    settings = get_settings()
    try:
        payload = await request.json()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON payload.") from exc

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                f"{settings.provisioning_api_url}/api/devices/register",
                json=payload,
            )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Provisioning service unavailable: {exc}") from exc

    try:
        response_payload = response.json()
    except ValueError as exc:
        raise HTTPException(status_code=502, detail="Provisioning service returned an invalid response.") from exc

    if response.status_code >= 400:
        logger.warning(
            "provisioned device registration failed status=%s payload=%s response=%s",
            response.status_code,
            payload,
            response_payload,
        )

    return JSONResponse(response_payload, status_code=response.status_code)
