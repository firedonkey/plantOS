from datetime import datetime

from pydantic import BaseModel


class DeviceStatusCreate(BaseModel):
    light_on: bool | None = None
    pump_on: bool | None = None
    message: str | None = None


class DeviceStatusRead(BaseModel):
    device_id: int
    light_on: bool | None
    pump_on: bool | None
    message: str | None
    updated_at: datetime | None
