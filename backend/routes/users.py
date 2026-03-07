import json
from datetime import datetime, timezone

from fastapi import APIRouter

from backend.db.database import get_connection
from backend.models import InterestsSubmit
from backend.services.wikipedia_category_service import INTEREST_TO_CATEGORY

router = APIRouter(prefix="/users", tags=["users"])

DEFAULT_USER_ID = "default_user"


@router.post("/interests")
def post_interests(body: InterestsSubmit):
    categories = [
        INTEREST_TO_CATEGORY.get(label, f"Category:{label}")
        for label in body.interests
    ]
    now = datetime.now(timezone.utc).isoformat()
    conn = get_connection()
    conn.execute(
        """INSERT INTO user_interests (id, interests, updated_at)
           VALUES (?, ?, ?)
           ON CONFLICT(id) DO UPDATE SET interests = excluded.interests, updated_at = excluded.updated_at""",
        (DEFAULT_USER_ID, json.dumps(categories), now),
    )
    conn.commit()
    conn.close()
    return {"ok": True}


@router.get("/interests")
def get_interests():
    conn = get_connection()
    row = conn.execute(
        "SELECT interests FROM user_interests WHERE id = ?", (DEFAULT_USER_ID,)
    ).fetchone()
    conn.close()
    if not row:
        return []
    try:
        return json.loads(row["interests"])
    except (json.JSONDecodeError, TypeError):
        return []
