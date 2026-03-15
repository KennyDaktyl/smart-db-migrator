"""add scheduler control policy fields

Revision ID: 4f7a9c2d1e6b
Revises: c91b4d3a7e10
Create Date: 2026-03-12 08:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "4f7a9c2d1e6b"
down_revision: Union[str, Sequence[str], None] = "c91b4d3a7e10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    control_mode_enum = sa.Enum(
        "DIRECT",
        "POLICY",
        name="scheduler_control_mode_enum",
    )
    control_mode_enum.create(op.get_bind(), checkfirst=True)

    op.add_column(
        "scheduler_slots",
        sa.Column(
            "control_mode",
            control_mode_enum,
            nullable=False,
            server_default="DIRECT",
        ),
    )
    op.add_column(
        "scheduler_slots",
        sa.Column("control_policy_json", sa.JSON(), nullable=True),
    )
    op.add_column(
        "scheduler_commands",
        sa.Column("command_payload_json", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("scheduler_commands", "command_payload_json")
    op.drop_column("scheduler_slots", "control_policy_json")
    op.drop_column("scheduler_slots", "control_mode")

    control_mode_enum = sa.Enum(
        "DIRECT",
        "POLICY",
        name="scheduler_control_mode_enum",
    )
    control_mode_enum.drop(op.get_bind(), checkfirst=True)
