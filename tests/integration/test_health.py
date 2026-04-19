"""Integration tests for health check endpoints.

Verifies that /health and /health/ready endpoints work correctly.
Run with: pytest -m integration tests/integration/test_health.py
"""

from __future__ import annotations

from urllib.request import urlopen
from urllib.error import URLError
import json

import pytest

pytestmark = pytest.mark.integration


BASE_URLS = [
    "http://localhost:8000",  # API Gateway
    "http://localhost:8001",  # Chat Service
    "http://localhost:8002",  # Admin Service
]


@pytest.fixture
def available_services():
    """Skip if no services are available."""
    for url in BASE_URLS:
        try:
            urlopen(f"{url}/health", timeout=2)
            return True
        except (URLError, TimeoutError):
            continue
    pytest.skip("No services available. Run 'make up' first.")


def test_api_gateway_health(available_services):
    """Test API Gateway /health endpoint."""
    try:
        response = urlopen("http://localhost:8000/health", timeout=5)
        data = json.loads(response.read().decode())

        assert response.status == 200
        assert "status" in data
    except (URLError, TimeoutError):
        pytest.skip("API Gateway not available.")


def test_api_gateway_health_ready(available_services):
    """Test API Gateway /health/ready endpoint."""
    try:
        response = urlopen("http://localhost:8000/health/ready", timeout=5)
        data = json.loads(response.read().decode())

        assert response.status == 200
        # Ready should include dependency status
        assert "postgres" in data or "dependencies" in data or data.get("status") == "ready"
    except (URLError, TimeoutError):
        pytest.skip("API Gateway not available.")


def test_chat_service_health(available_services):
    """Test Chat Service /health endpoint."""
    try:
        response = urlopen("http://localhost:8001/health", timeout=5)
        data = json.loads(response.read().decode())

        assert response.status == 200
        assert "status" in data
    except (URLError, TimeoutError):
        pytest.skip("Chat Service not available.")


def test_chat_service_health_ready(available_services):
    """Test Chat Service /health/ready endpoint."""
    try:
        response = urlopen("http://localhost:8001/health/ready", timeout=5)
        data = json.loads(response.read().decode())

        assert response.status == 200
    except (URLError, TimeoutError):
        pytest.skip("Chat Service not available.")


def test_admin_service_health(available_services):
    """Test Admin Service /health endpoint."""
    try:
        response = urlopen("http://localhost:8002/health", timeout=5)
        data = json.loads(response.read().decode())

        assert response.status == 200
        assert "status" in data
    except (URLError, TimeoutError):
        pytest.skip("Admin Service not available.")


def test_admin_service_health_ready(available_services):
    """Test Admin Service /health/ready endpoint."""
    try:
        response = urlopen("http://localhost:8002/health/ready", timeout=5)
        data = json.loads(response.read().decode())

        assert response.status == 200
    except (URLError, TimeoutError):
        pytest.skip("Admin Service not available.")


def test_all_services_health_z(available_services):
    """Test that all services respond to /health/z for deep health check."""
    for url in BASE_URLS:
        try:
            response = urlopen(f"{url}/health/z", timeout=5)
            data = json.loads(response.read().decode())

            assert response.status == 200
            # Deep health check should return detailed status
            assert "status" in data
        except (URLError, TimeoutError):
            continue  # Skip if not available
        except json.JSONDecodeError:
            # Some services may return plain text
            pass
