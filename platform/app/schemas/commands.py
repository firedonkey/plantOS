from datetime import datetime

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
            raise ValueError("Light commands support on or off.")
        return self


class CommandAck(BaseModel):
    status: CommandStatus
    message: str | None = Field(default=None, max_length=240)

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
    created_at: datetime
    sent_at: datetime | None
    completed_at: datetime | None

    model_config = {"from_attributes": True}
