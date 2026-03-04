import json
import traceback
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Request

from backend.db.database import get_connection
from backend.models import WikipediaCardOut
from backend.services.wikipedia_service import (
    extract_project_keywords,
    fetch_wikipedia_summary,
)

router = APIRouter(prefix="/wikipedia", tags=["wikipedia"])

DEFAULT_USER_ID = "default_user"
MAX_CARDS = 10
EXCLUDE_DAYS = 7


def _get_interests(conn) -> list[str]:
    row = conn.execute(
        "SELECT interests FROM user_interests WHERE id = ?", (DEFAULT_USER_ID,)
    ).fetchone()
    if not row:
        return []
    try:
        return json.loads(row["interests"])
    except (json.JSONDecodeError, TypeError):
        return []


def _ensure_project_keywords(conn, project_id: str, title: str, description: str, api_key: str | None) -> list[str]:
    # #region agent log
    try:
        row = conn.execute(
            "SELECT keywords, description_snapshot FROM project_keywords WHERE project_id = ?",
            (project_id,),
        ).fetchone()
    except Exception as e:
        try:
            with open("/Users/ethanwoolley/Local Work/Good scroll/goodscroll/.cursor/debug-cc8682.log", "a") as f:
                f.write(json.dumps({"sessionId":"cc8682","hypothesisId":"B","location":"wikipedia.py:_ensure_project_keywords:select","message":"project_keywords select failed","data":{"error":str(e),"tb":traceback.format_exc()},"timestamp":__import__("time").time()*1000}) + "\n")
        except Exception:
            pass
        raise
    # #endregion
    now = datetime.now(timezone.utc).isoformat()
    snapshot = (title or "") + "\n" + (description or "")
    if row and row["description_snapshot"] == snapshot:
        try:
            return json.loads(row["keywords"])
        except (json.JSONDecodeError, TypeError):
            pass
    keywords = extract_project_keywords(title, description, api_key)
    conn.execute(
        """INSERT INTO project_keywords (project_id, keywords, generated_at, description_snapshot)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(project_id) DO UPDATE SET
             keywords = excluded.keywords,
             generated_at = excluded.generated_at,
             description_snapshot = excluded.description_snapshot""",
        (project_id, json.dumps(keywords), now, snapshot),
    )
    conn.commit()
    return keywords


def get_wikipedia_cards_for_feed(api_key: str | None) -> list[WikipediaCardOut]:
    """Build up to MAX_CARDS Wikipedia cards (for feed assembly)."""
    conn = get_connection()

    interests = _get_interests(conn)
    terms_with_source = [(t, t) for t in interests if isinstance(t, str) and t.strip()]

    for row in conn.execute("SELECT id, title, description FROM projects").fetchall():
        kw = _ensure_project_keywords(
            conn, row["id"], row["title"], row["description"], api_key
        )
        for t in kw:
            if isinstance(t, str) and t.strip():
                terms_with_source.append((t.strip(), t.strip()))

    cutoff = (datetime.now(timezone.utc) - timedelta(days=EXCLUDE_DAYS)).isoformat()
    shown_titles = {
        r["article_title"]
        for r in conn.execute(
            "SELECT article_title FROM wikipedia_shown WHERE shown_at > ?", (cutoff,)
        ).fetchall()
    }

    cards = []
    now = datetime.now(timezone.utc).isoformat()
    seen_titles = set(shown_titles)

    for source_term, _ in terms_with_source:
        if len(cards) >= MAX_CARDS:
            break
        summary = fetch_wikipedia_summary(source_term)
        if not summary:
            continue
        title = summary["title"]
        if title in seen_titles:
            continue
        seen_titles.add(title)
        card_id = str(uuid.uuid4())
        cards.append(
            WikipediaCardOut(
                id=card_id,
                type="wikipedia",
                title=title,
                extract=summary["extract"],
                url=summary["url"],
                source_term=source_term,
                thumbnail_url=summary.get("thumbnail_url"),
            )
        )
        conn.execute(
            "INSERT INTO wikipedia_shown (id, article_title, shown_at) VALUES (?, ?, ?)",
            (card_id, title, now),
        )

    conn.commit()
    conn.close()
    return cards


@router.get("/cards", response_model=list[WikipediaCardOut])
def get_wikipedia_cards(request: Request):
    api_key = (request.headers.get("X-Anthropic-Key") or "").strip() or None
    return get_wikipedia_cards_for_feed(api_key)
