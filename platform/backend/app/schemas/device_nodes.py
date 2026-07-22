from datetime import datetime

from pydantic import BaseModel, Field

from app.contracts import CameraRole


class DeviceNodeHeartbeatCreate(BaseModel):
    device_id: int
    hardware_device_id: str = Field(min_length=3, max_length=120)
    node_role: str = Field(min_length=3, max_length=40)
    camera_role: CameraRole | None = None
    status: str = Field(min_length=2, max_length=40)
    software_version: str | None = Field(default=None, max_length=120)


class DeviceNodeHeartbeatRead(BaseModel):
    device_id: int
    hardware_device_id: str
    node_role: str
    camera_role: CameraRole | None = None
    status: str
    software_version: str | None = None
    last_seen_at: datetime | None


class DeviceNodeRegisterCreate(BaseModel):
    device_id: int
    hardware_device_id: str = Field(min_length=3, max_length=120)
    node_role: str = Field(min_length=3, max_length=40)
    node_index: int | None = Field(default=None, ge=1)
    camera_role: CameraRole | None = None
    display_name: str | None = Field(default=None, max_length=120)
    hardware_model: str | None = Field(default=None, max_length=120)
    hardware_version: str | None = Field(default=None, max_length=120)
    software_version: str | None = Field(default=None, max_length=120)
    capabilities: dict = Field(default_factory=dict)
    status: str = Field(default="online", min_length=2, max_length=40)


class DeviceNodeRegisterRead(BaseModel):
    device_id: int
    hardware_device_id: str
    node_role: str
    node_index: int | None
    camera_role: CameraRole | None = None
    display_name: str | None
    hardware_model: str | None
    hardware_version: str | None
    software_version: str | None
    capabilities: dict = Field(default_factory=dict)
    status: str
    last_seen_at: datetime | None
