"""add camera roles for dual camera devices

Revision ID: 20260716_0016
Revises: 20260611_0015
Create Date: 2026-07-16 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op


revision: str = "20260716_0016"
down_revision: str | None = "20260611_0015"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER TABLE device_hardware_ids ADD COLUMN IF NOT EXISTS camera_role VARCHAR(20)")
    op.execute("ALTER TABLE images ADD COLUMN IF NOT EXISTS camera_role VARCHAR(20)")
    op.execute(
        "ALTER TABLE device_timelapse_snapshots "
        "ADD COLUMN IF NOT EXISTS camera_role VARCHAR(20) NOT NULL DEFAULT 'top'"
    )
    op.execute(
        """
        WITH ranked AS (
          SELECT
            hardware_device_id,
            ROW_NUMBER() OVER (
              PARTITION BY device_id
              ORDER BY COALESCE(node_index, 9999), hardware_device_id
            ) AS role_rank
          FROM device_hardware_ids
          WHERE node_role = 'camera'
        )
        UPDATE device_hardware_ids AS node
        SET camera_role = CASE
          WHEN ranked.role_rank = 1 THEN 'top'
          WHEN ranked.role_rank = 2 THEN 'side'
          ELSE NULL
        END
        FROM ranked
        WHERE node.hardware_device_id = ranked.hardware_device_id
          AND node.camera_role IS NULL
          AND ranked.role_rank <= 2
        """
    )
    op.execute(
        """
        UPDATE images AS image
        SET camera_role = node.camera_role
        FROM device_hardware_ids AS node
        WHERE image.source_hardware_device_id = node.hardware_device_id
          AND image.camera_role IS NULL
          AND node.camera_role IS NOT NULL
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_device_hardware_ids_camera_role
          ON device_hardware_ids(camera_role)
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_device_hardware_ids_device_camera_role
          ON device_hardware_ids(device_id, camera_role)
          WHERE node_role = 'camera' AND camera_role IS NOT NULL
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_images_camera_role
          ON images(camera_role)
        """
    )
    op.execute(
        """
        ALTER TABLE device_timelapse_snapshots
          DROP CONSTRAINT IF EXISTS uq_device_timelapse_snapshot_window
        """
    )
    op.execute(
        """
        ALTER TABLE device_timelapse_snapshots
          ADD CONSTRAINT uq_device_timelapse_snapshot_window
          UNIQUE (
            device_id,
            window_days,
            interval_minutes,
            max_frames,
            target_duration_seconds,
            camera_role
          )
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE device_timelapse_snapshots
          DROP CONSTRAINT IF EXISTS uq_device_timelapse_snapshot_window
        """
    )
    op.execute(
        """
        ALTER TABLE device_timelapse_snapshots
          ADD CONSTRAINT uq_device_timelapse_snapshot_window
          UNIQUE (
            device_id,
            window_days,
            interval_minutes,
            max_frames,
            target_duration_seconds
          )
        """
    )
    op.execute("DROP INDEX IF EXISTS ix_images_camera_role")
    op.execute("DROP INDEX IF EXISTS uq_device_hardware_ids_device_camera_role")
    op.execute("DROP INDEX IF EXISTS ix_device_hardware_ids_camera_role")
    op.execute("ALTER TABLE device_timelapse_snapshots DROP COLUMN IF EXISTS camera_role")
    op.execute("ALTER TABLE images DROP COLUMN IF EXISTS camera_role")
    op.execute("ALTER TABLE device_hardware_ids DROP COLUMN IF EXISTS camera_role")
