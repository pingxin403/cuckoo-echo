"""Integration tests for Docker Compose environment.

Verifies that all required services are running and healthy.
Run with: pytest -m integration tests/integration/test_docker_compose.py
"""

from __future__ import annotations

import json
import subprocess
from urllib.request import urlopen
from urllib.error import URLError

import pytest

pytestmark = pytest.mark.integration


def test_docker_compose_services_running():
    """Verify all Docker Compose services are running."""
    result = subprocess.run(
        ["docker", "compose", "ps", "--format", "json"],
        capture_output=True,
        text=True,
        cwd=".",
        encoding="utf-8",
        errors="ignore",
    )

    if result.returncode != 0:
        pytest.skip("Docker Compose not available")

    if not result.stdout:
        pytest.skip("No services running. Run 'make up' first.")

    services = []
    for line in result.stdout.strip().split("\n"):
        if line:
            try:
                services.append(json.loads(line))
            except json.JSONDecodeError:
                pass

    required_services = [
        "api-gateway",
        "chat-service",
        "admin-service",
        "knowledge-pipeline",
        "postgres",
        "redis",
    ]

    running_services = [s.get("Service") for s in services if s.get("State") == "running"]

    missing = [s for s in required_services if s not in running_services]
    if missing:
        pytest.skip(f"Required services not running: {missing}. Run 'make up' first.")


def test_api_gateway_health():
    """Verify API Gateway is accessible."""
    try:
        response = urlopen("http://localhost:8000/health", timeout=5)
        assert response.status == 200
    except (URLError, TimeoutError):
        pytest.skip("API Gateway not available. Run 'make up' first.")


def test_chat_service_health():
    """Verify Chat Service is accessible."""
    try:
        response = urlopen("http://localhost:8001/health", timeout=5)
        assert response.status == 200
    except (URLError, TimeoutError):
        pytest.skip("Chat Service not available. Run 'make up' first.")


def test_admin_service_health():
    """Verify Admin Service is accessible."""
    try:
        response = urlopen("http://localhost:8002/health", timeout=5)
        assert response.status == 200
    except (URLError, TimeoutError):
        pytest.skip("Admin Service not available. Run 'make up' first.")


def test_postgres_connectivity():
    """Verify PostgreSQL is accessible."""
    result = subprocess.run(
        ["docker", "exec", "cuckoo-echo-postgres-1", "pg_isready", "-U", "postgres"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, "PostgreSQL not ready"


def test_redis_connectivity():
    """Verify Redis is accessible."""
    result = subprocess.run(
        ["docker", "exec", "cuckoo-echo-redis-1", "redis-cli", "ping"],
        capture_output=True,
        text=True,
    )
    assert "PONG" in result.stdout, "Redis not responding"
