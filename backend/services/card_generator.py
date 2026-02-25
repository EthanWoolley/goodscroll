import json
import uuid
from datetime import datetime, timezone

import anthropic

SYSTEM_PROMPT = """You are a project assistant. Given a project description, generate a set of focused questions to extract the most important information needed to make progress on this project.

For a "Creating" project: ask questions that extract the user's existing knowledge, constraints, key decisions, and next steps.
For a "Learning" project: ask questions that assess current knowledge level, clarify what specifically they want to learn, and identify any deadlines or goals.

Return ONLY a JSON array. No preamble, no markdown. Each item must be one of these two formats:

Multiple choice:
{
  "type": "multiple_choice",
  "question": "...",
  "options": ["option A", "option B", "option C", "option D"]
}

Open ended:
{
  "type": "open_ended",
  "question": "..."
}

Generate between 4 and 6 questions. Mix multiple choice and open ended. Keep questions specific to the project description provided. Do not generate generic questions."""


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
    )

    raw = response.content[0].text.strip()
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
            "round": round_number,
            "created_at": now,
        }
        cards.append(card)

    return cards
