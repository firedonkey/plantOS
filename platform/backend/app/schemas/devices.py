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

    model_config = {"from_attributes": True}

class DeviceSummaryRead(BaseModel):
    id: int
    name: str
    location: str | None
    plant_type: str | None
    latest_reading: DeviceSummaryReadingRead | None
    latest_image: DeviceSummaryImageRead | None
    node_summary: dict


class DeviceDeleteRead(BaseModel):
    status: str
    device_id: int
    message: str
