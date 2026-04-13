from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from platform_app.models.base import Base

if TYPE_CHECKING:
    from platform_app.models.device import Device


class User(Base):
    __tablename__ = "users"

    id: Mapped[Optional[int]] = mapped_column(primary_key=True, autoincrement=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), default=None)
    google_sub: Mapped[Optional[str]] = mapped_column(String(255), unique=True, index=True, default=None)
    name: Mapped[Optional[str]] = mapped_column(String(255), default=None)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    devices: Mapped[list["Device"]] = relationship(back_populates="owner")
