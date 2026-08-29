# GoodScroll developer tasks. Run these from the repo root.
VENV := .venv
BIN  := $(VENV)/bin

.PHONY: install db migrate api web check test

install:  ## Create the virtualenv and install Python + JavaScript dependencies
	python3 -m venv $(VENV)
	$(BIN)/pip install -r requirements-dev.txt
	cd app && npm install

db:  ## Start PostgreSQL in Docker, reusing the container if it already exists
	docker start scrollapp-db 2>/dev/null || docker run --name scrollapp-db \
	  -e POSTGRES_PASSWORD=password \
	  -e POSTGRES_DB=scrollapp \
	  -p 5432:5432 \
	  -d postgres:15

migrate:  ## Apply database migrations
	$(BIN)/alembic upgrade head

api:  ## Run the API on http://localhost:8000
	$(BIN)/uvicorn backend.main:app --reload

web:  ## Run the Expo app in the browser
	cd app && npm run web

check:  ## Lint Python and typecheck TypeScript
	$(BIN)/ruff check .
	cd app && npm run typecheck

test:  ## Run the backend test suite (no database or network required)
	$(BIN)/pytest
