"""add job lease

Revision ID: e4c9a1b27f03
Revises: d8b2c4e15a21
Create Date: 2026-10-01 13:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e4c9a1b27f03"
down_revision: Union[str, Sequence[str], None] = "d8b2c4e15a21"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("jobs", sa.Column("lease_token", sa.Uuid(), nullable=True))
    op.add_column("jobs", sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.execute(
        "UPDATE jobs SET lease_expires_at = TIMESTAMPTZ '1970-01-01 00:00:00+00' "
        "WHERE status = 'RUNNING' AND lease_expires_at IS NULL"
    )


def downgrade() -> None:
    op.drop_column("jobs", "lease_expires_at")
    op.drop_column("jobs", "lease_token")
