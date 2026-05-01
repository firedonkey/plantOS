import logging
import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_device_from_token
from app.core.settings import get_settings
from app.db.session import get_session
from app.models import User
from app.schemas.devices import DeviceCreate, DeviceRead
from app.services.devices import (
    create_device_for_user,
    factory_reset_device,
    get_device_for_user,
    list_devices_for_user,
)


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
