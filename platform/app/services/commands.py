from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Command, CommandStatus
from app.schemas.commands import CommandAck, CommandCreate


def create_command(session: Session, device_id: int, payload: CommandCreate) -> Command:
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
    return command


def list_commands_for_device(session: Session, device_id: int, limit: int = 20) -> list[Command]:
    return list(
        session.scalars(
            select(Command)
            .where(Command.device_id == device_id)
            .order_by(Command.created_at.desc())
            .limit(limit)
        )
    )


def take_pending_commands(session: Session, device_id: int, limit: int = 10) -> list[Command]:
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
        command.status = CommandStatus.SENT
        command.sent_at = now
    session.commit()
    for command in commands:
        session.refresh(command)
    return commands


def get_command_for_device(session: Session, device_id: int, command_id: int) -> Command | None:
    return session.scalar(
        select(Command).where(
            Command.id == command_id,
            Command.device_id == device_id,
        )
    )


def acknowledge_command(session: Session, command: Command, payload: CommandAck) -> Command:
    command.status = payload.status
    command.message = payload.message
    command.completed_at = datetime.now(timezone.utc)
    session.add(command)
    session.commit()
    session.refresh(command)
    return command
