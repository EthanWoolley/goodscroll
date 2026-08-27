"""Wikipedia category API: subcategories, category sizes, and random articles."""
import json
import random
from urllib.parse import quote
from urllib.request import Request, urlopen

from backend.services.wikipedia_service import fetch_wikipedia_summary

WIKI_API_URL = "https://en.wikipedia.org/w/api.php"
USER_AGENT = "ScrollApp/1.0"

INTEREST_TO_CATEGORY = {
    "Technology": "Category:Technology",
    "Science": "Category:Science",
    "History": "Category:History",
    "Design": "Category:Design",
    "Business": "Category:Business",
    "Psychology": "Category:Psychology",
    "Philosophy": "Category:Philosophy",
    "Health": "Category:Health",
    "Economics": "Category:Economics",
    "Space": "Category:Outer_space",
    "Politics": "Category:Politics",
    "Mathematics": "Category:Mathematics",
}

DRILLDOWN_READ_THRESHOLD = 3
SUBCATEGORY_OPTIONS_COUNT = 8


def _wiki_api_get(params: dict) -> dict | None:
    params.setdefault("format", "json")
    qs = "&".join(f"{k}={quote(str(v), safe='|:')}" for k, v in params.items())
    url = f"{WIKI_API_URL}?{qs}"
    try:
        req = Request(url, headers={"User-Agent": USER_AGENT})
        with urlopen(req, timeout=5) as resp:
            return json.loads(resp.read().decode())
    except Exception:
        return None


def fetch_subcategories(category_title: str, limit: int = 50) -> list[str]:
    """Return subcategory titles (e.g. 'Category:Foo') for a given category."""
    data = _wiki_api_get({
        "action": "query",
        "list": "categorymembers",
        "cmtitle": category_title,
        "cmtype": "subcat",
        "cmlimit": str(limit),
    })
    if not data:
        return []
    members = data.get("query", {}).get("categorymembers", [])
    return [m["title"] for m in members if "title" in m]


def fetch_category_sizes(category_titles: list[str]) -> dict[str, int]:
    """Return {category_title: page_count} using categoryinfo prop."""
    if not category_titles:
        return {}
    batch_size = 50
    result = {}
    for i in range(0, len(category_titles), batch_size):
        batch = category_titles[i : i + batch_size]
        titles_param = "|".join(batch)
        data = _wiki_api_get({
            "action": "query",
            "titles": titles_param,
            "prop": "categoryinfo",
        })
        if not data:
            continue
        pages = data.get("query", {}).get("pages", {})
        for page in pages.values():
            title = page.get("title", "")
            info = page.get("categoryinfo", {})
            result[title] = info.get("pages", 0)
    return result


def top_subcategories_by_size(
    category_title: str, count: int = SUBCATEGORY_OPTIONS_COUNT
) -> list[str]:
    """Fetch subcategories and return the top N by article count."""
    subcats = fetch_subcategories(category_title)
    if not subcats:
        return []
    sizes = fetch_category_sizes(subcats)
    subcats.sort(key=lambda s: sizes.get(s, 0), reverse=True)
    return subcats[:count]


def strip_category_prefix(title: str) -> str:
    if title.startswith("Category:"):
        return title[len("Category:"):]
    return title


def random_articles_from_category(
    category_title: str, count: int = 3, exclude_titles: set[str] | None = None
) -> list[dict]:
    """Fetch random article summaries from a category.

    Returns list of dicts with keys: title, extract, url, thumbnail_url, source_category.
    """
    exclude_titles = exclude_titles or set()
    data = _wiki_api_get({
        "action": "query",
        "list": "categorymembers",
        "cmtitle": category_title,
        "cmtype": "page",
        "cmlimit": "500",
    })
    if not data:
        return []
    members = data.get("query", {}).get("categorymembers", [])
    page_titles = [
        m["title"]
        for m in members
        if "title" in m and m["title"] not in exclude_titles
    ]
    if not page_titles:
        return []
    chosen = random.sample(page_titles, min(count, len(page_titles)))
    articles = []
    for title in chosen:
        summary = fetch_wikipedia_summary(title)
        if summary:
            summary["source_category"] = category_title
            articles.append(summary)
    return articles
