from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Command, CommandStatus
from app.schemas.commands import CommandAck, CommandCreate
from app.contracts import EventType
from app.services.command_events import add_command_event, event_type_for_result_status
from app.services.state_changes import emit_command_actuator_state_change


DEFAULT_COMMAND_TIMEOUT_SECONDS = 20
CAPTURE_COMMAND_TIMEOUT_SECONDS = 150
OTA_COMMAND_TIMEOUT_SECONDS = 1800


def _timeout_seconds_for_command(command: Command, default_timeout_seconds: int) -> int:
    if command.target == "camera" and command.action == "capture":
        return max(default_timeout_seconds, CAPTURE_COMMAND_TIMEOUT_SECONDS)
    if command.target == "ota" and command.action == "start":
        return max(default_timeout_seconds, OTA_COMMAND_TIMEOUT_SECONDS)
    return default_timeout_seconds


def _command_created_at(command: Command) -> datetime:
    created_at = command.created_at
    if created_at.tzinfo is None:
        return created_at.replace(tzinfo=timezone.utc)
    return created_at


def create_command(session: Session, device_id: int, payload: CommandCreate) -> Command:
    expire_stale_commands(session, device_id)
    existing_command = find_active_command(session, device_id, payload)
    if existing_command is not None:
        return existing_command

    command = Command(
        device_id=device_id,
        target=payload.target,
        action=payload.action,
        value=payload.value,
        status=CommandStatus.PENDING,
    )
    session.add(command)
    session.commit()
    session.refresh(command)
    add_command_event(
        session,
        command,
        event_type=EventType.COMMAND_QUEUED,
        status="queued",
    )
    session.commit()
    session.refresh(command)
    return command


def find_active_command(session: Session, device_id: int, payload: CommandCreate) -> Command | None:
    return session.scalar(
        select(Command)
        .where(
            Command.device_id == device_id,
            Command.target == payload.target,
            Command.action == payload.action,
            Command.value == payload.value,
            Command.status.in_([CommandStatus.PENDING, CommandStatus.SENT, CommandStatus.IN_PROGRESS]),
        )
        .order_by(Command.created_at.desc())
        .limit(1)
    )


def list_commands_for_device(
    session: Session,
    device_id: int,
    limit: int = 20,
    timeout_seconds: int = DEFAULT_COMMAND_TIMEOUT_SECONDS,
) -> list[Command]:
    expire_stale_commands(session, device_id, timeout_seconds)
    return list(
        session.scalars(
            select(Command)
            .where(Command.device_id == device_id)
            .order_by(Command.created_at.desc())
            .limit(limit)
        )
    )


def take_pending_commands(
    session: Session,
    device_id: int,
    limit: int = 10,
    timeout_seconds: int = DEFAULT_COMMAND_TIMEOUT_SECONDS,
) -> list[Command]:
    return _claim_pending_commands(
        session,
        device_id,
        claimed_status=CommandStatus.SENT,
        limit=limit,
        timeout_seconds=timeout_seconds,
    )


def claim_pending_commands(
    session: Session,
    device_id: int,
    limit: int = 10,
    timeout_seconds: int = DEFAULT_COMMAND_TIMEOUT_SECONDS,
) -> list[Command]:
    return _claim_pending_commands(
        session,
        device_id,
        claimed_status=CommandStatus.IN_PROGRESS,
        limit=limit,
        timeout_seconds=timeout_seconds,
    )


def _claim_pending_commands(
    session: Session,
    device_id: int,
    claimed_status: CommandStatus,
    limit: int = 10,
    timeout_seconds: int = DEFAULT_COMMAND_TIMEOUT_SECONDS,
) -> list[Command]:
    expire_stale_commands(session, device_id, timeout_seconds)
    commands = list(
        session.scalars(
            select(Command)
            .where(
                Command.device_id == device_id,
                Command.status == CommandStatus.PENDING,
            )
            .order_by(Command.created_at.asc())
            .limit(limit)
        )
    )
    now = datetime.now(timezone.utc)
    for command in commands:
        command.status = claimed_status
        command.sent_at = now
        add_command_event(
            session,
            command,
            event_type=EventType.COMMAND_SENT,
            status="sent",
            occurred_at=now,
        )
        if claimed_status == CommandStatus.IN_PROGRESS:
            add_command_event(
                session,
                command,
                event_type=EventType.COMMAND_ACKED,
                status="acked",
                occurred_at=now,
            )
            add_command_event(
                session,
                command,
                event_type=EventType.COMMAND_IN_PROGRESS,
                status="in_progress",
                occurred_at=now,
            )
    session.commit()
    for command in commands:
        session.refresh(command)
    return commands


def expire_stale_commands(
    session: Session,
    device_id: int,
    timeout_seconds: int = DEFAULT_COMMAND_TIMEOUT_SECONDS,
) -> None:
    commands = list(
        session.scalars(
            select(Command).where(
                Command.device_id == device_id,
                Command.status.in_([CommandStatus.PENDING, CommandStatus.SENT, CommandStatus.IN_PROGRESS]),
            )
        )
    )
    if not commands:
        return

    now = datetime.now(timezone.utc)
    stale_commands = [
        command
        for command in commands
        if _command_created_at(command) < now - timedelta(seconds=_timeout_seconds_for_command(command, timeout_seconds))
    ]
    if not stale_commands:
        return

    for command in stale_commands:
        command.status = CommandStatus.TIMED_OUT
        command.completed_at = now
        if command.sent_at:
            command.message = "Timed out waiting for device acknowledgement."
        else:
            command.message = "Timed out waiting for device pickup."
        add_command_event(
            session,
            command,
            event_type=EventType.COMMAND_TIMED_OUT,
            status="timed_out",
            error_code="TIMEOUT",
            occurred_at=now,
        )
    session.commit()


def get_command_for_device(session: Session, device_id: int, command_id: int) -> Command | None:
    return session.scalar(
        select(Command).where(
            Command.id == command_id,
            Command.device_id == device_id,
        )
    )


def acknowledge_command(session: Session, command: Command, payload: CommandAck) -> Command:
    return report_command_result(
        session,
        command,
        status=payload.status,
        message=payload.message,
        light_on=payload.light_on,
        light_intensity_percent=payload.light_intensity_percent,
        pump_on=payload.pump_on,
    )


def report_command_result(
    session: Session,
    command: Command,
    *,
    status: CommandStatus,
    message: str | None = None,
    light_on: bool | None = None,
    light_intensity_percent: int | None = None,
    pump_on: bool | None = None,
    event_type: EventType | None = None,
    event_status: str | None = None,
    error_code: str | None = None,
    result: dict | None = None,
) -> Command:
    now = datetime.now(timezone.utc)
    previous_light_state = {
        "enabled": command.device.current_light_on,
        "brightness_percent": command.device.current_light_intensity_percent,
    }
    command.status = status
    command.message = message
    command.light_on = light_on
    command.light_intensity_percent = light_intensity_percent
    command.pump_on = pump_on
    command.completed_at = now if status in {CommandStatus.COMPLETED, CommandStatus.FAILED, CommandStatus.TIMED_OUT} else None
    if light_on is not None:
        command.device.current_light_on = light_on
    if light_intensity_percent is not None:
        command.device.current_light_intensity_percent = light_intensity_percent
    if pump_on is not None:
        command.device.current_pump_on = pump_on
    if light_on is not None or light_intensity_percent is not None or pump_on is not None:
        command.device.status_message = message
        command.device.status_updated_at = now
    add_command_event(
        session,
        command,
        event_type=event_type or event_type_for_result_status(status.value if hasattr(status, "value") else str(status)),
        status=event_status or (status.value if hasattr(status, "value") else str(status)),
        result=result or {
            "light_on": light_on,
            "light_intensity_percent": light_intensity_percent,
            "pump_on": pump_on,
        },
        error_code=error_code or ("INTERNAL_ERROR" if status == CommandStatus.FAILED else None),
        occurred_at=now,
    )
    session.add(command)
    session.commit()
    if status == CommandStatus.COMPLETED and (light_on is not None or light_intensity_percent is not None):
        emit_command_actuator_state_change(
            session,
            command=command,
            previous=previous_light_state,
            current={
                "enabled": command.device.current_light_on,
                "brightness_percent": command.device.current_light_intensity_percent,
            },
            occurred_at=now,
        )
    session.refresh(command)
    return command
