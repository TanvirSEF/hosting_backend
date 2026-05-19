"""hosting order billing flow

Revision ID: 20260520_0002
Revises: 20260519_0001
Create Date: 2026-05-20
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260520_0002"
down_revision: Union[str, Sequence[str], None] = "20260519_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE hostingstatus ADD VALUE IF NOT EXISTS 'PAYMENT_PENDING'")
    op.execute("ALTER TYPE hostingstatus ADD VALUE IF NOT EXISTS 'PROVISIONING'")
    op.execute("ALTER TYPE hostingstatus ADD VALUE IF NOT EXISTS 'PROVISION_FAILED'")

    op.create_table(
        "hosting_packages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("whm_package_id", sa.String(), nullable=False),
        sa.Column("price_bdt", sa.Numeric(10, 2), nullable=False),
        sa.Column("billing_period_days", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_hosting_packages_id", "hosting_packages", ["id"], unique=False)
    op.create_index("ix_hosting_packages_name", "hosting_packages", ["name"], unique=True)
    op.create_unique_constraint(
        "uq_hosting_packages_whm_package_id",
        "hosting_packages",
        ["whm_package_id"],
    )

    op.add_column("hosting_orders", sa.Column("invoice_id", sa.Integer(), nullable=True))
    op.add_column("hosting_orders", sa.Column("package_id", sa.Integer(), nullable=True))
    op.add_column("hosting_orders", sa.Column("provision_error", sa.String(), nullable=True))
    op.create_index("ix_hosting_orders_invoice_id", "hosting_orders", ["invoice_id"], unique=False)
    op.create_foreign_key(
        "fk_hosting_orders_invoice_id_invoices",
        "hosting_orders",
        "invoices",
        ["invoice_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_hosting_orders_package_id_hosting_packages",
        "hosting_orders",
        "hosting_packages",
        ["package_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_hosting_orders_package_id_hosting_packages", "hosting_orders", type_="foreignkey")
    op.drop_constraint("fk_hosting_orders_invoice_id_invoices", "hosting_orders", type_="foreignkey")
    op.drop_index("ix_hosting_orders_invoice_id", table_name="hosting_orders")
    op.drop_column("hosting_orders", "provision_error")
    op.drop_column("hosting_orders", "package_id")
    op.drop_column("hosting_orders", "invoice_id")

    op.drop_constraint("uq_hosting_packages_whm_package_id", "hosting_packages", type_="unique")
    op.drop_index("ix_hosting_packages_name", table_name="hosting_packages")
    op.drop_index("ix_hosting_packages_id", table_name="hosting_packages")
    op.drop_table("hosting_packages")
