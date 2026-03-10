"""add expected_interval_sec to providers table

Revision ID: b7d0b216b867
Revises: 3963df7a259d
Create Date: 2026-01-20 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "b7d0b216b867"
down_revision: Union[str, Sequence[str], None] = "3963df7a259d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add expected_interval_sec to providers."""
    op.add_column(
        "providers",
        sa.Column(
            "expected_interval_sec",
            sa.Integer(),
            nullable=True,
            comment="Expected max interval (seconds) between measurements",
        ),
    )


def downgrade() -> None:
    """Remove expected_interval_sec from providers."""
    op.drop_column("providers", "expected_interval_sec")
