from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.device import Device
    from app.models.device_node import DeviceNode


class Image(Base):
    __tablename__ = "images"

    id: Mapped[Optional[int]] = mapped_column(primary_key=True, autoincrement=True, nullable=False)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), index=True)
    source_hardware_device_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("device_hardware_ids.hardware_device_id"),
        default=None,
        index=True,
    )
    path: Mapped[str] = mapped_column(String(500))
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    device: Mapped["Device"] = relationship(back_populates="images")
    source_node: Mapped[Optional["DeviceNode"]] = relationship()
