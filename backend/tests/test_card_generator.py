"""Parsing and card-shaping logic in backend.services.card_generator.

The Anthropic client is replaced wholesale by the ``anthropic_stub`` fixture, so
every case here is a canned response string fed through the real parser.
"""

import json
import uuid
from datetime import datetime

import pytest

from backend.services.card_generator import SYSTEM_PROMPT, generate_cards

STRUCTURED = json.dumps(
    {
        "questions": [
            {"type": "open_ended", "question": "What problem does this solve?"},
            {
                "type": "multiple_choice",
                "question": "Which stack?",
                "options": ["Django", "FastAPI"],
            },
        ]
    }
)

BARE_ARRAY = json.dumps(
    [
        {"type": "open_ended", "question": "What problem does this solve?"},
        {"type": "multiple_choice", "question": "Which stack?", "options": ["Django", "FastAPI"]},
    ]
)


def call(stub, response_text, **overrides):
    stub.queue(response_text)
    kwargs = {
        "project_description": "A scroll app",
        "project_type": "creating",
        "end_goal": None,
        "project_id": "project-1",
        "round_number": 1,
    }
    kwargs.update(overrides)
    return generate_cards(**kwargs)


# ---------------------------------------------------------------------------
# Response shapes that parse
# ---------------------------------------------------------------------------

def test_parses_structured_output_shape(anthropic_stub):
    """The {"questions": [...]} object the JSON-schema output config asks for."""
    cards = call(anthropic_stub, STRUCTURED)

    assert [c["question"] for c in cards] == [
        "What problem does this solve?",
        "Which stack?",
    ]
    assert [c["type"] for c in cards] == ["open_ended", "multiple_choice"]


def test_parses_bare_json_array_legacy_path(anthropic_stub):
    """Older responses put the array at the root rather than under "questions"."""
    cards = call(anthropic_stub, BARE_ARRAY)

    assert len(cards) == 2
    assert cards[1]["options"] == json.dumps(["Django", "FastAPI"])


def test_strips_json_fence(anthropic_stub):
    cards = call(anthropic_stub, f"```json\n{BARE_ARRAY}\n```")

    assert len(cards) == 2


def test_strips_fence_without_a_language_tag(anthropic_stub):
    cards = call(anthropic_stub, f"```\n{BARE_ARRAY}\n```")

    assert len(cards) == 2


def test_recovers_an_array_wrapped_in_prose(anthropic_stub):
    """The JSONDecodeError fallback slices between the outermost brackets."""
    cards = call(anthropic_stub, f"Sure, here you go:\n{BARE_ARRAY}\nHope that helps!")

    assert len(cards) == 2


# ---------------------------------------------------------------------------
# Response shapes that raise
# ---------------------------------------------------------------------------

def test_empty_response_raises_a_clear_error(anthropic_stub):
    with pytest.raises(ValueError, match="empty response for card generation"):
        call(anthropic_stub, "")


def test_whitespace_only_response_counts_as_empty(anthropic_stub):
    with pytest.raises(ValueError, match="empty response for card generation"):
        call(anthropic_stub, "   \n\t  ")


def test_fence_containing_nothing_counts_as_empty(anthropic_stub):
    """The fence is stripped before the emptiness check, so this is caught too."""
    with pytest.raises(ValueError, match="empty response for card generation"):
        call(anthropic_stub, "```json\n\n```")


def test_prose_with_no_brackets_raises_a_clear_error_not_a_decode_error(anthropic_stub):
    with pytest.raises(ValueError) as excinfo:
        call(anthropic_stub, "I need more detail before I can help with that.")

    assert not isinstance(excinfo.value, json.JSONDecodeError)
    assert "not valid JSON" in str(excinfo.value)
    # The message quotes the response so the failure can be diagnosed from a log.
    assert "I need more detail" in str(excinfo.value)


def test_truncates_the_offending_response_to_200_chars(anthropic_stub):
    with pytest.raises(ValueError) as excinfo:
        call(anthropic_stub, "x" * 500)

    assert "x" * 200 in str(excinfo.value)
    assert "x" * 201 not in str(excinfo.value)


@pytest.mark.xfail(
    strict=True,
    reason=(
        "Gap: when the response contains brackets but the slice between them is "
        "still not valid JSON, json.loads raises straight out of the except "
        "block, so callers see a bare JSONDecodeError instead of the clear "
        "ValueError the no-bracket path gives them."
    ),
)
def test_malformed_json_between_brackets_should_also_raise_a_clear_error(anthropic_stub):
    with pytest.raises(ValueError) as excinfo:
        call(anthropic_stub, "Sure! [not valid json at all] done")

    assert not isinstance(excinfo.value, json.JSONDecodeError)


# ---------------------------------------------------------------------------
# Question-level edge cases
# ---------------------------------------------------------------------------

def test_multiple_choice_missing_options_key_yields_no_options(anthropic_stub):
    """A multiple_choice question without options is accepted, with options=None.

    The JSON schema marks options optional, so the model can legitimately omit
    it. Nothing downstream substitutes a default.
    """
    cards = call(
        anthropic_stub,
        json.dumps([{"type": "multiple_choice", "question": "Which stack?"}]),
    )

    assert len(cards) == 1
    assert cards[0]["type"] == "multiple_choice"
    assert cards[0]["options"] is None


def test_multiple_choice_with_an_empty_options_list_also_yields_none(anthropic_stub):
    """`if q.get("options")` is falsy for [], so an empty list is not preserved."""
    cards = call(
        anthropic_stub,
        json.dumps([{"type": "multiple_choice", "question": "Which stack?", "options": []}]),
    )

    assert cards[0]["options"] is None


def test_question_missing_its_question_key_raises_keyerror(anthropic_stub):
    """Documents current behaviour: the card build indexes q["question"] directly."""
    with pytest.raises(KeyError):
        call(anthropic_stub, json.dumps([{"type": "open_ended"}]))


def test_object_without_a_questions_key_yields_no_cards(anthropic_stub):
    cards = call(anthropic_stub, json.dumps({"unexpected": "shape"}))

    assert cards == []


def test_json_scalar_yields_no_cards(anthropic_stub):
    """Neither a dict with "questions" nor a list, so the else branch empties it."""
    assert call(anthropic_stub, "42") == []


def test_empty_question_list_yields_no_cards(anthropic_stub):
    assert call(anthropic_stub, json.dumps({"questions": []})) == []


# ---------------------------------------------------------------------------
# Card shaping
# ---------------------------------------------------------------------------

def test_cards_carry_project_id_round_and_unanswered_status(anthropic_stub):
    cards = call(anthropic_stub, BARE_ARRAY, project_id="abc-123", round_number=4)

    assert all(c["project_id"] == "abc-123" for c in cards)
    assert all(c["round"] == 4 for c in cards)
    assert all(c["status"] == "unanswered" for c in cards)


def test_each_card_gets_a_distinct_uuid_and_iso_timestamp(anthropic_stub):
    cards = call(anthropic_stub, BARE_ARRAY)

    ids = [c["id"] for c in cards]
    assert len(set(ids)) == len(ids)
    for card in cards:
        uuid.UUID(card["id"])
        assert datetime.fromisoformat(card["created_at"]).tzinfo is not None


def test_options_are_serialised_as_a_json_string(anthropic_stub):
    """The route layer calls json.loads on this before writing the ARRAY column."""
    cards = call(anthropic_stub, BARE_ARRAY)

    assert json.loads(cards[1]["options"]) == ["Django", "FastAPI"]


# ---------------------------------------------------------------------------
# What gets sent to the client
# ---------------------------------------------------------------------------

def test_api_key_is_stripped_before_constructing_the_client(anthropic_stub):
    call(anthropic_stub, BARE_ARRAY, api_key="  sk-test-key  ")

    assert anthropic_stub.api_keys == ["sk-test-key"]


@pytest.mark.parametrize("api_key", [None, "", "   "])
def test_blank_api_key_falls_back_to_the_environment_client(anthropic_stub, api_key):
    call(anthropic_stub, BARE_ARRAY, api_key=api_key)

    assert anthropic_stub.api_keys == [None]


def test_end_goal_is_appended_to_the_user_message_when_present(anthropic_stub):
    call(anthropic_stub, BARE_ARRAY, end_goal="Ship by March")

    content = anthropic_stub.calls[0]["messages"][0]["content"]
    assert "End goal: Ship by March" in content
    assert "Project type: creating" in content


def test_end_goal_is_omitted_when_absent(anthropic_stub):
    call(anthropic_stub, BARE_ARRAY, end_goal=None)

    assert "End goal" not in anthropic_stub.calls[0]["messages"][0]["content"]


def test_request_pins_the_model_and_the_questions_schema(anthropic_stub):
    call(anthropic_stub, BARE_ARRAY)

    request = anthropic_stub.calls[0]
    assert request["model"] == "claude-sonnet-4-6"
    assert request["system"] == SYSTEM_PROMPT
    schema = request["output_config"]["format"]["schema"]
    assert schema["required"] == ["questions"]
