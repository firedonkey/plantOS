from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.deps import get_device_from_token, get_optional_current_user
from app.db.session import get_session
from app.models import User
from app.schemas.readings import SensorReadingCreate, SensorReadingRead
from app.services.device_nodes import get_node_for_device, list_nodes_for_device
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

    _validate_reading_origin(session, device.id, payload.hardware_device_id)

    return create_sensor_reading(session, payload)


def _validate_reading_origin(session: Session, device_id: int, hardware_device_id: str | None) -> None:
    nodes = list_nodes_for_device(session, device_id)
    if not nodes:
        return

    roles = {str(node.node_role or "").strip().lower() for node in nodes}
    has_cameras = "camera" in roles

    if hardware_device_id is None:
        if has_cameras:
            raise HTTPException(
                status_code=400,
                detail="hardware_device_id is required for grouped devices that include camera nodes.",
            )
        return

    node = get_node_for_device(session, device_id=device_id, hardware_device_id=hardware_device_id)
    if node is None:
        raise HTTPException(status_code=403, detail="Reading source node is not attached to this device.")

    node_role = str(node.node_role or "").strip().lower()
    if node_role == "camera":
        raise HTTPException(status_code=403, detail="Camera nodes cannot post device-level sensor readings.")
