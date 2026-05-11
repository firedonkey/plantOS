from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.deps import get_device_from_token
from app.db.session import get_session
from app.schemas.status import DeviceStatusCreate, DeviceStatusRead
from app.services.status import update_device_status


router = APIRouter(prefix="/api/devices/{device_id}/status", tags=["status"])


@router.post("", response_model=DeviceStatusRead)
def update_status(
    device_id: int,
    payload: DeviceStatusCreate,
    request: Request,
    session: Session = Depends(get_session),
):
    device = get_device_from_token(request, session)
    if device is None:
        raise HTTPException(status_code=401, detail="Valid device token required.")
    if device.id != device_id:
        raise HTTPException(status_code=403, detail="Device token does not match device_id.")
    return update_device_status(session, device, payload)
