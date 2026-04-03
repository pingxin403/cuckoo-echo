.PHONY: install test lint format up down migrate migrate-down migrate-new migrate-status dev pre-commit test-e2e dev-all seed logs clean verify-e2e quality-gate

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
	uv run alembic upgrade head

migrate-down:
	uv run alembic downgrade -1

migrate-new:
	@read -p "Migration message: " MSG; uv run alembic revision --autogenerate -m "$$MSG"

migrate-status:
	uv run alembic current

dev:
	uv run uvicorn api_gateway.main:app --reload --port 8000

dev-all:
	docker compose up -d postgres redis milvus minio
	@echo "Starting all services in development mode..."
	@echo "API Gateway:        http://localhost:8000"
	@echo "Chat Service:       http://localhost:8001"
	@echo "Admin Service:      http://localhost:8002"
	docker compose up api-gateway chat-service admin-service knowledge-pipeline

seed:
	uv run python scripts/seed_tenant.py

logs:
	docker compose logs -f api-gateway chat-service admin-service knowledge-pipeline

verify-e2e:
	bash scripts/verify_e2e.sh

clean:
	docker compose down -v
	@echo "All Docker volumes removed."

quality-gate:
	uv run python scripts/ragas_quality_gate.py --test-cases tests/quality/test_cases.json --output reports/ragas_report.json
