.PHONY: install test lint format typecheck verify up down migrate migrate-down migrate-new migrate-status dev pre-commit test-e2e dev-all seed logs clean verify-e2e quality-gate test-pbt test-all test-frontend test-frontend-e2e health init-db build build-frontend

# ── Setup ──
install:
	uv sync
	cd frontend && pnpm install

# ── Build ──
build:
	uv sync
	cd frontend && pnpm build

build-frontend:
	cd frontend && pnpm build

# ── Type Check ──
typecheck:
	uv run ruff check .
	cd frontend && pnpm typecheck

# ── Verify ──
verify: lint typecheck test
	@echo "All checks passed!"

# ── Backend Tests ──
test:
	uv run pytest tests/unit/ -v

test-pbt:
	uv run pytest tests/pbt/ -v

test-integration:
	uv run pytest tests/integration/ -m integration -v

test-e2e:
	uv run pytest tests/e2e/ -m e2e -v

test-all:
	uv run pytest tests/ -v

# ── Frontend Tests ──
test-frontend:
	cd frontend && pnpm test

test-frontend-e2e:
	cd frontend && pnpm exec playwright test --config playwright.integration.config.ts

# ── Code Quality ──
lint:
	uv run ruff check .
	cd frontend && pnpm lint

format:
	uv run ruff format .
	cd frontend && pnpm format

pre-commit:
	uv run pre-commit install

# ── RAG Quality Gate (Ragas) ──
quality-gate:
	uv run python scripts/ragas_quality_gate.py --test-cases tests/quality/test_cases.json --output reports/ragas_report.json

# ── Docker ──
up:
	docker compose up -d

down:
	docker compose down

clean:
	docker compose down -v
	@echo "All Docker volumes removed."

logs:
	docker compose logs -f api-gateway chat-service admin-service knowledge-pipeline

# ── Database ──
migrate:
	uv run alembic upgrade head

migrate-down:
	uv run alembic downgrade -1

migrate-new:
	@read -p "Migration message: " MSG; uv run alembic revision --autogenerate -m "$$MSG"

migrate-status:
	uv run alembic current

# Initialize database (run all migrations + seed)
init-db: migrate seed

# ── Health Check ──
health:
	@docker compose ps
	@echo "Checking services..."
	@curl -sf http://localhost:8000/health || echo "API Gateway not healthy"
	@curl -sf http://localhost:8001/health || echo "Chat Service not healthy"

# ── Development ──
dev:
	uv run uvicorn api_gateway.main:app --reload --port 8000

dev-frontend:
	cd frontend && pnpm dev

dev-all:
	docker compose up -d postgres redis milvus minio
	@echo "Starting all services in development mode..."
	@echo "API Gateway:        http://localhost:8000"
	@echo "Chat Service:       http://localhost:8001"
	@echo "Admin Service:      http://localhost:8002"
	docker compose up api-gateway chat-service admin-service knowledge-pipeline

seed:
	uv run python -m scripts.seed

# ── E2E Verification ──
verify-e2e:
	bash scripts/verify_e2e.sh

# ── Load Testing ──
load-test:
	uv run locust -f tests/load/locustfile.py --host http://localhost --headless -u 5 -r 1 --run-time 120s --csv reports/load --html reports/load_report.html

load-test-api:
	uv run locust -f tests/load/locustfile.py --host http://localhost --headless -u 50 -r 10 --run-time 30s --tags api --csv reports/load_api --html reports/load_api_report.html

load-test-rag:
	uv run locust -f tests/load/rag_load.py --host http://localhost --headless -u 20 -r 5 --run-time 60s --html reports/rag_load_report.html

# ── Visual Regression ──
update-snapshots:
	cd frontend && pnpm exec playwright test --config playwright.integration.config.ts --update-snapshots --grep "visual|responsive"

# ── Monitoring ──
monitoring-up:
	docker compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d prometheus grafana loki

monitoring-down:
	docker compose -f docker-compose.yml -f docker-compose.monitoring.yml down prometheus grafana loki
