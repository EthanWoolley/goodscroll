#!/usr/bin/env python3
"""Seed PostgreSQL from an existing SQLite database.

Usage:
    python scripts/seed_from_sqlite.py [path/to/scroll.db]

Defaults to backend/scroll.db if no path is provided.
Requires DATABASE_URL to be set in .env or environment.
"""
import asyncio
import json
import os
import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.db.models import (
    Answer,
    Base,
    Card,
    Project,
    ProjectContextOverride,
    ProjectKeyword,
    RssFeed,
    UserInterest,
    WikiCategoryRead,
    WikiInterestAnswer,
    WikiInterestCard,
    WikipediaShown,
)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:password@localhost:5432/scrollapp",
)


def _parse_ts(val: str | None) -> datetime:
    if not val:
        return datetime.now(timezone.utc)
    try:
        dt = datetime.fromisoformat(val)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return datetime.now(timezone.utc)


def _parse_uuid(val: str) -> uuid.UUID:
    try:
        return uuid.UUID(val)
    except (ValueError, TypeError):
        return uuid.uuid4()


def _parse_json_list(val: str | None) -> list[str]:
    if not val:
        return []
    try:
        parsed = json.loads(val)
        if isinstance(parsed, list):
            return [str(x) for x in parsed]
        return []
    except (json.JSONDecodeError, TypeError):
        return []


def read_sqlite(db_path: str) -> dict:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    data: dict[str, list[dict]] = {}

    tables = [
        "projects", "cards", "answers", "user_interests", "rss_feeds",
        "wikipedia_shown", "project_keywords", "project_context_overrides",
        "wiki_interest_cards", "wiki_interest_answers", "wiki_category_reads",
    ]
    for table in tables:
        try:
            rows = conn.execute(f"SELECT * FROM {table}").fetchall()
            data[table] = [dict(r) for r in rows]
        except sqlite3.OperationalError:
            data[table] = []

    conn.close()
    return data


async def seed(data: dict) -> None:
    engine = create_async_engine(DATABASE_URL, echo=False)
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        for row in data.get("projects", []):
            session.add(Project(
                id=_parse_uuid(row["id"]),
                title=row["title"],
                description=row["description"],
                project_type=row["project_type"],
                end_goal=row.get("end_goal"),
                deadline=row.get("deadline"),
                created_at=_parse_ts(row["created_at"]),
            ))
        await session.commit()

        for row in data.get("cards", []):
            session.add(Card(
                id=_parse_uuid(row["id"]),
                project_id=_parse_uuid(row["project_id"]),
                type=row["type"],
                question=row["question"],
                options=_parse_json_list(row.get("options")),
                status=row.get("status", "unanswered"),
                round=row.get("round", 1),
                created_at=_parse_ts(row["created_at"]),
            ))
        await session.commit()

        for row in data.get("answers", []):
            session.add(Answer(
                id=_parse_uuid(row["id"]),
                card_id=_parse_uuid(row["card_id"]),
                project_id=_parse_uuid(row["project_id"]),
                answer=row["answer"],
                created_at=_parse_ts(row["created_at"]),
            ))
        await session.commit()

        for row in data.get("user_interests", []):
            session.add(UserInterest(
                id=row["id"],
                interests=_parse_json_list(row.get("interests")),
                updated_at=_parse_ts(row["updated_at"]),
            ))
        await session.commit()

        for row in data.get("rss_feeds", []):
            session.add(RssFeed(
                id=_parse_uuid(row["id"]),
                url=row["url"],
                created_at=_parse_ts(row["created_at"]),
            ))
        await session.commit()

        for row in data.get("wikipedia_shown", []):
            session.add(WikipediaShown(
                id=_parse_uuid(row["id"]),
                article_title=row["article_title"],
                shown_at=_parse_ts(row["shown_at"]),
            ))
        await session.commit()

        for row in data.get("project_keywords", []):
            session.add(ProjectKeyword(
                project_id=_parse_uuid(row["project_id"]),
                keywords=_parse_json_list(row.get("keywords")),
                generated_at=_parse_ts(row["generated_at"]),
                description_snapshot=row.get("description_snapshot"),
            ))
        await session.commit()

        for row in data.get("project_context_overrides", []):
            session.add(ProjectContextOverride(
                project_id=_parse_uuid(row["project_id"]),
                context=row["context"],
                updated_at=_parse_ts(row["updated_at"]),
            ))
        await session.commit()

        for row in data.get("wiki_interest_cards", []):
            session.add(WikiInterestCard(
                id=_parse_uuid(row["id"]),
                parent_category=row["parent_category"],
                options=_parse_json_list(row.get("options")),
                status=row.get("status", "unanswered"),
                created_at=_parse_ts(row["created_at"]),
            ))
        await session.commit()

        for row in data.get("wiki_interest_answers", []):
            session.add(WikiInterestAnswer(
                id=_parse_uuid(row["id"]),
                card_id=_parse_uuid(row["card_id"]),
                selected_options=_parse_json_list(row.get("selected_options")),
                created_at=_parse_ts(row["created_at"]),
            ))
        await session.commit()

        for row in data.get("wiki_category_reads", []):
            session.add(WikiCategoryRead(
                user_id=row.get("user_id", "default_user"),
                category_title=row["category_title"],
                read_count=row.get("read_count", 0),
                updated_at=_parse_ts(row["updated_at"]),
            ))
        await session.commit()

    await engine.dispose()
    print("Seed complete.")


def main() -> None:
    default_path = Path(__file__).resolve().parent.parent / "backend" / "scroll.db"
    db_path = sys.argv[1] if len(sys.argv) > 1 else str(default_path)

    if not Path(db_path).exists():
        print(f"SQLite file not found: {db_path}")
        print("Nothing to seed.")
        return

    print(f"Reading from SQLite: {db_path}")
    data = read_sqlite(db_path)
    total = sum(len(v) for v in data.values())
    print(f"Found {total} rows across {len(data)} tables.")

    asyncio.run(seed(data))


if __name__ == "__main__":
    main()
