"""Integration tests for Milvus partition-key multi-tenant vector isolation.

Verifies that PartitionKey on tenant_id correctly isolates vector search
results between tenants in the knowledge_chunks collection.

Requires a running Milvus instance.
Run with: pytest -m integration
"""

from __future__ import annotations

import time
from uuid import uuid4

import numpy as np
import pytest

try:
    from pymilvus import MilvusClient
except ImportError:
    MilvusClient = None  # type: ignore[assignment,misc]

from shared.milvus_client import (
    COLLECTION_NAME,
    create_knowledge_chunks_collection,
    get_milvus_client,
)

pytestmark = [pytest.mark.integration]

VECTOR_DIM = 1536


@pytest.fixture
def milvus_client():
    """Connect to Milvus. Skip if not available."""
    if MilvusClient is None:
        pytest.skip("pymilvus not installed")
    try:
        client = get_milvus_client()
        # Ensure collection exists
        if not client.has_collection(COLLECTION_NAME):
            create_knowledge_chunks_collection(client)
        yield client
    except Exception:
        pytest.skip("Milvus not available")


def _random_vector(dim: int = VECTOR_DIM) -> list[float]:
    """Generate a random unit vector."""
    vec = np.random.randn(dim).astype(np.float32)
    vec = vec / np.linalg.norm(vec)
    return vec.tolist()


def _insert_vectors(client, tenant_id: str, count: int = 3) -> list[str]:
    """Insert test vectors for a tenant. Returns list of inserted IDs."""
    ids = []
    data = []
    for _ in range(count):
        chunk_id = str(uuid4())
        ids.append(chunk_id)
        data.append(
            {
                "id": chunk_id,
                "tenant_id": tenant_id,
                "doc_id": str(uuid4()),
                "chunk_text": f"Test chunk for tenant {tenant_id[:8]}",
                "dense_vector": _random_vector(),
                "created_at": int(time.time()),
            }
        )
    client.insert(collection_name=COLLECTION_NAME, data=data)
    return ids


def _cleanup_vectors(client, ids: list[str]) -> None:
    """Delete test vectors by ID."""
    if ids:
        id_list = ", ".join(f'"{i}"' for i in ids)
        client.delete(
            collection_name=COLLECTION_NAME,
            filter=f"id in [{id_list}]",
        )


# ------------------------------------------------------------------
# Tests
# ------------------------------------------------------------------


def test_partition_isolation(milvus_client):
    """Search with tenant_a filter returns only tenant_a vectors."""
    tenant_a = str(uuid4())
    tenant_b = str(uuid4())

    ids_a = _insert_vectors(milvus_client, tenant_a, count=3)
    ids_b = _insert_vectors(milvus_client, tenant_b, count=3)

    try:
        # Flush to make data searchable
        milvus_client.flush(collection_name=COLLECTION_NAME)

        # Search with tenant_a filter
        results = milvus_client.search(
            collection_name=COLLECTION_NAME,
            data=[_random_vector()],
            filter=f'tenant_id == "{tenant_a}"',
            limit=10,
            output_fields=["tenant_id"],
            anns_field="dense_vector",
        )

        # All results must belong to tenant_a
        for hits in results:
            for hit in hits:
                entity = hit.get("entity", hit)
                assert entity["tenant_id"] == tenant_a, (
                    f"Expected tenant_id={tenant_a}, got {entity['tenant_id']}"
                )

    finally:
        _cleanup_vectors(milvus_client, ids_a + ids_b)


def test_no_cross_tenant_leakage(milvus_client):
    """Vectors from tenant_b must not appear in tenant_a search results."""
    tenant_a = str(uuid4())
    tenant_b = str(uuid4())

    ids_a = _insert_vectors(milvus_client, tenant_a, count=3)
    ids_b = _insert_vectors(milvus_client, tenant_b, count=3)

    try:
        milvus_client.flush(collection_name=COLLECTION_NAME)

        # Search filtered to tenant_a
        results = milvus_client.search(
            collection_name=COLLECTION_NAME,
            data=[_random_vector()],
            filter=f'tenant_id == "{tenant_a}"',
            limit=10,
            output_fields=["tenant_id", "id"],
            anns_field="dense_vector",
        )

        # Collect all returned IDs
        returned_ids = set()
        for hits in results:
            for hit in hits:
                entity = hit.get("entity", hit)
                returned_ids.add(entity.get("id", hit.get("id")))

        # None of tenant_b's IDs should appear
        leaked = returned_ids & set(ids_b)
        assert len(leaked) == 0, f"Tenant B vectors leaked into tenant A results: {leaked}"

    finally:
        _cleanup_vectors(milvus_client, ids_a + ids_b)


def test_symmetric_isolation(milvus_client):
    """Both tenants see only their own data when searched independently."""
    tenant_a = str(uuid4())
    tenant_b = str(uuid4())

    ids_a = _insert_vectors(milvus_client, tenant_a, count=3)
    ids_b = _insert_vectors(milvus_client, tenant_b, count=3)

    try:
        milvus_client.flush(collection_name=COLLECTION_NAME)

        query_vec = [_random_vector()]

        # Search as tenant_a
        results_a = milvus_client.search(
            collection_name=COLLECTION_NAME,
            data=query_vec,
            filter=f'tenant_id == "{tenant_a}"',
            limit=10,
            output_fields=["tenant_id"],
            anns_field="dense_vector",
        )
        for hits in results_a:
            for hit in hits:
                entity = hit.get("entity", hit)
                assert entity["tenant_id"] == tenant_a

        # Search as tenant_b
        results_b = milvus_client.search(
            collection_name=COLLECTION_NAME,
            data=query_vec,
            filter=f'tenant_id == "{tenant_b}"',
            limit=10,
            output_fields=["tenant_id"],
            anns_field="dense_vector",
        )
        for hits in results_b:
            for hit in hits:
                entity = hit.get("entity", hit)
                assert entity["tenant_id"] == tenant_b

    finally:
        _cleanup_vectors(milvus_client, ids_a + ids_b)
