from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Device, User
from app.schemas.devices import DeviceCreate


def list_devices_for_user(session: Session, user: User) -> list[Device]:
    return list(
        session.scalars(
            select(Device)
            .where(Device.user_id == user.id)
            .order_by(Device.created_at.desc())
        )
    )


def create_device_for_user(session: Session, user: User, device_data: DeviceCreate) -> Device:
    device = Device(
        user_id=user.id,
        name=device_data.name,
        location=device_data.location,
        plant_type=device_data.plant_type,
    )
    session.add(device)
    session.commit()
    session.refresh(device)
    return device


def get_device_for_user(session: Session, user: User, device_id: int) -> Device | None:
    return session.scalar(
        select(Device).where(
            Device.id == device_id,
            Device.user_id == user.id,
        )
    )
