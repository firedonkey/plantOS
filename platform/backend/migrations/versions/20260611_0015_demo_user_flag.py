"""add demo user flag

Revision ID: 20260611_0015
Revises: 20260530_0014
Create Date: 2026-06-11 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260611_0015"
down_revision: str | None = "20260530_0014"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("is_demo_user", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.alter_column("users", "is_demo_user", server_default=None)


def downgrade() -> None:
    op.drop_column("users", "is_demo_user")
