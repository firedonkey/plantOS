from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class DeviceDiagnosticSnapshot(Base):
    __tablename__ = "device_diagnostic_snapshots"

    hardware_device_id: Mapped[str] = mapped_column(
        ForeignKey("device_hardware_ids.hardware_device_id", ondelete="CASCADE"),
        primary_key=True,
    )
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"), index=True)
    node_role: Mapped[Optional[str]] = mapped_column(String(40), default=None)
    schema_version: Mapped[int] = mapped_column(Integer, default=1)
    reported_status: Mapped[Optional[str]] = mapped_column(String(40), default=None)
    firmware_version: Mapped[Optional[str]] = mapped_column(String(120), default=None)
    uptime_seconds: Mapped[Optional[int]] = mapped_column(Integer, default=None)
    wifi_rssi_dbm: Mapped[Optional[int]] = mapped_column(Integer, default=None)
    reboot_reason: Mapped[Optional[str]] = mapped_column(String(80), default=None)
    provisioning_state: Mapped[Optional[str]] = mapped_column(String(80), default=None)
    last_sensor_reading_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), default=None)
    last_camera_image_upload_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), default=None)
    last_command_id: Mapped[Optional[int]] = mapped_column(Integer, default=None)
    last_command_status: Mapped[Optional[str]] = mapped_column(String(40), default=None)
    last_command_code: Mapped[Optional[str]] = mapped_column(String(80), default=None)
    last_command_message: Mapped[Optional[str]] = mapped_column(String(160), default=None)
    last_command_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), default=None)
    error_counters: Mapped[dict] = mapped_column(JSON, default=dict)
    last_error_code: Mapped[Optional[str]] = mapped_column(String(80), default=None)
    last_error_message: Mapped[Optional[str]] = mapped_column(String(160), default=None)
    reported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)


class DeviceDiagnosticEvent(Base):
    __tablename__ = "device_diagnostic_events"

    id: Mapped[Optional[int]] = mapped_column(primary_key=True, autoincrement=True, nullable=False)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"), index=True)
    hardware_device_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("device_hardware_ids.hardware_device_id", ondelete="CASCADE"),
        index=True,
        default=None,
    )
    event_type: Mapped[str] = mapped_column(String(80), index=True)
    severity: Mapped[str] = mapped_column(String(20), default="warning")
    code: Mapped[Optional[str]] = mapped_column(String(80), default=None)
    message: Mapped[Optional[str]] = mapped_column(String(160), default=None)
    count: Mapped[Optional[int]] = mapped_column(Integer, default=None)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
