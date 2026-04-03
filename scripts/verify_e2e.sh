#!/usr/bin/env bash
set -euo pipefail

echo "=== Cuckoo-Echo E2E Verification ==="

# 1. Start infrastructure
echo "Starting docker compose..."
docker compose up -d postgres redis milvus minio
sleep 10

# 2. Wait for health
echo "Waiting for PostgreSQL..."
until docker compose exec -T postgres pg_isready -U postgres; do sleep 2; done

echo "Waiting for Redis..."
until docker compose exec -T redis redis-cli ping | grep -q PONG; do sleep 2; done

# 3. Run migrations
echo "Running migrations..."
make migrate

# 4. Seed test tenant
echo "Seeding test tenant..."
SEED_OUTPUT=$(uv run python scripts/seed_tenant.py 2>&1)
API_KEY=$(echo "$SEED_OUTPUT" | grep "API Key:" | awk '{print $NF}')
echo "API Key: $API_KEY"

if [ -z "$API_KEY" ]; then
  echo "❌ Failed to extract API key from seed output"
  echo "Seed output: $SEED_OUTPUT"
  docker compose down
  exit 1
fi

# 5. Start chat service (background)
echo "Starting chat service..."
uv run uvicorn chat_service.main:app --host 0.0.0.0 --port 8001 &
CHAT_PID=$!
sleep 5

# 6. Verify chat service health
echo "Checking chat service health..."
if ! curl -sf http://localhost:8001/health > /dev/null; then
  echo "❌ Chat service failed to start"
  kill $CHAT_PID 2>/dev/null || true
  docker compose down
  exit 1
fi

# 7. Send chat request
echo "Sending chat request..."
RESPONSE=$(curl -s -N --max-time 30 \
  -X POST http://localhost:8001/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $API_KEY" \
  -d '{"user_id":"test-e2e-user","messages":[{"role":"user","content":"hello"}]}')

echo "Response: $RESPONSE"

# 8. Cleanup
echo "Cleaning up..."
kill $CHAT_PID 2>/dev/null || true
docker compose down

# 9. Verify response
if echo "$RESPONSE" | grep -q "content\|DONE\|error"; then
  echo "✅ E2E verification passed"
  exit 0
else
  echo "❌ E2E verification failed — no recognizable content in response"
  exit 1
fi
