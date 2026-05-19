"""initial schema

Revision ID: 20260519_0001
Revises:
Create Date: 2026-05-19
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260519_0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("full_name", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("phone_number", sa.String(), nullable=True),
        sa.Column("hashed_password", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("is_admin", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_users_id", "users", ["id"], unique=False)
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_phone_number", "users", ["phone_number"], unique=True)

    op.create_table(
        "hosting_orders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("domain", sa.String(), nullable=False),
        sa.Column("package_name", sa.String(), nullable=False),
        sa.Column("username", sa.String(), nullable=True),
        sa.Column(
            "status",
            sa.Enum("PENDING", "ACTIVE", "SUSPENDED", "TERMINATED", name="hostingstatus"),
            nullable=True,
        ),
        sa.Column("whm_package_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_hosting_orders_id", "hosting_orders", ["id"], unique=False)
    op.create_index("ix_hosting_orders_domain", "hosting_orders", ["domain"], unique=False)

    op.create_table(
        "invoices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("status", sa.Enum("UNPAID", "PAID", "CANCELLED", name="invoicestatus"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_invoices_id", "invoices", ["id"], unique=False)

    op.create_table(
        "user_domains",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("domain_name", sa.String(), nullable=False),
        sa.Column("status", sa.Enum("PENDING", "ACTIVE", "EXPIRED", name="domainstatus"), nullable=True),
        sa.Column("ns1", sa.String(), nullable=True),
        sa.Column("ns2", sa.String(), nullable=True),
        sa.Column("registration_date", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.Column("expiry_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_domains_id", "user_domains", ["id"], unique=False)
    op.create_index("ix_user_domains_domain_name", "user_domains", ["domain_name"], unique=True)

    op.create_table(
        "payment_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("invoice_id", sa.Integer(), nullable=False),
        sa.Column("gateway", sa.Enum("BKASH", "NAGAD", "SSLCOMMERZ", name="paymentgateway"), nullable=False),
        sa.Column("transaction_id", sa.String(), nullable=False),
        sa.Column("raw_response", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_payment_logs_id", "payment_logs", ["id"], unique=False)
    op.create_index("ix_payment_logs_transaction_id", "payment_logs", ["transaction_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_payment_logs_transaction_id", table_name="payment_logs")
    op.drop_index("ix_payment_logs_id", table_name="payment_logs")
    op.drop_table("payment_logs")

    op.drop_index("ix_user_domains_domain_name", table_name="user_domains")
    op.drop_index("ix_user_domains_id", table_name="user_domains")
    op.drop_table("user_domains")

    op.drop_index("ix_invoices_id", table_name="invoices")
    op.drop_table("invoices")

    op.drop_index("ix_hosting_orders_domain", table_name="hosting_orders")
    op.drop_index("ix_hosting_orders_id", table_name="hosting_orders")
    op.drop_table("hosting_orders")

    op.drop_index("ix_users_phone_number", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_id", table_name="users")
    op.drop_table("users")

    op.execute("DROP TYPE IF EXISTS paymentgateway")
    op.execute("DROP TYPE IF EXISTS domainstatus")
    op.execute("DROP TYPE IF EXISTS invoicestatus")
    op.execute("DROP TYPE IF EXISTS hostingstatus")
