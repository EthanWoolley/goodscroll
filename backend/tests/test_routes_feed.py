"""The integrated feed in backend.routes.feed.

The Wikipedia and RSS collaborators are patched at the names feed.py imported
them under, so each test controls exactly what goes into the interleave. The
scripted query sequence is: skipped cards, last answer per project, last
flashcard response per project, all flashcard responses, projects with due
questions, all flashcard cards, then one query per project with due cards.
"""

import uuid
from datetime import timedelta

from backend.models import WikipediaCardOut
from backend.routes import feed as feed_route
from backend.tests.support import FIXED_NOW, FakeResult, FakeSession, make_card, row

PROJECT_A = uuid.UUID("66666666-6666-6666-6666-666666666666")
PROJECT_B = uuid.UUID("77777777-7777-7777-7777-777777777777")


def patch_sources(monkeypatch, wiki_questions=(), wiki_cards=(), rss_cards=()):
    async def questions(db):
        return list(wiki_questions)

    async def cards(db, api_key):
        return list(wiki_cards)

    async def rss(db):
        return list(rss_cards)

    monkeypatch.setattr(feed_route, "ensure_wiki_interest_questions", questions)
    monkeypatch.setattr(feed_route, "get_wikipedia_cards_for_feed", cards)
    monkeypatch.setattr(feed_route, "get_rss_cards_list", rss)


def wiki_card(title="Kubernetes"):
    return WikipediaCardOut(
        id=str(uuid.uuid4()),
        title=title,
        extract="An orchestration system.",
        url="https://en.m.wikipedia.org/wiki/Kubernetes",
        source_term="Technology",
    )


def rss_card(title="First post"):
    return {
        "id": str(uuid.uuid4()),
        "title": title,
        "summary": "A summary",
        "url": "https://example.com/a",
        "published_at": "2026-01-01T00:00:00+00:00",
        "source": "Example Feed",
        "image_url": None,
    }


def base_results(
    skipped=(),
    question_projects=(),
    flashcards=(),
    responses=(),
    last_answers=(),
    last_flashcard_activity=(),
):
    """The six fixed queries every request to /feed makes."""
    return [
        FakeResult(rows=list(skipped)),
        FakeResult(rows=list(last_answers)),
        FakeResult(rows=list(last_flashcard_activity)),
        FakeResult(rows=list(responses)),
        FakeResult(rows=[row(project_id=pid) for pid in question_projects]),
        FakeResult(rows=list(flashcards)),
    ]


# ---------------------------------------------------------------------------
# Empty and single-source feeds
# ---------------------------------------------------------------------------

def test_feed_with_nothing_to_show_is_empty(client_factory, monkeypatch):
    patch_sources(monkeypatch)
    session = FakeSession(base_results())

    resp = client_factory(session).get("/feed")

    assert resp.status_code == 200
    assert resp.json() == []


def test_feed_serialises_a_question_card(client_factory, monkeypatch):
    patch_sources(monkeypatch)
    card = make_card(
        project_id=PROJECT_A, card_type="multiple_choice", question="Which stack?",
        options=["Django", "FastAPI"],
    )
    session = FakeSession(
        base_results(question_projects=[PROJECT_A])
        + [FakeResult(rows=[row(Card=card, project_title="Scroll app")])]
    )

    body = client_factory(session).get("/feed").json()

    assert len(body) == 1
    assert body[0]["source"] == "question"
    assert body[0]["project_title"] == "Scroll app"
    assert body[0]["question"] == "Which stack?"
    assert body[0]["options"] == ["Django", "FastAPI"]


def test_feed_puts_skipped_cards_before_unanswered_ones(client_factory, monkeypatch):
    """Skipped cards return at the top of the next session, per the spec."""
    patch_sources(monkeypatch)
    skipped = make_card(project_id=PROJECT_A, question="Skipped earlier", status="skipped")
    unanswered = make_card(project_id=PROJECT_A, question="Fresh question")
    session = FakeSession(
        base_results(
            skipped=[row(Card=skipped, project_title="Scroll app")],
            question_projects=[PROJECT_A],
        )
        + [FakeResult(rows=[row(Card=unanswered, project_title="Scroll app")])]
    )

    body = client_factory(session).get("/feed").json()

    assert [c["question"] for c in body] == ["Skipped earlier", "Fresh question"]


def test_feed_returns_wikipedia_and_rss_when_there_are_no_questions(
    client_factory, monkeypatch
):
    patch_sources(monkeypatch, wiki_cards=[wiki_card()], rss_cards=[rss_card()])
    session = FakeSession(base_results())

    body = client_factory(session).get("/feed").json()

    assert {c["source"] for c in body} == {"wikipedia", "rss"}
    wiki = next(c for c in body if c["source"] == "wikipedia")
    assert wiki["title"] == "Kubernetes"
    rss = next(c for c in body if c["source"] == "rss")
    assert rss["feed_source"] == "Example Feed"


def test_feed_maps_a_wiki_interest_question(client_factory, monkeypatch):
    question = {
        "id": str(uuid.uuid4()),
        "parent_category": "Category:Technology",
        "options_full": ["Category:Databases"],
        "options_display": ["Databases"],
    }
    patch_sources(monkeypatch, wiki_questions=[question])
    session = FakeSession(base_results())

    body = client_factory(session).get("/feed").json()

    assert len(body) == 1
    assert body[0]["source"] == "wikipedia_interest_question"
    assert body[0]["wiki_interest_card_id"] == question["id"]
    assert body[0]["options"] == ["Databases"]
    assert body[0]["question"] == "Which of these topics interest you most?"


# ---------------------------------------------------------------------------
# Flashcard due logic
# ---------------------------------------------------------------------------

def test_feed_includes_a_flashcard_never_responded_to(client_factory, monkeypatch):
    patch_sources(monkeypatch)
    flashcard = make_card(project_id=PROJECT_A, card_type="flashcard", question="B-tree?")
    session = FakeSession(
        base_results(flashcards=[row(Card=flashcard, project_title="Learning")])
        + [FakeResult(rows=[])]
    )

    body = client_factory(session).get("/feed").json()

    assert [c["question"] for c in body] == ["B-tree?"]


def test_feed_excludes_a_flashcard_the_user_knew(client_factory, monkeypatch):
    patch_sources(monkeypatch)
    flashcard = make_card(project_id=PROJECT_A, card_type="flashcard", question="B-tree?")
    session = FakeSession(
        base_results(
            flashcards=[row(Card=flashcard, project_title="Learning")],
            responses=[row(card_id=flashcard.id, response="knew", next_review_at=None)],
        )
    )

    assert client_factory(session).get("/feed").json() == []


def test_feed_includes_a_flashcard_whose_review_is_due(client_factory, monkeypatch):
    patch_sources(monkeypatch)
    flashcard = make_card(project_id=PROJECT_A, card_type="flashcard", question="B-tree?")
    session = FakeSession(
        base_results(
            flashcards=[row(Card=flashcard, project_title="Learning")],
            responses=[
                row(
                    card_id=flashcard.id,
                    response="partly",
                    next_review_at=FIXED_NOW - timedelta(days=1),
                )
            ],
        )
        + [FakeResult(rows=[])]
    )

    body = client_factory(session).get("/feed").json()

    assert [c["question"] for c in body] == ["B-tree?"]


def test_feed_excludes_a_flashcard_not_yet_due(client_factory, monkeypatch):
    patch_sources(monkeypatch)
    flashcard = make_card(project_id=PROJECT_A, card_type="flashcard", question="B-tree?")
    session = FakeSession(
        base_results(
            flashcards=[row(Card=flashcard, project_title="Learning")],
            responses=[
                row(
                    card_id=flashcard.id,
                    response="partly",
                    next_review_at=FIXED_NOW + timedelta(days=3650),
                )
            ],
        )
    )

    assert client_factory(session).get("/feed").json() == []


def test_feed_uses_only_the_most_recent_response_per_card(client_factory, monkeypatch):
    """The query orders newest first, so the first row seen for a card wins."""
    patch_sources(monkeypatch)
    flashcard = make_card(project_id=PROJECT_A, card_type="flashcard", question="B-tree?")
    session = FakeSession(
        base_results(
            flashcards=[row(Card=flashcard, project_title="Learning")],
            responses=[
                row(card_id=flashcard.id, response="knew", next_review_at=None),
                row(card_id=flashcard.id, response="didnt_know", next_review_at=None),
            ],
        )
    )

    assert client_factory(session).get("/feed").json() == []


# ---------------------------------------------------------------------------
# Interleaving and limits
# ---------------------------------------------------------------------------

def test_feed_round_robins_questions_across_projects(client_factory, monkeypatch):
    patch_sources(monkeypatch)
    a1 = make_card(project_id=PROJECT_A, question="A1")
    a2 = make_card(project_id=PROJECT_A, question="A2")
    b1 = make_card(project_id=PROJECT_B, question="B1")
    session = FakeSession(
        base_results(question_projects=[PROJECT_A, PROJECT_B])
        + [
            FakeResult(rows=[row(Card=a1, project_title="A"), row(Card=a2, project_title="A")]),
            FakeResult(rows=[row(Card=b1, project_title="B")]),
        ]
    )

    body = client_factory(session).get("/feed").json()

    assert [c["question"] for c in body] == ["A1", "B1", "A2"]


def test_feed_places_an_rss_card_in_every_fifth_slot(client_factory, monkeypatch):
    """The interleave puts RSS at index 4, then every fifth position after it."""
    patch_sources(monkeypatch, rss_cards=[rss_card("R1"), rss_card("R2")])
    cards = [make_card(project_id=PROJECT_A, question=f"Q{i}") for i in range(12)]
    session = FakeSession(
        base_results(question_projects=[PROJECT_A])
        + [FakeResult(rows=[row(Card=c, project_title="A") for c in cards])]
    )

    body = client_factory(session).get("/feed").json()

    assert body[4]["source"] == "rss"
    assert body[9]["source"] == "rss"
    assert body[0]["source"] == "question"


def test_feed_caps_the_response_at_the_feed_limit(client_factory, monkeypatch):
    patch_sources(monkeypatch, rss_cards=[rss_card(f"R{i}") for i in range(40)])
    cards = [make_card(project_id=PROJECT_A, question=f"Q{i}") for i in range(80)]
    session = FakeSession(
        base_results(question_projects=[PROJECT_A])
        + [FakeResult(rows=[row(Card=c, project_title="A") for c in cards])]
    )

    body = client_factory(session).get("/feed").json()

    assert len(body) == feed_route.FEED_LIMIT


def test_feed_caps_skipped_cards(client_factory, monkeypatch):
    """SKIPPED_CAP bounds the query, so the feed cannot be all backlog."""
    patch_sources(monkeypatch)
    skipped = [
        row(
            Card=make_card(project_id=PROJECT_A, question=f"S{i}", status="skipped"),
            project_title="A",
        )
        for i in range(feed_route.SKIPPED_CAP)
    ]
    session = FakeSession(base_results(skipped=skipped))

    body = client_factory(session).get("/feed").json()

    assert len(body) == feed_route.SKIPPED_CAP
    assert all(c["status"] == "skipped" for c in body)


def test_feed_forwards_the_anthropic_key_header_to_the_wikipedia_source(
    client_factory, monkeypatch
):
    seen = {}

    async def cards(db, api_key):
        seen["api_key"] = api_key
        return []

    async def nothing(db):
        return []

    monkeypatch.setattr(feed_route, "ensure_wiki_interest_questions", nothing)
    monkeypatch.setattr(feed_route, "get_rss_cards_list", nothing)
    monkeypatch.setattr(feed_route, "get_wikipedia_cards_for_feed", cards)
    session = FakeSession(base_results())

    client_factory(session).get("/feed", headers={"X-Anthropic-Key": "  sk-header  "})

    assert seen["api_key"] == "sk-header"


def test_feed_passes_no_key_when_the_header_is_absent(client_factory, monkeypatch):
    seen = {}

    async def cards(db, api_key):
        seen["api_key"] = api_key
        return []

    async def nothing(db):
        return []

    monkeypatch.setattr(feed_route, "ensure_wiki_interest_questions", nothing)
    monkeypatch.setattr(feed_route, "get_rss_cards_list", nothing)
    monkeypatch.setattr(feed_route, "get_wikipedia_cards_for_feed", cards)
    session = FakeSession(base_results())

    client_factory(session).get("/feed")

    assert seen["api_key"] is None


def test_feed_surfaces_an_rss_source_failure_as_500(client_factory, monkeypatch):
    """Nothing wraps the source calls, so a raising collaborator fails the request."""

    async def nothing(db):
        return []

    async def cards(db, api_key):
        return []

    async def boom(db):
        raise RuntimeError("feed source exploded")

    monkeypatch.setattr(feed_route, "ensure_wiki_interest_questions", nothing)
    monkeypatch.setattr(feed_route, "get_wikipedia_cards_for_feed", cards)
    monkeypatch.setattr(feed_route, "get_rss_cards_list", boom)
    session = FakeSession(base_results())

    resp = client_factory(session, raise_server_exceptions=False).get("/feed")

    assert resp.status_code == 500


# ---------------------------------------------------------------------------
# Project ordering and per-project assembly
# ---------------------------------------------------------------------------

def test_feed_orders_projects_by_least_recent_activity(client_factory, monkeypatch):
    """Flashcard responses count as activity, and the later timestamp wins."""
    patch_sources(monkeypatch)
    a1 = make_card(project_id=PROJECT_A, question="A1")
    b1 = make_card(project_id=PROJECT_B, question="B1")
    session = FakeSession(
        base_results(
            question_projects=[PROJECT_A, PROJECT_B],
            last_answers=[row(project_id=PROJECT_A, last_at=FIXED_NOW)],
            last_flashcard_activity=[
                # Later than the answer above, so it replaces it for A.
                row(project_id=PROJECT_A, last_at=FIXED_NOW + timedelta(days=120)),
                row(project_id=PROJECT_B, last_at=FIXED_NOW + timedelta(days=30)),
            ],
        )
        + [
            FakeResult(rows=[row(Card=b1, project_title="B")]),
            FakeResult(rows=[row(Card=a1, project_title="A")]),
        ]
    )

    body = client_factory(session).get("/feed").json()

    # B was touched longer ago than A, so B's card comes first.
    assert [c["question"] for c in body] == ["B1", "A1"]


def test_feed_offers_a_due_flashcard_only_to_its_own_project(client_factory, monkeypatch):
    patch_sources(monkeypatch)
    a1 = make_card(project_id=PROJECT_A, question="A1")
    b1 = make_card(project_id=PROJECT_B, question="B1")
    flashcard = make_card(project_id=PROJECT_A, card_type="flashcard", question="B-tree?")
    session = FakeSession(
        base_results(
            question_projects=[PROJECT_A, PROJECT_B],
            flashcards=[row(Card=flashcard, project_title="A")],
        )
        + [
            FakeResult(rows=[row(Card=a1, project_title="A")]),
            FakeResult(rows=[row(Card=b1, project_title="B")]),
        ]
    )

    body = client_factory(session).get("/feed").json()

    questions = [c["question"] for c in body]
    assert "B-tree?" in questions
    # The flashcard belongs to A only; B contributes just its own question.
    assert questions.count("B-tree?") == 1


# ---------------------------------------------------------------------------
# Remaining interleave branches
# ---------------------------------------------------------------------------

def test_feed_inserts_a_wikipedia_card_after_three_other_cards(client_factory, monkeypatch):
    patch_sources(monkeypatch, wiki_cards=[wiki_card("Kubernetes")])
    cards = [make_card(project_id=PROJECT_A, question=f"Q{i}") for i in range(6)]
    session = FakeSession(
        base_results(question_projects=[PROJECT_A])
        + [FakeResult(rows=[row(Card=c, project_title="A") for c in cards])]
    )

    body = client_factory(session).get("/feed").json()

    assert [c["source"] for c in body[:4]] == [
        "question",
        "question",
        "question",
        "wikipedia",
    ]


def test_feed_falls_back_to_remaining_wiki_questions(client_factory, monkeypatch):
    """Once questions and articles run out, spacing no longer gates the queue."""
    questions = [
        {
            "id": str(uuid.uuid4()),
            "parent_category": f"Category:C{i}",
            "options_full": [f"Category:S{i}"],
            "options_display": [f"S{i}"],
        }
        for i in range(3)
    ]
    patch_sources(monkeypatch, wiki_questions=questions)
    session = FakeSession(base_results())

    body = client_factory(session).get("/feed").json()

    assert len(body) == 3
    assert all(c["source"] == "wikipedia_interest_question" for c in body)


def test_feed_omits_wikipedia_entirely_when_the_toggle_is_set(client_factory, monkeypatch):
    """SKIP_WIKI_IN_FEED short-circuits both Wikipedia sources without calling them."""

    async def should_not_run(*args, **kwargs):
        raise AssertionError("Wikipedia sources must not be called when skipping")

    async def rss(db):
        return [rss_card("R1")]

    monkeypatch.setattr(feed_route, "SKIP_WIKI_IN_FEED", True)
    monkeypatch.setattr(feed_route, "ensure_wiki_interest_questions", should_not_run)
    monkeypatch.setattr(feed_route, "get_wikipedia_cards_for_feed", should_not_run)
    monkeypatch.setattr(feed_route, "get_rss_cards_list", rss)
    session = FakeSession(base_results())

    body = client_factory(session).get("/feed").json()

    assert [c["source"] for c in body] == ["rss"]


def test_feed_keeps_the_later_activity_when_a_flashcard_response_is_older(
    client_factory, monkeypatch
):
    """An older flashcard response must not overwrite a newer answer timestamp."""
    patch_sources(monkeypatch)
    a1 = make_card(project_id=PROJECT_A, question="A1")
    b1 = make_card(project_id=PROJECT_B, question="B1")
    session = FakeSession(
        base_results(
            question_projects=[PROJECT_A, PROJECT_B],
            last_answers=[
                row(project_id=PROJECT_A, last_at=FIXED_NOW + timedelta(days=120)),
                row(project_id=PROJECT_B, last_at=FIXED_NOW + timedelta(days=30)),
            ],
            # Older than A's answer above, so it is ignored.
            last_flashcard_activity=[row(project_id=PROJECT_A, last_at=FIXED_NOW)],
        )
        + [
            FakeResult(rows=[row(Card=b1, project_title="B")]),
            FakeResult(rows=[row(Card=a1, project_title="A")]),
        ]
    )

    body = client_factory(session).get("/feed").json()

    # A is still the most recently touched project, so B leads.
    assert [c["question"] for c in body] == ["B1", "A1"]
