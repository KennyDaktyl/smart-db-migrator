"""add last_seen_at to providers

Revision ID: c3f1b291c123
Revises: b7d0b216b867
Create Date: 2026-01-20 00:00:00.000001
"""

from alembic import op
import sqlalchemy as sa
from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "c3f1b291c123"
down_revision: Union[str, Sequence[str], None] = "b7d0b216b867"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add last_seen_at column to providers."""
    op.add_column(
        "providers",
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Timestamp of last measurement/heartbeat",
        ),
    )


def downgrade() -> None:
    """Remove last_seen_at column."""
    op.drop_column("providers", "last_seen_at")
