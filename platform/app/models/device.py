from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.command import Command
    from app.models.event import Event
    from app.models.image import Image
    from app.models.sensor_reading import SensorReading
    from app.models.user import User


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[Optional[int]] = mapped_column(primary_key=True, autoincrement=True, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    location: Mapped[Optional[str]] = mapped_column(String(120), default=None)
    plant_type: Mapped[Optional[str]] = mapped_column(String(120), default=None)
    api_token: Mapped[Optional[str]] = mapped_column(String(80), unique=True, index=True, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    owner: Mapped["User"] = relationship(back_populates="devices")
    readings: Mapped[list["SensorReading"]] = relationship(back_populates="device")
    commands: Mapped[list["Command"]] = relationship(back_populates="device")
    events: Mapped[list["Event"]] = relationship(back_populates="device")
    images: Mapped[list["Image"]] = relationship(back_populates="device")
