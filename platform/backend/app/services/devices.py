import secrets

from sqlalchemy import delete, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models import Command, Device, Event, Image, SensorReading, User
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


def delete_device_for_user(session: Session, user: User, device_id: int) -> bool:
    device = get_device_for_user(session, user, device_id)
    if device is None:
        return False

    _delete_device_record(session, device)
    return True


def factory_reset_device(session: Session, device: Device) -> None:
    _delete_device_record(session, device)


def _delete_device_record(session: Session, device: Device) -> None:
    _clear_provisioning_references(session, device.id)
    session.execute(delete(Command).where(Command.device_id == device.id))
    session.execute(delete(Event).where(Event.device_id == device.id))
    session.execute(delete(Image).where(Image.device_id == device.id))
    session.execute(delete(SensorReading).where(SensorReading.device_id == device.id))
    _clear_attached_device_nodes(session, device.id)
    session.delete(device)
    session.commit()


def _clear_provisioning_references(session: Session, device_id: int) -> None:
    """Best-effort cleanup for provisioning tables managed by the Node service."""
    statements = [
        text("DELETE FROM device_access_tokens WHERE device_id = :device_id"),
        text("DELETE FROM device_hardware_ids WHERE device_id = :device_id"),
        text(
            """
            UPDATE device_serial_numbers
            SET
              status = 'available',
              claimed_by_user_id = NULL,
              claimed_by_device_id = NULL,
              claimed_at = NULL,
              updated_at = CURRENT_TIMESTAMP
            WHERE claimed_by_device_id = :device_id
            """
        ),
        text("UPDATE device_claim_tokens SET used_by_device_id = NULL WHERE used_by_device_id = :device_id"),
    ]
    for statement in statements:
        try:
            session.execute(statement, {"device_id": device_id})
        except SQLAlchemyError:
            session.rollback()


def _clear_attached_device_nodes(session: Session, device_id: int) -> None:
    try:
        session.execute(text("DELETE FROM device_hardware_ids WHERE device_id = :device_id"), {"device_id": device_id})
    except SQLAlchemyError:
        session.rollback()
