"""add scheduler device_event_name enum values

Revision ID: 3ac93cd18e3d
Revises: 2f0f1b731a6b
Create Date: 2026-02-28 22:05:00.000000

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "3ac93cd18e3d"
down_revision: Union[str, Sequence[str], None] = "2f0f1b731a6b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_SCHEDULER_EVENT_NAMES = [
    "SCHEDULER_TRIGGER_ON",
    "SCHEDULER_SKIPPED_NO_POWER_DATA",
    "SCHEDULER_SKIPPED_THRESHOLD_NOT_MET",
    "SCHEDULER_ACK_FAILED",
]


def upgrade() -> None:
    """Upgrade schema."""
    for value in _SCHEDULER_EVENT_NAMES:
        op.execute(
            f"ALTER TYPE device_event_name_enum ADD VALUE IF NOT EXISTS '{value}'"
        )


def downgrade() -> None:
    """Downgrade schema."""
    # PostgreSQL enum value removal is destructive and intentionally skipped.
    pass
