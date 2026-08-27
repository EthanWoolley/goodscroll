"""Route handlers in backend.routes.users."""

from backend.db.models import UserInterest
from backend.tests.support import FIXED_NOW, FakeResult, FakeSession


def test_post_interests_maps_known_labels_to_categories(client_factory):
    session = FakeSession([FakeResult(scalar=None)])

    resp = client_factory(session).post(
        "/users/interests", json={"interests": ["Technology", "Space"]}
    )

    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
    stored = session.added_of(UserInterest)[0]
    assert stored.interests == ["Category:Technology", "Category:Outer_space"]
    assert stored.id == "default_user"


def test_post_interests_falls_back_to_a_prefixed_label_when_unmapped(client_factory):
    """An interest outside INTEREST_TO_CATEGORY still becomes a category title."""
    session = FakeSession([FakeResult(scalar=None)])

    client_factory(session).post("/users/interests", json={"interests": ["Cars"]})

    assert session.added_of(UserInterest)[0].interests == ["Category:Cars"]


def test_post_interests_updates_the_existing_row(client_factory):
    existing = UserInterest(
        id="default_user", interests=["Category:History"], updated_at=FIXED_NOW
    )
    session = FakeSession([FakeResult(scalar=existing), FakeResult()])

    resp = client_factory(session).post(
        "/users/interests", json={"interests": ["Technology"]}
    )

    assert resp.status_code == 200
    assert session.added_of(UserInterest) == []
    assert session.commits == 1


def test_post_interests_accepts_an_empty_list(client_factory):
    session = FakeSession([FakeResult(scalar=None)])

    resp = client_factory(session).post("/users/interests", json={"interests": []})

    assert resp.status_code == 200
    assert session.added_of(UserInterest)[0].interests == []


def test_post_interests_without_the_field_is_422(client_factory):
    resp = client_factory(FakeSession([])).post("/users/interests", json={})

    assert resp.status_code == 422


def test_post_interests_with_a_non_list_is_422(client_factory):
    resp = client_factory(FakeSession([])).post(
        "/users/interests", json={"interests": "Technology"}
    )

    assert resp.status_code == 422


def test_get_interests_returns_the_stored_categories(client_factory):
    session = FakeSession([FakeResult(scalar=["Category:Technology"])])

    resp = client_factory(session).get("/users/interests")

    assert resp.status_code == 200
    assert resp.json() == ["Category:Technology"]


def test_get_interests_returns_an_empty_list_when_unset(client_factory):
    session = FakeSession([FakeResult(scalar=None)])

    resp = client_factory(session).get("/users/interests")

    assert resp.status_code == 200
    assert resp.json() == []


def test_get_interests_returns_an_empty_list_for_a_stored_empty_row(client_factory):
    """An empty list is falsy, so it takes the same branch as a missing row."""
    session = FakeSession([FakeResult(scalar=[])])

    assert client_factory(session).get("/users/interests").json() == []
