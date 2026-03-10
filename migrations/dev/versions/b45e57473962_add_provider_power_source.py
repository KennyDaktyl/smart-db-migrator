"""add provider power source

Revision ID: b45e57473962
Revises: a5b3a38eaaea
Create Date: 2026-03-01 14:17:54.891224

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b45e57473962"
down_revision: Union[str, Sequence[str], None] = "a5b3a38eaaea"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    provider_power_source_enum = sa.Enum(
        "INVERTER", "METER", name="provider_power_source_enum"
    )
    provider_power_source_enum.create(bind, checkfirst=True)
    op.add_column(
        "providers",
        sa.Column(
            "power_source",
            sa.Enum("INVERTER", "METER", name="provider_power_source_enum"),
            nullable=True,
            comment="Selects which provider metric is treated as the primary power value",
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("providers", "power_source")
    bind = op.get_bind()
    provider_power_source_enum = sa.Enum(
        "INVERTER", "METER", name="provider_power_source_enum"
    )
    provider_power_source_enum.drop(bind, checkfirst=True)
