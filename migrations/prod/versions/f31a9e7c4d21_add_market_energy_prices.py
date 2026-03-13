"""add market energy prices table

Revision ID: f31a9e7c4d21
Revises: 8fbd96e3c3cb
Create Date: 2026-03-13 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f31a9e7c4d21"
down_revision: Union[str, Sequence[str], None] = "8fbd96e3c3cb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "market_energy_prices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("market", sa.String(length=32), nullable=False),
        sa.Column("business_date", sa.Date(), nullable=False),
        sa.Column("interval_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("interval_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("price_value", sa.Numeric(precision=12, scale=6), nullable=False),
        sa.Column("currency", sa.String(length=8), nullable=False),
        sa.Column("price_unit", sa.String(length=16), nullable=False),
        sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "market",
            "interval_start",
            name="uq_market_energy_prices_market_interval_start",
        ),
    )
    op.create_index(
        op.f("ix_market_energy_prices_market"),
        "market_energy_prices",
        ["market"],
        unique=False,
    )
    op.create_index(
        op.f("ix_market_energy_prices_business_date"),
        "market_energy_prices",
        ["business_date"],
        unique=False,
    )
    op.create_index(
        op.f("ix_market_energy_prices_interval_start"),
        "market_energy_prices",
        ["interval_start"],
        unique=False,
    )
    op.create_index(
        op.f("ix_market_energy_prices_interval_end"),
        "market_energy_prices",
        ["interval_end"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_market_energy_prices_interval_end"),
        table_name="market_energy_prices",
    )
    op.drop_index(
        op.f("ix_market_energy_prices_interval_start"),
        table_name="market_energy_prices",
    )
    op.drop_index(
        op.f("ix_market_energy_prices_business_date"),
        table_name="market_energy_prices",
    )
    op.drop_index(
        op.f("ix_market_energy_prices_market"),
        table_name="market_energy_prices",
    )
    op.drop_table("market_energy_prices")
