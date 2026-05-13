from datetime import datetime

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.models import CommandAction, CommandStatus, CommandTarget


class CommandCreate(BaseModel):
    target: CommandTarget
    action: CommandAction
    value: str | None = Field(default=None, max_length=120)

    @model_validator(mode="after")
    def validate_target_action(self):
        if self.target == CommandTarget.PUMP and self.action not in {CommandAction.RUN, CommandAction.OFF}:
            raise ValueError("Pump commands support run or off.")
        if self.target == CommandTarget.LIGHT and self.action not in {CommandAction.ON, CommandAction.OFF}:
            raise ValueError("Growing light commands support on or off.")
        if self.target == CommandTarget.CAMERA and self.action not in {CommandAction.CAPTURE}:
            raise ValueError("Camera commands support capture.")
        return self


class CommandAck(BaseModel):
    status: CommandStatus
    message: str | None = Field(default=None, max_length=240)
    light_on: bool | None = None
    pump_on: bool | None = None

    @model_validator(mode="after")
    def validate_ack_status(self):
        if self.status not in {CommandStatus.COMPLETED, CommandStatus.FAILED}:
            raise ValueError("Command acknowledgement status must be completed or failed.")
        return self


class CommandRead(BaseModel):
    id: int
    device_id: int
    target: CommandTarget
    action: CommandAction
    value: str | None
    status: CommandStatus
    message: str | None
    light_on: bool | None
    pump_on: bool | None
    created_at: datetime
    sent_at: datetime | None
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class LightCommandRequest(BaseModel):
    state: Literal["on", "off"]


class PumpCommandRequest(BaseModel):
    action: Literal["run", "off"] = "run"
    seconds: int | None = Field(default=None, ge=1, le=30)


class DeviceCommandEnvelopeRead(BaseModel):
    status: Literal["accepted", "unsupported", "error"]
    device_id: int
    command: Literal["light", "pump", "capture"]
    action: str
    queued: bool
    message: str
    command_id: int | None = None
    command_status: CommandStatus | None = None
    created_at: datetime | None = None
    value: str | None = None
