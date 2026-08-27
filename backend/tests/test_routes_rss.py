"""Route handlers and feed-parsing helpers in backend.routes.rss.

feedparser is patched at the name rss.py imported it under, so the entry
shapes below stand in for parsed network responses.
"""

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy.exc import IntegrityError

from backend.db.models import RssFeed
from backend.routes import rss as rss_route
from backend.routes.rss import _extract_image_url, _parse_published, _truncate_summary
from backend.tests.support import FIXED_NOW, FakeResult, FakeSession, row

FEED_ID = uuid.UUID("33333333-3333-3333-3333-333333333333")


def entry(**fields):
    """A feedparser entry stand-in; absent keys behave as absent attributes."""
    return SimpleNamespace(**fields)


def parsed_feed(title="Example Feed", entries=()):
    return SimpleNamespace(feed=SimpleNamespace(title=title), entries=list(entries))


# ---------------------------------------------------------------------------
# _truncate_summary
# ---------------------------------------------------------------------------

def test_truncate_summary_collapses_whitespace():
    assert _truncate_summary("a  b\n\tc") == "a b c"


def test_truncate_summary_leaves_short_text_alone():
    assert _truncate_summary("Short enough") == "Short enough"


def test_truncate_summary_cuts_at_a_word_boundary():
    text = " ".join(["word"] * 100)

    result = _truncate_summary(text, max_len=20)

    assert len(result) <= 20
    assert not result.endswith("wor")


def test_truncate_summary_of_empty_text_is_empty():
    assert _truncate_summary("") == ""


def test_truncate_summary_falls_back_when_there_is_no_space_to_cut_at():
    """A single long token has no word boundary, so it is cut mid-token."""
    result = _truncate_summary("x" * 300, max_len=50)

    assert result == "x" * 51


def test_truncate_summary_keeps_text_exactly_at_the_limit():
    assert _truncate_summary("x" * 200) == "x" * 200


# ---------------------------------------------------------------------------
# _extract_image_url
# ---------------------------------------------------------------------------

def test_extract_image_url_prefers_media_content():
    result = _extract_image_url(
        entry(
            media_content=[{"url": "https://example.com/a.jpg"}],
            media_thumbnail=[{"url": "https://example.com/b.jpg"}],
        )
    )

    assert result == "https://example.com/a.jpg"


def test_extract_image_url_falls_back_to_media_thumbnail():
    result = _extract_image_url(entry(media_thumbnail=[{"url": "https://example.com/b.jpg"}]))

    assert result == "https://example.com/b.jpg"


def test_extract_image_url_falls_back_to_an_image_enclosure():
    result = _extract_image_url(
        entry(
            enclosures=[
                {"type": "audio/mpeg", "href": "https://example.com/a.mp3"},
                {"type": "image/png", "href": "https://example.com/c.png"},
            ]
        )
    )

    assert result == "https://example.com/c.png"


def test_extract_image_url_ignores_non_image_enclosures():
    result = _extract_image_url(
        entry(enclosures=[{"type": "audio/mpeg", "href": "https://example.com/a.mp3"}])
    )

    assert result is None


def test_extract_image_url_scrapes_an_img_tag_from_the_summary():
    result = _extract_image_url(
        entry(summary='<p>Hi</p><img src="https://example.com/d.jpg" alt="x">')
    )

    assert result == "https://example.com/d.jpg"


def test_extract_image_url_reads_a_dict_shaped_summary():
    """feedparser sometimes hands back a detail dict rather than a string."""
    result = _extract_image_url(entry(summary={"value": '<img src="https://example.com/e.jpg">'}))

    assert result == "https://example.com/e.jpg"


def test_extract_image_url_returns_none_when_there_is_nothing_to_find():
    assert _extract_image_url(entry(summary="Just words")) is None


def test_extract_image_url_handles_empty_media_lists():
    assert _extract_image_url(entry(media_content=[], media_thumbnail=[])) is None


# ---------------------------------------------------------------------------
# _parse_published
# ---------------------------------------------------------------------------

def test_parse_published_prefers_the_raw_published_string():
    assert _parse_published(entry(published="Mon, 01 Jan 2026 00:00:00 GMT")) == (
        "Mon, 01 Jan 2026 00:00:00 GMT"
    )


def test_parse_published_falls_back_to_the_parsed_struct():
    result = _parse_published(entry(published_parsed=(2026, 1, 1, 12, 0, 0, 0, 1, 0)))

    assert datetime.fromisoformat(result).year == 2026


def test_parse_published_defaults_to_now_when_absent():
    before = datetime.now(timezone.utc)

    result = datetime.fromisoformat(_parse_published(entry(title="No date")))

    assert result >= before


def test_parse_published_defaults_to_now_on_an_out_of_range_struct():
    """mktime raises for values it cannot represent; the handler falls through."""
    result = _parse_published(entry(published_parsed=(999999, 1, 1, 0, 0, 0, 0, 1, 0)))

    assert datetime.fromisoformat(result).year == datetime.now(timezone.utc).year


# ---------------------------------------------------------------------------
# POST /rss/feeds
# ---------------------------------------------------------------------------

def test_add_feed_stores_the_url(client_factory):
    session = FakeSession([])

    resp = client_factory(session).post(
        "/rss/feeds", json={"url": "  https://example.com/feed.xml  "}
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["url"] == "https://example.com/feed.xml"
    uuid.UUID(body["id"])
    assert len(session.added_of(RssFeed)) == 1


def test_add_feed_rejects_a_blank_url(client_factory):
    session = FakeSession([])

    resp = client_factory(session).post("/rss/feeds", json={"url": "   "})

    assert resp.status_code == 400
    assert resp.json()["detail"] == "url is required"
    assert session.added == []


def test_add_feed_reports_a_duplicate_as_409(client_factory):
    session = FakeSession(
        commit_effects=[IntegrityError("INSERT", {}, Exception("duplicate key"))]
    )

    resp = client_factory(session).post("/rss/feeds", json={"url": "https://example.com/f.xml"})

    assert resp.status_code == 409
    assert resp.json()["detail"] == "Feed URL already added"
    assert session.rollbacks == 1


def test_add_feed_without_a_url_field_is_422(client_factory):
    resp = client_factory(FakeSession([])).post("/rss/feeds", json={})

    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET and DELETE /rss/feeds
# ---------------------------------------------------------------------------

def test_list_feeds_returns_stored_feeds(client_factory):
    feed = RssFeed(id=FEED_ID, url="https://example.com/feed.xml", created_at=FIXED_NOW)
    session = FakeSession([FakeResult(rows=[feed])])

    resp = client_factory(session).get("/rss/feeds")

    assert resp.json() == [
        {
            "id": str(FEED_ID),
            "url": "https://example.com/feed.xml",
            "created_at": FIXED_NOW.isoformat(),
        }
    ]


def test_list_feeds_with_none_returns_an_empty_list(client_factory):
    assert client_factory(FakeSession([FakeResult(rows=[])])).get("/rss/feeds").json() == []


def test_delete_feed_removes_it(client_factory):
    session = FakeSession([FakeResult(rowcount=1)])

    resp = client_factory(session).delete(f"/rss/feeds/{FEED_ID}")

    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
    assert session.commits == 1


def test_delete_feed_that_does_not_exist_is_404(client_factory):
    session = FakeSession([FakeResult(rowcount=0)])

    resp = client_factory(session).delete(f"/rss/feeds/{FEED_ID}")

    assert resp.status_code == 404
    assert resp.json()["detail"] == "Feed not found"


def test_delete_feed_with_a_malformed_id_is_a_server_error(client_factory):
    resp = client_factory(FakeSession([]), raise_server_exceptions=False).delete(
        "/rss/feeds/not-a-uuid"
    )

    assert resp.status_code == 500


# ---------------------------------------------------------------------------
# GET /rss/cards
# ---------------------------------------------------------------------------

def test_get_rss_cards_builds_cards_from_entries(client_factory, monkeypatch):
    monkeypatch.setattr(
        rss_route.feedparser,
        "parse",
        lambda url: parsed_feed(
            "Example Feed",
            [
                entry(
                    id="entry-1",
                    link="https://example.com/a",
                    title="First post",
                    summary="A  summary",
                    published="2026-01-02T00:00:00+00:00",
                )
            ],
        ),
    )
    session = FakeSession([FakeResult(rows=[row(id=FEED_ID, url="https://example.com/f.xml")])])

    resp = client_factory(session).get("/rss/cards")

    assert resp.status_code == 200
    assert resp.json() == [
        {
            "id": "entry-1",
            "type": "rss",
            "title": "First post",
            "source": "Example Feed",
            "summary": "A summary",
            "url": "https://example.com/a",
            "published_at": "2026-01-02T00:00:00+00:00",
            "image_url": None,
        }
    ]


def test_get_rss_cards_skips_entries_with_no_link(client_factory, monkeypatch):
    monkeypatch.setattr(
        rss_route.feedparser,
        "parse",
        lambda url: parsed_feed(entries=[entry(id="no-link", title="Skipped")]),
    )
    session = FakeSession([FakeResult(rows=[row(id=FEED_ID, url="https://example.com/f.xml")])])

    assert client_factory(session).get("/rss/cards").json() == []


def test_get_rss_cards_sorts_newest_first_and_caps_at_20(client_factory, monkeypatch):
    entries = [
        entry(
            id=f"entry-{i}",
            link=f"https://example.com/{i}",
            title=f"Post {i}",
            summary="s",
            published=f"2026-01-{i + 1:02d}T00:00:00+00:00",
        )
        for i in range(25)
    ]
    monkeypatch.setattr(rss_route.feedparser, "parse", lambda url: parsed_feed(entries=entries))
    session = FakeSession([FakeResult(rows=[row(id=FEED_ID, url="https://example.com/f.xml")])])

    body = client_factory(session).get("/rss/cards").json()

    assert len(body) == 20
    assert body[0]["published_at"] > body[1]["published_at"]


def test_get_rss_cards_skips_a_feed_that_fails_to_parse(client_factory, monkeypatch):
    """One broken feed must not take the whole response down."""

    def parse(url):
        if "broken" in url:
            raise ValueError("malformed feed")
        return parsed_feed(
            entries=[
                entry(
                    id="ok-1",
                    link="https://example.com/ok",
                    title="Fine",
                    summary="s",
                    published="2026-01-01T00:00:00+00:00",
                )
            ]
        )

    monkeypatch.setattr(rss_route.feedparser, "parse", parse)
    session = FakeSession(
        [
            FakeResult(
                rows=[
                    row(id=FEED_ID, url="https://example.com/broken.xml"),
                    row(id=uuid.uuid4(), url="https://example.com/good.xml"),
                ]
            )
        ]
    )

    body = client_factory(session).get("/rss/cards").json()

    assert [c["id"] for c in body] == ["ok-1"]


def test_get_rss_cards_generates_an_id_when_the_entry_has_none(client_factory, monkeypatch):
    monkeypatch.setattr(
        rss_route.feedparser,
        "parse",
        lambda url: parsed_feed(
            entries=[
                entry(
                    link="https://example.com/a",
                    title="No id",
                    summary="s",
                    published="2026-01-01T00:00:00+00:00",
                )
            ]
        ),
    )
    session = FakeSession([FakeResult(rows=[row(id=FEED_ID, url="https://example.com/f.xml")])])

    body = client_factory(session).get("/rss/cards").json()

    uuid.UUID(body[0]["id"])


def test_get_rss_cards_with_no_feeds_configured_is_empty(client_factory):
    assert client_factory(FakeSession([FakeResult(rows=[])])).get("/rss/cards").json() == []


async def test_get_rss_cards_list_is_awaitable_directly(monkeypatch):
    """feed.py calls this helper rather than the endpoint, so it is exercised too."""
    monkeypatch.setattr(rss_route.feedparser, "parse", lambda url: parsed_feed(entries=[]))
    session = FakeSession([FakeResult(rows=[row(id=FEED_ID, url="https://example.com/f.xml")])])

    assert await rss_route.get_rss_cards_list(session) == []


@pytest.mark.parametrize("missing_title", [True, False])
def test_get_rss_cards_defaults_an_unknown_feed_title(
    client_factory, monkeypatch, missing_title
):
    feed = SimpleNamespace() if missing_title else SimpleNamespace(title="Named Feed")
    monkeypatch.setattr(
        rss_route.feedparser,
        "parse",
        lambda url: SimpleNamespace(
            feed=feed,
            entries=[
                entry(
                    id="e",
                    link="https://example.com/a",
                    title="T",
                    summary="s",
                    published="2026-01-01T00:00:00+00:00",
                )
            ],
        ),
    )
    session = FakeSession([FakeResult(rows=[row(id=FEED_ID, url="https://example.com/f.xml")])])

    body = client_factory(session).get("/rss/cards").json()

    assert body[0]["source"] == ("Unknown" if missing_title else "Named Feed")
