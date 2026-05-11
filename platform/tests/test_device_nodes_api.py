from collections.abc import Generator
from base64 import b64encode
from datetime import datetime, timezone
import json

from fastapi.testclient import TestClient
from itsdangerous import TimestampSigner
from sqlalchemy import text
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import Session, sessionmaker

from app.api.deps import get_current_user, get_optional_current_user
from app.core.settings import get_settings
from app.db.session import get_session
from app.main import app
from app.models import Device, DeviceNode, SensorReading, User
from app.models.base import Base
from app.services.devices import delete_device_for_user
from app.services.device_nodes import get_node_by_hardware_id, upsert_device_node


def build_client_with_device(set_session_cookie: bool = False):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    with TestingSessionLocal() as session:
        user = User(email="grower@example.com", google_sub="google-123", name="Grower")
        session.add(user)
        session.commit()
        session.refresh(user)

        device = Device(
            user_id=user.id,
            name="ESP Device",
            api_token="test-device-token",
            created_at=datetime.now(timezone.utc),
        )
        session.add(device)
        session.commit()
        session.refresh(device)
        user_id = user.id
        device_id = device.id

    def override_session() -> Generator[Session, None, None]:
        with TestingSessionLocal() as session:
            yield session

    def override_current_user() -> User:
        with TestingSessionLocal() as session:
            return session.get(User, user_id)

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_optional_current_user] = override_current_user
    client = TestClient(app)
    if set_session_cookie:
        client.cookies.set("session", signed_session_cookie({"user_id": user_id}))

    return client, TestingSessionLocal, user_id, device_id


def signed_session_cookie(payload: dict) -> str:
    data = b64encode(json.dumps(payload).encode("utf-8"))
    return TimestampSigner(get_settings().session_secret).sign(data).decode("utf-8")


def teardown_overrides() -> None:
    app.dependency_overrides.clear()


def ensure_provisioning_cleanup_tables(session: Session) -> None:
    session.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS device_serial_numbers (
              serial_number TEXT PRIMARY KEY,
              hardware_model TEXT,
              status TEXT NOT NULL DEFAULT 'available',
              claimed_by_user_id INTEGER,
              claimed_by_device_id INTEGER,
              claimed_at DATETIME,
              created_at DATETIME,
              updated_at DATETIME
            )
            """
        )
    )
    session.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS device_claim_tokens (
              claim_token TEXT PRIMARY KEY,
              serial_number TEXT,
              device_name TEXT,
              location TEXT,
              user_id INTEGER NOT NULL,
              created_at DATETIME,
              expires_at DATETIME,
              used_at DATETIME,
              used_by_device_id INTEGER
            )
            """
        )
    )
    session.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS device_access_tokens (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              device_id INTEGER NOT NULL,
              token_hash TEXT NOT NULL UNIQUE,
              created_at DATETIME,
              revoked_at DATETIME
            )
            """
        )
    )
    session.commit()


def test_device_node_heartbeat_updates_registered_node():
    client, TestingSessionLocal, _, device_id = build_client_with_device()
    try:
        with TestingSessionLocal() as session:
            upsert_device_node(
                session,
                device_id=device_id,
                hardware_device_id="master-01",
                node_role="master",
                display_name="Master",
                status="provisioning",
            )

        response = client.post(
            "/api/device-nodes/heartbeat",
            json={
                "device_id": device_id,
                "hardware_device_id": "master-01",
                "node_role": "master",
                "status": "online",
            },
            headers={"X-Device-Token": "test-device-token"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["hardware_device_id"] == "master-01"
        assert payload["node_role"] == "master"
        assert payload["status"] == "online"
        assert payload["last_seen_at"] is not None
    finally:
        teardown_overrides()


def test_device_node_register_creates_camera_node_for_token_device():
    client, TestingSessionLocal, _, device_id = build_client_with_device()
    try:
        response = client.post(
            "/api/device-nodes/register",
            json={
                "device_id": device_id,
                "hardware_device_id": "cam-live-01",
                "node_role": "camera",
                "node_index": 1,
                "display_name": "Camera 1",
                "hardware_model": "xiao_esp32s3_camera",
                "hardware_version": "XIAO ESP32S3 Sense",
                "software_version": "0.1.0",
                "capabilities": {"camera": True},
                "status": "online",
            },
            headers={"X-Device-Token": "test-device-token"},
        )

        assert response.status_code == 201
        payload = response.json()
        assert payload["device_id"] == device_id
        assert payload["hardware_device_id"] == "cam-live-01"
        assert payload["node_role"] == "camera"
        assert payload["node_index"] == 1
        assert payload["display_name"] == "Camera 1"
        assert payload["hardware_model"] == "xiao_esp32s3_camera"
        assert payload["status"] == "online"

        with TestingSessionLocal() as session:
            node = get_node_by_hardware_id(session, "cam-live-01")
            assert node is not None
            assert node.device_id == device_id
    finally:
        teardown_overrides()


def test_device_summary_json_includes_node_summary():
    client, TestingSessionLocal, _, device_id = build_client_with_device(set_session_cookie=True)
    try:
        with TestingSessionLocal() as session:
            upsert_device_node(
                session,
                device_id=device_id,
                hardware_device_id="master-01",
                node_role="master",
                display_name="Master",
                status="online",
            )
            upsert_device_node(
                session,
                device_id=device_id,
                hardware_device_id="cam-01",
                node_role="camera",
                node_index=1,
                display_name="Camera 1",
                status="offline",
            )

        response = client.get(f"/devices/{device_id}/summary.json")

        assert response.status_code == 200
        payload = response.json()
        assert payload["node_summary"]["overall_status"] == "degraded"
        assert payload["node_summary"]["primary"]["node_role"] == "master"
        assert payload["node_summary"]["primary"]["display_name"] == "Master"
        assert payload["node_summary"]["cameras"][0]["node_role"] == "camera"
        assert payload["node_summary"]["cameras"][0]["display_name"] == "Camera 1"
        assert payload["node_summary"]["cameras"][0]["status"] == "offline"
    finally:
        teardown_overrides()


def test_device_detail_page_shows_raspberry_pi_component():
    client, TestingSessionLocal, _, device_id = build_client_with_device(set_session_cookie=True)
    try:
        with TestingSessionLocal() as session:
            upsert_device_node(
                session,
                device_id=device_id,
                hardware_device_id="pi-001",
                node_role="single_board",
                display_name="Raspberry Pi",
                status="online",
            )

        response = client.get(f"/devices/{device_id}")

        assert response.status_code == 200
        assert "Device Components" in response.text
        assert "Raspberry Pi" in response.text
        assert "Single Board" in response.text
        assert "Online" in response.text
    finally:
        teardown_overrides()


def test_device_detail_page_shows_master_and_camera_components():
    client, TestingSessionLocal, _, device_id = build_client_with_device(set_session_cookie=True)
    try:
        with TestingSessionLocal() as session:
            upsert_device_node(
                session,
                device_id=device_id,
                hardware_device_id="master-01",
                node_role="master",
                display_name="Master",
                status="online",
            )
            upsert_device_node(
                session,
                device_id=device_id,
                hardware_device_id="cam-01",
                node_role="camera",
                node_index=1,
                display_name="Camera 1",
                status="provisioning",
            )

        response = client.get(f"/devices/{device_id}")

        assert response.status_code == 200
        assert "Device Components" in response.text
        assert "Master" in response.text
        assert "Camera 1" in response.text
        assert "Provisioning" in response.text
    finally:
        teardown_overrides()


def test_devices_page_shows_compact_health_for_raspberry_pi_card():
    client, TestingSessionLocal, user_id, device_id = build_client_with_device(set_session_cookie=True)
    try:
        with TestingSessionLocal() as session:
            device = session.get(Device, device_id)
            device.name = "Kitchen Rose"
            device.user_id = user_id
            session.add(device)
            session.commit()
            upsert_device_node(
                session,
                device_id=device_id,
                hardware_device_id="pi-001",
                node_role="single_board",
                display_name="Raspberry Pi",
                status="online",
            )

        response = client.get("/devices")

        assert response.status_code == 200
        assert "Raspberry Pi online" in response.text
        assert response.text.count("View dashboard") == 1
    finally:
        teardown_overrides()


def test_devices_page_shows_compact_health_for_esp32_group_card():
    client, TestingSessionLocal, user_id, device_id = build_client_with_device(set_session_cookie=True)
    try:
        with TestingSessionLocal() as session:
            device = session.get(Device, device_id)
            device.name = "Device 1"
            device.user_id = user_id
            session.add(device)
            session.commit()
            upsert_device_node(
                session,
                device_id=device_id,
                hardware_device_id="master-01",
                node_role="master",
                display_name="Master",
                status="online",
            )
            upsert_device_node(
                session,
                device_id=device_id,
                hardware_device_id="cam-01",
                node_role="camera",
                node_index=1,
                display_name="Camera 1",
                status="provisioning",
            )

        response = client.get("/devices")

        assert response.status_code == 200
        assert "Master online" in response.text
        assert "1 camera needs setup" in response.text
        assert response.text.count("View dashboard") == 1
    finally:
        teardown_overrides()


def test_devices_page_keeps_one_card_per_logical_device_in_mixed_account():
    client, TestingSessionLocal, user_id, device_id = build_client_with_device(set_session_cookie=True)
    try:
        with TestingSessionLocal() as session:
            primary_device = session.get(Device, device_id)
            primary_device.name = "Device 1"
            primary_device.user_id = user_id
            session.add(primary_device)
            second_device = Device(
                user_id=user_id,
                name="Kitchen Rose",
                api_token="pi-device-token",
                created_at=datetime.now(timezone.utc),
            )
            session.add(second_device)
            session.commit()
            session.refresh(second_device)

            upsert_device_node(
                session,
                device_id=primary_device.id,
                hardware_device_id="master-01",
                node_role="master",
                display_name="Master",
                status="online",
            )
            upsert_device_node(
                session,
                device_id=primary_device.id,
                hardware_device_id="cam-01",
                node_role="camera",
                node_index=1,
                display_name="Camera 1",
                status="online",
            )
            upsert_device_node(
                session,
                device_id=second_device.id,
                hardware_device_id="pi-001",
                node_role="single_board",
                display_name="Raspberry Pi",
                status="online",
            )

        response = client.get("/devices")

        assert response.status_code == 200
        assert response.text.count("View dashboard") == 2
        assert "Master online" in response.text
        assert "1 camera online" in response.text
        assert "Raspberry Pi online" in response.text
    finally:
        teardown_overrides()


def test_setup_status_waits_for_image_for_single_board_device():
    client, TestingSessionLocal, user_id, device_id = build_client_with_device(set_session_cookie=True)
    try:
        with TestingSessionLocal() as session:
            device = session.get(Device, device_id)
            device.name = "Kitchen Rose"
            device.location = "Kitchen"
            device.user_id = user_id
            session.add(device)
            session.commit()

            upsert_device_node(
                session,
                device_id=device_id,
                hardware_device_id="pi-001",
                node_role="single_board",
                display_name="Raspberry Pi",
                status="online",
            )
            session.add(
                SensorReading(
                    device_id=device_id,
                    moisture=41.0,
                    temperature=23.1,
                    humidity=50.2,
                )
            )
            session.commit()

        response = client.get(
            "/setup/status.json",
            params={"device_name": "Kitchen Rose", "location": "Kitchen", "expect_image": "0"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["device_found"] is True
        assert payload["has_reading"] is True
        assert payload["has_image"] is False
        assert payload["expect_image"] is True
        assert payload["ready"] is False
    finally:
        teardown_overrides()


def test_setup_status_for_master_only_device_is_ready_after_first_reading_without_image():
    client, TestingSessionLocal, user_id, device_id = build_client_with_device(set_session_cookie=True)
    try:
        with TestingSessionLocal() as session:
            device = session.get(Device, device_id)
            device.name = "Device 1"
            device.location = "Grow Tent"
            device.user_id = user_id
            session.add(device)
            session.commit()

            upsert_device_node(
                session,
                device_id=device_id,
                hardware_device_id="master-01",
                node_role="master",
                display_name="Master",
                status="online",
            )
            session.add(
                SensorReading(
                    device_id=device_id,
                    moisture=39.2,
                    temperature=22.4,
                    humidity=54.0,
                )
            )
            session.commit()

        response = client.get(
            "/setup/status.json",
            params={"device_name": "Device 1", "location": "Grow Tent", "expect_image": "0"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["device_found"] is True
        assert payload["has_reading"] is True
        assert payload["has_image"] is False
        assert payload["expect_image"] is False
        assert payload["ready"] is True
        assert payload["redirect_url"] == f"/devices/{device_id}?setup=complete"
    finally:
        teardown_overrides()


def test_setup_status_for_master_only_device_keeps_explicit_image_expectation():
    client, TestingSessionLocal, user_id, device_id = build_client_with_device(set_session_cookie=True)
    try:
        with TestingSessionLocal() as session:
            device = session.get(Device, device_id)
            device.name = "Device 1"
            device.location = "Grow Tent"
            device.user_id = user_id
            session.add(device)
            session.commit()

            upsert_device_node(
                session,
                device_id=device_id,
                hardware_device_id="master-01",
                node_role="master",
                display_name="Master",
                status="online",
            )
            session.add(
                SensorReading(
                    device_id=device_id,
                    moisture=39.2,
                    temperature=22.4,
                    humidity=54.0,
                )
            )
            session.commit()

        response = client.get(
            "/setup/status.json",
            params={"device_name": "Device 1", "location": "Grow Tent", "expect_image": "1"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["device_found"] is True
        assert payload["has_reading"] is True
        assert payload["has_image"] is False
        assert payload["expect_image"] is True
        assert payload["ready"] is False
    finally:
        teardown_overrides()


def test_setup_finishing_page_hides_image_wait_for_master_device():
    client, TestingSessionLocal, user_id, device_id = build_client_with_device(set_session_cookie=True)
    try:
        with TestingSessionLocal() as session:
            device = session.get(Device, device_id)
            device.name = "Device 1"
            device.location = "Grow Tent"
            device.user_id = user_id
            session.add(device)
            session.commit()

            upsert_device_node(
                session,
                device_id=device_id,
                hardware_device_id="master-01",
                node_role="master",
                display_name="Master",
                status="online",
            )
            session.commit()

        response = client.get(
            "/devices/setup-finishing",
            params={"device_name": "Device 1", "location": "Grow Tent", "expect_image": "0"},
        )

        assert response.status_code == 200
        assert "registering your master node" in response.text
        assert "First photo uploaded" not in response.text
        assert "master node joins your Wi" in response.text
    finally:
        teardown_overrides()


def test_setup_status_for_master_with_camera_waits_for_first_image():
    client, TestingSessionLocal, user_id, device_id = build_client_with_device(set_session_cookie=True)
    try:
        with TestingSessionLocal() as session:
            device = session.get(Device, device_id)
            device.name = "Device 1"
            device.location = "Grow Tent"
            device.user_id = user_id
            session.add(device)
            session.commit()

            upsert_device_node(
                session,
                device_id=device_id,
                hardware_device_id="master-01",
                node_role="master",
                display_name="Master",
                status="online",
            )
            upsert_device_node(
                session,
                device_id=device_id,
                hardware_device_id="cam-01",
                node_role="camera",
                node_index=1,
                display_name="Camera 1",
                status="online",
            )
            session.add(
                SensorReading(
                    device_id=device_id,
                    moisture=39.2,
                    temperature=22.4,
                    humidity=54.0,
                )
            )
            session.commit()

        response = client.get(
            "/setup/status.json",
            params={"device_name": "Device 1", "location": "Grow Tent", "expect_image": "0"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["device_found"] is True
        assert payload["has_reading"] is True
        assert payload["has_image"] is False
        assert payload["expect_image"] is True
        assert payload["ready"] is False
    finally:
        teardown_overrides()


def test_setup_finishing_page_shows_image_wait_for_master_with_camera():
    client, TestingSessionLocal, user_id, device_id = build_client_with_device(set_session_cookie=True)
    try:
        with TestingSessionLocal() as session:
            device = session.get(Device, device_id)
            device.name = "Device 1"
            device.location = "Grow Tent"
            device.user_id = user_id
            session.add(device)
            session.commit()

            upsert_device_node(
                session,
                device_id=device_id,
                hardware_device_id="master-01",
                node_role="master",
                display_name="Master",
                status="online",
            )
            upsert_device_node(
                session,
                device_id=device_id,
                hardware_device_id="cam-01",
                node_role="camera",
                node_index=1,
                display_name="Camera 1",
                status="online",
            )
            session.commit()

        response = client.get(
            "/devices/setup-finishing",
            params={"device_name": "Device 1", "location": "Grow Tent", "expect_image": "0"},
        )

        assert response.status_code == 200
        assert "First photo uploaded" in response.text
    finally:
        teardown_overrides()


def test_setup_status_accepts_legacy_query_for_master_only_device():
    client, TestingSessionLocal, user_id, device_id = build_client_with_device(set_session_cookie=True)
    try:
        with TestingSessionLocal() as session:
            device = session.get(Device, device_id)
            device.name = "Device 1"
            device.location = "Location 1"
            device.user_id = user_id
            session.add(device)
            session.commit()

            upsert_device_node(
                session,
                device_id=device_id,
                hardware_device_id="master-01",
                node_role="master",
                display_name="Master",
                status="online",
            )
            session.add(
                SensorReading(
                    device_id=device_id,
                    moisture=39.2,
                    temperature=22.4,
                    humidity=54.0,
                )
            )
            session.commit()

        response = client.get(
            "/setup/status.json?pending_device_name=Device+1&amp;pending_location=Location+1&amp;expect_image=0"
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["expect_image"] is False
        assert payload["ready"] is True
    finally:
        teardown_overrides()


def test_delete_device_releases_single_board_provisioning_references():
    client, TestingSessionLocal, user_id, device_id = build_client_with_device(set_session_cookie=True)
    try:
        with TestingSessionLocal() as session:
            user = session.get(User, user_id)
            device = session.get(Device, device_id)
            device.name = "Kitchen Rose"
            session.add(device)
            ensure_provisioning_cleanup_tables(session)
            upsert_device_node(
                session,
                device_id=device_id,
                hardware_device_id="pi-001",
                node_role="single_board",
                display_name="Raspberry Pi",
                status="online",
            )
            session.execute(
                text(
                    """
                    INSERT INTO device_serial_numbers (
                      serial_number, hardware_model, status, claimed_by_user_id,
                      claimed_by_device_id, claimed_at, created_at, updated_at
                    )
                    VALUES (
                      'SN-PI-001', 'raspberry_pi', 'claimed', :user_id,
                      :device_id, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                    )
                    """
                ),
                {"user_id": user_id, "device_id": device_id},
            )
            session.execute(
                text(
                    """
                    INSERT INTO device_claim_tokens (
                      claim_token, serial_number, user_id, created_at, expires_at, used_at, used_by_device_id
                    )
                    VALUES (
                      'claim-pi-001', 'SN-PI-001', :user_id, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
                      CURRENT_TIMESTAMP, :device_id
                    )
                    """
                ),
                {"user_id": user_id, "device_id": device_id},
            )
            session.execute(
                text(
                    """
                    INSERT INTO device_access_tokens (device_id, token_hash, created_at)
                    VALUES (:device_id, 'hash-pi-001', CURRENT_TIMESTAMP)
                    """
                ),
                {"device_id": device_id},
            )
            session.commit()

            assert delete_device_for_user(session, user, device_id) is True

            assert session.get(Device, device_id) is None
            assert session.query(DeviceNode).filter(DeviceNode.device_id == device_id).count() == 0
            serial_row = session.execute(
                text(
                    """
                    SELECT status, claimed_by_user_id, claimed_by_device_id
                    FROM device_serial_numbers
                    WHERE serial_number = 'SN-PI-001'
                    """
                )
            ).mappings().one()
            assert serial_row["status"] == "available"
            assert serial_row["claimed_by_user_id"] is None
            assert serial_row["claimed_by_device_id"] is None
            claim_row = session.execute(
                text(
                    """
                    SELECT used_by_device_id
                    FROM device_claim_tokens
                    WHERE claim_token = 'claim-pi-001'
                    """
                )
            ).mappings().one()
            assert claim_row["used_by_device_id"] is None
            access_count = session.execute(
                text("SELECT COUNT(*) AS count FROM device_access_tokens WHERE device_id = :device_id"),
                {"device_id": device_id},
            ).mappings().one()["count"]
            assert access_count == 0
    finally:
        teardown_overrides()


def test_delete_device_releases_master_and_camera_node_mappings_together():
    client, TestingSessionLocal, user_id, device_id = build_client_with_device(set_session_cookie=True)
    try:
        with TestingSessionLocal() as session:
            user = session.get(User, user_id)
            device = session.get(Device, device_id)
            device.name = "Device 1"
            session.add(device)
            ensure_provisioning_cleanup_tables(session)
            upsert_device_node(
                session,
                device_id=device_id,
                hardware_device_id="master-01",
                node_role="master",
                display_name="Master",
                status="online",
            )
            upsert_device_node(
                session,
                device_id=device_id,
                hardware_device_id="cam-01",
                node_role="camera",
                node_index=1,
                display_name="Camera 1",
                status="online",
            )
            session.execute(
                text(
                    """
                    INSERT INTO device_serial_numbers (
                      serial_number, hardware_model, status, claimed_by_user_id,
                      claimed_by_device_id, claimed_at, created_at, updated_at
                    )
                    VALUES (
                      'SN-ESP32-001', 'esp32_master', 'claimed', :user_id,
                      :device_id, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
                    )
                    """
                ),
                {"user_id": user_id, "device_id": device_id},
            )
            session.execute(
                text(
                    """
                    INSERT INTO device_claim_tokens (
                      claim_token, serial_number, user_id, created_at, expires_at, used_at, used_by_device_id
                    )
                    VALUES (
                      'claim-esp32-001', 'SN-ESP32-001', :user_id, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP,
                      CURRENT_TIMESTAMP, :device_id
                    )
                    """
                ),
                {"user_id": user_id, "device_id": device_id},
            )
            session.execute(
                text(
                    """
                    INSERT INTO device_access_tokens (device_id, token_hash, created_at)
                    VALUES (:device_id, 'hash-esp32-001', CURRENT_TIMESTAMP)
                    """
                ),
                {"device_id": device_id},
            )
            session.commit()

            assert delete_device_for_user(session, user, device_id) is True

            assert session.get(Device, device_id) is None
            assert session.query(DeviceNode).filter(DeviceNode.device_id == device_id).count() == 0
            claim_row = session.execute(
                text(
                    """
                    SELECT used_by_device_id
                    FROM device_claim_tokens
                    WHERE claim_token = 'claim-esp32-001'
                    """
                )
            ).mappings().one()
            assert claim_row["used_by_device_id"] is None
            serial_row = session.execute(
                text(
                    """
                    SELECT status, claimed_by_device_id
                    FROM device_serial_numbers
                    WHERE serial_number = 'SN-ESP32-001'
                    """
                )
            ).mappings().one()
            assert serial_row["status"] == "available"
            assert serial_row["claimed_by_device_id"] is None
            access_count = session.execute(
                text("SELECT COUNT(*) AS count FROM device_access_tokens WHERE device_id = :device_id"),
                {"device_id": device_id},
            ).mappings().one()["count"]
            assert access_count == 0
    finally:
        teardown_overrides()
