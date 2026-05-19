"""add grow light intensity state

Revision ID: 20260519_0009
Revises: 20260516_0008
Create Date: 2026-05-19 08:07:43.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260519_0009"
down_revision: str | None = "20260516_0008"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("devices", sa.Column("current_light_intensity_percent", sa.Integer(), nullable=True))
    op.add_column("sensor_readings", sa.Column("light_intensity_percent", sa.Integer(), nullable=True))
    op.add_column("commands", sa.Column("light_intensity_percent", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("commands", "light_intensity_percent")
    op.drop_column("sensor_readings", "light_intensity_percent")
    op.drop_column("devices", "current_light_intensity_percent")
