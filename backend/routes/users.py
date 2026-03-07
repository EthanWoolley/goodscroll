from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import UserInterest
from backend.db.session import get_db
from backend.models import InterestsSubmit
from backend.services.wikipedia_category_service import INTEREST_TO_CATEGORY

router = APIRouter(prefix="/users", tags=["users"])

DEFAULT_USER_ID = "default_user"


@router.post("/interests")
async def post_interests(body: InterestsSubmit, db: AsyncSession = Depends(get_db)):
    categories = [
        INTEREST_TO_CATEGORY.get(label, f"Category:{label}")
        for label in body.interests
    ]
    now = datetime.now(timezone.utc)

    result = await db.execute(
        select(UserInterest).where(UserInterest.id == DEFAULT_USER_ID)
    )
    existing = result.scalar_one_or_none()
    if existing:
        await db.execute(
            update(UserInterest)
            .where(UserInterest.id == DEFAULT_USER_ID)
            .values(interests=categories, updated_at=now)
        )
    else:
        db.add(UserInterest(id=DEFAULT_USER_ID, interests=categories, updated_at=now))
    await db.commit()
    return {"ok": True}


@router.get("/interests")
async def get_interests(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(UserInterest.interests).where(UserInterest.id == DEFAULT_USER_ID)
    )
    interests = result.scalar_one_or_none()
    if not interests:
        return []
    return interests
