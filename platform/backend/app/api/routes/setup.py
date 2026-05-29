import httpx
from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.errors import api_error
from app.api.deps import get_current_user
from app.contracts import DiagnosticSeverity, EventType
from app.core.settings import get_settings
from app.db.session import get_session
from app.models import User
from app.schemas.setup import ClaimTokenStatusRead, ClaimTokenStatusRequest, SetupStatusRead
from app.services.device_nodes import latest_node_heartbeat_at, list_nodes_for_device
from app.services.devices import list_devices_for_user
from app.services.images import list_recent_images_for_device
from app.services.lifecycle_events import write_canonical_event_once
from app.services.readings import get_latest_reading_for_device


router = APIRouter(prefix="/api/setup", tags=["setup"])


@router.get("/status", response_model=SetupStatusRead)
def get_setup_status(
    device_name: str = Query(default=""),
    location: str = Query(default=""),
    expected_device_id: str = Query(default=""),
    expect_image: bool = Query(default=True),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    pending_device_name = device_name.strip()
    pending_location = location.strip()
    pending_expected_device_id = expected_device_id.strip()
    if not pending_device_name and not pending_expected_device_id:
        return _no_store_json(SetupStatusRead(ready=False).model_dump(mode="json"))

    devices = list_devices_for_user(session, current_user)
    matching_device = None
    matching_nodes = []
    if pending_expected_device_id:
        for device in devices:
            nodes = list_nodes_for_device(session, device.id)
            if any(
                node.hardware_device_id == pending_expected_device_id
                and str(getattr(node, "node_role", "") or "").strip().lower() in {"single_board", "master"}
                for node in nodes
            ):
                matching_device = device
                matching_nodes = nodes
                break
        if matching_device is None:
            return _no_store_json(
                SetupStatusRead(
                    ready=False,
                    device_found=False,
                    has_reading=False,
                    has_image=False,
                    expect_image=expect_image,
                    online=False,
                ).model_dump(mode="json")
            )

    if matching_device is None and pending_device_name:
        matching_device = next(
            (
                device
                for device in devices
                if device.name == pending_device_name and (device.location or "") == pending_location
            ),
            None,
        )

    if matching_device is None:
        return _no_store_json(
            SetupStatusRead(
                ready=False,
                device_found=False,
                has_reading=False,
                has_image=False,
                expect_image=expect_image,
                online=False,
            ).model_dump(mode="json")
        )

    latest_reading = get_latest_reading_for_device(session, matching_device.id)
    latest_images = list_recent_images_for_device(session, matching_device.id, limit=1)
    nodes = matching_nodes or list_nodes_for_device(session, matching_device.id)
    final_expect_image = _setup_finishing_expect_image(nodes, expect_image)
    has_reading = latest_reading is not None
    has_image = bool(latest_images)
    ready = has_reading and (has_image or not final_expect_image)
    status = _primary_node_status(nodes)
    online = status == "online"
    last_heartbeat_at = latest_node_heartbeat_at(nodes)
    if ready:
        _write_provisioning_event(session, matching_device.id, nodes, EventType.PROVISIONING_SUCCESS)
    elif status == "error":
        _write_provisioning_event(session, matching_device.id, nodes, EventType.PROVISIONING_FAILED)
    else:
        _write_provisioning_event(session, matching_device.id, nodes, EventType.PROVISIONING_STARTED)

    return _no_store_json(
        SetupStatusRead(
            ready=ready,
            device_found=True,
            device_id=matching_device.id,
            has_reading=has_reading,
            has_image=has_image,
            expect_image=final_expect_image,
            online=online,
            last_heartbeat_at=last_heartbeat_at,
            status=status,
            redirect_path=f"/devices/{matching_device.id}?setup=complete" if ready else None,
        ).model_dump(mode="json")
    )


@router.post("/claim-token/status", response_model=ClaimTokenStatusRead)
async def get_claim_token_status(
    payload: ClaimTokenStatusRequest,
    current_user: User = Depends(get_current_user),
):
    settings = get_settings()
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                f"{settings.provisioning_api_url}/api/devices/claim-token/status",
                json={"claim_token": payload.setup_token},
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
            "claim_token_status_failed",
            upstream_payload.get("message") or upstream_payload.get("error") or "Could not check setup token status.",
        )

    return ClaimTokenStatusRead(
        used=bool(upstream_payload.get("used")),
        used_by_device_id=upstream_payload.get("used_by_device_id"),
        expected_device_id=upstream_payload.get("expected_device_id"),
        expires_at=upstream_payload.get("expires_at"),
        expired=bool(upstream_payload.get("expired")),
        failure_code=upstream_payload.get("failure_code"),
        failure_message=upstream_payload.get("failure_message"),
        failed_at=upstream_payload.get("failed_at"),
    )


def _setup_finishing_expect_image(nodes: list, requested_expect_image: bool) -> bool:
    roles = {
        str(getattr(node, "node_role", "") or "").strip().lower()
        for node in nodes
        if getattr(node, "node_role", None) is not None
    }
    if any(_node_has_camera_capability(node) for node in nodes):
        return True
    if "master" in roles:
        return False
    if "single_board" in roles:
        return True
    return requested_expect_image


def _node_has_camera_capability(node) -> bool:
    role = str(getattr(node, "node_role", "") or "").strip().lower()
    if role == "camera":
        return True
    capabilities = getattr(node, "capabilities", None) or {}
    return bool(capabilities.get("camera"))


def _primary_node_status(nodes: list) -> str | None:
    primary = next(
        (
            node
            for node in nodes
            if str(getattr(node, "node_role", "") or "").strip().lower() in {"single_board", "master"}
        ),
        None,
    )
    if primary is None:
        return None
    status = str(getattr(primary, "status", "") or "").strip().lower()
    return status or None


def _write_provisioning_event(session: Session, device_id: int, nodes: list, event_type: EventType) -> None:
    primary = next(
        (
            node
            for node in nodes
            if str(getattr(node, "node_role", "") or "").strip().lower() in {"single_board", "master"}
        ),
        None,
    )
    if primary is None:
        return
    status = str(getattr(primary, "status", "") or "").strip().lower() or "unknown"
    severity = DiagnosticSeverity.WARNING if event_type == EventType.PROVISIONING_FAILED else DiagnosticSeverity.INFO
    write_canonical_event_once(
        session,
        event_type=event_type,
        severity=severity,
        device_id=device_id,
        hardware_device_id=primary.hardware_device_id,
        node_role=getattr(primary, "node_role", None) or "master",
        correlation_id=f"provisioning:{device_id}:{primary.hardware_device_id}",
        data={
            "status": status,
            "hardware_device_id": primary.hardware_device_id,
            "node_role": getattr(primary, "node_role", None),
        },
    )


def _no_store_json(payload: dict) -> JSONResponse:
    return JSONResponse(
        payload,
        headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"},
    )
