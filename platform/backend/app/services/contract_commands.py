from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.contracts import CommandPayload, CommandPollResponse, DeviceMessage, EventType, MessageType, NodeRole, ProtocolValidationError
from app.contracts.device_protocol import PLANTLAB_SCHEMA_VERSION, validate_supported_schema_version
from app.models import Command, CommandStatus, DeviceNode
from app.services.command_events import add_command_event, build_command_payload
from app.services.commands import DEFAULT_COMMAND_TIMEOUT_SECONDS, expire_stale_commands


logger = logging.getLogger(__name__)
MIN_CONTRACT_POLL_FIRMWARE_VERSION = "0.1.0"


def poll_contract_commands(
    session: Session,
    *,
    device_id: int,
    poller_node: DeviceNode,
    schema_version: str = PLANTLAB_SCHEMA_VERSION,
    firmware_version: str | None = None,
    hardware_model: str | None = None,
    limit: int = 10,
    timeout_seconds: int = DEFAULT_COMMAND_TIMEOUT_SECONDS,
) -> CommandPollResponse:
    try:
        validate_supported_schema_version(schema_version)
    except ValueError as exc:
        raise ProtocolValidationError("unsupported_schema_version", str(exc)) from exc

    if hardware_model and poller_node.hardware_model and hardware_model != poller_node.hardware_model:
        logger.warning(
            "Contract command poll hardware_model mismatch hardware_device_id=%s registered=%s reported=%s",
            poller_node.hardware_device_id,
            poller_node.hardware_model,
            hardware_model,
        )
        return CommandPollResponse(schema_version=schema_version, commands=[])
    if firmware_version and _version_code(firmware_version) < _version_code(MIN_CONTRACT_POLL_FIRMWARE_VERSION):
        logger.warning(
            "Contract command poll firmware_version unsupported hardware_device_id=%s firmware_version=%s minimum=%s",
            poller_node.hardware_device_id,
            firmware_version,
            MIN_CONTRACT_POLL_FIRMWARE_VERSION,
        )
        return CommandPollResponse(schema_version=schema_version, commands=[])

    expire_stale_commands(session, device_id, timeout_seconds)
    commands = list(
        session.scalars(
            select(Command)
            .where(Command.device_id == device_id)
            .where(Command.status == CommandStatus.PENDING)
            .order_by(Command.created_at.asc())
            .limit(limit * 3)
        )
    )

    now = datetime.now(timezone.utc)
    envelopes: list[DeviceMessage[CommandPayload]] = []
    for command in commands:
        payload = build_command_payload(session, command)
        if payload is None:
            logger.warning("Skipping unsupported contract command id=%s target=%s action=%s", command.id, command.target, command.action)
            continue
        if not _payload_matches_polling_node(payload, poller_node):
            continue
        command.status = CommandStatus.SENT
        command.sent_at = now
        envelope = _command_envelope(
            command=command,
            payload=payload,
            poller_node=poller_node,
            schema_version=schema_version,
            sent_at=now,
        )
        envelopes.append(envelope)
        add_command_event(
            session,
            command,
            event_type=EventType.COMMAND_POLLED,
            status="polled",
            correlation_id=payload.command_id,
            result={
                "poller_hardware_device_id": poller_node.hardware_device_id,
                "poller_node_role": _node_role_for_contract(poller_node.node_role).value,
                "firmware_version": firmware_version,
            },
            occurred_at=now,
        )
        add_command_event(
            session,
            command,
            event_type=EventType.COMMAND_SENT,
            status="sent",
            correlation_id=payload.command_id,
            result={
                "transport": "contract_poll",
                "poller_hardware_device_id": poller_node.hardware_device_id,
            },
            occurred_at=now,
        )
        if len(envelopes) >= limit:
            break

    session.commit()
    return CommandPollResponse(schema_version=schema_version, commands=envelopes)


def _command_envelope(
    *,
    command: Command,
    payload: CommandPayload,
    poller_node: DeviceNode,
    schema_version: str,
    sent_at: datetime,
) -> DeviceMessage[CommandPayload]:
    command_id = int(command.id or 0)
    return DeviceMessage[CommandPayload](
        schema_version=schema_version,
        message_id=f"cmdmsg_{command_id}_{int(sent_at.timestamp() * 1000)}",
        device_id=command.device_id,
        hardware_device_id=poller_node.hardware_device_id,
        node_role=_node_role_for_contract(poller_node.node_role),
        message_type=MessageType.COMMAND,
        sent_at=sent_at,
        payload=payload,
    )


def _payload_matches_polling_node(payload: CommandPayload, poller_node: DeviceNode) -> bool:
    poller_role = _node_role_for_contract(poller_node.node_role).value
    target_role = payload.target.node_role.value
    target_hardware_device_id = payload.target.hardware_device_id
    if target_hardware_device_id and target_hardware_device_id == poller_node.hardware_device_id:
        return True
    if target_role == poller_role:
        return True
    # Current product topology lets the master act as the camera gateway. This
    # keeps contract polling compatible with existing ESP-NOW camera forwarding.
    if poller_role == NodeRole.MASTER.value and target_role == NodeRole.CAMERA.value:
        return True
    return False


def _node_role_for_contract(node_role: str | None) -> NodeRole:
    normalized = str(node_role or "").strip().lower()
    if normalized == "single_board":
        return NodeRole.MASTER
    return NodeRole(normalized)


def _version_code(version: str | None) -> int:
    if not version:
        return 0
    parts = str(version).strip().lstrip("v").split(".")
    numeric_parts: list[int] = []
    for part in parts[:3]:
        digits = ""
        for char in part:
            if not char.isdigit():
                break
            digits += char
        numeric_parts.append(int(digits or 0))
    while len(numeric_parts) < 3:
        numeric_parts.append(0)
    return numeric_parts[0] * 1_000_000 + numeric_parts[1] * 1_000 + numeric_parts[2]
