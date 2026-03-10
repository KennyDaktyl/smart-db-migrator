"""Add provider measurements table to track value changes.

Revision ID: 3963df7a259d
Revises: 4c0081a4b9e2
Create Date: 2026-01-01 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "3963df7a259d"
down_revision: Union[str, Sequence[str], None] = "4c0081a4b9e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "provider_measurements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column(
            "provider_id",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "measured_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "measured_value",
            sa.Numeric(12, 4),
            nullable=True,
        ),
        sa.Column(
            "measured_unit",
            sa.String(length=16),
            nullable=True,
        ),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["provider_id"],
            ["providers.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_provider_measurements_provider_id"),
        "provider_measurements",
        ["provider_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_provider_measurements_measured_at"),
        "provider_measurements",
        ["measured_at"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f("ix_provider_measurements_measured_at"),
        table_name="provider_measurements",
    )
    op.drop_index(
        op.f("ix_provider_measurements_provider_id"),
        table_name="provider_measurements",
    )
    op.drop_table("provider_measurements")
