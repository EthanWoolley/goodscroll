"""Wikipedia summary fetch and project keyword extraction for feed cards."""
import json
import re
import uuid
from datetime import datetime, timezone
from urllib.parse import quote
from urllib.request import urlopen, Request

import anthropic


WIKI_SUMMARY_URL = "https://en.wikipedia.org/api/rest_v1/page/summary/{}"
KEYWORD_PROMPT = """Given this project title and description, return a JSON array of 2-3 short search terms suitable for a Wikipedia search. Focus on concrete topics, not verbs or generic words. Return only the JSON array, no preamble.

Title: {title}
Description: {description}"""


def _slugify(term: str) -> str:
    """Convert term to Wikipedia page title form (spaces to underscores)."""
    return term.strip().replace(" ", "_")


def _truncate_extract(text: str, max_len: int = 300) -> str:
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= max_len:
        return text
    truncated = text[: max_len + 1]
    last_space = truncated.rfind(" ")
    if last_space > 0:
        return truncated[:last_space].strip()
    return truncated[:max_len].strip()


def fetch_wikipedia_summary(term: str) -> dict | None:
    """Fetch page summary for a term. Returns dict with title, extract, url or None."""
    slug = _slugify(term)
    if not slug:
        return None
    encoded = quote(slug, safe="")
    url = WIKI_SUMMARY_URL.format(encoded)
    try:
        req = Request(url, headers={"User-Agent": "ScrollApp/1.0"})
        with urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode())
    except Exception:
        return None
    extract = data.get("extract") or data.get("description")
    if not extract:
        return None
    title = data.get("title") or term
    urls = data.get("content_urls") or {}
    mobile = urls.get("mobile") or {}
    page_url = mobile.get("page") or urls.get("desktop", {}).get("page") or ""
    if not page_url:
        return None
    thumbnail_url = None
    thumb = data.get("thumbnail")
    if thumb and isinstance(thumb, dict):
        thumbnail_url = thumb.get("source")
    elif thumb and hasattr(thumb, "source"):
        thumbnail_url = getattr(thumb, "source", None)

    return {
        "title": title,
        "extract": _truncate_extract(extract, 300),
        "url": page_url,
        "thumbnail_url": thumbnail_url,
    }


def extract_project_keywords(title: str, description: str, api_key: str | None = None) -> list[str]:
    """Call Anthropic to get 2-3 Wikipedia search terms from project title and description."""
    client = anthropic.Anthropic(api_key=api_key.strip()) if api_key and api_key.strip() else anthropic.Anthropic()
    prompt = KEYWORD_PROMPT.format(title=title or "", description=description or "")
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=256,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = (response.content[0].text or "").strip()
    if raw.startswith("```"):
        raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    try:
        terms = json.loads(raw)
        if isinstance(terms, list) and all(isinstance(t, str) for t in terms):
            return terms[:3]
        return []
    except json.JSONDecodeError:
        return []
