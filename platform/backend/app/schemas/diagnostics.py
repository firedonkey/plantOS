from datetime import datetime

from pydantic import BaseModel, Field, field_validator


KNOWN_COUNTER_KEYS = {
    "wifi_reconnects",
    "upload_failures",
    "ble_provisioning_failures",
    "espnow_failures",
}


class DiagnosticLastCommandCreate(BaseModel):
    id: int | None = Field(default=None, ge=1)
    status: str | None = Field(default=None, max_length=40)
    code: str | None = Field(default=None, max_length=80)
    message: str | None = Field(default=None, max_length=160)
    age_seconds: int | None = Field(default=None, ge=0, le=2_592_000)


class DiagnosticLastErrorCreate(BaseModel):
    code: str | None = Field(default=None, max_length=80)
    message: str | None = Field(default=None, max_length=160)


class HardwareDiagnosticsCreate(BaseModel):
    schema_version: int = Field(default=1, ge=1, le=5)
    uptime_seconds: int | None = Field(default=None, ge=0)
    wifi_rssi_dbm: int | None = Field(default=None, ge=-127, le=0)
    reboot_reason: str | None = Field(default=None, max_length=80)
    provisioning_state: str | None = Field(default=None, max_length=80)
    last_sensor_reading_age_seconds: int | None = Field(default=None, ge=0, le=2_592_000)
    last_camera_image_upload_age_seconds: int | None = Field(default=None, ge=0, le=2_592_000)
    last_command: DiagnosticLastCommandCreate | None = None
    error_counters: dict[str, int] = Field(default_factory=dict, max_length=8)
    last_error: DiagnosticLastErrorCreate | None = None

    @field_validator("error_counters")
    @classmethod
    def validate_error_counters(cls, value: dict[str, int]) -> dict[str, int]:
        normalized: dict[str, int] = {}
        for key, count in value.items():
            if key not in KNOWN_COUNTER_KEYS:
                raise ValueError(f"Unsupported diagnostic counter: {key}")
            if not isinstance(count, int) or count < 0:
                raise ValueError("Diagnostic counters must be non-negative integers.")
            normalized[key] = min(count, 2_147_483_647)
        return normalized


class DeviceDiagnosticSnapshotRead(BaseModel):
    hardware_device_id: str
    device_id: int
    node_role: str | None = None
    schema_version: int
    reported_status: str | None = None
    firmware_version: str | None = None
    uptime_seconds: int | None = None
    wifi_rssi_dbm: int | None = None
    reboot_reason: str | None = None
    provisioning_state: str | None = None
    last_sensor_reading_at: datetime | None = None
    last_camera_image_upload_at: datetime | None = None
    last_command_id: int | None = None
    last_command_status: str | None = None
    last_command_code: str | None = None
    last_command_message: str | None = None
    last_command_at: datetime | None = None
    error_counters: dict[str, int] = Field(default_factory=dict)
    last_error_code: str | None = None
    last_error_message: str | None = None
    reported_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DeviceDiagnosticEventRead(BaseModel):
    id: int
    device_id: int
    hardware_device_id: str | None = None
    event_type: str
    severity: str
    code: str | None = None
    message: str | None = None
    count: int | None = None
    metadata_json: dict = Field(default_factory=dict, alias="metadata")
    occurred_at: datetime
    created_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


class DeviceDiagnosticsRead(BaseModel):
    snapshots: list[DeviceDiagnosticSnapshotRead] = Field(default_factory=list)
    recent_events: list[DeviceDiagnosticEventRead] = Field(default_factory=list)


class DeviceTimelineEventRead(BaseModel):
    id: int
    event_type: str
    severity: str
    occurred_at: datetime
    hardware_device_id: str | None = None
    node_role: str | None = None
    correlation_id: str | None = None
    summary: str
    code: str | None = None
    message: str | None = None
    data: dict = Field(default_factory=dict)
    created_at: datetime


class DeviceTimelineRead(BaseModel):
    events: list[DeviceTimelineEventRead] = Field(default_factory=list)
    next_before: datetime | None = None
