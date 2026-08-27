"""Test doubles for the backend suite: a fake AsyncSession, a fake Anthropic
client, and factories for the ORM rows the handlers hand back.

The fake session replays a scripted list of results in the order the handler
issues its queries. That keeps the route tests free of a database, and so of
network access, at the cost of coupling each test to the number and order of
the queries its handler runs. When that drifts, the fake raises with an
explicit message rather than an obscure one.
"""

import uuid
from collections import deque
from datetime import datetime, timezone
from types import SimpleNamespace

from backend.db.models import Card, Project

UNSET = object()

# A fixed timestamp so ordering assertions do not depend on the wall clock.
FIXED_NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def row(**fields):
    """Stand in for a SQLAlchemy Row: attribute access over the selected columns."""
    return SimpleNamespace(**fields)


def make_project(
    project_id: uuid.UUID | None = None,
    title: str = "Test project",
    description: str = "A description",
    project_type: str = "creating",
    end_goal: str | None = None,
    deadline: str | None = None,
    created_at: datetime | None = None,
) -> Project:
    return Project(
        id=project_id or uuid.uuid4(),
        title=title,
        description=description,
        project_type=project_type,
        end_goal=end_goal,
        deadline=deadline,
        created_at=created_at or FIXED_NOW,
    )


def make_card(
    card_id: uuid.UUID | None = None,
    project_id: uuid.UUID | None = None,
    card_type: str = "open_ended",
    question: str = "What are you building?",
    options: list[str] | None = None,
    answer: str | None = None,
    topic: str | None = None,
    status: str = "unanswered",
    round_number: int = 1,
    created_at: datetime | None = None,
) -> Card:
    return Card(
        id=card_id or uuid.uuid4(),
        project_id=project_id or uuid.uuid4(),
        type=card_type,
        question=question,
        options=options,
        answer=answer,
        topic=topic,
        status=status,
        round=round_number,
        created_at=created_at or FIXED_NOW,
    )


class FakeScalars:
    def __init__(self, rows):
        self._rows = list(rows)

    def all(self):
        return list(self._rows)

    def first(self):
        return self._rows[0] if self._rows else None


class FakeResult:
    """One canned answer to ``AsyncSession.execute()``.

    ``rows`` covers ``.all()``, ``.first()`` and ``.scalars().all()``. Pass
    ``scalar`` when the handler calls ``.scalar_one_or_none()`` and the value it
    wants is not simply the single row, and ``rowcount`` for DELETE statements.
    """

    def __init__(self, rows=(), *, scalar=UNSET, rowcount=0):
        self._rows = list(rows)
        self._scalar = scalar
        self.rowcount = rowcount

    def all(self):
        return list(self._rows)

    def first(self):
        return self._rows[0] if self._rows else None

    def scalars(self):
        return FakeScalars(self._rows)

    def scalar_one_or_none(self):
        if self._scalar is not UNSET:
            return self._scalar
        if not self._rows:
            return None
        if len(self._rows) > 1:
            raise AssertionError("scalar_one_or_none() called on a multi-row FakeResult")
        return self._rows[0]


class FakeSession:
    """Async-session stand-in that replays scripted results in query order.

    ``results`` entries are :class:`FakeResult` instances, or exceptions to
    raise from ``execute()``. ``commit_effects`` does the same for ``commit()``:
    an entry of ``None`` commits normally, an exception is raised instead.
    """

    def __init__(self, results=(), commit_effects=()):
        self._results = deque(results)
        self._commit_effects = deque(commit_effects)
        self.executed = []
        self.added = []
        self.deleted = []
        self.refreshed = []
        self.commits = 0
        self.rollbacks = 0

    async def execute(self, statement, *args, **kwargs):
        self.executed.append(statement)
        if not self._results:
            raise AssertionError(
                "handler issued query #%d but the test scripted only %d result(s)"
                % (len(self.executed), len(self.executed) - 1)
            )
        nxt = self._results.popleft()
        if isinstance(nxt, Exception):
            raise nxt
        return nxt

    def add(self, obj):
        self.added.append(obj)

    async def delete(self, obj):
        self.deleted.append(obj)

    async def commit(self):
        self.commits += 1
        if self._commit_effects:
            effect = self._commit_effects.popleft()
            if isinstance(effect, Exception):
                raise effect

    async def rollback(self):
        self.rollbacks += 1

    async def refresh(self, obj, *args, **kwargs):
        self.refreshed.append(obj)

    @property
    def unused_results(self) -> int:
        return len(self._results)

    def added_of(self, model):
        """Every object handed to ``add()`` that is an instance of ``model``."""
        return [obj for obj in self.added if isinstance(obj, model)]


class FakeMessages:
    def __init__(self, recorder):
        self._recorder = recorder

    def create(self, **kwargs):
        self._recorder.calls.append(kwargs)
        if not self._recorder.responses:
            raise AssertionError(
                "messages.create() called more times than the test queued responses"
            )
        nxt = self._recorder.responses.popleft()
        if isinstance(nxt, Exception):
            raise nxt
        return SimpleNamespace(content=[SimpleNamespace(text=nxt)])


class FakeAnthropicClient:
    def __init__(self, recorder, api_key):
        self.api_key = api_key
        self.messages = FakeMessages(recorder)


class AnthropicRecorder:
    """Drop-in for ``anthropic.Anthropic``: calling it constructs a fake client.

    Queue the text each ``messages.create()`` should return with ``queue()``, or
    queue an exception to have the call raise.
    """

    def __init__(self):
        self.responses = deque()
        self.calls = []
        self.api_keys = []

    def queue(self, *responses):
        self.responses.extend(responses)
        return self

    def __call__(self, api_key=None, **kwargs):
        self.api_keys.append(api_key)
        return FakeAnthropicClient(self, api_key)
