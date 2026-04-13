from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from platform_app.api.deps import get_current_user
from platform_app.db.session import get_session
from platform_app.models import User
from platform_app.schemas.readings import SensorReadingCreate, SensorReadingRead
from platform_app.services.devices import get_device_for_user
from platform_app.services.readings import create_sensor_reading


router = APIRouter(prefix="/api", tags=["readings"])


@router.post("/data", response_model=SensorReadingRead, status_code=201)
def ingest_sensor_data(
    payload: SensorReadingCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    device = get_device_for_user(session, current_user, payload.device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found.")

    return create_sensor_reading(session, payload)
