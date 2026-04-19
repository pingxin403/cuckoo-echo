# Proposal: Add Search Enhancement

## Summary

Enhance search capabilities with hybrid search, reranking, and advanced features.

## Problem

- Basic vector search only
- No hybrid search
- No reranking

## Solution

### P0 - Hybrid Search

- **Vector + Keyword**: BM25 + embedding
- **Weighted fusion**: Configurable weights
- **Auto-detection**: Query type detection

### P1 - Reranking

- **Cross-encoder**: Rerank top-K results
- **Learning-to-rank**: (future)
- **Diversity**: MMR reranking

### P2 - Advanced

- **Synonyms**: Synonym expansion
- **Filters**: Metadata filters
- **Facets**: Search facets

## Priority

P1 - Product enhancement

## Impact

- Better search quality
- More relevant results
- User satisfaction