"""add staged ota rollout fields

Revision ID: 20260527_0012
Revises: 20260522_0011
Create Date: 2026-05-27 00:12:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260527_0012"
down_revision: str | None = "20260522_0011"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("firmware_releases", sa.Column("max_current_version", sa.String(length=120), nullable=True))
    op.add_column(
        "firmware_releases",
        sa.Column("channel", sa.String(length=20), nullable=False, server_default="stable"),
    )
    op.add_column(
        "firmware_releases",
        sa.Column("rollout_percentage", sa.Integer(), nullable=False, server_default="100"),
    )
    op.add_column("firmware_releases", sa.Column("allowed_hardware_device_ids", sa.Text(), nullable=True))
    op.add_column("firmware_releases", sa.Column("rollback_release_id", sa.String(length=80), nullable=True))
    op.add_column("firmware_releases", sa.Column("rollback_version", sa.String(length=120), nullable=True))
    op.create_index(op.f("ix_firmware_releases_channel"), "firmware_releases", ["channel"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_firmware_releases_channel"), table_name="firmware_releases")
    op.drop_column("firmware_releases", "rollback_version")
    op.drop_column("firmware_releases", "rollback_release_id")
    op.drop_column("firmware_releases", "allowed_hardware_device_ids")
    op.drop_column("firmware_releases", "rollout_percentage")
    op.drop_column("firmware_releases", "channel")
    op.drop_column("firmware_releases", "max_current_version")
