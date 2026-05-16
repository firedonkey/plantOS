from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from re import fullmatch
from urllib.parse import unquote, urlparse

from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.settings import Settings
from app.models import DeviceNode, FirmwareRelease
from app.schemas.firmware import FirmwareManifestRead, FirmwareOtaStatusCreate, FirmwareOtaStatusRead


OTA_STATUSES = {"idle", "available", "downloading", "installing", "success", "failed"}
PUBLISHED_STATUS = "published"
SHA256_PATTERN = r"^[0-9a-fA-F]{64}$"


def build_manifest_for_node(
    session: Session,
    *,
    node: DeviceNode,
    node_role: str,
    current_version: str | None,
) -> FirmwareManifestRead:
    if node.node_role != node_role:
        return FirmwareManifestRead(update_available=False)

    release = _latest_compatible_release(
        session,
        node_role=node_role,
        hardware_model=node.hardware_model,
        current_version=current_version or node.software_version,
    )
    if release is None:
        _mark_no_update(session, node)
        return FirmwareManifestRead(update_available=False)

    now = datetime.now(timezone.utc)
    node.ota_status = "available"
    node.ota_available_version = release.version
    node.ota_target_version = release.version
    node.ota_release_id = release.release_id
    node.ota_progress = 0
    node.ota_error = None
    node.ota_updated_at = now
    session.add(node)
    session.commit()

    return FirmwareManifestRead(
        update_available=True,
        schema_version=1,
        release_id=release.release_id,
        node_role=release.node_role,
        hardware_model=release.hardware_model,
        version=release.version,
        version_code=release.version_code,
        artifact_url=f"/api/hardware/ota/artifacts/{release.release_id}",
        artifact_size_bytes=release.artifact_size_bytes,
        sha256=release.sha256.lower(),
        signature=release.signature,
    )


def update_ota_status(
    session: Session,
    *,
    node: DeviceNode,
    payload: FirmwareOtaStatusCreate,
) -> FirmwareOtaStatusRead:
    now = datetime.now(timezone.utc)
    release = None
    if payload.release_id:
        release = session.get(FirmwareRelease, payload.release_id)

    node.ota_status = payload.status
    node.ota_release_id = payload.release_id or node.ota_release_id
    node.ota_target_version = payload.target_version or (release.version if release else node.ota_target_version)
    node.ota_progress = payload.progress
    node.ota_error = payload.error if payload.status == "failed" else None
    node.ota_updated_at = now

    if payload.status == "success":
        node.software_version = payload.installed_version or node.ota_target_version or node.software_version
        node.ota_available_version = None
        node.ota_progress = 100
        node.ota_last_success_at = now
    elif payload.status == "idle":
        node.ota_available_version = None
        node.ota_target_version = None
        node.ota_release_id = None
        node.ota_progress = None
    elif payload.status == "available":
        node.ota_available_version = payload.target_version or (release.version if release else node.ota_available_version)

    session.add(node)
    session.commit()
    session.refresh(node)
    return FirmwareOtaStatusRead(
        hardware_device_id=node.hardware_device_id,
        status=node.ota_status,  # type: ignore[arg-type]
        release_id=node.ota_release_id,
        target_version=node.ota_target_version,
        available_version=node.ota_available_version,
        installed_version=node.software_version,
        progress=node.ota_progress,
        error=node.ota_error,
        updated_at=node.ota_updated_at,
    )


def firmware_artifact_response(release: FirmwareRelease, settings: Settings):
    path = release.artifact_path.strip()
    if path.startswith(("http://", "https://")):
        raise ValueError("Firmware artifact path must be backend-owned storage, not an external URL.")
    if path.startswith("gs://") or settings.firmware_storage_backend == "gcs":
        bucket_name, object_name = _gcs_artifact_location(path, settings)
        return _gcs_artifact_response(bucket_name, object_name)

    artifact_path = _local_artifact_path(path, settings)
    if not artifact_path.is_file():
        raise FileNotFoundError("Firmware artifact not found.")
    return FileResponse(artifact_path, media_type="application/octet-stream", filename=artifact_path.name)


def get_published_release(session: Session, release_id: str) -> FirmwareRelease | None:
    release = session.get(FirmwareRelease, release_id)
    if release is None or release.status != PUBLISHED_STATUS:
        return None
    if not fullmatch(SHA256_PATTERN, release.sha256 or ""):
        return None
    return release


def _latest_compatible_release(
    session: Session,
    *,
    node_role: str,
    hardware_model: str | None,
    current_version: str | None,
) -> FirmwareRelease | None:
    current_code = _version_code(current_version)
    releases = session.scalars(
        select(FirmwareRelease)
        .where(FirmwareRelease.node_role == node_role)
        .where(FirmwareRelease.status == PUBLISHED_STATUS)
        .order_by(FirmwareRelease.version_code.desc())
    )
    for release in releases:
        if release.hardware_model and hardware_model and release.hardware_model != hardware_model:
            continue
        if release.hardware_model and not hardware_model:
            continue
        if release.version_code <= current_code:
            continue
        if release.min_current_version and current_code < _version_code(release.min_current_version):
            continue
        if release.artifact_size_bytes <= 0 or not fullmatch(SHA256_PATTERN, release.sha256 or ""):
            continue
        return release
    return None


def _mark_no_update(session: Session, node: DeviceNode) -> None:
    if node.ota_status == "idle" and not node.ota_available_version and not node.ota_target_version:
        return
    node.ota_status = "idle"
    node.ota_available_version = None
    node.ota_target_version = None
    node.ota_release_id = None
    node.ota_progress = None
    node.ota_error = None
    node.ota_updated_at = datetime.now(timezone.utc)
    session.add(node)
    session.commit()


def _version_code(version: str | None) -> int:
    if not version:
        return 0
    match = fullmatch(r"v?(\d+)(?:\.(\d+))?(?:\.(\d+))?.*", version.strip())
    if not match:
        return 0
    major = int(match.group(1) or 0)
    minor = int(match.group(2) or 0)
    patch = int(match.group(3) or 0)
    return major * 1_000_000 + minor * 1_000 + patch


def _local_artifact_path(artifact_path: str, settings: Settings) -> Path:
    base = Path(settings.firmware_local_dir).resolve()
    target = Path(artifact_path)
    if not target.is_absolute():
        target = base / target
    resolved = target.resolve()
    if base not in resolved.parents and resolved != base:
        raise ValueError("Firmware artifact path escapes firmware storage directory.")
    return resolved


def _gcs_artifact_location(path: str, settings: Settings) -> tuple[str, str]:
    if path.startswith("gs://"):
        parsed = urlparse(path)
        if not parsed.netloc or not parsed.path:
            raise ValueError("GCS firmware artifact path is invalid.")
        return parsed.netloc, unquote(parsed.path.lstrip("/"))
    if not settings.firmware_bucket_name:
        raise ValueError("PLANTLAB_FIRMWARE_BUCKET_NAME is required for GCS firmware artifacts.")
    object_name = f"{settings.firmware_prefix.strip('/')}/{path.lstrip('/')}" if settings.firmware_prefix else path.lstrip("/")
    return settings.firmware_bucket_name, object_name


def _gcs_artifact_response(bucket_name: str, object_name: str):
    try:
        from google.cloud import storage
    except ImportError as exc:
        raise RuntimeError("google-cloud-storage is required for GCS firmware reads.") from exc
    client = storage.Client()
    blob = client.bucket(bucket_name).blob(object_name)
    try:
        data = blob.download_as_bytes()
    except Exception as exc:
        raise RuntimeError("GCS firmware artifact could not be read.") from exc
    return StreamingResponse(BytesIO(data), media_type="application/octet-stream")
