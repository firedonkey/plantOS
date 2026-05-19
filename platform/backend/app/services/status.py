from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import Device
from app.schemas.status import DeviceStatusCreate, DeviceStatusRead


def update_device_status(session: Session, device: Device, payload: DeviceStatusCreate) -> DeviceStatusRead:
    device.current_light_on = payload.light_on
    if payload.light_intensity_percent is not None:
        device.current_light_intensity_percent = payload.light_intensity_percent
    device.current_pump_on = payload.pump_on
    device.status_message = payload.message
    device.status_updated_at = datetime.now(timezone.utc)
    session.add(device)
    session.commit()
    session.refresh(device)
    return DeviceStatusRead(
        device_id=int(device.id),
        light_on=device.current_light_on,
        light_intensity_percent=device.current_light_intensity_percent,
        pump_on=device.current_pump_on,
        message=device.status_message,
        updated_at=device.status_updated_at,
    )
