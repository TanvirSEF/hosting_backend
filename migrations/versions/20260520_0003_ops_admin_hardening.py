"""ops admin hardening

Revision ID: 20260520_0003
Revises: 20260520_0002
Create Date: 2026-05-20
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260520_0003"
down_revision: Union[str, Sequence[str], None] = "20260520_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "automation_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("hosting_order_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("message", sa.String(), nullable=True),
        sa.Column("raw_response", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=True),
        sa.ForeignKeyConstraint(["hosting_order_id"], ["hosting_orders.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_automation_logs_id", "automation_logs", ["id"], unique=False)
    op.create_index("ix_automation_logs_hosting_order_id", "automation_logs", ["hosting_order_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_automation_logs_hosting_order_id", table_name="automation_logs")
    op.drop_index("ix_automation_logs_id", table_name="automation_logs")
    op.drop_table("automation_logs")
