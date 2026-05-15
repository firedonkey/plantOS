from datetime import datetime

from pydantic import BaseModel, Field


class DeviceSetupCodeRequest(BaseModel):
    serial_number: str = Field(min_length=1, max_length=255)
    device_name: str | None = Field(default=None, max_length=120)
    location: str | None = Field(default=None, max_length=120)


class BleDeviceIdentityRequest(BaseModel):
    source: str | None = Field(default=None, max_length=40)
    schema_version: int | None = None
    device_id: str = Field(min_length=3, max_length=120)
    hardware_device_id: str | None = Field(default=None, max_length=120)
    hardware_model: str | None = Field(default=None, max_length=120)
    hardware_version: str | None = Field(default=None, max_length=120)
    software_version: str | None = Field(default=None, max_length=120)
    node_role: str | None = Field(default=None, max_length=40)
    display_name: str | None = Field(default=None, max_length=120)
    ble_name: str | None = Field(default=None, max_length=120)
    serial_number: str | None = Field(default=None, max_length=120)


class DeviceClaimTokenRequest(BaseModel):
    device_name: str | None = Field(default=None, max_length=120)
    location: str | None = Field(default=None, max_length=120)
    device_identity: BleDeviceIdentityRequest


class DeviceSetupCodeRead(BaseModel):
    serial_number: str | None = None
    expected_device_id: str | None = None
    setup_code: str | None = None
    claim_token: str | None = None
    setup_token: str | None = None
    local_setup_url: str
    provisioning_api_url: str
    platform_url: str | None = None
    setup_finishing_url: str
    continue_setup_url: str
    expect_image: bool = True


class SetupStatusRead(BaseModel):
    ready: bool
    device_found: bool = False
    device_id: int | None = None
    has_reading: bool = False
    has_image: bool = False
    expect_image: bool = True
    online: bool = False
    last_heartbeat_at: datetime | None = None
    status: str | None = None
    redirect_path: str | None = None
