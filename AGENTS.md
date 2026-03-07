## Cursor Cloud specific instructions

### Overview

GoodScroll is a two-service app: a Python FastAPI backend and a React Native Expo frontend. See `README.md` for standard setup and run commands.

### Services

| Service | Command | Port | Notes |
|---------|---------|------|-------|
| Backend (FastAPI) | `source .venv/bin/activate && uvicorn backend.main:app --reload` | 8000 | Run from repo root. Requires PostgreSQL (see README). Run `alembic upgrade head` before first start. |
| Frontend (Expo web) | `cd app && CI=1 npx expo start --web --port 19006` | 19006 | Use `CI=1` to avoid interactive prompts. Web deps (`react-dom`, `react-native-web`) must be installed via `npx expo install react-dom react-native-web` in `app/`. |

### Environment

- `ANTHROPIC_API_KEY` must be set in a `.env` file at the repo root (loaded by `python-dotenv`). The frontend can alternatively pass it per-request via the `X-Anthropic-Key` header.
- `DATABASE_URL` must be set in `.env` (e.g. `postgresql+asyncpg://postgres:password@localhost:5432/scrollapp`). Start PostgreSQL via Docker: `docker run --name scrollapp-db -e POSTGRES_PASSWORD=password -e POSTGRES_DB=scrollapp -p 5432:5432 -d postgres:15`.
- The `BASE_URL` in `app/api/client.ts` is hardcoded to a developer's LAN IP. For cloud dev, change it to `http://127.0.0.1:8000` (use `127.0.0.1`, **not** `localhost` — Chrome in this environment resolves `localhost` to IPv6 `::1` first, which uvicorn doesn't bind to, causing `ERR_CONNECTION_RESET`).

### Gotchas

- `backend/routes/feed.py` contains leftover debug logging that writes to a hardcoded macOS path (`/Users/ethanwoolley/...`). The `/feed` endpoint will 500 unless that directory exists. Workaround: `sudo mkdir -p "/Users/ethanwoolley/Local Work/Good scroll/goodscroll/.cursor/" && sudo chmod 777 "/Users/ethanwoolley/Local Work/Good scroll/goodscroll/.cursor/"`.
- No ESLint or Python linter is configured. TypeScript checking: `cd app && npx tsc --noEmit`.
- No automated test suite exists in this codebase.
- `python3.12-venv` system package is required to create the Python virtual environment (`sudo apt-get install -y python3.12-venv`).
- After changing `app/api/client.ts`, you **must** restart the Expo dev server with `--clear` flag (or delete `.expo/` and `node_modules/.cache`) for the Metro bundler to pick up the new code. Hot reload does NOT reliably update the bundle for this file.
- The backend binds to `0.0.0.0:8000` but only IPv4; IPv6 (`::1`) connections will fail.
