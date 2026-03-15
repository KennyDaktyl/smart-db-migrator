"""scheduler slots

Revision ID: 70c809c27c09
Revises: c91b4d3a7e10
Create Date: 2026-03-11 05:15:14.016676

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '70c809c27c09'
down_revision: Union[str, Sequence[str], None] = 'c91b4d3a7e10'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'devices',
        sa.Column(
            'auto_rule_json',
            sa.JSON(),
            nullable=True,
            comment='Structured AUTO mode rule for device',
        ),
    )
    op.add_column(
        'scheduler_slots',
        sa.Column(
            'activation_rule_json',
            sa.JSON(),
            nullable=True,
            comment='Structured activation rule for scheduler slot',
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('scheduler_slots', 'activation_rule_json')
    op.drop_column('devices', 'auto_rule_json')
