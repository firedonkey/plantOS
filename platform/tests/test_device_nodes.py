from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models import Device, User
from app.models.base import Base
from app.services.device_nodes import (
    derive_device_group_status,
    get_node_by_hardware_id,
    list_nodes_for_device,
    update_node_heartbeat,
    upsert_device_node,
)


def build_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return Session(engine)


def test_upsert_and_list_nodes_for_device():
    with build_session() as session:
        user = User(email="grower@example.com", password_hash="hash")
        session.add(user)
        session.commit()
        session.refresh(user)

        device = Device(user_id=user.id, name="Lab ESP32")
        session.add(device)
        session.commit()
        session.refresh(device)

        upsert_device_node(
            session,
            device_id=device.id,
            hardware_device_id="cam-02",
            node_role="camera",
            node_index=2,
            display_name="Camera 2",
            status="offline",
        )
        upsert_device_node(
            session,
            device_id=device.id,
            hardware_device_id="master-01",
            node_role="master",
            display_name="Master",
            status="online",
        )
        upsert_device_node(
            session,
            device_id=device.id,
            hardware_device_id="cam-01",
            node_role="camera",
            node_index=1,
            display_name="Camera 1",
            status="online",
        )

        nodes = list_nodes_for_device(session, device.id)
        assert [node.hardware_device_id for node in nodes] == ["master-01", "cam-01", "cam-02"]
        assert nodes[0].display_name == "Master"
        assert nodes[1].display_name == "Camera 1"


def test_update_node_heartbeat_changes_status_and_last_seen():
    with build_session() as session:
        user = User(email="grower@example.com", password_hash="hash")
        session.add(user)
        session.commit()
        session.refresh(user)

        device = Device(user_id=user.id, name="Lab ESP32")
        session.add(device)
        session.commit()
        session.refresh(device)

        upsert_device_node(
            session,
            device_id=device.id,
            hardware_device_id="master-01",
            node_role="master",
            status="provisioning",
        )

        seen_at = datetime(2026, 5, 2, 18, 30, tzinfo=timezone.utc)
        node = update_node_heartbeat(session, "master-01", status="online", seen_at=seen_at)

        assert node is not None
        assert node.status == "online"
        assert node.last_seen_at.replace(tzinfo=timezone.utc) == seen_at
        assert get_node_by_hardware_id(session, "master-01").status == "online"


def test_derive_device_group_status_for_single_board_and_grouped_devices():
    with build_session() as session:
        user = User(email="grower@example.com", password_hash="hash")
        session.add(user)
        session.commit()
        session.refresh(user)

        pi_device = Device(user_id=user.id, name="Pi Device")
        esp_device = Device(user_id=user.id, name="ESP Device")
        session.add(pi_device)
        session.add(esp_device)
        session.commit()
        session.refresh(pi_device)
        session.refresh(esp_device)

        upsert_device_node(
            session,
            device_id=pi_device.id,
            hardware_device_id="pi-001",
            node_role="single_board",
            status="online",
        )
        upsert_device_node(
            session,
            device_id=esp_device.id,
            hardware_device_id="master-01",
            node_role="master",
            status="online",
        )
        upsert_device_node(
            session,
            device_id=esp_device.id,
            hardware_device_id="cam-01",
            node_role="camera",
            node_index=1,
            status="offline",
        )

        pi_status = derive_device_group_status(list_nodes_for_device(session, pi_device.id))
        esp_status = derive_device_group_status(list_nodes_for_device(session, esp_device.id))

        assert pi_status.status == "online"
        assert pi_status.master_status == "online"
        assert pi_status.camera_statuses == ()

        assert esp_status.status == "degraded"
        assert esp_status.master_status == "online"
        assert esp_status.camera_statuses == ("offline",)
