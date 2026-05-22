"""add apple sign-in subject

Revision ID: 20260522_0011
Revises: 20260519_0010
Create Date: 2026-05-22 12:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260522_0011"
down_revision: str | None = "20260519_0010"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("apple_sub", sa.String(length=255), nullable=True))
    op.create_index(op.f("ix_users_apple_sub"), "users", ["apple_sub"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_users_apple_sub"), table_name="users")
    op.drop_column("users", "apple_sub")
