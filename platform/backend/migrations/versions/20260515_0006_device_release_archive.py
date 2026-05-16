"""add device release archive fields

Revision ID: 20260515_0006
Revises: 20260513_0004
Create Date: 2026-05-15 00:06:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260515_0006"
down_revision: str | None = "20260513_0004"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("devices", sa.Column("released_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("devices", sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("devices", sa.Column("release_reason", sa.String(length=80), nullable=True))
    op.create_index(op.f("ix_devices_released_at"), "devices", ["released_at"], unique=False)
    op.create_index(op.f("ix_devices_archived_at"), "devices", ["archived_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_devices_archived_at"), table_name="devices")
    op.drop_index(op.f("ix_devices_released_at"), table_name="devices")
    op.drop_column("devices", "release_reason")
    op.drop_column("devices", "archived_at")
    op.drop_column("devices", "released_at")
