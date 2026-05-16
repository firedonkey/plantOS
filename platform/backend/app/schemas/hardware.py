from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.models import CommandStatus


class HardwareReadingCreate(BaseModel):
    hardware_device_id: str | None = Field(default=None, max_length=120)
    moisture: float | None = Field(default=None, ge=0, le=100)
    temperature: float | None = None
    humidity: float | None = Field(default=None, ge=0, le=100)
    light_on: bool | None = None
    pump_on: bool | None = None
    pump_status: str | None = Field(default=None, max_length=120)
    timestamp: datetime | None = None


class HardwareCommandResultCreate(BaseModel):
    status: CommandStatus
    message: str | None = Field(default=None, max_length=240)
    error: str | None = Field(default=None, max_length=240)
    light_on: bool | None = None
    pump_on: bool | None = None

    @model_validator(mode="after")
    def validate_status(self):
        if self.status not in {CommandStatus.IN_PROGRESS, CommandStatus.COMPLETED, CommandStatus.FAILED}:
            raise ValueError("Hardware command result status must be in_progress, completed, or failed.")
        return self

    @property
    def final_message(self) -> str | None:
        return self.error or self.message


class HardwareHeartbeatCreate(BaseModel):
    hardware_device_id: str | None = Field(default=None, max_length=120)
    node_role: str | None = Field(default=None, min_length=3, max_length=40)
    status: str = Field(default="online", min_length=2, max_length=40)
    software_version: str | None = Field(default=None, max_length=120)
    light_on: bool | None = None
    pump_on: bool | None = None
    message: str | None = Field(default=None, max_length=160)


class HardwareHeartbeatRead(BaseModel):
    device_id: int
    status: str
    hardware_device_id: str | None
    node_role: str | None
    software_version: str | None = None
    light_on: bool | None
    pump_on: bool | None
    message: str | None
    updated_at: datetime | None
    last_seen_at: datetime | None


class HardwarePollEnvelopeRead(BaseModel):
    device_id: int
    commands: list
