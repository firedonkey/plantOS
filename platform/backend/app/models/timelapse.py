from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class DeviceTimelapseSnapshot(Base):
    __tablename__ = "device_timelapse_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "device_id",
            "window_days",
            "interval_minutes",
            "max_frames",
            "target_duration_seconds",
            name="uq_device_timelapse_snapshot_window",
        ),
    )

    id: Mapped[Optional[int]] = mapped_column(primary_key=True, autoincrement=True, nullable=False)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), index=True)
    window_days: Mapped[int] = mapped_column(Integer, nullable=False)
    interval_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    max_frames: Mapped[int] = mapped_column(Integer, nullable=False)
    target_duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    playback_frame_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    total_image_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    frame_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    window_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    frames: Mapped[list[dict]] = mapped_column(JSON, nullable=False, default=list)
    latest_image_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    refreshed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
