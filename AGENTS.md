## Cursor Cloud specific instructions

### Overview

GoodScroll is a two-service app: a Python FastAPI backend and a React Native Expo frontend. See `README.md` for standard setup and run commands.

### Services

| Service | Command | Port | Notes |
|---------|---------|------|-------|
| Backend (FastAPI) | `source .venv/bin/activate && uvicorn backend.main:app --reload` | 8000 | Run from repo root. SQLite DB auto-creates on startup. |
| Frontend (Expo web) | `cd app && CI=1 npx expo start --web --port 19006` | 19006 | Use `CI=1` to avoid interactive prompts. Web deps (`react-dom`, `react-native-web`) must be installed via `npx expo install react-dom react-native-web` in `app/`. |

### Environment

- `ANTHROPIC_API_KEY` must be set in a `.env` file at the repo root (loaded by `python-dotenv`). The frontend can alternatively pass it per-request via the `X-Anthropic-Key` header.
- The `BASE_URL` in `app/api/client.ts` is hardcoded to `192.168.1.109:8000`. For local/cloud dev, this should point to `localhost:8000`.

### Gotchas

- `backend/routes/feed.py` contains leftover debug logging that writes to a hardcoded macOS path (`/Users/ethanwoolley/...`). The `/feed` endpoint will 500 unless that directory exists. Workaround: `sudo mkdir -p "/Users/ethanwoolley/Local Work/Good scroll/goodscroll/.cursor/" && sudo chmod 777 "/Users/ethanwoolley/Local Work/Good scroll/goodscroll/.cursor/"`.
- No ESLint or Python linter is configured. TypeScript checking: `cd app && npx tsc --noEmit`.
- No automated test suite exists in this codebase.
- `python3.12-venv` system package is required to create the Python virtual environment (`sudo apt-get install -y python3.12-venv`).
