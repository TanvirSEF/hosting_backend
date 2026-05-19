"""security hardening

Revision ID: 20260520_0005
Revises: 20260520_0004
Create Date: 2026-05-20
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260520_0005"
down_revision: Union[str, Sequence[str], None] = "20260520_0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("resource_type", sa.String(), nullable=True),
        sa.Column("resource_id", sa.String(), nullable=True),
        sa.Column("ip_address", sa.String(), nullable=True),
        sa.Column("user_agent", sa.String(), nullable=True),
        sa.Column("message", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_logs_id", "audit_logs", ["id"], unique=False)
    op.create_index("ix_audit_logs_actor_user_id", "audit_logs", ["actor_user_id"], unique=False)

    op.create_table(
        "token_blacklist",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("jti", sa.String(), nullable=False),
        sa.Column("token_type", sa.String(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_token_blacklist_id", "token_blacklist", ["id"], unique=False)
    op.create_index("ix_token_blacklist_jti", "token_blacklist", ["jti"], unique=True)
    op.create_index("ix_token_blacklist_user_id", "token_blacklist", ["user_id"], unique=False)

    op.create_table(
        "refresh_token_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("jti", sa.String(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_refresh_token_sessions_id", "refresh_token_sessions", ["id"], unique=False)
    op.create_index("ix_refresh_token_sessions_jti", "refresh_token_sessions", ["jti"], unique=True)
    op.create_index("ix_refresh_token_sessions_user_id", "refresh_token_sessions", ["user_id"], unique=False)

    op.create_table(
        "admin_two_factor_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=True),
        sa.Column("method", sa.String(), nullable=True),
        sa.Column("secret_hint", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index("ix_admin_two_factor_settings_id", "admin_two_factor_settings", ["id"], unique=False)

    op.create_table(
        "provider_credentials",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("provider_name", sa.String(), nullable=False),
        sa.Column("credential_type", sa.String(), nullable=False),
        sa.Column("encrypted_secret", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_provider_credentials_id", "provider_credentials", ["id"], unique=False)
    op.create_index("ix_provider_credentials_provider_name", "provider_credentials", ["provider_name"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_provider_credentials_provider_name", table_name="provider_credentials")
    op.drop_index("ix_provider_credentials_id", table_name="provider_credentials")
    op.drop_table("provider_credentials")

    op.drop_index("ix_admin_two_factor_settings_id", table_name="admin_two_factor_settings")
    op.drop_table("admin_two_factor_settings")

    op.drop_index("ix_refresh_token_sessions_user_id", table_name="refresh_token_sessions")
    op.drop_index("ix_refresh_token_sessions_jti", table_name="refresh_token_sessions")
    op.drop_index("ix_refresh_token_sessions_id", table_name="refresh_token_sessions")
    op.drop_table("refresh_token_sessions")

    op.drop_index("ix_token_blacklist_user_id", table_name="token_blacklist")
    op.drop_index("ix_token_blacklist_jti", table_name="token_blacklist")
    op.drop_index("ix_token_blacklist_id", table_name="token_blacklist")
    op.drop_table("token_blacklist")

    op.drop_index("ix_audit_logs_actor_user_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_id", table_name="audit_logs")
    op.drop_table("audit_logs")
