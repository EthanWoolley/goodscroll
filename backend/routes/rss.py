import re
import time
import uuid
from datetime import datetime, timezone

import feedparser
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import RssFeed
from backend.db.session import get_db
from backend.models import RssFeedAdd

router = APIRouter(prefix="/rss", tags=["rss"])


def _truncate_summary(text: str, max_len: int = 200) -> str:
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= max_len:
        return text
    truncated = text[: max_len + 1]
    last_space = truncated.rfind(" ")
    if last_space > 0:
        return truncated[:last_space].strip()
    return truncated.strip()


def _extract_image_url(entry) -> str | None:
    media_content = getattr(entry, "media_content", None)
    if media_content and len(media_content) > 0:
        first = media_content[0]
        url = first.get("url") if isinstance(first, dict) else getattr(first, "url", None)
        if url:
            return url
    media_thumbnail = getattr(entry, "media_thumbnail", None)
    if media_thumbnail and len(media_thumbnail) > 0:
        first = media_thumbnail[0]
        url = first.get("url") if isinstance(first, dict) else getattr(first, "url", None)
        if url:
            return url
    enclosures = getattr(entry, "enclosures", None) or []
    for enc in enclosures:
        enc_type = enc.get("type", "") if isinstance(enc, dict) else getattr(enc, "type", "") or ""
        if "image" in enc_type.lower():
            url = enc.get("href") if isinstance(enc, dict) else getattr(enc, "href", None)
            if url:
                return url
    raw_desc = getattr(entry, "summary", None) or getattr(entry, "description", None) or ""
    if hasattr(raw_desc, "get"):
        raw_desc = raw_desc.get("value", str(raw_desc))
    raw_str = str(raw_desc)
    if "<img" in raw_str.lower():
        match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', raw_str, re.I)
        if match:
            return match.group(1).strip()
    return None


def _parse_published(entry) -> str:
    published = getattr(entry, "published", None)
    if published:
        return published
    parsed = getattr(entry, "published_parsed", None)
    if parsed and len(parsed) >= 6:
        try:
            dt = datetime.fromtimestamp(time.mktime(parsed), tz=timezone.utc)
            return dt.isoformat()
        except (ValueError, OSError):
            pass
    return datetime.now(timezone.utc).isoformat()


@router.post("/feeds")
async def add_feed(body: RssFeedAdd, db: AsyncSession = Depends(get_db)):
    url = (body.url or "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="url is required")

    feed_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    feed = RssFeed(id=feed_id, url=url, created_at=now)
    db.add(feed)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Feed URL already added") from None

    await db.refresh(feed)
    return {
        "id": str(feed.id),
        "url": feed.url,
        "created_at": feed.created_at.isoformat(),
    }


@router.get("/feeds")
async def list_feeds(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RssFeed).order_by(RssFeed.created_at))
    rows = result.scalars().all()
    return [
        {"id": str(r.id), "url": r.url, "created_at": r.created_at.isoformat()}
        for r in rows
    ]


@router.delete("/feeds/{feed_id}")
async def delete_feed(feed_id: str, db: AsyncSession = Depends(get_db)):
    fid = uuid.UUID(feed_id)
    result = await db.execute(delete(RssFeed).where(RssFeed.id == fid))
    await db.commit()
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Feed not found")
    return {"ok": True}


async def get_rss_cards_list(db: AsyncSession):
    result = await db.execute(select(RssFeed.id, RssFeed.url))
    rows = result.all()

    all_entries = []
    for row in rows:
        try:
            parsed = feedparser.parse(row.url)
            feed_title = getattr(parsed.feed, "title", None) or "Unknown"
            for entry in parsed.entries:
                link = getattr(entry, "link", None)
                if not link:
                    continue
                title = getattr(entry, "title", None) or ""
                raw_desc = getattr(entry, "summary", None) or getattr(
                    entry, "description", None
                ) or ""
                if hasattr(raw_desc, "get"):
                    raw_desc = raw_desc.get("value", str(raw_desc))
                summary = _truncate_summary(str(raw_desc))
                published_at = _parse_published(entry)
                entry_id = getattr(entry, "id", None) or str(uuid.uuid4())
                image_url = _extract_image_url(entry)
                all_entries.append(
                    {
                        "id": entry_id,
                        "type": "rss",
                        "title": title,
                        "source": feed_title,
                        "summary": summary,
                        "url": link,
                        "published_at": published_at,
                        "image_url": image_url,
                    }
                )
        except Exception:
            continue

    all_entries.sort(key=lambda e: e["published_at"], reverse=True)
    return all_entries[:20]


@router.get("/cards")
async def get_rss_cards(db: AsyncSession = Depends(get_db)):
    return await get_rss_cards_list(db)
