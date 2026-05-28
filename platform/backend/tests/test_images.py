from collections.abc import Generator
from datetime import datetime, timedelta, timezone
from io import BytesIO
import json
import sys
from types import ModuleType, SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_current_user, get_optional_current_user
from app.core.settings import Settings, get_settings
from app.db.session import get_session
from app.main import app
from app.models import Device, DeviceDiagnosticEvent, Image, User
from app.models.base import Base
from app.services.device_nodes import upsert_device_node
from app.services import storage as storage_service
from app.services.storage import GcsImageStorage, image_client_url, image_src


def build_client_with_device(upload_dir: str) -> tuple[TestClient, int, int]:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    with TestingSessionLocal() as session:
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
        with TestingSessionLocal() as session:
            yield session

    def override_current_user() -> User:
        with TestingSessionLocal() as session:
            return session.get(User, user_id)

    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_optional_current_user] = override_current_user
    get_settings.cache_clear()
    return TestClient(app), device_id, other_device_id


def teardown_overrides() -> None:
    app.dependency_overrides.clear()
    get_settings.cache_clear()


def test_image_upload_requires_auth():
    client = TestClient(app)
    response = client.post(
        "/api/image",
        data={"device_id": "1"},
        files={"file": ("plant.jpg", b"fake-jpeg", "image/jpeg")},
    )

    assert response.status_code == 401


def test_upload_image_for_owned_device(tmp_path, monkeypatch):
    monkeypatch.setenv("PLANTLAB_UPLOAD_DIR", str(tmp_path))
    client, device_id, _ = build_client_with_device(str(tmp_path))
    try:
        response = client.post(
            "/api/image",
            data={"device_id": str(device_id)},
            files={"file": ("plant.jpg", b"fake-jpeg", "image/jpeg")},
        )

        assert response.status_code == 201
        payload = response.json()
        assert payload["device_id"] == device_id
        saved_path = tmp_path / f"device-{device_id}"
        assert saved_path.exists()
        assert len(list(saved_path.glob("*.jpg"))) == 1
    finally:
        teardown_overrides()


def test_upload_image_rejects_other_users_device(tmp_path, monkeypatch):
    monkeypatch.setenv("PLANTLAB_UPLOAD_DIR", str(tmp_path))
    client, _, other_device_id = build_client_with_device(str(tmp_path))
    try:
        response = client.post(
            "/api/image",
            data={"device_id": str(other_device_id)},
            files={"file": ("plant.jpg", b"fake-jpeg", "image/jpeg")},
        )

        assert response.status_code == 404
    finally:
        teardown_overrides()


def test_upload_image_rejects_non_image_file(tmp_path, monkeypatch):
    monkeypatch.setenv("PLANTLAB_UPLOAD_DIR", str(tmp_path))
    client, device_id, _ = build_client_with_device(str(tmp_path))
    try:
        response = client.post(
            "/api/image",
            data={"device_id": str(device_id)},
            files={"file": ("notes.txt", b"not-an-image", "text/plain")},
        )

        assert response.status_code == 400
    finally:
        teardown_overrides()


def test_upload_image_accepts_device_token(tmp_path, monkeypatch):
    monkeypatch.setenv("PLANTLAB_UPLOAD_DIR", str(tmp_path))
    client, device_id, _ = build_client_with_device(str(tmp_path))
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_optional_current_user, None)
    try:
        response = client.post(
            "/api/image",
            data={"device_id": str(device_id)},
            files={"file": ("plant.jpg", b"fake-jpeg", "image/jpeg")},
            headers={"X-Device-Token": "token-owner"},
        )

        assert response.status_code == 201
        assert response.json()["device_id"] == device_id
    finally:
        teardown_overrides()


def test_upload_image_stores_attached_camera_source(tmp_path, monkeypatch):
    monkeypatch.setenv("PLANTLAB_UPLOAD_DIR", str(tmp_path))
    client, device_id, _ = build_client_with_device(str(tmp_path))
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_optional_current_user, None)
    try:
        with next(app.dependency_overrides[get_session]()) as session:
            upsert_device_node(
                session,
                device_id=device_id,
                hardware_device_id="cam-01",
                node_role="camera",
                node_index=1,
                display_name="Camera 1",
                status="online",
            )

        response = client.post(
            "/api/image",
            data={"device_id": str(device_id), "source_hardware_device_id": "cam-01"},
            files={"file": ("plant.jpg", b"fake-jpeg", "image/jpeg")},
            headers={"X-Device-Token": "token-owner"},
        )

        assert response.status_code == 201
        payload = response.json()
        assert payload["device_id"] == device_id
        assert payload["source_hardware_device_id"] == "cam-01"
    finally:
        teardown_overrides()


def test_upload_image_accepts_contract_metadata_and_emits_event(tmp_path, monkeypatch):
    monkeypatch.setenv("PLANTLAB_UPLOAD_DIR", str(tmp_path))
    client, device_id, _ = build_client_with_device(str(tmp_path))
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_optional_current_user, None)
    try:
        with next(app.dependency_overrides[get_session]()) as session:
            upsert_device_node(
                session,
                device_id=device_id,
                hardware_device_id="cam-01",
                node_role="camera",
                node_index=1,
                display_name="Camera 1",
                status="online",
            )

        captured_at = "2026-05-27T12:10:00Z"
        metadata = _image_upload_envelope(
            device_id=device_id,
            hardware_device_id="cam-01",
            status="uploaded",
            captured_at=captured_at,
            upload_reason="manual",
            width=360,
            height=240,
            content_type="image/png",
            upload_ms=1380,
        )
        response = client.post(
            "/api/image",
            data={"device_id": str(device_id), "metadata": json.dumps(metadata)},
            files={"file": ("plant.png", b"fake-png", "image/png")},
            headers={"X-Device-Token": "token-owner"},
        )

        assert response.status_code == 201
        payload = response.json()
        assert payload["device_id"] == device_id
        assert payload["source_hardware_device_id"] == "cam-01"
        with next(app.dependency_overrides[get_session]()) as session:
            event_types = [
                event.event_type
                for event in session.query(DeviceDiagnosticEvent).order_by(DeviceDiagnosticEvent.id).all()
            ]
            assert event_types == ["IMAGE_UPLOAD_STARTED", "IMAGE_CAPTURED", "IMAGE_UPLOADED"]
            event = session.query(DeviceDiagnosticEvent).filter_by(event_type="IMAGE_UPLOADED").one()
            data = event.metadata_json["data"]
            assert event.hardware_device_id == "cam-01"
            assert data["image_id"] == payload["id"]
            assert data["captured_at"].startswith("2026-05-27T12:10:00")
            assert data["upload_reason"] == "manual"
            assert data["width"] == 360
            assert data["height"] == 240
            assert data["content_type"] == "image/png"
            assert data["upload_ms"] == 1380
    finally:
        teardown_overrides()


def test_upload_image_rejects_invalid_contract_metadata(tmp_path, monkeypatch):
    monkeypatch.setenv("PLANTLAB_UPLOAD_DIR", str(tmp_path))
    client, device_id, _ = build_client_with_device(str(tmp_path))
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_optional_current_user, None)
    try:
        with next(app.dependency_overrides[get_session]()) as session:
            upsert_device_node(
                session,
                device_id=device_id,
                hardware_device_id="cam-01",
                node_role="camera",
                node_index=1,
                display_name="Camera 1",
                status="online",
            )

        metadata = _image_upload_envelope(
            device_id=device_id,
            hardware_device_id="cam-01",
            status="uploaded",
            content_type="image/jpeg",
        )
        response = client.post(
            "/api/image",
            data={"device_id": str(device_id), "metadata": json.dumps(metadata)},
            files={"file": ("plant.png", b"fake-png", "image/png")},
            headers={"X-Device-Token": "token-owner"},
        )

        assert response.status_code == 422
        assert response.json()["error"]["code"] == "image_content_type_mismatch"
    finally:
        teardown_overrides()


def test_image_upload_failed_report_emits_canonical_event(tmp_path, monkeypatch):
    monkeypatch.setenv("PLANTLAB_UPLOAD_DIR", str(tmp_path))
    client, device_id, _ = build_client_with_device(str(tmp_path))
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_optional_current_user, None)
    try:
        with next(app.dependency_overrides[get_session]()) as session:
            upsert_device_node(
                session,
                device_id=device_id,
                hardware_device_id="cam-01",
                node_role="camera",
                node_index=1,
                display_name="Camera 1",
                status="online",
            )

        report = _image_upload_envelope(
            device_id=device_id,
            hardware_device_id="cam-01",
            status="failed",
            upload_reason="manual",
            content_type="image/png",
            failure_reason="camera_timeout",
        )
        response = client.post(
            "/api/hardware/image-upload/report",
            json=report,
            headers={"X-Device-Token": "token-owner"},
        )
        duplicate_response = client.post(
            "/api/hardware/image-upload/report",
            json=report,
            headers={"X-Device-Token": "token-owner"},
        )

        assert response.status_code == 200
        assert response.json() == {"status": "accepted", "event_type": "IMAGE_UPLOAD_FAILED"}
        assert duplicate_response.status_code == 200
        with next(app.dependency_overrides[get_session]()) as session:
            events = session.query(DeviceDiagnosticEvent).filter_by(event_type="IMAGE_UPLOAD_FAILED").all()
            assert len(events) == 1
            event = events[0]
            data = event.metadata_json["data"]
            assert event.severity == "warning"
            assert data["failure_reason"] == "camera_timeout"
            assert data["source_hardware_device_id"] == "cam-01"
    finally:
        teardown_overrides()


def test_capture_command_emits_image_capture_started_event(tmp_path, monkeypatch):
    monkeypatch.setenv("PLANTLAB_UPLOAD_DIR", str(tmp_path))
    client, device_id, _ = build_client_with_device(str(tmp_path))
    try:
        with next(app.dependency_overrides[get_session]()) as session:
            upsert_device_node(
                session,
                device_id=device_id,
                hardware_device_id="cam-01",
                node_role="camera",
                node_index=1,
                display_name="Camera 1",
                status="online",
            )

        response = client.post(f"/api/devices/{device_id}/commands/capture")

        assert response.status_code == 201
        command_id = response.json()["command_id"]
        with next(app.dependency_overrides[get_session]()) as session:
            event = session.query(DeviceDiagnosticEvent).filter_by(event_type="IMAGE_CAPTURE_STARTED").one()
            assert event.hardware_device_id == "cam-01"
            assert event.metadata_json["correlation_id"] == f"cmd_{command_id}"
            assert event.metadata_json["data"]["upload_reason"] == "manual"
    finally:
        teardown_overrides()


def test_upload_image_rejects_unattached_camera_source(tmp_path, monkeypatch):
    monkeypatch.setenv("PLANTLAB_UPLOAD_DIR", str(tmp_path))
    client, device_id, _ = build_client_with_device(str(tmp_path))
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_optional_current_user, None)
    try:
        response = client.post(
            "/api/image",
            data={"device_id": str(device_id), "source_hardware_device_id": "cam-99"},
            files={"file": ("plant.jpg", b"fake-jpeg", "image/jpeg")},
            headers={"X-Device-Token": "token-owner"},
        )

        assert response.status_code == 403
        assert response.json()["error"]["message"] == "Image source node is not attached to this device."
    finally:
        teardown_overrides()


def test_image_content_serves_owned_local_image(tmp_path, monkeypatch):
    monkeypatch.setenv("PLANTLAB_STORAGE_BACKEND", "local")
    monkeypatch.setenv("PLANTLAB_UPLOAD_DIR", str(tmp_path))
    client, device_id, _ = build_client_with_device(str(tmp_path))
    try:
        upload = client.post(
            "/api/image",
            data={"device_id": str(device_id)},
            files={"file": ("plant.jpg", b"fake-jpeg", "image/jpeg")},
        )
        image_id = upload.json()["id"]

        response = client.get(f"/api/images/{image_id}/content")

        assert response.status_code == 200
        assert response.content == b"fake-jpeg"
        assert response.headers["content-type"].startswith("image/jpeg")
    finally:
        teardown_overrides()


def test_image_content_rejects_other_users_image(tmp_path, monkeypatch):
    monkeypatch.setenv("PLANTLAB_STORAGE_BACKEND", "local")
    monkeypatch.setenv("PLANTLAB_UPLOAD_DIR", str(tmp_path))
    client, _, other_device_id = build_client_with_device(str(tmp_path))
    try:
        image_path = tmp_path / "other.jpg"
        image_path.write_bytes(b"other-jpeg")
        with next(app.dependency_overrides[get_session]()) as session:
            image = Image(device_id=other_device_id, path=str(image_path))
            session.add(image)
            session.commit()
            session.refresh(image)
            image_id = image.id

        response = client.get(f"/api/images/{image_id}/content")

        assert response.status_code == 404
    finally:
        teardown_overrides()


def test_device_timelapse_returns_sampled_owned_frames(tmp_path, monkeypatch):
    monkeypatch.setenv("PLANTLAB_STORAGE_BACKEND", "local")
    monkeypatch.setenv("PLANTLAB_UPLOAD_DIR", str(tmp_path))
    client, device_id, _ = build_client_with_device(str(tmp_path))
    try:
        now = datetime.now(timezone.utc)
        timestamps = [
            now - timedelta(hours=3) + timedelta(minutes=10),
            now - timedelta(hours=3) + timedelta(minutes=20),
            now - timedelta(hours=2) + timedelta(minutes=10),
            now - timedelta(hours=2) + timedelta(minutes=20),
            now - timedelta(hours=1) + timedelta(minutes=10),
            now - timedelta(hours=1) + timedelta(minutes=20),
        ]
        with next(app.dependency_overrides[get_session]()) as session:
            session.add_all(
                [
                    Image(
                        device_id=device_id,
                        path=f"data/uploads/device-{device_id}/timelapse-{index}.jpg",
                        timestamp=timestamp,
                        source_hardware_device_id="cam-01",
                    )
                    for index, timestamp in enumerate(timestamps, start=1)
                ]
            )
            session.commit()

        response = client.get(f"/api/devices/{device_id}/timelapse?days=1&interval_minutes=60&max_frames=10")

        assert response.status_code == 200
        payload = response.json()
        assert payload["device_id"] == device_id
        assert payload["interval_minutes"] == 60
        assert payload["total_image_count"] == 6
        assert payload["frame_count"] == 3
        assert [frame["timestamp"] for frame in payload["frames"]] == sorted(
            frame["timestamp"] for frame in payload["frames"]
        )
        assert all(frame["content_url"].endswith("/content") for frame in payload["frames"])
        assert all(frame["source_hardware_device_id"] == "cam-01" for frame in payload["frames"])
    finally:
        teardown_overrides()


def test_device_timelapse_rejects_other_users_device(tmp_path, monkeypatch):
    monkeypatch.setenv("PLANTLAB_STORAGE_BACKEND", "local")
    monkeypatch.setenv("PLANTLAB_UPLOAD_DIR", str(tmp_path))
    client, _, other_device_id = build_client_with_device(str(tmp_path))
    try:
        response = client.get(f"/api/devices/{other_device_id}/timelapse")

        assert response.status_code == 404
    finally:
        teardown_overrides()


def test_image_src_supports_local_paths_and_public_urls():
    assert image_src("data/uploads/device-1/plant.jpg") == "/data/uploads/device-1/plant.jpg"
    assert image_src("https://storage.googleapis.com/bucket/plant.jpg") == "https://storage.googleapis.com/bucket/plant.jpg"


def test_gcs_upload_stores_canonical_gs_path_and_content_type(monkeypatch):
    uploaded = {}

    class FakeBlob:
        def __init__(self, object_name: str):
            self.object_name = object_name

        def upload_from_file(self, file_obj, content_type=None):
            uploaded["object_name"] = self.object_name
            uploaded["data"] = file_obj.read()
            uploaded["content_type"] = content_type

    class FakeBucket:
        def __init__(self, name: str):
            self.name = name

        def blob(self, object_name: str):
            uploaded["bucket"] = self.name
            return FakeBlob(object_name)

    class FakeStorageClient:
        def bucket(self, name: str):
            return FakeBucket(name)

    storage_module = ModuleType("google.cloud.storage")
    storage_module.Client = FakeStorageClient
    cloud_module = ModuleType("google.cloud")
    cloud_module.storage = storage_module
    google_module = ModuleType("google")
    google_module.cloud = cloud_module
    monkeypatch.setitem(sys.modules, "google", google_module)
    monkeypatch.setitem(sys.modules, "google.cloud", cloud_module)
    monkeypatch.setitem(sys.modules, "google.cloud.storage", storage_module)

    upload_file = SimpleNamespace(file=BytesIO(b"fake-jpeg"), content_type="image/jpeg")

    stored = GcsImageStorage("plantlab-images").save_image(upload_file, device_id=7, suffix=".jpg")

    assert stored.path.startswith("gs://plantlab-images/device-7/")
    assert stored.path.endswith(".jpg")
    assert uploaded["bucket"] == "plantlab-images"
    assert uploaded["object_name"].startswith("device-7/")
    assert uploaded["data"] == b"fake-jpeg"
    assert uploaded["content_type"] == "image/jpeg"


def test_image_client_url_signs_gs_paths_with_configured_ttl(monkeypatch):
    calls = []

    def fake_signed_url(bucket_name: str, object_name: str, settings: Settings) -> str:
        calls.append((bucket_name, object_name, settings.image_signed_url_ttl_seconds))
        return f"https://signed.example/{bucket_name}/{object_name}"

    monkeypatch.setattr(storage_service, "_signed_gcs_image_url", fake_signed_url)
    request = SimpleNamespace(url_for=lambda name, image_id: f"https://api.example/api/images/{image_id}/content")
    settings = Settings(
        storage_backend="gcs",
        gcs_bucket_name="plantlab-images",
        image_signed_url_ttl_seconds=600,
    )
    image = SimpleNamespace(id=42, path="gs://plantlab-images/device-1/rose%20one.jpg")

    url = image_client_url(image, request, settings)

    assert url == "https://signed.example/plantlab-images/device-1/rose one.jpg"
    assert calls == [("plantlab-images", "device-1/rose one.jpg", 600)]


def test_image_client_url_signs_existing_public_gcs_urls(monkeypatch):
    calls = []

    def fake_signed_url(bucket_name: str, object_name: str, settings: Settings) -> str:
        calls.append((bucket_name, object_name))
        return "https://signed.example/legacy"

    monkeypatch.setattr(storage_service, "_signed_gcs_image_url", fake_signed_url)
    request = SimpleNamespace(url_for=lambda name, image_id: f"https://api.example/api/images/{image_id}/content")
    settings = Settings(storage_backend="gcs", gcs_bucket_name="plantlab-images")
    image = SimpleNamespace(
        id=43,
        path="https://storage.googleapis.com/legacy-bucket/device-1/old%20rose.jpg",
    )

    url = image_client_url(image, request, settings)

    assert url == "https://signed.example/legacy"
    assert calls == [("legacy-bucket", "device-1/old rose.jpg")]


def test_image_client_url_falls_back_to_proxy_when_signing_fails(monkeypatch):
    def fake_signed_url(bucket_name: str, object_name: str, settings: Settings) -> str:
        raise RuntimeError("signing unavailable")

    monkeypatch.setattr(storage_service, "_signed_gcs_image_url", fake_signed_url)
    request = SimpleNamespace(url_for=lambda name, image_id: f"https://api.example/api/images/{image_id}/content")
    settings = Settings(storage_backend="gcs", gcs_bucket_name="plantlab-images")
    image = SimpleNamespace(id=45, path="gs://plantlab-images/device-1/rose.jpg")

    url = image_client_url(image, request, settings)

    assert url == "https://api.example/api/images/45/content"


def test_image_client_url_uses_backend_proxy_for_local_storage():
    request = SimpleNamespace(url_for=lambda name, image_id: f"https://api.example/api/images/{image_id}/content")
    settings = Settings(storage_backend="local")
    image = SimpleNamespace(id=44, path="data/uploads/device-1/plant.jpg")

    url = image_client_url(image, request, settings)

    assert url == "https://api.example/api/images/44/content"


def _image_upload_envelope(
    *,
    device_id: int,
    hardware_device_id: str,
    status: str,
    captured_at: str | None = None,
    upload_reason: str | None = None,
    width: int | None = None,
    height: int | None = None,
    content_type: str | None = None,
    upload_ms: int | None = None,
    failure_reason: str | None = None,
) -> dict:
    payload = {
        "status": status,
        "source_hardware_device_id": hardware_device_id,
        "source_node_role": "camera",
        "captured_at": captured_at,
        "upload_reason": upload_reason,
        "width": width,
        "height": height,
        "content_type": content_type,
        "upload_ms": upload_ms,
        "failure_reason": failure_reason,
    }
    return {
        "schema_version": "1.0",
        "message_id": f"img_{hardware_device_id}_{status}",
        "device_id": device_id,
        "hardware_device_id": hardware_device_id,
        "node_role": "camera",
        "message_type": "IMAGE_UPLOAD",
        "sent_at": "2026-05-27T12:00:00Z",
        "payload": {key: value for key, value in payload.items() if value is not None},
    }
