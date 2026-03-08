#!/usr/bin/env bash
# Launch the GoodScroll backend (PostgreSQL + migrations + uvicorn).
# Run from repo root. Requires Docker for PostgreSQL.

set -e
cd "$(dirname "$0")/.."

echo "==> 1. PostgreSQL (Docker)"
if ! docker info &>/dev/null; then
  echo "Docker is not running. Start Docker Desktop (or the daemon), then run this script again."
  exit 1
fi
if ! docker ps --format '{{.Names}}' | grep -qx scrollapp-db; then
  if docker ps -a --format '{{.Names}}' | grep -qx scrollapp-db; then
    docker start scrollapp-db
    echo "Started existing container scrollapp-db"
  else
    docker run --name scrollapp-db \
      -e POSTGRES_PASSWORD=password \
      -e POSTGRES_DB=scrollapp \
      -p 5432:5432 \
      -d postgres:15
    echo "Created and started scrollapp-db"
  fi
  echo "Waiting for Postgres to accept connections..."
  sleep 3
fi
echo "PostgreSQL: OK"

echo "==> 2. Environment"
if [ ! -f .env ]; then
  echo "Missing .env. Create it with ANTHROPIC_API_KEY and DATABASE_URL."
  exit 1
fi
echo ".env: OK"

echo "==> 3. Dependencies"
source .venv/bin/activate
pip install -r backend/requirements.txt -q
echo "Dependencies: OK"

echo "==> 4. Migrations"
alembic upgrade head
echo "Migrations: OK"

echo "==> 5. (Optional) Seed from SQLite"
if [ -f backend/scroll.db ]; then
  python scripts/seed_from_sqlite.py || true
else
  echo "No backend/scroll.db; skipping seed"
fi

echo "==> 6. Start server"
echo "API will be at http://localhost:8000 (docs: http://localhost:8000/docs)"
exec uvicorn backend.main:app --reload --host 0.0.0.0
