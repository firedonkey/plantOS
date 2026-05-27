from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.api.deps import get_device_from_token
from app.api.errors import api_error
from app.contracts import ProtocolValidationError, is_device_message_envelope, parse_ota_status_message
from app.core.settings import get_settings
from app.db.session import get_session
from app.schemas.firmware import FirmwareManifestRead, FirmwareOtaStatusCreate, FirmwareOtaStatusRead
from app.services.device_nodes import get_node_by_hardware_id
from app.services.firmware import (
    build_manifest_for_node,
    firmware_artifact_response,
    get_published_release,
    update_ota_status,
)


router = APIRouter(prefix="/api/hardware/ota", tags=["firmware"])


def _require_device(request: Request, session: Session):
    device = get_device_from_token(request, session)
    if device is None:
        raise HTTPException(status_code=401, detail="Valid device token required.")
    return device


def _require_node(session: Session, device_id: int, hardware_device_id: str):
    node = get_node_by_hardware_id(session, hardware_device_id)
    if node is None or node.device_id != device_id:
        raise HTTPException(status_code=404, detail="Device node not found.")
    return node


@router.get("/manifest", response_model=FirmwareManifestRead)
def ota_manifest(
    request: Request,
    hardware_device_id: str = Query(min_length=3, max_length=120),
    node_role: str = Query(min_length=3, max_length=40),
    current_version: str | None = Query(default=None, max_length=120),
    session: Session = Depends(get_session),
):
    device = _require_device(request, session)
    node = _require_node(session, device.id, hardware_device_id)
    if node.node_role != node_role:
        raise HTTPException(status_code=409, detail="Device node role does not match registration.")
    return build_manifest_for_node(
        session,
        node=node,
        node_role=node_role,
        current_version=current_version,
    )


@router.post("/status", response_model=FirmwareOtaStatusRead)
def ota_status(
    request: Request,
    raw_payload: dict[str, Any] = Body(...),
    session: Session = Depends(get_session),
):
    device = _require_device(request, session)
    payload, correlation_id, contract_data, contract_node_role = _normalize_ota_status_payload(raw_payload, device_id=device.id)
    node = _require_node(session, device.id, payload.hardware_device_id)
    if contract_node_role is not None and node.node_role != contract_node_role:
        raise HTTPException(status_code=409, detail="Device node role does not match registration.")
    return update_ota_status(
        session,
        node=node,
        payload=payload,
        correlation_id=correlation_id,
        contract_data=contract_data,
    )


@router.get("/artifacts/{release_id}")
def ota_artifact(
    release_id: str,
    request: Request,
    session: Session = Depends(get_session),
):
    _require_device(request, session)
    release = get_published_release(session, release_id)
    if release is None:
        raise HTTPException(status_code=404, detail="Firmware release not found.")
    try:
        return firmware_artifact_response(release, get_settings())
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=404, detail="Firmware artifact not found.") from exc


def _normalize_ota_status_payload(
    raw_payload: dict[str, Any],
    *,
    device_id: int,
) -> tuple[FirmwareOtaStatusCreate, str | None, dict[str, Any], str | None]:
    if is_device_message_envelope(raw_payload):
        try:
            message = parse_ota_status_message(raw_payload)
        except ProtocolValidationError as exc:
            _raise_protocol_error(exc)
        _validate_contract_device_id(message.device_id, device_id)
        status_payload = message.payload
        contract_data = status_payload.model_dump(mode="json", exclude_none=True)
        error = None
        if status_payload.status.value in {"failed", "rolled_back"}:
            error = status_payload.message or (
                status_payload.failure_reason.value if status_payload.failure_reason is not None else None
            )
        installed_version = (
            status_payload.current_version
            if status_payload.status.value in {"success", "rolled_back"}
            else None
        )
        return (
            FirmwareOtaStatusCreate(
                hardware_device_id=message.hardware_device_id,
                status=status_payload.status.value,
                release_id=status_payload.release_id,
                target_version=status_payload.target_version,
                installed_version=installed_version,
                progress=status_payload.progress_percent,
                error=error,
            ),
            message.message_id,
            contract_data,
            message.node_role.value,
        )

    try:
        payload = FirmwareOtaStatusCreate.model_validate(raw_payload)
    except ValidationError as exc:
        raise api_error(
            422,
            "validation_error",
            "Request validation failed.",
            details=_validation_error_details(exc),
        ) from exc
    return payload, None, {"source": "legacy"}, None


def _validate_contract_device_id(contract_device_id: int | None, token_device_id: int) -> None:
    if contract_device_id is not None and contract_device_id != token_device_id:
        raise api_error(
            409,
            "device_id_mismatch",
            "Device message device_id does not match the device token.",
            details={"device_id": contract_device_id},
        )


def _raise_protocol_error(exc: ProtocolValidationError) -> None:
    raise api_error(
        422,
        exc.code,
        exc.message,
        details=exc.details,
    )


def _validation_error_details(error: ValidationError) -> dict[str, Any]:
    errors = []
    for item in error.errors():
        errors.append(
            {
                "loc": list(item.get("loc") or []),
                "msg": str(item.get("msg") or ""),
                "type": str(item.get("type") or ""),
            }
        )
    return {"errors": errors}
