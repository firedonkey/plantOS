from datetime import datetime

from pydantic import BaseModel, Field

from app.contracts import CameraRole
from app.schemas.diagnostics import DeviceDiagnosticEventRead, DeviceDiagnosticSnapshotRead


class DeviceSummaryReadingRead(BaseModel):
    timestamp: datetime
    moisture: float | None
    temperature: float | None
    humidity: float | None
    water_temperature_c: float | None
    water_level_raw: int | None
    water_level_state: str | None
    light_on: bool | None
    light_intensity_percent: int | None
    pump_on: bool | None
    pump_status: str | None


class DeviceSummaryImageRead(BaseModel):
    id: int
    content_url: str
    timestamp: datetime
    source_hardware_device_id: str | None = None
    camera_role: CameraRole | None = None


class DeviceTimelapseFrameRead(BaseModel):
    id: int
    content_url: str
    timestamp: datetime
    source_hardware_device_id: str | None = None
    camera_role: CameraRole | None = None


class DeviceTimelapseRead(BaseModel):
    device_id: int
    camera_role: str = "top"
    window_start: datetime
    window_end: datetime
    interval_minutes: int
    target_duration_seconds: int
    playback_frame_ms: int
    total_image_count: int
    frame_count: int
    frames: list[DeviceTimelapseFrameRead] = Field(default_factory=list)


class DeviceHealthNodeRead(BaseModel):
    hardware_device_id: str
    node_role: str | None
    node_index: int | None
    camera_role: CameraRole | None = None
    display_name: str | None
    status: str
    hardware_model: str | None = None
    hardware_version: str | None = None
    software_version: str | None = None
    ota_status: str | None = None
    ota_available_version: str | None = None
    ota_target_version: str | None = None
    ota_release_id: str | None = None
    ota_progress: int | None = None
    ota_error: str | None = None
    ota_updated_at: datetime | None = None
    ota_last_success_at: datetime | None = None
    capabilities: dict | None = None
    last_seen_at: datetime | None = None
    health_status: str | None = None
    diagnostics: DeviceDiagnosticSnapshotRead | None = None


class DeviceHealthCommandRead(BaseModel):
    id: int
    target: str
    action: str
    status: str
    message: str | None = None
    created_at: datetime
    completed_at: datetime | None = None
    sent_at: datetime | None = None
    timestamp: datetime


class DeviceHardwareHealthRead(BaseModel):
    overall_status: str
    master_status: str | None = None
    master_online: bool = False
    primary: DeviceHealthNodeRead | None = None
    cameras: list[DeviceHealthNodeRead] = Field(default_factory=list)
    last_heartbeat_at: datetime | None = None
    heartbeat_status: str | None = None
    last_reading_at: datetime | None = None
    reading_status: str | None = None
    last_image_at: datetime | None = None
    image_status: str | None = None
    camera_status: str | None = None
    last_command: DeviceHealthCommandRead | None = None
    last_failed_command_reason: str | None = None
    last_failed_command_at: datetime | None = None
    last_successful_command_at: datetime | None = None
    friendly_status: str | None = None
    attention_reasons: list[str] = Field(default_factory=list)
    recent_events: list[DeviceDiagnosticEventRead] = Field(default_factory=list)


class DeviceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    location: str | None = Field(default=None, max_length=120)
    plant_type: str | None = Field(default=None, max_length=120)


class DeviceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    location: str | None = Field(default=None, max_length=120)
    plant_type: str | None = Field(default=None, max_length=120)


class DeviceRead(BaseModel):
    id: int
    name: str
    location: str | None
    plant_type: str | None
    api_token: str | None
    created_at: datetime
    released_at: datetime | None = None
    archived_at: datetime | None = None
    release_reason: str | None = None
    status: str | None = None
    current_light_on: bool | None = None
    current_light_intensity_percent: int | None = None
    current_pump_on: bool | None = None
    latest_reading: DeviceSummaryReadingRead | None = None
    latest_image: DeviceSummaryImageRead | None = None
    node_summary: dict | None = None
    hardware_health: DeviceHardwareHealthRead | None = None

    model_config = {"from_attributes": True}


class DeviceSummaryRead(BaseModel):
    id: int
    name: str
    location: str | None
    plant_type: str | None
    current_light_on: bool | None = None
    current_light_intensity_percent: int | None = None
    current_pump_on: bool | None = None
    latest_reading: DeviceSummaryReadingRead | None
    latest_image: DeviceSummaryImageRead | None
    node_summary: dict
    hardware_health: DeviceHardwareHealthRead | None = None


class DeviceDeleteRead(BaseModel):
    status: str
    device_id: int
    message: str


class DeviceReleaseRead(BaseModel):
    status: str
    device_id: int
    released_at: datetime
    message: str
