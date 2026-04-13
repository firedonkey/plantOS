from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.deps import get_device_from_token, get_optional_current_user
from app.db.session import get_session
from app.models import User
from app.schemas.readings import SensorReadingCreate, SensorReadingRead
from app.services.devices import get_device_for_user
from app.services.readings import create_sensor_reading


router = APIRouter(prefix="/api", tags=["readings"])


@router.post("/data", response_model=SensorReadingRead, status_code=201)
def ingest_sensor_data(
    payload: SensorReadingCreate,
    request: Request,
    session: Session = Depends(get_session),
    current_user: User | None = Depends(get_optional_current_user),
):
    if current_user is not None:
        device = get_device_for_user(session, current_user, payload.device_id)
        if device is None:
            raise HTTPException(status_code=404, detail="Device not found.")
    else:
        device = get_device_from_token(request, session)
        if device is None:
            raise HTTPException(status_code=401, detail="Sign in or valid device token required.")
        if device.id != payload.device_id:
            raise HTTPException(status_code=403, detail="Device token does not match device_id.")

    return create_sensor_reading(session, payload)
