import json
import uuid
from datetime import datetime, timezone

import anthropic

SYSTEM_PROMPT = """You are a project assistant. Given a project description, generate a set of \
focused questions to extract the most important information needed to make progress on this \
project.

For a "Creating" project: ask questions that extract the user's existing knowledge, \
constraints, key decisions, and next steps.
For a "Learning" project: ask questions that assess current knowledge level, clarify what \
specifically they want to learn, and identify any deadlines or goals.

Never respond with plain-text clarification or meta-questions. Always output only the JSON \
array of questions. If the description is vague or missing details, include questions in the \
array that ask for those details.

Each item must be one of these two formats:

Multiple choice:
{ "type": "multiple_choice", "question": "...", "options": ["option A", "option B", \
"option C", "option D"] }

Open ended:
{ "type": "open_ended", "question": "..." }

Generate between 4 and 6 questions. Mix multiple choice and open ended. Keep questions \
specific to the project description provided. Do not generate generic questions."""

# JSON schema for structured output so the API returns only valid JSON (no plain-text
# clarification).
# Root must be an object per Anthropic structured output; we use "questions" array.
QUESTIONS_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "questions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {"type": "string", "enum": ["multiple_choice", "open_ended"]},
                    "question": {"type": "string"},
                    "options": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["type", "question"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["questions"],
    "additionalProperties": False,
}


def _not_valid_json_error(raw: str) -> ValueError:
    """The error raised whenever a response cannot be parsed as questions.

    Callers get this rather than a bare JSONDecodeError, and the message quotes
    the start of the response so a failure can be diagnosed from a log.
    """
    return ValueError(
        "Anthropic response was not valid JSON. First 200 chars: %s" % repr(raw[:200])
    )


def generate_cards(
    project_description: str,
    project_type: str,
    end_goal: str | None,
    project_id: str,
    round_number: int,
    api_key: str | None = None,
) -> list[dict]:
    if api_key and api_key.strip():
        client = anthropic.Anthropic(api_key=api_key.strip())
    else:
        client = anthropic.Anthropic()

    user_msg = f"Project type: {project_type}\nDescription: {project_description}"
    if end_goal:
        user_msg += f"\nEnd goal: {end_goal}"

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_msg}],
        output_config={
            "format": {"type": "json_schema", "schema": QUESTIONS_JSON_SCHEMA},
        },
    )

    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    if not raw:
        raise ValueError("Anthropic returned an empty response for card generation")

    try:
        parsed = json.loads(raw)
        # Structured output returns {"questions": [...]}; legacy path may return array at root
        if isinstance(parsed, dict) and "questions" in parsed:
            questions = parsed["questions"]
        elif isinstance(parsed, list):
            questions = parsed
        else:
            questions = []
    except json.JSONDecodeError:
        # Try to extract a JSON array from the response (e.g. preamble or trailing text)
        start = raw.find("[")
        end = raw.rfind("]")
        if start == -1 or end == -1 or end <= start:
            raise _not_valid_json_error(raw) from None
        try:
            questions = json.loads(raw[start : end + 1])
        except json.JSONDecodeError:
            # Brackets were there, but what sat between them was not an array.
            raise _not_valid_json_error(raw) from None
    now = datetime.now(timezone.utc).isoformat()

    cards = []
    for q in questions:
        card = {
            "id": str(uuid.uuid4()),
            "project_id": project_id,
            "type": q["type"],
            "question": q["question"],
            "options": json.dumps(q.get("options")) if q.get("options") else None,
            "status": "unanswered",
            "round": round_number,
            "created_at": now,
        }
        cards.append(card)

    return cards
