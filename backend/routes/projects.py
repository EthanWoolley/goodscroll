import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import Answer, Card, Project, ProjectContextOverride
from backend.db.session import get_db
from backend.models import (
    AnswersSubmit,
    CardOut,
    ContextOut,
    ContextUpdate,
    NextRoundResponse,
    ProjectCreate,
    ProjectCreateResponse,
    ProjectOut,
)
from backend.services.card_generator import generate_cards
from backend.services.evaluator import build_qa_history, evaluate_and_generate

router = APIRouter(prefix="/projects", tags=["projects"])


def _orm_to_card(row: Card) -> CardOut:
    return CardOut(
        id=str(row.id),
        project_id=str(row.project_id),
        type=row.type,
        question=row.question,
        options=list(row.options) if row.options else None,
        status=row.status,
        round=row.round,
        created_at=row.created_at.isoformat(),
    )


def _orm_to_project(row: Project) -> ProjectOut:
    return ProjectOut(
        id=str(row.id),
        title=row.title,
        description=row.description,
        project_type=row.project_type,
        end_goal=row.end_goal,
        deadline=row.deadline,
        created_at=row.created_at.isoformat(),
    )


async def _get_project_context(db: AsyncSession, project_id: uuid.UUID) -> str:
    result = await db.execute(
        select(ProjectContextOverride.context).where(
            ProjectContextOverride.project_id == project_id
        )
    )
    override = result.scalar_one_or_none()
    if override:
        return override

    result = await db.execute(
        select(Card.question, Answer.answer)
        .join(Card, Answer.card_id == Card.id)
        .where(Answer.project_id == project_id)
        .order_by(Answer.created_at)
    )
    qa_rows = result.all()
    qa_list = [{"question": r.question, "answer": r.answer} for r in qa_rows]
    return build_qa_history(qa_list)


@router.get("", response_model=list[ProjectOut])
async def list_projects(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).order_by(Project.created_at.desc()))
    rows = result.scalars().all()
    return [_orm_to_project(r) for r in rows]


@router.get("/{project_id}/context", response_model=ContextOut)
async def get_project_context(project_id: str, db: AsyncSession = Depends(get_db)):
    pid = uuid.UUID(project_id)
    result = await db.execute(
        select(Project.id, Project.title).where(Project.id == pid)
    )
    project = result.first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    context = await _get_project_context(db, pid)
    return ContextOut(context=context, project_title=project.title)


@router.put("/{project_id}/context", response_model=ContextOut)
async def put_project_context(
    project_id: str, body: ContextUpdate, db: AsyncSession = Depends(get_db)
):
    pid = uuid.UUID(project_id)
    result = await db.execute(select(Project.id).where(Project.id == pid))
    if not result.first():
        raise HTTPException(status_code=404, detail="Project not found")

    now = datetime.now(timezone.utc)
    existing = await db.execute(
        select(ProjectContextOverride).where(ProjectContextOverride.project_id == pid)
    )
    if existing.scalar_one_or_none():
        await db.execute(
            update(ProjectContextOverride)
            .where(ProjectContextOverride.project_id == pid)
            .values(context=body.context, updated_at=now)
        )
    else:
        db.add(ProjectContextOverride(project_id=pid, context=body.context, updated_at=now))
    await db.commit()
    return ContextOut(context=body.context)


@router.delete("/{project_id}/context/override")
async def delete_project_context_override(
    project_id: str, db: AsyncSession = Depends(get_db)
):
    pid = uuid.UUID(project_id)
    result = await db.execute(
        select(ProjectContextOverride).where(ProjectContextOverride.project_id == pid)
    )
    obj = result.scalar_one_or_none()
    if obj:
        await db.delete(obj)
        await db.commit()
    return {"ok": True}


def _parse_card_options(raw_options: str | None) -> list[str] | None:
    """Card generator/evaluator return options as a JSON string; convert to list for DB ARRAY."""
    if not raw_options:
        return None
    return json.loads(raw_options)


@router.post("", response_model=ProjectCreateResponse)
async def create_project(
    request: Request, body: ProjectCreate, db: AsyncSession = Depends(get_db)
):
    project_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    api_key = (request.headers.get("X-Anthropic-Key") or "").strip()

    project = Project(
        id=project_id,
        title=body.title,
        description=body.description,
        project_type=body.project_type,
        end_goal=body.end_goal,
        deadline=body.deadline,
        created_at=now,
    )
    db.add(project)
    await db.commit()

    cards_raw = generate_cards(
        project_description=body.description,
        project_type=body.project_type,
        end_goal=body.end_goal,
        project_id=str(project_id),
        round_number=1,
        api_key=api_key or None,
    )

    for c in cards_raw:
        card = Card(
            id=uuid.UUID(c["id"]),
            project_id=project_id,
            type=c["type"],
            question=c["question"],
            options=_parse_card_options(c["options"]),
            status=c["status"],
            round=c["round"],
            created_at=datetime.fromisoformat(c["created_at"]),
        )
        db.add(card)
    await db.commit()

    await db.refresh(project)
    result = await db.execute(
        select(Card).where(Card.project_id == project_id).order_by(Card.created_at)
    )
    card_rows = result.scalars().all()

    return ProjectCreateResponse(
        project=_orm_to_project(project),
        cards=[_orm_to_card(r) for r in card_rows],
    )


@router.get("/{project_id}/cards", response_model=list[CardOut])
async def get_cards(project_id: str, db: AsyncSession = Depends(get_db)):
    pid = uuid.UUID(project_id)
    result = await db.execute(select(Project.id).where(Project.id == pid))
    if not result.first():
        raise HTTPException(status_code=404, detail="Project not found")

    result = await db.execute(
        select(Card)
        .where(Card.project_id == pid, Card.status != "answered")
        .order_by(
            (Card.status == "skipped").desc(),
            Card.created_at,
        )
    )
    rows = result.scalars().all()
    return [_orm_to_card(r) for r in rows]


@router.post("/{project_id}/answers", response_model=NextRoundResponse)
async def submit_answers(
    request: Request,
    project_id: str,
    body: AnswersSubmit,
    db: AsyncSession = Depends(get_db),
):
    api_key = (request.headers.get("X-Anthropic-Key") or "").strip()
    pid = uuid.UUID(project_id)
    result = await db.execute(select(Project).where(Project.id == pid))
    project_row = result.scalar_one_or_none()
    if not project_row:
        raise HTTPException(status_code=404, detail="Project not found")

    now = datetime.now(timezone.utc)
    for a in body.answers:
        db.add(
            Answer(
                id=uuid.uuid4(),
                card_id=uuid.UUID(a.card_id),
                project_id=pid,
                answer=a.answer,
                created_at=now,
            )
        )
        await db.execute(
            update(Card).where(Card.id == uuid.UUID(a.card_id)).values(status="answered")
        )
    await db.commit()

    result = await db.execute(
        select(Card.question, Answer.answer)
        .join(Card, Answer.card_id == Card.id)
        .where(Answer.project_id == pid)
        .order_by(Answer.created_at)
    )
    qa_rows = result.all()
    qa_list = [{"question": r.question, "answer": r.answer} for r in qa_rows]

    result = await db.execute(
        select(Card.round).where(Card.project_id == pid).order_by(Card.round.desc()).limit(1)
    )
    max_round = result.scalar_one_or_none() or 1

    context_str = await _get_project_context(db, pid)
    eval_result = evaluate_and_generate(
        project_type=project_row.project_type,
        description=project_row.description,
        qa_rows=qa_list,
        project_id=str(pid),
        next_round=max_round + 1,
        api_key=api_key or None,
        qa_history_override=context_str,
    )

    if eval_result["status"] == "complete":
        return NextRoundResponse(status="complete", cards=[])

    for c in eval_result["cards"]:
        card = Card(
            id=uuid.UUID(c["id"]),
            project_id=pid,
            type=c["type"],
            question=c["question"],
            options=_parse_card_options(c["options"]),
            status=c["status"],
            round=c["round"],
            created_at=datetime.fromisoformat(c["created_at"]),
        )
        db.add(card)
    await db.commit()

    result = await db.execute(
        select(Card)
        .where(Card.project_id == pid, Card.status != "answered")
        .order_by(
            (Card.status == "skipped").desc(),
            Card.created_at,
        )
    )
    card_rows = result.scalars().all()
    return NextRoundResponse(
        status="continue",
        cards=[_orm_to_card(r) for r in card_rows],
    )


@router.patch("/{project_id}/cards/{card_id}/skip")
async def skip_card(
    project_id: str, card_id: str, db: AsyncSession = Depends(get_db)
):
    await db.execute(
        update(Card)
        .where(Card.id == uuid.UUID(card_id), Card.project_id == uuid.UUID(project_id))
        .values(status="skipped")
    )
    await db.commit()
    return {"ok": True}
