from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_admin_user
from app.db.session import get_session
from app.models import (
    Command,
    Device,
    DeviceDiagnosticEvent,
    DeviceDiagnosticSnapshot,
    DeviceNode,
    FirmwareRelease,
    Image,
    SensorReading,
    User,
)
from app.schemas.admin import (
    AdminCommandRead,
    AdminDeviceRead,
    AdminDiagnosticsRead,
    AdminEventRead,
    AdminFirmwareReleaseRead,
    AdminNodeRead,
    AdminRequesterRead,
    AdminSummaryRead,
    AdminUserRead,
)


router = APIRouter(prefix="/api/admin", tags=["admin"])
STALE_NODE_AFTER = timedelta(minutes=5)
RECENT_EVENT_WINDOW = timedelta(hours=24)


@router.get("/diagnostics", response_model=AdminDiagnosticsRead)
def get_admin_diagnostics(
    session: Session = Depends(get_session),
    admin_user: User = Depends(get_admin_user),
) -> AdminDiagnosticsRead:
    now = datetime.now(timezone.utc)
    stale_cutoff = now - STALE_NODE_AFTER
    event_cutoff = now - RECENT_EVENT_WINDOW

    return AdminDiagnosticsRead(
        generated_at=now,
        requested_by=AdminRequesterRead(id=admin_user.id, email=admin_user.email),
        summary=AdminSummaryRead(
            users=_count(session, User.id),
            active_users=_count_active_users(session),
            devices=_count(session, Device.id),
            active_devices=_count_active_devices(session),
            released_devices=_count(session, Device.id, Device.released_at.is_not(None)),
            archived_devices=_count(session, Device.id, Device.archived_at.is_not(None)),
            hardware_nodes=_count(session, DeviceNode.hardware_device_id),
            stale_nodes=_count(
                session,
                DeviceNode.hardware_device_id,
                (DeviceNode.last_seen_at.is_(None)) | (DeviceNode.last_seen_at < stale_cutoff),
            ),
            recent_warning_events=_count(
                session,
                DeviceDiagnosticEvent.id,
                DeviceDiagnosticEvent.occurred_at >= event_cutoff,
                DeviceDiagnosticEvent.severity.in_(("warning", "error", "critical")),
            ),
            firmware_releases=_count(session, FirmwareRelease.release_id),
        ),
        users=_admin_users(session),
        devices=_admin_devices(session, now=now),
        recent_events=_admin_events(session),
        recent_commands=_admin_commands(session),
        firmware_releases=_admin_firmware_releases(session),
    )


def _count(session: Session, column, *conditions) -> int:
    statement = select(func.count(column))
    for condition in conditions:
        statement = statement.where(condition)
    return int(session.scalar(statement) or 0)


def _count_active_devices(session: Session) -> int:
    return _count(
        session,
        Device.id,
        Device.released_at.is_(None),
        Device.archived_at.is_(None),
    )


def _count_active_users(session: Session) -> int:
    statement = (
        select(func.count(func.distinct(Device.user_id)))
        .where(Device.released_at.is_(None))
        .where(Device.archived_at.is_(None))
    )
    return int(session.scalar(statement) or 0)


def _admin_users(session: Session) -> list[AdminUserRead]:
    users = session.scalars(select(User).order_by(User.created_at.desc()).limit(50)).all()
    event_cutoff = datetime.now(timezone.utc) - RECENT_EVENT_WINDOW
    command_cutoff = datetime.now(timezone.utc) - RECENT_EVENT_WINDOW
    rows: list[AdminUserRead] = []
    for user in users:
        rows.append(
            AdminUserRead(
                id=user.id,
                email=user.email,
                name=user.name,
                created_at=user.created_at,
                device_count=_count(session, Device.id, Device.user_id == user.id),
                active_device_count=_count(
                    session,
                    Device.id,
                    Device.user_id == user.id,
                    Device.released_at.is_(None),
                    Device.archived_at.is_(None),
                ),
                last_seen_at=session.scalar(
                    select(func.max(DeviceNode.last_seen_at))
                    .join(Device, Device.id == DeviceNode.device_id)
                    .where(Device.user_id == user.id)
                ),
                recent_warning_event_count=_count_user_warning_events(session, user.id, event_cutoff),
                recent_command_count=_count_user_commands(session, user.id, command_cutoff),
                last_command_at=session.scalar(
                    select(func.max(Command.created_at))
                    .join(Device, Device.id == Command.device_id)
                    .where(Device.user_id == user.id)
                ),
            )
        )
    return rows


def _count_user_warning_events(session: Session, user_id: int, cutoff: datetime) -> int:
    statement = (
        select(func.count(DeviceDiagnosticEvent.id))
        .join(Device, Device.id == DeviceDiagnosticEvent.device_id)
        .where(Device.user_id == user_id)
        .where(DeviceDiagnosticEvent.occurred_at >= cutoff)
        .where(DeviceDiagnosticEvent.severity.in_(("warning", "error", "critical")))
    )
    return int(session.scalar(statement) or 0)


def _count_user_commands(session: Session, user_id: int, cutoff: datetime) -> int:
    statement = (
        select(func.count(Command.id))
        .join(Device, Device.id == Command.device_id)
        .where(Device.user_id == user_id)
        .where(Command.created_at >= cutoff)
    )
    return int(session.scalar(statement) or 0)


def _admin_devices(session: Session, *, now: datetime) -> list[AdminDeviceRead]:
    rows = session.execute(select(Device, User).join(User, User.id == Device.user_id).order_by(Device.created_at.desc()).limit(100)).all()
    device_reads: list[AdminDeviceRead] = []
    for device, owner in rows:
        nodes = session.scalars(select(DeviceNode).where(DeviceNode.device_id == device.id).order_by(DeviceNode.node_role, DeviceNode.node_index)).all()
        latest_snapshot = session.scalar(
            select(DeviceDiagnosticSnapshot)
            .where(DeviceDiagnosticSnapshot.device_id == device.id)
            .order_by(DeviceDiagnosticSnapshot.updated_at.desc())
            .limit(1)
        )
        device_reads.append(
            AdminDeviceRead(
                id=device.id,
                name=device.name,
                owner_email=owner.email,
                location=device.location,
                plant_type=device.plant_type,
                status=_device_status(device, nodes, now=now),
                created_at=device.created_at,
                released_at=device.released_at,
                archived_at=device.archived_at,
                latest_reading_at=session.scalar(select(func.max(SensorReading.timestamp)).where(SensorReading.device_id == device.id)),
                latest_image_at=session.scalar(select(func.max(Image.timestamp)).where(Image.device_id == device.id)),
                node_count=len(nodes),
                nodes=[
                    AdminNodeRead(
                        hardware_device_id=node.hardware_device_id,
                        node_role=node.node_role,
                        display_name=node.display_name,
                        hardware_model=node.hardware_model,
                        software_version=node.software_version,
                        status=node.status,
                        last_seen_at=node.last_seen_at,
                        ota_status=node.ota_status,
                        ota_target_version=node.ota_target_version,
                        ota_error=node.ota_error,
                    )
                    for node in nodes
                ],
                last_error_code=latest_snapshot.last_error_code if latest_snapshot is not None else None,
                last_error_message=latest_snapshot.last_error_message if latest_snapshot is not None else None,
                recent_event_count=_count(session, DeviceDiagnosticEvent.id, DeviceDiagnosticEvent.device_id == device.id),
            )
        )
    return device_reads


def _device_status(device: Device, nodes: list[DeviceNode], *, now: datetime) -> str:
    if device.archived_at is not None:
        return "archived"
    if device.released_at is not None:
        return "released"
    if not nodes:
        return "provisioning"

    stale_cutoff = now - STALE_NODE_AFTER
    if any(_is_recent(node.last_seen_at, stale_cutoff) and node.status == "online" for node in nodes):
        return "online"
    if any(node.last_seen_at for node in nodes):
        return "stale"
    return "offline"


def _is_recent(value: datetime | None, cutoff: datetime) -> bool:
    if value is None:
        return False
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value >= cutoff


def _admin_events(session: Session) -> list[AdminEventRead]:
    rows = session.execute(
        select(DeviceDiagnosticEvent, Device, User)
        .join(Device, Device.id == DeviceDiagnosticEvent.device_id)
        .join(User, User.id == Device.user_id)
        .order_by(DeviceDiagnosticEvent.occurred_at.desc())
        .limit(50)
    ).all()
    return [
        AdminEventRead(
            id=event.id,
            device_id=device.id,
            device_name=device.name,
            owner_email=owner.email,
            hardware_device_id=event.hardware_device_id,
            event_type=event.event_type,
            severity=event.severity,
            code=event.code,
            message=event.message,
            occurred_at=event.occurred_at,
        )
        for event, device, owner in rows
    ]


def _admin_commands(session: Session) -> list[AdminCommandRead]:
    rows = session.execute(
        select(Command, Device, User)
        .join(Device, Device.id == Command.device_id)
        .join(User, User.id == Device.user_id)
        .order_by(Command.created_at.desc())
        .limit(50)
    ).all()
    return [
        AdminCommandRead(
            id=command.id,
            device_id=device.id,
            device_name=device.name,
            owner_email=owner.email,
            target=command.target.value if hasattr(command.target, "value") else str(command.target),
            action=command.action.value if hasattr(command.action, "value") else str(command.action),
            value=command.value,
            status=command.status.value if hasattr(command.status, "value") else str(command.status),
            message=command.message,
            created_at=command.created_at,
            sent_at=command.sent_at,
            completed_at=command.completed_at,
        )
        for command, device, owner in rows
        if command.id is not None
    ]


def _admin_firmware_releases(session: Session) -> list[AdminFirmwareReleaseRead]:
    releases = session.scalars(select(FirmwareRelease).order_by(FirmwareRelease.created_at.desc()).limit(20)).all()
    return [
        AdminFirmwareReleaseRead(
            release_id=release.release_id,
            node_role=release.node_role,
            hardware_model=release.hardware_model,
            version=release.version,
            channel=release.channel,
            rollout_percentage=release.rollout_percentage,
            rollback_version=release.rollback_version,
            status=release.status,
            published_at=release.published_at,
        )
        for release in releases
    ]
