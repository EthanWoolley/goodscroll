import re
import sqlite3
import time
import uuid
from datetime import datetime, timezone

import feedparser
from fastapi import APIRouter, HTTPException

from backend.db.database import get_connection
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
    """Extract image URL from RSS entry (media_content, media_thumbnail, enclosures, or HTML)."""
    media_content = getattr(entry, "media_content", None)
    if media_content and len(media_content) > 0:
        url = media_content[0].get("url") if isinstance(media_content[0], dict) else getattr(media_content[0], "url", None)
        if url:
            return url
    media_thumbnail = getattr(entry, "media_thumbnail", None)
    if media_thumbnail and len(media_thumbnail) > 0:
        url = media_thumbnail[0].get("url") if isinstance(media_thumbnail[0], dict) else getattr(media_thumbnail[0], "url", None)
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
def add_feed(body: RssFeedAdd):
    url = (body.url or "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="url is required")
    feed_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO rss_feeds (id, url, created_at) VALUES (?, ?, ?)",
            (feed_id, url, now),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise HTTPException(status_code=409, detail="Feed URL already added")
    row = conn.execute(
        "SELECT id, url, created_at FROM rss_feeds WHERE id = ?", (feed_id,)
    ).fetchone()
    conn.close()
    return {"id": row["id"], "url": row["url"], "created_at": row["created_at"]}


@router.get("/feeds")
def list_feeds():
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, url, created_at FROM rss_feeds ORDER BY created_at"
    ).fetchall()
    conn.close()
    return [
        {"id": r["id"], "url": r["url"], "created_at": r["created_at"]}
        for r in rows
    ]


@router.delete("/feeds/{feed_id}")
def delete_feed(feed_id: str):
    conn = get_connection()
    cur = conn.execute("DELETE FROM rss_feeds WHERE id = ?", (feed_id,))
    conn.commit()
    conn.close()
    if cur.rowcount == 0:
        raise HTTPException(status_code=404, detail="Feed not found")
    return {"ok": True}


def get_rss_cards_list():
    """Return list of RSS card dicts (shared for feed assembly)."""
    conn = get_connection()
    rows = conn.execute("SELECT id, url FROM rss_feeds").fetchall()
    conn.close()

    all_entries = []
    for row in rows:
        try:
            parsed = feedparser.parse(row["url"])
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

    all_entries.sort(
        key=lambda e: e["published_at"],
        reverse=True,
    )
    return all_entries[:20]


@router.get("/cards")
def get_rss_cards():
    return get_rss_cards_list()
