import logging
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.errors import api_error
from app.api.deps import get_current_user, get_device_from_token
from app.contracts import CameraRole, DiagnosticSeverity, EventType
from app.core.settings import get_settings
from app.db.session import get_session
from app.models import CommandStatus, User
from app.schemas.commands import (
    CommandCreate,
    CommandRead,
    CaptureCommandRequest,
    DeviceCommandEnvelopeRead,
    GrowLightChannelCommandRequest,
    LightCommandRequest,
    PumpCommandRequest,
)
from app.schemas.devices import (
    DeviceCreate,
    DeviceDeleteRead,
    DeviceHardwareHealthRead,
    DeviceHealthCommandRead,
    DeviceHealthNodeRead,
    DeviceRead,
    DeviceReleaseRead,
    DeviceSummaryImageRead,
    DeviceSummaryRead,
    DeviceSummaryReadingRead,
    DeviceTimelapseFrameRead,
    DeviceTimelapseRead,
    DeviceUpdate,
)
from app.schemas.diagnostics import DeviceDiagnosticsRead, DeviceTimelineRead
from app.schemas.setup import DeviceClaimTokenRequest, DeviceSetupCodeRead, DeviceSetupCodeRequest
from app.schemas.readings import SensorReadingRead
from app.services.commands import create_command, list_commands_for_device
from app.services.device_diagnostics import event_read, list_diagnostic_events, list_diagnostic_snapshots, snapshot_read
from app.services.device_nodes import build_node_summary, latest_node_heartbeat_at, list_camera_nodes_for_device, list_nodes_for_device
from app.services.device_timeline import list_timeline_events, timeline_event_read
from app.services.demo import (
    demo_capture_command,
    demo_device_read,
    demo_device_summary,
    demo_diagnostics,
    demo_forbidden_message,
    demo_image_response,
    demo_images,
    demo_latest_image,
    demo_light_command,
    demo_readings,
    demo_timelapse,
    demo_timeline,
    is_demo_device_id,
    is_demo_user,
)
from app.services.devices import (
    create_device_for_user,
    delete_device_for_user,
    factory_reset_device,
    get_device_for_user,
    list_devices_for_user,
    release_device_for_user,
    update_device_for_user,
)
from app.services.images import list_recent_images_for_device, list_timelapse_images_for_device
from app.services.lifecycle_events import write_canonical_event_once
from app.services.readings import MAX_READING_QUERY_LIMIT, get_latest_reading_for_device, list_recent_readings_for_device
from app.services.storage import image_client_url
from app.services.timelapse import (
    empty_timelapse_payload,
    get_timelapse_snapshot,
    refresh_device_timelapse_snapshot,
    timelapse_snapshot_payload,
)


router = APIRouter(prefix="/api/devices", tags=["devices"])
logger = logging.getLogger(__name__)

HEARTBEAT_STALE_AFTER = timedelta(seconds=90)
HEARTBEAT_OFFLINE_AFTER = timedelta(minutes=5)
READING_STALE_AFTER = timedelta(minutes=2)
READING_OFFLINE_AFTER = timedelta(minutes=15)
IMAGE_STALE_AFTER = timedelta(minutes=5)
IMAGE_OFFLINE_AFTER = timedelta(minutes=20)


@router.get("/demo/images/{image_id}", name="demo_image")
def demo_image(image_id: int):
    return demo_image_response(image_id)


@dataclass(frozen=True)
class CommandHealthSnapshot:
    latest: object | None
    last_failed: object | None
    last_successful: object | None


@router.get("", response_model=list[DeviceRead])
def list_devices(
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if is_demo_user(current_user):
        return [demo_device_read(request, current_user.id)]
    devices = list_devices_for_user(session, current_user)
    return [_build_device_read(request, session, device) for device in devices]


@router.post("", response_model=DeviceRead, status_code=201)
def create_device(
    payload: DeviceCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if is_demo_user(current_user):
        raise api_error(403, "demo_account_read_only", demo_forbidden_message("provision"))
    return create_device_for_user(session, current_user, payload)


@router.post("/setup-code", response_model=DeviceSetupCodeRead)
async def create_device_setup_code(
    request: Request,
    payload: DeviceSetupCodeRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if is_demo_user(current_user):
        raise api_error(403, "demo_account_read_only", demo_forbidden_message("provision"))
    settings = get_settings()
    serial_number = payload.serial_number.strip()
    if not serial_number:
        raise api_error(422, "validation_error", "SN is required.")

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                f"{settings.provisioning_api_url}/api/devices/setup-code",
                json={
                    "serial_number": serial_number,
                    "device_name": payload.device_name.strip() if payload.device_name else None,
                    "location": payload.location.strip() if payload.location else None,
                },
                headers={
                    "x-plantlab-service-secret": settings.provisioning_service_secret or "",
                    "x-plantlab-user-id": str(current_user.id),
                    "x-plantlab-user-email": current_user.email or "",
                },
            )
    except httpx.HTTPError as exc:
        raise api_error(502, "provisioning_service_unavailable", f"Provisioning service unavailable: {exc}") from exc

    try:
        upstream_payload = response.json()
    except ValueError as exc:
        raise api_error(502, "invalid_upstream_response", "Provisioning service returned an invalid response.") from exc

    if response.status_code >= 400:
        raise api_error(
            response.status_code,
            "setup_code_request_failed",
            upstream_payload.get("message") or upstream_payload.get("error") or "Could not verify this SN.",
        )

    setup_token = upstream_payload.get("setup_code") or upstream_payload.get("claim_token")
    frontend_origin = (request.headers.get("origin") or str(request.base_url).rstrip("/")).rstrip("/")
    setup_finishing_url = _build_setup_finishing_url(
        frontend_origin=frontend_origin,
        device_name=payload.device_name or "",
        location=payload.location or "",
        expect_image=True,
    )
    continue_setup_url = _build_continue_setup_url(
        settings=settings,
        setup_token=setup_token,
        serial_number=upstream_payload.get("serial_number") or serial_number,
        device_name=payload.device_name or "",
        location=payload.location or "",
        setup_finishing_url=setup_finishing_url,
    )
    return DeviceSetupCodeRead(
        serial_number=upstream_payload.get("serial_number") or serial_number,
        setup_code=upstream_payload.get("setup_code"),
        claim_token=upstream_payload.get("claim_token"),
        setup_token=setup_token,
        local_setup_url=settings.local_setup_url,
        provisioning_api_url=settings.effective_provisioning_public_url,
        platform_url=settings.device_platform_url,
        setup_finishing_url=setup_finishing_url,
        continue_setup_url=continue_setup_url,
        expect_image=True,
    )


@router.post("/claim-token", response_model=DeviceSetupCodeRead)
async def create_device_claim_token(
    request: Request,
    payload: DeviceClaimTokenRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    del session
    if is_demo_user(current_user):
        raise api_error(403, "demo_account_read_only", demo_forbidden_message("provision"))
    settings = get_settings()
    identity = payload.device_identity
    expected_device_id = (identity.hardware_device_id or identity.device_id).strip()
    if not expected_device_id:
        raise api_error(422, "validation_error", "Device identity is required.")

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                f"{settings.provisioning_api_url}/api/devices/claim-token",
                json={
                    "device_name": payload.device_name.strip() if payload.device_name else None,
                    "location": payload.location.strip() if payload.location else None,
                    "device_identity": {
                        "source": identity.source,
                        "schema_version": identity.schema_version,
                        "device_id": identity.device_id.strip(),
                        "hardware_device_id": expected_device_id,
                        "hardware_model": identity.hardware_model,
                        "hardware_version": identity.hardware_version,
                        "software_version": identity.software_version,
                        "node_role": identity.node_role,
                        "display_name": identity.display_name,
                        "ble_name": identity.ble_name,
                        "serial_number": identity.serial_number,
                    },
                },
                headers={
                    "x-plantlab-service-secret": settings.provisioning_service_secret or "",
                    "x-plantlab-user-id": str(current_user.id),
                    "x-plantlab-user-email": current_user.email or "",
                },
            )
    except httpx.HTTPError as exc:
        raise api_error(502, "provisioning_service_unavailable", f"Provisioning service unavailable: {exc}") from exc

    try:
        upstream_payload = response.json()
    except ValueError as exc:
        raise api_error(502, "invalid_upstream_response", "Provisioning service returned an invalid response.") from exc

    if response.status_code >= 400:
        raise api_error(
            response.status_code,
            "claim_token_request_failed",
            upstream_payload.get("message") or upstream_payload.get("error") or "Could not create a device claim token.",
        )

    setup_token = upstream_payload.get("setup_code") or upstream_payload.get("claim_token")
    frontend_origin = (request.headers.get("origin") or str(request.base_url).rstrip("/")).rstrip("/")
    setup_finishing_url = _build_setup_finishing_url(
        frontend_origin=frontend_origin,
        device_name=payload.device_name or "",
        location=payload.location or "",
        expect_image=True,
    )
    continue_setup_url = _build_continue_setup_url(
        settings=settings,
        setup_token=setup_token,
        serial_number=upstream_payload.get("serial_number") or expected_device_id,
        device_name=payload.device_name or "",
        location=payload.location or "",
        setup_finishing_url=setup_finishing_url,
    )
    return DeviceSetupCodeRead(
        serial_number=upstream_payload.get("serial_number"),
        expected_device_id=upstream_payload.get("expected_device_id") or expected_device_id,
        setup_code=upstream_payload.get("setup_code"),
        claim_token=upstream_payload.get("claim_token"),
        setup_token=setup_token,
        local_setup_url=settings.local_setup_url,
        provisioning_api_url=settings.effective_provisioning_public_url,
        platform_url=settings.device_platform_url,
        setup_finishing_url=setup_finishing_url,
        continue_setup_url=continue_setup_url,
        expect_image=True,
    )


@router.get("/{device_id}", response_model=DeviceRead)
def get_device(
    device_id: int,
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if is_demo_user(current_user):
        if is_demo_device_id(device_id):
            return demo_device_read(request, current_user.id)
        raise HTTPException(status_code=404, detail="Device not found.")
    device = get_device_for_user(session, current_user, device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found.")
    return _build_device_read(request, session, device)


@router.patch("/{device_id}", response_model=DeviceRead)
def update_device(
    device_id: int,
    payload: DeviceUpdate,
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if is_demo_user(current_user):
        if is_demo_device_id(device_id):
            raise api_error(403, "demo_account_read_only", demo_forbidden_message("modify"))
        raise HTTPException(status_code=404, detail="Device not found.")
    device = update_device_for_user(session, current_user, device_id, payload)
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found.")
    return _build_device_read(request, session, device)


@router.delete("/{device_id}", response_model=DeviceDeleteRead)
def delete_device(
    device_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if is_demo_user(current_user):
        if is_demo_device_id(device_id):
            raise api_error(403, "demo_account_read_only", demo_forbidden_message("delete"))
        raise HTTPException(status_code=404, detail="Device not found.")
    deleted = delete_device_for_user(session, current_user, device_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Device not found.")
    return DeviceDeleteRead(
        status="released",
        device_id=device_id,
        message="Device released and archived.",
    )


@router.post("/{device_id}/release", response_model=DeviceReleaseRead)
def release_device(
    device_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if is_demo_user(current_user):
        if is_demo_device_id(device_id):
            raise api_error(403, "demo_account_read_only", demo_forbidden_message("release"))
        raise HTTPException(status_code=404, detail="Device not found.")
    device = release_device_for_user(session, current_user, device_id)
    if device is None or device.released_at is None:
        raise HTTPException(status_code=404, detail="Device not found.")
    return DeviceReleaseRead(
        status="released",
        device_id=device_id,
        released_at=device.released_at,
        message="Device released for transfer. Hold the device button for 20 seconds to clear local Wi-Fi and tokens.",
    )


@router.get("/{device_id}/summary", response_model=DeviceSummaryRead)
def get_device_summary(
    device_id: int,
    request: Request,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if is_demo_user(current_user):
        if is_demo_device_id(device_id):
            return demo_device_summary(request, current_user.id)
        raise HTTPException(status_code=404, detail="Device not found.")
    device = get_device_for_user(session, current_user, device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found.")

    latest_reading = get_latest_reading_for_device(session, device.id)
    latest_images = list_recent_images_for_device(session, device.id, limit=1, camera_role=CameraRole.TOP)
    latest_image = latest_images[0] if latest_images else None
    nodes = list_nodes_for_device(session, device.id)
    command_health = _command_health(session, device.id)
    diagnostic_snapshots = list_diagnostic_snapshots(session, device.id)
    diagnostic_events = list_diagnostic_events(session, device.id, limit=20)

    return DeviceSummaryRead(
        id=device.id,
        name=device.name,
        location=device.location,
        plant_type=device.plant_type,
        current_light_on=device.current_light_on,
        current_light_intensity_percent=device.current_light_intensity_percent,
        current_pump_on=device.current_pump_on,
        latest_reading=(
            DeviceSummaryReadingRead.model_validate(latest_reading, from_attributes=True)
            if latest_reading is not None
            else None
        ),
        latest_image=(
            _build_summary_image_read(request, latest_image)
            if latest_image is not None
            else None
        ),
        node_summary=build_node_summary(nodes),
        hardware_health=_build_hardware_health(
            nodes=nodes,
            latest_reading=latest_reading,
            latest_image=latest_image,
            command_health=command_health,
            diagnostic_snapshots=diagnostic_snapshots,
            diagnostic_events=diagnostic_events,
        ),
    )


@router.get("/{device_id}/diagnostics", response_model=DeviceDiagnosticsRead)
def get_device_diagnostics(
    device_id: int,
    events_limit: int = Query(default=20, ge=1, le=100),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if is_demo_user(current_user):
        if is_demo_device_id(device_id):
            return demo_diagnostics(current_user.id, events_limit=events_limit)
        raise HTTPException(status_code=404, detail="Device not found.")
    device = get_device_for_user(session, current_user, device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found.")
    return DeviceDiagnosticsRead(
        snapshots=[snapshot_read(snapshot) for snapshot in list_diagnostic_snapshots(session, device.id)],
        recent_events=[event_read(event) for event in list_diagnostic_events(session, device.id, limit=events_limit)],
    )


@router.get("/{device_id}/timeline", response_model=DeviceTimelineRead)
def get_device_timeline(
    device_id: int,
    limit: int = Query(default=50, ge=1, le=100),
    before: datetime | None = Query(default=None),
    after: datetime | None = Query(default=None),
    event_type: list[str] | None = Query(default=None),
    severity: list[str] | None = Query(default=None),
    node_role: str | None = Query(default=None, min_length=3, max_length=40),
    correlation_id: str | None = Query(default=None, min_length=1, max_length=120),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if is_demo_user(current_user):
        if is_demo_device_id(device_id):
            return demo_timeline(
                current_user.id,
                limit=limit,
                before=before,
                after=after,
                event_types=event_type,
                severities=severity,
                node_role=node_role,
                correlation_id=correlation_id,
            )
        raise HTTPException(status_code=404, detail="Device not found.")
    device = get_device_for_user(session, current_user, device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found.")
    events = list_timeline_events(
        session,
        device.id,
        limit=limit,
        before=before,
        after=after,
        event_types=event_type,
        severities=severity,
        node_role=node_role,
        correlation_id=correlation_id,
    )
    return DeviceTimelineRead(
        events=[timeline_event_read(event) for event in events],
        next_before=events[-1].occurred_at if len(events) == limit else None,
    )


@router.get("/{device_id}/camera-nodes", response_model=list[DeviceHealthNodeRead])
def get_device_camera_nodes(
    device_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if is_demo_user(current_user):
        if is_demo_device_id(device_id):
            return []
        raise HTTPException(status_code=404, detail="Device not found.")
    device = get_device_for_user(session, current_user, device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found.")
    snapshots = {
        snapshot.hardware_device_id: snapshot
        for snapshot in list_diagnostic_snapshots(session, device.id)
    }
    return [
        health_node
        for health_node in (
            _build_health_node(_node_summary_from_model(node), snapshots)
            for node in list_camera_nodes_for_device(session, device.id)
        )
        if health_node is not None
    ]


@router.get("/{device_id}/readings", response_model=list[SensorReadingRead])
def get_device_readings(
    device_id: int,
    limit: int = Query(default=50, ge=1, le=MAX_READING_QUERY_LIMIT),
    start: datetime | None = Query(default=None),
    end: datetime | None = Query(default=None),
    order: str = Query(default="newest", pattern="^(newest|oldest)$"),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if is_demo_user(current_user):
        if is_demo_device_id(device_id):
            return demo_readings(
                current_user.id,
                limit=limit,
                since=start,
                until=end,
                order=order,
            )
        raise HTTPException(status_code=404, detail="Device not found.")
    device = get_device_for_user(session, current_user, device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found.")
    return list_recent_readings_for_device(
        session,
        device.id,
        limit=limit,
        since=start,
        until=end,
        order=order,
    )


@router.get("/{device_id}/images/latest", response_model=DeviceSummaryImageRead | None)
def get_device_latest_image(
    device_id: int,
    request: Request,
    camera_role: str = Query(default="top", pattern="^(top|side|all)$"),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if is_demo_user(current_user):
        if is_demo_device_id(device_id):
            return demo_latest_image(request, current_user.id)
        raise HTTPException(status_code=404, detail="Device not found.")
    device = get_device_for_user(session, current_user, device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found.")

    latest_images = list_recent_images_for_device(session, device.id, limit=1, camera_role=camera_role)
    latest_image = latest_images[0] if latest_images else None
    if latest_image is None:
        return None

    return _build_summary_image_read(request, latest_image)


@router.get("/{device_id}/images", response_model=list[DeviceSummaryImageRead])
def get_device_images(
    device_id: int,
    request: Request,
    limit: int = Query(default=12, ge=1, le=50),
    camera_role: str = Query(default="all", pattern="^(top|side|all)$"),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if is_demo_user(current_user):
        if is_demo_device_id(device_id):
            return demo_images(request, current_user.id, limit=limit)
        raise HTTPException(status_code=404, detail="Device not found.")
    device = get_device_for_user(session, current_user, device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found.")

    images = list_recent_images_for_device(session, device.id, limit=limit, camera_role=camera_role)
    return [_build_summary_image_read(request, image) for image in images]


@router.get("/{device_id}/timelapse", response_model=DeviceTimelapseRead)
def get_device_timelapse(
    device_id: int,
    request: Request,
    days: int = Query(default=7, ge=1, le=30),
    interval_minutes: int = Query(default=60, ge=5, le=24 * 60),
    max_frames: int = Query(default=168, ge=2, le=720),
    target_duration_seconds: int = Query(default=30, ge=5, le=120),
    playback_frame_ms: int | None = Query(default=None, ge=50, le=30_000),
    camera_role: str = Query(default="top", pattern="^(top|side)$"),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if is_demo_user(current_user):
        if is_demo_device_id(device_id):
            return demo_timelapse(
                request,
                current_user.id,
                days=days,
                interval_minutes=interval_minutes,
                max_frames=max_frames,
                target_duration_seconds=target_duration_seconds,
                playback_frame_ms=playback_frame_ms,
            )
        raise HTTPException(status_code=404, detail="Device not found.")
    device = get_device_for_user(session, current_user, device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found.")

    snapshot = get_timelapse_snapshot(
        session,
        device.id,
        days=days,
        interval_minutes=interval_minutes,
        max_frames=max_frames,
        target_duration_seconds=target_duration_seconds,
        camera_role=camera_role,
    )
    if snapshot is None or _timelapse_snapshot_expired(snapshot.expires_at):
        return DeviceTimelapseRead.model_validate(
            empty_timelapse_payload(
                device_id=device.id,
                days=days,
                interval_minutes=interval_minutes,
                target_duration_seconds=target_duration_seconds,
                camera_role=camera_role,
                playback_frame_ms=playback_frame_ms,
            )
        )
    payload = timelapse_snapshot_payload(snapshot, playback_frame_ms=playback_frame_ms)
    return DeviceTimelapseRead.model_validate(payload)


@router.post("/{device_id}/timelapse/refresh", response_model=DeviceTimelapseRead)
def refresh_device_timelapse(
    device_id: int,
    request: Request,
    days: int = Query(default=7, ge=1, le=30),
    interval_minutes: int = Query(default=5, ge=5, le=24 * 60),
    max_frames: int = Query(default=168, ge=2, le=720),
    target_duration_seconds: int = Query(default=30, ge=5, le=120),
    camera_role: str = Query(default="top", pattern="^(top|side)$"),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if is_demo_user(current_user):
        if is_demo_device_id(device_id):
            return demo_timelapse(
                request,
                current_user.id,
                days=days,
                interval_minutes=interval_minutes,
                max_frames=max_frames,
                target_duration_seconds=target_duration_seconds,
            )
        raise HTTPException(status_code=404, detail="Device not found.")
    device = get_device_for_user(session, current_user, device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found.")
    snapshot = refresh_device_timelapse_snapshot(
        session=session,
        request=request,
        device=device,
        settings=get_settings(),
        days=days,
        interval_minutes=interval_minutes,
        max_frames=max_frames,
        target_duration_seconds=target_duration_seconds,
        camera_role=camera_role,
    )
    return DeviceTimelapseRead.model_validate(timelapse_snapshot_payload(snapshot))


def _timelapse_snapshot_expired(expires_at: datetime | None) -> bool:
    if expires_at is None:
        return False
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    return expires_at <= datetime.now(timezone.utc) + timedelta(seconds=60)


@router.post("/{device_id}/commands/light", response_model=DeviceCommandEnvelopeRead, status_code=201)
def create_light_command(
    device_id: int,
    payload: LightCommandRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if is_demo_user(current_user):
        if is_demo_device_id(device_id):
            return demo_light_command(current_user.id, payload)
        raise HTTPException(status_code=404, detail="Device not found.")
    device = get_device_for_user(session, current_user, device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found.")

    if payload.intensity_percent is not None:
        nodes = list_nodes_for_device(session, device.id)
        if not _device_supports_light_intensity(nodes):
            raise HTTPException(status_code=409, detail="Light intensity control is not supported by this device.")
        command = create_command(
            session,
            device.id,
            CommandCreate(target="grow_light", action="set_intensity", value=str(payload.intensity_percent)),
        )
        return _queued_command_response(
            device_id=device.id,
            command_name="grow_light",
            action="set_intensity",
            command=command,
            message=f"Grow-light command queued: set intensity to {payload.intensity_percent}%.",
        )

    if payload.state is None:
        raise HTTPException(status_code=422, detail="Light command state is required.")
    command = create_command(
        session,
        device.id,
        CommandCreate(target="grow_light", action=payload.state),
    )
    return _queued_command_response(
        device_id=device.id,
        command_name="grow_light",
        action=payload.state,
        command=command,
        message=f"Grow-light command queued: turn {payload.state}.",
    )


@router.post("/{device_id}/commands/grow-light-channel", response_model=DeviceCommandEnvelopeRead, status_code=201)
def create_grow_light_channel_command(
    device_id: int,
    payload: GrowLightChannelCommandRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if is_demo_user(current_user):
        if is_demo_device_id(device_id):
            raise api_error(403, "demo_account_read_only", demo_forbidden_message("send grow-light test commands to"))
        raise HTTPException(status_code=404, detail="Device not found.")
    device = get_device_for_user(session, current_user, device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found.")

    nodes = list_nodes_for_device(session, device.id)
    if not _device_supports_grow_light_channel_control(nodes):
        raise HTTPException(status_code=409, detail="Grow-light channel control is not supported by this device.")

    value = json.dumps(
        {"channel": payload.channel, "brightness_percent": payload.intensity_percent},
        separators=(",", ":"),
        sort_keys=True,
    )
    command = create_command(
        session,
        device.id,
        CommandCreate(target="grow_light", action="set_channel_intensity", value=value),
    )
    return _queued_command_response(
        device_id=device.id,
        command_name="grow_light",
        action=f"set_{payload.channel}_intensity",
        command=command,
        message=f"Grow-light {payload.channel} channel command queued: set intensity to {payload.intensity_percent}%.",
    )


@router.post("/{device_id}/commands/pump", response_model=DeviceCommandEnvelopeRead, status_code=201)
def create_pump_command(
    device_id: int,
    payload: PumpCommandRequest,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if is_demo_user(current_user):
        if is_demo_device_id(device_id):
            raise api_error(403, "demo_account_read_only", demo_forbidden_message("run pump commands on"))
        raise HTTPException(status_code=404, detail="Device not found.")
    device = get_device_for_user(session, current_user, device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found.")

    command = create_command(
        session,
        device.id,
        CommandCreate(
            target="pump",
            action=payload.action,
            value=str(payload.seconds) if payload.action == "run" and payload.seconds is not None else None,
        ),
    )
    return _queued_command_response(
        device_id=device.id,
        command_name="pump",
        action=payload.action,
        command=command,
        message=(
            f"Pump command queued: run for {payload.seconds} seconds."
            if payload.action == "run" and payload.seconds is not None
            else "Pump command queued: turn off."
        ),
    )


@router.post("/{device_id}/commands/capture", response_model=DeviceCommandEnvelopeRead, status_code=201)
def create_capture_command(
    device_id: int,
    payload: CaptureCommandRequest | None = None,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    if is_demo_user(current_user):
        if is_demo_device_id(device_id):
            return demo_capture_command(current_user.id)
        raise HTTPException(status_code=404, detail="Device not found.")
    device = get_device_for_user(session, current_user, device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found.")
    payload = payload or CaptureCommandRequest()
    command = create_command(
        session,
        device.id,
        CommandCreate(target="camera", action="capture", value=_capture_command_value(payload)),
    )
    source_nodes = _image_event_source_nodes(session, device.id, payload)
    for source_node in source_nodes:
        write_canonical_event_once(
            session,
            event_type=EventType.IMAGE_CAPTURE_STARTED,
            severity=DiagnosticSeverity.INFO,
            device_id=device.id,
            hardware_device_id=source_node.hardware_device_id,
            node_role=source_node.node_role,
            correlation_id=f"cmd_{command.id}",
            data={
                "command_id": f"cmd_{command.id}",
                "upload_reason": "manual",
                "source_hardware_device_id": source_node.hardware_device_id,
                "source_node_role": source_node.node_role,
                "camera_node_id": source_node.hardware_device_id,
                "camera_role": source_node.camera_role,
            },
        )
    return _queued_command_response(
        device_id=device.id,
        command_name="capture",
        action="capture",
        command=command,
        message="Capture command queued.",
        camera_role=str(getattr(payload.camera_role, "value", payload.camera_role)),
        camera_node_id=payload.camera_node_id,
    )


@router.post("/{device_id}/factory-reset")
def factory_reset_device_route(
    device_id: int,
    request: Request,
    session: Session = Depends(get_session),
):
    device = get_device_from_token(request, session)
    if device is None:
        raise HTTPException(status_code=401, detail="Valid device token required.")
    if device.id != device_id:
        raise HTTPException(status_code=403, detail="Device token does not match device_id.")

    factory_reset_device(session, device)
    return {"ok": True, "device_id": device_id, "status": "released"}


@router.post("/register-provisioned")
async def register_provisioned_device_proxy(request: Request):
    settings = get_settings()
    try:
        payload = await request.json()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON payload.") from exc

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(
                f"{settings.provisioning_api_url}/api/devices/register",
                json=payload,
            )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Provisioning service unavailable: {exc}") from exc

    try:
        response_payload = response.json()
    except ValueError as exc:
        raise HTTPException(status_code=502, detail="Provisioning service returned an invalid response.") from exc

    if response.status_code >= 400:
        logger.warning(
            "provisioned device registration failed status=%s payload=%s response=%s",
            response.status_code,
            _sanitize_registration_log_payload(payload),
            _sanitize_registration_log_payload(response_payload),
        )

    return JSONResponse(response_payload, status_code=response.status_code)


def _sanitize_registration_log_payload(value):
    if isinstance(value, dict):
        sanitized = {}
        for key, item in value.items():
            normalized_key = str(key).lower()
            if normalized_key in {
                "claim_token",
                "setup_code",
                "setup_token",
                "device_access_token",
                "device_token",
                "api_token",
                "wifi_password",
                "password",
                "psk",
            }:
                sanitized[key] = "[redacted]"
            elif normalized_key in {"wifi_ssid", "ssid"}:
                sanitized[key] = "[omitted]"
            else:
                sanitized[key] = _sanitize_registration_log_payload(item)
        return sanitized
    if isinstance(value, list):
        return [_sanitize_registration_log_payload(item) for item in value]
    return value


def _image_event_source_nodes(session: Session, device_id: int, payload: CaptureCommandRequest) -> list:
    nodes = list_nodes_for_device(session, device_id)
    if payload.camera_node_id:
        return [
            node
            for node in nodes
            if node.hardware_device_id == payload.camera_node_id and str(node.node_role).lower() == "camera"
        ]
    camera_role = str(getattr(payload.camera_role, "value", payload.camera_role) or "top").lower()
    camera_nodes = [node for node in nodes if str(node.node_role).lower() == "camera"]
    if camera_role == "all":
        return camera_nodes
    matched = [node for node in camera_nodes if str(node.camera_role or "").lower() == camera_role]
    if matched:
        return matched
    if camera_role == CameraRole.TOP.value:
        legacy = [node for node in camera_nodes if node.camera_role is None]
        if legacy:
            return legacy[:1]
    fallback = next((node for node in nodes if str(node.node_role).lower() in {"master", "single_board"}), None)
    return [fallback] if fallback is not None else []


def _capture_command_value(payload: CaptureCommandRequest) -> str:
    data = {
        "reason": "manual",
        "camera_role": str(getattr(payload.camera_role, "value", payload.camera_role)),
    }
    if payload.camera_node_id:
        data["camera_node_id"] = payload.camera_node_id
    return json.dumps(data, separators=(",", ":"))


def _build_device_read(request: Request, session: Session, device) -> DeviceRead:
    latest_reading = get_latest_reading_for_device(session, device.id)
    latest_images = list_recent_images_for_device(session, device.id, limit=1, camera_role=CameraRole.TOP)
    latest_image = latest_images[0] if latest_images else None
    nodes = list_nodes_for_device(session, device.id)
    node_summary = build_node_summary(nodes)
    command_health = _command_health(session, device.id)
    diagnostic_snapshots = list_diagnostic_snapshots(session, device.id)
    diagnostic_events = list_diagnostic_events(session, device.id, limit=20)
    return DeviceRead(
        id=device.id,
        name=device.name,
        location=device.location,
        plant_type=device.plant_type,
        api_token=device.api_token,
        created_at=device.created_at,
        released_at=device.released_at,
        archived_at=device.archived_at,
        release_reason=device.release_reason,
        status=_device_status(node_summary, latest_reading, latest_node_heartbeat_at(nodes)),
        current_light_on=device.current_light_on,
        current_light_intensity_percent=device.current_light_intensity_percent,
        current_pump_on=device.current_pump_on,
        latest_reading=(
            DeviceSummaryReadingRead.model_validate(latest_reading, from_attributes=True)
            if latest_reading is not None
            else None
        ),
        latest_image=(
            _build_summary_image_read(request, latest_image)
            if latest_image is not None
            else None
        ),
        node_summary=node_summary,
        hardware_health=_build_hardware_health(
            nodes=nodes,
            latest_reading=latest_reading,
            latest_image=latest_image,
            command_health=command_health,
            diagnostic_snapshots=diagnostic_snapshots,
            diagnostic_events=diagnostic_events,
        ),
    )


def _device_status(node_summary: dict, latest_reading, last_heartbeat_at: datetime | None) -> str:
    primary = node_summary.get("primary") or {}
    primary_status = str(primary.get("status") or "").lower()
    if primary_status == "online":
        heartbeat_status = _freshness_status(
            last_heartbeat_at,
            stale_after=HEARTBEAT_STALE_AFTER,
            offline_after=HEARTBEAT_OFFLINE_AFTER,
        )
        if heartbeat_status in {"stale", "offline"}:
            return heartbeat_status
        return "online"
    if primary_status in {"offline", "error"}:
        return "offline"
    if latest_reading is not None:
        return "online"
    return "unknown"


def _queued_command_response(
    *,
    device_id: int,
    command_name: str,
    action: str,
    command,
    message: str,
    camera_role: str | None = None,
    camera_node_id: str | None = None,
) -> DeviceCommandEnvelopeRead:
    return DeviceCommandEnvelopeRead(
        status="accepted",
        device_id=device_id,
        command=command_name,
        action=action,
        queued=True,
        message=message,
        command_id=command.id,
        command_status=command.status,
        created_at=command.created_at,
        value=command.value,
        camera_role=camera_role,
        camera_node_id=camera_node_id,
    )


def _build_summary_image_read(request: Request, image) -> DeviceSummaryImageRead:
    return DeviceSummaryImageRead(
        id=image.id,
        content_url=image_client_url(image, request, get_settings()),
        timestamp=image.timestamp,
        source_hardware_device_id=image.source_hardware_device_id,
        camera_role=image.camera_role,
    )


def _node_summary_from_model(node) -> dict:
    return {
        "hardware_device_id": node.hardware_device_id,
        "node_role": node.node_role,
        "node_index": node.node_index,
        "camera_role": node.camera_role,
        "display_name": node.display_name,
        "hardware_model": node.hardware_model,
        "hardware_version": node.hardware_version,
        "software_version": node.software_version,
        "ota_status": node.ota_status,
        "ota_available_version": node.ota_available_version,
        "ota_target_version": node.ota_target_version,
        "ota_release_id": node.ota_release_id,
        "ota_progress": node.ota_progress,
        "ota_error": node.ota_error,
        "ota_updated_at": node.ota_updated_at,
        "ota_last_success_at": node.ota_last_success_at,
        "capabilities": node.capabilities or {},
        "status": node.status,
        "last_seen_at": node.last_seen_at,
    }


def _device_supports_light_intensity(nodes: list) -> bool:
    return any(_node_supports_light_intensity(getattr(node, "capabilities", None) or {}) for node in nodes)


def _device_supports_grow_light_channel_control(nodes: list) -> bool:
    return any(_node_supports_grow_light_channel_control(getattr(node, "capabilities", None) or {}) for node in nodes)


def _node_supports_light_intensity(capabilities: dict) -> bool:
    if capabilities.get("light_intensity_control") is True:
        return True
    if capabilities.get("light_dimming") is True or capabilities.get("light_pwm") is True:
        return True
    modes = capabilities.get("light_control_modes")
    if isinstance(modes, list):
        normalized_modes = {str(mode).strip().lower() for mode in modes}
        return bool(normalized_modes & {"intensity", "dimming", "pwm"})
    return False


def _node_supports_grow_light_channel_control(capabilities: dict) -> bool:
    return capabilities.get("grow_light_channel_control") is True


def _command_health(session: Session, device_id: int) -> CommandHealthSnapshot:
    commands = list_commands_for_device(session, device_id, limit=20)
    return CommandHealthSnapshot(
        latest=commands[0] if commands else None,
        last_failed=next(
            (command for command in commands if command.status in {CommandStatus.FAILED, CommandStatus.TIMED_OUT}),
            None,
        ),
        last_successful=next((command for command in commands if command.status == CommandStatus.COMPLETED), None),
    )


def _build_hardware_health(
    *,
    nodes: list,
    latest_reading,
    latest_image,
    command_health: CommandHealthSnapshot,
    diagnostic_snapshots: list | None = None,
    diagnostic_events: list | None = None,
) -> DeviceHardwareHealthRead:
    node_summary = build_node_summary(nodes)
    primary = node_summary.get("primary")
    primary_status = (primary or {}).get("status")
    camera_summaries = node_summary.get("cameras") or []
    last_heartbeat_at = latest_node_heartbeat_at(nodes)
    snapshot_by_hardware_id = {
        snapshot.hardware_device_id: snapshot
        for snapshot in (diagnostic_snapshots or [])
    }
    primary_snapshot = snapshot_by_hardware_id.get((primary or {}).get("hardware_device_id"))
    camera_snapshots = [
        snapshot_by_hardware_id.get(item.get("hardware_device_id"))
        for item in camera_summaries
        if item.get("hardware_device_id") in snapshot_by_hardware_id
    ]
    last_reading_at = getattr(latest_reading, "timestamp", None) or getattr(primary_snapshot, "last_sensor_reading_at", None)
    last_image_at = getattr(latest_image, "timestamp", None) or _latest_snapshot_timestamp(
        [snapshot.last_camera_image_upload_at for snapshot in camera_snapshots if snapshot is not None]
    )
    heartbeat_status = _freshness_status(last_heartbeat_at, stale_after=HEARTBEAT_STALE_AFTER, offline_after=HEARTBEAT_OFFLINE_AFTER)
    reading_status = _reading_status(
        timestamp=last_reading_at,
        primary_status=primary_status,
        last_heartbeat_at=last_heartbeat_at,
    )
    image_status = _image_status(camera_summaries, last_image_at)
    camera_status = _camera_status(camera_summaries)
    recent_event_reads = [event_read(event) for event in (diagnostic_events or [])]
    attention_reasons = _attention_reasons(
        primary=primary,
        camera_summaries=camera_summaries,
        snapshots=diagnostic_snapshots or [],
        heartbeat_status=heartbeat_status,
        reading_status=reading_status,
        image_status=image_status,
        camera_status=camera_status,
        command_health=command_health,
    )
    return DeviceHardwareHealthRead(
        overall_status=node_summary.get("overall_status") or "offline",
        master_status=primary_status,
        master_online=primary_status == "online",
        primary=_build_health_node(primary, snapshot_by_hardware_id),
        cameras=[health_node for health_node in (_build_health_node(item, snapshot_by_hardware_id) for item in camera_summaries) if health_node is not None],
        last_heartbeat_at=last_heartbeat_at,
        heartbeat_status=heartbeat_status,
        last_reading_at=last_reading_at,
        reading_status=reading_status,
        last_image_at=last_image_at,
        image_status=image_status,
        camera_status=camera_status,
        last_command=_build_health_command(command_health.latest),
        last_failed_command_reason=getattr(command_health.last_failed, "message", None),
        last_failed_command_at=getattr(command_health.last_failed, "completed_at", None),
        last_successful_command_at=getattr(command_health.last_successful, "completed_at", None),
        friendly_status=_friendly_status(heartbeat_status, attention_reasons),
        attention_reasons=attention_reasons,
        recent_events=recent_event_reads,
    )


def _build_health_node(node_summary_item: dict | None, snapshots: dict | None = None) -> DeviceHealthNodeRead | None:
    if not node_summary_item:
        return None
    payload = dict(node_summary_item)
    payload["health_status"] = _node_health_status(node_summary_item)
    if snapshots:
        payload["diagnostics"] = snapshot_read(snapshots.get(node_summary_item.get("hardware_device_id")))
    return DeviceHealthNodeRead.model_validate(payload)


def _build_health_command(command) -> DeviceHealthCommandRead | None:
    if command is None:
        return None
    timestamp = command.completed_at or command.sent_at or command.created_at
    return DeviceHealthCommandRead(
        id=command.id,
        target=command.target,
        action=command.action,
        status=command.status,
        message=command.message,
        created_at=command.created_at,
        completed_at=command.completed_at,
        sent_at=command.sent_at,
        timestamp=timestamp,
    )


def _latest_snapshot_timestamp(timestamps: list[datetime | None]) -> datetime | None:
    present = [_as_utc(timestamp) for timestamp in timestamps if timestamp is not None]
    return max(present) if present else None


def _friendly_status(heartbeat_status: str | None, attention_reasons: list[str]) -> str:
    if heartbeat_status == "offline":
        return "offline"
    if attention_reasons:
        return "needs_attention"
    if heartbeat_status == "stale":
        return "recently_seen"
    if heartbeat_status == "online":
        return "online"
    return "offline"


def _attention_reasons(
    *,
    primary: dict | None,
    camera_summaries: list[dict],
    snapshots: list,
    heartbeat_status: str | None,
    reading_status: str | None,
    image_status: str | None,
    camera_status: str | None,
    command_health: CommandHealthSnapshot,
) -> list[str]:
    if heartbeat_status == "offline":
        return []
    reasons: list[str] = []
    if primary and _node_health_status(primary) == "warning":
        reasons.append("primary_node_warning")
    if any(_node_health_status(item) == "warning" for item in camera_summaries):
        reasons.append("camera_node_warning")
    if reading_status == "warning":
        reasons.append("sensor_reading_missing_or_stale")
    if image_status == "warning" or camera_status == "warning":
        reasons.append("camera_image_missing_or_stale")
    if getattr(command_health.last_failed, "completed_at", None) is not None:
        reasons.append("recent_command_failed")
    for snapshot in snapshots:
        if snapshot.wifi_rssi_dbm is not None and snapshot.wifi_rssi_dbm <= -75:
            reasons.append("weak_wifi_signal")
        if snapshot.last_error_code:
            reasons.append("diagnostic_error")
        for key, count in (snapshot.error_counters or {}).items():
            if count:
                reasons.append(f"{key}_reported")
        if getattr(snapshot, "reported_status", None) in {"error", "degraded"}:
            reasons.append("diagnostic_status_warning")
    return list(dict.fromkeys(reasons))


def _camera_status(camera_summaries: list[dict]) -> str | None:
    if not camera_summaries:
        return None
    statuses = [_node_health_status(item) for item in camera_summaries]
    if any(status == "offline" for status in statuses):
        return "offline"
    if any(status == "stale" for status in statuses):
        return "stale"
    if any(status == "warning" for status in statuses):
        return "warning"
    return "online"


def _image_status(camera_summaries: list[dict], timestamp: datetime | None) -> str | None:
    if not camera_summaries and timestamp is None:
        return None
    if camera_summaries and _camera_status(camera_summaries) in {"offline", "stale", "warning"} and timestamp is None:
        return "warning"
    return _signal_status(
        timestamp=timestamp,
        stale_after=IMAGE_STALE_AFTER,
        offline_after=IMAGE_OFFLINE_AFTER,
        missing_status="warning" if camera_summaries else None,
    )


def _node_health_status(node_summary_item: dict | None) -> str:
    if not node_summary_item:
        return "offline"
    status = str(node_summary_item.get("status") or "").strip().lower()
    if status == "offline":
        return "offline"
    if status in {"provisioning", "error", "degraded"}:
        return "warning"
    return _freshness_status(
        _parse_timestamp(node_summary_item.get("last_seen_at")),
        stale_after=HEARTBEAT_STALE_AFTER,
        offline_after=HEARTBEAT_OFFLINE_AFTER,
    )


def _reading_status(timestamp: datetime | None, primary_status: str | None, last_heartbeat_at: datetime | None) -> str | None:
    if timestamp is None:
        if last_heartbeat_at is None:
            return None
        if str(primary_status or "").lower() == "online":
            return "warning"
        return _freshness_status(last_heartbeat_at, stale_after=HEARTBEAT_STALE_AFTER, offline_after=HEARTBEAT_OFFLINE_AFTER)
    return _freshness_status(timestamp, stale_after=READING_STALE_AFTER, offline_after=READING_OFFLINE_AFTER)


def _signal_status(
    *,
    timestamp: datetime | None,
    stale_after: timedelta,
    offline_after: timedelta,
    missing_status: str | None,
) -> str | None:
    if timestamp is None:
        return missing_status
    return _freshness_status(timestamp, stale_after=stale_after, offline_after=offline_after)


def _freshness_status(timestamp: datetime | None, *, stale_after: timedelta, offline_after: timedelta) -> str | None:
    if timestamp is None:
        return None
    age = datetime.now(timezone.utc) - _as_utc(timestamp)
    if age > offline_after:
        return "offline"
    if age > stale_after:
        return "stale"
    return "online"


def _parse_timestamp(value) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return _as_utc(value)
    if isinstance(value, str):
        normalized = value.replace("Z", "+00:00")
        return _as_utc(datetime.fromisoformat(normalized))
    return None


def _as_utc(timestamp: datetime) -> datetime:
    if timestamp.tzinfo is None:
        return timestamp.replace(tzinfo=timezone.utc)
    return timestamp.astimezone(timezone.utc)


def _build_setup_finishing_url(*, frontend_origin: str, device_name: str, location: str, expect_image: bool) -> str:
    from urllib.parse import urlencode

    query = urlencode(
        {
            "device_name": device_name,
            "location": location,
            "expect_image": "1" if expect_image else "0",
        }
    )
    return f"{frontend_origin}/devices/setup-finishing?{query}"


def _build_continue_setup_url(*, settings, setup_token: str | None, serial_number: str, device_name: str, location: str, setup_finishing_url: str) -> str:
    from urllib.parse import urlencode, urlparse, urlunparse

    parsed = urlparse(settings.local_setup_url)
    query_params = {
        "sn": serial_number,
        "serial_number": serial_number,
        "device_name": device_name,
        "backend_url": settings.effective_provisioning_public_url,
        "return_url": setup_finishing_url,
    }
    if setup_token:
        query_params["setup_code"] = setup_token
    if location:
        query_params["location"] = location
    if settings.device_platform_url:
        query_params["platform_url"] = settings.device_platform_url
    return urlunparse(parsed._replace(query=urlencode(query_params)))
