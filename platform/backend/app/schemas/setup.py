from pydantic import BaseModel, Field


class DeviceSetupCodeRequest(BaseModel):
    serial_number: str = Field(min_length=1, max_length=255)
    device_name: str | None = Field(default=None, max_length=120)
    location: str | None = Field(default=None, max_length=120)


class DeviceSetupCodeRead(BaseModel):
    serial_number: str
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
    redirect_path: str | None = None
