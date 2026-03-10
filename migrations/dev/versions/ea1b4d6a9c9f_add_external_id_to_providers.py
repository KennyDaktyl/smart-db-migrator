"""Add external_id to providers

Revision ID: ea1b4d6a9c9f
Revises: c729572b50d4
Create Date: 2025-12-22 15:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "ea1b4d6a9c9f"
down_revision: Union[str, Sequence[str], None] = "c729572b50d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "providers",
        sa.Column("external_id", sa.String(), nullable=True),
    )
    op.execute(
        """
        UPDATE providers
        SET external_id = config ->> 'device_id'
        WHERE external_id IS NULL AND (config::jsonb) ? 'device_id'
        """
    )
    op.execute(
        """
        WITH duplicates AS (
            SELECT
                id,
                ROW_NUMBER() OVER (
                    PARTITION BY user_id, vendor, external_id
                    ORDER BY id
                ) AS rn
            FROM providers
            WHERE external_id IS NOT NULL
        )
        UPDATE providers
        SET external_id = NULL
        FROM duplicates
        WHERE providers.id = duplicates.id AND duplicates.rn > 1
        """
    )
    op.create_unique_constraint(
        "uq_providers_user_vendor_external",
        "providers",
        ["user_id", "vendor", "external_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_providers_user_vendor_external",
        "providers",
        type_="unique",
    )
    op.drop_column("providers", "external_id")
