"""add energy price fields to user profiles

Revision ID: 1c2d9f4a6b7e
Revises: 38efb6371b9c
Create Date: 2026-03-08 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "1c2d9f4a6b7e"
down_revision: Union[str, Sequence[str], None] = "38efb6371b9c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user_profiles",
        sa.Column("energy_price_amount", sa.Numeric(precision=12, scale=6), nullable=True),
    )
    op.add_column(
        "user_profiles",
        sa.Column("energy_price_currency", sa.String(length=8), nullable=True),
    )
    op.add_column(
        "user_profiles",
        sa.Column("energy_price_unit", sa.String(length=16), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("user_profiles", "energy_price_unit")
    op.drop_column("user_profiles", "energy_price_currency")
    op.drop_column("user_profiles", "energy_price_amount")
