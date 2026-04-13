import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Device, User
from app.schemas.devices import DeviceCreate


def generate_device_token() -> str:
    return secrets.token_urlsafe(32)


def ensure_device_api_token(session: Session, device: Device) -> Device:
    if device.api_token:
        return device
    device.api_token = generate_device_token()
    session.add(device)
    session.commit()
    session.refresh(device)
    return device


def list_devices_for_user(session: Session, user: User) -> list[Device]:
    devices = list(
        session.scalars(
            select(Device)
            .where(Device.user_id == user.id)
            .order_by(Device.created_at.desc())
        )
    )
    for device in devices:
        ensure_device_api_token(session, device)
    return devices


def create_device_for_user(session: Session, user: User, device_data: DeviceCreate) -> Device:
    device = Device(
        user_id=user.id,
        name=device_data.name,
        location=device_data.location,
        plant_type=device_data.plant_type,
        api_token=generate_device_token(),
    )
    session.add(device)
    session.commit()
    session.refresh(device)
    return device


def get_device_for_user(session: Session, user: User, device_id: int) -> Device | None:
    device = session.scalar(
        select(Device).where(
            Device.id == device_id,
            Device.user_id == user.id,
        )
    )
    if device is None:
        return None
    return ensure_device_api_token(session, device)


def get_device_by_api_token(session: Session, api_token: str) -> Device | None:
    return session.scalar(select(Device).where(Device.api_token == api_token))
