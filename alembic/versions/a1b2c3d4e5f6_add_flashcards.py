"""add_flashcards

Revision ID: a1b2c3d4e5f6
Revises: 9c3437b709f6
Create Date: 2026-03-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "9c3437b709f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    # Idempotent: add columns only if missing (table may exist from partial prior run)
    cr = conn.execute(sa.text("SELECT column_name FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'cards'")).fetchall()
    card_cols = {r[0] for r in cr}
    if "answer" not in card_cols:
        op.add_column("cards", sa.Column("answer", sa.Text(), nullable=True))
    if "topic" not in card_cols:
        op.add_column("cards", sa.Column("topic", sa.Text(), nullable=True))

    tr = conn.execute(sa.text("SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'flashcard_responses'")).fetchall()
    if not tr:
        op.create_table(
            "flashcard_responses",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "card_id",
                UUID(as_uuid=True),
                sa.ForeignKey("cards.id"),
                nullable=False,
            ),
            sa.Column(
                "project_id",
                UUID(as_uuid=True),
                sa.ForeignKey("projects.id"),
                nullable=False,
            ),
            sa.Column("user_id", sa.Text(), nullable=False, server_default="default_user"),
            sa.Column("response", sa.Text(), nullable=False),
            sa.Column("next_review_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )


def downgrade() -> None:
    op.drop_table("flashcard_responses")
    op.drop_column("cards", "topic")
    op.drop_column("cards", "answer")
