"""Add device node metadata.

Revision ID: 20260502_0002
Revises: 20260419_0001
Create Date: 2026-05-02 00:00:00
"""

from collections.abc import Sequence

from alembic import op


revision: str = "20260502_0002"
down_revision: str | Sequence[str] | None = "20260419_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS device_hardware_ids (
          hardware_device_id VARCHAR(120) PRIMARY KEY,
          device_id INTEGER NOT NULL REFERENCES devices(id) ON DELETE CASCADE,
          node_role VARCHAR(40) NOT NULL DEFAULT 'single_board',
          node_index INTEGER,
          display_name VARCHAR(120),
          hardware_model VARCHAR(120),
          hardware_version VARCHAR(120),
          software_version VARCHAR(120),
          capabilities JSONB NOT NULL DEFAULT '{}'::jsonb,
          status VARCHAR(40) NOT NULL DEFAULT 'provisioning',
          created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
          last_seen_at TIMESTAMPTZ
        )
        """
    )
    op.execute(
        """
        ALTER TABLE device_hardware_ids
          ADD COLUMN IF NOT EXISTS node_role VARCHAR(40) NOT NULL DEFAULT 'single_board'
        """
    )
    op.execute(
        """
        ALTER TABLE device_hardware_ids
          ADD COLUMN IF NOT EXISTS node_index INTEGER
        """
    )
    op.execute(
        """
        ALTER TABLE device_hardware_ids
          ADD COLUMN IF NOT EXISTS display_name VARCHAR(120)
        """
    )
    op.execute(
        """
        ALTER TABLE device_hardware_ids
          ADD COLUMN IF NOT EXISTS hardware_model VARCHAR(120)
        """
    )
    op.execute(
        """
        ALTER TABLE device_hardware_ids
          ADD COLUMN IF NOT EXISTS hardware_version VARCHAR(120)
        """
    )
    op.execute(
        """
        ALTER TABLE device_hardware_ids
          ADD COLUMN IF NOT EXISTS software_version VARCHAR(120)
        """
    )
    op.execute(
        """
        ALTER TABLE device_hardware_ids
          ADD COLUMN IF NOT EXISTS capabilities JSONB NOT NULL DEFAULT '{}'::jsonb
        """
    )
    op.execute(
        """
        ALTER TABLE device_hardware_ids
          ADD COLUMN IF NOT EXISTS status VARCHAR(40) NOT NULL DEFAULT 'provisioning'
        """
    )
    op.execute(
        """
        ALTER TABLE device_hardware_ids
          ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        """
    )
    op.execute(
        """
        ALTER TABLE device_hardware_ids
          ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        """
    )
    op.execute(
        """
        ALTER TABLE device_hardware_ids
          ADD COLUMN IF NOT EXISTS last_seen_at TIMESTAMPTZ
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_device_hardware_ids_device_id
          ON device_hardware_ids(device_id)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_device_hardware_ids_node_role
          ON device_hardware_ids(node_role)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_device_hardware_ids_node_role")
