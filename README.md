# GoodScroll

AI-powered project assistant that generates targeted question cards to extract context about your projects.

The product specification lives in [scroll-app-spec.md](scroll-app-spec.md).

## Requirements

- Python 3.11 or newer
- Node.js 20 or newer (Node 22 is what CI uses)
- Docker, for the local PostgreSQL instance
- An Anthropic API key

## Quick Start

```bash
make install                 # virtualenv + Python deps + npm install
make db                      # start PostgreSQL in Docker
cp .env.example .env         # then edit .env and set a real ANTHROPIC_API_KEY
make migrate                 # apply database migrations
make api                     # serve the API on http://localhost:8000
```

Then, in a second terminal:

```bash
cp app/.env.example app/.env # optional; the default already points at localhost
make web                     # start the Expo app in the browser
```

Run `make check` to lint the Python and typecheck the TypeScript.

The rest of this file spells out what those targets do, in case you would rather
run the steps by hand.

## PostgreSQL

Start a local PostgreSQL instance (Docker recommended):

```bash
docker run --name scrollapp-db \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=scrollapp \
  -p 5432:5432 \
  -d postgres:15
```

The container takes a couple of seconds to start accepting connections. If the
migration step below fails with a connection error, wait and run it again.

Once the container exists, restart it later with `docker start scrollapp-db`
(which is what `make db` does).

## Backend

```bash
# Create a virtual environment and install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt   # runtime deps plus ruff
```

Use `pip install -r backend/requirements.txt` instead if you want the runtime
dependencies only, without the linter.

```bash
# Configure environment
cp .env.example .env
```

Open `.env` and replace the `ANTHROPIC_API_KEY` placeholder with a real key.
`DATABASE_URL` already matches the Docker command above, so you can leave it
alone. `.env` is gitignored; never commit it.

The API also accepts a per-request key via the `X-Anthropic-Key` header, which
the app sends when you set one in its Settings screen. A key must be available
by one route or the other before card generation will work.

```bash
# Run database migrations
alembic upgrade head

# (Optional) Seed from an existing SQLite database
python scripts/seed_from_sqlite.py          # defaults to backend/scroll.db
# python scripts/seed_from_sqlite.py /path/to/scroll.db

# Run the server
uvicorn backend.main:app --reload
```

The API runs at `http://localhost:8000`, with interactive docs at
`http://localhost:8000/docs`.

`scripts/launch_backend.sh` runs all of the above in order — container,
migrations, optional seed, then uvicorn — if you would rather have one command.

## Frontend

```bash
cd app
npm install
npx expo start
```

Scan the QR code with Expo Go, or press `i` for iOS simulator / `w` for web.

The app talks to `http://127.0.0.1:8000` by default, which is correct for web
and for simulators running on the same machine. To point it somewhere else —
a physical device, for instance, where `127.0.0.1` is the phone itself — copy
`app/.env.example` to `app/.env` and set your machine's LAN IP:

```bash
EXPO_PUBLIC_API_URL=http://192.168.1.42:8000
```

Restart the Expo dev server after changing `app/.env`; the value is compiled
into the bundle at build time, so a hot reload will not pick it up.

## Checks

```bash
make check
```

That runs `ruff check .` over the Python tree and `tsc --noEmit` over the app.
Both also run in CI on every push (`.github/workflows/ci.yml`). There is no
automated test suite yet.

## Architecture

- **Frontend:** React Native + Expo (TypeScript), Zustand for state, React Navigation
- **Backend:** Python, FastAPI, PostgreSQL, SQLAlchemy (async), Alembic
- **AI:** Anthropic Claude claude-sonnet-4-6 for question generation and completeness evaluation

## Core Loop

1. Create a project with a description
2. AI generates 4–6 targeted question cards
3. Swipe through cards — answer or skip
4. Answers feed back into AI to generate the next round
5. Loop terminates when the AI determines sufficient context exists
