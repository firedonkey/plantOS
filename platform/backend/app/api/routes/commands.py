from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_device_from_token
from app.db.session import get_session
from app.models import User
from app.schemas.commands import CommandAck, CommandCreate, CommandRead
from app.services.commands import (
    acknowledge_command,
    create_command,
    get_command_for_device,
    list_commands_for_device,
    take_pending_commands,
)
from app.services.devices import get_device_for_user


router = APIRouter(prefix="/api/devices/{device_id}/commands", tags=["commands"])


@router.get("", response_model=list[CommandRead])
def list_commands(
    device_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    device = get_device_for_user(session, current_user, device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found.")
    return list_commands_for_device(session, device.id)


@router.post("", response_model=CommandRead, status_code=201)
def create_device_command(
    device_id: int,
    payload: CommandCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    device = get_device_for_user(session, current_user, device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found.")
    return create_command(session, device.id, payload)


@router.get("/pending", response_model=list[CommandRead])
def poll_pending_commands(
    device_id: int,
    request: Request,
    session: Session = Depends(get_session),
):
    device = get_device_from_token(request, session)
    if device is None:
        raise HTTPException(status_code=401, detail="Valid device token required.")
    if device.id != device_id:
        raise HTTPException(status_code=403, detail="Device token does not match device_id.")
    return take_pending_commands(session, device.id)


@router.post("/{command_id}/ack", response_model=CommandRead)
def acknowledge_device_command(
    device_id: int,
    command_id: int,
    payload: CommandAck,
    request: Request,
    session: Session = Depends(get_session),
):
    device = get_device_from_token(request, session)
    if device is None:
        raise HTTPException(status_code=401, detail="Valid device token required.")
    if device.id != device_id:
        raise HTTPException(status_code=403, detail="Device token does not match device_id.")

    command = get_command_for_device(session, device.id, command_id)
    if command is None:
        raise HTTPException(status_code=404, detail="Command not found.")
    return acknowledge_command(session, command, payload)
