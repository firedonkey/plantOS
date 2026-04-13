from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_session
from app.models import User
from app.schemas.devices import DeviceCreate, DeviceRead
from app.services.devices import (
    create_device_for_user,
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
