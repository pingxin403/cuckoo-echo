"""Property 2: Embedding idempotency.

# Feature: cuckoo-echo, Property 2: Embedding 幂等性
**Validates: Requirements 3, Acceptance Criterion 6**

For any valid text input, Embedding_Service returns the same vector on repeated calls.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

from hypothesis import given, settings, HealthCheck, strategies as st

from shared.embedding_service import EmbeddingService


def _make_deterministic_embed(dim: int = 8):
    """Create a mock aembedding that returns deterministic vectors based on input hash."""

    async def fake_aembedding(model: str, input: list[str]):
        """Deterministic embedding: same input always produces same vector."""
        results = []
        for text in input:
            h = hash(text)
            vec = [float((h >> (i * 4)) & 0xF) / 15.0 for i in range(dim)]
            results.append({"embedding": vec})

        mock_resp = AsyncMock()
        mock_resp.data = results
        return mock_resp

    return fake_aembedding


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow], deadline=None)
@given(
    text=st.text(
        min_size=1,
        max_size=500,
        alphabet=st.characters(whitelist_categories=("L", "N", "P", "Z")),
    )
)
def test_embedding_idempotency(text):
    """Same text input produces identical vectors on two consecutive calls."""
    svc = EmbeddingService(model="test-model")

    async def _run():
        with patch("litellm.aembedding", side_effect=_make_deterministic_embed()):
            vec1 = await svc.embed(text)
            vec2 = await svc.embed(text)
            return vec1, vec2

    loop = asyncio.new_event_loop()
    try:
        vec1, vec2 = loop.run_until_complete(_run())
    finally:
        loop.close()

    assert len(vec1) == len(vec2), "Vector dimensions must match"
    for i, (a, b) in enumerate(zip(vec1, vec2)):
        assert abs(a - b) < 1e-6, f"Dimension {i} differs: {a} vs {b}"
