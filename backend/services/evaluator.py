import json
import uuid
from datetime import datetime, timezone

import anthropic


def build_qa_history(rows: list[dict]) -> str:
    lines = []
    for r in rows:
        lines.append(f"Q: {r['question']}")
        lines.append(f"A: {r['answer']}")
        lines.append("")
    return "\n".join(lines)


EVAL_PROMPT_TEMPLATE = """You are a project assistant reviewing a user's answers so far.

Project type: {project_type}
Project description: {description}

Q&A so far:
{qa_history}

Decide: does this project have enough context to move forward, or are there important gaps still?

For "Creating" projects, minimum sufficient context means: the user's goal is clear, key constraints or preferences are known, and there is at least one actionable next step implied.
For "Learning" projects, minimum sufficient context means: current knowledge level is clear, target topics are identified, and learning goal or deadline is known.

If context is sufficient, respond with exactly: COMPLETE

If more questions are needed, respond with a JSON array of 3 to 4 additional questions in the same format as before (type: multiple_choice or open_ended). No preamble, no markdown, just the JSON array or the word COMPLETE."""


def evaluate_and_generate(
    project_type: str,
    description: str,
    qa_rows: list[dict],
    project_id: str,
    next_round: int,
    api_key: str | None = None,
) -> dict:
    """Returns {"status": "complete"} or {"status": "continue", "cards": [...]}"""
    if api_key and api_key.strip():
        client = anthropic.Anthropic(api_key=api_key.strip())
    else:
        client = anthropic.Anthropic()
    qa_history = build_qa_history(qa_rows)

    prompt = EVAL_PROMPT_TEMPLATE.format(
        project_type=project_type,
        description=description,
        qa_history=qa_history,
    )

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text.strip()

    if raw.upper() == "COMPLETE":
        return {"status": "complete", "cards": []}

    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    questions = json.loads(raw)
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
            "round": next_round,
            "created_at": now,
        }
        cards.append(card)

    return {"status": "continue", "cards": cards}
