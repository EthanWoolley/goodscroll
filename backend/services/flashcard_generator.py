"""Generate flashcards for Learning projects based on project description and Q&A history."""

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


FLASHCARD_PROMPT_TEMPLATE = """You are a learning assistant. Based on this learning project and the user's Q&A history, generate flashcards to test their knowledge on the topics they want to learn.

Project description: {description}
Q&A history: {qa_history}

Generate 5 flashcards. Each should test a specific, concrete piece of knowledge relevant to the project's learning goals. Avoid vague or overly broad questions.

Return ONLY a JSON array. No preamble, no markdown. Each item:
{{
  "question": "...",
  "answer": "...",
  "topic": "..."
}}"""


def generate_flashcards(
    description: str,
    qa_rows: list[dict],
    project_id: str,
    api_key: str | None = None,
) -> list[dict]:
    """Returns a list of dicts with question, answer, topic. Each will be stored as a card with type='flashcard'."""
    if api_key and api_key.strip():
        client = anthropic.Anthropic(api_key=api_key.strip())
    else:
        client = anthropic.Anthropic()

    qa_history = build_qa_history(qa_rows)
    prompt = FLASHCARD_PROMPT_TEMPLATE.format(
        description=description,
        qa_history=qa_history or "(No Q&A yet)",
    )

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()

    if not raw:
        raise ValueError("Anthropic returned an empty response for flashcard generation")

    try:
        items = json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("[")
        end = raw.rfind("]")
        if start != -1 and end != -1 and end > start:
            items = json.loads(raw[start : end + 1])
        else:
            raise ValueError(
                "Flashcard response was not valid JSON. First 200 chars: %s"
                % repr(raw[:200])
            ) from None

    if not isinstance(items, list):
        raise ValueError("Flashcard response was not a JSON array")

    now = datetime.now(timezone.utc).isoformat()
    cards = []
    for item in items[:5]:
        question = item.get("question") or ""
        answer = item.get("answer") or ""
        topic = item.get("topic") or ""
        cards.append({
            "id": str(uuid.uuid4()),
            "project_id": project_id,
            "type": "flashcard",
            "question": question,
            "answer": answer,
            "topic": topic,
            "options": None,
            "status": "unanswered",
            "round": 1,
            "created_at": now,
        })
    return cards
