"""expand command value length

Revision ID: 20260530_0013
Revises: 20260527_0012
Create Date: 2026-05-30 09:25:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260530_0013"
down_revision: str | None = "20260527_0012"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "commands",
        "value",
        existing_type=sa.String(length=120),
        type_=sa.String(length=2000),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "commands",
        "value",
        existing_type=sa.String(length=2000),
        type_=sa.String(length=120),
        existing_nullable=True,
    )
