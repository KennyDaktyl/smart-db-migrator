"""add dynamic provider metrics

Revision ID: c91b4d3a7e10
Revises: 1c2d9f4a6b7e
Create Date: 2026-03-10 11:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c91b4d3a7e10"
down_revision: Union[str, Sequence[str], None] = "1c2d9f4a6b7e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.add_column(
        "providers",
        sa.Column(
            "has_power_meter",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "providers",
        sa.Column(
            "has_energy_storage",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )

    op.create_table(
        "provider_metric_definitions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("provider_id", sa.Integer(), nullable=False),
        sa.Column("metric_key", sa.String(length=64), nullable=False),
        sa.Column("label", sa.String(length=128), nullable=False),
        sa.Column("unit", sa.String(length=16), nullable=True),
        sa.Column("chart_type", sa.String(length=32), nullable=False),
        sa.Column(
            "aggregation_mode",
            sa.String(length=32),
            nullable=False,
        ),
        sa.Column(
            "capability_tag",
            sa.String(length=32),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["provider_id"],
            ["providers.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "provider_id",
            "metric_key",
            name="uq_provider_metric_definitions_provider_metric_key",
        ),
    )
    op.create_index(
        op.f("ix_provider_metric_definitions_provider_id"),
        "provider_metric_definitions",
        ["provider_id"],
        unique=False,
    )

    op.create_table(
        "provider_metric_samples",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("provider_id", sa.Integer(), nullable=False),
        sa.Column("provider_measurement_id", sa.Integer(), nullable=False),
        sa.Column("metric_key", sa.String(length=64), nullable=False),
        sa.Column("measured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("value", sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column("unit", sa.String(length=16), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(
            ["provider_id"],
            ["providers.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["provider_measurement_id"],
            ["provider_measurements.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "provider_measurement_id",
            "metric_key",
            name="uq_provider_metric_samples_measurement_metric_key",
        ),
    )
    op.create_index(
        op.f("ix_provider_metric_samples_provider_id"),
        "provider_metric_samples",
        ["provider_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_provider_metric_samples_provider_measurement_id"),
        "provider_metric_samples",
        ["provider_measurement_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_provider_metric_samples_measured_at"),
        "provider_metric_samples",
        ["measured_at"],
        unique=False,
    )
    op.create_index(
        "ix_provider_metric_samples_provider_metric_measured_at",
        "provider_metric_samples",
        ["provider_id", "metric_key", "measured_at"],
        unique=False,
    )

    op.alter_column("providers", "has_power_meter", server_default=None)
    op.alter_column("providers", "has_energy_storage", server_default=None)


def downgrade() -> None:
    op.drop_index(
        "ix_provider_metric_samples_provider_metric_measured_at",
        table_name="provider_metric_samples",
    )
    op.drop_index(
        op.f("ix_provider_metric_samples_measured_at"),
        table_name="provider_metric_samples",
    )
    op.drop_index(
        op.f("ix_provider_metric_samples_provider_measurement_id"),
        table_name="provider_metric_samples",
    )
    op.drop_index(
        op.f("ix_provider_metric_samples_provider_id"),
        table_name="provider_metric_samples",
    )
    op.drop_table("provider_metric_samples")

    op.drop_index(
        op.f("ix_provider_metric_definitions_provider_id"),
        table_name="provider_metric_definitions",
    )
    op.drop_table("provider_metric_definitions")

    op.drop_column("providers", "has_energy_storage")
    op.drop_column("providers", "has_power_meter")
