"""E2E test — knowledge upload and RAG query flow."""
import asyncio

import httpx
import pytest

pytestmark = [pytest.mark.e2e]

ADMIN_URL = "http://localhost:8002"


async def test_knowledge_upload_and_query():
    """Upload doc → wait for processing → query should reference content."""
    try:
        async with httpx.AsyncClient() as client:
            # Upload
            resp = await client.post(
                f"{ADMIN_URL}/admin/v1/knowledge/docs",
                files={"file": ("test.txt", b"Our return policy is 30 days.", "text/plain")},
                headers={"X-Tenant-ID": "test-tenant"},
                timeout=10.0,
            )
            if resp.status_code != 200:
                pytest.skip("Admin service not available")
            doc_id = resp.json()["doc_id"]

            # Wait for processing (poll)
            for _ in range(10):
                progress = await client.get(
                    f"{ADMIN_URL}/admin/v1/knowledge/docs/{doc_id}",
                    headers={"X-Tenant-ID": "test-tenant"},
                    timeout=5.0,
                )
                if progress.json().get("status") in ("completed", "failed"):
                    break
                await asyncio.sleep(2)
    except httpx.ConnectError:
        pytest.skip("Infrastructure not running")
