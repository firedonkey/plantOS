from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_session
from app.models import User
from app.schemas.setup import SetupStatusRead
from app.services.device_nodes import list_nodes_for_device
from app.services.devices import list_devices_for_user
from app.services.images import list_recent_images_for_device
from app.services.readings import get_latest_reading_for_device


router = APIRouter(prefix="/api/setup", tags=["setup"])


@router.get("/status", response_model=SetupStatusRead)
def get_setup_status(
    device_name: str = Query(default=""),
    location: str = Query(default=""),
    expect_image: bool = Query(default=True),
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    pending_device_name = device_name.strip()
    pending_location = location.strip()
    if not pending_device_name:
        return _no_store_json(SetupStatusRead(ready=False).model_dump())

    devices = list_devices_for_user(session, current_user)
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
            ).model_dump()
        )

    latest_reading = get_latest_reading_for_device(session, matching_device.id)
    latest_images = list_recent_images_for_device(session, matching_device.id, limit=1)
    nodes = list_nodes_for_device(session, matching_device.id)
    final_expect_image = _setup_finishing_expect_image(nodes, expect_image)
    has_reading = latest_reading is not None
    has_image = bool(latest_images)
    ready = has_reading and (has_image or not final_expect_image)

    return _no_store_json(
        SetupStatusRead(
            ready=ready,
            device_found=True,
            device_id=matching_device.id,
            has_reading=has_reading,
            has_image=has_image,
            expect_image=final_expect_image,
            redirect_path=f"/devices/{matching_device.id}?setup=complete" if ready else None,
        ).model_dump()
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


def _no_store_json(payload: dict) -> JSONResponse:
    return JSONResponse(
        payload,
        headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"},
    )
