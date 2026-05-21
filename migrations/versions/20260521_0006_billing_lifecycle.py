"""billing lifecycle

Revision ID: 20260521_0006
Revises: 20260520_0005
Create Date: 2026-05-21
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260521_0006"
down_revision: Union[str, Sequence[str], None] = "20260520_0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    billing_service_type = sa.Enum("HOSTING", "DOMAIN", name="billingservicetype")
    billing_reason = sa.Enum("MANUAL", "INITIAL_PURCHASE", "RENEWAL", name="billingreason")
    billing_service_type.create(op.get_bind(), checkfirst=True)
    billing_reason.create(op.get_bind(), checkfirst=True)

    op.add_column("invoices", sa.Column("service_type", billing_service_type, nullable=True))
    op.add_column("invoices", sa.Column("service_id", sa.Integer(), nullable=True))
    op.add_column(
        "invoices",
        sa.Column("billing_reason", billing_reason, server_default="MANUAL", nullable=False),
    )
    op.add_column("invoices", sa.Column("reminder_sent_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("invoices", sa.Column("overdue_processed_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_invoices_service_type", "invoices", ["service_type"], unique=False)
    op.create_index("ix_invoices_service_id", "invoices", ["service_id"], unique=False)

    op.add_column("hosting_orders", sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "hosting_orders",
        sa.Column("auto_renew", sa.Boolean(), server_default=sa.text("true"), nullable=False),
    )
    op.create_index("ix_hosting_orders_expires_at", "hosting_orders", ["expires_at"], unique=False)

    op.add_column(
        "user_domains",
        sa.Column("auto_renew", sa.Boolean(), server_default=sa.text("true"), nullable=False),
    )


def downgrade() -> None:
    op.drop_column("user_domains", "auto_renew")

    op.drop_index("ix_hosting_orders_expires_at", table_name="hosting_orders")
    op.drop_column("hosting_orders", "auto_renew")
    op.drop_column("hosting_orders", "expires_at")

    op.drop_index("ix_invoices_service_id", table_name="invoices")
    op.drop_index("ix_invoices_service_type", table_name="invoices")
    op.drop_column("invoices", "overdue_processed_at")
    op.drop_column("invoices", "reminder_sent_at")
    op.drop_column("invoices", "billing_reason")
    op.drop_column("invoices", "service_id")
    op.drop_column("invoices", "service_type")

    sa.Enum(name="billingreason").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="billingservicetype").drop(op.get_bind(), checkfirst=True)
