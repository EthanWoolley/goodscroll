# GoodScroll

AI-powered project assistant that generates targeted question cards to extract context about your projects.

## Quick Start

### Backend

```bash
# Create a virtual environment and install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

# Set your Anthropic API key
echo 'ANTHROPIC_API_KEY=sk-ant-...' > .env

# Run the server
uvicorn backend.main:app --reload
```

The API runs at `http://localhost:8000`.

### Frontend

```bash
cd app
npm install
npx expo start
```

Scan the QR code with Expo Go, or press `i` for iOS simulator / `w` for web.

If testing on a physical device, update the `BASE_URL` in `app/api/client.ts` to your machine's local IP.

## Architecture

- **Frontend:** React Native + Expo (TypeScript), Zustand for state, React Navigation
- **Backend:** Python, FastAPI, SQLite
- **AI:** Anthropic Claude claude-sonnet-4-6 for question generation and completeness evaluation

## Core Loop

1. Create a project with a description
2. AI generates 4–6 targeted question cards
3. Swipe through cards — answer or skip
4. Answers feed back into AI to generate the next round
5. Loop terminates when the AI determines sufficient context exists
