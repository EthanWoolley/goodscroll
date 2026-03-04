"""Integrated feed: question cards (all projects) + Wikipedia + RSS."""
import json
import traceback

from fastapi import APIRouter, Request

from backend.db.database import get_connection
from backend.models import FeedItemOut
from backend.routes.rss import get_rss_cards_list
from backend.routes.wikipedia import get_wikipedia_cards_for_feed

router = APIRouter(tags=["feed"])
FEED_LIMIT = 30
SKIPPED_CAP = 10


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

    # 1. Skipped question cards (all projects), oldest first
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

    # 2. Unanswered cards: projects weighted by least recently answered, round-robin
    project_last_answer = conn.execute(
        """SELECT project_id, MAX(a.created_at) as last_at
           FROM answers a
           GROUP BY project_id"""
    ).fetchall()
    last_by_project = {r["project_id"]: r["last_at"] for r in project_last_answer}

    projects_with_cards = conn.execute(
        """SELECT DISTINCT project_id FROM cards WHERE status = 'unanswered'"""
    ).fetchall()
    project_ids = [r["project_id"] for r in projects_with_cards]
    # Sort by last answered (null first = never answered), then by project_id for stability
    project_ids.sort(key=lambda pid: (last_by_project.get(pid) or "", pid))

    unanswered_cards = []
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
    conn.close()

    # #region agent log
    try:
        wiki_cards = get_wikipedia_cards_for_feed(api_key)
        with open("/Users/ethanwoolley/Local Work/Good scroll/goodscroll/.cursor/debug-cc8682.log", "a") as f:
            f.write(json.dumps({"sessionId":"cc8682","hypothesisId":"A,D","location":"feed.py:get_feed:after_wiki","message":"wikipedia ok","data":{"count":len(wiki_cards)},"timestamp":__import__("time").time()*1000}) + "\n")
    except Exception as e:
        try:
            with open("/Users/ethanwoolley/Local Work/Good scroll/goodscroll/.cursor/debug-cc8682.log", "a") as f:
                f.write(json.dumps({"sessionId":"cc8682","hypothesisId":"A,D","location":"feed.py:get_feed:wiki_error","message":"wikipedia failed","data":{"error":str(e),"tb":traceback.format_exc()},"timestamp":__import__("time").time()*1000}) + "\n")
        except Exception:
            pass
        raise
    # #endregion
    # #region agent log
    try:
        rss_cards = get_rss_cards_list()
        with open("/Users/ethanwoolley/Local Work/Good scroll/goodscroll/.cursor/debug-cc8682.log", "a") as f:
            f.write(json.dumps({"sessionId":"cc8682","hypothesisId":"D","location":"feed.py:get_feed:after_rss","message":"rss ok","data":{"count":len(rss_cards)},"timestamp":__import__("time").time()*1000}) + "\n")
    except Exception as e:
        try:
            with open("/Users/ethanwoolley/Local Work/Good scroll/goodscroll/.cursor/debug-cc8682.log", "a") as f:
                f.write(json.dumps({"sessionId":"cc8682","hypothesisId":"D","location":"feed.py:get_feed:rss_error","message":"rss failed","data":{"error":str(e),"tb":traceback.format_exc()},"timestamp":__import__("time").time()*1000}) + "\n")
        except Exception:
            pass
        raise
    # #endregion

    # Convert wiki to FeedItemOut
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

    # Convert rss to FeedItemOut
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

    # Interleave: ~1 Wikipedia per 3 question cards, ~1 RSS per 5 total; cap 30
    result = []
    q_idx = 0
    w_idx = 0
    r_idx = 0
    questions_since_wiki = 0
    while len(result) < FEED_LIMIT:
        if len(result) % 5 == 4 and r_idx < len(rss_items):
            result.append(rss_items[r_idx])
            r_idx += 1
        elif questions_since_wiki >= 3 and w_idx < len(wiki_items):
            result.append(wiki_items[w_idx])
            w_idx += 1
            questions_since_wiki = 0
        elif q_idx < len(question_cards):
            result.append(question_cards[q_idx])
            q_idx += 1
            questions_since_wiki += 1
        elif w_idx < len(wiki_items):
            result.append(wiki_items[w_idx])
            w_idx += 1
        elif r_idx < len(rss_items):
            result.append(rss_items[r_idx])
            r_idx += 1
        else:
            break
    return result[:FEED_LIMIT]
