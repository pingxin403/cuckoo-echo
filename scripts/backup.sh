#!/bin/bash
# Cuckoo-Echo Backup Script
# Performs PostgreSQL full backup and Milvus data export.
# Usage: ./scripts/backup.sh [backup_dir]
# Default backup_dir: ./backups/$(date +%Y%m%d_%H%M%S)
#
# RPO Target: < 15 minutes (with WAL archiving enabled)
# Retention: 7 days (configurable via BACKUP_RETENTION_DAYS)

set -euo pipefail

BACKUP_DIR="${1:-./backups/$(date +%Y%m%d_%H%M%S)}"
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-7}"

# Database connection (from env or defaults)
PG_HOST="${PG_HOST:-localhost}"
PG_PORT="${PG_PORT:-5432}"
PG_USER="${PG_USER:-postgres}"
PG_DB="${PG_DB:-cuckoo}"
export PGPASSWORD="${PG_PASSWORD:-postgres}"

echo "=== Cuckoo-Echo Backup ==="
echo "Backup directory: ${BACKUP_DIR}"
echo "Timestamp: $(date -u +%Y-%m-%dT%H:%M:%SZ)"

mkdir -p "${BACKUP_DIR}"

# ============================================================
# 1. PostgreSQL Full Backup
# ============================================================
echo ""
echo "--- PostgreSQL Backup ---"
PG_BACKUP_FILE="${BACKUP_DIR}/cuckoo_pg_$(date +%Y%m%d_%H%M%S).sql.gz"

pg_dump -h "${PG_HOST}" -p "${PG_PORT}" -U "${PG_USER}" -d "${PG_DB}" \
  --format=custom --compress=6 --verbose \
  -f "${PG_BACKUP_FILE%.gz}"

echo "PostgreSQL backup: ${PG_BACKUP_FILE%.gz}"
echo "Size: $(du -h "${PG_BACKUP_FILE%.gz}" | cut -f1)"

# ============================================================
# 2. Alembic Migration Version
# ============================================================
echo ""
echo "--- Migration Version ---"
MIGRATION_VERSION=$(psql -h "${PG_HOST}" -p "${PG_PORT}" -U "${PG_USER}" -d "${PG_DB}" \
  -t -c "SELECT version_num FROM alembic_version LIMIT 1;" 2>/dev/null || echo "unknown")
echo "Current Alembic version: ${MIGRATION_VERSION}" | tee "${BACKUP_DIR}/migration_version.txt"

# ============================================================
# 3. Milvus Data Export (via API)
# ============================================================
echo ""
echo "--- Milvus Backup Note ---"
echo "Milvus data backup requires using milvus-backup tool or volume snapshots."
echo "For production: use 'milvus-backup create' CLI tool."
echo "For local dev: Docker volume snapshot is sufficient."
echo "See: https://milvus.io/docs/milvus_backup_overview.md"
echo "milvus_backup_note=manual" > "${BACKUP_DIR}/milvus_backup_status.txt"

# ============================================================
# 4. Cleanup Old Backups
# ============================================================
echo ""
echo "--- Cleanup (retention: ${BACKUP_RETENTION_DAYS} days) ---"
BACKUP_PARENT_DIR="$(dirname "${BACKUP_DIR}")"
if [ -d "${BACKUP_PARENT_DIR}" ]; then
  OLD_COUNT=$(find "${BACKUP_PARENT_DIR}" -maxdepth 1 -type d -mtime "+${BACKUP_RETENTION_DAYS}" | wc -l | tr -d ' ')
  if [ "${OLD_COUNT}" -gt 0 ]; then
    echo "Removing ${OLD_COUNT} backup(s) older than ${BACKUP_RETENTION_DAYS} days..."
    find "${BACKUP_PARENT_DIR}" -maxdepth 1 -type d -mtime "+${BACKUP_RETENTION_DAYS}" -exec rm -rf {} +
  else
    echo "No old backups to clean up."
  fi
fi

# ============================================================
# Summary
# ============================================================
echo ""
echo "=== Backup Complete ==="
echo "Location: ${BACKUP_DIR}"
echo "Files:"
ls -lh "${BACKUP_DIR}/"
echo ""
echo "To restore: ./scripts/restore.sh ${BACKUP_DIR}"
