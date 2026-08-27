"""Route handlers and helpers in backend.routes.wikipedia.

The two Wikipedia services and the keyword extractor are patched at the names
wikipedia.py imported them under, so nothing here touches the Wikipedia API or
Anthropic.
"""

import uuid

from backend.db.models import (
    ProjectKeyword,
    WikiCategoryRead,
    WikiInterestAnswer,
    WikiInterestCard,
    WikipediaShown,
)
from backend.routes import wikipedia as wiki_route
from backend.routes.wikipedia import _ensure_category_prefix
from backend.tests.support import FIXED_NOW, FakeResult, FakeSession, row

CARD_ID = uuid.UUID("44444444-4444-4444-4444-444444444444")
PROJECT_ID = uuid.UUID("55555555-5555-5555-5555-555555555555")

ARTICLE = {
    "title": "Kubernetes",
    "extract": "An orchestration system.",
    "url": "https://en.m.wikipedia.org/wiki/Kubernetes",
    "thumbnail_url": "https://example.com/k8s.png",
}


def patch_services(
    monkeypatch,
    articles=(),
    summary=None,
    keywords=(),
    subcategories=(),
):
    monkeypatch.setattr(
        wiki_route, "random_articles_from_category", lambda *a, **kw: list(articles)
    )
    monkeypatch.setattr(wiki_route, "fetch_wikipedia_summary", lambda term: summary)
    monkeypatch.setattr(
        wiki_route, "extract_project_keywords", lambda *a, **kw: list(keywords)
    )
    monkeypatch.setattr(
        wiki_route, "top_subcategories_by_size", lambda *a, **kw: list(subcategories)
    )


# ---------------------------------------------------------------------------
# _ensure_category_prefix
# ---------------------------------------------------------------------------

def test_ensure_category_prefix_leaves_a_prefixed_title_alone():
    assert _ensure_category_prefix("Category:Technology") == "Category:Technology"


def test_ensure_category_prefix_adds_the_prefix_and_underscores_spaces():
    assert _ensure_category_prefix("Outer space") == "Category:Outer_space"


def test_ensure_category_prefix_passes_blank_input_straight_through():
    assert _ensure_category_prefix("") == ""
    assert _ensure_category_prefix("   ") == "   "


# ---------------------------------------------------------------------------
# GET /wikipedia/cards
# ---------------------------------------------------------------------------

def test_get_cards_with_no_interests_and_no_projects_is_empty(client_factory, monkeypatch):
    patch_services(monkeypatch)
    session = FakeSession(
        [
            FakeResult(scalar=None),  # interests
            FakeResult(rows=[]),  # answered interest questions
            FakeResult(rows=[]),  # projects
            FakeResult(rows=[]),  # shown titles (project phase)
        ]
    )

    resp = client_factory(session).get("/wikipedia/cards")

    assert resp.status_code == 200
    assert resp.json() == []


def test_get_cards_builds_an_interest_card_and_records_it(client_factory, monkeypatch):
    patch_services(monkeypatch, articles=[ARTICLE])
    session = FakeSession(
        [
            FakeResult(scalar=["Category:Technology"]),  # interests
            FakeResult(rows=[]),  # answered interest questions
            FakeResult(rows=[]),  # shown titles
            FakeResult(scalar=None),  # category read count
            FakeResult(rows=[]),  # projects
            FakeResult(rows=[]),  # shown titles (project phase)
        ]
    )

    resp = client_factory(session).get("/wikipedia/cards")

    body = resp.json()
    assert len(body) == 1
    assert body[0]["title"] == "Kubernetes"
    assert body[0]["source_term"] == "Technology"
    assert body[0]["thumbnail_url"] == "https://example.com/k8s.png"
    assert [s.article_title for s in session.added_of(WikipediaShown)] == ["Kubernetes"]
    assert session.added_of(WikiCategoryRead)[0].read_count == 1


def test_get_cards_increments_an_existing_category_read_count(client_factory, monkeypatch):
    patch_services(monkeypatch, articles=[ARTICLE])
    existing = WikiCategoryRead(
        user_id="default_user",
        category_title="Category:Technology",
        read_count=2,
        updated_at=FIXED_NOW,
    )
    session = FakeSession(
        [
            FakeResult(scalar=["Category:Technology"]),  # interests
            FakeResult(rows=[]),  # answered interest questions
            FakeResult(rows=[]),  # shown titles
            FakeResult(scalar=existing),  # category read count
            FakeResult(),  # the increment
            FakeResult(rows=[]),  # projects
            FakeResult(rows=[]),  # shown titles (project phase)
        ]
    )

    client_factory(session).get("/wikipedia/cards")

    assert session.added_of(WikiCategoryRead) == []


def test_get_cards_skips_articles_already_shown(client_factory, monkeypatch):
    patch_services(monkeypatch, articles=[ARTICLE])
    session = FakeSession(
        [
            FakeResult(scalar=["Category:Technology"]),  # interests
            FakeResult(rows=[]),  # answered interest questions
            FakeResult(rows=[row(article_title="Kubernetes")]),  # shown titles
            FakeResult(rows=[]),  # projects
            FakeResult(rows=[]),  # shown titles (project phase)
        ]
    )

    assert client_factory(session).get("/wikipedia/cards").json() == []


def test_get_cards_includes_categories_selected_in_interest_answers(
    client_factory, monkeypatch
):
    """Drill-down selections are appended to the top-level interest categories."""
    seen = []

    def capture(cat, **kwargs):
        seen.append(cat)
        return []

    monkeypatch.setattr(wiki_route, "random_articles_from_category", capture)
    monkeypatch.setattr(wiki_route, "fetch_wikipedia_summary", lambda term: None)
    monkeypatch.setattr(wiki_route, "extract_project_keywords", lambda *a, **kw: [])
    session = FakeSession(
        [
            FakeResult(scalar=["Category:Technology"]),  # interests
            FakeResult(rows=[row(selected_options=["Category:Databases"])]),
            FakeResult(rows=[]),  # shown titles
            FakeResult(rows=[]),  # projects
            FakeResult(rows=[]),  # shown titles (project phase)
        ]
    )

    client_factory(session).get("/wikipedia/cards")

    assert seen == ["Category:Technology", "Category:Databases"]


def test_get_cards_builds_a_project_card_from_extracted_keywords(
    client_factory, monkeypatch
):
    patch_services(monkeypatch, summary=ARTICLE, keywords=["Kubernetes"])
    session = FakeSession(
        [
            FakeResult(scalar=None),
            FakeResult(rows=[]),
            FakeResult(rows=[row(id=PROJECT_ID, title="Infra", description="k8s work")]),
            FakeResult(scalar=None),
            FakeResult(rows=[]),
        ]
    )

    body = client_factory(session).get("/wikipedia/cards").json()

    assert len(body) == 1
    assert body[0]["source_term"] == "Kubernetes"
    stored = session.added_of(ProjectKeyword)[0]
    assert stored.keywords == ["Kubernetes"]
    assert stored.description_snapshot == "Infra\nk8s work"


def test_get_cards_reuses_cached_keywords_when_the_snapshot_matches(
    client_factory, monkeypatch
):
    """A matching snapshot must not re-run the Anthropic keyword extraction."""

    def should_not_run(*args, **kwargs):
        raise AssertionError("keywords should have been reused from the cache")

    monkeypatch.setattr(wiki_route, "random_articles_from_category", lambda *a, **kw: [])
    monkeypatch.setattr(wiki_route, "fetch_wikipedia_summary", lambda term: ARTICLE)
    monkeypatch.setattr(wiki_route, "extract_project_keywords", should_not_run)
    cached = ProjectKeyword(
        project_id=PROJECT_ID,
        keywords=["Kubernetes"],
        generated_at=FIXED_NOW,
        description_snapshot="Infra\nk8s work",
    )
    session = FakeSession(
        [
            FakeResult(scalar=None),
            FakeResult(rows=[]),
            FakeResult(rows=[row(id=PROJECT_ID, title="Infra", description="k8s work")]),
            FakeResult(scalar=cached),
            FakeResult(rows=[]),
        ]
    )

    body = client_factory(session).get("/wikipedia/cards").json()

    assert body[0]["title"] == "Kubernetes"


def test_get_cards_drops_a_keyword_with_no_wikipedia_summary(client_factory, monkeypatch):
    patch_services(monkeypatch, summary=None, keywords=["Nonexistent topic"])
    session = FakeSession(
        [
            FakeResult(scalar=None),
            FakeResult(rows=[]),
            FakeResult(rows=[row(id=PROJECT_ID, title="Infra", description="k8s work")]),
            FakeResult(scalar=None),
            FakeResult(rows=[]),
        ]
    )

    assert client_factory(session).get("/wikipedia/cards").json() == []


def test_get_cards_deduplicates_a_project_card_against_an_interest_card(
    client_factory, monkeypatch
):
    patch_services(monkeypatch, articles=[ARTICLE], summary=ARTICLE, keywords=["Kubernetes"])
    session = FakeSession(
        [
            FakeResult(scalar=["Category:Technology"]),
            FakeResult(rows=[]),
            FakeResult(rows=[]),
            FakeResult(scalar=None),
            FakeResult(rows=[row(id=PROJECT_ID, title="Infra", description="k8s work")]),
            FakeResult(scalar=None),
            FakeResult(rows=[]),
        ]
    )

    body = client_factory(session).get("/wikipedia/cards").json()

    assert [c["title"] for c in body] == ["Kubernetes"]


# ---------------------------------------------------------------------------
# POST /wikipedia/interest-questions/{id}/answer
# ---------------------------------------------------------------------------

def test_answer_resolves_display_labels_back_to_full_titles(client_factory):
    card = WikiInterestCard(
        id=CARD_ID,
        parent_category="Category:Technology",
        options=["Category:Databases", "Category:Robotics"],
        status="unanswered",
        created_at=FIXED_NOW,
    )
    session = FakeSession([FakeResult(scalar=card), FakeResult()])

    resp = client_factory(session).post(
        f"/wikipedia/interest-questions/{CARD_ID}/answer",
        json={"selected_options": ["Databases"]},
    )

    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
    assert session.added_of(WikiInterestAnswer)[0].selected_options == ["Category:Databases"]


def test_answer_also_accepts_full_category_titles(client_factory):
    card = WikiInterestCard(
        id=CARD_ID,
        parent_category="Category:Technology",
        options=["Category:Databases"],
        status="unanswered",
        created_at=FIXED_NOW,
    )
    session = FakeSession([FakeResult(scalar=card), FakeResult()])

    client_factory(session).post(
        f"/wikipedia/interest-questions/{CARD_ID}/answer",
        json={"selected_options": ["Category:Databases"]},
    )

    assert session.added_of(WikiInterestAnswer)[0].selected_options == ["Category:Databases"]


def test_answer_for_an_unknown_card_reports_not_found_with_status_200(client_factory):
    """This endpoint signals failure in the body rather than the status code."""
    session = FakeSession([FakeResult(scalar=None)])

    resp = client_factory(session).post(
        f"/wikipedia/interest-questions/{CARD_ID}/answer",
        json={"selected_options": ["Databases"]},
    )

    assert resp.status_code == 200
    assert resp.json() == {"ok": False, "error": "not found"}


def test_answer_on_an_already_answered_card_is_rejected(client_factory):
    card = WikiInterestCard(
        id=CARD_ID,
        parent_category="Category:Technology",
        options=["Category:Databases"],
        status="answered",
        created_at=FIXED_NOW,
    )
    session = FakeSession([FakeResult(scalar=card)])

    resp = client_factory(session).post(
        f"/wikipedia/interest-questions/{CARD_ID}/answer",
        json={"selected_options": ["Databases"]},
    )

    assert resp.json() == {"ok": False, "error": "already processed"}
    assert session.added == []


def test_answer_with_no_recognised_option_is_rejected(client_factory):
    card = WikiInterestCard(
        id=CARD_ID,
        parent_category="Category:Technology",
        options=["Category:Databases"],
        status="unanswered",
        created_at=FIXED_NOW,
    )
    session = FakeSession([FakeResult(scalar=card)])

    resp = client_factory(session).post(
        f"/wikipedia/interest-questions/{CARD_ID}/answer",
        json={"selected_options": ["Something else entirely"]},
    )

    assert resp.json() == {"ok": False, "error": "no valid options selected"}
    assert session.added == []


def test_answer_without_the_field_is_422(client_factory):
    resp = client_factory(FakeSession([])).post(
        f"/wikipedia/interest-questions/{CARD_ID}/answer", json={}
    )

    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# PATCH /wikipedia/interest-questions/{id}/skip
# ---------------------------------------------------------------------------

def test_skip_marks_the_card_and_generates_a_replacement(client_factory, monkeypatch):
    patch_services(monkeypatch, subcategories=["Category:Databases", "Category:Robotics"])
    session = FakeSession(
        [
            FakeResult(rows=[row(id=CARD_ID, parent_category="Category:Technology")]),
            FakeResult(),
        ]
    )

    resp = client_factory(session).patch(f"/wikipedia/interest-questions/{CARD_ID}/skip")

    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
    replacement = session.added_of(WikiInterestCard)[0]
    assert replacement.parent_category == "Category:Technology"
    assert replacement.options == ["Category:Databases", "Category:Robotics"]


def test_skip_still_succeeds_when_no_replacement_can_be_built(client_factory, monkeypatch):
    """top_subcategories_by_size returning nothing means no new card, but still ok."""
    patch_services(monkeypatch, subcategories=[])
    session = FakeSession(
        [
            FakeResult(rows=[row(id=CARD_ID, parent_category="Category:Technology")]),
            FakeResult(),
        ]
    )

    resp = client_factory(session).patch(f"/wikipedia/interest-questions/{CARD_ID}/skip")

    assert resp.json() == {"ok": True}
    assert session.added_of(WikiInterestCard) == []


def test_skip_an_unknown_card_reports_not_found(client_factory):
    session = FakeSession([FakeResult(rows=[])])

    resp = client_factory(session).patch(f"/wikipedia/interest-questions/{CARD_ID}/skip")

    assert resp.json() == {"ok": False, "error": "not found"}
    assert session.commits == 0


# ---------------------------------------------------------------------------
# ensure_wiki_interest_questions, called by the feed
# ---------------------------------------------------------------------------

async def test_ensure_questions_returns_the_pending_ones_with_display_options(monkeypatch):
    patch_services(monkeypatch)
    pending = WikiInterestCard(
        id=CARD_ID,
        parent_category="Category:Technology",
        options=["Category:Databases"],
        status="unanswered",
        created_at=FIXED_NOW,
    )
    session = FakeSession(
        [
            FakeResult(rows=[pending]),  # pending question cards
            FakeResult(scalar=["Category:Technology"]),  # interests
            FakeResult(rows=[]),  # drilldown candidates
            FakeResult(rows=[]),  # categories that already have a card
        ]
    )

    result = await wiki_route.ensure_wiki_interest_questions(session)

    assert len(result) == 1
    assert result[0]["options_display"] == ["Databases"]
    assert result[0]["options_full"] == ["Category:Databases"]


async def test_ensure_questions_creates_one_for_an_interest_with_none_pending(monkeypatch):
    patch_services(monkeypatch, subcategories=["Category:Databases"])
    session = FakeSession(
        [
            FakeResult(rows=[]),  # pending question cards
            FakeResult(scalar=["Category:Technology"]),  # interests
            FakeResult(rows=[]),  # drilldown candidates
            FakeResult(rows=[]),  # categories that already have a card
        ]
    )

    result = await wiki_route.ensure_wiki_interest_questions(session)

    assert [q["parent_category"] for q in result] == ["Category:Technology"]
    assert len(session.added_of(WikiInterestCard)) == 1


async def test_ensure_questions_drills_down_into_a_well_read_category(monkeypatch):
    """A category read past the threshold earns a follow-up question card."""
    patch_services(monkeypatch, subcategories=["Category:Robotics"])
    session = FakeSession(
        [
            FakeResult(rows=[]),
            FakeResult(scalar=[]),
            FakeResult(rows=[row(category_title="Category:Technology", read_count=5)]),
            FakeResult(rows=[]),
        ]
    )

    result = await wiki_route.ensure_wiki_interest_questions(session)

    assert [q["parent_category"] for q in result] == ["Category:Technology"]


async def test_ensure_questions_skips_a_drilldown_that_already_has_a_card(monkeypatch):
    patch_services(monkeypatch, subcategories=["Category:Robotics"])
    session = FakeSession(
        [
            FakeResult(rows=[]),
            FakeResult(scalar=[]),
            FakeResult(rows=[row(category_title="Category:Technology", read_count=5)]),
            FakeResult(rows=[row(parent_category="Category:Technology")]),
        ]
    )

    assert await wiki_route.ensure_wiki_interest_questions(session) == []


# ---------------------------------------------------------------------------
# Remaining branches
# ---------------------------------------------------------------------------

def test_get_cards_ignores_a_non_list_selected_options_value(client_factory, monkeypatch):
    """Guards the ARRAY column coming back as something other than a list."""
    patch_services(monkeypatch)
    session = FakeSession(
        [
            FakeResult(scalar=None),  # interests
            FakeResult(rows=[row(selected_options="Category:Databases")]),
            FakeResult(rows=[]),  # projects
            FakeResult(rows=[]),  # shown titles (project phase)
        ]
    )

    assert client_factory(session).get("/wikipedia/cards").json() == []


def test_get_cards_refreshes_cached_keywords_when_the_description_changed(
    client_factory, monkeypatch
):
    patch_services(monkeypatch, summary=ARTICLE, keywords=["Kubernetes"])
    stale = ProjectKeyword(
        project_id=PROJECT_ID,
        keywords=["Old topic"],
        generated_at=FIXED_NOW,
        description_snapshot="Infra\nan older description",
    )
    session = FakeSession(
        [
            FakeResult(scalar=None),  # interests
            FakeResult(rows=[]),  # answered interest questions
            FakeResult(rows=[row(id=PROJECT_ID, title="Infra", description="k8s work")]),
            FakeResult(scalar=stale),  # cached keywords
            FakeResult(),  # the update
            FakeResult(rows=[]),  # shown titles (project phase)
        ]
    )

    body = client_factory(session).get("/wikipedia/cards").json()

    assert body[0]["source_term"] == "Kubernetes"
    assert session.added_of(ProjectKeyword) == []


def test_get_cards_discards_blank_and_non_string_keywords(client_factory, monkeypatch):
    seen = []

    def summary(term):
        seen.append(term)
        return dict(ARTICLE, title=f"Article about {term}")

    monkeypatch.setattr(wiki_route, "random_articles_from_category", lambda *a, **kw: [])
    monkeypatch.setattr(wiki_route, "fetch_wikipedia_summary", summary)
    monkeypatch.setattr(
        wiki_route, "extract_project_keywords", lambda *a, **kw: ["  Kubernetes  ", "   ", 42]
    )
    session = FakeSession(
        [
            FakeResult(scalar=None),
            FakeResult(rows=[]),
            FakeResult(rows=[row(id=PROJECT_ID, title="Infra", description="k8s work")]),
            FakeResult(scalar=None),
            FakeResult(rows=[]),
        ]
    )

    client_factory(session).get("/wikipedia/cards")

    assert seen == ["Kubernetes"]


def test_get_cards_stops_at_the_project_card_cap(client_factory, monkeypatch):
    monkeypatch.setattr(wiki_route, "random_articles_from_category", lambda *a, **kw: [])
    monkeypatch.setattr(
        wiki_route,
        "fetch_wikipedia_summary",
        lambda term: dict(ARTICLE, title=f"Article about {term}"),
    )
    monkeypatch.setattr(
        wiki_route, "extract_project_keywords", lambda *a, **kw: ["a", "b", "c", "d", "e"]
    )
    session = FakeSession(
        [
            FakeResult(scalar=None),
            FakeResult(rows=[]),
            FakeResult(rows=[row(id=PROJECT_ID, title="Infra", description="k8s work")]),
            FakeResult(scalar=None),
            FakeResult(rows=[]),
        ]
    )

    body = client_factory(session).get("/wikipedia/cards").json()

    assert len(body) == wiki_route.PROJECT_MAX_CARDS


def test_get_cards_skips_a_second_keyword_resolving_to_the_same_article(
    client_factory, monkeypatch
):
    monkeypatch.setattr(wiki_route, "random_articles_from_category", lambda *a, **kw: [])
    monkeypatch.setattr(wiki_route, "fetch_wikipedia_summary", lambda term: ARTICLE)
    monkeypatch.setattr(
        wiki_route, "extract_project_keywords", lambda *a, **kw: ["k8s", "kubernetes"]
    )
    session = FakeSession(
        [
            FakeResult(scalar=None),
            FakeResult(rows=[]),
            FakeResult(rows=[row(id=PROJECT_ID, title="Infra", description="k8s work")]),
            FakeResult(scalar=None),
            FakeResult(rows=[]),
        ]
    )

    body = client_factory(session).get("/wikipedia/cards").json()

    assert [c["title"] for c in body] == ["Kubernetes"]


async def test_ensure_questions_stops_at_the_per_request_cap(monkeypatch):
    """Five interests plus a drill-down candidate, capped at four new questions."""
    patch_services(monkeypatch, subcategories=["Category:Databases"])
    session = FakeSession(
        [
            FakeResult(rows=[]),  # pending question cards
            FakeResult(scalar=[f"Category:C{i}" for i in range(5)]),  # interests
            FakeResult(rows=[row(category_title="Category:Extra", read_count=9)]),
            FakeResult(rows=[]),  # categories that already have a card
        ]
    )

    result = await wiki_route.ensure_wiki_interest_questions(session)

    assert len(result) == wiki_route.MAX_NEW_WIKI_QUESTIONS_PER_REQUEST


async def test_ensure_questions_creates_none_when_no_subcategories_exist(monkeypatch):
    """generate_wiki_interest_question returns None, so both loops just move on."""
    patch_services(monkeypatch, subcategories=[])
    session = FakeSession(
        [
            FakeResult(rows=[]),  # pending question cards
            FakeResult(scalar=["Category:Technology"]),  # interests
            FakeResult(rows=[row(category_title="Category:Robotics", read_count=9)]),
            FakeResult(rows=[]),  # categories that already have a card
        ]
    )

    result = await wiki_route.ensure_wiki_interest_questions(session)

    assert result == []
    assert session.added_of(WikiInterestCard) == []


async def test_ensure_questions_skips_a_drilldown_already_pending(monkeypatch):
    """A drill-down candidate that already has a pending card is not duplicated."""
    patch_services(monkeypatch, subcategories=["Category:Databases"])
    pending = WikiInterestCard(
        id=CARD_ID,
        parent_category="Category:Technology",
        options=["Category:Databases"],
        status="unanswered",
        created_at=FIXED_NOW,
    )
    session = FakeSession(
        [
            FakeResult(rows=[pending]),  # pending question cards
            FakeResult(scalar=[]),  # interests
            FakeResult(rows=[row(category_title="Category:Technology", read_count=9)]),
            FakeResult(rows=[]),  # categories that already have a card
        ]
    )

    result = await wiki_route.ensure_wiki_interest_questions(session)

    assert len(result) == 1
    assert session.added_of(WikiInterestCard) == []
