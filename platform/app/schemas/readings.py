from datetime import datetime

from pydantic import BaseModel, Field


class SensorReadingCreate(BaseModel):
    device_id: int
    moisture: float | None = Field(default=None, ge=0, le=100)
    temperature: float | None = None
    humidity: float | None = Field(default=None, ge=0, le=100)
    light_on: bool | None = None
    pump_on: bool | None = None
    pump_status: str | None = Field(default=None, max_length=120)
    timestamp: datetime | None = None


class SensorReadingRead(BaseModel):
    id: int
    device_id: int
    timestamp: datetime
    moisture: float | None
    temperature: float | None
    humidity: float | None
    light_on: bool | None
    pump_on: bool | None
    pump_status: str | None

    model_config = {"from_attributes": True}
