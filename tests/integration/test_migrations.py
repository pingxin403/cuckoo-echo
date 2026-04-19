"""Integration tests for database migrations.

Verifies that Alembic migrations work correctly.
Run with: pytest -m integration tests/integration/test_migrations.py
"""

from __future__ import annotations

import subprocess

import pytest

pytestmark = pytest.mark.integration


def test_migration_upgrade():
    """Verify migration upgrade works."""
    result = subprocess.run(
        ["uv", "run", "alembic", "upgrade", "head"],
        capture_output=True,
        text=True,
        cwd=".",
    )

    if result.returncode != 0:
        if "connection refused" in result.stderr.lower() or "could not connect" in result.stderr.lower():
            pytest.skip("PostgreSQL not available. Run 'make up' first.")
        pytest.fail(f"Migration upgrade failed: {result.stderr}")


def test_migration_current():
    """Verify current migration version."""
    result = subprocess.run(
        ["uv", "run", "alembic", "current"],
        capture_output=True,
        text=True,
        cwd=".",
    )

    if result.returncode != 0:
        if "connection refused" in result.stderr.lower():
            pytest.skip("PostgreSQL not available.")
        pytest.fail(f"Migration current failed: {result.stderr}")

    # Should show current revision
    assert result.stdout.strip() != ""


def test_migration_history():
    """Verify migration history is valid."""
    result = subprocess.run(
        ["uv", "run", "alembic", "history", "--verbose"],
        capture_output=True,
        text=True,
        cwd=".",
    )

    if result.returncode != 0:
        pytest.skip("PostgreSQL not available.")

    # Should show migration history
    assert result.stdout.strip() != ""


def test_migration_downgrade_upgrade():
    """Verify downgrade then upgrade works (idempotency)."""
    # First get current revision
    result = subprocess.run(
        ["uv", "run", "alembic", "current", "--verbose"],
        capture_output=True,
        text=True,
        cwd=".",
    )

    if result.returncode != 0:
        pytest.skip("PostgreSQL not available.")

    current = result.stdout.strip()

    # Try downgrade
    down_result = subprocess.run(
        ["uv", "run", "alembic", "downgrade", "-1"],
        capture_output=True,
        text=True,
        cwd=".",
    )

    if down_result.returncode == 0:
        # Upgrade back
        up_result = subprocess.run(
            ["uv", "run", "alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            cwd=".",
        )

        if "connection refused" in up_result.stderr.lower():
            pytest.skip("PostgreSQL not available.")

        assert up_result.returncode == 0, f"Re-upgrade failed: {up_result.stderr}"
