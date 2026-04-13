from datetime import datetime, timezone
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.device import Device


class CommandTarget(str, Enum):
    PUMP = "pump"
    LIGHT = "light"


class CommandAction(str, Enum):
    ON = "on"
    OFF = "off"
    RUN = "run"


class CommandStatus(str, Enum):
    PENDING = "pending"
    SENT = "sent"
    COMPLETED = "completed"
    FAILED = "failed"


class Command(Base):
    __tablename__ = "commands"

    id: Mapped[Optional[int]] = mapped_column(primary_key=True, autoincrement=True, nullable=False)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), index=True)
    target: Mapped[CommandTarget] = mapped_column(String(40), index=True)
    action: Mapped[CommandAction] = mapped_column(String(40))
    value: Mapped[Optional[str]] = mapped_column(String(120), default=None)
    status: Mapped[CommandStatus] = mapped_column(
        String(40),
        default=CommandStatus.PENDING,
        index=True,
    )
    message: Mapped[Optional[str]] = mapped_column(String(240), default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), default=None)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), default=None)

    device: Mapped["Device"] = relationship(back_populates="commands")
