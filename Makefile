.PHONY: install test lint format up down migrate dev pre-commit test-e2e

install:
	uv sync

test:
	uv run pytest tests/unit/

test-integration:
	uv run pytest tests/integration/ -m integration -v

test-e2e:
	uv run pytest tests/e2e/ -m e2e -v

lint:
	uv run ruff check .

format:
	uv run ruff format .

pre-commit:
	uv run pre-commit install

up:
	docker compose up -d

down:
	docker compose down

migrate:
	psql "postgresql://postgres:postgres@localhost:5432/cuckoo" -f migrations/001_initial.sql
	psql "postgresql://postgres:postgres@localhost:5432/cuckoo" -f migrations/002_escalation_tables.sql

migrate-status:
	@echo "Migrations are raw SQL files in migrations/"
	@ls -la migrations/*.sql

dev:
	uv run uvicorn api_gateway.main:app --reload --port 8000
