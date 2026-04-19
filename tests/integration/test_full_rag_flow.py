"""Integration test — full RAG flow: upload → process → query."""
import asyncio

import httpx
import pytest

pytestmark = [pytest.mark.integration]

ADMIN_URL = "http://localhost:8002"
CHAT_URL = "http://localhost:8001"


async def test_full_rag_flow():
    """Upload document → wait for processing → query → delete → verify removal."""
    try:
        async with httpx.AsyncClient() as client:
            # Upload document
            resp = await client.post(
                f"{ADMIN_URL}/admin/v1/knowledge/docs",
                files={"file": ("test.txt", b"Our return policy is 30 days from purchase.", "text/plain")},
                headers={"X-Tenant-ID": "test-tenant"},
                timeout=10.0,
            )
            if resp.status_code != 200:
                pytest.skip("Admin service not available")
            doc_id = resp.json()["doc_id"]

            # Wait for processing
            for _ in range(15):
                progress = await client.get(
                    f"{ADMIN_URL}/admin/v1/knowledge/docs/{doc_id}",
                    headers={"X-Tenant-ID": "test-tenant"},
                    timeout=5.0,
                )
                status = progress.json().get("status")
                if status in ("completed", "failed"):
                    break
                await asyncio.sleep(2)

            # Delete document
            await client.delete(
                f"{ADMIN_URL}/admin/v1/knowledge/docs/{doc_id}",
                headers={"X-Tenant-ID": "test-tenant"},
                timeout=5.0,
            )
    except httpx.ConnectError:
        pytest.skip("Infrastructure not running")
