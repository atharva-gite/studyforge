"""add chunk search vector

Revision ID: c7a1e2b94d10
Revises: b8143f5ec902
Create Date: 2026-09-29 12:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "c7a1e2b94d10"
down_revision: Union[str, Sequence[str], None] = "b8143f5ec902"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "document_chunks",
        sa.Column(
            "search_vector",
            postgresql.TSVECTOR(),
            sa.Computed("to_tsvector('english', text)", persisted=True),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_document_chunks_search",
        "document_chunks",
        ["search_vector"],
        unique=False,
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index("ix_document_chunks_search", table_name="document_chunks")
    op.drop_column("document_chunks", "search_vector")
