"""Integrated feed: question cards (all projects) + Wikipedia articles + RSS + wiki interest questions."""
import json

from fastapi import APIRouter, Request

from backend.db.database import get_connection
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
# Feature flag: when True, skip Wikipedia work in the feed (for perf/debug); default False so wiki is enabled
SKIP_WIKI_IN_FEED = False


def _row_to_feed_item(row, project_title: str) -> FeedItemOut:
    return FeedItemOut(
        source="question",
        id=row["id"],
        project_id=row["project_id"],
        project_title=project_title,
        type=row["type"],
        question=row["question"],
        options=json.loads(row["options"]) if row["options"] else None,
        status=row["status"],
        round=row["round"],
        created_at=row["created_at"],
    )


@router.get("/feed", response_model=list[FeedItemOut])
def get_feed(request: Request):
    api_key = (request.headers.get("X-Anthropic-Key") or "").strip() or None
    conn = get_connection()

    # 1. Skipped project question cards, oldest first
    skipped_rows = conn.execute(
        """SELECT c.id, c.project_id, c.type, c.question, c.options, c.status, c.round, c.created_at, p.title as project_title
           FROM cards c
           JOIN projects p ON c.project_id = p.id
           WHERE c.status = 'skipped'
           ORDER BY c.created_at ASC
           LIMIT ?""",
        (SKIPPED_CAP,),
    ).fetchall()
    skipped_cards = [_row_to_feed_item(r, r["project_title"]) for r in skipped_rows]

    # 2. Unanswered project question cards: round-robin by least-recently-answered project
    project_last_answer = conn.execute(
        """SELECT project_id, MAX(a.created_at) as last_at
           FROM answers a
           GROUP BY project_id"""
    ).fetchall()
    last_by_project = {r["project_id"]: r["last_at"] for r in project_last_answer}

    projects_with_cards = conn.execute(
        "SELECT DISTINCT project_id FROM cards WHERE status = 'unanswered'"
    ).fetchall()
    project_ids = [r["project_id"] for r in projects_with_cards]
    project_ids.sort(key=lambda pid: (last_by_project.get(pid) or "", pid))

    unanswered_cards: list[FeedItemOut] = []
    indices = {pid: 0 for pid in project_ids}
    card_rows_by_project = {}
    for pid in project_ids:
        rows = conn.execute(
            """SELECT c.id, c.project_id, c.type, c.question, c.options, c.status, c.round, c.created_at, p.title as project_title
               FROM cards c
               JOIN projects p ON c.project_id = p.id
               WHERE c.project_id = ? AND c.status = 'unanswered'
               ORDER BY c.created_at""",
            (pid,),
        ).fetchall()
        card_rows_by_project[pid] = rows

    remaining = sum(len(card_rows_by_project[pid]) for pid in project_ids)
    while remaining > 0 and len(skipped_cards) + len(unanswered_cards) < FEED_LIMIT:
        for pid in project_ids:
            rows = card_rows_by_project[pid]
            i = indices[pid]
            if i >= len(rows):
                continue
            r = rows[i]
            unanswered_cards.append(_row_to_feed_item(r, r["project_title"]))
            indices[pid] = i + 1
            remaining -= 1
            if len(skipped_cards) + len(unanswered_cards) >= FEED_LIMIT:
                break
        if len(skipped_cards) + len(unanswered_cards) >= FEED_LIMIT:
            break

    question_cards = skipped_cards + unanswered_cards

    # 3. Wiki interest question cards (skipped when SKIP_WIKI_IN_FEED is True)
    if SKIP_WIKI_IN_FEED:
        pending_questions = []
    else:
        pending_questions = ensure_wiki_interest_questions(conn)
    conn.close()

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

    # 4. Wikipedia article cards (skipped when SKIP_WIKI_IN_FEED is True)
    if SKIP_WIKI_IN_FEED:
        wiki_cards = []
    else:
        wiki_cards = get_wikipedia_cards_for_feed(api_key)
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
    rss_cards = get_rss_cards_list()
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
    # Rules:
    #   - Wiki interest question: at most once every WIKI_QUESTION_SPACING cards
    #   - RSS: every 5th position
    #   - Wiki articles: every 3rd non-question position
    #   - No cap on total feed size (raised to FEED_LIMIT=60)
    result: list[FeedItemOut] = []
    q_idx = 0
    w_idx = 0
    r_idx = 0
    wq_idx = 0
    cards_since_wiki_question = WIKI_QUESTION_SPACING
    cards_since_wiki_article = 0

    while len(result) < FEED_LIMIT:
        # RSS every 5th slot
        if len(result) % 5 == 4 and r_idx < len(rss_items):
            result.append(rss_items[r_idx])
            r_idx += 1
            cards_since_wiki_question += 1
            cards_since_wiki_article += 1
        # Wiki interest question if spacing allows
        elif cards_since_wiki_question >= WIKI_QUESTION_SPACING and wq_idx < len(wiki_question_items):
            result.append(wiki_question_items[wq_idx])
            wq_idx += 1
            cards_since_wiki_question = 0
            cards_since_wiki_article += 1
        # Wiki article every ~3 question cards
        elif cards_since_wiki_article >= 3 and w_idx < len(wiki_items):
            result.append(wiki_items[w_idx])
            w_idx += 1
            cards_since_wiki_article = 0
            cards_since_wiki_question += 1
        # Project question card
        elif q_idx < len(question_cards):
            result.append(question_cards[q_idx])
            q_idx += 1
            cards_since_wiki_question += 1
            cards_since_wiki_article += 1
        # Drain remaining wiki articles
        elif w_idx < len(wiki_items):
            result.append(wiki_items[w_idx])
            w_idx += 1
            cards_since_wiki_question += 1
        # Drain remaining wiki questions
        elif wq_idx < len(wiki_question_items):
            result.append(wiki_question_items[wq_idx])
            wq_idx += 1
        # Drain remaining RSS
        elif r_idx < len(rss_items):
            result.append(rss_items[r_idx])
            r_idx += 1
        else:
            break

    return result[:FEED_LIMIT]
