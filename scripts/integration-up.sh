#!/usr/bin/env bash
# Quick integration environment startup script
# Usage: bash scripts/integration-up.sh
set -euo pipefail

echo "🚀 Starting Cuckoo-Echo integration environment..."

# 1. Start Docker Compose
echo "📦 Starting Docker services..."
docker compose up -d

# 2. Wait for services to be healthy
echo "⏳ Waiting for services..."
timeout=120
elapsed=0
while ! docker compose ps --format json 2>/dev/null | grep -q '"healthy"'; do
  sleep 5
  elapsed=$((elapsed + 5))
  if [ $elapsed -ge $timeout ]; then
    echo "❌ Timeout waiting for services"
    docker compose ps
    exit 1
  fi
  echo "   ... waiting ($elapsed/${timeout}s)"
done

# 3. Verify key services
echo "🔍 Verifying services..."
curl -sf http://localhost/nginx-health > /dev/null && echo "  ✅ Frontend (Nginx)" || echo "  ❌ Frontend"
curl -sf http://localhost:8000/health > /dev/null && echo "  ✅ API Gateway" || echo "  ❌ API Gateway"
curl -sf http://localhost:8002/health > /dev/null && echo "  ✅ Admin Service" || echo "  ❌ Admin Service"

# 4. Install Playwright browsers if needed
echo "🎭 Checking Playwright..."
cd frontend
if ! pnpm exec playwright --version > /dev/null 2>&1; then
  pnpm install
fi
pnpm exec playwright install chromium --with-deps 2>/dev/null || true
cd ..

echo ""
echo "✅ Integration environment ready!"
echo ""
echo "  管理后台:  http://localhost/login"
echo "  登录账号:  admin@test.com / test123456"
echo "  C端聊天:   http://localhost/chat?api_key=ck_test_integration_key"
echo ""
echo "  运行 E2E:  cd frontend && pnpm exec playwright test --config playwright.integration.config.ts"
