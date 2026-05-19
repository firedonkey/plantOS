from datetime import datetime

from pydantic import BaseModel, Field


class DeviceStatusCreate(BaseModel):
    light_on: bool | None = None
    light_intensity_percent: int | None = Field(default=None, ge=0, le=100)
    pump_on: bool | None = None
    message: str | None = None


class DeviceStatusRead(BaseModel):
    device_id: int
    light_on: bool | None
    light_intensity_percent: int | None
    pump_on: bool | None
    message: str | None
    updated_at: datetime | None
