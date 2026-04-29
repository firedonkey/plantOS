from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_device_from_token
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
