"""add device dependency rules

Revision ID: 9b2d4c8e1f10
Revises: 4f7a9c2d1e6b
Create Date: 2026-03-12 18:45:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9b2d4c8e1f10"
down_revision: Union[str, Sequence[str], None] = "4f7a9c2d1e6b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "devices",
        sa.Column("device_dependency_rule_json", sa.JSON(), nullable=True),
    )
    op.add_column(
        "scheduler_slots",
        sa.Column("device_dependency_rule_json", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("scheduler_slots", "device_dependency_rule_json")
    op.drop_column("devices", "device_dependency_rule_json")
