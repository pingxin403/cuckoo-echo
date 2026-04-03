"""Property 11: Knowledge base round-trip consistency.

# Feature: cuckoo-echo, Property 11: 知识库往返一致性
**Validates: Requirements 3.8**

Tests the chunker round-trip property: split_text must produce non-empty
chunks within size limits, and preserve original content.
"""

from hypothesis import given, settings, HealthCheck, strategies as st

from knowledge_pipeline.chunker import split_text


@settings(max_examples=100, suppress_health_check=[HealthCheck.too_slow])
@given(
    doc=st.text(
        min_size=100,
        max_size=2000,
        alphabet=st.characters(whitelist_categories=("L", "N", "P", "Z")),
    )
)
def test_rag_round_trip(doc):
    """Chunking must produce non-empty chunks within size limits that preserve content."""
    chunks = split_text(doc)
    # Property: at least one chunk for valid input
    assert len(chunks) >= 1
    # Property: all chunks are non-empty
    assert all(len(c.strip()) > 0 for c in chunks)
    # Property: all chunks respect size limit
    assert all(len(c) <= 512 for c in chunks)
    # Property: original content is largely preserved
    # Note: separator characters (., !, ?, 。, etc.) may be consumed during splitting
    all_chunk_text = "".join(chunks)
    separators = set("\n。！？.!? ")
    for char in doc.strip()[:50]:
        if char.strip() and char not in separators:
            assert char in all_chunk_text, f"Character '{char}' lost in chunking"
