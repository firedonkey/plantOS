from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from platform_app.models.base import Base

if TYPE_CHECKING:
    from platform_app.models.device import Device


class SensorReading(Base):
    __tablename__ = "sensor_readings"

    id: Mapped[Optional[int]] = mapped_column(primary_key=True, autoincrement=True, nullable=False)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), index=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
    moisture: Mapped[Optional[float]] = mapped_column(Float, default=None)
    temperature: Mapped[Optional[float]] = mapped_column(Float, default=None)
    humidity: Mapped[Optional[float]] = mapped_column(Float, default=None)

    device: Mapped["Device"] = relationship(back_populates="readings")
