"""Integrated feed: question cards (all projects) + Wikipedia articles + RSS + wiki interest questions."""

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import Answer, Card, FlashcardResponse, Project
from backend.db.session import get_db
from backend.models import FeedItemOut
from backend.routes.rss import get_rss_cards_list
from backend.routes.wikipedia import (
    ensure_wiki_interest_questions,
    get_wikipedia_cards_for_feed,
)

router = APIRouter(tags=["feed"])
FEED_LIMIT = 60
SKIPPED_CAP = 10
WIKI_QUESTION_SPACING = 4
SKIP_WIKI_IN_FEED = False


def _row_to_feed_item(card: Card, project_title: str) -> FeedItemOut:
    return FeedItemOut(
        source="question",
        id=str(card.id),
        project_id=str(card.project_id),
        project_title=project_title,
        type=card.type,
        question=card.question,
        options=list(card.options) if card.options else None,
        status=card.status,
        round=card.round,
        created_at=card.created_at.isoformat(),
        answer=card.answer,
        topic=card.topic,
    )


@router.get("/feed", response_model=list[FeedItemOut])
async def get_feed(request: Request, db: AsyncSession = Depends(get_db)):
    api_key = (request.headers.get("X-Anthropic-Key") or "").strip() or None

    # 1. Skipped project question cards, oldest first
    skipped_result = await db.execute(
        select(Card, Project.title.label("project_title"))
        .join(Project, Card.project_id == Project.id)
        .where(Card.status == "skipped")
        .order_by(Card.created_at.asc())
        .limit(SKIPPED_CAP)
    )
    skipped_rows = skipped_result.all()
    skipped_cards = [_row_to_feed_item(r.Card, r.project_title) for r in skipped_rows]

    # 2. Last activity per project (answers and flashcard responses)
    last_answer_result = await db.execute(
        select(Answer.project_id, func.max(Answer.created_at).label("last_at"))
        .group_by(Answer.project_id)
    )
    last_by_project = {str(r.project_id): r.last_at for r in last_answer_result.all()}

    last_flashcard_result = await db.execute(
        select(
            FlashcardResponse.project_id,
            func.max(FlashcardResponse.created_at).label("last_at"),
        ).group_by(FlashcardResponse.project_id)
    )
    for r in last_flashcard_result.all():
        pid = str(r.project_id)
        existing = last_by_project.get(pid)
        if existing is None or (r.last_at and r.last_at > existing):
            last_by_project[pid] = r.last_at

    # 3. Latest flashcard response per card (for due check)
    fr_result = await db.execute(
        select(
            FlashcardResponse.card_id,
            FlashcardResponse.response,
            FlashcardResponse.next_review_at,
        ).order_by(FlashcardResponse.created_at.desc())
    )
    latest_fr_by_card: dict[str, tuple[str, datetime | None]] = {}
    for r in fr_result.all():
        cid = str(r.card_id)
        if cid not in latest_fr_by_card:
            latest_fr_by_card[cid] = (r.response, r.next_review_at)

    now = datetime.now(timezone.utc)

    # 4. Project IDs with due cards: unanswered question cards or due flashcard cards
    question_only_result = await db.execute(
        select(Card.project_id)
        .where(
            Card.status == "unanswered",
            Card.type.in_(["multiple_choice", "open_ended"]),
        )
        .distinct()
    )
    project_ids_set = {str(r.project_id) for r in question_only_result.all()}

    flashcard_cards_result = await db.execute(
        select(Card, Project.title.label("project_title"))
        .join(Project, Card.project_id == Project.id)
        .where(Card.type == "flashcard")
    )
    due_flashcard_rows: list[tuple[Card, str]] = []
    for r in flashcard_cards_result.all():
        card, title = r.Card, r.project_title
        latest = latest_fr_by_card.get(str(card.id))
        if latest is None:
            due_flashcard_rows.append((card, title))
            project_ids_set.add(str(card.project_id))
        else:
            response, next_review_at = latest
            if response != "knew" and (next_review_at is None or next_review_at <= now):
                due_flashcard_rows.append((card, title))
                project_ids_set.add(str(card.project_id))

    project_ids = sorted(
        project_ids_set,
        key=lambda pid: (str(last_by_project.get(pid) or ""), pid),
    )

    # 5. Per-project due cards: unanswered questions + due flashcards, by created_at
    card_rows_by_project: dict[str, list] = {}
    for pid in project_ids:
        pid_uuid = UUID(pid)
        # Unanswered question cards
        q_result = await db.execute(
            select(Card, Project.title.label("project_title"))
            .join(Project, Card.project_id == Project.id)
            .where(
                Card.project_id == pid_uuid,
                Card.status == "unanswered",
                Card.type.in_(["multiple_choice", "open_ended"]),
            )
            .order_by(Card.created_at)
        )
        rows = list(q_result.all())
        # Due flashcards for this project
        for card, title in due_flashcard_rows:
            if str(card.project_id) != pid:
                continue
            rows.append((card, title))
        rows.sort(key=lambda r: r[0].created_at)
        card_rows_by_project[pid] = rows

    unanswered_cards: list[FeedItemOut] = []
    indices: dict[str, int] = {pid: 0 for pid in project_ids}
    remaining = sum(len(card_rows_by_project[pid]) for pid in project_ids)
    while remaining > 0 and len(skipped_cards) + len(unanswered_cards) < FEED_LIMIT:
        for pid in project_ids:
            rows = card_rows_by_project[pid]
            i = indices[pid]
            if i >= len(rows):
                continue
            r = rows[i]
            card, title = r[0], r[1]
            unanswered_cards.append(_row_to_feed_item(card, title))
            indices[pid] = i + 1
            remaining -= 1
            if len(skipped_cards) + len(unanswered_cards) >= FEED_LIMIT:
                break
        if len(skipped_cards) + len(unanswered_cards) >= FEED_LIMIT:
            break

    question_cards = skipped_cards + unanswered_cards

    # 3. Wiki interest question cards
    if SKIP_WIKI_IN_FEED:
        pending_questions: list[dict] = []
    else:
        pending_questions = await ensure_wiki_interest_questions(db)

    wiki_question_items: list[FeedItemOut] = []
    for q in pending_questions:
        wiki_question_items.append(
            FeedItemOut(
                source="wikipedia_interest_question",
                id=q["id"],
                wiki_interest_card_id=q["id"],
                parent_category=q["parent_category"],
                question="Which of these topics interest you most?",
                options=q["options_display"],
            )
        )

    # 4. Wikipedia article cards
    if SKIP_WIKI_IN_FEED:
        wiki_cards = []
    else:
        wiki_cards = await get_wikipedia_cards_for_feed(db, api_key)
    wiki_items = [
        FeedItemOut(
            source="wikipedia",
            id=w.id,
            title=w.title,
            extract=w.extract,
            url=w.url,
            source_term=w.source_term,
            thumbnail_url=w.thumbnail_url,
        )
        for w in wiki_cards
    ]

    # 5. RSS
    rss_cards = await get_rss_cards_list(db)
    rss_items = [
        FeedItemOut(
            source="rss",
            id=r["id"],
            title=r["title"],
            summary=r["summary"],
            url=r["url"],
            published_at=r["published_at"],
            feed_source=r["source"],
            image_url=r.get("image_url"),
        )
        for r in rss_cards
    ]

    # 6. Interleave
    result_feed: list[FeedItemOut] = []
    q_idx = 0
    w_idx = 0
    r_idx = 0
    wq_idx = 0
    cards_since_wiki_question = WIKI_QUESTION_SPACING
    cards_since_wiki_article = 0

    while len(result_feed) < FEED_LIMIT:
        if len(result_feed) % 5 == 4 and r_idx < len(rss_items):
            result_feed.append(rss_items[r_idx])
            r_idx += 1
            cards_since_wiki_question += 1
            cards_since_wiki_article += 1
        elif cards_since_wiki_question >= WIKI_QUESTION_SPACING and wq_idx < len(wiki_question_items):
            result_feed.append(wiki_question_items[wq_idx])
            wq_idx += 1
            cards_since_wiki_question = 0
            cards_since_wiki_article += 1
        elif cards_since_wiki_article >= 3 and w_idx < len(wiki_items):
            result_feed.append(wiki_items[w_idx])
            w_idx += 1
            cards_since_wiki_article = 0
            cards_since_wiki_question += 1
        elif q_idx < len(question_cards):
            result_feed.append(question_cards[q_idx])
            q_idx += 1
            cards_since_wiki_question += 1
            cards_since_wiki_article += 1
        elif w_idx < len(wiki_items):
            result_feed.append(wiki_items[w_idx])
            w_idx += 1
            cards_since_wiki_question += 1
        elif wq_idx < len(wiki_question_items):
            result_feed.append(wiki_question_items[wq_idx])
            wq_idx += 1
        elif r_idx < len(rss_items):
            result_feed.append(rss_items[r_idx])
            r_idx += 1
        else:
            break

    return result_feed[:FEED_LIMIT]
