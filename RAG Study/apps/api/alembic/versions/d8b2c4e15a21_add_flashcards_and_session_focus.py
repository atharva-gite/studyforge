"""add flashcards and session focus

Revision ID: d8b2c4e15a21
Revises: c7a1e2b94d10
Create Date: 2026-09-30 13:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "d8b2c4e15a21"
down_revision: Union[str, Sequence[str], None] = "c7a1e2b94d10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("study_sessions", sa.Column("focus", sa.String(length=200), nullable=True))
    op.create_table(
        "flashcard_decks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["course_id"], ["courses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_flashcard_decks_course_user", "flashcard_decks", ["course_id", "user_id"])
    op.create_table(
        "flashcards",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("deck_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("front", sa.Text(), nullable=False),
        sa.Column("back", sa.Text(), nullable=False),
        sa.Column("source_chunk_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["deck_id"], ["flashcard_decks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_chunk_id"], ["document_chunks.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_flashcards_deck_id", "flashcards", ["deck_id"])
    op.create_table(
        "flashcard_reviews",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("card_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column(
            "rating",
            sa.Enum("AGAIN", "KNOWN", name="card_rating", native_enum=False, length=40),
            nullable=False,
        ),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["card_id"], ["flashcards.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_flashcard_reviews_card_id", "flashcard_reviews", ["card_id"])


def downgrade() -> None:
    op.drop_index("ix_flashcard_reviews_card_id", table_name="flashcard_reviews")
    op.drop_table("flashcard_reviews")
    op.drop_index("ix_flashcards_deck_id", table_name="flashcards")
    op.drop_table("flashcards")
    op.drop_index("ix_flashcard_decks_course_user", table_name="flashcard_decks")
    op.drop_table("flashcard_decks")
    op.drop_column("study_sessions", "focus")
