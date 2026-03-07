"""Wikipedia feed cards: interest-based (category) and project-based (keyword)."""
import json
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Request

from backend.db.database import get_connection
from backend.models import WikipediaCardOut, WikiInterestAnswerSubmit
from backend.services.wikipedia_service import (
    extract_project_keywords,
    fetch_wikipedia_summary,
)
from backend.services.wikipedia_category_service import (
    DRILLDOWN_READ_THRESHOLD,
    SUBCATEGORY_OPTIONS_COUNT,
    random_articles_from_category,
    strip_category_prefix,
    top_subcategories_by_size,
)

router = APIRouter(prefix="/wikipedia", tags=["wikipedia"])

DEFAULT_USER_ID = "default_user"
PROJECT_MAX_CARDS = 3
EXCLUDE_DAYS = 7
# Caps to keep GET /feed response time bounded (avoid timeout from many sequential Wikipedia API calls)
MAX_INTEREST_CATEGORIES_PER_REQUEST = 2
MAX_ARTICLES_PER_INTEREST_CATEGORY = 1
MAX_NEW_WIKI_QUESTIONS_PER_REQUEST = 4


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_interest_categories(conn) -> list[str]:
    """Return stored Wikipedia category titles from user_interests."""
    row = conn.execute(
        "SELECT interests FROM user_interests WHERE id = ?", (DEFAULT_USER_ID,)
    ).fetchone()
    if not row:
        return []
    try:
        return json.loads(row["interests"])
    except (json.JSONDecodeError, TypeError):
        return []


def _ensure_category_prefix(cat: str) -> str:
    """Ensure category is in Wikipedia form 'Category:Name' for API calls."""
    if not cat or not str(cat).strip():
        return cat
    s = str(cat).strip()
    if s.startswith("Category:"):
        return s
    return f"Category:{s.replace(' ', '_')}"


def _get_active_categories(conn) -> list[str]:
    """Build full set of active categories: top-level interests + answered subcategories."""
    top_level = [_ensure_category_prefix(c) for c in _get_interest_categories(conn)]

    answered_rows = conn.execute(
        """SELECT a.selected_options FROM wiki_interest_answers a
           JOIN wiki_interest_cards c ON a.card_id = c.id"""
    ).fetchall()
    selected = set()
    for r in answered_rows:
        try:
            opts = json.loads(r["selected_options"])
            if isinstance(opts, list):
                selected.update(opts)
        except (json.JSONDecodeError, TypeError):
            pass

    selected_normalized = [_ensure_category_prefix(c) for c in selected]
    categories = list(dict.fromkeys(top_level + selected_normalized))
    return categories


def _get_shown_titles(conn) -> set[str]:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=EXCLUDE_DAYS)).isoformat()
    return {
        r["article_title"]
        for r in conn.execute(
            "SELECT article_title FROM wikipedia_shown WHERE shown_at > ?", (cutoff,)
        ).fetchall()
    }


def _record_shown(conn, card_id: str, title: str, now: str):
    conn.execute(
        "INSERT INTO wikipedia_shown (id, article_title, shown_at) VALUES (?, ?, ?)",
        (card_id, title, now),
    )


def _increment_category_read(conn, category_title: str):
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """INSERT INTO wiki_category_reads (user_id, category_title, read_count, updated_at)
           VALUES (?, ?, 1, ?)
           ON CONFLICT(user_id, category_title) DO UPDATE SET
             read_count = read_count + 1,
             updated_at = excluded.updated_at""",
        (DEFAULT_USER_ID, category_title, now),
    )


def _categories_needing_drilldown(conn) -> list[str]:
    """Categories that hit the read threshold but don't yet have an unanswered drilldown card."""
    rows = conn.execute(
        """SELECT category_title, read_count FROM wiki_category_reads
           WHERE user_id = ? AND read_count >= ?""",
        (DEFAULT_USER_ID, DRILLDOWN_READ_THRESHOLD),
    ).fetchall()
    candidates = [r["category_title"] for r in rows]

    already_have = set()
    for r in conn.execute(
        "SELECT parent_category FROM wiki_interest_cards WHERE status IN ('unanswered', 'answered')"
    ).fetchall():
        already_have.add(r["parent_category"])

    return [c for c in candidates if c not in already_have]


# ---------------------------------------------------------------------------
# Interest-based Wikipedia article cards (no cap on count)
# ---------------------------------------------------------------------------

def get_interest_wikipedia_cards(conn) -> list[WikipediaCardOut]:
    """Build Wikipedia article cards from interest categories (unlimited count)."""
    categories = _get_active_categories(conn)
    if not categories:
        return []

    shown_titles = _get_shown_titles(conn)
    seen_titles = set(shown_titles)
    cards: list[WikipediaCardOut] = []
    now = datetime.now(timezone.utc).isoformat()

    for cat in categories[:MAX_INTEREST_CATEGORIES_PER_REQUEST]:
        articles = random_articles_from_category(cat, count=MAX_ARTICLES_PER_INTEREST_CATEGORY, exclude_titles=seen_titles)
        for article in articles:
            title = article["title"]
            if title in seen_titles:
                continue
            seen_titles.add(title)
            card_id = str(uuid.uuid4())
            cards.append(
                WikipediaCardOut(
                    id=card_id,
                    type="wikipedia",
                    title=title,
                    extract=article["extract"],
                    url=article["url"],
                    source_term=strip_category_prefix(cat),
                    thumbnail_url=article.get("thumbnail_url"),
                )
            )
            _record_shown(conn, card_id, title, now)
            _increment_category_read(conn, cat)

    conn.commit()
    return cards


# ---------------------------------------------------------------------------
# Project-based Wikipedia article cards (capped, unchanged logic)
# ---------------------------------------------------------------------------

def _ensure_project_keywords(conn, project_id: str, title: str, description: str, api_key: str | None) -> list[str]:
    row = conn.execute(
        "SELECT keywords, description_snapshot FROM project_keywords WHERE project_id = ?",
        (project_id,),
    ).fetchone()
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


def get_project_wikipedia_cards(api_key: str | None) -> list[WikipediaCardOut]:
    """Build up to PROJECT_MAX_CARDS Wikipedia cards from project keywords."""
    conn = get_connection()
    terms = []
    for row in conn.execute("SELECT id, title, description FROM projects").fetchall():
        kw = _ensure_project_keywords(conn, row["id"], row["title"], row["description"], api_key)
        for t in kw:
            if isinstance(t, str) and t.strip():
                terms.append(t.strip())

    shown_titles = _get_shown_titles(conn)
    seen_titles = set(shown_titles)
    cards: list[WikipediaCardOut] = []
    now = datetime.now(timezone.utc).isoformat()

    for term in terms:
        if len(cards) >= PROJECT_MAX_CARDS:
            break
        summary = fetch_wikipedia_summary(term)
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
                source_term=term,
                thumbnail_url=summary.get("thumbnail_url"),
            )
        )
        _record_shown(conn, card_id, title, now)

    conn.commit()
    conn.close()
    return cards


# ---------------------------------------------------------------------------
# Wiki interest question cards
# ---------------------------------------------------------------------------

def generate_wiki_interest_question(conn, parent_category: str) -> dict | None:
    """Create a wiki interest question card for a parent category. Returns card dict or None."""
    subcats = top_subcategories_by_size(parent_category, SUBCATEGORY_OPTIONS_COUNT)
    if not subcats:
        return None

    card_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    display_options = [strip_category_prefix(s) for s in subcats]

    conn.execute(
        """INSERT INTO wiki_interest_cards (id, parent_category, options, status, created_at)
           VALUES (?, ?, ?, 'unanswered', ?)""",
        (card_id, parent_category, json.dumps(subcats), now),
    )
    conn.commit()

    return {
        "id": card_id,
        "parent_category": parent_category,
        "options_full": subcats,
        "options_display": display_options,
    }


def get_pending_wiki_interest_questions(conn) -> list[dict]:
    """Return unanswered wiki interest question cards."""
    rows = conn.execute(
        "SELECT id, parent_category, options, created_at FROM wiki_interest_cards WHERE status = 'unanswered' ORDER BY created_at ASC"
    ).fetchall()
    result = []
    for r in rows:
        try:
            full_opts = json.loads(r["options"])
        except (json.JSONDecodeError, TypeError):
            full_opts = []
        result.append({
            "id": r["id"],
            "parent_category": r["parent_category"],
            "options_full": full_opts,
            "options_display": [strip_category_prefix(o) for o in full_opts],
        })
    return result


def ensure_wiki_interest_questions(conn) -> list[dict]:
    """Make sure there's at least one unanswered wiki interest question per top-level interest.

    Also creates drilldown questions for categories that exceeded the read threshold.
    Returns the list of unanswered questions.
    """
    pending = get_pending_wiki_interest_questions(conn)
    pending_parents = {q["parent_category"] for q in pending}

    interests = [_ensure_category_prefix(c) for c in _get_interest_categories(conn)]
    new_created = 0
    for cat in interests:
        if new_created >= MAX_NEW_WIKI_QUESTIONS_PER_REQUEST:
            break
        if cat not in pending_parents:
            q = generate_wiki_interest_question(conn, cat)
            if q:
                pending.append(q)
                pending_parents.add(cat)
                new_created += 1

    for cat in _categories_needing_drilldown(conn):
        if new_created >= MAX_NEW_WIKI_QUESTIONS_PER_REQUEST:
            break
        cat = _ensure_category_prefix(cat)
        if cat not in pending_parents:
            q = generate_wiki_interest_question(conn, cat)
            if q:
                pending.append(q)
                pending_parents.add(cat)
                new_created += 1

    return pending


# ---------------------------------------------------------------------------
# Combined function for feed.py
# ---------------------------------------------------------------------------

def get_wikipedia_cards_for_feed(api_key: str | None) -> list[WikipediaCardOut]:
    """Build Wikipedia article cards: interest-based + project-based."""
    conn = get_connection()
    interest_cards = get_interest_wikipedia_cards(conn)
    conn.close()
    project_cards = get_project_wikipedia_cards(api_key)

    seen = {c.title for c in interest_cards}
    for pc in project_cards:
        if pc.title not in seen:
            interest_cards.append(pc)
            seen.add(pc.title)

    return interest_cards


# ---------------------------------------------------------------------------
# REST endpoints
# ---------------------------------------------------------------------------

@router.get("/cards", response_model=list[WikipediaCardOut])
def get_wikipedia_cards(request: Request):
    api_key = (request.headers.get("X-Anthropic-Key") or "").strip() or None
    return get_wikipedia_cards_for_feed(api_key)


@router.post("/interest-questions/{card_id}/answer")
def answer_wiki_interest_question(card_id: str, body: WikiInterestAnswerSubmit):
    conn = get_connection()
    row = conn.execute(
        "SELECT id, options, status FROM wiki_interest_cards WHERE id = ?", (card_id,)
    ).fetchone()
    if not row:
        conn.close()
        return {"ok": False, "error": "not found"}
    if row["status"] != "unanswered":
        conn.close()
        return {"ok": False, "error": "already processed"}

    try:
        valid_opts = json.loads(row["options"])
    except (json.JSONDecodeError, TypeError):
        valid_opts = []

    display_to_full = {strip_category_prefix(o): o for o in valid_opts}
    resolved = []
    for sel in body.selected_options:
        if sel in display_to_full:
            resolved.append(display_to_full[sel])
        elif sel in valid_opts:
            resolved.append(sel)

    if not resolved:
        conn.close()
        return {"ok": False, "error": "no valid options selected"}

    now = datetime.now(timezone.utc).isoformat()
    answer_id = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO wiki_interest_answers (id, card_id, selected_options, created_at) VALUES (?, ?, ?, ?)",
        (answer_id, card_id, json.dumps(resolved), now),
    )
    conn.execute(
        "UPDATE wiki_interest_cards SET status = 'answered' WHERE id = ?", (card_id,)
    )
    conn.commit()
    conn.close()
    return {"ok": True}


@router.patch("/interest-questions/{card_id}/skip")
def skip_wiki_interest_question(card_id: str):
    conn = get_connection()
    row = conn.execute(
        "SELECT id, parent_category FROM wiki_interest_cards WHERE id = ?", (card_id,)
    ).fetchone()
    if not row:
        conn.close()
        return {"ok": False, "error": "not found"}
    conn.execute(
        "UPDATE wiki_interest_cards SET status = 'skipped' WHERE id = ?", (card_id,)
    )
    conn.commit()

    generate_wiki_interest_question(conn, row["parent_category"])
    conn.close()
    return {"ok": True}
