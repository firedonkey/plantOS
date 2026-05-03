"""add image source node column

Revision ID: 20260502_0003
Revises: 20260502_0002
Create Date: 2026-05-02 19:10:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260502_0003"
down_revision: str | None = "20260502_0002"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "images",
        sa.Column("source_hardware_device_id", sa.String(length=120), nullable=True),
    )
    op.create_index(
        "ix_images_source_hardware_device_id",
        "images",
        ["source_hardware_device_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_images_source_hardware_device_id_device_hardware_ids",
        "images",
        "device_hardware_ids",
        ["source_hardware_device_id"],
        ["hardware_device_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_images_source_hardware_device_id_device_hardware_ids",
        "images",
        type_="foreignkey",
    )
    op.drop_index("ix_images_source_hardware_device_id", table_name="images")
    op.drop_column("images", "source_hardware_device_id")
