#!/bin/bash
# Cuckoo-Echo Restore Script
# Restores PostgreSQL from backup and verifies data integrity.
# Usage: ./scripts/restore.sh <backup_dir>
#
# RTO Target: < 4 hours
# Steps: Stop services → Restore PG → Run migrations → Verify → Start services

set -euo pipefail

BACKUP_DIR="${1:?Usage: ./scripts/restore.sh <backup_dir>}"

if [ ! -d "${BACKUP_DIR}" ]; then
  echo "ERROR: Backup directory not found: ${BACKUP_DIR}"
  exit 1
fi

# Database connection (from env or defaults)
PG_HOST="${PG_HOST:-localhost}"
PG_PORT="${PG_PORT:-5432}"
PG_USER="${PG_USER:-postgres}"
PG_DB="${PG_DB:-cuckoo}"
export PGPASSWORD="${PG_PASSWORD:-postgres}"

echo "=== Cuckoo-Echo Restore ==="
echo "Backup directory: ${BACKUP_DIR}"
echo "Timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo ""

# ============================================================
# 1. Pre-flight Checks
# ============================================================
echo "--- Pre-flight Checks ---"

# Find the backup file
PG_BACKUP=$(find "${BACKUP_DIR}" -name "cuckoo_pg_*.sql*" -type f | head -1)
if [ -z "${PG_BACKUP}" ]; then
  echo "ERROR: No PostgreSQL backup file found in ${BACKUP_DIR}"
  exit 1
fi
echo "Backup file: ${PG_BACKUP}"
echo "Size: $(du -h "${PG_BACKUP}" | cut -f1)"

# Check migration version
if [ -f "${BACKUP_DIR}/migration_version.txt" ]; then
  echo "Backup migration version: $(cat "${BACKUP_DIR}/migration_version.txt")"
fi

echo ""
read -p "WARNING: This will DROP and recreate the database. Continue? (yes/no): " CONFIRM
if [ "${CONFIRM}" != "yes" ]; then
  echo "Restore cancelled."
  exit 0
fi

# ============================================================
# 2. Drop and Recreate Database
# ============================================================
echo ""
echo "--- Recreating Database ---"
psql -h "${PG_HOST}" -p "${PG_PORT}" -U "${PG_USER}" -d postgres \
  -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '${PG_DB}' AND pid <> pg_backend_pid();" \
  2>/dev/null || true

psql -h "${PG_HOST}" -p "${PG_PORT}" -U "${PG_USER}" -d postgres \
  -c "DROP DATABASE IF EXISTS ${PG_DB};"

psql -h "${PG_HOST}" -p "${PG_PORT}" -U "${PG_USER}" -d postgres \
  -c "CREATE DATABASE ${PG_DB};"

echo "Database recreated."

# ============================================================
# 3. Restore PostgreSQL Backup
# ============================================================
echo ""
echo "--- Restoring PostgreSQL ---"
pg_restore -h "${PG_HOST}" -p "${PG_PORT}" -U "${PG_USER}" -d "${PG_DB}" \
  --verbose --no-owner --no-privileges \
  "${PG_BACKUP}" 2>&1 | tail -5

echo "PostgreSQL restore complete."

# ============================================================
# 4. Verify Data Integrity
# ============================================================
echo ""
echo "--- Verifying Data Integrity ---"

TENANT_COUNT=$(psql -h "${PG_HOST}" -p "${PG_PORT}" -U "${PG_USER}" -d "${PG_DB}" \
  -t -c "SELECT COUNT(*) FROM tenants;" 2>/dev/null | tr -d ' ')
echo "Tenants: ${TENANT_COUNT}"

THREAD_COUNT=$(psql -h "${PG_HOST}" -p "${PG_PORT}" -U "${PG_USER}" -d "${PG_DB}" \
  -t -c "SELECT COUNT(*) FROM threads;" 2>/dev/null | tr -d ' ')
echo "Threads: ${THREAD_COUNT}"

MESSAGE_COUNT=$(psql -h "${PG_HOST}" -p "${PG_PORT}" -U "${PG_USER}" -d "${PG_DB}" \
  -t -c "SELECT COUNT(*) FROM messages;" 2>/dev/null | tr -d ' ')
echo "Messages: ${MESSAGE_COUNT}"

DOC_COUNT=$(psql -h "${PG_HOST}" -p "${PG_PORT}" -U "${PG_USER}" -d "${PG_DB}" \
  -t -c "SELECT COUNT(*) FROM knowledge_docs;" 2>/dev/null | tr -d ' ')
echo "Knowledge Docs: ${DOC_COUNT}"

ALEMBIC_VER=$(psql -h "${PG_HOST}" -p "${PG_PORT}" -U "${PG_USER}" -d "${PG_DB}" \
  -t -c "SELECT version_num FROM alembic_version LIMIT 1;" 2>/dev/null | tr -d ' ')
echo "Alembic Version: ${ALEMBIC_VER}"

# ============================================================
# 5. Milvus Restore Note
# ============================================================
echo ""
echo "--- Milvus Restore ---"
echo "Milvus data must be restored separately using milvus-backup tool."
echo "See: https://milvus.io/docs/milvus_backup_overview.md"
echo "After PG restore, re-run Knowledge Pipeline to rebuild vectors if needed."

# ============================================================
# Summary
# ============================================================
echo ""
echo "=== Restore Complete ==="
echo "Database: ${PG_DB} restored from ${PG_BACKUP}"
echo "Next steps:"
echo "  1. Verify Alembic migration: uv run alembic current"
echo "  2. Restore Milvus data (if backup available)"
echo "  3. Start application services: docker compose up -d"
echo "  4. Run health check: ./scripts/healthcheck.sh"
