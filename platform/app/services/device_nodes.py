from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.device_node import DeviceNode


@dataclass(frozen=True)
class DeviceGroupStatus:
    status: str
    master_status: str | None
    camera_statuses: tuple[str, ...]


def build_node_summary(nodes: list[DeviceNode]) -> dict:
    group_status = derive_device_group_status(nodes)
    primary = next(
        (node for node in nodes if node.node_role in {"single_board", "master"}),
        None,
    )
    cameras = [node for node in nodes if node.node_role == "camera"]
    return {
        "overall_status": group_status.status,
        "primary": _node_summary_item(primary) if primary is not None else None,
        "cameras": [_node_summary_item(node) for node in cameras],
    }


def list_nodes_for_device(session: Session, device_id: int) -> list[DeviceNode]:
    nodes = list(
        session.scalars(
            select(DeviceNode)
            .where(DeviceNode.device_id == device_id)
            .order_by(DeviceNode.hardware_device_id)
        )
    )
    return sorted(nodes, key=_node_sort_key)


def get_node_by_hardware_id(session: Session, hardware_device_id: str) -> DeviceNode | None:
    return session.scalar(
        select(DeviceNode).where(DeviceNode.hardware_device_id == hardware_device_id)
    )


def get_node_for_device(
    session: Session,
    *,
    device_id: int,
    hardware_device_id: str,
) -> DeviceNode | None:
    return session.scalar(
        select(DeviceNode)
        .where(DeviceNode.device_id == device_id)
        .where(DeviceNode.hardware_device_id == hardware_device_id)
    )


def upsert_device_node(
    session: Session,
    *,
    device_id: int,
    hardware_device_id: str,
    node_role: str = "single_board",
    node_index: int | None = None,
    display_name: str | None = None,
    hardware_model: str | None = None,
    hardware_version: str | None = None,
    software_version: str | None = None,
    capabilities: dict | None = None,
    status: str = "provisioning",
    last_seen_at: datetime | None = None,
) -> DeviceNode:
    node = get_node_by_hardware_id(session, hardware_device_id)
    if node is None:
        node = DeviceNode(
            device_id=device_id,
            hardware_device_id=hardware_device_id,
        )
        session.add(node)

    node.device_id = device_id
    node.node_role = node_role
    node.node_index = node_index
    node.display_name = display_name
    node.hardware_model = hardware_model
    node.hardware_version = hardware_version
    node.software_version = software_version
    node.capabilities = capabilities or {}
    node.status = status
    node.last_seen_at = last_seen_at
    node.updated_at = datetime.now(timezone.utc)
    session.commit()
    session.refresh(node)
    return node


def update_node_heartbeat(
    session: Session,
    hardware_device_id: str,
    *,
    status: str,
    seen_at: datetime | None = None,
) -> DeviceNode | None:
    node = get_node_by_hardware_id(session, hardware_device_id)
    if node is None:
        return None

    node.status = status
    node.last_seen_at = seen_at or datetime.now(timezone.utc)
    node.updated_at = datetime.now(timezone.utc)
    session.add(node)
    session.commit()
    session.refresh(node)
    return node


def derive_device_group_status(nodes: list[DeviceNode]) -> DeviceGroupStatus:
    if not nodes:
        return DeviceGroupStatus(status="offline", master_status=None, camera_statuses=())

    single_board = next((node for node in nodes if node.node_role == "single_board"), None)
    if single_board is not None:
        return DeviceGroupStatus(
            status=_normalized_node_status(single_board.status),
            master_status=_normalized_node_status(single_board.status),
            camera_statuses=(),
        )

    master = next((node for node in nodes if node.node_role == "master"), None)
    master_status = _normalized_node_status(master.status if master else None)
    camera_statuses = tuple(
        _normalized_node_status(node.status)
        for node in nodes
        if node.node_role == "camera"
    )

    if master_status != "online":
        return DeviceGroupStatus(
            status=master_status,
            master_status=master_status,
            camera_statuses=camera_statuses,
        )

    if camera_statuses and any(status != "online" for status in camera_statuses):
        return DeviceGroupStatus(
            status="degraded",
            master_status=master_status,
            camera_statuses=camera_statuses,
        )

    return DeviceGroupStatus(
        status="online",
        master_status=master_status,
        camera_statuses=camera_statuses,
    )


def _normalized_node_status(status: str | None) -> str:
    if not status:
        return "offline"
    normalized = status.strip().lower()
    if normalized in {"online", "offline", "provisioning", "error", "degraded"}:
        return normalized
    return "offline"


def _node_sort_key(node: DeviceNode) -> tuple[int, int, str]:
    role_order = {
        "single_board": 0,
        "master": 1,
        "camera": 2,
    }
    return (
        role_order.get(node.node_role, 99),
        node.node_index if node.node_index is not None else 9999,
        node.hardware_device_id,
    )


def _node_summary_item(node: DeviceNode) -> dict:
    return {
        "hardware_device_id": node.hardware_device_id,
        "node_role": node.node_role,
        "node_index": node.node_index,
        "display_name": node.display_name,
        "status": _normalized_node_status(node.status),
        "last_seen_at": node.last_seen_at.isoformat() if node.last_seen_at is not None else None,
    }
