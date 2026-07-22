import json
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_device_from_token, get_optional_current_user
from app.api.errors import api_error
from app.contracts import (
    CameraRole,
    DiagnosticSeverity,
    EventType,
    ImageUploadPayload,
    ImageUploadStatus,
    ProtocolValidationError,
    is_device_message_envelope,
    parse_image_upload_message,
)
from app.core.settings import get_settings
from app.db.session import get_session
from app.models import Device, Image, User
from app.models.device_node import DeviceNode
from app.schemas.images import ImageRead
from app.services.device_nodes import get_node_for_device
from app.services.devices import get_device_for_user
from app.services.images import save_uploaded_image
from app.services.lifecycle_events import write_canonical_event_once
from app.services.storage import image_response


router = APIRouter(prefix="/api", tags=["images"])


@router.post("/image", response_model=ImageRead, status_code=201)
def upload_image(
    request: Request,
    device_id: int = Form(...),
    source_hardware_device_id: str | None = Form(default=None),
    camera_node_id: str | None = Form(default=None),
    camera_role: CameraRole | None = Form(default=None),
    metadata: str | None = Form(default=None),
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
    current_user: User | None = Depends(get_optional_current_user),
):
    if current_user is not None:
        device = get_device_for_user(session, current_user, device_id)
        if device is None:
            raise HTTPException(status_code=404, detail="Device not found.")
    else:
        device = get_device_from_token(request, session)
        if device is None:
            raise HTTPException(status_code=401, detail="Sign in or valid device token required.")
        if device.id != device_id:
            raise HTTPException(status_code=403, detail="Device token does not match device_id.")

    source_hardware_device_id = _selected_source_hardware_device_id(source_hardware_device_id, camera_node_id)
    image_message = _parse_optional_image_upload_metadata(metadata)
    if image_message is not None:
        _validate_contract_device_id(image_message.device_id, device.id)
        if image_message.payload.status != ImageUploadStatus.UPLOADED:
            raise api_error(
                422,
                "image_upload_status_mismatch",
                "Multipart image uploads must use image upload status 'uploaded'.",
                details={"status": image_message.payload.status.value},
            )
        source_hardware_device_id = _source_hardware_device_id(image_message.payload, image_message.hardware_device_id)
        camera_role = image_message.payload.camera_role or camera_role
        if image_message.payload.content_type and file.content_type and image_message.payload.content_type != file.content_type:
            raise api_error(
                422,
                "image_content_type_mismatch",
                "Image upload metadata content_type does not match the uploaded file.",
                details={"metadata": image_message.payload.content_type, "file": file.content_type},
            )

    source_node = _validate_source_node(
        session,
        device_id=device.id,
        source_hardware_device_id=source_hardware_device_id,
    )
    camera_role = _validated_camera_role(source_node, camera_role)
    if image_message is not None and source_node is not None and source_node.node_role != image_message.node_role.value:
        raise HTTPException(status_code=409, detail="Image source node role does not match registration.")

    image_correlation_id = (
        image_message.message_id
        if image_message is not None
        else f"image_upload:{source_hardware_device_id}:{datetime.now(timezone.utc).isoformat()}"
    )
    if source_node is not None:
        _write_image_flow_event(
            session,
            device_id=device.id,
            source_node=source_node,
            event_type=EventType.IMAGE_UPLOAD_STARTED,
            payload=image_message.payload if image_message is not None else None,
            correlation_id=image_correlation_id,
            image=None,
            fallback_content_type=file.content_type,
        )

    try:
        image = save_uploaded_image(
            session=session,
            upload_file=file,
            device_id=device.id,
            source_hardware_device_id=source_hardware_device_id,
            camera_role=camera_role,
            settings=get_settings(),
            captured_at=image_message.payload.captured_at if image_message is not None else None,
        )
    except ValueError as exc:
        if source_node is not None:
            _write_image_flow_event(
                session,
                device_id=device.id,
                source_node=source_node,
                event_type=EventType.IMAGE_UPLOAD_FAILED,
                payload=image_message.payload if image_message is not None else None,
                correlation_id=image_correlation_id,
                image=None,
                fallback_content_type=file.content_type,
                extra_data={"failure_reason": str(exc)},
            )
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if source_node is not None:
        _write_image_flow_event(
            session,
            device_id=device.id,
            source_node=source_node,
            event_type=EventType.IMAGE_CAPTURED,
            payload=image_message.payload if image_message is not None else None,
            correlation_id=image_correlation_id,
            image=image,
            fallback_content_type=file.content_type,
        )
        _write_image_flow_event(
            session,
            device_id=device.id,
            source_node=source_node,
            event_type=EventType.IMAGE_UPLOADED,
            payload=image_message.payload if image_message is not None else None,
            correlation_id=image_correlation_id,
            image=image,
            fallback_content_type=file.content_type,
        )
    return image


@router.post("/hardware/image-upload/report")
def report_image_upload(
    request: Request,
    raw_payload: dict[str, Any],
    session: Session = Depends(get_session),
):
    device = get_device_from_token(request, session)
    if device is None:
        raise HTTPException(status_code=401, detail="Valid device token required.")
    if not is_device_message_envelope(raw_payload):
        raise api_error(
            422,
            "contract_envelope_required",
            "Image upload reports must use the PlantLab device message envelope.",
        )
    try:
        message = parse_image_upload_message(raw_payload)
    except ProtocolValidationError as exc:
        _raise_protocol_error(exc)
    _validate_contract_device_id(message.device_id, device.id)
    source_node = _validate_source_node(
        session,
        device_id=device.id,
        source_hardware_device_id=_source_hardware_device_id(message.payload, message.hardware_device_id),
    )
    if source_node is None:
        raise HTTPException(status_code=403, detail="Image source node is not attached to this device.")
    if source_node.node_role != message.node_role.value:
        raise HTTPException(status_code=409, detail="Image source node role does not match registration.")
    event_type = EventType.IMAGE_UPLOAD_FAILED if message.payload.status == ImageUploadStatus.FAILED else EventType.IMAGE_UPLOADED
    image = session.get(Image, message.payload.image_id) if message.payload.image_id is not None else None
    if image is not None and image.device_id != device.id:
        raise HTTPException(status_code=404, detail="Image not found.")
    _write_image_flow_event(
        session,
        device_id=device.id,
        source_node=source_node,
        event_type=event_type,
        payload=message.payload,
        correlation_id=message.message_id,
        image=image,
        fallback_content_type=message.payload.content_type,
    )
    return {"status": "accepted", "event_type": event_type.value}


@router.get("/images/{image_id}/content")
def image_content(
    image_id: int,
    session: Session = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    image = session.scalars(
        select(Image)
        .join(Device)
        .where(Image.id == image_id)
        .where(Device.user_id == current_user.id)
    ).first()
    if image is None:
        raise HTTPException(status_code=404, detail="Image not found.")

    image_path = image.path
    # Release the DB connection before reading image bytes from storage. The
    # proxy endpoint can receive many concurrent browser image requests, and
    # holding a pooled DB connection during GCS reads can starve auth lookups.
    session.close()

    try:
        return image_response(image_path, get_settings())
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=404, detail="Image content not found.") from exc


def _parse_optional_image_upload_metadata(metadata: str | None):
    if not metadata:
        return None
    try:
        raw = json.loads(metadata)
    except json.JSONDecodeError as exc:
        raise api_error(
            422,
            "invalid_image_upload_metadata",
            "Image upload metadata must be valid JSON.",
            details={"error": str(exc)},
        ) from exc
    if not is_device_message_envelope(raw):
        raise api_error(
            422,
            "contract_envelope_required",
            "Image upload metadata must use the PlantLab device message envelope.",
        )
    try:
        return parse_image_upload_message(raw)
    except ProtocolValidationError as exc:
        _raise_protocol_error(exc)


def _validate_source_node(
    session: Session,
    *,
    device_id: int,
    source_hardware_device_id: str | None,
) -> DeviceNode | None:
    if not source_hardware_device_id:
        return None
    source_node = get_node_for_device(
        session,
        device_id=device_id,
        hardware_device_id=source_hardware_device_id,
    )
    if source_node is None:
        raise HTTPException(status_code=403, detail="Image source node is not attached to this device.")
    return source_node


def _selected_source_hardware_device_id(
    source_hardware_device_id: str | None,
    camera_node_id: str | None,
) -> str | None:
    if source_hardware_device_id and camera_node_id and source_hardware_device_id != camera_node_id:
        raise api_error(
            409,
            "image_source_mismatch",
            "source_hardware_device_id and camera_node_id must identify the same camera node.",
            details={"source_hardware_device_id": source_hardware_device_id, "camera_node_id": camera_node_id},
        )
    return source_hardware_device_id or camera_node_id


def _source_hardware_device_id(payload: ImageUploadPayload, envelope_hardware_device_id: str) -> str:
    if payload.source_hardware_device_id and payload.source_hardware_device_id != envelope_hardware_device_id:
        raise api_error(
            409,
            "image_source_mismatch",
            "Image upload source_hardware_device_id does not match the envelope hardware_device_id.",
            details={"payload": payload.source_hardware_device_id, "envelope": envelope_hardware_device_id},
        )
    if payload.camera_node_id and payload.camera_node_id not in {payload.source_hardware_device_id, envelope_hardware_device_id}:
        raise api_error(
            409,
            "image_source_mismatch",
            "Image upload camera_node_id does not match the envelope hardware_device_id.",
            details={"camera_node_id": payload.camera_node_id, "envelope": envelope_hardware_device_id},
        )
    return payload.source_hardware_device_id or payload.camera_node_id or envelope_hardware_device_id


def _validated_camera_role(source_node: DeviceNode | None, camera_role: CameraRole | None) -> str | None:
    if source_node is None:
        if camera_role is not None:
            raise api_error(
                422,
                "camera_role_requires_source_node",
                "camera_role requires a source camera node.",
            )
        return None
    if source_node.node_role != "camera":
        return None
    if camera_role is not None:
        if source_node.camera_role is not None and source_node.camera_role != camera_role.value:
            raise HTTPException(status_code=409, detail="Image camera role does not match source node registration.")
        return camera_role.value
    return source_node.camera_role


def _write_image_flow_event(
    session: Session,
    *,
    device_id: int,
    source_node: DeviceNode,
    event_type: EventType,
    payload: ImageUploadPayload | None,
    correlation_id: str,
    image: Image | None,
    fallback_content_type: str | None,
    extra_data: dict[str, Any] | None = None,
) -> None:
    data = payload.model_dump(mode="json", exclude_none=True) if payload is not None else {}
    if image is not None:
        data["image_id"] = image.id
        data["path"] = image.path
        data["captured_at"] = image.timestamp.isoformat()
    data["hardware_device_id"] = source_node.hardware_device_id
    data["source_hardware_device_id"] = source_node.hardware_device_id
    data["source_node_role"] = source_node.node_role
    if source_node.camera_role:
        data["camera_node_id"] = source_node.hardware_device_id
        data["camera_role"] = source_node.camera_role
    if fallback_content_type and "content_type" not in data:
        data["content_type"] = fallback_content_type
    if extra_data:
        data.update(extra_data)
    write_canonical_event_once(
        session,
        event_type=event_type,
        severity=DiagnosticSeverity.WARNING if event_type == EventType.IMAGE_UPLOAD_FAILED else DiagnosticSeverity.INFO,
        device_id=device_id,
        hardware_device_id=source_node.hardware_device_id,
        node_role=source_node.node_role,
        correlation_id=correlation_id,
        data=data,
        occurred_at=datetime.now(timezone.utc),
    )


def _validate_contract_device_id(contract_device_id: int | None, token_device_id: int) -> None:
    if contract_device_id is not None and contract_device_id != token_device_id:
        raise api_error(
            409,
            "device_id_mismatch",
            "Device message device_id does not match the authenticated device.",
            details={"device_id": contract_device_id},
        )


def _raise_protocol_error(exc: ProtocolValidationError) -> None:
    raise api_error(
        422,
        exc.code,
        exc.message,
        details=exc.details,
    )
