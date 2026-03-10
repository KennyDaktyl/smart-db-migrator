"""add scheduler commands queue

Revision ID: a1f7b5c92d4e
Revises: 3ac93cd18e3d
Create Date: 2026-03-01 12:00:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "a1f7b5c92d4e"
down_revision: Union[str, Sequence[str], None] = "3ac93cd18e3d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        """
        DO $$
        BEGIN
            CREATE TYPE scheduler_command_action_enum AS ENUM ('ON', 'OFF');
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END $$;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            CREATE TYPE scheduler_command_status_enum AS ENUM
            ('PENDING', 'SENT', 'ACK_OK', 'ACK_FAIL', 'TIMEOUT', 'CANCELLED');
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END $$;
        """
    )

    scheduler_command_action_enum = postgresql.ENUM(
        "ON",
        "OFF",
        name="scheduler_command_action_enum",
        create_type=False,
    )
    scheduler_command_status_enum = postgresql.ENUM(
        "PENDING",
        "SENT",
        "ACK_OK",
        "ACK_FAIL",
        "TIMEOUT",
        "CANCELLED",
        name="scheduler_command_status_enum",
        create_type=False,
    )

    op.create_table(
        "scheduler_commands",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("command_id", sa.UUID(), nullable=False),
        sa.Column("minute_key", sa.DateTime(timezone=True), nullable=False),
        sa.Column("device_id", sa.Integer(), nullable=False),
        sa.Column("device_uuid", sa.UUID(), nullable=False),
        sa.Column("device_number", sa.Integer(), nullable=False),
        sa.Column("microcontroller_uuid", sa.UUID(), nullable=False),
        sa.Column("scheduler_id", sa.Integer(), nullable=False),
        sa.Column("slot_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("action", scheduler_command_action_enum, nullable=False),
        sa.Column(
            "status",
            scheduler_command_status_enum,
            nullable=False,
        ),
        sa.Column("attempt", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ack_deadline_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("trigger_reason", sa.String(), nullable=True),
        sa.Column("measured_value", sa.Numeric(precision=12, scale=4), nullable=True),
        sa.Column("measured_unit", sa.String(length=16), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["scheduler_id"], ["schedulers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["slot_id"], ["scheduler_slots.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "device_id",
            "slot_id",
            "minute_key",
            "action",
            name="uq_scheduler_idempotency",
        ),
        sa.UniqueConstraint("command_id", name="uq_scheduler_command_id"),
    )
    op.create_index(op.f("ix_scheduler_commands_command_id"), "scheduler_commands", ["command_id"], unique=False)
    op.create_index(op.f("ix_scheduler_commands_device_id"), "scheduler_commands", ["device_id"], unique=False)
    op.create_index(op.f("ix_scheduler_commands_microcontroller_uuid"), "scheduler_commands", ["microcontroller_uuid"], unique=False)
    op.create_index(op.f("ix_scheduler_commands_minute_key"), "scheduler_commands", ["minute_key"], unique=False)
    op.create_index(op.f("ix_scheduler_commands_scheduler_id"), "scheduler_commands", ["scheduler_id"], unique=False)
    op.create_index(op.f("ix_scheduler_commands_slot_id"), "scheduler_commands", ["slot_id"], unique=False)
    op.create_index(op.f("ix_scheduler_commands_user_id"), "scheduler_commands", ["user_id"], unique=False)
    op.create_index(
        "idx_scheduler_commands_pending",
        "scheduler_commands",
        ["status", "next_retry_at", "minute_key"],
        unique=False,
    )
    op.create_index(
        "idx_scheduler_commands_mc",
        "scheduler_commands",
        ["microcontroller_uuid", "status"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("idx_scheduler_commands_mc", table_name="scheduler_commands")
    op.drop_index("idx_scheduler_commands_pending", table_name="scheduler_commands")
    op.drop_index(op.f("ix_scheduler_commands_user_id"), table_name="scheduler_commands")
    op.drop_index(op.f("ix_scheduler_commands_slot_id"), table_name="scheduler_commands")
    op.drop_index(op.f("ix_scheduler_commands_scheduler_id"), table_name="scheduler_commands")
    op.drop_index(op.f("ix_scheduler_commands_minute_key"), table_name="scheduler_commands")
    op.drop_index(op.f("ix_scheduler_commands_microcontroller_uuid"), table_name="scheduler_commands")
    op.drop_index(op.f("ix_scheduler_commands_device_id"), table_name="scheduler_commands")
    op.drop_index(op.f("ix_scheduler_commands_command_id"), table_name="scheduler_commands")
    op.drop_table("scheduler_commands")

    op.execute("DROP TYPE IF EXISTS scheduler_command_status_enum")
    op.execute("DROP TYPE IF EXISTS scheduler_command_action_enum")
