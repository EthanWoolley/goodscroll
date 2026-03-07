"""Wikipedia feed cards: interest-based (category) and project-based (keyword)."""
import json
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Request
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import (
    Project,
    ProjectKeyword,
    UserInterest,
    WikiCategoryRead,
    WikiInterestAnswer,
    WikiInterestCard,
    WikipediaShown,
)
from backend.db.session import get_db
from backend.models import WikiInterestAnswerSubmit, WikipediaCardOut
from backend.services.wikipedia_category_service import (
    DRILLDOWN_READ_THRESHOLD,
    SUBCATEGORY_OPTIONS_COUNT,
    random_articles_from_category,
    strip_category_prefix,
    top_subcategories_by_size,
)
from backend.services.wikipedia_service import (
    extract_project_keywords,
    fetch_wikipedia_summary,
)

router = APIRouter(prefix="/wikipedia", tags=["wikipedia"])

DEFAULT_USER_ID = "default_user"
PROJECT_MAX_CARDS = 3
EXCLUDE_DAYS = 7
MAX_INTEREST_CATEGORIES_PER_REQUEST = 2
MAX_ARTICLES_PER_INTEREST_CATEGORY = 1
MAX_NEW_WIKI_QUESTIONS_PER_REQUEST = 4


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_interest_categories(db: AsyncSession) -> list[str]:
    result = await db.execute(
        select(UserInterest.interests).where(UserInterest.id == DEFAULT_USER_ID)
    )
    interests = result.scalar_one_or_none()
    if not interests:
        return []
    return list(interests)


def _ensure_category_prefix(cat: str) -> str:
    if not cat or not str(cat).strip():
        return cat
    s = str(cat).strip()
    if s.startswith("Category:"):
        return s
    return f"Category:{s.replace(' ', '_')}"


async def _get_active_categories(db: AsyncSession) -> list[str]:
    top_level = [_ensure_category_prefix(c) for c in await _get_interest_categories(db)]

    result = await db.execute(
        select(WikiInterestAnswer.selected_options)
        .join(WikiInterestCard, WikiInterestAnswer.card_id == WikiInterestCard.id)
    )
    answered_rows = result.all()
    selected = set()
    for r in answered_rows:
        opts = r.selected_options
        if isinstance(opts, list):
            selected.update(opts)

    selected_normalized = [_ensure_category_prefix(c) for c in selected]
    categories = list(dict.fromkeys(top_level + selected_normalized))
    return categories


async def _get_shown_titles(db: AsyncSession) -> set[str]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=EXCLUDE_DAYS)
    result = await db.execute(
        select(WikipediaShown.article_title).where(WikipediaShown.shown_at > cutoff)
    )
    return {r.article_title for r in result.all()}


async def _record_shown(db: AsyncSession, card_id: uuid.UUID, title: str, now: datetime):
    db.add(WikipediaShown(id=card_id, article_title=title, shown_at=now))


async def _increment_category_read(db: AsyncSession, category_title: str):
    now = datetime.now(timezone.utc)
    result = await db.execute(
        select(WikiCategoryRead).where(
            WikiCategoryRead.user_id == DEFAULT_USER_ID,
            WikiCategoryRead.category_title == category_title,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        await db.execute(
            update(WikiCategoryRead)
            .where(
                WikiCategoryRead.user_id == DEFAULT_USER_ID,
                WikiCategoryRead.category_title == category_title,
            )
            .values(read_count=WikiCategoryRead.read_count + 1, updated_at=now)
        )
    else:
        db.add(
            WikiCategoryRead(
                user_id=DEFAULT_USER_ID,
                category_title=category_title,
                read_count=1,
                updated_at=now,
            )
        )


async def _categories_needing_drilldown(db: AsyncSession) -> list[str]:
    result = await db.execute(
        select(WikiCategoryRead.category_title, WikiCategoryRead.read_count).where(
            WikiCategoryRead.user_id == DEFAULT_USER_ID,
            WikiCategoryRead.read_count >= DRILLDOWN_READ_THRESHOLD,
        )
    )
    candidates = [r.category_title for r in result.all()]

    result = await db.execute(
        select(WikiInterestCard.parent_category).where(
            WikiInterestCard.status.in_(["unanswered", "answered"])
        )
    )
    already_have = {r.parent_category for r in result.all()}

    return [c for c in candidates if c not in already_have]


# ---------------------------------------------------------------------------
# Interest-based Wikipedia article cards
# ---------------------------------------------------------------------------

async def get_interest_wikipedia_cards(db: AsyncSession) -> list[WikipediaCardOut]:
    categories = await _get_active_categories(db)
    if not categories:
        return []

    shown_titles = await _get_shown_titles(db)
    seen_titles = set(shown_titles)
    cards: list[WikipediaCardOut] = []
    now = datetime.now(timezone.utc)

    for cat in categories[:MAX_INTEREST_CATEGORIES_PER_REQUEST]:
        articles = random_articles_from_category(cat, count=MAX_ARTICLES_PER_INTEREST_CATEGORY, exclude_titles=seen_titles)
        for article in articles:
            title = article["title"]
            if title in seen_titles:
                continue
            seen_titles.add(title)
            card_id = uuid.uuid4()
            cards.append(
                WikipediaCardOut(
                    id=str(card_id),
                    type="wikipedia",
                    title=title,
                    extract=article["extract"],
                    url=article["url"],
                    source_term=strip_category_prefix(cat),
                    thumbnail_url=article.get("thumbnail_url"),
                )
            )
            await _record_shown(db, card_id, title, now)
            await _increment_category_read(db, cat)

    await db.commit()
    return cards


# ---------------------------------------------------------------------------
# Project-based Wikipedia article cards
# ---------------------------------------------------------------------------

async def _ensure_project_keywords(
    db: AsyncSession,
    project_id: uuid.UUID,
    title: str,
    description: str,
    api_key: str | None,
) -> list[str]:
    result = await db.execute(
        select(ProjectKeyword).where(ProjectKeyword.project_id == project_id)
    )
    row = result.scalar_one_or_none()
    snapshot = (title or "") + "\n" + (description or "")
    if row and row.description_snapshot == snapshot:
        return list(row.keywords)

    keywords = extract_project_keywords(title, description, api_key)
    now = datetime.now(timezone.utc)
    if row:
        await db.execute(
            update(ProjectKeyword)
            .where(ProjectKeyword.project_id == project_id)
            .values(keywords=keywords, generated_at=now, description_snapshot=snapshot)
        )
    else:
        db.add(
            ProjectKeyword(
                project_id=project_id,
                keywords=keywords,
                generated_at=now,
                description_snapshot=snapshot,
            )
        )
    await db.commit()
    return keywords


async def get_project_wikipedia_cards(
    db: AsyncSession, api_key: str | None
) -> list[WikipediaCardOut]:
    result = await db.execute(select(Project.id, Project.title, Project.description))
    projects = result.all()

    terms = []
    for row in projects:
        kw = await _ensure_project_keywords(db, row.id, row.title, row.description, api_key)
        for t in kw:
            if isinstance(t, str) and t.strip():
                terms.append(t.strip())

    shown_titles = await _get_shown_titles(db)
    seen_titles = set(shown_titles)
    cards: list[WikipediaCardOut] = []
    now = datetime.now(timezone.utc)

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
        card_id = uuid.uuid4()
        cards.append(
            WikipediaCardOut(
                id=str(card_id),
                type="wikipedia",
                title=title,
                extract=summary["extract"],
                url=summary["url"],
                source_term=term,
                thumbnail_url=summary.get("thumbnail_url"),
            )
        )
        await _record_shown(db, card_id, title, now)

    await db.commit()
    return cards


# ---------------------------------------------------------------------------
# Wiki interest question cards
# ---------------------------------------------------------------------------

async def generate_wiki_interest_question(
    db: AsyncSession, parent_category: str
) -> dict | None:
    subcats = top_subcategories_by_size(parent_category, SUBCATEGORY_OPTIONS_COUNT)
    if not subcats:
        return None

    card_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    display_options = [strip_category_prefix(s) for s in subcats]

    db.add(
        WikiInterestCard(
            id=card_id,
            parent_category=parent_category,
            options=subcats,
            status="unanswered",
            created_at=now,
        )
    )
    await db.commit()

    return {
        "id": str(card_id),
        "parent_category": parent_category,
        "options_full": subcats,
        "options_display": display_options,
    }


async def get_pending_wiki_interest_questions(db: AsyncSession) -> list[dict]:
    result = await db.execute(
        select(WikiInterestCard)
        .where(WikiInterestCard.status == "unanswered")
        .order_by(WikiInterestCard.created_at.asc())
    )
    rows = result.scalars().all()
    output = []
    for r in rows:
        full_opts = list(r.options) if r.options else []
        output.append({
            "id": str(r.id),
            "parent_category": r.parent_category,
            "options_full": full_opts,
            "options_display": [strip_category_prefix(o) for o in full_opts],
        })
    return output


async def ensure_wiki_interest_questions(db: AsyncSession) -> list[dict]:
    pending = await get_pending_wiki_interest_questions(db)
    pending_parents = {q["parent_category"] for q in pending}

    interests = [_ensure_category_prefix(c) for c in await _get_interest_categories(db)]
    new_created = 0
    for cat in interests:
        if new_created >= MAX_NEW_WIKI_QUESTIONS_PER_REQUEST:
            break
        if cat not in pending_parents:
            q = await generate_wiki_interest_question(db, cat)
            if q:
                pending.append(q)
                pending_parents.add(cat)
                new_created += 1

    for cat in await _categories_needing_drilldown(db):
        if new_created >= MAX_NEW_WIKI_QUESTIONS_PER_REQUEST:
            break
        cat = _ensure_category_prefix(cat)
        if cat not in pending_parents:
            q = await generate_wiki_interest_question(db, cat)
            if q:
                pending.append(q)
                pending_parents.add(cat)
                new_created += 1

    return pending


# ---------------------------------------------------------------------------
# Combined function for feed.py
# ---------------------------------------------------------------------------

async def get_wikipedia_cards_for_feed(
    db: AsyncSession, api_key: str | None
) -> list[WikipediaCardOut]:
    interest_cards = await get_interest_wikipedia_cards(db)
    project_cards = await get_project_wikipedia_cards(db, api_key)

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
async def get_wikipedia_cards(
    request: Request, db: AsyncSession = Depends(get_db)
):
    api_key = (request.headers.get("X-Anthropic-Key") or "").strip() or None
    return await get_wikipedia_cards_for_feed(db, api_key)


@router.post("/interest-questions/{card_id}/answer")
async def answer_wiki_interest_question(
    card_id: str, body: WikiInterestAnswerSubmit, db: AsyncSession = Depends(get_db)
):
    cid = uuid.UUID(card_id)
    result = await db.execute(
        select(WikiInterestCard).where(WikiInterestCard.id == cid)
    )
    row = result.scalar_one_or_none()
    if not row:
        return {"ok": False, "error": "not found"}
    if row.status != "unanswered":
        return {"ok": False, "error": "already processed"}

    valid_opts = list(row.options) if row.options else []
    display_to_full = {strip_category_prefix(o): o for o in valid_opts}
    resolved = []
    for sel in body.selected_options:
        if sel in display_to_full:
            resolved.append(display_to_full[sel])
        elif sel in valid_opts:
            resolved.append(sel)

    if not resolved:
        return {"ok": False, "error": "no valid options selected"}

    now = datetime.now(timezone.utc)
    db.add(
        WikiInterestAnswer(
            id=uuid.uuid4(),
            card_id=cid,
            selected_options=resolved,
            created_at=now,
        )
    )
    await db.execute(
        update(WikiInterestCard).where(WikiInterestCard.id == cid).values(status="answered")
    )
    await db.commit()
    return {"ok": True}


@router.patch("/interest-questions/{card_id}/skip")
async def skip_wiki_interest_question(
    card_id: str, db: AsyncSession = Depends(get_db)
):
    cid = uuid.UUID(card_id)
    result = await db.execute(
        select(WikiInterestCard.id, WikiInterestCard.parent_category).where(
            WikiInterestCard.id == cid
        )
    )
    row = result.first()
    if not row:
        return {"ok": False, "error": "not found"}

    await db.execute(
        update(WikiInterestCard).where(WikiInterestCard.id == cid).values(status="skipped")
    )
    await db.commit()

    await generate_wiki_interest_question(db, row.parent_category)
    return {"ok": True}
