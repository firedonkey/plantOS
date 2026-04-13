from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from platform_app.models.base import Base

if TYPE_CHECKING:
    from platform_app.models.device import Device


class Image(Base):
    __tablename__ = "images"

    id: Mapped[Optional[int]] = mapped_column(primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), index=True)
    path: Mapped[str] = mapped_column(String(500))
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    device: Mapped["Device"] = relationship(back_populates="images")
