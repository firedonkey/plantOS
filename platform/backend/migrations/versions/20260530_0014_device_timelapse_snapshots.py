"""add device timelapse snapshots

Revision ID: 20260530_0014
Revises: 20260530_0013
Create Date: 2026-05-30 14:20:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260530_0014"
down_revision: str | None = "20260530_0013"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "device_timelapse_snapshots",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("device_id", sa.Integer(), nullable=False),
        sa.Column("window_days", sa.Integer(), nullable=False),
        sa.Column("interval_minutes", sa.Integer(), nullable=False),
        sa.Column("max_frames", sa.Integer(), nullable=False),
        sa.Column("target_duration_seconds", sa.Integer(), nullable=False),
        sa.Column("playback_frame_ms", sa.Integer(), nullable=False),
        sa.Column("total_image_count", sa.Integer(), nullable=False),
        sa.Column("frame_count", sa.Integer(), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("frames", sa.JSON(), nullable=False),
        sa.Column("latest_image_id", sa.Integer(), nullable=True),
        sa.Column("refreshed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "device_id",
            "window_days",
            "interval_minutes",
            "max_frames",
            "target_duration_seconds",
            name="uq_device_timelapse_snapshot_window",
        ),
    )
    op.create_index(
        op.f("ix_device_timelapse_snapshots_device_id"),
        "device_timelapse_snapshots",
        ["device_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_device_timelapse_snapshots_device_id"), table_name="device_timelapse_snapshots")
    op.drop_table("device_timelapse_snapshots")
