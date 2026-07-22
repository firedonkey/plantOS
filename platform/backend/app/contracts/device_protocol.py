from __future__ import annotations

import logging
from datetime import datetime
from enum import Enum
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator


logger = logging.getLogger(__name__)

PLANTLAB_SCHEMA_VERSION = "1.0"
SUPPORTED_SCHEMA_MAJOR = 1


class NodeRole(str, Enum):
    MASTER = "master"
    CAMERA = "camera"
    SENSOR = "sensor"
    ACTUATOR = "actuator"


class CameraRole(str, Enum):
    TOP = "top"
    SIDE = "side"


class MessageType(str, Enum):
    HEARTBEAT = "HEARTBEAT"
    DIAGNOSTICS = "DIAGNOSTICS"
    COMMAND = "COMMAND"
    COMMAND_RESULT = "COMMAND_RESULT"
    OTA_STATUS = "OTA_STATUS"
    IMAGE_UPLOAD = "IMAGE_UPLOAD"


class DeviceStatus(str, Enum):
    ONLINE = "online"
    DEGRADED = "degraded"
    OFFLINE = "offline"
    PROVISIONING = "provisioning"
    UPDATING = "updating"
    ERROR = "error"


class DiagnosticSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class EventType(str, Enum):
    DEVICE_ONLINE = "DEVICE_ONLINE"
    DEVICE_OFFLINE = "DEVICE_OFFLINE"
    HEARTBEAT_RECEIVED = "HEARTBEAT_RECEIVED"
    DIAGNOSTICS_RECEIVED = "DIAGNOSTICS_RECEIVED"
    SENSOR_ERROR = "SENSOR_ERROR"
    ACTUATOR_STATE_CHANGED = "ACTUATOR_STATE_CHANGED"
    CAMERA_NODE_CONNECTED = "CAMERA_NODE_CONNECTED"
    CAMERA_NODE_DISCONNECTED = "CAMERA_NODE_DISCONNECTED"
    OTA_STATE_CHANGED = "OTA_STATE_CHANGED"
    DEVICE_HEALTH_CHANGED = "DEVICE_HEALTH_CHANGED"
    WIFI_SIGNAL_DEGRADED = "WIFI_SIGNAL_DEGRADED"
    WIFI_SIGNAL_RECOVERED = "WIFI_SIGNAL_RECOVERED"
    OTA_AVAILABLE = "OTA_AVAILABLE"
    OTA_STARTED = "OTA_STARTED"
    OTA_PROGRESS = "OTA_PROGRESS"
    OTA_PREPARING = "OTA_PREPARING"
    OTA_DOWNLOADING = "OTA_DOWNLOADING"
    OTA_VALIDATING = "OTA_VALIDATING"
    OTA_INSTALLING = "OTA_INSTALLING"
    OTA_REBOOTING = "OTA_REBOOTING"
    OTA_SUCCESS = "OTA_SUCCESS"
    OTA_FAILED = "OTA_FAILED"
    OTA_ROLLED_BACK = "OTA_ROLLED_BACK"
    COMMAND_QUEUED = "COMMAND_QUEUED"
    COMMAND_SENT = "COMMAND_SENT"
    COMMAND_POLLED = "COMMAND_POLLED"
    COMMAND_POLL_STALE = "COMMAND_POLL_STALE"
    COMMAND_ACKED = "COMMAND_ACKED"
    COMMAND_IN_PROGRESS = "COMMAND_IN_PROGRESS"
    COMMAND_COMPLETED = "COMMAND_COMPLETED"
    COMMAND_FAILED = "COMMAND_FAILED"
    COMMAND_TIMED_OUT = "COMMAND_TIMED_OUT"
    COMMAND_REJECTED = "COMMAND_REJECTED"
    PROVISIONING_STARTED = "PROVISIONING_STARTED"
    PROVISIONING_SUCCESS = "PROVISIONING_SUCCESS"
    PROVISIONING_FAILED = "PROVISIONING_FAILED"
    FACTORY_RESET = "FACTORY_RESET"
    IMAGE_CAPTURE_STARTED = "IMAGE_CAPTURE_STARTED"
    IMAGE_CAPTURED = "IMAGE_CAPTURED"
    IMAGE_UPLOAD_STARTED = "IMAGE_UPLOAD_STARTED"
    IMAGE_UPLOADED = "IMAGE_UPLOADED"
    IMAGE_UPLOAD_FAILED = "IMAGE_UPLOAD_FAILED"


class CommandType(str, Enum):
    SET_GROW_LIGHT_BRIGHTNESS = "SET_GROW_LIGHT_BRIGHTNESS"
    SET_LIGHT_BRIGHTNESS = "SET_LIGHT_BRIGHTNESS"
    SET_AMBIENT_LED_BELT = "SET_AMBIENT_LED_BELT"
    CAPTURE_IMAGE = "CAPTURE_IMAGE"
    REBOOT = "REBOOT"
    START_OTA = "START_OTA"
    ENTER_PAIRING_MODE = "ENTER_PAIRING_MODE"
    FACTORY_RESET = "FACTORY_RESET"
    REQUEST_DIAGNOSTICS = "REQUEST_DIAGNOSTICS"
    UPDATE_CAPTURE_INTERVAL = "UPDATE_CAPTURE_INTERVAL"


class CommandProtocolStatus(str, Enum):
    QUEUED = "queued"
    SENT = "sent"
    ACKED = "acked"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    REJECTED = "rejected"


class CommandTargetRole(str, Enum):
    MASTER = "master"
    CAMERA = "camera"
    SENSOR = "sensor"
    ACTUATOR = "actuator"


class CommandPriority(str, Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


class CommandErrorCode(str, Enum):
    UNKNOWN_COMMAND = "UNKNOWN_COMMAND"
    INVALID_PARAMS = "INVALID_PARAMS"
    UNSUPPORTED_TARGET = "UNSUPPORTED_TARGET"
    DEVICE_BUSY = "DEVICE_BUSY"
    TIMEOUT = "TIMEOUT"
    TRANSPORT_ERROR = "TRANSPORT_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class OTAStatus(str, Enum):
    IDLE = "idle"
    AVAILABLE = "available"
    PREPARING = "preparing"
    DOWNLOADING = "downloading"
    VALIDATING = "validating"
    INSTALLING = "installing"
    REBOOTING = "rebooting"
    SUCCESS = "success"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class OTAFailureReason(str, Enum):
    CHECKSUM_MISMATCH = "checksum_mismatch"
    UNSUPPORTED_HARDWARE = "unsupported_hardware"
    UNSUPPORTED_FIRMWARE_VERSION = "unsupported_firmware_version"
    UNSUPPORTED_SCHEMA_VERSION = "unsupported_schema_version"
    DOWNLOAD_FAILED = "download_failed"
    VALIDATION_FAILED = "validation_failed"
    INSTALL_FAILED = "install_failed"
    REBOOT_FAILED = "reboot_failed"
    ROLLBACK_FAILED = "rollback_failed"
    NETWORK_ERROR = "network_error"
    TIMEOUT = "timeout"
    INTERNAL_ERROR = "internal_error"


class OTAChannel(str, Enum):
    STABLE = "stable"
    ALPHA = "alpha"
    BETA = "beta"
    DEV = "dev"
    LOCAL = "local"


class OTAInstallPhase(str, Enum):
    CHECK = "check"
    PREPARE = "prepare"
    DOWNLOAD = "download"
    VALIDATE = "validate"
    INSTALL = "install"
    REBOOT = "reboot"
    COMPLETED = "completed"
    ROLLBACK = "rollback"


class ImageUploadStatus(str, Enum):
    UPLOADED = "uploaded"
    FAILED = "failed"


class ProtocolValidationError(ValueError):
    def __init__(self, code: str, message: str, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or {}


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="allow")


class HeartbeatGrowLightState(ContractModel):
    enabled: bool | None = None
    brightness_percent: int | None = Field(default=None, ge=0, le=100)


class HeartbeatActuatorState(ContractModel):
    grow_light: HeartbeatGrowLightState | None = None
    ambient_light: HeartbeatGrowLightState | None = None


class HeartbeatAmbientLedBeltColor(ContractModel):
    r: int | None = Field(default=None, ge=0, le=255)
    g: int | None = Field(default=None, ge=0, le=255)
    b: int | None = Field(default=None, ge=0, le=255)


class HeartbeatAmbientLedBeltState(ContractModel):
    available: bool | None = None
    enabled: bool | None = None
    mode: str | None = Field(default=None, pattern="^(off|solid|breathe|pulse|chase|rainbow|diagnostic)$")
    brightness: int | None = Field(default=None, ge=0, le=255)
    max_brightness: int | None = Field(default=None, ge=0, le=255)
    color: HeartbeatAmbientLedBeltColor | None = None
    logical_pixel_count: int | None = Field(default=None, ge=1, le=120)
    physical_led_count: int | None = Field(default=None, ge=1)
    color_order: str | None = Field(default=None, pattern="^(RGB|RBG|GRB|GBR|BRG|BGR)$")
    data_gpio: int | None = Field(default=None, ge=0, le=48)
    diagnostic_active: bool | None = None
    last_error: str | None = Field(default=None, max_length=160)


class HeartbeatRuntimeState(ContractModel):
    capture_interval_seconds: int | None = Field(default=None, ge=0)
    ota_status: OTAStatus | None = None
    provisioning_status: str | None = Field(default=None, min_length=1, max_length=80)
    camera_node_status: DeviceStatus | None = None
    last_command_id: str | None = Field(default=None, min_length=1, max_length=120)
    last_command_status: str | None = Field(default=None, min_length=1, max_length=80)
    last_command_poll_at: datetime | None = None
    last_command_poll_status: str | None = Field(default=None, min_length=1, max_length=80)
    last_command_poll_error: str | None = Field(default=None, max_length=160)
    last_command_poll_latency_ms: int | None = Field(default=None, ge=0, le=300_000)
    command_poll_stale_seconds: int | None = Field(default=None, ge=0, le=86_400)
    ambient_led_belt: HeartbeatAmbientLedBeltState | None = None
    time_sync_status: str | None = Field(default=None, min_length=1, max_length=80)
    last_ntp_sync_at: datetime | None = None


class HeartbeatPayload(ContractModel):
    uptime_seconds: int = Field(ge=0)
    wifi_rssi_dbm: int | None = Field(default=None, ge=-127, le=0)
    ip_address: str | None = Field(default=None, max_length=64)
    free_heap_bytes: int | None = Field(default=None, ge=0)
    node_status: DeviceStatus
    firmware_version: str = Field(min_length=1, max_length=120)
    hardware_model: str | None = Field(default=None, min_length=1, max_length=120)
    hardware_version: str | None = Field(default=None, min_length=1, max_length=120)
    camera_role: CameraRole | None = None
    capabilities: list[str] | None = Field(default=None, max_length=32)
    actuators: HeartbeatActuatorState | None = None
    runtime: HeartbeatRuntimeState | None = None


class DiagnosticsPayload(ContractModel):
    status: DeviceStatus
    severity: DiagnosticSeverity
    error_counters: dict[str, int] = Field(default_factory=dict, max_length=16)
    last_error_code: str | None = Field(default=None, max_length=80)
    last_error_message: str | None = Field(default=None, max_length=160)
    reboot_reason: str | None = Field(default=None, max_length=80)
    subsystem_statuses: dict[str, DeviceStatus] = Field(default_factory=dict, max_length=16)

    @field_validator("error_counters")
    @classmethod
    def validate_error_counters(cls, value: dict[str, int]) -> dict[str, int]:
        normalized: dict[str, int] = {}
        for key, count in value.items():
            cleaned_key = str(key).strip()
            if not cleaned_key:
                raise ValueError("Diagnostic counter names must not be empty.")
            if not isinstance(count, int) or count < 0:
                raise ValueError("Diagnostic counters must be non-negative integers.")
            normalized[cleaned_key[:80]] = min(count, 2_147_483_647)
        return normalized


class CommandTarget(ContractModel):
    node_role: CommandTargetRole
    hardware_device_id: str | None = Field(default=None, max_length=120)
    camera_role: CameraRole | None = None


class RetryPolicy(ContractModel):
    max_attempts: int = Field(ge=1, le=10)
    backoff_ms: int = Field(ge=0, le=300_000)


class CommandPayload(ContractModel):
    command_id: str = Field(min_length=1, max_length=120)
    command_type: CommandType
    target: CommandTarget
    params: dict[str, Any] = Field(default_factory=dict)
    timeout_ms: int = Field(ge=1, le=3_600_000)
    retry_policy: RetryPolicy | None = None
    priority: CommandPriority = CommandPriority.NORMAL
    scheduled_for: datetime | None = None


class CommandResultPayload(ContractModel):
    command_id: str = Field(min_length=1, max_length=120)
    command_type: CommandType
    status: CommandProtocolStatus
    message: str | None = Field(default=None, max_length=240)
    result: dict[str, Any] = Field(default_factory=dict)
    error_code: CommandErrorCode | None = None
    occurred_at: datetime | None = None


class OTACommandParams(ContractModel):
    target_version: str = Field(min_length=1, max_length=120)
    firmware_channel: OTAChannel = OTAChannel.STABLE
    download_url: str | None = Field(default=None, max_length=500)
    checksum_sha256: str | None = Field(default=None, min_length=1, max_length=128)
    hardware_model: str | None = Field(default=None, max_length=120)
    minimum_current_version: str | None = Field(default=None, max_length=120)
    schema_major: int | None = Field(default=SUPPORTED_SCHEMA_MAJOR, ge=1, le=10)
    rollback_version: str | None = Field(default=None, max_length=120)


class OTAStatusPayload(ContractModel):
    command_id: str = Field(min_length=1, max_length=120)
    status: OTAStatus
    progress_percent: int | None = Field(default=None, ge=0, le=100)
    current_version: str | None = Field(default=None, max_length=120)
    target_version: str | None = Field(default=None, max_length=120)
    firmware_channel: OTAChannel | None = None
    phase: OTAInstallPhase | None = None
    message: str | None = Field(default=None, max_length=240)
    failure_reason: OTAFailureReason | None = None
    release_id: str | None = Field(default=None, max_length=80)


class ImageUploadPayload(ContractModel):
    status: ImageUploadStatus
    image_id: int | None = Field(default=None, ge=1)
    camera_node_id: str | None = Field(default=None, min_length=1, max_length=120)
    camera_role: CameraRole | None = None
    source_hardware_device_id: str | None = Field(default=None, min_length=1, max_length=120)
    source_node_role: NodeRole | None = None
    captured_at: datetime | None = None
    upload_reason: str | None = Field(default=None, min_length=1, max_length=80)
    width: int | None = Field(default=None, ge=1, le=20000)
    height: int | None = Field(default=None, ge=1, le=20000)
    content_type: str | None = Field(default=None, min_length=1, max_length=80)
    upload_ms: int | None = Field(default=None, ge=0, le=3_600_000)
    failure_reason: str | None = Field(default=None, min_length=1, max_length=160)

    @model_validator(mode="after")
    def validate_failure_reason(self) -> ImageUploadPayload:
        if self.status == ImageUploadStatus.FAILED and not self.failure_reason:
            raise ValueError("failure_reason is required when image upload status is failed.")
        return self


PayloadT = TypeVar("PayloadT", bound=BaseModel)


class DeviceMessage(ContractModel, Generic[PayloadT]):
    schema_version: str = Field(min_length=3, max_length=16)
    message_id: str = Field(min_length=1, max_length=120)
    device_id: int | None = Field(default=None, ge=1)
    hardware_device_id: str = Field(min_length=1, max_length=120)
    node_role: NodeRole
    message_type: MessageType
    sent_at: datetime | None = None
    payload: PayloadT

    @field_validator("schema_version")
    @classmethod
    def validate_schema_version(cls, value: str) -> str:
        validate_supported_schema_version(value)
        return value


class CommandPollResponse(ContractModel):
    schema_version: str = Field(default=PLANTLAB_SCHEMA_VERSION, min_length=3, max_length=16)
    commands: list[DeviceMessage[CommandPayload]] = Field(default_factory=list)

    @field_validator("schema_version")
    @classmethod
    def validate_schema_version(cls, value: str) -> str:
        validate_supported_schema_version(value)
        return value


class CanonicalEvent(ContractModel):
    schema_version: str = Field(default=PLANTLAB_SCHEMA_VERSION, min_length=3, max_length=16)
    event_type: EventType
    severity: DiagnosticSeverity
    device_id: int = Field(ge=1)
    hardware_device_id: str = Field(min_length=1, max_length=120)
    node_role: NodeRole
    occurred_at: datetime
    correlation_id: str | None = Field(default=None, max_length=120)
    data: dict[str, Any] = Field(default_factory=dict)

    @field_validator("schema_version")
    @classmethod
    def validate_schema_version(cls, value: str) -> str:
        validate_supported_schema_version(value)
        return value


class ContractLastError(BaseModel):
    code: str | None = Field(default=None, max_length=80)
    message: str | None = Field(default=None, max_length=160)


class ContractDiagnosticsSnapshotPayload(BaseModel):
    schema_version: int = Field(default=1, ge=1, le=5)
    uptime_seconds: int | None = Field(default=None, ge=0)
    wifi_rssi_dbm: int | None = Field(default=None, ge=-127, le=0)
    reboot_reason: str | None = Field(default=None, max_length=80)
    provisioning_state: str | None = Field(default=None, max_length=80)
    last_sensor_reading_age_seconds: int | None = Field(default=None, ge=0, le=2_592_000)
    last_camera_image_upload_age_seconds: int | None = Field(default=None, ge=0, le=2_592_000)
    last_command: None = None
    error_counters: dict[str, int] = Field(default_factory=dict)
    last_error: ContractLastError | None = None


def is_device_message_envelope(raw: Any) -> bool:
    return (
        isinstance(raw, dict)
        and isinstance(raw.get("payload"), dict)
        and "schema_version" in raw
        and "message_type" in raw
        and "message_id" in raw
    )


def parse_heartbeat_message(raw: dict[str, Any]) -> DeviceMessage[HeartbeatPayload]:
    message = _parse_message(raw, HeartbeatPayload)
    if message.message_type != MessageType.HEARTBEAT:
        raise ProtocolValidationError(
            "message_type_mismatch",
            "Expected HEARTBEAT message_type.",
            details={"message_type": str(message.message_type.value)},
        )
    _warn_unknown_fields(message, "heartbeat envelope")
    _warn_unknown_fields(message.payload, "heartbeat payload")
    return message


def parse_diagnostics_message(raw: dict[str, Any]) -> DeviceMessage[DiagnosticsPayload]:
    message = _parse_message(raw, DiagnosticsPayload)
    if message.message_type != MessageType.DIAGNOSTICS:
        raise ProtocolValidationError(
            "message_type_mismatch",
            "Expected DIAGNOSTICS message_type.",
            details={"message_type": str(message.message_type.value)},
        )
    _warn_unknown_fields(message, "diagnostics envelope")
    _warn_unknown_fields(message.payload, "diagnostics payload")
    return message


def parse_command_message(raw: dict[str, Any]) -> DeviceMessage[CommandPayload]:
    message = _parse_message(raw, CommandPayload)
    if message.message_type != MessageType.COMMAND:
        raise ProtocolValidationError(
            "message_type_mismatch",
            "Expected COMMAND message_type.",
            details={"message_type": str(message.message_type.value)},
        )
    _warn_unknown_fields(message, "command envelope")
    _warn_unknown_fields(message.payload, "command payload")
    _warn_unknown_fields(message.payload.target, "command target")
    if message.payload.retry_policy is not None:
        _warn_unknown_fields(message.payload.retry_policy, "command retry policy")
    return message


def parse_command_result_message(raw: dict[str, Any]) -> DeviceMessage[CommandResultPayload]:
    message = _parse_message(raw, CommandResultPayload)
    if message.message_type != MessageType.COMMAND_RESULT:
        raise ProtocolValidationError(
            "message_type_mismatch",
            "Expected COMMAND_RESULT message_type.",
            details={"message_type": str(message.message_type.value)},
        )
    _warn_unknown_fields(message, "command result envelope")
    _warn_unknown_fields(message.payload, "command result payload")
    return message


def parse_ota_status_message(raw: dict[str, Any]) -> DeviceMessage[OTAStatusPayload]:
    message = _parse_message(raw, OTAStatusPayload)
    if message.message_type != MessageType.OTA_STATUS:
        raise ProtocolValidationError(
            "message_type_mismatch",
            "Expected OTA_STATUS message_type.",
            details={"message_type": str(message.message_type.value)},
        )
    _warn_unknown_fields(message, "OTA status envelope")
    _warn_unknown_fields(message.payload, "OTA status payload")
    return message


def parse_image_upload_message(raw: dict[str, Any]) -> DeviceMessage[ImageUploadPayload]:
    message = _parse_message(raw, ImageUploadPayload)
    if message.message_type != MessageType.IMAGE_UPLOAD:
        raise ProtocolValidationError(
            "message_type_mismatch",
            "Expected IMAGE_UPLOAD message_type.",
            details={"message_type": str(message.message_type.value)},
        )
    _warn_unknown_fields(message, "image upload envelope")
    _warn_unknown_fields(message.payload, "image upload payload")
    return message


def diagnostics_snapshot_payload(diagnostics: DiagnosticsPayload) -> ContractDiagnosticsSnapshotPayload:
    return ContractDiagnosticsSnapshotPayload(
        schema_version=SUPPORTED_SCHEMA_MAJOR,
        reboot_reason=diagnostics.reboot_reason,
        error_counters=diagnostics.error_counters,
        last_error=ContractLastError(
            code=diagnostics.last_error_code,
            message=diagnostics.last_error_message,
        )
        if diagnostics.last_error_code or diagnostics.last_error_message
        else None,
    )


def validate_supported_schema_version(value: str) -> None:
    parts = value.split(".")
    if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
        raise ValueError("schema_version must use MAJOR.MINOR format.")
    major = int(parts[0])
    if major != SUPPORTED_SCHEMA_MAJOR:
        raise ValueError(f"Unsupported schema major version: {major}.")


def validation_error_details(error: ValidationError) -> dict[str, Any]:
    safe_errors = []
    for item in error.errors():
        safe_errors.append(
            {
                "loc": list(item.get("loc") or []),
                "msg": str(item.get("msg") or ""),
                "type": str(item.get("type") or ""),
            }
        )
    return {"errors": safe_errors}


def _parse_message(raw: dict[str, Any], payload_model: type[PayloadT]) -> DeviceMessage[PayloadT]:
    try:
        return DeviceMessage[payload_model].model_validate(raw)
    except ValidationError as exc:
        code = "contract_validation_failed"
        message = "Device message failed contract validation."
        for item in exc.errors():
            if "schema_version" in [str(part) for part in item.get("loc", [])] and "Unsupported schema major" in str(item.get("msg", "")):
                code = "unsupported_schema_version"
                message = str(item.get("msg", "")).removeprefix("Value error, ")
        raise ProtocolValidationError(
            code,
            message,
            details=validation_error_details(exc),
        ) from exc
    except ValueError as exc:
        raise ProtocolValidationError(
            "unsupported_schema_version",
            str(exc),
        ) from exc


def _warn_unknown_fields(model: BaseModel, context: str) -> None:
    extra = getattr(model, "model_extra", None)
    if extra:
        logger.warning(
            "Accepted unknown additive fields in %s: %s",
            context,
            ",".join(sorted(str(key) for key in extra.keys())),
        )
