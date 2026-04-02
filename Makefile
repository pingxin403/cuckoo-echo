.PHONY: install test lint format up down migrate dev

install:
	uv sync

test:
	uv run pytest

lint:
	uv run ruff check .

format:
	uv run ruff format .

up:
	docker compose up -d

down:
	docker compose down

migrate:
	psql "postgresql://postgres:postgres@localhost:5432/cuckoo" -f migrations/001_initial.sql

dev:
	uv run uvicorn api_gateway.main:app --reload --port 8000
