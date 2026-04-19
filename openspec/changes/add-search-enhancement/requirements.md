# Requirements: Search Enhancement

## Functional

1. **Hybrid Search**
   - Vector + BM25 fusion
   - Weights: vector 0.7, keyword 0.3
   - Query classification

2. **Reranking**
   - Cross-encoder rerank top-20
   - Reorder by relevance
   - Return top-10

## Non-Functional

- Latency: < 500ms
- Accuracy improvement: > 15%

## Out of Scope

- Learning to rank
- Semantic synonyms