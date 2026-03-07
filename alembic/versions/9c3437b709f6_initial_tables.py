"""initial_tables

Revision ID: 9c3437b709f6
Revises:
Create Date: 2026-03-07 18:55:06.060428

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, UUID

revision: str = "9c3437b709f6"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "projects",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("project_type", sa.Text(), nullable=False),
        sa.Column("end_goal", sa.Text(), nullable=True),
        sa.Column("deadline", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "cards",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "project_id",
            UUID(as_uuid=True),
            sa.ForeignKey("projects.id"),
            nullable=False,
        ),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("options", ARRAY(sa.Text()), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="unanswered"),
        sa.Column("round", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "answers",
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
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "user_interests",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("interests", ARRAY(sa.Text()), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "rss_feeds",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("url", sa.Text(), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "wikipedia_shown",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("article_title", sa.Text(), nullable=False),
        sa.Column("shown_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "project_keywords",
        sa.Column(
            "project_id",
            UUID(as_uuid=True),
            sa.ForeignKey("projects.id"),
            primary_key=True,
        ),
        sa.Column("keywords", ARRAY(sa.Text()), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("description_snapshot", sa.Text(), nullable=True),
    )

    op.create_table(
        "project_context_overrides",
        sa.Column(
            "project_id",
            UUID(as_uuid=True),
            sa.ForeignKey("projects.id"),
            primary_key=True,
        ),
        sa.Column("context", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "wiki_interest_cards",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("parent_category", sa.Text(), nullable=False),
        sa.Column("options", ARRAY(sa.Text()), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="unanswered"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "wiki_interest_answers",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "card_id",
            UUID(as_uuid=True),
            sa.ForeignKey("wiki_interest_cards.id"),
            nullable=False,
        ),
        sa.Column("selected_options", ARRAY(sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "wiki_category_reads",
        sa.Column("user_id", sa.Text(), primary_key=True, server_default="default_user"),
        sa.Column("category_title", sa.Text(), primary_key=True),
        sa.Column("read_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("wiki_category_reads")
    op.drop_table("wiki_interest_answers")
    op.drop_table("wiki_interest_cards")
    op.drop_table("project_context_overrides")
    op.drop_table("project_keywords")
    op.drop_table("wikipedia_shown")
    op.drop_table("rss_feeds")
    op.drop_table("user_interests")
    op.drop_table("answers")
    op.drop_table("cards")
    op.drop_table("projects")
