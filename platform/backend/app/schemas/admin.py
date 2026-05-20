from datetime import datetime

from pydantic import BaseModel, Field


class AdminRequesterRead(BaseModel):
    id: int
    email: str


class AdminSummaryRead(BaseModel):
    users: int
    devices: int
    active_devices: int
    released_devices: int
    archived_devices: int
    hardware_nodes: int
    stale_nodes: int
    recent_warning_events: int
    firmware_releases: int


class AdminUserRead(BaseModel):
    id: int
    email: str
    name: str | None = None
    created_at: datetime
    device_count: int
    active_device_count: int
    last_seen_at: datetime | None = None


class AdminNodeRead(BaseModel):
    hardware_device_id: str
    node_role: str | None = None
    display_name: str | None = None
    hardware_model: str | None = None
    software_version: str | None = None
    status: str
    last_seen_at: datetime | None = None
    ota_status: str | None = None
    ota_target_version: str | None = None
    ota_error: str | None = None


class AdminDeviceRead(BaseModel):
    id: int
    name: str
    owner_email: str
    location: str | None = None
    plant_type: str | None = None
    status: str
    created_at: datetime
    released_at: datetime | None = None
    archived_at: datetime | None = None
    latest_reading_at: datetime | None = None
    latest_image_at: datetime | None = None
    node_count: int
    nodes: list[AdminNodeRead] = Field(default_factory=list)
    last_error_code: str | None = None
    last_error_message: str | None = None
    recent_event_count: int


class AdminEventRead(BaseModel):
    id: int
    device_id: int
    device_name: str
    owner_email: str
    hardware_device_id: str | None = None
    event_type: str
    severity: str
    code: str | None = None
    message: str | None = None
    occurred_at: datetime


class AdminFirmwareReleaseRead(BaseModel):
    release_id: str
    node_role: str
    hardware_model: str | None = None
    version: str
    status: str
    published_at: datetime | None = None


class AdminDiagnosticsRead(BaseModel):
    generated_at: datetime
    requested_by: AdminRequesterRead
    summary: AdminSummaryRead
    users: list[AdminUserRead] = Field(default_factory=list)
    devices: list[AdminDeviceRead] = Field(default_factory=list)
    recent_events: list[AdminEventRead] = Field(default_factory=list)
    firmware_releases: list[AdminFirmwareReleaseRead] = Field(default_factory=list)
