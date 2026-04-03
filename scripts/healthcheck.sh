#!/bin/bash
# Cuckoo-Echo Health Check Script
# Checks all services and infrastructure components.
# Usage: ./scripts/healthcheck.sh
# Exit code: 0 = all healthy, 1 = one or more unhealthy

set -uo pipefail

PASS=0
FAIL=0

check() {
  local name="$1"
  local cmd="$2"
  if eval "${cmd}" > /dev/null 2>&1; then
    echo "  ✅ ${name}"
    PASS=$((PASS + 1))
  else
    echo "  ❌ ${name}"
    FAIL=$((FAIL + 1))
  fi
}

echo "=== Cuckoo-Echo Health Check ==="
echo "Timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo ""

# ============================================================
# Infrastructure
# ============================================================
echo "--- Infrastructure ---"
check "PostgreSQL" "pg_isready -h ${PG_HOST:-localhost} -p ${PG_PORT:-5432} -U ${PG_USER:-postgres}"
check "Redis" "redis-cli -h ${REDIS_HOST:-localhost} -p ${REDIS_PORT:-6379} ping"
check "Milvus" "curl -sf http://${MILVUS_HOST:-localhost}:9091/healthz"
check "MinIO" "curl -sf http://${MINIO_HOST:-localhost}:9000/minio/health/live"

echo ""

# ============================================================
# Application Services
# ============================================================
echo "--- Application Services ---"
check "API Gateway" "curl -sf http://${GATEWAY_HOST:-localhost}:8000/health"
check "Chat Service" "curl -sf http://${CHAT_HOST:-localhost}:8001/health"
check "Admin Service" "curl -sf http://${ADMIN_HOST:-localhost}:8002/health"

echo ""

# ============================================================
# Database Checks
# ============================================================
echo "--- Database ---"
check "Alembic Migration" "psql -h ${PG_HOST:-localhost} -p ${PG_PORT:-5432} -U ${PG_USER:-postgres} -d ${PG_DB:-cuckoo} -t -c 'SELECT version_num FROM alembic_version LIMIT 1;'"
check "RLS Enabled (users)" "psql -h ${PG_HOST:-localhost} -p ${PG_PORT:-5432} -U ${PG_USER:-postgres} -d ${PG_DB:-cuckoo} -t -c \"SELECT relrowsecurity FROM pg_class WHERE relname='users';\" | grep -q t"

echo ""

# ============================================================
# Summary
# ============================================================
TOTAL=$((PASS + FAIL))
echo "=== Summary: ${PASS}/${TOTAL} checks passed ==="

if [ "${FAIL}" -gt 0 ]; then
  echo "⚠️  ${FAIL} check(s) failed"
  exit 1
else
  echo "All systems operational."
  exit 0
fi
