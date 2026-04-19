#!/bin/bash
# Cuckoo-Echo Local Development Startup Script
# Starts infrastructure in Docker, services run locally

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "=============================================="
echo "Cuckoo-Echo Local Development Setup"
echo "=============================================="

# Check dependencies
command -v uv >/dev/null 2>&1 || { echo "uv not found. Install: pip install uv"; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "docker not found."; exit 1; }

echo ""
echo "[1/4] Starting infrastructure (Docker)..."
docker compose -f docker-compose.dev.yml up -d
echo "Waiting for infrastructure to be healthy..."
sleep 5

# Wait for postgres
until docker compose -f docker-compose.dev.yml exec -T postgres pg_isready -U postgres >/dev/null 2>&1; do
  echo "  Waiting for PostgreSQL..."
  sleep 2
done

# Wait for redis
until docker compose -f docker-compose.dev.yml exec -T redis redis-cli ping >/dev/null 2>&1; do
  echo "  Waiting for Redis..."
  sleep 2
done

echo "  Infrastructure ready!"

echo ""
echo "[2/4] Installing dependencies..."
uv sync

echo ""
echo "[3/4] Running migrations..."
uv run alembic upgrade head

echo ""
echo "[4/4] Starting services..."
echo ""
echo "=============================================="
echo "Services ready! Start each service in a separate terminal:"
echo ""
echo "  Terminal 1 (API Gateway):"
echo "    uvicorn api_gateway.main:app --reload --port 8000"
echo ""
echo "  Terminal 2 (Chat Service):"
echo "    uvicorn chat_service.main:app --reload --port 8001"
echo ""
echo "  Terminal 3 (Admin Service):"
echo "    python -m admin_service.main"
echo ""
echo "  Terminal 4 (Frontend - optional):"
echo "    cd frontend && pnpm dev"
echo ""
echo "=============================================="
echo "Endpoints:"
echo "  API Gateway:  http://localhost:8000"
echo "  Chat Service: http://localhost:8001"
echo "  Admin Svc:     http://localhost:8002"
echo "  Frontend:      http://localhost:5173"
echo "=============================================="