from datetime import datetime

from pydantic import BaseModel, Field


class DeviceSummaryReadingRead(BaseModel):
    timestamp: datetime
    moisture: float | None
    temperature: float | None
    humidity: float | None
    light_on: bool | None
    pump_on: bool | None
    pump_status: str | None


class DeviceSummaryImageRead(BaseModel):
    id: int
    content_url: str
    timestamp: datetime
    source_hardware_device_id: str | None = None


class DeviceHealthNodeRead(BaseModel):
    hardware_device_id: str
    node_role: str | None
    node_index: int | None
    display_name: str | None
    status: str
    last_seen_at: datetime | None = None


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
    last_reading_at: datetime | None = None
    last_image_at: datetime | None = None
    last_command: DeviceHealthCommandRead | None = None


class DeviceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    location: str | None = Field(default=None, max_length=120)
    plant_type: str | None = Field(default=None, max_length=120)


class DeviceRead(BaseModel):
    id: int
    name: str
    location: str | None
    plant_type: str | None
    api_token: str | None
    created_at: datetime
    status: str | None = None
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
    latest_reading: DeviceSummaryReadingRead | None
    latest_image: DeviceSummaryImageRead | None
    node_summary: dict
    hardware_health: DeviceHardwareHealthRead | None = None


class DeviceDeleteRead(BaseModel):
    status: str
    device_id: int
    message: str
