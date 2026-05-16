import secrets
from datetime import datetime, timezone

from sqlalchemy import delete, select, text, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models import Command, Device, Event, Image, SensorReading, User
from app.schemas.devices import DeviceCreate, DeviceUpdate


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
            .where(
                Device.user_id == user.id,
                Device.archived_at.is_(None),
                Device.released_at.is_(None),
            )
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
            Device.archived_at.is_(None),
            Device.released_at.is_(None),
        )
    )
    if device is None:
        return None
    return ensure_device_api_token(session, device)


def update_device_for_user(session: Session, user: User, device_id: int, device_data: DeviceUpdate) -> Device | None:
    device = get_device_for_user(session, user, device_id)
    if device is None:
        return None

    updates = device_data.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(device, field, value)
    session.add(device)
    session.commit()
    session.refresh(device)
    return ensure_device_api_token(session, device)


def get_device_by_api_token(session: Session, api_token: str) -> Device | None:
    return session.scalar(select(Device).where(Device.api_token == api_token))


def delete_device_for_user(session: Session, user: User, device_id: int) -> bool:
    device = get_device_for_user(session, user, device_id)
    if device is None:
        return False

    _release_device_record(session, device, reason="user_removed")
    return True


def factory_reset_device(session: Session, device: Device) -> None:
    _release_device_record(session, device, reason="device_factory_reset")


def release_device_for_user(session: Session, user: User, device_id: int) -> Device | None:
    device = get_device_for_user(session, user, device_id)
    if device is None:
        return None
    _release_device_record(session, device, reason="owner_transfer")
    return device


def _release_device_record(session: Session, device: Device, *, reason: str) -> None:
    _clear_provisioning_references(session, device.id)
    released_at = datetime.now(timezone.utc)
    device.api_token = None
    device.released_at = released_at
    device.archived_at = released_at
    device.release_reason = reason
    device.status_message = "Device released for reprovisioning."
    device.status_updated_at = released_at
    session.add(device)
    session.commit()
    session.refresh(device)


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
    try:
        session.execute(
            update(Image)
            .where(Image.device_id == device_id)
            .values(source_hardware_device_id=None)
        )
        session.execute(text("DELETE FROM device_hardware_ids WHERE device_id = :device_id"), {"device_id": device_id})
    except SQLAlchemyError:
        session.rollback()


def _clear_attached_device_nodes(session: Session, device_id: int) -> None:
    try:
        session.execute(text("DELETE FROM device_hardware_ids WHERE device_id = :device_id"), {"device_id": device_id})
    except SQLAlchemyError:
        session.rollback()
