"""add standalone auth sessions

Revision ID: 20260513_0004
Revises: 20260502_0003
Create Date: 2026-05-13 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260513_0004"
down_revision: str | None = "20260502_0003"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "auth_refresh_sessions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("replaced_by_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["replaced_by_id"], ["auth_refresh_sessions.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_auth_refresh_sessions_expires_at"), "auth_refresh_sessions", ["expires_at"], unique=False)
    op.create_index(op.f("ix_auth_refresh_sessions_token_hash"), "auth_refresh_sessions", ["token_hash"], unique=True)
    op.create_index(op.f("ix_auth_refresh_sessions_user_id"), "auth_refresh_sessions", ["user_id"], unique=False)

    op.create_table(
        "auth_handoff_codes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_auth_handoff_codes_code_hash"), "auth_handoff_codes", ["code_hash"], unique=True)
    op.create_index(op.f("ix_auth_handoff_codes_expires_at"), "auth_handoff_codes", ["expires_at"], unique=False)
    op.create_index(op.f("ix_auth_handoff_codes_user_id"), "auth_handoff_codes", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_auth_handoff_codes_user_id"), table_name="auth_handoff_codes")
    op.drop_index(op.f("ix_auth_handoff_codes_expires_at"), table_name="auth_handoff_codes")
    op.drop_index(op.f("ix_auth_handoff_codes_code_hash"), table_name="auth_handoff_codes")
    op.drop_table("auth_handoff_codes")

    op.drop_index(op.f("ix_auth_refresh_sessions_user_id"), table_name="auth_refresh_sessions")
    op.drop_index(op.f("ix_auth_refresh_sessions_token_hash"), table_name="auth_refresh_sessions")
    op.drop_index(op.f("ix_auth_refresh_sessions_expires_at"), table_name="auth_refresh_sessions")
    op.drop_table("auth_refresh_sessions")
