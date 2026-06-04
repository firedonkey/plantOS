from collections.abc import Generator
from datetime import datetime, timezone
from hashlib import sha256
import sys
from types import ModuleType

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_current_user, get_optional_current_user
from app.core.settings import get_settings
from app.db.session import get_session
from app.main import app
from app.models import Device, DeviceDiagnosticEvent, DeviceNode, FirmwareRelease, User
from app.models.base import Base


def build_client_with_devices() -> tuple[TestClient, sessionmaker[Session], int, int]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    testing_session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    with testing_session_local() as session:
        user = User(email="owner@example.com", google_sub="owner-google")
        other_user = User(email="other@example.com", google_sub="other-google")
        session.add_all([user, other_user])
        session.commit()
        session.refresh(user)
        session.refresh(other_user)

        device = Device(user_id=user.id, name="Kitchen Rose", api_token="token-owner")
        other_device = Device(user_id=other_user.id, name="Other Rose", api_token="token-other")
        session.add_all([device, other_device])
        session.commit()
        session.refresh(device)
        session.refresh(other_device)
        user_id = user.id
        device_id = device.id
        other_device_id = other_device.id

    def override_session() -> Generator[Session, None, None]:
        with testing_session_local() as session:
            yield session

    def override_current_user() -> User:
        with testing_session_local() as session:
            return session.get(User, user_id)

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_optional_current_user] = override_current_user
    client = TestClient(app)
    return client, testing_session_local, device_id, other_device_id


def teardown_overrides() -> None:
    app.dependency_overrides.clear()


def add_master_node(session: Session, device_id: int, *, software_version: str = "0.1.0") -> DeviceNode:
    node = DeviceNode(
        device_id=device_id,
        hardware_device_id="master-01",
        node_role="master",
        display_name="Master",
        hardware_model="esp32-s3-devkitc-1",
        software_version=software_version,
        status="online",
    )
    session.add(node)
    session.commit()
    session.refresh(node)
    return node


def add_node(
    session: Session,
    device_id: int,
    *,
    hardware_device_id: str,
    node_role: str = "master",
    hardware_model: str = "esp32-s3-devkitc-1",
    software_version: str = "0.1.0",
) -> DeviceNode:
    node = DeviceNode(
        device_id=device_id,
        hardware_device_id=hardware_device_id,
        node_role=node_role,
        display_name=hardware_device_id,
        hardware_model=hardware_model,
        software_version=software_version,
        status="online",
    )
    session.add(node)
    session.commit()
    session.refresh(node)
    return node


def add_release(
    session: Session,
    *,
    release_id: str = "master-0.2.0",
    version: str = "0.2.0",
    version_code: int = 2000,
    hardware_model: str | None = "esp32-s3-devkitc-1",
    channel: str = "stable",
    rollout_percentage: int = 100,
    allowed_hardware_device_ids: str | None = None,
    max_current_version: str | None = None,
    rollback_release_id: str | None = None,
    rollback_version: str | None = None,
    artifact_path: str = "master-0.2.0.bin",
    artifact_size_bytes: int = 1024,
    checksum: str | None = None,
    status: str = "published",
) -> FirmwareRelease:
    release = FirmwareRelease(
        release_id=release_id,
        node_role="master",
        hardware_model=hardware_model,
        version=version,
        version_code=version_code,
        min_current_version="0.1.0",
        max_current_version=max_current_version,
        channel=channel,
        rollout_percentage=rollout_percentage,
        allowed_hardware_device_ids=allowed_hardware_device_ids,
        rollback_release_id=rollback_release_id,
        rollback_version=rollback_version,
        artifact_path=artifact_path,
        artifact_size_bytes=artifact_size_bytes,
        sha256=checksum or ("a" * 64),
        status=status,
        published_at=datetime.now(timezone.utc),
    )
    session.add(release)
    session.commit()
    session.refresh(release)
    return release


def test_ota_manifest_advertises_backend_owned_release_and_marks_node_available():
    client, testing_session_local, device_id, _ = build_client_with_devices()
    try:
        with testing_session_local() as session:
            add_master_node(session, device_id)
            add_release(session, checksum="ABCDEF" + ("1" * 58))

        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_optional_current_user, None)
        response = client.get(
            "/api/hardware/ota/manifest",
            params={
                "hardware_device_id": "master-01",
                "node_role": "master",
                "current_version": "0.1.0",
            },
            headers={"X-Device-Token": "token-owner"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["update_available"] is True
        assert payload["release_id"] == "master-0.2.0"
        assert payload["version"] == "0.2.0"
        assert payload["artifact_url"] == "/api/hardware/ota/artifacts/master-0.2.0"
        assert not payload["artifact_url"].startswith(("http://", "https://"))
        assert payload["sha256"] == "abcdef" + ("1" * 58)

        with testing_session_local() as session:
            node = session.get(DeviceNode, "master-01")
            assert node.ota_status == "available"
            assert node.ota_available_version == "0.2.0"
            assert node.ota_target_version == "0.2.0"
            assert node.ota_release_id == "master-0.2.0"
            assert node.ota_progress == 0
            event = session.query(DeviceDiagnosticEvent).order_by(DeviceDiagnosticEvent.id.desc()).first()
            assert event.event_type == "OTA_AVAILABLE"
            assert event.metadata_json["data"]["target_version"] == "0.2.0"
    finally:
        teardown_overrides()


def test_ota_manifest_rejects_foreign_node_and_role_mismatch():
    client, testing_session_local, device_id, other_device_id = build_client_with_devices()
    try:
        with testing_session_local() as session:
            add_master_node(session, other_device_id)
            session.add(
                DeviceNode(
                    device_id=device_id,
                    hardware_device_id="cam-01",
                    node_role="camera",
                    display_name="Camera 1",
                    hardware_model="xiao_esp32s3_camera",
                    status="online",
                )
            )
            session.commit()

        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_optional_current_user, None)
        foreign_response = client.get(
            "/api/hardware/ota/manifest",
            params={"hardware_device_id": "master-01", "node_role": "master"},
            headers={"X-Device-Token": "token-owner"},
        )
        role_response = client.get(
            "/api/hardware/ota/manifest",
            params={"hardware_device_id": "cam-01", "node_role": "master"},
            headers={"X-Device-Token": "token-owner"},
        )

        assert foreign_response.status_code == 404
        assert role_response.status_code == 409
    finally:
        teardown_overrides()


def test_ota_manifest_ignores_incompatible_nonadvancing_or_invalid_releases():
    client, testing_session_local, device_id, _ = build_client_with_devices()
    try:
        with testing_session_local() as session:
            add_master_node(session, device_id, software_version="0.2.0")
            add_release(session, release_id="same-version", version="0.2.0", version_code=2000)
            add_release(
                session,
                release_id="wrong-model",
                version="0.3.0",
                version_code=3000,
                hardware_model="other-board",
            )
            add_release(
                session,
                release_id="bad-checksum",
                version="0.4.0",
                version_code=4000,
                checksum="not-a-sha",
            )

        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_optional_current_user, None)
        response = client.get(
            "/api/hardware/ota/manifest",
            params={
                "hardware_device_id": "master-01",
                "node_role": "master",
                "current_version": "0.2.0",
            },
            headers={"X-Device-Token": "token-owner"},
        )

        assert response.status_code == 200
        assert response.json()["update_available"] is False

        with testing_session_local() as session:
            node = session.get(DeviceNode, "master-01")
            assert node.ota_status == "idle"
            assert node.ota_available_version is None
            assert node.ota_release_id is None
    finally:
        teardown_overrides()


def test_ota_manifest_respects_channel_rollout_and_allowlist():
    client, testing_session_local, device_id, _ = build_client_with_devices()
    try:
        with testing_session_local() as session:
            add_master_node(session, device_id)
            add_node(session, device_id, hardware_device_id="master-02")
            add_release(session, release_id="stable-open", version="0.2.0", version_code=2000)
            add_release(session, release_id="beta-new", version="0.4.0", version_code=4000, channel="beta")
            add_release(
                session,
                release_id="stable-blocked",
                version="0.5.0",
                version_code=5000,
                rollout_percentage=0,
            )
            add_release(
                session,
                release_id="stable-allowlisted",
                version="0.6.0",
                version_code=6000,
                rollout_percentage=0,
                allowed_hardware_device_ids='["master-01"]',
            )

        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_optional_current_user, None)
        allowlisted = client.get(
            "/api/hardware/ota/manifest",
            params={"hardware_device_id": "master-01", "node_role": "master", "current_version": "0.1.0"},
            headers={"X-Device-Token": "token-owner"},
        )
        non_allowlisted = client.get(
            "/api/hardware/ota/manifest",
            params={"hardware_device_id": "master-02", "node_role": "master", "current_version": "0.1.0"},
            headers={"X-Device-Token": "token-owner"},
        )
        beta = client.get(
            "/api/hardware/ota/manifest",
            params={
                "hardware_device_id": "master-02",
                "node_role": "master",
                "current_version": "0.1.0",
                "firmware_channel": "beta",
            },
            headers={"X-Device-Token": "token-owner"},
        )
        invalid_channel = client.get(
            "/api/hardware/ota/manifest",
            params={"hardware_device_id": "master-02", "node_role": "master", "firmware_channel": "gamma"},
            headers={"X-Device-Token": "token-owner"},
        )

        assert allowlisted.status_code == 200
        assert allowlisted.json()["release_id"] == "stable-allowlisted"
        assert allowlisted.json()["firmware_channel"] == "stable"
        assert allowlisted.json()["rollout_percentage"] == 0
        assert non_allowlisted.status_code == 200
        assert non_allowlisted.json()["release_id"] == "stable-open"
        assert beta.status_code == 200
        assert beta.json()["release_id"] == "beta-new"
        assert beta.json()["firmware_channel"] == "beta"
        assert invalid_channel.status_code == 422
        assert invalid_channel.json()["error"]["code"] == "unsupported_ota_channel"
    finally:
        teardown_overrides()


def test_ota_manifest_respects_max_current_version_and_returns_rollback_metadata():
    client, testing_session_local, device_id, _ = build_client_with_devices()
    try:
        with testing_session_local() as session:
            add_master_node(session, device_id, software_version="0.2.0")
            add_release(
                session,
                release_id="too-old-current-version",
                version="0.3.0",
                version_code=3000,
                max_current_version="0.1.5",
            )
            add_release(
                session,
                release_id="rollback-ready",
                version="0.2.1",
                version_code=2001,
                max_current_version="0.2.9",
                rollback_release_id="master-0.2.0-stable",
                rollback_version="0.2.0",
            )

        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_optional_current_user, None)
        response = client.get(
            "/api/hardware/ota/manifest",
            params={"hardware_device_id": "master-01", "node_role": "master", "current_version": "0.2.0"},
            headers={"X-Device-Token": "token-owner"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["release_id"] == "rollback-ready"
        assert payload["max_current_version"] == "0.2.9"
        assert payload["rollback_release_id"] == "master-0.2.0-stable"
        assert payload["rollback_version"] == "0.2.0"
    finally:
        teardown_overrides()


def test_ota_status_transitions_persist_failure_and_success_state():
    client, testing_session_local, device_id, _ = build_client_with_devices()
    try:
        with testing_session_local() as session:
            add_master_node(session, device_id)
            add_release(session)

        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_optional_current_user, None)
        downloading_response = client.post(
            "/api/hardware/ota/status",
            json={
                "hardware_device_id": "master-01",
                "status": "downloading",
                "release_id": "master-0.2.0",
                "target_version": "0.2.0",
                "progress": 42,
            },
            headers={"X-Device-Token": "token-owner"},
        )
        failed_response = client.post(
            "/api/hardware/ota/status",
            json={
                "hardware_device_id": "master-01",
                "status": "failed",
                "release_id": "master-0.2.0",
                "target_version": "0.2.0",
                "progress": 42,
                "error": "checksum mismatch",
            },
            headers={"X-Device-Token": "token-owner"},
        )
        success_response = client.post(
            "/api/hardware/ota/status",
            json={
                "hardware_device_id": "master-01",
                "status": "success",
                "release_id": "master-0.2.0",
                "installed_version": "0.2.0",
            },
            headers={"X-Device-Token": "token-owner"},
        )

        assert downloading_response.status_code == 200
        assert downloading_response.json()["progress"] == 42
        assert failed_response.status_code == 200
        assert failed_response.json()["error"] == "checksum mismatch"
        assert success_response.status_code == 200
        assert success_response.json()["installed_version"] == "0.2.0"
        assert success_response.json()["progress"] == 100

        with testing_session_local() as session:
            node = session.get(DeviceNode, "master-01")
            assert node.software_version == "0.2.0"
            assert node.ota_status == "success"
            assert node.ota_error is None
            assert node.ota_available_version is None
            assert node.ota_last_success_at is not None
    finally:
        teardown_overrides()


def test_ota_artifact_requires_device_token_and_serves_only_local_firmware_files(tmp_path, monkeypatch):
    client, testing_session_local, device_id, _ = build_client_with_devices()
    firmware_bytes = b"firmware-image"
    firmware_dir = tmp_path / "firmware"
    firmware_dir.mkdir()
    (firmware_dir / "master.bin").write_bytes(firmware_bytes)
    monkeypatch.setenv("PLANTLAB_FIRMWARE_LOCAL_DIR", str(firmware_dir))
    monkeypatch.setenv("PLANTLAB_FIRMWARE_STORAGE_BACKEND", "local")
    get_settings.cache_clear()
    try:
        with testing_session_local() as session:
            add_master_node(session, device_id)
            add_release(
                session,
                release_id="local-release",
                artifact_path="master.bin",
                artifact_size_bytes=len(firmware_bytes),
                checksum=sha256(firmware_bytes).hexdigest(),
            )
            add_release(
                session,
                release_id="external-release",
                artifact_path="https://example.com/master.bin",
                checksum="b" * 64,
            )

        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_optional_current_user, None)
        unauthenticated = client.get("/api/hardware/ota/artifacts/local-release")
        authorized = client.get(
            "/api/hardware/ota/artifacts/local-release",
            headers={"X-Device-Token": "token-owner"},
        )
        external = client.get(
            "/api/hardware/ota/artifacts/external-release",
            headers={"X-Device-Token": "token-owner"},
        )

        assert unauthenticated.status_code == 401
        assert authorized.status_code == 200
        assert authorized.content == firmware_bytes
        assert external.status_code == 404
    finally:
        teardown_overrides()
        get_settings.cache_clear()


def test_gcs_ota_artifact_response_includes_content_length(monkeypatch):
    client, testing_session_local, device_id, _ = build_client_with_devices()
    firmware_bytes = b"camera-firmware-image"

    class FakeBlob:
        def download_as_bytes(self) -> bytes:
            return firmware_bytes

    class FakeBucket:
        def blob(self, object_name: str) -> FakeBlob:
            assert object_name == "firmware/camera.bin"
            return FakeBlob()

    class FakeStorageClient:
        def bucket(self, bucket_name: str) -> FakeBucket:
            assert bucket_name == "plantlab-firmware"
            return FakeBucket()

    storage_module = ModuleType("google.cloud.storage")
    storage_module.Client = FakeStorageClient
    cloud_module = ModuleType("google.cloud")
    cloud_module.storage = storage_module
    google_module = ModuleType("google")
    google_module.cloud = cloud_module

    monkeypatch.setitem(sys.modules, "google", google_module)
    monkeypatch.setitem(sys.modules, "google.cloud", cloud_module)
    monkeypatch.setitem(sys.modules, "google.cloud.storage", storage_module)
    monkeypatch.setenv("PLANTLAB_FIRMWARE_STORAGE_BACKEND", "gcs")
    monkeypatch.setenv("PLANTLAB_FIRMWARE_BUCKET_NAME", "plantlab-firmware")
    get_settings.cache_clear()
    try:
        with testing_session_local() as session:
            add_master_node(session, device_id)
            add_release(
                session,
                release_id="camera-gcs-release",
                artifact_path="gs://plantlab-firmware/firmware/camera.bin",
                artifact_size_bytes=len(firmware_bytes),
                checksum=sha256(firmware_bytes).hexdigest(),
            )

        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_optional_current_user, None)
        response = client.get(
            "/api/hardware/ota/artifacts/camera-gcs-release",
            headers={"X-Device-Token": "token-owner"},
        )

        assert response.status_code == 200
        assert response.content == firmware_bytes
        assert response.headers["content-length"] == str(len(firmware_bytes))
    finally:
        teardown_overrides()
        get_settings.cache_clear()


def test_hardware_heartbeat_and_device_summary_include_firmware_ota_fields():
    client, testing_session_local, device_id, _ = build_client_with_devices()
    try:
        with testing_session_local() as session:
            node = add_master_node(session, device_id)
            node.ota_status = "failed"
            node.ota_target_version = "0.2.0"
            node.ota_error = "download failed"
            session.add(node)
            session.commit()

        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_optional_current_user, None)
        heartbeat_response = client.post(
            "/api/hardware/heartbeat",
            json={
                "hardware_device_id": "master-01",
                "node_role": "master",
                "status": "online",
                "software_version": "0.1.1",
            },
            headers={"X-Device-Token": "token-owner"},
        )
        app.dependency_overrides[get_current_user] = lambda: User(id=1, email="owner@example.com", google_sub="owner-google")
        summary_response = client.get(f"/api/devices/{device_id}/summary")

        assert heartbeat_response.status_code == 200
        assert heartbeat_response.json()["software_version"] == "0.1.1"
        assert summary_response.status_code == 200
        primary = summary_response.json()["hardware_health"]["primary"]
        assert primary["software_version"] == "0.1.1"
        assert primary["ota_status"] == "failed"
        assert primary["ota_target_version"] == "0.2.0"
        assert primary["ota_error"] == "download failed"

        with testing_session_local() as session:
            node = session.get(DeviceNode, "master-01")
            assert node.software_version == "0.1.1"
    finally:
        teardown_overrides()
