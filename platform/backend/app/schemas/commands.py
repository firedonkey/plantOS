import json
from datetime import datetime

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

from app.contracts import CameraRole
from app.models import CommandAction, CommandStatus, CommandTarget


class CommandCreate(BaseModel):
    target: CommandTarget
    action: CommandAction
    value: str | dict[str, Any] | None = None

    @model_validator(mode="after")
    def validate_target_action(self):
        grow_light_targets = {CommandTarget.GROW_LIGHT, CommandTarget.LIGHT}
        allows_json_value = (
            self.target == CommandTarget.AMBIENT_LED_BELT
            or (self.target in grow_light_targets and self.action == CommandAction.SET_CHANNEL_INTENSITY)
        )
        if self.value is not None and not isinstance(self.value, str) and not allows_json_value:
            raise ValueError("Command value must be a string.")
        if isinstance(self.value, str) and len(self.value) > 2000:
            raise ValueError("Command value must be at most 2000 characters.")
        if self.target == CommandTarget.PUMP and self.action not in {CommandAction.RUN, CommandAction.OFF}:
            raise ValueError("Pump commands support run or off.")
        if self.target in grow_light_targets and self.action not in {
            CommandAction.ON,
            CommandAction.OFF,
            CommandAction.SET_INTENSITY,
            CommandAction.SET_CHANNEL_INTENSITY,
        }:
            raise ValueError("Grow light commands support on, off, set_intensity, or set_channel_intensity.")
        if self.target in grow_light_targets and self.action == CommandAction.SET_INTENSITY:
            if self.value is None:
                raise ValueError("Grow light intensity commands require a value.")
            try:
                intensity_percent = int(self.value)
            except ValueError as exc:
                raise ValueError("Grow light intensity value must be an integer percent.") from exc
            if intensity_percent < 0 or intensity_percent > 100:
                raise ValueError("Grow light intensity value must be between 0 and 100.")
        if self.target in grow_light_targets and self.action == CommandAction.SET_CHANNEL_INTENSITY:
            if self.value is None:
                raise ValueError("Grow light channel intensity commands require a JSON value.")
            if isinstance(self.value, str):
                try:
                    parsed = json.loads(self.value)
                except json.JSONDecodeError as exc:
                    raise ValueError("Grow light channel intensity value must be JSON.") from exc
            else:
                parsed = self.value
            if not isinstance(parsed, dict):
                raise ValueError("Grow light channel intensity value must be a JSON object.")
            channel = str(parsed.get("channel", "")).strip().lower()
            if channel not in {"red", "white"}:
                raise ValueError("Grow light channel must be red or white.")
            try:
                brightness_percent = int(parsed.get("brightness_percent"))
            except (TypeError, ValueError) as exc:
                raise ValueError("Grow light channel brightness_percent must be an integer percent.") from exc
            if brightness_percent < 0 or brightness_percent > 100:
                raise ValueError("Grow light channel brightness_percent must be between 0 and 100.")
            self.value = json.dumps(
                {"channel": channel, "brightness_percent": brightness_percent},
                separators=(",", ":"),
                sort_keys=True,
            )
        if self.target == CommandTarget.LIGHT:
            self.target = CommandTarget.GROW_LIGHT
        if self.target == CommandTarget.AMBIENT_LED_BELT and self.action != CommandAction.SET:
            raise ValueError("ambient LED belt commands support set.")
        if self.target == CommandTarget.AMBIENT_LED_BELT and self.action == CommandAction.SET:
            if self.value is None:
                raise ValueError("ambient LED belt commands require a JSON value.")
            if isinstance(self.value, str):
                try:
                    parsed = json.loads(self.value)
                except json.JSONDecodeError as exc:
                    raise ValueError("ambient LED belt command value must be JSON.") from exc
            else:
                parsed = self.value
            if not isinstance(parsed, dict):
                raise ValueError("ambient LED belt command value must be a JSON object.")
            encoded = json.dumps(parsed, separators=(",", ":"), sort_keys=True)
            if len(encoded) > 2000:
                raise ValueError("ambient LED belt command value must be at most 2000 characters.")
            self.value = encoded
        if self.target == CommandTarget.CAMERA and self.action not in {CommandAction.CAPTURE}:
            raise ValueError("Camera commands support capture.")
        if self.target == CommandTarget.OTA and self.action not in {CommandAction.START}:
            raise ValueError("OTA commands support start.")
        if self.target == CommandTarget.DIAGNOSTICS and self.action not in {CommandAction.REQUEST}:
            raise ValueError("Diagnostics commands support request.")
        if self.target == CommandTarget.SYSTEM and self.action not in {CommandAction.REBOOT}:
            raise ValueError("System commands support reboot.")
        return self


class CommandAck(BaseModel):
    status: CommandStatus
    message: str | None = Field(default=None, max_length=240)
    light_on: bool | None = None
    light_intensity_percent: int | None = Field(default=None, ge=0, le=100)
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
    light_intensity_percent: int | None
    pump_on: bool | None
    created_at: datetime
    sent_at: datetime | None
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class LightCommandRequest(BaseModel):
    state: Literal["on", "off"] | None = None
    intensity_percent: int | None = Field(default=None, ge=0, le=100)

    @model_validator(mode="after")
    def validate_light_command(self):
        if self.state is None and self.intensity_percent is None:
            raise ValueError("Provide either state or intensity_percent.")
        if self.state is not None and self.intensity_percent is not None:
            raise ValueError("Provide only one of state or intensity_percent.")
        return self


class GrowLightChannelCommandRequest(BaseModel):
    channel: Literal["red", "white"]
    intensity_percent: int = Field(ge=0, le=100)


class PumpCommandRequest(BaseModel):
    action: Literal["run", "off"] = "run"
    seconds: int | None = Field(default=None, ge=1, le=30)


class CaptureCommandRequest(BaseModel):
    camera_role: CameraRole | Literal["all"] = CameraRole.TOP
    camera_node_id: str | None = Field(default=None, min_length=1, max_length=120)

    @model_validator(mode="after")
    def validate_capture_target(self):
        if self.camera_node_id is not None and self.camera_role == "all":
            raise ValueError("camera_node_id cannot be combined with camera_role=all.")
        return self


class DeviceCommandEnvelopeRead(BaseModel):
    status: Literal["accepted", "unsupported", "error"]
    device_id: int
    command: Literal["grow_light", "light", "pump", "capture", "ota"]
    action: str
    queued: bool
    message: str
    command_id: int | None = None
    command_status: CommandStatus | None = None
    created_at: datetime | None = None
    value: str | None = None
    camera_role: str | None = None
    camera_node_id: str | None = None
