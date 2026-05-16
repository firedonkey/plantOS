"""add firmware ota release catalog

Revision ID: 20260516_0007
Revises: 20260515_0006
Create Date: 2026-05-16 00:07:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260516_0007"
down_revision: str | None = "20260515_0006"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "firmware_releases",
        sa.Column("release_id", sa.String(length=80), nullable=False),
        sa.Column("node_role", sa.String(length=40), nullable=False),
        sa.Column("hardware_model", sa.String(length=120), nullable=True),
        sa.Column("version", sa.String(length=120), nullable=False),
        sa.Column("version_code", sa.Integer(), nullable=False),
        sa.Column("min_current_version", sa.String(length=120), nullable=True),
        sa.Column("artifact_path", sa.String(length=500), nullable=False),
        sa.Column("artifact_size_bytes", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("signature", sa.String(length=512), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("release_id"),
    )
    op.create_index(op.f("ix_firmware_releases_node_role"), "firmware_releases", ["node_role"], unique=False)
    op.create_index(op.f("ix_firmware_releases_hardware_model"), "firmware_releases", ["hardware_model"], unique=False)
    op.create_index(op.f("ix_firmware_releases_version_code"), "firmware_releases", ["version_code"], unique=False)
    op.create_index(op.f("ix_firmware_releases_status"), "firmware_releases", ["status"], unique=False)

    op.add_column("device_hardware_ids", sa.Column("ota_status", sa.String(length=40), nullable=False, server_default="idle"))
    op.add_column("device_hardware_ids", sa.Column("ota_available_version", sa.String(length=120), nullable=True))
    op.add_column("device_hardware_ids", sa.Column("ota_target_version", sa.String(length=120), nullable=True))
    op.add_column("device_hardware_ids", sa.Column("ota_release_id", sa.String(length=80), nullable=True))
    op.add_column("device_hardware_ids", sa.Column("ota_progress", sa.Integer(), nullable=True))
    op.add_column("device_hardware_ids", sa.Column("ota_error", sa.String(length=240), nullable=True))
    op.add_column("device_hardware_ids", sa.Column("ota_updated_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("device_hardware_ids", sa.Column("ota_last_success_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("device_hardware_ids", "ota_last_success_at")
    op.drop_column("device_hardware_ids", "ota_updated_at")
    op.drop_column("device_hardware_ids", "ota_error")
    op.drop_column("device_hardware_ids", "ota_progress")
    op.drop_column("device_hardware_ids", "ota_release_id")
    op.drop_column("device_hardware_ids", "ota_target_version")
    op.drop_column("device_hardware_ids", "ota_available_version")
    op.drop_column("device_hardware_ids", "ota_status")
    op.drop_index(op.f("ix_firmware_releases_status"), table_name="firmware_releases")
    op.drop_index(op.f("ix_firmware_releases_version_code"), table_name="firmware_releases")
    op.drop_index(op.f("ix_firmware_releases_hardware_model"), table_name="firmware_releases")
    op.drop_index(op.f("ix_firmware_releases_node_role"), table_name="firmware_releases")
    op.drop_table("firmware_releases")
