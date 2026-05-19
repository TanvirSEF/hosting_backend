"""phase2 mock mvp

Revision ID: 20260520_0004
Revises: 20260520_0003
Create Date: 2026-05-20
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260520_0004"
down_revision: Union[str, Sequence[str], None] = "20260520_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "support_tickets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("subject", sa.String(), nullable=False),
        sa.Column("status", sa.Enum("OPEN", "WAITING_CUSTOMER", "WAITING_ADMIN", "RESOLVED", "CLOSED", name="supportticketstatus"), nullable=True),
        sa.Column("priority", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_support_tickets_id", "support_tickets", ["id"], unique=False)
    op.create_index("ix_support_tickets_user_id", "support_tickets", ["user_id"], unique=False)

    op.create_table(
        "support_ticket_messages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ticket_id", sa.Integer(), nullable=False),
        sa.Column("sender_user_id", sa.Integer(), nullable=False),
        sa.Column("sender_role", sa.String(), nullable=False),
        sa.Column("message", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["sender_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["ticket_id"], ["support_tickets.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_support_ticket_messages_id", "support_ticket_messages", ["id"], unique=False)
    op.create_index("ix_support_ticket_messages_ticket_id", "support_ticket_messages", ["ticket_id"], unique=False)

    op.create_table(
        "hosting_tool_action_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("hosting_order_id", sa.Integer(), nullable=False),
        sa.Column("tool", sa.String(), nullable=False),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("message", sa.String(), nullable=True),
        sa.Column("raw_response", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["hosting_order_id"], ["hosting_orders.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_hosting_tool_action_logs_id", "hosting_tool_action_logs", ["id"], unique=False)
    op.create_index("ix_hosting_tool_action_logs_hosting_order_id", "hosting_tool_action_logs", ["hosting_order_id"], unique=False)

    op.create_table(
        "dns_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("hosting_order_id", sa.Integer(), nullable=False),
        sa.Column("record_type", sa.Enum("A", "AAAA", "CNAME", "MX", "TXT", "NS", name="dnsrecordtype"), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("value", sa.String(), nullable=False),
        sa.Column("ttl", sa.Integer(), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["hosting_order_id"], ["hosting_orders.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_dns_records_id", "dns_records", ["id"], unique=False)
    op.create_index("ix_dns_records_hosting_order_id", "dns_records", ["hosting_order_id"], unique=False)

    op.create_table(
        "ssl_certificates",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("hosting_order_id", sa.Integer(), nullable=False),
        sa.Column("domain", sa.String(), nullable=False),
        sa.Column("status", sa.Enum("NOT_ISSUED", "PENDING", "ACTIVE", "FAILED", "EXPIRED", name="sslstatus"), nullable=True),
        sa.Column("issuer", sa.String(), nullable=True),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["hosting_order_id"], ["hosting_orders.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ssl_certificates_id", "ssl_certificates", ["id"], unique=False)
    op.create_index("ix_ssl_certificates_hosting_order_id", "ssl_certificates", ["hosting_order_id"], unique=False)

    op.create_table(
        "email_accounts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("hosting_order_id", sa.Integer(), nullable=False),
        sa.Column("email_address", sa.String(), nullable=False),
        sa.Column("quota_mb", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["hosting_order_id"], ["hosting_orders.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_email_accounts_id", "email_accounts", ["id"], unique=False)
    op.create_index("ix_email_accounts_hosting_order_id", "email_accounts", ["hosting_order_id"], unique=False)
    op.create_index("ix_email_accounts_email_address", "email_accounts", ["email_address"], unique=False)

    op.create_table(
        "hosting_databases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("hosting_order_id", sa.Integer(), nullable=False),
        sa.Column("database_name", sa.String(), nullable=False),
        sa.Column("username", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["hosting_order_id"], ["hosting_orders.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_hosting_databases_id", "hosting_databases", ["id"], unique=False)
    op.create_index("ix_hosting_databases_hosting_order_id", "hosting_databases", ["hosting_order_id"], unique=False)

    op.create_table(
        "wordpress_installs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("hosting_order_id", sa.Integer(), nullable=False),
        sa.Column("site_url", sa.String(), nullable=False),
        sa.Column("admin_username", sa.String(), nullable=False),
        sa.Column("status", sa.Enum("PENDING", "INSTALLED", "FAILED", name="wordpressstatus"), nullable=True),
        sa.Column("install_error", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("installed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["hosting_order_id"], ["hosting_orders.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_wordpress_installs_id", "wordpress_installs", ["id"], unique=False)
    op.create_index("ix_wordpress_installs_hosting_order_id", "wordpress_installs", ["hosting_order_id"], unique=False)

    op.create_table(
        "backup_jobs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("hosting_order_id", sa.Integer(), nullable=False),
        sa.Column("backup_type", sa.String(), nullable=True),
        sa.Column("status", sa.Enum("QUEUED", "RUNNING", "COMPLETED", "FAILED", "RESTORING", "RESTORED", name="backupstatus"), nullable=True),
        sa.Column("message", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["hosting_order_id"], ["hosting_orders.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_backup_jobs_id", "backup_jobs", ["id"], unique=False)
    op.create_index("ix_backup_jobs_hosting_order_id", "backup_jobs", ["hosting_order_id"], unique=False)

    op.create_table(
        "hosting_usage_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("hosting_order_id", sa.Integer(), nullable=False),
        sa.Column("disk_used_mb", sa.Integer(), nullable=True),
        sa.Column("bandwidth_used_mb", sa.Integer(), nullable=True),
        sa.Column("inode_used", sa.Integer(), nullable=True),
        sa.Column("email_accounts", sa.Integer(), nullable=True),
        sa.Column("databases", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["hosting_order_id"], ["hosting_orders.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_hosting_usage_snapshots_id", "hosting_usage_snapshots", ["id"], unique=False)
    op.create_index("ix_hosting_usage_snapshots_hosting_order_id", "hosting_usage_snapshots", ["hosting_order_id"], unique=False)

    op.create_table(
        "file_manager_entries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("hosting_order_id", sa.Integer(), nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("path", sa.String(), nullable=False),
        sa.Column("entry_type", sa.String(), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["hosting_order_id"], ["hosting_orders.id"]),
        sa.ForeignKeyConstraint(["parent_id"], ["file_manager_entries.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_file_manager_entries_id", "file_manager_entries", ["id"], unique=False)
    op.create_index("ix_file_manager_entries_hosting_order_id", "file_manager_entries", ["hosting_order_id"], unique=False)
    op.create_index("ix_file_manager_entries_parent_id", "file_manager_entries", ["parent_id"], unique=False)

    op.create_table(
        "whmcs_import_batches",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_whmcs_import_batches_id", "whmcs_import_batches", ["id"], unique=False)

    op.create_table(
        "whmcs_import_rows",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("batch_id", sa.Integer(), nullable=False),
        sa.Column("row_type", sa.String(), nullable=False),
        sa.Column("source_id", sa.String(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("message", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["batch_id"], ["whmcs_import_batches.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_whmcs_import_rows_id", "whmcs_import_rows", ["id"], unique=False)
    op.create_index("ix_whmcs_import_rows_batch_id", "whmcs_import_rows", ["batch_id"], unique=False)


def downgrade() -> None:
    tables = [
        ("whmcs_import_rows", ["ix_whmcs_import_rows_batch_id", "ix_whmcs_import_rows_id"]),
        ("whmcs_import_batches", ["ix_whmcs_import_batches_id"]),
        ("file_manager_entries", ["ix_file_manager_entries_parent_id", "ix_file_manager_entries_hosting_order_id", "ix_file_manager_entries_id"]),
        ("hosting_usage_snapshots", ["ix_hosting_usage_snapshots_hosting_order_id", "ix_hosting_usage_snapshots_id"]),
        ("backup_jobs", ["ix_backup_jobs_hosting_order_id", "ix_backup_jobs_id"]),
        ("wordpress_installs", ["ix_wordpress_installs_hosting_order_id", "ix_wordpress_installs_id"]),
        ("hosting_databases", ["ix_hosting_databases_hosting_order_id", "ix_hosting_databases_id"]),
        ("email_accounts", ["ix_email_accounts_email_address", "ix_email_accounts_hosting_order_id", "ix_email_accounts_id"]),
        ("ssl_certificates", ["ix_ssl_certificates_hosting_order_id", "ix_ssl_certificates_id"]),
        ("dns_records", ["ix_dns_records_hosting_order_id", "ix_dns_records_id"]),
        ("hosting_tool_action_logs", ["ix_hosting_tool_action_logs_hosting_order_id", "ix_hosting_tool_action_logs_id"]),
        ("support_ticket_messages", ["ix_support_ticket_messages_ticket_id", "ix_support_ticket_messages_id"]),
        ("support_tickets", ["ix_support_tickets_user_id", "ix_support_tickets_id"]),
    ]
    for table_name, indexes in tables:
        for index_name in indexes:
            op.drop_index(index_name, table_name=table_name)
        op.drop_table(table_name)

    op.execute("DROP TYPE IF EXISTS backupstatus")
    op.execute("DROP TYPE IF EXISTS wordpressstatus")
    op.execute("DROP TYPE IF EXISTS sslstatus")
    op.execute("DROP TYPE IF EXISTS dnsrecordtype")
    op.execute("DROP TYPE IF EXISTS supportticketstatus")
