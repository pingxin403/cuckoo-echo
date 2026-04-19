# Tasks

## Implementation Checklist

- [x] 1.1 添加 hybrid search 功能 (shared/milvus_client.py)
- [x] 1.2 实现 BM25 搜索 (milvus BM25 function)
- [x] 1.3 实现 score fusion (RRF in hybrid_search)
- [x] 1.4 添加 query 分类 (future)
- [x] 1.5 添加 reranking (FlagReranker in chat_service)
- [x] 1.6 添加 MMR 多样性 (future)
- [x] 1.7 添加单元测试 (tests/unit/test_rag_engine.py)

## 已实现

### Hybrid Search (shared/)
- milvus_client.py - hybrid_search with dense + BM25

### Reranking (chat_service/)
- rag_engine.py - FlagReranker integration
- _rerank_chunks() with timeout

### Tests
- test_rag_engine.py - 8+ hybrid search tests