"""Route handlers in backend.routes.projects.

The card generator, evaluator and flashcard generator are patched at the names
projects.py imported them under, so no prompt is ever built and no HTTP call is
ever made. The database is a FakeSession replaying scripted query results.
"""

import json
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from backend.db.models import Answer, Card, FlashcardResponse, ProjectContextOverride
from backend.routes import projects as projects_route
from backend.tests.support import FIXED_NOW, FakeResult, FakeSession, make_card, make_project, row

PROJECT_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
CARD_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")


def generated_card(question="Generated?", card_type="open_ended", options=None, round_number=1):
    """The dict shape the generator and evaluator hand back to the route."""
    return {
        "id": str(uuid.uuid4()),
        "project_id": str(PROJECT_ID),
        "type": card_type,
        "question": question,
        "options": json.dumps(options) if options else None,
        "status": "unanswered",
        "round": round_number,
        "created_at": FIXED_NOW.isoformat(),
    }


# ---------------------------------------------------------------------------
# GET /projects
# ---------------------------------------------------------------------------

def test_list_projects_returns_serialised_projects(client_factory):
    project = make_project(PROJECT_ID, title="Scroll app", end_goal="Ship it")
    session = FakeSession([FakeResult(rows=[project])])

    resp = client_factory(session).get("/projects")

    assert resp.status_code == 200
    assert resp.json() == [
        {
            "id": str(PROJECT_ID),
            "title": "Scroll app",
            "description": "A description",
            "project_type": "creating",
            "end_goal": "Ship it",
            "deadline": None,
            "created_at": FIXED_NOW.isoformat(),
        }
    ]


def test_list_projects_with_none_returns_an_empty_list(client_factory):
    resp = client_factory(FakeSession([FakeResult(rows=[])])).get("/projects")

    assert resp.status_code == 200
    assert resp.json() == []


# ---------------------------------------------------------------------------
# GET /projects/{id}/context
# ---------------------------------------------------------------------------

def test_get_context_prefers_a_stored_override(client_factory):
    session = FakeSession(
        [
            FakeResult(rows=[row(id=PROJECT_ID, title="Scroll app")]),
            FakeResult(scalar="A hand-edited context document"),
        ]
    )

    resp = client_factory(session).get(f"/projects/{PROJECT_ID}/context")

    assert resp.status_code == 200
    assert resp.json() == {
        "context": "A hand-edited context document",
        "project_title": "Scroll app",
    }


def test_get_context_falls_back_to_the_qa_history(client_factory):
    session = FakeSession(
        [
            FakeResult(rows=[row(id=PROJECT_ID, title="Scroll app")]),
            FakeResult(scalar=None),
            FakeResult(
                rows=[
                    row(question="Who for?", answer="Solo devs"),
                    row(question="When?", answer="March"),
                ]
            ),
        ]
    )

    resp = client_factory(session).get(f"/projects/{PROJECT_ID}/context")

    assert resp.json()["context"] == "Q: Who for?\nA: Solo devs\n\nQ: When?\nA: March\n"


def test_get_context_for_an_unknown_project_is_404(client_factory):
    session = FakeSession([FakeResult(rows=[])])

    resp = client_factory(session).get(f"/projects/{PROJECT_ID}/context")

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Project not found"


def test_get_context_with_a_malformed_project_id_is_a_server_error(client_factory):
    """uuid.UUID() raises before any query; nothing converts that to a 400."""
    session = FakeSession([])

    resp = client_factory(session, raise_server_exceptions=False).get(
        "/projects/not-a-uuid/context"
    )

    assert resp.status_code == 500


# ---------------------------------------------------------------------------
# PUT /projects/{id}/context
# ---------------------------------------------------------------------------

def test_put_context_inserts_when_no_override_exists(client_factory):
    session = FakeSession([FakeResult(rows=[row(id=PROJECT_ID)]), FakeResult(scalar=None)])

    resp = client_factory(session).put(
        f"/projects/{PROJECT_ID}/context", json={"context": "New context"}
    )

    assert resp.status_code == 200
    assert resp.json() == {"context": "New context", "project_title": None}
    inserted = session.added_of(ProjectContextOverride)
    assert len(inserted) == 1
    assert inserted[0].context == "New context"
    assert session.commits == 1


def test_put_context_updates_an_existing_override(client_factory):
    existing = ProjectContextOverride(project_id=PROJECT_ID, context="Old", updated_at=FIXED_NOW)
    session = FakeSession(
        [
            FakeResult(rows=[row(id=PROJECT_ID)]),
            FakeResult(scalar=existing),
            FakeResult(),
        ]
    )

    resp = client_factory(session).put(
        f"/projects/{PROJECT_ID}/context", json={"context": "Newer"}
    )

    assert resp.status_code == 200
    assert session.added_of(ProjectContextOverride) == []
    assert session.commits == 1


def test_put_context_for_an_unknown_project_is_404(client_factory):
    session = FakeSession([FakeResult(rows=[])])

    resp = client_factory(session).put(
        f"/projects/{PROJECT_ID}/context", json={"context": "New"}
    )

    assert resp.status_code == 404
    assert session.commits == 0


def test_put_context_without_a_context_field_is_422(client_factory):
    resp = client_factory(FakeSession([])).put(f"/projects/{PROJECT_ID}/context", json={})

    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# DELETE /projects/{id}/context/override
# ---------------------------------------------------------------------------

def test_delete_override_removes_it_when_present(client_factory):
    existing = ProjectContextOverride(project_id=PROJECT_ID, context="Old", updated_at=FIXED_NOW)
    session = FakeSession([FakeResult(scalar=existing)])

    resp = client_factory(session).delete(f"/projects/{PROJECT_ID}/context/override")

    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
    assert session.deleted == [existing]
    assert session.commits == 1


def test_delete_override_is_a_no_op_when_absent(client_factory):
    """Still reports ok; the endpoint is idempotent by design."""
    session = FakeSession([FakeResult(scalar=None)])

    resp = client_factory(session).delete(f"/projects/{PROJECT_ID}/context/override")

    assert resp.json() == {"ok": True}
    assert session.deleted == []
    assert session.commits == 0


# ---------------------------------------------------------------------------
# POST /projects
# ---------------------------------------------------------------------------

BODY = {
    "title": "Scroll app",
    "description": "A description",
    "project_type": "creating",
    "end_goal": "Ship it",
}


def test_create_project_persists_the_project_and_generated_cards(
    client_factory, monkeypatch
):
    captured = {}

    def fake_generate_cards(**kwargs):
        captured.update(kwargs)
        return [
            generated_card("What problem?"),
            generated_card("Which stack?", "multiple_choice", ["Django", "FastAPI"]),
        ]

    monkeypatch.setattr(projects_route, "generate_cards", fake_generate_cards)
    stored = [make_card(question="What problem?"), make_card(question="Which stack?")]
    session = FakeSession([FakeResult(rows=stored)])

    resp = client_factory(session).post("/projects", json=BODY)

    assert resp.status_code == 200
    body = resp.json()
    assert body["project"]["title"] == "Scroll app"
    assert [c["question"] for c in body["cards"]] == ["What problem?", "Which stack?"]
    assert captured["project_description"] == "A description"
    assert captured["round_number"] == 1
    assert len(session.added_of(Card)) == 2
    # One commit for the project, one for its cards.
    assert session.commits == 2


def test_create_project_forwards_the_anthropic_key_header(client_factory, monkeypatch):
    captured = {}

    def fake_generate_cards(**kwargs):
        captured.update(kwargs)
        return []

    monkeypatch.setattr(projects_route, "generate_cards", fake_generate_cards)
    session = FakeSession([FakeResult(rows=[])])

    client_factory(session).post(
        "/projects", json=BODY, headers={"X-Anthropic-Key": "  sk-header-key  "}
    )

    assert captured["api_key"] == "sk-header-key"


def test_create_project_without_the_header_passes_no_key(client_factory, monkeypatch):
    """A blank header becomes None so the service falls back to the server key."""
    captured = {}

    def fake_generate_cards(**kwargs):
        captured.update(kwargs)
        return []

    monkeypatch.setattr(projects_route, "generate_cards", fake_generate_cards)

    client_factory(FakeSession([FakeResult(rows=[])])).post("/projects", json=BODY)

    assert captured["api_key"] is None


def test_create_project_converts_json_options_into_a_list(client_factory, monkeypatch):
    monkeypatch.setattr(
        projects_route,
        "generate_cards",
        lambda **kw: [generated_card("Which stack?", "multiple_choice", ["Django", "FastAPI"])],
    )
    session = FakeSession([FakeResult(rows=[])])

    client_factory(session).post("/projects", json=BODY)

    assert session.added_of(Card)[0].options == ["Django", "FastAPI"]


def test_create_project_surfaces_a_generator_failure_as_500(client_factory, monkeypatch):
    """The route does not catch generator errors, so the project is left cardless."""

    def boom(**kwargs):
        raise ValueError("Anthropic returned an empty response for card generation")

    monkeypatch.setattr(projects_route, "generate_cards", boom)
    session = FakeSession([])

    resp = client_factory(session, raise_server_exceptions=False).post("/projects", json=BODY)

    assert resp.status_code == 500
    # The project row was already committed before the generator ran.
    assert session.commits == 1


def test_create_project_with_a_missing_field_is_422(client_factory):
    resp = client_factory(FakeSession([])).post("/projects", json={"title": "Only a title"})

    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /projects/{id}/cards
# ---------------------------------------------------------------------------

def test_get_cards_returns_unanswered_cards(client_factory):
    card = make_card(CARD_ID, PROJECT_ID, "multiple_choice", "Which stack?", ["Django"])
    session = FakeSession([FakeResult(rows=[row(id=PROJECT_ID)]), FakeResult(rows=[card])])

    resp = client_factory(session).get(f"/projects/{PROJECT_ID}/cards")

    assert resp.status_code == 200
    assert resp.json() == [
        {
            "id": str(CARD_ID),
            "project_id": str(PROJECT_ID),
            "type": "multiple_choice",
            "question": "Which stack?",
            "options": ["Django"],
            "answer": None,
            "topic": None,
            "status": "unanswered",
            "round": 1,
            "created_at": FIXED_NOW.isoformat(),
        }
    ]


def test_get_cards_for_an_unknown_project_is_404(client_factory):
    session = FakeSession([FakeResult(rows=[])])

    resp = client_factory(session).get(f"/projects/{PROJECT_ID}/cards")

    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /projects/{id}/answers
# ---------------------------------------------------------------------------

ANSWERS = {"answers": [{"card_id": str(CARD_ID), "answer": "Solo developers"}]}


def continue_session(project, next_cards):
    """Scripted results for submit_answers taking the "continue" branch."""
    return FakeSession(
        [
            FakeResult(scalar=project),
            FakeResult(),
            FakeResult(rows=[row(question="Who for?", answer="Solo developers")]),
            FakeResult(scalar=2),
            FakeResult(scalar="An override context"),
            FakeResult(rows=next_cards),
        ]
    )


def test_submit_answers_records_answers_and_returns_the_next_round(
    client_factory, monkeypatch
):
    captured = {}

    def fake_evaluate(**kwargs):
        captured.update(kwargs)
        return {"status": "continue", "cards": [generated_card("Next question?", round_number=3)]}

    monkeypatch.setattr(projects_route, "evaluate_and_generate", fake_evaluate)
    project = make_project(PROJECT_ID)
    stored = make_card(question="Next question?", round_number=3)
    session = continue_session(project, [stored])

    resp = client_factory(session).post(f"/projects/{PROJECT_ID}/answers", json=ANSWERS)

    assert resp.status_code == 200
    assert resp.json()["status"] == "continue"
    assert [c["question"] for c in resp.json()["cards"]] == ["Next question?"]
    assert len(session.added_of(Answer)) == 1
    assert session.added_of(Answer)[0].answer == "Solo developers"
    # max_round was 2, so the next round is 3.
    assert captured["next_round"] == 3
    assert captured["qa_history_override"] == "An override context"


def test_submit_answers_returns_complete_and_writes_no_cards(client_factory, monkeypatch):
    monkeypatch.setattr(
        projects_route,
        "evaluate_and_generate",
        lambda **kw: {"status": "complete", "cards": []},
    )
    session = FakeSession(
        [
            FakeResult(scalar=make_project(PROJECT_ID)),
            FakeResult(),
            FakeResult(rows=[row(question="Who for?", answer="Solo devs")]),
            FakeResult(scalar=2),
            FakeResult(scalar="An override context"),
        ]
    )

    resp = client_factory(session).post(f"/projects/{PROJECT_ID}/answers", json=ANSWERS)

    assert resp.json() == {"status": "complete", "cards": []}
    assert session.added_of(Card) == []


def test_submit_answers_defaults_the_round_when_no_cards_exist(client_factory, monkeypatch):
    """`scalar_one_or_none() or 1` means a project with no cards starts at round 2."""
    captured = {}

    def fake_evaluate(**kwargs):
        captured.update(kwargs)
        return {"status": "complete", "cards": []}

    monkeypatch.setattr(projects_route, "evaluate_and_generate", fake_evaluate)
    session = FakeSession(
        [
            FakeResult(scalar=make_project(PROJECT_ID)),
            FakeResult(),
            FakeResult(rows=[]),
            FakeResult(scalar=None),
            FakeResult(scalar="ctx"),
        ]
    )

    client_factory(session).post(f"/projects/{PROJECT_ID}/answers", json=ANSWERS)

    assert captured["next_round"] == 2


def test_submit_answers_generates_flashcards_when_a_learning_project_completes(
    client_factory, monkeypatch
):
    monkeypatch.setattr(
        projects_route,
        "evaluate_and_generate",
        lambda **kw: {"status": "complete", "cards": []},
    )
    monkeypatch.setattr(
        projects_route,
        "generate_flashcards",
        lambda **kw: [
            {
                "id": str(uuid.uuid4()),
                "question": "What is a B-tree?",
                "answer": "A balanced tree",
                "topic": "Databases",
                "status": "unanswered",
                "round": 1,
                "created_at": FIXED_NOW.isoformat(),
            }
        ],
    )
    session = FakeSession(
        [
            FakeResult(scalar=make_project(PROJECT_ID, project_type="learning")),
            FakeResult(),
            FakeResult(rows=[]),
            FakeResult(scalar=2),
            FakeResult(scalar="ctx"),
            FakeResult(scalar=None),
        ]
    )

    resp = client_factory(session).post(f"/projects/{PROJECT_ID}/answers", json=ANSWERS)

    assert resp.json()["status"] == "complete"
    flashcards = session.added_of(Card)
    assert len(flashcards) == 1
    assert flashcards[0].type == "flashcard"
    assert flashcards[0].answer == "A balanced tree"


def test_submit_answers_skips_flashcards_when_the_project_already_has_some(
    client_factory, monkeypatch
):
    monkeypatch.setattr(
        projects_route,
        "evaluate_and_generate",
        lambda **kw: {"status": "complete", "cards": []},
    )

    def should_not_run(**kwargs):
        raise AssertionError("flashcards should not be regenerated")

    monkeypatch.setattr(projects_route, "generate_flashcards", should_not_run)
    session = FakeSession(
        [
            FakeResult(scalar=make_project(PROJECT_ID, project_type="learning")),
            FakeResult(),
            FakeResult(rows=[]),
            FakeResult(scalar=2),
            FakeResult(scalar="ctx"),
            FakeResult(scalar=CARD_ID),
        ]
    )

    resp = client_factory(session).post(f"/projects/{PROJECT_ID}/answers", json=ANSWERS)

    assert resp.json()["status"] == "complete"


def test_submit_answers_swallows_a_flashcard_generation_failure(client_factory, monkeypatch):
    """Flashcards are best-effort: the completion response must survive their failure."""
    monkeypatch.setattr(
        projects_route,
        "evaluate_and_generate",
        lambda **kw: {"status": "complete", "cards": []},
    )

    def boom(**kwargs):
        raise ValueError("Flashcard response was not a JSON array")

    monkeypatch.setattr(projects_route, "generate_flashcards", boom)
    session = FakeSession(
        [
            FakeResult(scalar=make_project(PROJECT_ID, project_type="learning")),
            FakeResult(),
            FakeResult(rows=[]),
            FakeResult(scalar=2),
            FakeResult(scalar="ctx"),
            FakeResult(scalar=None),
        ]
    )

    resp = client_factory(session).post(f"/projects/{PROJECT_ID}/answers", json=ANSWERS)

    assert resp.status_code == 200
    assert resp.json()["status"] == "complete"


def test_submit_answers_for_an_unknown_project_is_404(client_factory):
    session = FakeSession([FakeResult(scalar=None)])

    resp = client_factory(session).post(f"/projects/{PROJECT_ID}/answers", json=ANSWERS)

    assert resp.status_code == 404
    assert session.added == []


def test_submit_answers_surfaces_an_evaluator_failure_as_500(client_factory, monkeypatch):
    def boom(**kwargs):
        raise json.JSONDecodeError("Expecting value", "COMPLETE.", 0)

    monkeypatch.setattr(projects_route, "evaluate_and_generate", boom)
    session = FakeSession(
        [
            FakeResult(scalar=make_project(PROJECT_ID)),
            FakeResult(),
            FakeResult(rows=[]),
            FakeResult(scalar=2),
            FakeResult(scalar="ctx"),
        ]
    )

    resp = client_factory(session, raise_server_exceptions=False).post(
        f"/projects/{PROJECT_ID}/answers", json=ANSWERS
    )

    assert resp.status_code == 500


def test_submit_answers_with_a_malformed_body_is_422(client_factory):
    resp = client_factory(FakeSession([])).post(
        f"/projects/{PROJECT_ID}/answers", json={"answers": [{"answer": "no card_id"}]}
    )

    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# POST /projects/{id}/flashcard-response
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("response", "expected_delay"),
    [("knew", None), ("partly", timedelta(days=1)), ("didnt_know", timedelta(days=3))],
)
def test_flashcard_response_schedules_the_next_review(
    client_factory, response, expected_delay
):
    card = make_card(CARD_ID, PROJECT_ID, card_type="flashcard")
    session = FakeSession([FakeResult(scalar=card)])
    before = datetime.now(timezone.utc)

    resp = client_factory(session).post(
        f"/projects/{PROJECT_ID}/flashcard-response",
        json={"card_id": str(CARD_ID), "response": response},
    )

    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
    recorded = session.added_of(FlashcardResponse)[0]
    assert recorded.response == response
    if expected_delay is None:
        assert recorded.next_review_at is None
    else:
        assert recorded.next_review_at >= before + expected_delay


def test_flashcard_response_for_an_unknown_card_is_404(client_factory):
    session = FakeSession([FakeResult(scalar=None)])

    resp = client_factory(session).post(
        f"/projects/{PROJECT_ID}/flashcard-response",
        json={"card_id": str(CARD_ID), "response": "knew"},
    )

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Card not found"


def test_flashcard_response_on_a_question_card_is_400(client_factory):
    card = make_card(CARD_ID, PROJECT_ID, card_type="open_ended")
    session = FakeSession([FakeResult(scalar=card)])

    resp = client_factory(session).post(
        f"/projects/{PROJECT_ID}/flashcard-response",
        json={"card_id": str(CARD_ID), "response": "knew"},
    )

    assert resp.status_code == 400
    assert resp.json()["detail"] == "Card is not a flashcard"


def test_flashcard_response_rejects_an_unknown_response_value(client_factory):
    """The Literal in FlashcardResponseIn rejects anything outside the three."""
    resp = client_factory(FakeSession([])).post(
        f"/projects/{PROJECT_ID}/flashcard-response",
        json={"card_id": str(CARD_ID), "response": "maybe"},
    )

    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# PATCH /projects/{id}/cards/{card_id}/skip
# ---------------------------------------------------------------------------

def test_skip_card_commits_the_status_change(client_factory):
    session = FakeSession([FakeResult()])

    resp = client_factory(session).patch(f"/projects/{PROJECT_ID}/cards/{CARD_ID}/skip")

    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
    assert session.commits == 1


def test_skip_card_reports_ok_even_when_nothing_matched(client_factory):
    """The handler never checks rowcount, so an unknown card still returns ok."""
    session = FakeSession([FakeResult(rowcount=0)])

    resp = client_factory(session).patch(f"/projects/{PROJECT_ID}/cards/{CARD_ID}/skip")

    assert resp.json() == {"ok": True}


def test_skip_card_with_a_malformed_id_is_a_server_error(client_factory):
    resp = client_factory(FakeSession([]), raise_server_exceptions=False).patch(
        f"/projects/{PROJECT_ID}/cards/not-a-uuid/skip"
    )

    assert resp.status_code == 500
