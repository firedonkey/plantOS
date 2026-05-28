from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class FirmwareRelease(Base):
    __tablename__ = "firmware_releases"

    release_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    node_role: Mapped[str] = mapped_column(String(40), index=True)
    hardware_model: Mapped[Optional[str]] = mapped_column(String(120), default=None, index=True)
    version: Mapped[str] = mapped_column(String(120))
    version_code: Mapped[int] = mapped_column(Integer, index=True)
    min_current_version: Mapped[Optional[str]] = mapped_column(String(120), default=None)
    max_current_version: Mapped[Optional[str]] = mapped_column(String(120), default=None)
    channel: Mapped[str] = mapped_column(String(20), default="stable", index=True)
    rollout_percentage: Mapped[int] = mapped_column(Integer, default=100)
    allowed_hardware_device_ids: Mapped[Optional[str]] = mapped_column(Text, default=None)
    rollback_release_id: Mapped[Optional[str]] = mapped_column(String(80), default=None)
    rollback_version: Mapped[Optional[str]] = mapped_column(String(120), default=None)
    artifact_path: Mapped[str] = mapped_column(String(500))
    artifact_size_bytes: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(String(64))
    signature: Mapped[Optional[str]] = mapped_column(String(512), default=None)
    status: Mapped[str] = mapped_column(String(40), default="draft", index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), default=None)
