from datetime import datetime

from pydantic import BaseModel, Field


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

    model_config = {"from_attributes": True}
