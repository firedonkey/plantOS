from __future__ import annotations

import json
from datetime import datetime, timezone
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from re import fullmatch
from urllib.parse import unquote, urlparse

from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.contracts import DiagnosticSeverity, EventType, OTACommandParams
from app.contracts.device_protocol import SUPPORTED_SCHEMA_MAJOR
from app.core.settings import Settings
from app.models import DeviceNode, FirmwareRelease
from app.schemas.firmware import FirmwareManifestRead, FirmwareOtaStatusCreate, FirmwareOtaStatusRead
from app.services.events import write_canonical_event
from app.services.state_changes import emit_ota_state_change


OTA_STATUSES = {
    "idle",
    "available",
    "preparing",
    "downloading",
    "validating",
    "installing",
    "rebooting",
    "success",
    "failed",
    "rolled_back",
}
PUBLISHED_STATUS = "published"
SHA256_PATTERN = r"^[0-9a-fA-F]{64}$"
OTA_CHANNELS = {"dev", "alpha", "beta", "stable", "local"}


class OtaCompatibilityError(ValueError):
    def __init__(self, code: str, message: str, *, details: dict | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


def build_manifest_for_node(
    session: Session,
    *,
    node: DeviceNode,
    node_role: str,
    current_version: str | None,
    firmware_channel: str = "stable",
) -> FirmwareManifestRead:
    if node.node_role != node_role:
        return FirmwareManifestRead(update_available=False)
    requested_channel = normalize_ota_channel(firmware_channel)

    release = _latest_compatible_release(
        session,
        node_role=node_role,
        hardware_device_id=node.hardware_device_id,
        hardware_model=node.hardware_model,
        current_version=current_version or node.software_version,
        firmware_channel=requested_channel,
    )
    if release is None:
        _mark_no_update(session, node)
        return FirmwareManifestRead(update_available=False)

    should_emit_available = (
        node.ota_status != "available"
        or node.ota_release_id != release.release_id
        or node.ota_target_version != release.version
    )
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
    if should_emit_available:
        _write_ota_event(
            session,
            node=node,
            event_type=EventType.OTA_AVAILABLE,
            status="available",
            correlation_id=release.release_id,
            data={
                "release_id": release.release_id,
                "current_version": current_version or node.software_version,
                "target_version": release.version,
                "firmware_channel": release.channel,
                "progress_percent": 0,
                "hardware_model": release.hardware_model,
                "rollout_percentage": release.rollout_percentage,
                "rollback_release_id": release.rollback_release_id,
                "rollback_version": release.rollback_version,
            },
        )

    return FirmwareManifestRead(
        update_available=True,
        schema_version=1,
        release_id=release.release_id,
        node_role=release.node_role,
        hardware_model=release.hardware_model,
        version=release.version,
        version_code=release.version_code,
        firmware_channel=release.channel,
        min_current_version=release.min_current_version,
        max_current_version=release.max_current_version,
        rollout_percentage=release.rollout_percentage,
        rollback_release_id=release.rollback_release_id,
        rollback_version=release.rollback_version,
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
    correlation_id: str | None = None,
    contract_data: dict | None = None,
) -> FirmwareOtaStatusRead:
    now = datetime.now(timezone.utc)
    previous_status = node.ota_status
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
    elif payload.status == "rolled_back":
        node.software_version = payload.installed_version or node.software_version
        node.ota_progress = payload.progress if payload.progress is not None else 100
        node.ota_error = payload.error
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
    emit_ota_state_change(
        session,
        node=node,
        previous_status=previous_status,
        current_status=payload.status,
        correlation_id=correlation_id or payload.release_id,
        data=_ota_event_data(node, payload, release, contract_data),
        occurred_at=now,
    )
    if _should_emit_started(previous_status, payload.status):
        _write_ota_event(
            session,
            node=node,
            event_type=EventType.OTA_STARTED,
            status=payload.status,
            correlation_id=correlation_id or payload.release_id,
            data=_ota_event_data(node, payload, release, contract_data),
        )
    event_type = _ota_event_type(payload.status)
    if event_type is not None:
        _write_ota_event(
            session,
            node=node,
            event_type=event_type,
            status=payload.status,
            correlation_id=correlation_id or payload.release_id,
            data=_ota_event_data(node, payload, release, contract_data),
        )
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


def validate_ota_command_compatibility(
    *,
    node: DeviceNode,
    params: OTACommandParams,
) -> None:
    schema_major = params.schema_major or SUPPORTED_SCHEMA_MAJOR
    if schema_major != SUPPORTED_SCHEMA_MAJOR:
        raise OtaCompatibilityError(
            "unsupported_schema_version",
            f"Unsupported OTA schema major version: {schema_major}.",
            details={"schema_major": schema_major, "supported_schema_major": SUPPORTED_SCHEMA_MAJOR},
        )
    if params.hardware_model and node.hardware_model and params.hardware_model != node.hardware_model:
        raise OtaCompatibilityError(
            "unsupported_hardware",
            "OTA command hardware_model does not match the registered node hardware_model.",
            details={"expected": node.hardware_model, "actual": params.hardware_model},
        )
    if params.hardware_model and not node.hardware_model:
        raise OtaCompatibilityError(
            "unsupported_hardware",
            "OTA command requires a known node hardware_model.",
            details={"actual": params.hardware_model},
        )

    current_code = _version_code(node.software_version)
    if params.minimum_current_version and current_code < _version_code(params.minimum_current_version):
        raise OtaCompatibilityError(
            "unsupported_firmware_version",
            "Current firmware is below the minimum supported OTA version.",
            details={
                "current_version": node.software_version,
                "minimum_current_version": params.minimum_current_version,
            },
        )
    if params.rollback_version is None and _version_code(params.target_version) <= current_code:
        raise OtaCompatibilityError(
            "unsupported_firmware_version",
            "OTA target_version must be newer than the current firmware version.",
            details={
                "current_version": node.software_version,
                "target_version": params.target_version,
            },
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


def normalize_ota_channel(value: str | None) -> str:
    channel = str(value or "stable").strip().lower()
    if channel not in OTA_CHANNELS:
        raise OtaCompatibilityError(
            "unsupported_ota_channel",
            f"Unsupported OTA channel: {channel}.",
            details={"channel": channel, "supported_channels": sorted(OTA_CHANNELS)},
        )
    return channel


def _latest_compatible_release(
    session: Session,
    *,
    node_role: str,
    hardware_device_id: str,
    hardware_model: str | None,
    current_version: str | None,
    firmware_channel: str,
) -> FirmwareRelease | None:
    current_code = _version_code(current_version)
    releases = session.scalars(
        select(FirmwareRelease)
        .where(FirmwareRelease.node_role == node_role)
        .where(FirmwareRelease.status == PUBLISHED_STATUS)
        .where(FirmwareRelease.channel == firmware_channel)
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
        if release.max_current_version and current_code > _version_code(release.max_current_version):
            continue
        if not _release_rollout_allows_device(release, hardware_device_id):
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


def _ota_event_type(status: str) -> EventType | None:
    return {
        "available": EventType.OTA_AVAILABLE,
        "preparing": EventType.OTA_PREPARING,
        "downloading": EventType.OTA_DOWNLOADING,
        "validating": EventType.OTA_VALIDATING,
        "installing": EventType.OTA_INSTALLING,
        "rebooting": EventType.OTA_REBOOTING,
        "success": EventType.OTA_SUCCESS,
        "failed": EventType.OTA_FAILED,
        "rolled_back": EventType.OTA_ROLLED_BACK,
    }.get(status)


def _should_emit_started(previous_status: str | None, next_status: str) -> bool:
    active_statuses = {"preparing", "downloading", "validating", "installing", "rebooting"}
    inactive_statuses = {"idle", "available", None}
    return next_status in active_statuses and previous_status in inactive_statuses


def _ota_event_data(
    node: DeviceNode,
    payload: FirmwareOtaStatusCreate,
    release: FirmwareRelease | None,
    contract_data: dict | None,
) -> dict:
    data = {
        "release_id": payload.release_id or node.ota_release_id,
        "current_version": payload.installed_version or node.software_version,
        "target_version": payload.target_version or (release.version if release else node.ota_target_version),
        "firmware_channel": (contract_data or {}).get("firmware_channel") or (release.channel if release else "stable"),
        "progress_percent": payload.progress,
        "failure_reason": (contract_data or {}).get("failure_reason"),
        "message": payload.error,
        "rollback_release_id": release.rollback_release_id if release else None,
        "rollback_version": release.rollback_version if release else None,
    }
    if contract_data:
        data["contract"] = contract_data
    return {key: value for key, value in data.items() if value is not None}


def _write_ota_event(
    session: Session,
    *,
    node: DeviceNode,
    event_type: EventType,
    status: str,
    correlation_id: str | None,
    data: dict,
) -> None:
    severity = DiagnosticSeverity.WARNING if status in {"failed", "rolled_back"} else DiagnosticSeverity.INFO
    write_canonical_event(
        session,
        event_type=event_type,
        severity=severity,
        device_id=node.device_id,
        hardware_device_id=node.hardware_device_id,
        node_role=node.node_role,
        correlation_id=correlation_id,
        data=data,
    )


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


def _release_rollout_allows_device(release: FirmwareRelease, hardware_device_id: str) -> bool:
    allowlist = _allowed_hardware_ids(release.allowed_hardware_device_ids)
    if hardware_device_id in allowlist:
        return True
    percentage = max(0, min(100, int(release.rollout_percentage or 0)))
    if percentage >= 100:
        return True
    if percentage <= 0:
        return False
    bucket = int.from_bytes(
        sha256(f"{release.release_id}:{hardware_device_id}".encode("utf-8")).digest()[:4],
        "big",
    ) % 100
    return bucket < percentage


def _allowed_hardware_ids(raw_value: str | None) -> set[str]:
    text = str(raw_value or "").strip()
    if not text:
        return set()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        parsed = None
    if isinstance(parsed, list):
        return {str(item).strip() for item in parsed if str(item).strip()}
    normalized = text.replace("\n", ",").replace(" ", ",")
    return {item.strip() for item in normalized.split(",") if item.strip()}


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
