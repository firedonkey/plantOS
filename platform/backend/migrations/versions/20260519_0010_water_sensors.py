"""add water sensor reading fields

Revision ID: 20260519_0010
Revises: 20260519_0009
Create Date: 2026-05-19 22:33:06.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260519_0010"
down_revision: str | None = "20260519_0009"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("sensor_readings", sa.Column("water_temperature_c", sa.Float(), nullable=True))
    op.add_column("sensor_readings", sa.Column("water_level_raw", sa.Integer(), nullable=True))
    op.add_column("sensor_readings", sa.Column("water_level_state", sa.String(length=40), nullable=True))


def downgrade() -> None:
    op.drop_column("sensor_readings", "water_level_state")
    op.drop_column("sensor_readings", "water_level_raw")
    op.drop_column("sensor_readings", "water_temperature_c")
