"""add device diagnostics snapshots and events

Revision ID: 20260516_0008
Revises: 20260516_0007
Create Date: 2026-05-16 00:08:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260516_0008"
down_revision: str | None = "20260516_0007"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "device_diagnostic_snapshots",
        sa.Column("hardware_device_id", sa.String(length=120), nullable=False),
        sa.Column("device_id", sa.Integer(), nullable=False),
        sa.Column("node_role", sa.String(length=40), nullable=True),
        sa.Column("schema_version", sa.Integer(), nullable=False),
        sa.Column("reported_status", sa.String(length=40), nullable=True),
        sa.Column("firmware_version", sa.String(length=120), nullable=True),
        sa.Column("uptime_seconds", sa.Integer(), nullable=True),
        sa.Column("wifi_rssi_dbm", sa.Integer(), nullable=True),
        sa.Column("reboot_reason", sa.String(length=80), nullable=True),
        sa.Column("provisioning_state", sa.String(length=80), nullable=True),
        sa.Column("last_sensor_reading_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_camera_image_upload_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_command_id", sa.Integer(), nullable=True),
        sa.Column("last_command_status", sa.String(length=40), nullable=True),
        sa.Column("last_command_code", sa.String(length=80), nullable=True),
        sa.Column("last_command_message", sa.String(length=160), nullable=True),
        sa.Column("last_command_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_counters", sa.JSON(), nullable=False),
        sa.Column("last_error_code", sa.String(length=80), nullable=True),
        sa.Column("last_error_message", sa.String(length=160), nullable=True),
        sa.Column("reported_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["hardware_device_id"], ["device_hardware_ids.hardware_device_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("hardware_device_id"),
    )
    op.create_index(op.f("ix_device_diagnostic_snapshots_device_id"), "device_diagnostic_snapshots", ["device_id"], unique=False)
    op.create_index(op.f("ix_device_diagnostic_snapshots_reported_at"), "device_diagnostic_snapshots", ["reported_at"], unique=False)
    op.create_index(op.f("ix_device_diagnostic_snapshots_updated_at"), "device_diagnostic_snapshots", ["updated_at"], unique=False)

    op.create_table(
        "device_diagnostic_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("device_id", sa.Integer(), nullable=False),
        sa.Column("hardware_device_id", sa.String(length=120), nullable=True),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("code", sa.String(length=80), nullable=True),
        sa.Column("message", sa.String(length=160), nullable=True),
        sa.Column("count", sa.Integer(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["hardware_device_id"], ["device_hardware_ids.hardware_device_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_device_diagnostic_events_created_at"), "device_diagnostic_events", ["created_at"], unique=False)
    op.create_index(op.f("ix_device_diagnostic_events_device_id"), "device_diagnostic_events", ["device_id"], unique=False)
    op.create_index(op.f("ix_device_diagnostic_events_event_type"), "device_diagnostic_events", ["event_type"], unique=False)
    op.create_index(op.f("ix_device_diagnostic_events_hardware_device_id"), "device_diagnostic_events", ["hardware_device_id"], unique=False)
    op.create_index(op.f("ix_device_diagnostic_events_occurred_at"), "device_diagnostic_events", ["occurred_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_device_diagnostic_events_occurred_at"), table_name="device_diagnostic_events")
    op.drop_index(op.f("ix_device_diagnostic_events_hardware_device_id"), table_name="device_diagnostic_events")
    op.drop_index(op.f("ix_device_diagnostic_events_event_type"), table_name="device_diagnostic_events")
    op.drop_index(op.f("ix_device_diagnostic_events_device_id"), table_name="device_diagnostic_events")
    op.drop_index(op.f("ix_device_diagnostic_events_created_at"), table_name="device_diagnostic_events")
    op.drop_table("device_diagnostic_events")
    op.drop_index(op.f("ix_device_diagnostic_snapshots_updated_at"), table_name="device_diagnostic_snapshots")
    op.drop_index(op.f("ix_device_diagnostic_snapshots_reported_at"), table_name="device_diagnostic_snapshots")
    op.drop_index(op.f("ix_device_diagnostic_snapshots_device_id"), table_name="device_diagnostic_snapshots")
    op.drop_table("device_diagnostic_snapshots")
