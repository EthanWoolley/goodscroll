# Agent instructions

## Overview

GoodScroll is a two-service app: a Python FastAPI backend and a React Native
Expo frontend. `README.md` has the setup and run commands; this file covers what
is specific to working in the repo rather than using it.

## Layout

| Path | What lives there |
|------|------------------|
| `backend/routes/` | FastAPI endpoints. `feed.py` builds the interleaved feed. |
| `backend/services/` | Anthropic prompt chains and the Wikipedia client. Prompt text is here. |
| `backend/db/` | SQLAlchemy models and the async session/engine. |
| `alembic/versions/` | Migrations. |
| `app/` | The Expo app. `api/client.ts` is the single place the backend is called from. |
| `scripts/` | `launch_backend.sh` (full local bring-up) and `seed_from_sqlite.py`. |

## Services

| Service | Command | Port |
|---------|---------|------|
| Backend (FastAPI) | `make api`, or `.venv/bin/uvicorn backend.main:app --reload` | 8000 |
| Frontend (Expo web) | `make web`, or `cd app && npx expo start --web` | 8081 by default |

Run both from the repo root. The backend needs PostgreSQL running and
`alembic upgrade head` applied at least once.

In a non-interactive environment, set `CI=1` before `expo start` to skip the
interactive prompts.

## Environment

Two `.env` files, both gitignored, both with a checked-in `.env.example`:

- `.env` at the repo root — `ANTHROPIC_API_KEY` and `DATABASE_URL`. Loaded by
  `python-dotenv` in `backend/main.py`, `alembic/env.py` and the seed script.
- `app/.env` — `EXPO_PUBLIC_API_URL`, the backend base URL. Optional; the app
  falls back to `http://127.0.0.1:8000`.

`.env.example` is the source of truth for what the code reads. If you add a new
variable, add it there in the same commit.

The frontend can also supply the Anthropic key per request via the
`X-Anthropic-Key` header, which every route prefers over the server's own key
when present.

## Checks

`make check` runs both:

- `ruff check .` — configured in `pyproject.toml`, line length 100.
- `cd app && npm run typecheck` — `tsc --noEmit`.

`make test` runs the backend suite in `backend/tests/`. All three run in CI on
push and pull request (`.github/workflows/ci.yml`).

The suite covers the backend's non-AI logic only, and runs without PostgreSQL,
without an Anthropic key and without network access:

- `anthropic.Anthropic` is patched out per test by the `anthropic_stub`
  fixture, which queues canned response text.
- Route handlers get a `FakeSession` through a `get_db` dependency override. It
  replays scripted results in the order the handler queries, so a test breaks
  loudly when a handler gains or loses a query. It does not run SQL, so query
  correctness is not covered — exercise that against a running backend.
- An autouse fixture blocks `socket.connect`. A test that reaches for the
  network fails rather than hanging.

There is no frontend test suite.

Two ruff exemptions are deliberate and should not be "cleaned up":

- `E402` is ignored in `backend/main.py` and `scripts/seed_from_sqlite.py`.
  Import order there is load-bearing — `load_dotenv()` has to run before
  `backend.db.session` is imported, because that module reads `DATABASE_URL` at
  import time.
- `fastapi.Depends` is registered as an immutable call, so `db: AsyncSession =
  Depends(get_db)` does not trip `B008`.

## Gotchas

- Prompt text in `backend/services/` is wrapped with backslash line
  continuations to stay under the line limit. The backslashes are what keep the
  strings byte-identical to how they read; if you reflow a prompt, keep them, or
  you will silently change what is sent to the model.
- `EXPO_PUBLIC_API_URL` is compiled into the bundle at build time. After
  changing `app/.env`, restart the Expo dev server — hot reload will not pick it
  up. `npx expo start --clear` if a stale value persists.
- `uvicorn` binds `127.0.0.1` by default and IPv4 only. A browser that resolves
  `localhost` to IPv6 `::1` will fail to connect; this is why `api/client.ts`
  defaults to `127.0.0.1` rather than `localhost`. `launch_backend.sh` passes
  `--host 0.0.0.0` for access from other devices.
- `backend/main.py` calls `Base.metadata.create_all` on startup, so a fresh
  database will get tables even without migrations. Alembic is still the source
  of truth — add a migration for schema changes rather than relying on this.
- `scripts/seed_from_sqlite.py` is a no-op, exiting 0, if no SQLite file is
  present. It is optional; skip it on a fresh install.
