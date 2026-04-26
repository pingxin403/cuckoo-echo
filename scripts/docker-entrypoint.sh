#!/bin/bash
set -e

# Run Alembic migrations before starting the application service.
# Only the first service to start will actually apply migrations;
# subsequent services will see "already at head" and proceed.
echo "Running database migrations..."
alembic upgrade head 2>&1 || echo "Migration skipped or failed (may already be applied)"

# Execute the original CMD
exec "$@"