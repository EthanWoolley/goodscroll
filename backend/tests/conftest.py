"""Shared fixtures. Two rules hold for every test in this package.

No network. An autouse fixture blocks outbound socket connections and the two
``urlopen`` names the Wikipedia services imported, so a test that reaches for
Anthropic, Wikipedia or PostgreSQL fails loudly instead of hanging.

No database. Route handlers get a :class:`~backend.tests.support.FakeSession`
through FastAPI's dependency override for ``get_db``. These tests therefore
cover handler logic — status codes, branching, response shaping — and not the
SQL those handlers build.
"""

import socket

import anthropic
import pytest
from fastapi.testclient import TestClient

from backend.db.session import get_db
from backend.main import app
from backend.services import wikipedia_category_service, wikipedia_service
from backend.tests.support import AnthropicRecorder, FakeSession


@pytest.fixture(autouse=True)
def block_network(monkeypatch):
    """Fail any attempt to open an outbound connection.

    ``socket.socket.connect`` is the choke point every HTTP client ends up at.
    Blocking it rather than socket construction leaves ``socket.socketpair()``
    alone, which asyncio needs for its self-pipe.
    """

    def blocked(*args, **kwargs):
        raise RuntimeError("network access is not allowed in the test suite")

    monkeypatch.setattr(socket.socket, "connect", blocked)
    monkeypatch.setattr(socket.socket, "connect_ex", blocked)
    monkeypatch.setattr(socket, "create_connection", blocked)
    # Both services did `from urllib.request import urlopen`, so the module-level
    # name has to be patched directly. The socket guard above would catch these
    # anyway; patching here just makes the failure name the culprit.
    monkeypatch.setattr(wikipedia_service, "urlopen", blocked)
    monkeypatch.setattr(wikipedia_category_service, "urlopen", blocked)


@pytest.fixture
def anthropic_stub(monkeypatch):
    """Replace ``anthropic.Anthropic`` everywhere with a recording fake.

    Every service reaches the SDK through ``anthropic.Anthropic(...)`` at call
    time, so patching the attribute on the module covers all of them at once.
    """
    recorder = AnthropicRecorder()
    monkeypatch.setattr(anthropic, "Anthropic", recorder)
    return recorder


@pytest.fixture
def client_factory():
    """Build a TestClient whose ``get_db`` yields the supplied fake session.

    The client is deliberately not used as a context manager: entering one runs
    the app's lifespan, which calls ``create_all`` against the real engine and
    would need a live PostgreSQL.
    """
    clients = []

    def make(session: FakeSession, *, raise_server_exceptions: bool = True) -> TestClient:
        app.dependency_overrides[get_db] = lambda: session
        client = TestClient(app, raise_server_exceptions=raise_server_exceptions)
        clients.append(client)
        return client

    yield make

    app.dependency_overrides.clear()
