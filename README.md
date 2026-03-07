# GoodScroll

AI-powered project assistant that generates targeted question cards to extract context about your projects.

## Quick Start

### PostgreSQL

Start a local PostgreSQL instance (Docker recommended):

```bash
docker run --name scrollapp-db \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=scrollapp \
  -p 5432:5432 \
  -d postgres:15
```

### Backend

```bash
# Create a virtual environment and install dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

# Configure environment
cat > .env << 'EOF'
ANTHROPIC_API_KEY=sk-ant-...
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/scrollapp
EOF

# Run database migrations
alembic upgrade head

# (Optional) Seed from an existing SQLite database
python scripts/seed_from_sqlite.py          # defaults to backend/scroll.db
# python scripts/seed_from_sqlite.py /path/to/scroll.db

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
- **Backend:** Python, FastAPI, PostgreSQL, SQLAlchemy (async), Alembic
- **AI:** Anthropic Claude claude-sonnet-4-6 for question generation and completeness evaluation

## Core Loop

1. Create a project with a description
2. AI generates 4–6 targeted question cards
3. Swipe through cards — answer or skip
4. Answers feed back into AI to generate the next round
5. Loop terminates when the AI determines sufficient context exists



# GoodScroll — Product Specification (MVP)

## Core Concept

An infinite scroll feed that hijacks the passive scroll habit and makes it productive. Users define projects and goals; the app surfaces AI-generated question cards to extract structured knowledge, learning snippet cards to fill gaps, and RSS content from sources they already trust. Background agents (v2) will act on decisions made in the feed.

**Thesis:** You're going to scroll anyway. Scroll this instead.

---

## Target User

**Primary (MVP):** Solo developers who already self-host tools or tinker with AI setups (Claude bots, automation scripts, etc.). Comfortable with BYOK and manual configuration.

**Secondary (later):** Students, job hunters, anyone managing personal projects independently.

---

## Two Project Types

### Creating Projects
The user has the expertise. The agent extracts it through questions and builds structured documentation. The output is a living document: a master CV, a README, a structured coding agent prompt, etc.

### Learning Projects
The user lacks expertise. The agent identifies knowledge gaps, surfaces learning content, and tests retention through quiz/flashcard cards. The output is mastery, not a document.

This distinction is surfaced clearly during project setup.

---

## Feed Card Types

### Decision Cards (Creating Projects)
AI-generated questions to extract knowledge and make project decisions. Mix of multiple choice (programmatic, no typing required) and open-ended text input. Skipped cards return at the top of the next session.

### Quiz / Flashcard Cards (Learning Projects)
Question cards used for active recall testing. User is put on the spot. Used to assess and reinforce learning progress.

### Learning Snippet Cards
Short summaries of web content or Wikipedia sections. Surfaced two ways: pushed by a project agent when it detects a knowledge gap, or pulled from interest categories the user set at onboarding.

### RSS Cards
Articles from RSS feeds the user has manually connected. Headline, source, and short summary shown in-card. Full article opens externally. Provides feed volume without significant token cost.

### Completion / Status Cards
Surfaced when a project agent judges that the minimum information threshold has been met. Notifies the user that a document is ready to generate on request. (Agent status cards for background task updates are v2.)

---

## Per-Project Agent

Each project has its own persistent agent with its own context store.

**Agent responsibilities:**
- Ingest the project setup template on creation
- Generate a first round of question cards (mix of multiple choice and open-ended)
- Append user answers to a raw response store
- Evaluate after each round whether minimum information criteria have been met
- If criteria unmet: generate another round of questions
- If criteria met: surface a completion card
- Push learning snippet cards into the feed when a knowledge gap is detected
- Accept user-volunteered information at any time

**Two stores per project:**
- Raw response bank: all user answers, used as ongoing context for question generation
- Generated document: produced on demand only, format varies by project type (markdown)

The minimum information criteria are defined per project type from the start, so the agent has a clear checklist rather than an open-ended loop.

---

## Feed Queue Logic

Priority order within the feed:

1. Skipped question cards from the previous session (always first on return)
2. Agent-pushed cards (knowledge gaps, completion notifications)
3. RSS cards from connected feeds
4. Interest-based learning snippet cards

Users can save any card for later re-surfacing.

---

## Onboarding Flow

**Step 1 — Interests**
User picks from a curated list of interest categories (e.g. cars, history, tech, design). Each category maps to known content sources (Wikipedia domains, RSS feeds, etc.).

**Step 2 — Project Setup**
User creates one or more projects using a structured template form. Template fields:
- Title
- Description / brain dump (free text)
- Project type: Creating or Learning
- End goal
- Deadline or ongoing
- Any known tasks or subtasks

No AI-generated questions at this stage. Template questions are universal and fixed. This keeps onboarding cost predictable.

**Step 3 — Feed Begins**
Project agent ingests the template and generates the first round of question cards. Feed starts.

---

## RSS Integration

**MVP:** Manual URL input. User pastes RSS feed URLs (e.g. TechCrunch, Hacker News, niche blogs). No curation layer.

**Roadmap:** Curated directory of common sources, one-tap subscribe.

---

## Technical Architecture (MVP)

### Platform
React Native, mobile-first. Expo for faster initial iteration. Door left open for web via React Native Web — not a priority.

### Frontend
- React Native with Expo
- Reanimated 3 for card swipe gestures
- Simple card component system with distinct layouts per card type

### Backend
- Python, FastAPI
- REST API with SSE (Server-Sent Events) for real-time card pushes to the feed

### Agent Layer
- Structured prompt chain using the Anthropic SDK directly (no LangGraph yet)
- One prompt chain instance per project, stateless calls with full context passed each time
- LangGraph introduced in v2 when agent complexity warrants it

### Databases
- PostgreSQL: users, projects, raw response store, card queue, RSS feeds
- JSONB column on the project table holds the in-progress context document
- pgvector deferred to v2

### Feed Queue
- Priority queue implemented in PostgreSQL for MVP
- Redis introduced when scale requires it

### Learning Content
- Tavily or Exa API for web search
- Wikipedia API for interest-mapped categories
- Short summarisation prompt trims content to card-sized snippets

### Monetisation (MVP)
- BYOK: users provide their own Anthropic (or OpenAI) API key
- Keeps infrastructure costs near zero while validating the concept
- Subscription model introduced once real usage patterns and per-user costs are understood

---

## Token Cost Notes

RSS cards, Wikipedia snippets, and saved cards cost little to nothing in tokens. AI spend is concentrated on question generation and context evaluation. A feed that is ~60% non-AI content dramatically reduces per-session cost and makes BYOK viable for daily users.

Rough estimate for a heavy daily user on a managed subscription (for future reference): £9–£25/month in API costs alone depending on usage. Price accordingly once real data exists.

---

## Roadmap (Post-MVP)

- Background agent connectors: Cursor, GitHub, Google Docs, etc.
- Agent status cards and follow-up decision cards after agent task completion
- LangGraph orchestration replacing the simple prompt chain
- Document generation UI (export master CV, README, structured prompt, etc.)
- pgvector for semantic search across user's captured knowledge
- Redis for queue scalability
- Curated RSS source directory
- Voice brain dump for project setup
- Web / desktop version

---

## Open Questions (Resolved)

| Question | Decision |
|---|---|
| AI-generated vs templated questions | AI-generated for feed cards, fixed template for onboarding only |
| Primary value: questions or agents? | Question loop is core; agents are additive and compelling but not required for MVP |
| Platform | Mobile-first, React Native |
| Agent framework | Plain prompt chain for MVP, LangGraph deferred |
| Skipped cards | Return at top of next session |
| RSS integration | Manual URL input for MVP, curated directory on roadmap |
| Monetisation | BYOK for MVP, subscription model TBD post-validation |
| Document generation | On-demand only, not automatic |
| Knowledge base structure | Raw response bank (always) + generated document (on request) kept separately |
