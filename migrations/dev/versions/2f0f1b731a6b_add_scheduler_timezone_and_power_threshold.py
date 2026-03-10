"""add scheduler timezone and power-threshold slot fields

Revision ID: 2f0f1b731a6b
Revises: 8fbd96e3c3cb
Create Date: 2026-02-28 11:40:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "2f0f1b731a6b"
down_revision: Union[str, Sequence[str], None] = "8fbd96e3c3cb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "schedulers",
        sa.Column(
            "timezone", sa.String(length=64), nullable=False, server_default="UTC"
        ),
    )
    op.add_column(
        "schedulers",
        sa.Column(
            "utc_offset_minutes", sa.Integer(), nullable=False, server_default="0"
        ),
    )

    op.add_column(
        "scheduler_slots",
        sa.Column(
            "start_local_time",
            sa.String(length=5),
            nullable=True,
            comment="HH:MM in user's local timezone",
        ),
    )
    op.add_column(
        "scheduler_slots",
        sa.Column(
            "end_local_time",
            sa.String(length=5),
            nullable=True,
            comment="HH:MM in user's local timezone",
        ),
    )
    op.add_column(
        "scheduler_slots",
        sa.Column(
            "start_utc_time",
            sa.String(length=5),
            nullable=True,
            comment="HH:MM normalized to UTC",
        ),
    )
    op.add_column(
        "scheduler_slots",
        sa.Column(
            "end_utc_time",
            sa.String(length=5),
            nullable=True,
            comment="HH:MM normalized to UTC",
        ),
    )
    op.add_column(
        "scheduler_slots",
        sa.Column(
            "use_power_threshold", sa.Boolean(), nullable=False, server_default="false"
        ),
    )
    op.add_column(
        "scheduler_slots",
        sa.Column(
            "power_threshold_value",
            sa.Numeric(precision=12, scale=4),
            nullable=True,
            comment="Power threshold value for slot rule",
        ),
    )
    op.add_column(
        "scheduler_slots",
        sa.Column(
            "power_threshold_unit",
            sa.String(length=16),
            nullable=True,
            comment="Power threshold unit (W, kW, MW)",
        ),
    )

    op.execute(
        """
        UPDATE scheduler_slots
        SET
            start_local_time = start_time,
            end_local_time = end_time,
            start_utc_time = start_time,
            end_utc_time = end_time
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("scheduler_slots", "power_threshold_unit")
    op.drop_column("scheduler_slots", "power_threshold_value")
    op.drop_column("scheduler_slots", "use_power_threshold")
    op.drop_column("scheduler_slots", "end_utc_time")
    op.drop_column("scheduler_slots", "start_utc_time")
    op.drop_column("scheduler_slots", "end_local_time")
    op.drop_column("scheduler_slots", "start_local_time")
    op.drop_column("schedulers", "utc_offset_minutes")
    op.drop_column("schedulers", "timezone")
