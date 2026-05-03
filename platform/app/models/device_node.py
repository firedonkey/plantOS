from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.device import Device


class DeviceNode(Base):
    __tablename__ = "device_hardware_ids"

    hardware_device_id: Mapped[str] = mapped_column(String(120), primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id", ondelete="CASCADE"), index=True)
    node_role: Mapped[str] = mapped_column(String(40), default="single_board", index=True)
    node_index: Mapped[Optional[int]] = mapped_column(Integer, default=None)
    display_name: Mapped[Optional[str]] = mapped_column(String(120), default=None)
    hardware_model: Mapped[Optional[str]] = mapped_column(String(120), default=None)
    hardware_version: Mapped[Optional[str]] = mapped_column(String(120), default=None)
    software_version: Mapped[Optional[str]] = mapped_column(String(120), default=None)
    capabilities: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(40), default="provisioning")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )
    last_seen_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), default=None)

    device: Mapped["Device"] = relationship(back_populates="nodes")
