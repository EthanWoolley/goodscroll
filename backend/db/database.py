"""Kept for backward-compatible imports during migration. All DB access now goes
through backend.db.session (async engine / AsyncSession)."""

from backend.db.session import get_db  # noqa: F401
