"""Completion detection and card shaping in backend.services.evaluator.

The completion check is ``raw.strip().upper() == "COMPLETE"``: an exact match
against the whole response. The tests below pin down both what that catches and
what it does not.
"""

import json
import uuid
from datetime import datetime

import pytest

from backend.services.evaluator import EVAL_PROMPT_TEMPLATE, build_qa_history, evaluate_and_generate

QUESTION_ARRAY = json.dumps(
    [
        {"type": "open_ended", "question": "Who is the audience?"},
        {"type": "multiple_choice", "question": "Ship when?", "options": ["Q1", "Q2"]},
        {"type": "open_ended", "question": "What is out of scope?"},
    ]
)


def call(stub, response_text, **overrides):
    stub.queue(response_text)
    kwargs = {
        "project_type": "creating",
        "description": "A scroll app",
        "qa_rows": [],
        "project_id": "project-1",
        "next_round": 2,
    }
    kwargs.update(overrides)
    return evaluate_and_generate(**kwargs)


# ---------------------------------------------------------------------------
# Recognising COMPLETE
# ---------------------------------------------------------------------------

def test_recognises_complete_exactly(anthropic_stub):
    assert call(anthropic_stub, "COMPLETE") == {"status": "complete", "cards": []}


def test_recognises_complete_with_trailing_whitespace(anthropic_stub):
    """The response is stripped before the comparison."""
    result = call(anthropic_stub, "COMPLETE   \n\t ")

    assert result["status"] == "complete"


def test_recognises_complete_with_leading_whitespace(anthropic_stub):
    assert call(anthropic_stub, "\n  COMPLETE")["status"] == "complete"


@pytest.mark.parametrize("text", ["complete", "Complete", "cOmPlEtE"])
def test_completion_check_is_case_insensitive(anthropic_stub, text):
    assert call(anthropic_stub, text)["status"] == "complete"


@pytest.mark.xfail(
    strict=True,
    reason=(
        "Gap: the check is an exact match on the whole response, so a trailing "
        "full stop stops it matching. The response then falls through to "
        "json.loads and raises a bare JSONDecodeError, turning a completed "
        "project into a 500. Whether to loosen the match is a product call."
    ),
)
def test_recognises_complete_with_a_trailing_full_stop(anthropic_stub):
    assert call(anthropic_stub, "COMPLETE.")["status"] == "complete"


# ---------------------------------------------------------------------------
# Not falsely recognising COMPLETE
# ---------------------------------------------------------------------------

def test_does_not_match_the_word_complete_inside_a_question_string(anthropic_stub):
    """A question array mentioning "complete" must still be treated as more work.

    An exact whole-response match is what protects this: a substring or prefix
    check would misread this payload as a finished project and drop three
    questions on the floor.
    """
    payload = json.dumps(
        [
            {"type": "open_ended", "question": "Is the design complete?"},
            {"type": "open_ended", "question": "Which parts are COMPLETE already?"},
            {"type": "multiple_choice", "question": "Complete by when?", "options": ["Q1", "Q2"]},
        ]
    )

    result = call(anthropic_stub, payload)

    assert result["status"] == "continue"
    assert len(result["cards"]) == 3
    assert result["cards"][0]["question"] == "Is the design complete?"


def test_does_not_match_a_question_whose_entire_text_is_complete(anthropic_stub):
    """The strictest version of the same trap: "COMPLETE" as a whole question."""
    payload = json.dumps([{"type": "open_ended", "question": "COMPLETE"}])

    result = call(anthropic_stub, payload)

    assert result["status"] == "continue"
    assert result["cards"][0]["question"] == "COMPLETE"


def test_does_not_match_a_sentence_containing_the_word(anthropic_stub):
    """Prose is not a completion signal; it fails the JSON parse instead."""
    with pytest.raises(json.JSONDecodeError):
        call(anthropic_stub, "The project context is now COMPLETE, well done.")


# ---------------------------------------------------------------------------
# Parsing the continue path
# ---------------------------------------------------------------------------

def test_parses_a_question_array_into_cards(anthropic_stub):
    result = call(anthropic_stub, QUESTION_ARRAY, project_id="proj-9", next_round=3)

    assert result["status"] == "continue"
    cards = result["cards"]
    assert len(cards) == 3
    assert [c["question"] for c in cards] == [
        "Who is the audience?",
        "Ship when?",
        "What is out of scope?",
    ]
    assert all(c["project_id"] == "proj-9" for c in cards)
    assert all(c["round"] == 3 for c in cards)
    assert all(c["status"] == "unanswered" for c in cards)


def test_each_card_gets_a_distinct_uuid_and_iso_timestamp(anthropic_stub):
    cards = call(anthropic_stub, QUESTION_ARRAY)["cards"]

    ids = [c["id"] for c in cards]
    assert len(set(ids)) == len(ids)
    for card in cards:
        uuid.UUID(card["id"])
        assert datetime.fromisoformat(card["created_at"]).tzinfo is not None


def test_options_are_serialised_as_a_json_string(anthropic_stub):
    cards = call(anthropic_stub, QUESTION_ARRAY)["cards"]

    assert cards[0]["options"] is None
    assert json.loads(cards[1]["options"]) == ["Q1", "Q2"]


def test_strips_a_json_fence_around_the_array(anthropic_stub):
    result = call(anthropic_stub, f"```json\n{QUESTION_ARRAY}\n```")

    assert len(result["cards"]) == 3


def test_empty_question_array_continues_with_no_cards(anthropic_stub):
    assert call(anthropic_stub, "[]") == {"status": "continue", "cards": []}


def test_empty_response_raises_a_decode_error(anthropic_stub):
    """Documents a gap: unlike card_generator, there is no emptiness guard here."""
    with pytest.raises(json.JSONDecodeError):
        call(anthropic_stub, "")


def test_unlike_card_generator_prose_is_not_recovered(anthropic_stub):
    """There is no bracket-slicing fallback here, so a preamble is fatal."""
    with pytest.raises(json.JSONDecodeError):
        call(anthropic_stub, f"Here you go: {QUESTION_ARRAY}")


# ---------------------------------------------------------------------------
# build_qa_history and prompt assembly
# ---------------------------------------------------------------------------

def test_build_qa_history_formats_each_pair_with_a_blank_line():
    history = build_qa_history(
        [
            {"question": "Who for?", "answer": "Solo devs"},
            {"question": "When?", "answer": "March"},
        ]
    )

    assert history == "Q: Who for?\nA: Solo devs\n\nQ: When?\nA: March\n"


def test_build_qa_history_of_nothing_is_empty():
    assert build_qa_history([]) == ""


def test_prompt_uses_the_history_built_from_qa_rows(anthropic_stub):
    call(
        anthropic_stub,
        "COMPLETE",
        qa_rows=[{"question": "Who for?", "answer": "Solo devs"}],
    )

    prompt = anthropic_stub.calls[0]["messages"][0]["content"]
    assert "Q: Who for?\nA: Solo devs" in prompt
    assert "Project type: creating" in prompt
    assert "Project description: A scroll app" in prompt


def test_override_replaces_the_history_built_from_qa_rows(anthropic_stub):
    call(
        anthropic_stub,
        "COMPLETE",
        qa_rows=[{"question": "Who for?", "answer": "Solo devs"}],
        qa_history_override="A hand-edited context document",
    )

    prompt = anthropic_stub.calls[0]["messages"][0]["content"]
    assert "A hand-edited context document" in prompt
    assert "Solo devs" not in prompt


def test_an_empty_override_is_honoured_rather_than_falling_back(anthropic_stub):
    """The check is `is not None`, so an empty override still wins over qa_rows."""
    call(
        anthropic_stub,
        "COMPLETE",
        qa_rows=[{"question": "Who for?", "answer": "Solo devs"}],
        qa_history_override="",
    )

    assert "Solo devs" not in anthropic_stub.calls[0]["messages"][0]["content"]


def test_prompt_is_built_from_the_shared_template(anthropic_stub):
    call(anthropic_stub, "COMPLETE")

    prompt = anthropic_stub.calls[0]["messages"][0]["content"]
    assert prompt == EVAL_PROMPT_TEMPLATE.format(
        project_type="creating", description="A scroll app", qa_history=""
    )


def test_api_key_is_stripped_before_constructing_the_client(anthropic_stub):
    call(anthropic_stub, "COMPLETE", api_key="  sk-test-key  ")

    assert anthropic_stub.api_keys == ["sk-test-key"]


@pytest.mark.parametrize("api_key", [None, "", "   "])
def test_blank_api_key_falls_back_to_the_environment_client(anthropic_stub, api_key):
    call(anthropic_stub, "COMPLETE", api_key=api_key)

    assert anthropic_stub.api_keys == [None]


def test_request_pins_the_model(anthropic_stub):
    call(anthropic_stub, "COMPLETE")

    assert anthropic_stub.calls[0]["model"] == "claude-sonnet-4-6"
