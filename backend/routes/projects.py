import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request

from backend.db.database import get_connection
from backend.models import (
    AnswersSubmit,
    CardOut,
    NextRoundResponse,
    ProjectCreate,
    ProjectCreateResponse,
    ProjectOut,
)
from backend.services.card_generator import generate_cards
from backend.services.evaluator import evaluate_and_generate

router = APIRouter(prefix="/projects", tags=["projects"])


def _row_to_card(row) -> CardOut:
    return CardOut(
        id=row["id"],
        project_id=row["project_id"],
        type=row["type"],
        question=row["question"],
        options=json.loads(row["options"]) if row["options"] else None,
        status=row["status"],
        round=row["round"],
        created_at=row["created_at"],
    )


def _row_to_project(row) -> ProjectOut:
    return ProjectOut(
        id=row["id"],
        title=row["title"],
        description=row["description"],
        project_type=row["project_type"],
        end_goal=row["end_goal"],
        deadline=row["deadline"],
        created_at=row["created_at"],
    )


@router.get("", response_model=list[ProjectOut])
def list_projects():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM projects ORDER BY created_at DESC").fetchall()
    conn.close()
    return [_row_to_project(r) for r in rows]


@router.post("", response_model=ProjectCreateResponse)
def create_project(request: Request, body: ProjectCreate):
    project_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    api_key = (request.headers.get("X-Anthropic-Key") or "").strip()

    conn = get_connection()
    conn.execute(
        "INSERT INTO projects (id, title, description, project_type, end_goal, deadline, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (project_id, body.title, body.description, body.project_type, body.end_goal, body.deadline, now),
    )
    conn.commit()

    cards = generate_cards(
        project_description=body.description,
        project_type=body.project_type,
        end_goal=body.end_goal,
        project_id=project_id,
        round_number=1,
        api_key=api_key or None,
    )

    for c in cards:
        conn.execute(
            "INSERT INTO cards (id, project_id, type, question, options, status, round, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (c["id"], c["project_id"], c["type"], c["question"], c["options"], c["status"], c["round"], c["created_at"]),
        )
    conn.commit()

    project_row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    card_rows = conn.execute("SELECT * FROM cards WHERE project_id = ? ORDER BY created_at", (project_id,)).fetchall()
    conn.close()

    return ProjectCreateResponse(
        project=_row_to_project(project_row),
        cards=[_row_to_card(r) for r in card_rows],
    )


@router.get("/{project_id}/cards", response_model=list[CardOut])
def get_cards(project_id: str):
    conn = get_connection()
    project = conn.execute("SELECT id FROM projects WHERE id = ?", (project_id,)).fetchone()
    if not project:
        conn.close()
        raise HTTPException(status_code=404, detail="Project not found")

    rows = conn.execute(
        """SELECT * FROM cards
           WHERE project_id = ? AND status != 'answered'
           ORDER BY
             CASE WHEN status = 'skipped' THEN 0 ELSE 1 END,
             created_at""",
        (project_id,),
    ).fetchall()
    conn.close()
    return [_row_to_card(r) for r in rows]


@router.post("/{project_id}/answers", response_model=NextRoundResponse)
def submit_answers(request: Request, project_id: str, body: AnswersSubmit):
    api_key = (request.headers.get("X-Anthropic-Key") or "").strip()
    conn = get_connection()
    project_row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    if not project_row:
        conn.close()
        raise HTTPException(status_code=404, detail="Project not found")

    now = datetime.now(timezone.utc).isoformat()

    for a in body.answers:
        conn.execute(
            "INSERT INTO answers (id, card_id, project_id, answer, created_at) VALUES (?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), a.card_id, project_id, a.answer, now),
        )
        conn.execute("UPDATE cards SET status = 'answered' WHERE id = ?", (a.card_id,))
    conn.commit()

    qa_rows = conn.execute(
        """SELECT c.question, a.answer
           FROM answers a
           JOIN cards c ON a.card_id = c.id
           WHERE a.project_id = ?
           ORDER BY a.created_at""",
        (project_id,),
    ).fetchall()

    qa_list = [{"question": r["question"], "answer": r["answer"]} for r in qa_rows]

    max_round = conn.execute(
        "SELECT MAX(round) as mr FROM cards WHERE project_id = ?", (project_id,)
    ).fetchone()["mr"] or 1

    result = evaluate_and_generate(
        project_type=project_row["project_type"],
        description=project_row["description"],
        qa_rows=qa_list,
        project_id=project_id,
        next_round=max_round + 1,
        api_key=api_key or None,
    )

    if result["status"] == "complete":
        conn.close()
        return NextRoundResponse(status="complete", cards=[])

    for c in result["cards"]:
        conn.execute(
            "INSERT INTO cards (id, project_id, type, question, options, status, round, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (c["id"], c["project_id"], c["type"], c["question"], c["options"], c["status"], c["round"], c["created_at"]),
        )
    conn.commit()

    card_rows = conn.execute(
        """SELECT * FROM cards
           WHERE project_id = ? AND status != 'answered'
           ORDER BY
             CASE WHEN status = 'skipped' THEN 0 ELSE 1 END,
             created_at""",
        (project_id,),
    ).fetchall()
    conn.close()

    return NextRoundResponse(
        status="continue",
        cards=[_row_to_card(r) for r in card_rows],
    )


@router.patch("/{project_id}/cards/{card_id}/skip")
def skip_card(project_id: str, card_id: str):
    conn = get_connection()
    conn.execute(
        "UPDATE cards SET status = 'skipped' WHERE id = ? AND project_id = ?",
        (card_id, project_id),
    )
    conn.commit()
    conn.close()
    return {"ok": True}
