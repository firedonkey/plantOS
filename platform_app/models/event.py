from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from platform_app.models.base import Base

if TYPE_CHECKING:
    from platform_app.models.device import Device


class EventType(str, Enum):
    PUMP = "pump"
    LIGHT = "light"


class Event(Base):
    __tablename__ = "events"

    id: Mapped[Optional[int]] = mapped_column(primary_key=True, autoincrement=True, nullable=False)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), index=True)
    type: Mapped[EventType] = mapped_column(String(40), index=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
    value: Mapped[Optional[str]] = mapped_column(String(120), default=None)

    device: Mapped["Device"] = relationship(back_populates="events")
