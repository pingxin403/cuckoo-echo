"""Semantic cache — placeholder for Phase 2.

TODO: Implement using Milvus semantic_cache collection.
- On query, search cache with similarity >= 0.95
- If hit, return cached answer without LLM call
- On miss, cache the new Q&A pair after LLM response
"""
