from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


OtaStatus = Literal[
    "idle",
    "available",
    "preparing",
    "downloading",
    "validating",
    "installing",
    "rebooting",
    "success",
    "failed",
    "rolled_back",
]


class FirmwareManifestRead(BaseModel):
    update_available: bool
    schema_version: int = 1
    release_id: str | None = None
    node_role: str | None = None
    hardware_model: str | None = None
    version: str | None = None
    version_code: int | None = None
    artifact_url: str | None = None
    artifact_size_bytes: int | None = None
    sha256: str | None = None
    signature: str | None = None


class FirmwareOtaStatusCreate(BaseModel):
    hardware_device_id: str = Field(min_length=3, max_length=120)
    status: OtaStatus
    release_id: str | None = Field(default=None, max_length=80)
    target_version: str | None = Field(default=None, max_length=120)
    installed_version: str | None = Field(default=None, max_length=120)
    progress: int | None = Field(default=None, ge=0, le=100)
    error: str | None = Field(default=None, max_length=240)


class FirmwareOtaStatusRead(BaseModel):
    hardware_device_id: str
    status: OtaStatus
    release_id: str | None = None
    target_version: str | None = None
    available_version: str | None = None
    installed_version: str | None = None
    progress: int | None = None
    error: str | None = None
    updated_at: datetime | None = None
